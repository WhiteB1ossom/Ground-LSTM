"""Select advisory persistence/hysteresis using validation predictions only."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.evaluation.stream_metrics import StreamMetrics
from src.realtime.decision import DecisionEngine


def select_policy(model_dir: Path, dataset_dir: Path, *, model: str, minimum_recall: float) -> dict:
    if model not in {"logistic", "lstm"}: raise ValueError("Unsupported calibration model")
    report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    with np.load(model_dir / "validation-predictions.npz", allow_pickle=False) as data:
        scores, y = data[model], data["y"]
    with np.load(dataset_dir / "validation.npz", allow_pickle=False) as data:
        metadata = {k: data[k] for k in ("end_timestamp", "device_id", "event_id", "y")}
        metadata["session_id"] = data["session_id"] if "session_id" in data.files else data["event_id"]
    if not np.array_equal(y, metadata["y"]) or set(np.unique(y)) != {0, 1}: raise ValueError("Invalid validation targets")
    on = report["models"][model]["threshold_selection"]["selected_threshold"]
    pipeline = manifest["configuration"]["pipeline"]
    period = pipeline["alignment_period_seconds"] * pipeline["windows"]["stride"]
    candidates = []
    for ratio in (1., .8, .6):
        for consecutive in (1, 2, 3):
            engine, session = None, None
            accumulator = StreamMetrics(on, period)
            tp = fp = fn = tn = 0
            for i, probability in enumerate(scores):
                current = (str(metadata["device_id"][i]), str(metadata["session_id"][i]))
                if current != session:
                    session = current
                    engine = DecisionEngine(on, on * ratio, consecutive=consecutive)
                value = metadata["end_timestamp"][i]
                timestamp = int(value) if isinstance(value, (int, np.integer)) else int(pd.Timestamp(str(value)).value)
                decision = engine.update(timestamp, float(probability), available=True)
                truth = int(y[i])
                predicted = int(decision.alarm_active)
                tp += truth == 1 and predicted == 1; fn += truth == 1 and predicted == 0
                fp += truth == 0 and predicted == 1; tn += truth == 0 and predicted == 0
                accumulator.consume({"timestamp_ns": timestamp, "device_id": current[0], "session_id": current[1],
                                     "ground_truth": "risk" if truth else "normal", "available": True,
                                     "prediction": {"risk_score": float(probability)},
                                     "decision": {"alarm_active": decision.alarm_active, "transition": decision.transition}})
            measured = accumulator.finish()
            recall = tp / (tp + fn)
            f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.
            candidates.append({"on": on, "off": on * ratio, "consecutive": consecutive, "alarm_recall": recall,
                               "alarm_f1": f1, "alarm_fp": fp, "alarm_fn": fn,
                               "false_alarm_episodes": measured["false_alarm_episodes"],
                               "normal_alarm_fraction": measured["normal_alarm_fraction"],
                               "median_detection_delay_seconds": measured["median_detection_delay_seconds"]})
    eligible = [c for c in candidates if c["alarm_recall"] >= minimum_recall]
    if eligible:
        selected = min(eligible, key=lambda c: (c["false_alarm_episodes"], c["normal_alarm_fraction"], -c["alarm_f1"], c["consecutive"]))
    else:
        selected = max(candidates, key=lambda c: (c["alarm_recall"], c["alarm_f1"], -c["consecutive"]))
    return {"schema_version": 1, "selection_split": "validation", "model": model, "minimum_recall": minimum_recall,
            "target_met": bool(eligible), "selected": selected, "candidates": candidates, "deployment_approved": False,
            "scope": "software_fixture_window-persistence_calibration_not_physical_safety"}
