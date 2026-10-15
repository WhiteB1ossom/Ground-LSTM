"""CSV replay demo of preprocessing -> fixed ring -> LSTM-shaped input (no model)."""

import argparse
from collections import Counter
import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.loader import load_raw
from src.data.schema import parse_timestamp
from src.features.transform import FeatureTransform
from src.preprocessing.alignment import CausalAligner
from src.preprocessing.scaling import FrozenScaler
from src.realtime.ring_buffer import RingBuffer, buffer_capacity
from src.realtime.sequence_builder import SequenceBuilder
from src.utils.config import SensorSpec, read_yaml

LOGGER = logging.getLogger(__name__)


def run_demo(dataset: Path, realtime_config: Path, output: Path) -> dict:
    dataset, output = dataset.resolve(), output.resolve()
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    settings = manifest["configuration"]
    profile = read_yaml(realtime_config)
    if profile.get("mode") != "advisory" or profile.get("hardware_actuation_enabled") is not False:
        raise ValueError("Ring demo only supports advisory mode without hardware actuation")
    buffers = profile["buffer"]
    p = settings["pipeline"]
    if buffers["sequence_length"] != p["windows"]["sequence_length"] or buffers["sampling_period_seconds"] != p["alignment_period_seconds"] or buffers["stride"] != p["windows"]["stride"]:
        raise ValueError("Realtime sequence/period/stride must match dataset artifacts")
    scaler = FrozenScaler.load(dataset / "scaler.json")
    if scaler.order != manifest["feature_order"]: raise ValueError("Scaler order conflicts with manifest")
    sensors = tuple(SensorSpec(**s) for s in manifest["sensors"])
    capacity = buffer_capacity(buffers["sequence_length"], buffers["pre_event_seconds"], buffers["sampling_period_seconds"])
    ring = RingBuffer(capacity, len(scaler.order))
    builder = SequenceBuilder(ring, buffers["sequence_length"], buffers["sampling_period_seconds"], stride=buffers["stride"])
    tensor = np.empty((1, builder.length, ring.feature_count), dtype=np.float32)
    snapshot_path = output.with_suffix(".snapshot.npz")
    if output.exists() or snapshot_path.exists(): raise FileExistsError("Demo results already exist; specify a new --output path")
    source = settings["input"]["source"]
    frames = []
    for origin in manifest["inputs"]:
        raw = load_raw(origin["path"], source=source)
        if raw.sha256 != origin["sha256"]: raise ValueError("Raw input has changed since the dataset was built")
        if output == raw.path or raw.path.parent in output.parents: raise ValueError("Demo output must be outside raw inputs")
        frame = raw.frame.copy()
        timestamps = [parse_timestamp(v, settings["timestamp"]) for v in frame["timestamp"]]
        if any(reason for _, reason in timestamps): raise ValueError("Invalid input timestamp")
        frame["timestamp"] = [stamp for stamp, _ in timestamps]
        frame["device_id"] = frame.get("device_id", pd.Series("", index=frame.index)).fillna("").astype(str)
        frame["event_id"] = frame.get("event_id", pd.Series("", index=frame.index)).fillna("").astype(str)
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    if frame["device_id"].nunique() != 1: raise ValueError("Demo expects one device; use independent rings per stream")
    frame = frame.sort_values("timestamp", kind="stable")
    if frame["timestamp"].duplicated().any(): raise ValueError("Duplicate input timestamps")
    blocks = frame["event_id"].ne(frame["event_id"].shift()).cumsum()
    counts, samples, segments = Counter(), 0, 0
    LOGGER.info("Ring allocated: capacity=%s features=%s storage_bytes=%s", ring.capacity, ring.feature_count, ring.storage_bytes)
    for _, block in frame.groupby(blocks, sort=False):
        # Offline fixture segmentation is explicit; the device itself will not
        # know ground-truth event IDs. Live stream resets must be acquisition resets.
        ring.clear()
        aligner, features = CausalAligner(sensors, stale_action=p["stale_action"]), FeatureTransform(sensors, p)
        if features.order != scaler.order: raise ValueError("Preprocessor feature order conflicts with scaler")
        rows, cursor = block.to_dict("records"), 0
        period = pd.Timedelta(seconds=buffers["sampling_period_seconds"])
        grid = pd.date_range(rows[0]["timestamp"].ceil(period), rows[-1]["timestamp"].floor(period), freq=period)
        for timestamp in grid:
            while cursor < len(rows) and rows[cursor]["timestamp"] <= timestamp:
                row = rows[cursor]
                status_ok = all(field not in row or (not pd.isna(row[field]) and str(row[field]) in settings["quality"][key])
                                for field, key in (("sensor_status", "healthy_sensor_status"), ("communication_status", "healthy_communication_status")))
                aligner.update(row["timestamp"], row, status_ok=status_ok)
                cursor += 1
            aligned = aligner.sample(timestamp)
            vector = features.transform(aligned)
            valid = aligned.valid and (p["stale_action"] != "drop_window" or np.isfinite(vector).all())
            ring.append(timestamp, scaler.transform(vector[None, :], features.order)[0], valid=bool(valid))
            counts[builder.build_into(tensor).reason] += 1
            samples += 1
        segments += 1
        LOGGER.info("Segment %s: ring_size=%s/%s cumulative_overwrites=%s", segments, ring.size, ring.capacity, ring.overwritten_samples)
    final = ring.snapshot()
    report = {"schema_version": 1, "purpose": "RING_BUFFER_SOFTWARE_DEMO_NO_MODEL_INFERENCE",
              "dataset_version": manifest["dataset_version"], "replayed_samples": samples, "fixture_segments": segments,
              "buffer_capacity": ring.capacity, "final_buffer_size": ring.size, "overwritten_samples": ring.overwritten_samples,
              "buffer_storage_bytes": ring.storage_bytes, "sequence_workspace_bytes": builder.workspace_bytes,
              "tensor_bytes": tensor.nbytes, "status_counts": dict(counts), "sequence_shape": list(tensor.shape),
              "oldest_retained_timestamp": pd.Timestamp(int(final.timestamps_ns[0]), tz="UTC").isoformat() if len(final.timestamps_ns) else None,
              "latest_retained_timestamp": pd.Timestamp(int(final.timestamps_ns[-1]), tz="UTC").isoformat() if len(final.timestamps_ns) else None,
              "model_inference_performed": False, "hardware_actuation_performed": False,
              "notes": ["Array payload memory only; not total Python RAM or an MCU deployment estimate.",
                        "Snapshot export is explicit demo inspection, not automatic risk event recording.",
                        "Fixture event boundaries reset context to match offline preparation, not a live detection mechanism."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("xb") as handle:
        np.savez_compressed(handle, values=final.values, timestamps_ns=final.timestamps_ns, valid=final.valid, feature_order=np.array(scaler.order, dtype=str))
    with output.open("x", encoding="utf-8") as handle: json.dump(report, handle, ensure_ascii=False, indent=2)
    LOGGER.info("Sequence-ready=%s overwrites=%s; saved %s", counts["READY"], ring.overwritten_samples, output)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, help="Prepared Phase 2 run; default: latest verification report's run")
    parser.add_argument("--config", type=Path, default=Path("configs/realtime_demo.yaml"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/reports/ring-buffer-demo.json"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        dataset = args.dataset
        if dataset is None:
            verification = json.loads(Path("artifacts/reports/phase2-verification.json").read_text(encoding="utf-8"))
            dataset = Path(verification["output_directory"])
        run_demo(dataset, args.config, args.output)
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        LOGGER.error("Ring demo failed: %s", error)
        return 2


if __name__ == "__main__": raise SystemExit(main())
