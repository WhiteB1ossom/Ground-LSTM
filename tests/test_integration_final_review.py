"""Integration failures and identities that cannot be checked by training scores."""

import json
from pathlib import Path
from threading import Event

import numpy as np
import pandas as pd
import pytest

from src.dataset.events import extract_events
from src.dataset.split import assert_event_isolation
from src.dataset.split import split_raw
from src.evaluation.timeline import timeline_metrics
from src.realtime.decision import DecisionEngine
from src.realtime.recorder import EventRecorder


def test_reused_event_id_in_separate_sessions_is_isolated():
    first = pd.DataFrame({"device_id": ["one"], "session_id": ["a"], "event_id": ["1"]})
    second = first.assign(session_id="b")
    assert_event_isolation({"train": first, "test": second})
    with pytest.raises(ValueError, match="leakage"):
        assert_event_isolation({"train": first, "test": first})


def test_extracted_events_cannot_mix_sessions_with_same_clock():
    stamp = "2026-01-01T00:00:00Z"
    frame = pd.DataFrame({"timestamp": pd.to_datetime([stamp, stamp]), "event_timestamp": [stamp, stamp],
                          "device_id": ["one"] * 2, "session_id": ["a", "b"], "event_id": ["1"] * 2,
                          "source": ["monitoring"] * 2, "acquisition_kind": ["synthetic"] * 2})
    records, segments = extract_events(frame, {"pre_event_seconds": 1, "post_event_seconds": 1},
                                       {"naive_policy": "reject", "output_timezone": "UTC"})
    assert len(records) == 2 and all(len(s) == 1 for s in segments.values())


def test_event_split_keeps_multiple_events_in_one_acquisition():
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=6, freq="s", tz="UTC"),
                          "device_id": ["one"] * 6, "session_id": ["a", "a", "b", "b", "c", "c"],
                          "event_id": ["normal", "risk"] * 3})
    parts, _ = split_raw(frame, {"mode": "event", "ratios": [.6, .2, .2], "purge_gap_seconds": 0})
    assert [set(parts[name]["session_id"]) for name in ("train", "validation", "test")] == [{"a"}, {"b"}, {"c"}]


def test_offline_and_live_definitions_include_rule_cube():
    rows = []
    engine = DecisionEngine(.5, .5)
    for i, (truth, score, rule) in enumerate((("normal", .8, False), ("risk", .8, True), ("normal", .1, None))):
        state = engine.update(i, score, available=True)
        rows.append({"timestamp_ns": i * 10**9, "device_id": "one", "session_id": "a", "ground_truth": truth,
                     "available": True, "prediction": {"risk_score": score}, "sensor_rules": {"condition_met": rule},
                     "decision": {"alarm_active": state.alarm_active, "transition": state.transition}})
    result = timeline_metrics(rows, threshold=.5, period_seconds=1)
    assert result["false_alarm_episodes"] == 1 and result["unmatched_alarm_episodes"] == 0
    assert result["rule_condition_by_truth_by_prediction"][0][0][1] == 1
    assert result["rule_condition_by_truth_by_prediction"][1][1][1] == 1
    assert result["rule_unknown_scored_windows"] == 1


def test_event_storage_limit_preserves_first_file(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1, max_saved_events=1)
    engine = DecisionEngine(.5, .5)
    for i, score in enumerate((.8, .1, .8)):
        recorder.consume({"timestamp_ns": i}, engine.update(i, score, available=True))
    report = recorder.close()
    assert report["saved_events"] == 1 and report["writer_error_count"] == 1
    assert "EVENT_STORAGE_LIMIT" in report["writer_errors"][0]["error"]
    assert len(list((tmp_path / "events").glob("*.json"))) == 1


def test_queue_overflow_does_not_wait_for_disk(tmp_path, monkeypatch):
    entered, release = Event(), Event()
    original = Path.open
    def slow_open(path, *args, **kwargs):
        if path.suffix == ".partial":
            entered.set()
            assert release.wait(5), "Test writer failed to unblock"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", slow_open)
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1, queue_capacity=1)
    engine = DecisionEngine(.5, .5)
    try:
        recorder.consume({"timestamp_ns": 0}, engine.update(0, .8, available=True))
        assert entered.wait(5)
        for i, score in enumerate((.1, .8, .1, .8), 1):
            recorder.consume({"timestamp_ns": i}, engine.update(i, score, available=True))
        assert recorder.dropped == 1
        assert recorder.errors[-1]["error"] == "WRITER_QUEUE_FULL"
    finally:
        release.set()
        report = recorder.close()
    assert report["saved_events"] == 2
