"""Backend failures, status isolation, off-grid capture and temporary ownership."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.evaluation.stream_metrics import StreamMetrics
from src.evaluation.timeline import timeline_metrics
from src.realtime import recorder as recorder_module
from src.realtime import replay as replay_module
from src.realtime.decision import DecisionEngine
from src.realtime.inference import InferenceEngine
from src.realtime.recorder import EventRecorder
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import iter_timeline
from test_realtime_bugfixes import replay_settings
from test_realtime_integration import FakeEngine, observation, settings


def keras_adapter(callback):
    """Exercise real inference code with an injected TensorFlow operation."""
    import tensorflow as tf
    fixture = FakeEngine()
    engine = InferenceEngine.__new__(InferenceEngine)
    engine.kind, engine.shape, engine.threshold = "lstm", fixture.shape, fixture.threshold
    engine.manifest = {**fixture.manifest, "class_count": 2, "model_version": "failure-fixture"}
    engine.scaler, engine.predict_fn = fixture.scaler, callback
    engine.backend_errors = (tf.errors.OpError,)
    return engine


@pytest.mark.parametrize("error_name", ["InternalError", "ResourceExhaustedError", "InvalidArgumentError"])
def test_tensorflow_error_holds_alarm_recovers_and_never_reuses_failed_score(error_name):
    import tensorflow as tf
    calls = [0]
    def predict(tensor):
        calls[0] += 1
        if calls[0] == 2:
            raise getattr(tf.errors, error_name)(None, None, "injected operation failure")
        return tf.constant([[.9 if calls[0] == 1 else .1]], dtype=tf.float32)
    pipeline = RealtimePipeline(keras_adapter(predict), settings())
    for t in (0., .1, .2): first = pipeline.feed(observation(t, .9))[0]
    assert first["available"] and first["decision"]["alarm_active"]
    pipeline.feed(observation(.3, .9))
    failed = pipeline.feed(observation(.4, .9))[0]
    assert not failed["available"] and failed["prediction"] is None
    assert failed["decision"]["status"] == "UNAVAILABLE" and failed["decision"]["alarm_active"]
    assert failed["decision"]["reason"].startswith("INFERENCE_ERROR:" + error_name)
    waiting = pipeline.feed(observation(.5, .9))[0]
    assert not waiting["available"] and calls[0] == 2
    recovered = pipeline.feed(observation(.6, .9))[0]
    assert recovered["available"] and not recovered["decision"]["alarm_active"] and calls[0] == 3


def test_unexpected_backend_programming_error_is_not_swallowed():
    def fail(tensor): raise KeyError("programming error")
    engine = keras_adapter(fail)
    with pytest.raises(KeyError, match="programming error"):
        engine.predict(np.zeros(engine.shape, dtype=np.float32))


@pytest.mark.parametrize("status", [
    {"record_type": "STATUS", "input_status": "INPUT_REJECTED", "reason": "duplicate"},
    {"record_type": "STATUS", "input_status": "INPUT_TIMEOUT", "available": False,
     "ground_truth": "UNLABELED", "device_id": "one", "session_id": "same",
     "prediction": None, "decision": {"alarm_active": True}},
])
def test_status_does_not_change_any_measurement_metric_or_end_risk_interval(status):
    pipeline = RealtimePipeline(FakeEngine(), settings())
    rows = []
    for t in (0., .1, .2, .3, .4):
        rows.extend(pipeline.feed({**observation(t, .9), "ground_truth": "risk"}))
    expected = timeline_metrics(rows, threshold=.5, period_seconds=.1)
    mixed = [status, *rows[:3], status, *rows[3:], status]
    assert timeline_metrics(mixed, threshold=.5, period_seconds=.1) == expected
    accumulator = StreamMetrics(.5, .1)
    for row in mixed: accumulator.consume(row)
    assert accumulator.finish() == {k: v for k, v in expected.items() if k != "schema_version"}


def test_missing_fields_in_a_sensor_record_still_raise():
    with pytest.raises(KeyError): StreamMetrics(.5, .1).consume({"record_type": "SAMPLE"})


def load_events(directory):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))]


def test_all_off_grid_and_dense_observations_including_eof_tail_are_saved(tmp_path):
    times = (.05, .11, .12, .13, .21, .22, .23, .31, .32, .33, .35, .45, .55)
    inputs = [{**observation(t, .9), "receive_index": i} for i, t in enumerate(times)]
    directory = tmp_path / "events"
    recorder = EventRecorder(directory, pre_seconds=.3, post_seconds=1., period_seconds=.1)
    pipeline = RealtimePipeline(FakeEngine(), {**settings(), "pre_event_seconds": .3}, recorder)
    reference = RealtimePipeline(FakeEngine(), {**settings(), "pre_event_seconds": .3})
    rows, original = [], []
    try:
        for value in inputs:
            rows.extend(pipeline.feed(value))
            original.extend(reference.feed(value))
    finally: report = recorder.close()
    assert report["saved_events"] == 1 and report["accepted_raw_observations"] == len(inputs)
    assert not report["raw_event_dropped"] and not report["raw_history_dropped"]
    event = load_events(directory)[0]
    assert [r["raw_observation"] for r in event["raw_observations"]] == inputs
    assert not event["raw_observations_truncated"]
    assert not event["complete"] and event["completion_reason"] == "STREAM_END"
    assert event["raw_observations"][-1]["raw_observation"]["receive_index"] == len(inputs) - 1
    assert all(pd.Timestamp(r["raw_observation"]["timestamp"]).value <= r["timestamp_ns"] for r in rows)
    assert any(pd.Timestamp(r["raw_observation"]["timestamp"]).value < r["timestamp_ns"] for r in rows)
    keys = ("timestamp_ns", "processed_values", "available", "decision", "prediction")
    assert [{k: r[k] for k in keys} for r in rows] == [{k: r[k] for k in keys} for r in original]


def test_raw_capture_is_a_snapshot_and_rejected_input_is_not_captured(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=.3, post_seconds=1., period_seconds=.1)
    pipeline = RealtimePipeline(FakeEngine(), settings(), recorder)
    first = {**observation(.05, .9), "metadata": {"original": True}}
    try:
        pipeline.feed(first)
        first["metadata"]["original"] = False
        with pytest.raises(ValueError, match="Duplicate"):
            pipeline.feed(observation(.05, .1))
        for t in (.15, .25, .35): pipeline.feed(observation(t, .9))
    finally: report = recorder.close()
    assert report["accepted_raw_observations"] == 4
    raw = load_events(tmp_path / "events")[0]["raw_observations"]
    assert raw[0]["raw_observation"]["metadata"] == {"original": True}


def test_session_reset_separates_raw_capture(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=.3, post_seconds=1., period_seconds=.1)
    pipeline = RealtimePipeline(FakeEngine(), settings(), recorder)
    try:
        for t in (.05, .15, .25, .35): pipeline.feed(observation(t, .9))
        pipeline.feed(observation(.4, .9, session="new"))
        assert len(recorder.raw_history) == 1
        assert recorder.raw_history[0]["raw_observation"]["session_id"] == "new"
    finally: recorder.close()
    event = load_events(tmp_path / "events")[0]
    assert event["completion_reason"] == "ACQUISITION_RESET"
    assert len(event["raw_observations"]) == 4
    assert all(r["raw_observation"]["session_id"] == "same" for r in event["raw_observations"])


@pytest.mark.parametrize("history_capacity,event_capacity", [(2, 4096), (1024, 2)])
def test_raw_capture_limits_report_loss_and_keep_fixed_capacity(tmp_path, history_capacity, event_capacity):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=1., post_seconds=1., period_seconds=.1,
                             raw_history_capacity=history_capacity, max_raw_observations_per_event=event_capacity)
    pipeline = RealtimePipeline(FakeEngine(), settings(), recorder)
    try:
        for t in (.05, .15, .25, .35, .45, .55):
            pipeline.feed(observation(t, .9))
            assert len(recorder.raw_history) <= history_capacity
            assert all(len(e["raw_observations"]) <= event_capacity for e in recorder.active)
    finally: report = recorder.close()
    event = load_events(tmp_path / "events")[0]
    assert event["raw_observations_truncated"]
    if history_capacity == 2: assert report["raw_history_dropped"] > 0
    else: assert report["raw_event_dropped"] > 0 and event["dropped_raw_observations"] > 0


@pytest.mark.parametrize("key", ["raw_history_capacity", "max_raw_observations_per_event"])
@pytest.mark.parametrize("value", [0, -1, True])
def test_invalid_raw_capture_limits_fail_before_starting_writer(tmp_path, key, value):
    with pytest.raises(ValueError):
        EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1, **{key: value})
    assert not (tmp_path / "events").exists()


def trigger_three_events(recorder):
    engine = DecisionEngine(.7, .4)
    for t, score in enumerate((.9, .1, .9, .1, .9)):
        recorder.consume({"timestamp_ns": t * 10**9}, engine.update(t, score, available=True))


@pytest.mark.parametrize("failure", [OSError, ValueError, TypeError])
def test_mid_write_failure_leaves_no_partial_files(tmp_path, monkeypatch, failure):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1, max_saved_events=1)
    def fail(event, handle, **kwargs):
        handle.write('{"incomplete":')
        raise failure("injected partial write")
    monkeypatch.setattr(recorder_module.json, "dump", fail)
    trigger_three_events(recorder)
    report = recorder.close()
    assert report["saved_events"] == 0 and report["writer_error_count"] == 3
    assert not list((tmp_path / "events").iterdir()) and not report["storage_disabled"]


def test_cleanup_failure_disables_storage_instead_of_accumulating_files(tmp_path, monkeypatch):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1)
    calls = [0]
    def fail(event, handle, **kwargs):
        calls[0] += 1
        handle.write('{"incomplete":')
        raise OSError("injected write failure")
    original = Path.unlink
    def deny_cleanup(path, *args, **kwargs):
        if path.suffix == ".partial": raise PermissionError("cleanup unavailable")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(recorder_module.json, "dump", fail)
    monkeypatch.setattr(Path, "unlink", deny_cleanup)
    trigger_three_events(recorder)
    report = recorder.close()
    assert report["storage_disabled"] and report["cleanup_error_count"] == 1
    assert report["writer_error_count"] == 4 and calls[0] == 1
    assert len(list((tmp_path / "events").glob("*.partial"))) == 1


def test_existing_partial_file_is_preserved(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1)
    foreign = recorder.directory / "alarm-000001.partial"
    foreign.write_text("existing evidence", encoding="utf-8")
    state = DecisionEngine(.7, .4).update(0, .9, available=True)
    recorder.consume({"timestamp_ns": 0}, state)
    report = recorder.close()
    assert foreign.read_text(encoding="utf-8") == "existing evidence"
    assert report["writer_error_count"] == 1 and not report["cleanup_error_count"]


def test_success_after_mid_write_failure_respects_storage_limit(tmp_path, monkeypatch):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1, max_saved_events=1)
    original = recorder_module.json.dump
    calls = [0]
    def fail_once(event, handle, **kwargs):
        calls[0] += 1
        if calls[0] == 1:
            handle.write('{"incomplete":')
            raise OSError("transient failure")
        return original(event, handle, **kwargs)
    monkeypatch.setattr(recorder_module.json, "dump", fail_once)
    trigger_three_events(recorder)
    report = recorder.close()
    assert report["saved_events"] == 1 and report["writer_error_count"] == 2
    assert not list(recorder.directory.glob("*.partial"))
    assert len(list(recorder.directory.glob("*.json"))) == 1
    assert load_events(recorder.directory)[0]["event_id"] == "alarm-000002"


def test_replay_reports_raw_capture_overflow_as_degraded(tmp_path, monkeypatch):
    def backend(*args, **kwargs):
        engine = FakeEngine()
        engine.manifest.update(model_version="fake", synthetic_demo=True, files={"scaler.json": "fixture"})
        return engine
    monkeypatch.setattr(replay_module, "InferenceEngine", backend)
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    pd.DataFrame([observation(t, .9) for t in (.05, .15, .25, .35, .45, .55)]).to_csv(path, index=False)
    result = replay_module.replay(path, tmp_path / "bundle", {**replay_settings(), "max_raw_observations_per_event": 1}, tmp_path / "out")
    assert result["status"] == "DEGRADED" and result["recorder"]["raw_event_dropped"] > 0
    assert all(row["raw_observation"] is not None for row in iter_timeline(tmp_path / "out"))
