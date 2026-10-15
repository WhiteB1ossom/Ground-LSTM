"""Validated training choices, independent of unconfirmed physical thresholds."""

import math
from pathlib import Path

from src.utils.config import read_inherited_yaml


def load_training_config(path: Path) -> dict:
    c = read_inherited_yaml(path)
    def integer(value, name, zero=False):
        if type(value) is not int or (value < 0 if zero else value <= 0): raise ValueError(f"Invalid {name}")
    integer(c["seed"], "seed", True)
    for key in ("hidden_units", "num_layers"): integer(c["model"][key], key)
    if c["model"]["type"] != "lstm" or c["model"]["bidirectional"] is not False: raise ValueError("Only forward LSTM is supported")
    drop = c["model"]["dropout"]
    if isinstance(drop, bool) or not isinstance(drop, (int, float)) or not 0 <= drop < 1: raise ValueError("Invalid dropout")
    if c["model"]["sequence_length"] is not None: integer(c["model"]["sequence_length"], "sequence_length")
    for key in ("batch_size", "epochs"): integer(c["training"][key], key)
    integer(c["training"]["early_stopping_patience"], "early_stopping_patience", True)
    training = c["training"]
    training.setdefault("early_stopping_min_delta", 0.0)
    delta = training["early_stopping_min_delta"]
    if isinstance(delta, bool) or not isinstance(delta, (int, float)) or not math.isfinite(delta) or delta < 0: raise ValueError("Invalid early_stopping_min_delta")
    schedule = training.setdefault("lr_schedule", {"enabled": False})
    if not isinstance(schedule, dict) or type(schedule.get("enabled")) is not bool: raise ValueError("Invalid lr_schedule")
    if schedule["enabled"]:
        integer(schedule["patience"], "lr_schedule.patience")
        if schedule["patience"] >= training["early_stopping_patience"]: raise ValueError("Learning rate must be reduced before early stopping")
        for key in ("factor", "min_learning_rate"):
            value = schedule[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0: raise ValueError(f"Invalid lr_schedule.{key}")
        if schedule["factor"] >= 1 or schedule["min_learning_rate"] > training["learning_rate"]: raise ValueError("Invalid learning rate reduction bounds")
    lr = c["training"]["learning_rate"]
    if isinstance(lr, bool) or not isinstance(lr, (int, float)) or not math.isfinite(lr) or lr <= 0: raise ValueError("Invalid learning_rate")
    for key in ("deterministic", "allow_synthetic_demo"):
        if type(c["training"][key]) is not bool: raise ValueError(f"Invalid {key}")
    if c["training"]["class_weight"] not in {None, "balanced"}: raise ValueError("class_weight must be null or balanced")
    integer(c["baseline"]["logistic_max_iter"], "logistic_max_iter")
    candidates = c["evaluation"]["validation_threshold_candidates"]
    if not candidates or any(isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 < t < 1 for t in candidates): raise ValueError("Invalid threshold candidates")
    if c["evaluation"].setdefault("threshold_search", "configured_candidates") not in {"configured_candidates", "validation_scores"}: raise ValueError("Invalid threshold_search")
    contract = c.setdefault("input_contract", {"minimum_context_seconds": None, "require_slow_sensor_age": False})
    minimum = contract.get("minimum_context_seconds")
    if minimum is not None and (isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or minimum <= 0): raise ValueError("Invalid minimum_context_seconds")
    if type(contract.get("require_slow_sensor_age", False)) is not bool: raise ValueError("Invalid require_slow_sensor_age")
    if c["evaluation"]["threshold_objective"] not in {"recall_then_f1", "max_f1"}: raise ValueError("Invalid threshold objective")
    recall = c["evaluation"]["minimum_recall"]
    if isinstance(recall, bool) or not isinstance(recall, (int, float)) or not 0 <= recall <= 1: raise ValueError("Invalid recall target")
    integer(c["evaluation"]["latency_repetitions"], "latency_repetitions")
    if c["labeling"]["mode"] not in {"binary", "multiclass"} or c["labeling"]["unlabeled_action"] != "stop_training": raise ValueError("Invalid label policy")
    mapping = c["labeling"]["ground_truth_mapping"]
    if mapping is not None:
        if not isinstance(mapping, dict) or not mapping or any(type(v) is not int or v < 0 for v in mapping.values()): raise ValueError("Invalid label mapping")
        classes = sorted(set(mapping.values()))
        if classes != list(range(len(classes))) or len(classes) < 2: raise ValueError("Labels require contiguous classes starting at zero")
        if c["labeling"]["mode"] == "binary" and classes != [0, 1]: raise ValueError("Binary labeling requires exactly two classes")
    if type(c["labeling"]["multiclass_semantics_confirmed"]) is not bool: raise ValueError("Invalid multiclass confirmation")
    return c
