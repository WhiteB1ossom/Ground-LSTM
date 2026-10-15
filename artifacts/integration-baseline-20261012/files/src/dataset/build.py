"""Build auditable, leakage-safe tensors from immutable sensor observations."""

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import logging
from pathlib import Path
import shutil
import tempfile

import numpy as np
import pandas as pd

from src.data.loader import discover_inputs, load_raw
from src.data.quality import inspect_quality
from src.data.report import save_report
from src.data.schema import parse_timestamp
from src.dataset.events import extract_events
from src.dataset.labeling import map_labels
from src.dataset.split import NAMES, split_raw
from src.dataset.windows import build_windows
from src.features.transform import FeatureTransform
from src.preprocessing.alignment import align_block
from src.preprocessing.scaling import FrozenScaler
from src.preprocessing.settings import validate_pipeline
from src.utils.config import PipelineConfig, load_config

LOGGER = logging.getLogger(__name__)


def _read_inputs(config: PipelineConfig, paths: list[Path]) -> tuple[pd.DataFrame, list[dict]]:
    frames, origins = [], []
    source, kind = config.settings["input"]["source"], config.settings["input"]["acquisition_kind"]
    offset = 0
    for path in paths:
        raw = load_raw(path, source=source)
        report = inspect_quality(raw, config)
        save_report(report, config.resolve(config.settings["report"]["directory"]))
        fatal = {"TIMESTAMP_PARSE_FAILED", "TIMESTAMP_TIMEZONE_MISSING", "TIMESTAMP_DUPLICATE", "TIMESTAMP_REVERSED", "SENSOR_COLUMN_MISSING", "EMPTY_DATASET"}
        if fatal.intersection(report["summary"]["reason_counts"]):
            raise ValueError(f"{path.name}: structural/time errors; inspect quality report before building")
        frame = raw.frame.copy(deep=True)
        if "acquisition_kind" in frame:
            declared = set(frame["acquisition_kind"].dropna().astype(str)) - {""}
            if declared - {kind}: raise ValueError("Acquisition provenance conflicts with configuration")
        synthetic_flag = frame.get("is_synthetic", pd.Series(False, index=frame.index)).astype(str).str.lower().isin(["true", "1"])
        if synthetic_flag.any() and kind != "synthetic": raise ValueError("Synthetic data cannot be treated as field/lab measurement")
        frame["timestamp"] = [parse_timestamp(v, config.settings["timestamp"])[0] for v in frame["timestamp"]]
        frame["device_id"] = frame.get("device_id", pd.Series("", index=frame.index)).fillna("").astype(str)
        frame["event_id"] = frame.get("event_id", pd.Series("", index=frame.index)).fillna("").astype(str)
        frame["source"], frame["acquisition_kind"] = source, kind
        frame["raw_row"] = np.arange(offset, offset + len(frame))
        frame["raw_file"], frame["raw_file_row"] = str(raw.path), np.arange(len(frame))
        offset += len(frame)
        frames.append(frame)
        origins.append({"path": str(raw.path), "sha256": raw.sha256, "rows": len(frame), "source": source, "acquisition_kind": kind})
    frame = pd.concat(frames, ignore_index=True)
    if frame.duplicated(["device_id", "timestamp"]).any():
        raise ValueError("Overlapping/duplicate observations across files; choose one representation, not both CSV and Parquet copies")
    return frame.sort_values(["device_id", "timestamp"], kind="stable").reset_index(drop=True), origins


def _blocks(frame: pd.DataFrame):
    for device, stream in frame.groupby("device_id", sort=False):
        # Keep contiguous event segments separate even when a group ID recurs.
        boundaries = stream["event_id"].ne(stream["event_id"].shift()).cumsum()
        for segment, block in stream.groupby(boundaries, sort=False):
            yield str(device), int(segment), block.reset_index(drop=True)


def build_dataset(config: PipelineConfig, paths: list[Path] | None = None, *, output: Path | None = None) -> Path:
    settings = validate_pipeline(config)
    paths = discover_inputs(config) if paths is None else [Path(p).resolve() for p in paths]
    if not paths: raise ValueError("No input CSV/Parquet files found")
    # Reject report/output placement under raw even when an override is supplied.
    raw_dir = config.resolve(config.settings["input"]["directory"])
    report_dir = config.resolve(config.settings["report"]["directory"])
    if report_dir == raw_dir or raw_dir in report_dir.parents: raise ValueError("Reports must be outside raw data")
    frame, origins = _read_inputs(config, paths)
    implementation = hashlib.sha256()
    source_root = Path(__file__).resolve().parents[1]
    modules = sorted(p for package in ("dataset", "preprocessing", "features", "data", "utils") for p in (source_root / package).glob("*.py"))
    for module in modules:
        implementation.update(str(module.relative_to(source_root)).encode())
        implementation.update(module.read_bytes())
    fingerprint = {"inputs": origins, "settings": config.settings, "sensors": [asdict(s) for s in config.sensors], "pipeline_version": 2,
                   "implementation_sha256": implementation.hexdigest()}
    run_id = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()[:16]
    destination = output.resolve() if output else config.resolve(settings["output_directory"]) / run_id
    forbidden = [raw_dir, *[p.parent for p in paths]]
    if any(destination == parent or parent in destination.parents for parent in forbidden):
        raise ValueError("Processed outputs must be outside all raw input directories")
    if destination.exists(): raise FileExistsError(f"Output already exists: {destination}; existing artifacts are preserved")
    parts, split_report = split_raw(frame, settings["split"])
    transformed = {name: [] for name in NAMES}
    order = FeatureTransform(config.sensors, settings).order
    counters = {}
    for split, part in parts.items():
        for device, segment, block in _blocks(part):
            period = settings["alignment_period_seconds"]
            if (block["timestamp"].iloc[-1] - block["timestamp"].iloc[0]).total_seconds() / period > 1_000_000:
                raise ValueError("Block exceeds one million aligned steps; use explicit acquisition segments/chunk adapter")
            metadata, samples = align_block(block, config.sensors, settings, config.settings["quality"])
            if not samples: continue
            transform = FeatureTransform(config.sensors, settings)
            features = np.stack([transform.transform(sample) for sample in samples])
            valid = np.array([s.valid for s in samples])
            if settings["stale_action"] == "drop_window": valid &= np.isfinite(features).all(axis=1)
            labels, label_status = map_labels(metadata["ground_truth"], settings["labeling"])
            metadata["segment_id"] = f"{split}:{device}:{segment}"
            transformed[split].append({"metadata": metadata, "features": features, "valid": valid, "labels": labels, "label_status": label_status})
        counters[split] = sum(len(b["features"]) for b in transformed[split])
    training = [b["features"][b["valid"]] for b in transformed["train"] if b["valid"].any()]
    if not training: raise ValueError("No valid train rows remain; review missing/staleness/drop-window policies")
    scaler = FrozenScaler(order, settings["scaler"]).fit(np.concatenate(training), split="train")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".dataset-build-", dir=destination.parent))
    try:
        scaler.save(staging / "scaler.json")
        (staging / "feature_order.json").write_text(json.dumps({"schema_version": 1, "feature_order": order, "sequence_length": settings["windows"]["sequence_length"], "alignment_period_seconds": settings["alignment_period_seconds"]}, indent=2) + "\n", encoding="utf-8")
        window_counts, unlabeled_counts, event_files = {}, {}, {}
        for split, blocks in transformed.items():
            outputs, aligned_frames = [], []
            for block in blocks:
                scaled = scaler.transform(block["features"], order)
                windows = build_windows(scaled, block["metadata"], block["labels"], block["valid"], settings["windows"], period_seconds=settings["alignment_period_seconds"])
                n = len(windows["y"])
                windows["segment_id"] = np.repeat(block["metadata"]["segment_id"].iloc[0], n).astype(str)
                windows["event_id"] = np.repeat(str(block["metadata"]["event_id"].iloc[0]), n).astype(str)
                windows["device_id"] = np.repeat(str(block["metadata"]["device_id"].iloc[0]), n).astype(str)
                outputs.append(windows)
                aligned = block["metadata"].copy()
                for index, name in enumerate(order): aligned[name] = block["features"][:, index]
                aligned["window_row_valid"] = block["valid"]
                aligned_frames.append(aligned)
            if not outputs or not sum(len(o["y"]) for o in outputs):
                raise ValueError(f"{split} has no usable windows; review sequence length, data duration or missing policy")
            joined = {key: np.concatenate([o[key] for o in outputs]) for key in outputs[0]}
            joined["feature_order"] = np.array(order, dtype=str)
            joined["source"] = np.repeat(config.settings["input"]["source"], len(joined["y"])).astype(str)
            joined["acquisition_kind"] = np.repeat(config.settings["input"]["acquisition_kind"], len(joined["y"])).astype(str)
            np.savez_compressed(staging / f"{split}.npz", **joined)
            pd.concat(aligned_frames, ignore_index=True).to_parquet(staging / f"{split}.aligned.parquet", index=False)
            index, segments = extract_events(parts[split], settings["events"], config.settings["timestamp"])
            index.to_json(staging / f"{split}.events.json", orient="records", indent=2, force_ascii=False)
            # An event key is untrusted metadata, never a filesystem path.
            event_dir = staging / "events" / split
            event_dir.mkdir(parents=True, exist_ok=True)
            event_files[split] = {}
            for event_id, segment in segments.items():
                filename = hashlib.sha256(event_id.encode()).hexdigest()[:16] + ".parquet"
                segment.to_parquet(event_dir / filename, index=False)
                event_files[split][event_id] = f"events/{split}/{filename}"
            window_counts[split], unlabeled_counts[split] = len(joined["y"]), int((joined["y"] < 0).sum())
        supervised_ready = all(v == 0 for v in unlabeled_counts.values()) and config.settings["input"]["acquisition_kind"] != "synthetic"
        manifest = {"schema_version": 1, "phase": 2, "dataset_version": run_id, "inputs": origins,
                    "implementation_sha256": fingerprint["implementation_sha256"],
                    "configuration": fingerprint["settings"], "sensors": fingerprint["sensors"],
                    "feature_order": order, "split": split_report, "aligned_rows": counters,
                    "windows": window_counts, "unlabeled_windows": unlabeled_counts,
                    "supervised_training_ready": supervised_ready,
                    "label_status": "UNLABELED" if all(unlabeled_counts[n] == window_counts[n] for n in NAMES) else "PARTIALLY_LABELED" if any(unlabeled_counts.values()) else "LABELED",
                    "event_files": event_files, "scaler_fit_split": "train",
                    "notes": ["Post-event exports are offline verification data, not prediction inputs.",
                              "Missing features use medians fitted on valid train rows only; missing indicators are preserved.",
                              "No model is trained or physical detection performance claimed."]}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        scaler_root = config.resolve(settings["scaler_directory"])
        if any(scaler_root == p or p in scaler_root.parents for p in forbidden): raise ValueError("Scaler output must be outside raw input")
        scaler_root.mkdir(parents=True, exist_ok=True)
        scaler_path = scaler_root / f"{run_id}.json"
        if scaler_path.exists():
            if scaler_path.read_bytes() != (staging / "scaler.json").read_bytes(): raise ValueError("Existing scaler artifact conflicts with dataset")
        else:
            with scaler_path.open("xb") as handle: handle.write((staging / "scaler.json").read_bytes())
        staging.rename(destination)
        LOGGER.info("Built %s: windows=%s label_status=%s supervised_training_ready=%s", destination, window_counts, manifest["label_status"], supervised_ready)
        return destination
    finally:
        if staging.exists():
            resolved = staging.resolve()
            if resolved.parent != destination.parent.resolve() or not resolved.name.startswith(".dataset-build-"):
                raise RuntimeError("Refusing cleanup outside the verified staging directory")
            shutil.rmtree(resolved)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/preprocessing.yaml")
    parser.add_argument("--input", type=Path, action="append", help="Repeat to combine non-overlapping files from one source")
    parser.add_argument("--output", type=Path, help="New run directory; existing outputs are never overwritten")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        build_dataset(load_config(args.config), args.input, output=args.output)
        return 0
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as error:
        LOGGER.error("Dataset build failed: %s", error)
        return 2


if __name__ == "__main__": raise SystemExit(main())
