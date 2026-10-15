"""Two advisory tasks: equipment review and surge activity, never lightning confirmation."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from src.evaluation.stream_metrics import StreamMetrics
from src.realtime.inference import InferenceEngine
from src.realtime.replay import observations
from src.realtime.recorder import EventRecorder
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import TimelineWriter
from src.utils.config import read_yaml


TASKS = ("degradation", "surge")


def _local(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError("Server artifact path must remain within its run")
    return path


class EquipmentServer:
    def __init__(self, run_directory: Path):
        self.directory = run_directory.resolve()
        manifest = json.loads((self.directory / "server-models.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1 or manifest.get("deployment_target") != "server" or set(manifest.get("tasks", {})) != set(TASKS):
            raise ValueError("Expected complete equipment server model manifest")
        self.pipelines = {}
        for task in TASKS:
            paths = manifest["tasks"][task]
            engine = InferenceEngine(_local(self.directory, paths["bundle"]), model="lstm")
            enabled = [s for s in engine.manifest["sensors"] if s["enabled"]]
            if len(enabled) != 10 or next(s for s in enabled if s["name"] == "lightning_sensor")["unit"] != "count":
                raise ValueError("Server models must retain ten sensors and a cumulative counter")
            self.pipelines[task] = RealtimePipeline(engine, read_yaml(_local(self.directory, paths["replay_config"]))["replay"])

    def feed(self, observation):
        results = {}
        # Validate both tasks before mutating either pipeline.
        for pipeline in self.pipelines.values():
            stamp = pipeline.validate_observation(observation)
            if pipeline.last_observation is not None and stamp <= pipeline.last_observation: raise ValueError("Duplicate/late server observation")
            if pipeline.device is not None and observation.get("device_id", "") != pipeline.device: raise ValueError("Mixed server devices rejected")
        for task, pipeline in self.pipelines.items():
            source = deepcopy(observation)
            source["ground_truth"] = source.get(task + "_truth", "UNLABELED")
            results[task] = pipeline.feed(source)
        if len(results["degradation"]) != len(results["surge"]): raise RuntimeError("Server task alignment mismatch")
        rows = []
        for degradation, surge in zip(results["degradation"], results["surge"]):
            if degradation["timestamp_ns"] != surge["timestamp_ns"]: raise RuntimeError("Server task timestamp mismatch")
            available = degradation["available"] and surge["available"]
            flags = (degradation["decision"]["alarm_active"], surge["decision"]["alarm_active"])
            counter = degradation["equipment"]["counter"]
            state = {(False, False): "NORMAL", (True, False): "EQUIPMENT_REVIEW", (False, True): "SURGE_ACTIVITY", (True, True): "EQUIPMENT_REVIEW_AND_SURGE"}[flags]
            rows.append({"timestamp_ns": degradation["timestamp_ns"], "timestamp": degradation["timestamp"],
                         "device_id": degradation["device_id"], "session_id": degradation["session_id"], "available": available,
                         "state": state if available else "UNAVAILABLE", "latched_advisory_state": state,
                         "equipment": degradation["equipment"], "maintenance_criteria": degradation["sensor_rules"],
                         "observed_surge_activity": counter["recent_count"] > 0 if counter["increment_known"] else None,
                         "tasks": {"degradation": degradation, "surge": surge},
                         "lightning_confirmed": None, "hardware_actuation_performed": False})
        return rows


def replay_server(input_path: Path, run_directory: Path, output: Path):
    if output.exists(): raise FileExistsError("Server replay output exists")
    input_root = input_path.resolve().parent
    if output.resolve().is_relative_to(input_root): raise ValueError("Server output must be outside raw inputs")
    server = EquipmentServer(run_directory)
    output.mkdir(parents=True)
    writer = TimelineWriter(output)
    metrics = {task: StreamMetrics(p.engine.threshold, p.period.total_seconds()) for task, p in server.pipelines.items()}
    states, count, aligned, rejected = {}, 0, 0, 0
    failures = 0
    errors = []
    recorders, recorder_reports = {}, {}
    try:
        for task, pipeline in server.pipelines.items():
            s = pipeline.settings
            recorders[task] = EventRecorder(output / task / "events", pre_seconds=s["pre_event_seconds"], post_seconds=s["post_event_seconds"],
                                            period_seconds=pipeline.period.total_seconds(), queue_capacity=s["writer_queue_capacity"],
                                            max_active=s["max_active_events"], max_event_seconds=s["max_event_seconds"],
                                            max_saved_events=s.get("max_saved_events", 1000), shutdown_timeout_seconds=s.get("shutdown_timeout_seconds", 5),
                                            metadata={"task": task, "model_version": pipeline.engine.manifest["model_version"], "physical_validation": False})
            pipeline.recorder = recorders[task]
        for observation in observations(input_path, [s.name for s in server.pipelines["degradation"].sensors if s.enabled]):
            count += 1
            try: rows = server.feed(observation)
            except ValueError as error:
                rejected += 1
                if len(errors) < 100: errors.append({"row": count, "error": str(error)})
                continue
            for row in rows:
                writer.write(row)
                aligned += 1
                states[row["state"]] = states.get(row["state"], 0) + 1
                for task in TASKS:
                    record = row["tasks"][task]
                    metrics[task].consume(record)
                    failures += record["decision"]["reason"].startswith(("INFERENCE_ERROR:", "PREPROCESSING_ERROR:"))
    finally:
        for task, recorder in recorders.items(): recorder_reports[task] = recorder.close()
        trace = writer.close()
    degraded = rejected or failures or trace["error_count"] or not aligned or any(not m.valid for m in metrics.values()) or any(r["status"] != "SUCCESS" for r in recorder_reports.values())
    result = {"schema_version": 1, "status": "DEGRADED" if degraded else "SUCCESS",
              "deployment_target": "server", "observations": count, "aligned_rows": aligned, "states": states,
              "rejected_observations": rejected, "processing_failure_count": failures, "errors": errors,
              "tasks": {t: m.finish() for t, m in metrics.items()}, "recorders": recorder_reports,
              "timeline": trace, "lightning_confirmation_supported": False, "physical_validation": False,
              "hardware_actuation_performed": False}
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try: result = replay_server(args.input, args.run, args.output)
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Server replay failed: {type(error).__name__}: {error}")
        return 2
    print(json.dumps({k: result[k] for k in ("status", "observations", "aligned_rows", "states")}))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__": raise SystemExit(main())
