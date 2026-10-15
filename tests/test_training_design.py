"""Behavioral checks for adaptive training, exact threshold search and context."""

import numpy as np
import pytest

from src.evaluation.metrics import classification_metrics, event_group_metrics, select_threshold
from src.training.data import input_context_audit
from src.training.train import validation_recommendation


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_exact_search_matches_bruteforce_with_tied_scores(dtype):
    y = np.array([0, 1, 0, 1, 1, 0])
    p = np.array([.15, .25, .25, .65, .8, .9], dtype=dtype)
    settings = {"threshold_search": "validation_scores", "threshold_objective": "max_f1", "minimum_recall": .9}
    result = select_threshold(y, p, settings, split="validation")
    for row in result["candidates"]:
        full = classification_metrics(y, p, threshold=row["threshold"], class_count=2)
        for key in ("precision", "recall", "f1", "false_negatives", "false_positives"):
            assert row[key] == pytest.approx(full[key])
    assert result["selected_threshold"] == .25


def test_search_can_choose_below_old_grid():
    result = select_threshold(np.array([0, 1, 1]), np.array([.01, .02, .03]),
                              {"threshold_search": "validation_scores", "threshold_objective": "recall_then_f1", "minimum_recall": 1}, split="validation")
    assert result["selected_threshold"] == .02
    assert result["recall_target_met"]


def test_context_requires_age_and_sufficient_fast_duration():
    manifest = {"sensors": [{"name": "humidity", "enabled": True, "group": "slow_context", "nominal_sampling_period": 3600}]}
    artifact = {"sequence_length": 16, "alignment_period_seconds": .1, "feature_order": ["humidity__current_value"]}
    config = {"input_contract": {"minimum_context_seconds": 6.4, "require_slow_sensor_age": True}}
    with pytest.raises(ValueError, match="too short"): input_context_audit(manifest, artifact, config)
    artifact["sequence_length"] = 64
    with pytest.raises(ValueError, match="age features"): input_context_audit(manifest, artifact, config)
    artifact["feature_order"].append("humidity__age_seconds")
    audit = input_context_audit(manifest, artifact, config)
    assert audit["nominal_window_seconds"] == 6.4
    assert audit["endpoint_span_seconds"] == pytest.approx(6.3)
    assert audit["slow_sensors"][0]["role"] == "current_context_not_long_term_trend"


def test_event_summary_does_not_count_missing_predictions_as_misses():
    metadata = {"event_id": np.array(["eventA", "eventA", "eventB", "normal"]),
                "device_id": np.repeat("device", 4), "y": np.array([1, 1, 1, 0])}
    result = event_group_metrics(metadata, np.array([.7, .1, np.nan, .9]), threshold=.5, class_count=2)
    assert result["risk_groups"] == 2
    assert result["detected_in_positive_windows"] == 1
    assert result["missed_risk_groups"] == 0
    assert result["incompletely_covered_risk_groups"] == 1
    assert result["normal_groups_with_false_alarm"] == 1


def test_model_recommendation_ignores_test_result():
    models = {name: {"status": "evaluated", "validation": {"f1": f1, "recall": 1.},
                     "test": {"f1": test_f1}, "coverage": {"validation": 1.}}
              for name, f1, test_f1 in [("logistic", .9, .1), ("lstm", .8, 1.)]}
    result = validation_recommendation(models, {"evaluation": {"minimum_recall": .9}}, 2)
    assert result["model"] == "logistic"
    assert result["selection_split"] == "validation"
    assert result["deployment_approved"] is False
