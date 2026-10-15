"""Load prepared, labeled splits and audit the feature/provenance contract."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from src.preprocessing.scaling import FrozenScaler


@dataclass
class TrainingDataset:
    directory: Path
    manifest: dict
    splits: dict
    hashes: dict
    class_count: int
    synthetic: bool


def file_hash(path: Path) -> str:
    with path.open("rb") as handle: return hashlib.file_digest(handle, "sha256").hexdigest()


def input_context_audit(manifest: dict, artifact: dict, config: dict) -> dict:
    period = artifact.get("alignment_period_seconds")
    length = artifact["sequence_length"]
    seconds = length * period if period is not None else None
    contract = config.get("input_contract", {})
    minimum = contract.get("minimum_context_seconds")
    if minimum is not None and (seconds is None or seconds + 1e-9 < minimum):
        raise ValueError("Prepared input context is too short; rebuild dataset for minimum_context_seconds")
    slow = [s for s in manifest.get("sensors", []) if s.get("enabled") and s.get("group") == "slow_context"]
    if contract.get("require_slow_sensor_age", False):
        missing = [s["name"] for s in slow if s["name"] + "__age_seconds" not in artifact["feature_order"]]
        if missing: raise ValueError(f"Slow sensors require observation age features: {missing}")
    return {"alignment_period_seconds": period, "nominal_window_seconds": seconds,
            "endpoint_span_seconds": (length - 1) * period if period is not None else None,
            "slow_sensors": [{"sensor": s["name"], "period_seconds": s["nominal_sampling_period"],
                              "role": "current_context_not_long_term_trend" if seconds is not None and s["nominal_sampling_period"] is not None and s["nominal_sampling_period"] > seconds else "within_window_observations",
                              "has_age_feature": s["name"] + "__age_seconds" in artifact["feature_order"]} for s in slow],
            "note": "A short fast-signal window does not establish hourly trend learning."}


def load_dataset(directory: Path, config: dict, *, synthetic_demo: bool = False) -> TrainingDataset:
    directory = directory.resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("scaler_fit_split") != "train": raise ValueError("Invalid dataset/scaler contract")
    synthetic = manifest["configuration"]["input"]["acquisition_kind"] == "synthetic"
    if synthetic and not (synthetic_demo and config["training"]["allow_synthetic_demo"]):
        raise ValueError("Synthetic data requires --synthetic-demo and allow_synthetic_demo; not a real performance evaluation")
    if synthetic_demo and not synthetic: raise ValueError("--synthetic-demo cannot override real-data validation")
    if manifest.get("label_status") != "LABELED" or (not synthetic and manifest.get("supervised_training_ready") is not True):
        raise ValueError("UNLABELED/partially labeled data cannot be used for supervised training")
    dataset_labels = manifest["configuration"]["pipeline"]["labeling"]
    expected_mapping = config["labeling"]["ground_truth_mapping"]
    if expected_mapping is None or {str(k): v for k, v in expected_mapping.items()} != {str(k): v for k, v in dataset_labels["mapping"].items()} or config["labeling"]["mode"] != dataset_labels["mode"]:
        raise ValueError("Model labeling mode/mapping must match prepared dataset")
    classes = sorted(set(expected_mapping.values()))
    if classes != list(range(len(classes))) or len(classes) < 2: raise ValueError("At least two contiguous classes are required")
    if config["labeling"]["mode"] == "multiclass" and not config["labeling"]["multiclass_semantics_confirmed"]:
        raise ValueError("Multiclass semantics must be explicitly confirmed")
    scaler = FrozenScaler.load(directory / "scaler.json")
    if scaler.order != manifest["feature_order"]: raise ValueError("Scaler feature order mismatch")
    artifact = json.loads((directory / "feature_order.json").read_text(encoding="utf-8"))
    if artifact["feature_order"] != scaler.order: raise ValueError("Feature artifact order mismatch")
    sequence = artifact["sequence_length"]
    input_context_audit(manifest, artifact, config)
    if config["model"]["sequence_length"] not in {None, sequence}: raise ValueError("Sequence length must match dataset")
    splits, hashes, seen_events, seen_samples = {}, {}, {}, set()
    hashes = {name: file_hash(directory / name) for name in ("manifest.json", "scaler.json", "feature_order.json")}
    for name in ("train", "validation", "test"):
        path = directory / f"{name}.npz"
        with np.load(path, allow_pickle=False) as data: values = {key: data[key] for key in data.files}
        X, y = values["X"], values["y"]
        if X.ndim != 3 or X.shape[1:] != (sequence, len(scaler.order)) or len(X) != len(y) or y.ndim != 1 or not len(y) or not np.isfinite(X).all():
            raise ValueError(f"{name}: invalid tensor shape/nonfinite input")
        if y.dtype.kind not in "iu" or ((y < 0) | (y >= len(classes))).any(): raise ValueError(f"{name}: invalid/UNLABELED targets")
        if values["feature_order"].tolist() != scaler.order: raise ValueError(f"{name}: feature order mismatch")
        kind = manifest["configuration"]["input"]["acquisition_kind"]
        source = manifest["configuration"]["input"]["source"]
        if set(values["acquisition_kind"].tolist()) != {kind} or set(values["source"].tolist()) != {source}:
            raise ValueError(f"{name}: provenance mismatch")
        for key in ("event_id", "device_id", "start_timestamp", "end_timestamp", "target_timestamp"):
            if len(values[key]) != len(y): raise ValueError(f"{name}: metadata length mismatch")
        for event in set(values["event_id"].tolist()) - {""}:
            if event in seen_events: raise ValueError(f"Data leakage: event {event} crosses {seen_events[event]} and {name}")
            seen_events[event] = name
        keys = set(zip(values["device_id"].tolist(), values["start_timestamp"].tolist(), values["end_timestamp"].tolist()))
        if seen_samples.intersection(keys): raise ValueError("Data leakage: same window crosses splits")
        seen_samples.update(keys)
        splits[name], hashes[path.name] = values, file_hash(path)
    if set(splits["train"]["y"].tolist()) != set(classes): raise ValueError("Train must contain all configured classes")
    if config["labeling"]["mode"] == "binary" and set(splits["validation"]["y"].tolist()) != {0, 1}:
        raise ValueError("Validation needs both binary classes to select a meaningful threshold")
    return TrainingDataset(directory, manifest, splits, hashes, len(classes), synthetic)
