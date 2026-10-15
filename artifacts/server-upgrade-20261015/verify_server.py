"""Verify saved server weights against held-out tensors and current stream code."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys

import numpy as np
import pandas as pd
import tensorflow as tf

from src.evaluation.stream_metrics import StreamMetrics
from src.realtime.equipment_server import EquipmentServer
from src.realtime.replay import observations
from src.utils.config import read_yaml


root = Path.cwd()
output = Path(__file__).parent.resolve()
run = root / "artifacts/server-equipment-20261015"
raw = root / "data/raw/equipment-server/server-equipment-20261015"
state = json.loads((run / "run.json").read_text(encoding="utf-8"))
assert state["status"] == "SERVER_SOFTWARE_COMPLETE_PHYSICAL_VALIDATION_PENDING"
server = EquipmentServer(run)
metadata, probabilities, checked, maximum_error, reports = {}, {}, Counter(), Counter(), {}
for task in ("degradation", "surge"):
    with np.load(run / task / "dataset/test.npz", allow_pickle=False) as saved:
        tensors = saved["X"]
        keys = [int(pd.Timestamp(str(v)).value) if not isinstance(v, (int, np.integer)) else int(v) for v in saved["end_timestamp"]]
        metadata[task] = {key: (i, tensors[i]) for i, key in enumerate(keys)}
    selected = state["stages"][task]["selected"]
    model_dir = run / task / "models" / selected
    reports[task] = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    with np.load(model_dir / "test-predictions.npz", allow_pickle=False) as saved:
        probabilities[task] = saved["lstm"]
    assert len(metadata[task]) == len(probabilities[task]) == 2958
    assert len(reports[task]["feature_order"]) == 39
    assert all(s["enabled"] for s in server.pipelines[task].manifest["sensors"])

joint_cm = np.zeros((4, 4), dtype=np.int64)
counter_cm = np.zeros((2, 2), dtype=np.int64)
counter_covered = 0
per_scenario = {}
resets = 0
last = None
for observation in observations(raw / "heldout.synthetic.csv"):
    original_truth = observation["ground_truth"]
    scenario = observation["scenario"]
    if scenario not in per_scenario:
        per_scenario[scenario] = {task: StreamMetrics(p.engine.threshold, p.period.total_seconds()) for task, p in server.pipelines.items()}
    for row in server.feed(observation):
        for task, pipeline in server.pipelines.items():
            sample = row["tasks"][task]
            per_scenario[scenario][task].consume(sample)
            timestamp = sample["timestamp_ns"]
            if sample["prediction"] is not None:
                assert timestamp in metadata[task], (task, timestamp)
                index, tensor = metadata[task][timestamp]
                np.testing.assert_array_equal(pipeline.tensor[0], tensor)
                error = abs(sample["prediction"]["risk_score"] - float(probabilities[task][index]))
                assert error < 2e-5, error
                assert sample["prediction"]["predicted_class"] == int(probabilities[task][index] >= pipeline.engine.threshold)
                maximum_error[task] = max(maximum_error[task], error)
                checked[task] += 1
        if row["available"]:
            truth = int(observation["degradation_truth"] == "risk") + 2 * int(observation["surge_truth"] == "risk")
            prediction = int(row["tasks"]["degradation"]["decision"]["alarm_active"]) + 2 * int(row["tasks"]["surge"]["decision"]["alarm_active"])
            joint_cm[truth, prediction] += 1
        counter = row["equipment"]["counter"]
        if row["observed_surge_activity"] is not None:
            counter_cm[int(observation["surge_truth"] == "risk"), int(row["observed_surge_activity"])] += 1
            counter_covered += 1
        if counter["reset"]:
            resets += 1
            assert not counter["increment_known"] and counter["recent_count"] is None
        if scenario in {"normal", "hot_ambient", "high_count_only", "counter_reset", "heating_without_surge"}:
            assert counter["recent_count"] in (0, None), (scenario, counter)
        if row["equipment"]["voltage_response"]:
            assert row["equipment"]["voltage_response"]["protection_success"] is None
        assert row["lightning_confirmed"] is None
    assert observation["ground_truth"] == original_truth
    last = observation
assert checked == {"degradation": 2958, "surge": 2958}, checked
assert resets == 1

# An actual TensorFlow backend failure must not silently clear the other task.
pipeline = server.pipelines["surge"]
original_predict = pipeline.engine.predict_fn
pipeline.decision.active = True
def fail(tensor): raise tf.errors.InternalError(None, None, "injected server surge failure")
pipeline.engine.predict_fn = fail
stamp = pd.Timestamp(last["timestamp"])
failure_seen = False
for tick in range(1, 11):
    observation = {**last, "timestamp": (stamp + pd.Timedelta(milliseconds=tick * 100)).isoformat()}
    for row in server.feed(observation):
        if row["tasks"]["surge"]["decision"]["reason"].startswith("INFERENCE_ERROR:"):
            assert not row["available"] and row["state"] == "UNAVAILABLE"
            assert row["tasks"]["surge"]["decision"]["alarm_active"]
            failure_seen = True
assert failure_seen
pipeline.engine.predict_fn = original_predict
recovery_seen = False
for tick in range(11, 21):
    observation = {**last, "timestamp": (stamp + pd.Timedelta(milliseconds=tick * 100)).isoformat()}
    for row in server.feed(observation):
        if row["tasks"]["surge"]["prediction"] is not None: recovery_seen = row["available"]
assert recovery_seen

# Boundary challenges are deliberately unlabeled. They verify the review-rule
# contract through the real models without inventing physical failure labels.
boundaries = []
rules = read_yaml(root / "configs/equipment_server.yaml")["replay"]["rules"]
base_values = dict(ground_voltage_a=.5, ground_voltage_b=.5, leakage_current=.0015,
                   limiter_temp_a=30., limiter_temp_b=30., limiter_temp_c=30.,
                   humidity=50., ambient_temp=25., input_voltage=220., lightning_sensor=1000.)
origin = stamp + pd.Timedelta(seconds=100)
for case, (rule, position) in enumerate((rule, position) for rule in rules for position in (-1, 0, 1)):
    physical = {**base_values, rule["sensor"]: rule["value"] + position * max(abs(rule["value"]) * .01, 1e-6)}
    for tick in range(64):
        observation = {**physical, "timestamp": (origin + pd.Timedelta(milliseconds=(case * 64 + tick) * 100)).isoformat(),
                       "device_id": "SERVER_SOFTWARE_DEVICE", "session_id": f"unlabeled-boundary-{case}", "event_id": "",
                       "ground_truth": "UNLABELED", "degradation_truth": "UNLABELED", "surge_truth": "UNLABELED"}
        row = server.feed(observation)[0]
    checked_rule = next(v for v in row["maintenance_criteria"]["details"] if v["sensor"] == rule["sensor"])
    assert checked_rule["condition_met"] == (position >= 0)
    assert row["observed_surge_activity"] is False and row["lightning_confirmed"] is None
    boundaries.append({"sensor": rule["sensor"], "value": physical[rule["sensor"]], "unit": rule["unit"],
                       "boundary_position": position, "review_condition_met": checked_rule["condition_met"],
                       "ground_truth": "UNLABELED", "model_scores": {t: row["tasks"][t]["prediction"]["risk_score"] for t in ("degradation", "surge")}})
(output / "boundary-challenges.json").write_text(json.dumps(boundaries, indent=2), encoding="utf-8")

# The run manifest must load from a different directory without rewriting
# immutable training/bundle manifests or relying on the original run paths.
portable = output / "portable copy"
portable.mkdir(exist_ok=False)
shutil.copyfile(run / "server-models.json", portable / "server-models.json")
for task in ("degradation", "surge"):
    shutil.copytree(run / task / "bundle", portable / task / "bundle")
    shutil.copyfile(run / task / "replay-selected.yaml", portable / task / "replay-selected.yaml")
relocated = EquipmentServer(portable)
for task in ("degradation", "surge"):
    tensor = next(iter(metadata[task].values()))[1][None, ...]
    original = server.pipelines[task].engine.predict(tensor)
    copied = relocated.pipelines[task].engine.predict(tensor)
    assert abs(original["risk_score"] - copied["risk_score"]) < 1e-6
    assert original["predicted_class"] == copied["predicted_class"]

# Exercise the public two-task CLI, including both asynchronous event recorders.
frame = pd.read_csv(raw / "heldout.synthetic.csv")
subset = frame.loc[frame["scenario"].isin({"normal", "heating_without_surge", "surge_only", "both", "counter_reset"})]
inputs = output / "inputs"
inputs.mkdir(exist_ok=False)
subset.to_csv(inputs / "combined.csv", index=False)
target = output / "combined-replay"
process = subprocess.run([sys.executable, "-m", "src.realtime.equipment_server", "--run", str(run),
                          "--input", str(inputs / "combined.csv"), "--output", str(target)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
(output / "combined-replay.log").write_text(process.stdout + process.stderr, encoding="utf-8")
assert process.returncode == 0, "See combined-replay.log"
combined = json.loads((target / "summary.json").read_text(encoding="utf-8"))
assert combined["status"] == "SUCCESS" and combined["aligned_rows"] == len(subset) == 9000
assert all(r["shutdown_complete"] and not r["writer_error_count"] for r in combined["recorders"].values())

protected = json.loads((output / "protected-hashes.json").read_text(encoding="utf-8"))
changed = [name for name, before in protected.items() if hashlib.sha256((root / name).read_bytes()).hexdigest() != before]
assert not changed, changed
result = {"schema_version": 1, "status": "SUCCESS", "raw_rows": 153000, "heldout_rows": len(frame),
          "ten_sensors_enabled": True, "features": 39, "offline_stream_tensor_parity_windows": dict(checked),
          "maximum_score_error": dict(maximum_error), "joint_confusion_matrix": joint_cm.tolist(),
          "joint_axes": ["normal", "equipment_review", "surge_activity", "both"],
          "counter_activity_baseline": {"confusion_matrix": counter_cm.tolist(), "covered_rows": counter_covered, "meaning": "observed_recent_counter_increase_not_lightning_truth"},
          "per_scenario": {name: {task: metric.finish() for task, metric in tasks.items()} for name, tasks in per_scenario.items()},
          "counter_reset_not_new_surge": True, "tensorflow_failure_preserved_alarm": True, "recovered": True,
          "unlabeled_boundary_challenges_verified": len(boundaries),
          "portable_server_copy_verified": True, "actual_laptop_verified": False,
          "combined_cli": combined, "protected_files": len(protected), "protected_changed": changed,
          "selection": {task: {"selected": state["stages"][task]["selected"], "test": reports[task]["models"]["lstm"]["test"],
                                "best_epoch": reports[task]["best_epoch"], "epochs_completed": reports[task]["epochs_completed"]} for task in reports},
          "physical_validation": False, "hardware_actuation_performed": False}
(output / "runtime-verification.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("status", "heldout_rows", "features", "offline_stream_tensor_parity_windows", "maximum_score_error", "protected_files")}))
