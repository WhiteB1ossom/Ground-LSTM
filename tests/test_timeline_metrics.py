import numpy as np
import pytest

from src.evaluation.stream_metrics import StreamMetrics
from src.realtime.decision import DecisionEngine


def trace(labels, scores, available=None):
    engine = DecisionEngine(.5, .5)
    output = []
    for t, (label, score) in enumerate(zip(labels, scores)):
        valid = available[t] if available is not None else True
        decision = engine.update(t, score if valid else None, available=valid)
        output.append({"timestamp_ns": t*10**9, "device_id": "one", "session_id": "session",
                       "ground_truth": label, "available": valid, "prediction": {"risk_score": score} if valid else None,
                       "decision": {"alarm_active": decision.alarm_active}})
    return output


def test_many_false_windows_form_one_alarm_episode():
    metrics = StreamMetrics(.5, 1.)
    for row in trace(["normal"] * 5, [.8, .8, .8, .8, .1]): metrics.consume(row)
    result = metrics.finish()
    assert result["window"]["false_positives"] == 4
    assert result["false_alarm_episodes"] == 1
    assert result["normal_alarm_fraction"] == .8
    assert result["false_alarm_per_normal_valid_hour"] == pytest.approx(720)


def test_unknown_not_normal_and_unavailability_coverage():
    metrics = StreamMetrics(.5, 1.)
    for row in trace(["UNLABELED", "normal", "risk"], [.8, .1, .8], [True, False, True]): metrics.consume(row)
    result = metrics.finish()
    assert result["window"]["samples"] == 1
    assert result["window"]["risk_false_positive_rate"] is None
    assert result["normal_valid_seconds"] == 0
    assert result["false_alarm_per_normal_valid_hour"] is None
    assert result["coverage"] == pytest.approx(2/3)
    assert result["detected_risk_intervals"] == 1


def test_separate_risk_intervals_and_delay():
    metrics = StreamMetrics(.5, .5)
    for row in trace(["risk", "risk", "normal", "risk"], [.1, .8, .1, .1]): metrics.consume(row)
    result = metrics.finish()
    assert result["risk_intervals"] == 2 and result["detected_risk_intervals"] == 1
    assert result["missed_risk_intervals"] == 1
    assert result["detection_delays_seconds"] == [1.]


def test_stats_storage_bounded_with_many_events():
    metrics = StreamMetrics(.5, 1.)
    for row in trace(["risk", "normal"] * 1200, [.8, .1] * 1200): metrics.consume(row)
    result = metrics.finish()
    assert result["detected_risk_intervals"] == 1200
    assert len(result["detection_delays_seconds"]) == 1024
