"""Regression tests for typed timestamps, silent input and bounded trace failures."""

from datetime import datetime, timezone
import json
from pathlib import Path
from queue import Full
from threading import Event, Thread

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from src.realtime import replay as replay_module
from src.realtime.recorder import EventRecorder
from src.realtime.serialization import json_value
from src.realtime.service import RealtimeService
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import TimelineWriter, iter_timeline
from test_realtime_integration import FakeEngine, observation, settings


def replay_settings():
    return {**settings(), "post_event_seconds": .2, "writer_queue_capacity": 16, "max_active_events": 4,
            "max_event_seconds": 2, "max_saved_events": 10}


@pytest.fixture
def fake_backend(monkeypatch):
    def engine(*args, **kwargs):
        instance = FakeEngine()
        instance.manifest.update(model_version="fake", synthetic_demo=True, files={"scaler.json": "fixture"})
        return instance
    monkeypatch.setattr(replay_module, "InferenceEngine", engine)
    return engine


@pytest.mark.parametrize("unit", ["s", "ms", "us", "ns"])
def test_typed_parquet_replay_matches_csv_and_saves_events(tmp_path, fake_backend, unit):
    raw = tmp_path / "raw"
    raw.mkdir()
    frame = pd.DataFrame([observation(t, .9) for t in range(5)])
    frame.to_csv(raw / "input.csv", index=False)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    stamps = pa.array(pd.to_datetime(frame["timestamp"]).dt.to_pydatetime().tolist(), type=pa.timestamp(unit, tz="UTC"))
    table = table.set_column(0, "timestamp", stamps)
    pq.write_table(table, raw / "input.parquet")
    results = []
    traces = []
    for kind in ("csv", "parquet"):
        out = tmp_path / kind
        result = replay_module.replay(raw / f"input.{kind}", tmp_path / "bundle", replay_settings(), out)
        assert result["status"] == "SUCCESS" and result["timeline"]["error_count"] == 0
        assert result["recorder"]["saved_events"] > 0 and not result["recorder"]["writer_errors"]
        rows = list(iter_timeline(out))
        assert isinstance(rows[0]["raw_observation"]["timestamp"], str)
        events = [json.loads(p.read_text(encoding="utf-8")) for p in (out / "events").glob("*.json")]
        assert all(isinstance(r["raw_observation"]["timestamp"], str) for event in events for r in event["samples"] if r["raw_observation"])
        results.append(result["evaluation"])
        traces.append([{key: row[key] for key in ("timestamp_ns", "processed_values", "decision", "input_status")} for row in rows])
    assert results[0] == results[1] and traces[0] == traces[1]


def test_json_normalization_preserves_timezone_and_missing_metadata():
    stamp = datetime(2026, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
    result = json.loads(json.dumps(json_value({"timestamp": stamp, "flag": np.bool_(True), "missing": pd.NaT})))
    assert result == {"timestamp": "2026-01-01T00:00:00.123456+00:00", "flag": True, "missing": None}


def test_timeout_holds_alarm_and_recovery_requires_fresh_window():
    now = [0.]
    engine = FakeEngine()
    pipeline = RealtimePipeline(engine, {**settings(), "input_timeout_seconds": .5}, clock=lambda: now[0])
    for t in (0., .1, .2): pipeline.feed(observation(t, .9))
    assert engine.calls == 1 and pipeline.decision.active
    now[0] = .499
    assert pipeline.poll() is None
    now[0] = .5
    status = pipeline.poll()
    assert status["decision"]["status"] == "UNAVAILABLE" and status["decision"]["alarm_active"]
    assert status["prediction"] is None and "timestamp_ns" not in status
    assert pipeline.ring.size == 0 and engine.calls == 1
    now[0] = .6
    assert pipeline.poll() is None and pipeline.input_timeouts == 1
    first = pipeline.feed(observation(.3, 0.))[0]
    assert first["input_status"] == "WARMING_UP" and first["decision"]["alarm_active"]
    pipeline.feed(observation(.4, 0.))
    last = pipeline.feed(observation(.5, 0.))[0]
    assert last["input_status"] == "READY" and not last["decision"]["alarm_active"]
    assert engine.calls == 2


def test_timeout_before_first_packet_and_invalid_packet_cannot_refresh_it():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), {**settings(), "input_timeout_seconds": .5}, clock=lambda: now[0])
    now[0] = .5
    with pytest.raises(ValueError): pipeline.feed(observation(0, .9) | {"timestamp": "invalid"})
    status = pipeline.poll()
    assert status["last_observation_timestamp"] is None and status["decision"]["status"] == "UNAVAILABLE"


def test_timeout_flushes_incomplete_post_event(tmp_path):
    now = [0.]
    recorder = EventRecorder(tmp_path / "events", pre_seconds=.2, post_seconds=1, period_seconds=.1, max_event_seconds=3)
    pipeline = RealtimePipeline(FakeEngine(), {**settings(), "input_timeout_seconds": .5}, recorder, clock=lambda: now[0])
    for t in (0., .1, .2): pipeline.feed(observation(t, .9))
    now[0] = .5
    pipeline.poll()
    report = recorder.close()
    assert report["saved_events"] == 1
    event = json.loads(next((tmp_path / "events").glob("*.json")).read_text(encoding="utf-8"))
    assert not event["complete"] and event["completion_reason"] == "INPUT_TIMEOUT"


def test_live_loop_detects_silence_without_new_input():
    engine = FakeEngine()
    pipeline = RealtimePipeline(engine, {**settings(), "input_timeout_seconds": .2})
    service = RealtimeService(pipeline, queue_capacity=4, poll_interval_seconds=.01)
    for t in (0., .1, .2): service.submit(observation(t, .9))
    stop, timed_out = Event(), Event()
    records, reports = [], []
    def emit(row):
        records.append(row)
        if row["input_status"] == "INPUT_TIMEOUT":
            timed_out.set()
            stop.set()
    worker = Thread(target=lambda: reports.append(service.run(stop, emit)))
    worker.start()
    try: assert timed_out.wait(3), "Idle receive loop did not emit timeout"
    finally:
        stop.set()
        worker.join(3)
    assert not worker.is_alive() and engine.calls == 1
    assert records[-1]["decision"]["alarm_active"]
    assert reports[0]["accepted_observations"] == 3 and reports[0]["input_timeouts"] == 1


def test_live_queue_overflow_is_explicit_and_bounded():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()), queue_capacity=1)
    service.submit(observation(0, .9))
    with pytest.raises(Full): service.submit(observation(.1, .9))
    assert service.inbox.qsize() == 1 and service.dropped == 1


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf")])
def test_invalid_watchdog_settings(timeout):
    with pytest.raises(ValueError): RealtimePipeline(FakeEngine(), {**settings(), "input_timeout_seconds": timeout})


def test_watchdog_rejects_clock_rollback():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    now[0] = -1
    with pytest.raises(ValueError, match="monotonic"): pipeline.poll()


def test_trace_rotation_preserves_byte_limit_order_and_unrelated_files(tmp_path):
    other = tmp_path / "original.jsonl"
    other.write_text("preserve", encoding="utf-8")
    writer = TimelineWriter(tmp_path, segment_bytes=90, max_segments=3)
    for i in range(30): assert writer.write({"index": i, "text": "센서"})
    report = writer.close()
    assert report["evicted_records"] > 0 and report["retained_records"] + report["evicted_records"] == 30
    assert len(report["files"]) <= 3 and report["retained_payload_bytes"] <= 270
    assert all((tmp_path / f).stat().st_size <= 90 for f in report["files"])
    assert other.read_text(encoding="utf-8") == "preserve"
    (tmp_path / "summary.json").write_text(json.dumps({"timeline": report}), encoding="utf-8")
    with pytest.raises(ValueError, match="retention"): list(iter_timeline(tmp_path))
    rows = list(iter_timeline(tmp_path, require_complete=False))
    assert rows[-1]["index"] == 29 and [r["index"] for r in rows] == sorted(r["index"] for r in rows)


def test_oversized_record_is_reported_and_never_exceeds_quota(tmp_path):
    writer = TimelineWriter(tmp_path, segment_bytes=32, max_segments=1)
    assert not writer.write({"payload": "x" * 128})
    report = writer.close()
    assert report["error_count"] == 1 and report["dropped_records"] == 1
    assert (tmp_path / "timeline.jsonl").stat().st_size == 0


def test_rotation_disk_failure_is_reported_and_preserves_previous_file(tmp_path, monkeypatch):
    writer = TimelineWriter(tmp_path, segment_bytes=16, max_segments=2)
    assert writer.write({"i": 0})
    original = Path.open
    def denied(path, *args, **kwargs):
        if path.name == "timeline.000001.jsonl": raise PermissionError("disk unavailable")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", denied)
    assert not writer.write({"i": 1})
    assert not writer.write({"i": 2})
    report = writer.close()
    assert report["disabled"] and report["error_count"] == 1 and report["dropped_records"] == 2
    assert json.loads((tmp_path / "timeline.jsonl").read_text()) == {"i": 0}


@pytest.mark.parametrize("value", [0, True, -1])
def test_invalid_trace_limits(tmp_path, value):
    with pytest.raises(ValueError): TimelineWriter(tmp_path, segment_bytes=value)


@pytest.mark.parametrize("kind,expected", [("success", 0), ("rejected", 1), ("storage", 1), ("inference", 1), ("empty", 1), ("config", 2)])
def test_cli_exit_code_matches_recorded_status(tmp_path, monkeypatch, fake_backend, kind, expected):
    raw = tmp_path / "raw"
    raw.mkdir()
    options = replay_settings()
    frame = pd.DataFrame([observation(t, .9) for t in (0., .1, .2)])
    if kind == "rejected": frame.loc[0, "timestamp"] = "invalid"
    if kind == "empty": frame = frame.iloc[:0]
    if kind == "config": options["input_timeout_seconds"] = 0
    if kind == "storage": options["timeline_segment_bytes"] = 32
    if kind == "inference":
        def failing(*args, **kwargs):
            engine = fake_backend()
            def predict(tensor): raise RuntimeError("model unavailable")
            engine.predict = predict
            return engine
        monkeypatch.setattr(replay_module, "InferenceEngine", failing)
    path, out = raw / "input.csv", tmp_path / "out"
    frame.to_csv(path, index=False)
    monkeypatch.setattr(replay_module, "read_yaml", lambda _: {"replay": options})
    code = replay_module.main(["--input", str(path), "--bundle", str(tmp_path / "bundle"), "--output", str(out)])
    assert code == expected
    if expected != 2:
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        assert summary["status"] == ("SUCCESS" if expected == 0 else "DEGRADED")


def test_cli_writer_error_returns_nonzero(tmp_path, monkeypatch, fake_backend):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    pd.DataFrame([observation(t, .9) for t in (0., .1, .2)]).to_csv(path, index=False)
    options = {**replay_settings(), "post_event_seconds": 0}
    monkeypatch.setattr(replay_module, "read_yaml", lambda _: {"replay": options})
    original = Path.open
    def denied(path, *args, **kwargs):
        if path.suffix == ".partial": raise PermissionError("disk unavailable")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", denied)
    out = tmp_path / "out"
    assert replay_module.main(["--input", str(path), "--bundle", str(tmp_path / "bundle"), "--output", str(out)]) == 1
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["recorder"]["writer_error_count"] == 1


@pytest.mark.parametrize("schema_version,expected", [(1, 0), (None, 2)])
def test_cli_uses_real_schema_validation(tmp_path, fake_backend, schema_version, expected):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    pd.DataFrame([observation(t, .9) for t in (0., .1, .2)]).to_csv(path, index=False)
    config = {"replay": replay_settings()}
    if schema_version is not None: config["schema_version"] = schema_version
    config_path = tmp_path / "replay.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    assert replay_module.main(["--input", str(path), "--bundle", str(tmp_path / "bundle"),
                               "--config", str(config_path), "--output", str(tmp_path / "out")]) == expected
