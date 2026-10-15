"""Boundary rules, advisory state, non-blocking capture and causal stream parity."""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models.baselines import ThresholdBaseline
from src.models.rules import compare, evaluate_rules, validate_rule
from src.preprocessing.scaling import FrozenScaler
from src.realtime.decision import DecisionEngine
from src.realtime.recorder import EventRecorder
from src.realtime.stream import RealtimePipeline
from src.utils.config import SensorSpec


@pytest.mark.parametrize("operator,expected", [("gt", [False, False, True]), ("ge", [False, True, True]),
                                                ("lt", [True, False, False]), ("le", [True, True, False]), ("eq", [False, True, False])])
def test_explicit_direction_and_equality(operator, expected):
    assert compare(np.array([1., 2., 3.]), {"operator": operator, "value": 2}).tolist() == expected


def test_threshold_never_infers_ge_from_metadata():
    scaler = FrozenScaler(["v__current_value"], "standard").fit(np.array([[1.], [3.]]), split="train")
    baseline = ThresholdBaseline({"sensors": [{"name": "v", "enabled": True, "threshold": 2}]}, scaler, [])
    assert baseline.rules == []
    with pytest.raises(ValueError, match="disabled"): baseline.predict(np.ones((1, 1, 1)))


def test_physical_unit_and_difference_reference():
    sensors = {"temp": {"unit": "degC"}, "ambient": {"unit": "degC"}, "current": {"unit": "A"}}
    rule = {"sensor": "temp", "unit": "degC", "operator": "gt", "value": 25, "reference_sensor": "ambient"}
    validate_rule(rule, sensors)
    assert evaluate_rules({"temp": 45., "ambient": 20.}, [rule])["condition_met"] is False
    assert evaluate_rules({"temp": 46., "ambient": 20.}, [rule])["condition_met"] is True
    assert evaluate_rules({"temp": 46.}, [rule])["condition_met"] is None
    with pytest.raises(ValueError, match="unit"): validate_rule({**rule, "unit": "A"}, sensors)
    with pytest.raises(ValueError, match="reference"): validate_rule({**rule, "reference_sensor": "current"}, sensors)


def test_three_valued_and_or():
    rules = [{"sensor": "a", "operator": "gt", "value": 1}, {"sensor": "b", "operator": "lt", "value": 2}]
    assert evaluate_rules({"a": 2.}, rules)["condition_met"] is True
    assert evaluate_rules({"a": 2.}, rules, combination="all")["condition_met"] is None
    assert evaluate_rules({"a": 0.}, rules, combination="all")["condition_met"] is False


def test_hysteresis_unknown_never_clears_alarm():
    engine = DecisionEngine(.7, .4, consecutive=2)
    assert engine.update(1, .7, available=True).alarm_active is False
    assert engine.update(2, .7, available=True).transition == "ENTER"
    unavailable = engine.update(3, None, available=False)
    assert unavailable.status == "UNAVAILABLE" and unavailable.alarm_active
    assert engine.update(4, .4, available=True).alarm_active
    assert engine.update(5, .399, available=True).transition == "EXIT"
    with pytest.raises(ValueError, match="increase"): engine.update(5, .8, available=True)


def test_interrupted_consecutive_count():
    engine = DecisionEngine(.7, .4, consecutive=2)
    engine.update(1, .8, available=True)
    engine.update(2, None, available=False)
    assert not engine.update(3, .8, available=True).alarm_active


@pytest.mark.parametrize("on,off,count", [(.3, .4, 1), (float("nan"), .1, 1), (.8, .4, True), (.8, .4, 0)])
def test_invalid_decision_settings(on, off, count):
    with pytest.raises(ValueError): DecisionEngine(on, off, consecutive=count)


def test_pre_post_recording_and_incomplete_eof(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=2, post_seconds=2, period_seconds=1)
    decision = DecisionEngine(.7, .4)
    for t, score in enumerate((.1, .1, .8, .8, .1, .8)):
        state = decision.update(t, score, available=True)
        recorder.consume({"timestamp_ns": t * 10**9, "raw_observation": {"v": str(t)}, "processed_values": [float(t)]}, state)
    summary = recorder.close()
    assert summary["saved_events"] == 2 and not summary["writer_errors"]
    events = [json.loads(p.read_text()) for p in sorted((tmp_path / "events").glob("*.json"))]
    assert [r["timestamp_ns"] for r in events[0]["samples"]] == [0, 10**9, 2*10**9, 3*10**9, 4*10**9]
    assert events[0]["complete"] and events[0]["pre_history_complete"]
    assert not events[1]["complete"] and events[1]["completion_reason"] == "STREAM_END"
    assert events[0]["ground_truth"] == "UNLABELED"


def test_writer_failure_reported_without_raising_in_ingestion(tmp_path, monkeypatch):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=1)
    original = Path.open
    def denied(path, *args, **kwargs):
        if path.suffix == ".partial": raise PermissionError("software disk failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", denied)
    state = DecisionEngine(.7, .4).update(1, .9, available=True)
    recorder.consume({"timestamp_ns": 1}, state)
    report = recorder.close()
    assert report["saved_events"] == 0 and report["writer_error_count"] == 1


class FakeEngine:
    shape, threshold = (1, 3, 3), .5
    def __init__(self):
        sensor = SensorSpec("v", "V", None, None, .1, None, "drop_window", .3, True, "fast")
        p = {"features": ["current_value"], "ground_voltage_difference": False, "include_missing_indicators": True,
             "include_age_features": True, "stale_action": "missing_indicator", "alignment_period_seconds": .1,
             "windows": {"stride": 2}}
        self.manifest = {"configuration": {"pipeline": p, "timestamp": {"naive_policy": "reject", "output_timezone": "UTC"},
                           "input": {"source": "monitoring", "acquisition_kind": "synthetic"},
                           "quality": {"healthy_sensor_status": ["OK"], "healthy_communication_status": ["OK"]}},
                         "sensors": [asdict(sensor)]}
        self.scaler = FrozenScaler(["v__current_value", "v__missing", "v__age_seconds"], "standard").fit(np.array([[0., 0, 0], [1., 0, 0]]), split="train")
        self.calls = 0
    def predict(self, tensor):
        self.calls += 1
        return {"risk_score": .9 if tensor[0, -1, 0] > 0 else .1, "inference_ms": 0.1}


def settings():
    return {"mode": "advisory", "hardware_actuation_enabled": False, "pre_event_seconds": .2,
            "minimum_consecutive_detections": 1, "off_threshold_ratio": .8, "rules": []}


def observation(t, value, *, event="a", session="same"):
    return {"timestamp": (pd.Timestamp("2026-01-01T00:00:00Z") + pd.Timedelta(seconds=t)).isoformat(),
            "v": value, "event_id": event, "session_id": session, "device_id": "one", "ground_truth": "normal"}


def test_event_id_does_not_reset_live_stream_and_invalid_tensor_not_reused():
    engine = FakeEngine()
    pipeline = RealtimePipeline(engine, settings())
    pipeline.feed(observation(0, .9))
    pipeline.feed(observation(.1, .9, event="changed"))
    first = pipeline.feed(observation(.2, .9))[0]
    assert first["decision"]["alarm_active"] and engine.calls == 1
    failed = pipeline.feed(observation(.3, "NaN"))[0]
    assert not failed["available"] and failed["decision"]["status"] == "UNAVAILABLE"
    assert failed["decision"]["alarm_active"] and engine.calls == 1
    for t in (.4, .5): pipeline.feed(observation(t, 0.))
    recovered = pipeline.feed(observation(.6, 0.))[0]
    assert recovered["available"] and not recovered["decision"]["alarm_active"]


def test_explicit_session_reset_and_mixed_device_rejection():
    pipeline = RealtimePipeline(FakeEngine(), settings())
    for t in (0., .1, .2): pipeline.feed(observation(t, .9))
    restarted = pipeline.feed(observation(.3, .9, session="restart"))[0]
    assert restarted["input_status"] == "WARMING_UP"
    assert restarted["decision"]["alarm_active"]
    with pytest.raises(ValueError, match="mixed streams"): pipeline.feed({**observation(.4, .9), "device_id": "two"})


@pytest.mark.parametrize("speed", ["1", "2", "10", "max"])
def test_replay_speeds_preserve_virtual_predictions(tmp_path, monkeypatch, speed):
    from src.realtime import replay as replay_module
    def fake_engine(*args, **kwargs):
        engine = FakeEngine()
        engine.manifest.update(model_version="fake", synthetic_demo=True, files={"scaler.json": "fixture"})
        return engine
    monkeypatch.setattr(replay_module, "InferenceEngine", fake_engine)
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    pd.DataFrame([observation(t, .9) for t in (0., .1, .2, .3, .4)]).to_csv(path, index=False)
    now = [0.]
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
    result = replay_module.replay(path, tmp_path / "bundle", settings(), tmp_path / "out", speed=speed,
                                  clock=lambda: now[0], sleep=sleep, write_events=False)
    rows = [json.loads(line) for line in (tmp_path / "out/timeline.jsonl").read_text().splitlines()]
    assert [r["input_status"] for r in rows] == ["WARMING_UP", "WARMING_UP", "READY", "WAITING_FOR_STRIDE", "READY"]
    assert [r["prediction"]["risk_score"] for r in rows if r["prediction"]] == [.9, .9]
    assert result["evaluation"]["window"]["false_positives"] == 2
    assert result["status"] == "SUCCESS"
    assert sum(sleeps) == pytest.approx(0. if speed == "max" else .4 / float(speed))
