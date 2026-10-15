"""Configuration, input and alarm definition contracts."""

import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from src.realtime.inference import InferenceEngine
from src.training.config import load_training_config


def test_integration_training_config_inherits_base():
    config = load_training_config(Path(__file__).parents[1] / "configs/model_integration_demo.yaml")
    assert config["model"]["sequence_length"] == 64
    assert config["training"]["epochs"] == 50
    assert config["labeling"]["ground_truth_mapping"] == {"normal": 0, "risk": 1}


def test_reader_header_requires_active_sensors(tmp_path):
    from src.realtime.replay import observations
    file = tmp_path / "partial.csv"
    file.write_text("timestamp,a\n2026-01-01T00:00:00Z,1\n")
    with pytest.raises(ValueError, match="sensor column"): list(observations(file, ["a", "b"]))


def test_alarm_start_normal_is_false_even_if_later_risk():
    from src.evaluation.stream_metrics import StreamMetrics
    accumulator = StreamMetrics(.5, 1)
    for t, label in enumerate(("normal", "risk")):
        accumulator.consume({"timestamp_ns": t*10**9, "device_id": "one", "session_id": "same", "ground_truth": label,
                             "available": True, "prediction": {"risk_score": .8},
                             "decision": {"alarm_active": True, "transition": "ENTER" if t==0 else None}})
    result = accumulator.finish()
    assert result["false_alarm_episodes"] == 1 and result["unmatched_alarm_episodes"] == 0
    assert result["detected_risk_intervals"] == 1
