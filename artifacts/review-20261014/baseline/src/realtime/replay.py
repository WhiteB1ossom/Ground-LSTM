"""Timestamp-preserving stream replay with injectable clocks and no label resets."""

import argparse
from collections import Counter, deque
import csv
import json
import logging
from pathlib import Path
import time

import numpy as np

from src.data.schema import parse_timestamp
from src.evaluation.stream_metrics import StreamMetrics
from src.realtime.inference import InferenceEngine
from src.realtime.recorder import EventRecorder
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import TimelineWriter
from src.utils.config import read_yaml

LOGGER = logging.getLogger(__name__)


def observations(path: Path, required_sensors=()):
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq
        if not set(required_sensors).issubset(pq.ParquetFile(path).schema.names): raise ValueError("Missing active sensor column")
        for batch in pq.ParquetFile(path).iter_batches(batch_size=1024):
            for row in batch.to_pylist(): yield row
        return
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "timestamp" not in reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("Missing timestamp or duplicate CSV header")
        if not set(required_sensors).issubset(reader.fieldnames): raise ValueError("Missing active sensor column")
        for row in reader:
            if None in row or any(v is None for v in row.values()): raise ValueError("Malformed CSV row")
            yield row


def replay(path: Path, bundle: Path, settings: dict, output: Path, *, model="logistic", speed="max", tflite_path=None,
           clock=time.monotonic, sleep=time.sleep, write_events=True):
    if speed != "max" and (not np.isfinite(float(speed)) or float(speed) <= 0): raise ValueError("Invalid replay speed")
    if output.exists(): raise FileExistsError("Replay output exists")
    input_root = path.resolve().parent
    if output.resolve() == input_root or input_root in output.resolve().parents:
        raise ValueError("Replay output must be outside raw input directory")
    engine = InferenceEngine(bundle, model=model, tflite_path=tflite_path)
    pipeline = RealtimePipeline(engine, settings)
    output.mkdir(parents=True)
    recorder = writer = None
    errors, count, origin, wall_origin = deque(maxlen=1024), 0, None, clock()
    rejected, aligned_count, inference_failures, preprocessing_failures, statuses = 0, 0, 0, 0, Counter()
    accumulator = StreamMetrics(engine.threshold, pipeline.period.total_seconds())
    latencies = deque(maxlen=4096)
    start = time.perf_counter()
    recorder_report = None
    try:
        trace_options = {k: settings[k] for k in ("timeline_segment_bytes", "timeline_max_segments") if k in settings}
        writer = TimelineWriter(output, **{k.removeprefix("timeline_"): v for k, v in trace_options.items()})
        if write_events:
            recorder = EventRecorder(output / "events", pre_seconds=settings["pre_event_seconds"], post_seconds=settings["post_event_seconds"],
                                     period_seconds=pipeline.period.total_seconds(), queue_capacity=settings["writer_queue_capacity"],
                                     max_active=settings["max_active_events"], max_event_seconds=settings["max_event_seconds"],
                                     max_saved_events=settings.get("max_saved_events", 1000),
                                     raw_history_capacity=settings.get("raw_history_capacity", 1024),
                                     max_raw_observations_per_event=settings.get("max_raw_observations_per_event", 4096),
                                     metadata={"model_version": engine.manifest["model_version"],
                                     "scaler_sha256": engine.manifest["files"]["scaler.json"], "settings": settings})
            pipeline.recorder = recorder
        for observation in observations(path, [s.name for s in pipeline.sensors if s.enabled]):
            count += 1
            timestamp, reason = parse_timestamp(observation.get("timestamp"), pipeline.config["timestamp"])
            if reason:
                errors.append({"row": count, "reason": reason})
                rejected += 1
                continue
            if origin is None: origin = timestamp
            if speed != "max":
                due = wall_origin + (timestamp - origin).total_seconds() / float(speed)
                wait = due - clock()
                if wait > 0: sleep(wait)
            try: samples = pipeline.feed(observation)
            except ValueError as error:
                errors.append({"row": count, "reason": str(error)})
                rejected += 1
                continue
            for sample in samples:
                writer.write(sample)
                aligned_count += 1
                statuses[sample["input_status"]] += 1
                inference_failures += sample["decision"]["reason"].startswith("INFERENCE_ERROR:")
                preprocessing_failures += sample["decision"]["reason"].startswith("PREPROCESSING_ERROR:")
                accumulator.consume(sample)
                if sample["prediction"]: latencies.append(sample["prediction"]["inference_ms"])
            if count % 10000 == 0: LOGGER.info("Replayed %s observations", count)
    finally:
        if recorder: recorder_report = recorder.close()
        trace_report = writer.close() if writer else None
    metrics = accumulator.finish()
    degraded = rejected or inference_failures or preprocessing_failures or not aligned_count or trace_report["error_count"] or (recorder_report and
                (recorder_report["writer_error_count"] or recorder_report["raw_history_dropped"] or recorder_report["raw_event_dropped"]))
    summary = {"schema_version": 1, "status": "DEGRADED" if degraded else "SUCCESS", "input": str(path.resolve()), "model": model, "speed": speed,
               "synthetic_demo": engine.manifest["synthetic_demo"], "observations": count, "aligned_rows": aligned_count,
               "model_version": engine.manifest["model_version"], "decision_thresholds": {"on": pipeline.decision.on, "off": pipeline.decision.off,
               "consecutive": pipeline.decision.consecutive}, "status_counts": dict(statuses),
               "rejected_observations": list(errors), "rejected_observation_count": rejected, "buffer_capacity": pipeline.ring.capacity, "buffer_array_bytes": pipeline.ring.storage_bytes,
               "input_tensor_bytes": pipeline.tensor.nbytes, "sequence_workspace_bytes": pipeline.builder.workspace_bytes,
               "elapsed_host_seconds": time.perf_counter() - start, "inference_host_ms": {"median": float(np.median(latencies)), "p95": float(np.percentile(latencies, 95)), "sample_limit": latencies.maxlen} if latencies else None,
               "recorder": recorder_report, "timeline": trace_report, "inference_failure_count": inference_failures,
               "preprocessing_failure_count": preprocessing_failures,
               "evaluation": metrics, "mcu_verified": False, "hardware_actuation_performed": False}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/integration.yaml"))
    parser.add_argument("--model", choices=("logistic", "lstm", "tflite"), default="logistic")
    parser.add_argument("--tflite", type=Path)
    parser.add_argument("--speed", choices=("1", "2", "10", "max"), default="max")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        result = replay(args.input, args.bundle, read_yaml(args.config)["replay"], args.output, model=args.model, speed=args.speed, tflite_path=args.tflite)
    except (ValueError, OSError, RuntimeError) as error:
        LOGGER.error("Replay failed: %s", error)
        return 2
    print(json.dumps({"status": result["status"], "aligned_rows": result["aligned_rows"], "evaluation": result["evaluation"]}))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
