"""Fit baselines/LSTM on train, select on validation, report held-out test metrics."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import shutil
import tempfile
import time

import numpy as np
from sklearn.utils.class_weight import compute_class_weight

from src.evaluation.metrics import classification_metrics, select_threshold, event_group_metrics
from src.evaluation.report import plot_results, write_json, write_summary
from src.models.baselines import LogisticBaseline, ThresholdBaseline
from src.models.lstm import build_lstm
from src.preprocessing.scaling import FrozenScaler
from src.training.config import load_training_config
from src.training.data import file_hash, load_dataset, input_context_audit

LOGGER = logging.getLogger(__name__)


def keras_probabilities(model, X, batch_size: int):
    values = np.concatenate([model(X[start:start + batch_size], training=False).numpy() for start in range(0, len(X), batch_size)])
    return values[:, 0] if values.shape[1] == 1 else values


def evaluate_predictions(y_validation, validation_p, y_test, test_p, config, class_count, *, validation_metadata=None, test_metadata=None):
    validation_ok, test_ok = np.isfinite(validation_p).all(axis=1) if validation_p.ndim > 1 else np.isfinite(validation_p), np.isfinite(test_p).all(axis=1) if test_p.ndim > 1 else np.isfinite(test_p)
    if not validation_ok.any() or not test_ok.any(): return {"status": "disabled", "reason": "No covered validation/test predictions"}
    if class_count == 2:
        if set(np.unique(y_validation[validation_ok])) != {0, 1}:
            return {"status": "disabled", "reason": "Covered validation rows lack both classes"}
        selection = select_threshold(y_validation[validation_ok], validation_p[validation_ok], config["evaluation"], split="validation")
        threshold = selection["selected_threshold"]
    else:
        threshold, selection = None, {"selection_split": "validation", "reason": "Multiclass uses argmax; no binary threshold tuning"}
    result = {"status": "evaluated", "threshold_selection": selection,
            "validation": classification_metrics(y_validation[validation_ok], validation_p[validation_ok], threshold=threshold, class_count=class_count),
            "test": classification_metrics(y_test[test_ok], test_p[test_ok], threshold=threshold, class_count=class_count),
            "coverage": {"validation": float(validation_ok.mean()), "test": float(test_ok.mean())}}
    for split, metadata, probabilities in (("validation", validation_metadata, validation_p), ("test", test_metadata, test_p)):
        if metadata is not None: result[split]["event_summary"] = event_group_metrics(metadata, probabilities, threshold=threshold, class_count=class_count)
    return result


def validation_recommendation(results: dict, config: dict, class_count: int) -> dict:
    candidates = [(name, result["validation"]) for name, result in results.items()
                  if result["status"] == "evaluated" and result["coverage"]["validation"] == 1]
    eligible = [(name, metric) for name, metric in candidates if metric["recall"] >= config["evaluation"]["minimum_recall"]] if class_count == 2 else candidates
    pool = eligible or candidates
    name, _ = max(pool, key=lambda pair: ((pair[1]["f1"] if eligible else pair[1]["recall"]),
                                        pair[1]["recall"] if eligible else pair[1]["f1"], pair[0] == "logistic"))
    return {"model": name, "selection_split": "validation", "full_coverage_required": True,
            "recall_target_met": bool(eligible) if class_count == 2 else None,
            "tie_break": "Prefer logistic simplicity on equal validation metrics",
            "deployment_approved": False}


def train(dataset_dir: Path, config_path: Path, output: Path, *, synthetic_demo=False) -> Path:
    config = load_training_config(config_path)
    data = load_dataset(dataset_dir, config, synthetic_demo=synthetic_demo)
    output = output.resolve()
    forbidden = [data.directory, *[Path(item["path"]).resolve().parent for item in data.manifest["inputs"]]]
    if any(output == p or p in output.parents for p in forbidden): raise ValueError("Training output must be outside raw/prepared inputs")
    if output.exists(): raise FileExistsError("Training output exists; use a new experiment directory")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import tensorflow as tf
    tf.keras.utils.set_random_seed(config["seed"])
    if config["training"]["deterministic"]: tf.config.experimental.enable_op_determinism()
    train_data, validation, test = (data.splits[k] for k in ("train", "validation", "test"))
    class_weights = None
    if config["training"]["class_weight"] == "balanced":
        ids = np.arange(data.class_count)
        class_weights = {int(i): float(w) for i, w in zip(ids, compute_class_weight("balanced", classes=ids, y=train_data["y"]))}
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".training-", dir=output.parent))
    try:
        scaler = FrozenScaler.load(data.directory / "scaler.json")
        baseline = LogisticBaseline().fit(train_data["X"], train_data["y"], max_iter=config["baseline"]["logistic_max_iter"], class_weight="balanced" if class_weights else None, seed=config["seed"])
        baseline.save(staging / "logistic.json")
        results = {"logistic": evaluate_predictions(validation["y"], baseline.predict(validation["X"]), test["y"], baseline.predict(test["X"]), config, data.class_count, validation_metadata=validation, test_metadata=test)}
        test_predictions = {"logistic": baseline.predict(test["X"])}
        rules = ThresholdBaseline(data.manifest, scaler, config["baseline"]["threshold_rules"])
        if rules.rules and data.class_count == 2:
            validation_rule, test_rule = rules.predict(validation["X"]), rules.predict(test["X"])
            results["threshold_rule"] = evaluate_predictions(validation["y"], validation_rule, test["y"], test_rule, config, data.class_count, validation_metadata=validation, test_metadata=test)
            test_predictions["threshold_rule"] = test_rule
        else:
            results["threshold_rule"] = {"status": "disabled", "reason": "No confirmed sensor thresholds supplied" if not rules.rules else "Binary rules cannot provide multiclass predictions"}
        model = build_lstm(train_data["X"].shape[1:], data.class_count, config)
        batch_size = config["training"]["batch_size"]
        options = tf.data.Options()
        options.threading.private_threadpool_size = 1
        options.experimental_deterministic = True
        def batches(part):
            return tf.data.Dataset.from_tensor_slices((part["X"], part["y"])).batch(batch_size).with_options(options)

        class ValidationMetrics(tf.keras.callbacks.Callback):
            def on_epoch_end(self, epoch, logs=None):
                logs = logs if logs is not None else {}
                scores = keras_probabilities(self.model, validation["X"], batch_size)
                measured = classification_metrics(validation["y"], scores, threshold=.5 if data.class_count == 2 else None, class_count=data.class_count)
                logs["val_f1"] = measured["f1"]
                logs["val_false_negatives"] = measured["false_negatives"]
                logs["val_false_positives"] = measured["false_positives"]
                logs["val_risk_pr_auc_trapezoidal"] = measured["risk_pr_auc_trapezoidal"] or 0.0
                if "precision" in logs and "recall" in logs:
                    logs["f1"] = 2 * logs["precision"] * logs["recall"] / (logs["precision"] + logs["recall"]) if logs["precision"] + logs["recall"] else 0.0
                LOGGER.info("Epoch %s loss=%.5f val_loss=%.5f val_f1=%.4f val_FN=%s", epoch + 1, logs["loss"], logs["val_loss"], measured["f1"], measured["false_negatives"])

        early_stop = tf.keras.callbacks.EarlyStopping(monitor="val_loss", mode="min", min_delta=config["training"]["early_stopping_min_delta"], patience=config["training"]["early_stopping_patience"], restore_best_weights=False)
        callbacks = [ValidationMetrics(), tf.keras.callbacks.TerminateOnNaN(),
                     tf.keras.callbacks.ModelCheckpoint(staging / "best_model.keras", monitor="val_loss", mode="min", save_best_only=True),
                     early_stop]
        schedule = config["training"]["lr_schedule"]
        if schedule["enabled"]:
            callbacks.append(tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", mode="min", factor=schedule["factor"], patience=schedule["patience"], min_delta=config["training"]["early_stopping_min_delta"], min_lr=schedule["min_learning_rate"]))
        callbacks.append(tf.keras.callbacks.CSVLogger(staging / "history.csv"))
        history = model.fit(batches(train_data), validation_data=batches(validation), epochs=config["training"]["epochs"], callbacks=callbacks, class_weight=class_weights, shuffle=False, verbose=0)
        history_data = {key: [float(value) for value in values] for key, values in history.history.items()}
        if any(not np.isfinite(v).all() for v in history_data.values()): raise ValueError("Nonfinite training metrics; training failed")
        model = tf.keras.models.load_model(staging / "best_model.keras")
        validation_p = keras_probabilities(model, validation["X"], batch_size)
        test_p = keras_probabilities(model, test["X"], batch_size)
        results["lstm"] = evaluate_predictions(validation["y"], validation_p, test["y"], test_p, config, data.class_count, validation_metadata=validation, test_metadata=test)
        test_predictions["lstm"] = test_p
        # Early stopping measures significant improvements; the checkpoint keeps
        # the strict minimum. Reload that checkpoint as the evaluation authority.
        reloaded_p = keras_probabilities(tf.keras.models.load_model(staging / "best_model.keras"), validation["X"], batch_size)
        if not np.allclose(reloaded_p, validation_p, rtol=1e-5, atol=1e-6): raise ValueError("Saved checkpoint reload mismatch")
        example = test["X"][:1]
        for _ in range(3): model(example, training=False).numpy()
        timings = []
        for _ in range(config["evaluation"]["latency_repetitions"]):
            start = time.perf_counter_ns()
            model(example, training=False).numpy()
            timings.append((time.perf_counter_ns() - start) / 1e6)
        parameters = model.count_params()
        report = {"schema_version": 1, "experiment_id": output.name, "created_utc": datetime.now(timezone.utc).isoformat(),
                  "dataset_version": data.manifest["dataset_version"], "dataset_directory": str(data.directory),
                  "dataset_hashes": data.hashes, "synthetic_demo": data.synthetic,
                  "config": config, "class_count": data.class_count, "feature_order": scaler.order,
                  "sequence_length": int(example.shape[1]), "class_weights": class_weights,
                  "epochs_completed": len(history_data["loss"]), "best_epoch": int(np.argmin(history_data["val_loss"]) + 1),
                  "training_control": {"stop_reason": "early_stopping" if early_stop.stopped_epoch else "epoch_budget_reached",
                                       "maximum_epochs": config["training"]["epochs"], "learning_rate_schedule": schedule,
                                       "best_epoch_at_budget_boundary": len(history_data["loss"]) == config["training"]["epochs"] and int(np.argmin(history_data["val_loss"])) == len(history_data["loss"]) - 1,
                                       "convergence_guaranteed": False},
                  "input_context": input_context_audit(data.manifest, json.loads((data.directory / "feature_order.json").read_text(encoding="utf-8")), config),
                  "models": results, "threshold_rules": rules.rules,
                  "validation_recommendation": validation_recommendation(results, config, data.class_count),
                  "resources": {"parameters": parameters, "keras_file_bytes": (staging / "best_model.keras").stat().st_size,
                                "float32_weight_bytes_estimate": parameters * 4, "input_tensor_bytes": example.nbytes,
                                "recurrent_state_bytes_lower_bound": 2 * config["model"]["hidden_units"] * config["model"]["num_layers"] * 4,
                                "host_latency_ms": {"median": float(np.median(timings)), "p95": float(np.percentile(timings, 95)), "repetitions": len(timings), "batch_size": 1, "includes_python_call": True},
                                "mcu_ram_estimate": None, "mcu_latency": None, "tflite_size": None},
                  "environment": {"python": platform.python_version(), "system": platform.system(), "tensorflow": tf.__version__, "keras": importlib.metadata.version("keras"), "sklearn": importlib.metadata.version("scikit-learn")},
                  "notes": ["Test labels never select model weights or classification thresholds.", "Synthetic metrics are software fixture results only.", "Window metrics do not measure event detection rate or forecasting lead time."]}
        write_json(staging / "history.json", history_data)
        write_json(staging / "report.json", report)
        write_summary(staging / "report.md", report)
        plot_results(staging, history_data, report, test["y"], test_predictions)
        np.savez_compressed(staging / "test-predictions.npz", y=test["y"], **test_predictions)
        np.savez_compressed(staging / "validation-predictions.npz", y=validation["y"], lstm=validation_p, logistic=baseline.predict(validation["X"]))
        for name in ("scaler.json", "feature_order.json"): shutil.copyfile(data.directory / name, staging / name)
        write_json(staging / "model-integrity.json", {"files": {name: file_hash(staging / name) for name in ("best_model.keras", "logistic.json", "scaler.json", "feature_order.json", "report.json")}})
        staging.rename(output)
        LOGGER.info("Training/evaluation saved: %s; synthetic_demo=%s", output, data.synthetic)
        return output
    finally:
        if staging.exists():
            safe = staging.resolve()
            if safe.parent != output.parent.resolve() or not safe.name.startswith(".training-"): raise RuntimeError("Unsafe staging cleanup")
            shutil.rmtree(safe)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/model.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthetic-demo", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        train(args.dataset, args.config, args.output, synthetic_demo=args.synthetic_demo)
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError) as error:
        LOGGER.error("Training failed: %s", error)
        return 2


if __name__ == "__main__": raise SystemExit(main())
