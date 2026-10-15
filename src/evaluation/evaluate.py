"""Re-evaluate saved models using their frozen validation thresholds and dataset."""

import argparse
import json
import logging
from pathlib import Path

import numpy as np

from src.evaluation.metrics import classification_metrics, event_group_metrics
from src.models.baselines import LogisticBaseline, ThresholdBaseline
from src.preprocessing.scaling import FrozenScaler
from src.training.data import file_hash, load_dataset
from src.training.train import keras_probabilities


def evaluate(experiment: Path, dataset: Path, output: Path) -> dict:
    experiment, output = experiment.resolve(), output.resolve()
    if output.exists(): raise FileExistsError("Evaluation output exists; use a new file")
    integrity = json.loads((experiment / "model-integrity.json").read_text(encoding="utf-8"))
    required = {"best_model.keras", "logistic.json", "scaler.json", "feature_order.json", "report.json"}
    if set(integrity["files"]) != required: raise ValueError("Incomplete experiment integrity contract")
    for name, expected in integrity["files"].items():
        if file_hash(experiment / name) != expected: raise ValueError(f"Experiment artifact changed: {name}")
    report = json.loads((experiment / "report.json").read_text(encoding="utf-8"))
    data = load_dataset(dataset, report["config"], synthetic_demo=report["synthetic_demo"])
    if data.hashes != report["dataset_hashes"]: raise ValueError("Dataset changed since training")
    forbidden = [data.directory, experiment, *[Path(i["path"]).resolve().parent for i in data.manifest["inputs"]]]
    if any(output == p or p in output.parents for p in forbidden): raise ValueError("Evaluation output must be outside experiment/raw/prepared inputs")
    if any(file_hash(experiment / name) != data.hashes[name] for name in ("scaler.json", "feature_order.json")):
        raise ValueError("Experiment preprocessing differs from dataset")
    import tensorflow as tf
    model = tf.keras.models.load_model(experiment / "best_model.keras")
    if tuple(model.input_shape[1:]) != data.splits["test"]["X"].shape[1:]: raise ValueError("Model input shape mismatch")
    expected_outputs = 1 if data.class_count == 2 else data.class_count
    if model.output_shape[-1] != expected_outputs: raise ValueError("Model class count mismatch")
    logistic = LogisticBaseline.load(experiment / "logistic.json")
    rules = ThresholdBaseline(data.manifest, FrozenScaler.load(experiment / "scaler.json"), report["threshold_rules"])
    results = {}
    for name, saved in report["models"].items():
        if saved["status"] != "evaluated":
            results[name] = saved
            continue
        # Replay never searches candidate thresholds, even if test labels differ.
        threshold = saved["threshold_selection"].get("selected_threshold")
        result = {"status": "evaluated", "threshold_selection": saved["threshold_selection"], "coverage": {}}
        for split in ("validation", "test"):
            part = data.splits[split]
            if name == "lstm": p = keras_probabilities(model, part["X"], report["config"]["training"]["batch_size"])
            elif name == "logistic": p = logistic.predict(part["X"])
            elif name == "threshold_rule": p = rules.predict(part["X"])
            else: raise ValueError("Unknown saved model")
            covered = np.isfinite(p).all(axis=1) if p.ndim == 2 else np.isfinite(p)
            if not covered.any(): raise ValueError("Saved model has no covered predictions")
            result[split] = classification_metrics(part["y"][covered], p[covered], threshold=threshold, class_count=data.class_count)
            if "event_summary" in saved[split]: result[split]["event_summary"] = event_group_metrics(part, p, threshold=threshold, class_count=data.class_count)
            result["coverage"][split] = float(covered.mean())
        results[name] = result
    result = {"schema_version": 1, "experiment_directory": str(experiment), "dataset_hashes": data.hashes,
              "synthetic_demo": data.synthetic, "thresholds_retuned": False, "models": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evaluate(args.experiment, args.dataset, args.output)
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError) as error:
        logging.error("Evaluation failed: %s", error)
        return 2


if __name__ == "__main__": raise SystemExit(main())
