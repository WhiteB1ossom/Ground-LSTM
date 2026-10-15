"""Ownership, output failures and numerical faults must not poison later input."""

import json
from pathlib import Path
from threading import Event

import numpy as np
import pandas as pd
import pytest

from src.preprocessing.scaling import ScalingOverflowError
from src.realtime import replay as replay_module
from src.realtime.decision import DecisionEngine
from src.realtime.recorder import EventRecorder
from src.realtime.service import RealtimeService
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import TimelineWriter, iter_timeline
from test_realtime_bugfixes import replay_settings
from test_realtime_integration import FakeEngine, observation, settings


def event_files(directory):
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]


def test_editing_returned_pre_and_post_samples_cannot_change_saved_event(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=.2, post_seconds=1., period_seconds=.1)
    pipeline = RealtimePipeline(FakeEngine(), settings(), recorder)
    try:
        first = pipeline.feed(observation(0., .9))[0]
        expected = first["processed_values"].copy()
        first["processed_values"][0] = 9999
        first["raw_observation"]["v"] = 9999
        pipeline.feed(observation(.1, .9))
        pipeline.feed(observation(.2, .9))
        post = pipeline.feed(observation(.3, .9))[0]
        post["decision"]["alarm_active"] = False
        post["physical_values"]["v"] = 9999
    finally: recorder.close()
    event = event_files(tmp_path / "events")[0]
    assert event["samples"][0]["processed_values"] == expected
    assert event["samples"][0]["raw_observation"]["v"] == .9
    assert event["samples"][-1]["decision"]["alarm_active"]
    assert event["samples"][-1]["physical_values"]["v"] == .9


def test_editing_event_row_while_writer_is_queued_cannot_change_disk_data(tmp_path, monkeypatch):
    entered, release = Event(), Event()
    original = Path.open
    def delayed_open(path, *args, **kwargs):
        if path.suffix == ".partial":
            entered.set()
            assert release.wait(5), "Writer did not unblock"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", delayed_open)
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0., post_seconds=0., period_seconds=.1)
    row = {"timestamp_ns": 0, "processed_values": [1., 2.], "raw_observation": {"v": .9}}
    try:
        recorder.consume(row, DecisionEngine(.7, .4).update(0, .9, available=True))
        assert entered.wait(5)
        row["processed_values"][0] = 9999
        row["raw_observation"]["v"] = 9999
    finally:
        release.set()
        recorder.close()
    assert event_files(tmp_path / "events")[0]["samples"] == [
        {"timestamp_ns": 0, "processed_values": [1., 2.], "raw_observation": {"v": .9}}]


def test_mutating_configuration_metadata_cannot_change_saved_event(tmp_path):
    metadata = {"settings": {"threshold": .7}}
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0., post_seconds=0., period_seconds=.1, metadata=metadata)
    metadata["settings"]["threshold"] = .1
    recorder.consume({"timestamp_ns": 0}, DecisionEngine(.7, .4).update(0, .9, available=True))
    recorder.close()
    assert event_files(tmp_path / "events")[0]["metadata"] == {"settings": {"threshold": .7}}


def test_live_report_counts_actual_timeline_write_failures(tmp_path):
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    writer = TimelineWriter(tmp_path, segment_bytes=32)
    stop, calls = Event(), [0]
    for t in (0., .1, .2): service.submit(observation(t, .9))
    def emit(row):
        calls[0] += 1
        if calls[0] == 3: stop.set()
        return writer.write(row)
    try: report = service.run(stop, emit)
    finally: trace = writer.close()
    assert report["status"] == "DEGRADED" and report["accepted_observations"] == 3
    assert report["output_failure_count"] == 3 and trace["dropped_records"] == 3


def test_live_callback_returning_none_is_a_success():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    stop, rows = Event(), []
    for t in (0., .1, .2): service.submit(observation(t, .9))
    def emit(row):
        rows.append(row)
        if len(rows) == 3: stop.set()
    report = service.run(stop, emit)
    assert report["status"] == "SUCCESS" and report["output_failure_count"] == 0
    assert report["processing_failure_count"] == 0 and report["pending_observations"] == 0


def test_live_failed_status_write_is_counted():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    stop = Event()
    service.submit(observation(0., .9))
    service.submit(observation(0., .9))
    def emit(row):
        if row.get("record_type") == "STATUS":
            stop.set()
            return False
        return True
    report = service.run(stop, emit)
    assert report["output_failure_count"] == 1 and report["rejected_observations"] == 1
    assert report["status"] == "DEGRADED"


def test_stopping_with_queued_input_reports_pending_records():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    service.submit(observation(0., .9))
    stop = Event()
    stop.set()
    report = service.run(stop, lambda row: None)
    assert report["pending_observations"] == 1 and report["accepted_observations"] == 0
    assert report["status"] == "DEGRADED"


@pytest.mark.parametrize("bad_value", [1e300, -1e300])
def test_overflow_marks_row_invalid_holds_alarm_and_recovers_with_clean_window(bad_value):
    engine = FakeEngine()
    pipeline = RealtimePipeline(engine, settings())
    for t in (0., .1, .2, .3): pipeline.feed(observation(t, .9))
    assert pipeline.decision.active and engine.calls == 1
    failed = pipeline.feed(observation(.4, bad_value))[0]
    assert failed["input_status"] == "PREPROCESSING_ERROR" and not failed["available"] and not failed["window_valid"]
    assert failed["decision"]["reason"].startswith("PREPROCESSING_ERROR:")
    assert failed["decision"]["status"] == "UNAVAILABLE" and failed["decision"]["alarm_active"]
    assert np.isfinite(failed["processed_values"]).all() and failed["prediction"] is None and engine.calls == 1
    for t in (.5, .6, .7):
        row = pipeline.feed(observation(t, 0.))[0]
        assert not row["available"] and row["decision"]["alarm_active"] and engine.calls == 1
    recovered = pipeline.feed(observation(.8, 0.))[0]
    assert recovered["available"] and not recovered["decision"]["alarm_active"] and engine.calls == 2


def test_scaler_numeric_fault_is_explicit_and_restores_numpy_error_policy():
    scaler = FakeEngine().scaler
    previous = np.geterr().copy()
    with pytest.raises(ScalingOverflowError): scaler.transform(np.array([[1e300, 0., 0.]]), scaler.order)
    assert np.geterr() == previous
    assert np.isfinite(scaler.transform(np.array([[.9, 0., 0.]]), scaler.order)).all()


def test_unexpected_scaler_contract_error_is_not_hidden(monkeypatch):
    engine = FakeEngine()
    def wrong_contract(*args): raise ValueError("Feature matrix shape mismatch")
    monkeypatch.setattr(engine.scaler, "transform", wrong_contract)
    pipeline = RealtimePipeline(engine, settings())
    with pytest.raises(ValueError, match="Feature matrix shape mismatch"):
        pipeline.feed(observation(0., .9))


def fault_observations():
    return [observation(t, 1e300 if t == .4 else .9) for t in (0., .1, .2, .3, .4, .5, .6, .7, .8)]


def test_live_report_counts_preprocessing_fault_without_rejecting_later_input():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    values = fault_observations()
    for value in values: service.submit(value)
    stop, rows = Event(), []
    def emit(row):
        rows.append(row)
        if len(rows) == len(values): stop.set()
    report = service.run(stop, emit)
    assert report["accepted_observations"] == len(values) and report["rejected_observations"] == 0
    assert report["status"] == "DEGRADED" and report["processing_failure_count"] == 1
    assert rows[-1]["available"] and report["output_failure_count"] == 0


def test_replay_overflow_is_degraded_and_remaining_observations_are_processed(tmp_path, monkeypatch):
    def backend(*args, **kwargs):
        engine = FakeEngine()
        engine.manifest.update(model_version="fake", synthetic_demo=True, files={"scaler.json": "fixture"})
        return engine
    monkeypatch.setattr(replay_module, "InferenceEngine", backend)
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    pd.DataFrame(fault_observations()).to_csv(path, index=False)
    result = replay_module.replay(path, tmp_path / "bundle", replay_settings(), tmp_path / "out")
    assert result["status"] == "DEGRADED" and result["preprocessing_failure_count"] == 1
    assert result["rejected_observation_count"] == 0 and result["aligned_rows"] == 9
    rows = list(iter_timeline(tmp_path / "out"))
    assert rows[4]["input_status"] == "PREPROCESSING_ERROR" and rows[-1]["available"]
