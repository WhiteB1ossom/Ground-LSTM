"""Static inference export with actual interpreter checks and explicit failures."""

import argparse
import json
from pathlib import Path
import time
import tempfile
import shutil
import subprocess
import sys
import importlib.metadata

import numpy as np

from src.evaluation.metrics import classification_metrics
from src.training.data import file_hash


def operator_codes(payload: bytes) -> list[str]:
    # OperatorCodes includes nested WHILE subgraphs that interpreter summaries omit.
    from tensorflow.lite.python import schema_py_generated as schema
    names = {value: name for name, value in vars(schema.BuiltinOperator).items() if isinstance(value, int)}
    model = schema.Model.GetRootAsModel(payload, 0)
    result = set()
    for index in range(model.OperatorCodesLength()):
        code = model.OperatorCodes(index)
        builtin = max(code.BuiltinCode(), code.DeprecatedBuiltinCode())
        name = names[builtin]
        if name == "CUSTOM": raise ValueError("Non-builtin custom operator")
        result.add(name)
    return sorted(result)


def run_interpreter(interpreter, X):
    inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
    predictions, timings, saturated = [], [], 0
    for row in X:
        interpreter.reset_all_variables()
        values = row[None, :]
        if np.issubdtype(inp["dtype"], np.integer):
            scale, zero = inp["quantization"]
            if scale <= 0: raise ValueError("Invalid quantization scale")
            values = np.rint(values / scale + zero)
            limits = np.iinfo(inp["dtype"])
            saturated += int(((values < limits.min) | (values > limits.max)).sum())
            values = np.clip(values, limits.min, limits.max).astype(inp["dtype"])
        interpreter.set_tensor(inp["index"], values)
        start = time.perf_counter_ns()
        interpreter.invoke()
        timings.append((time.perf_counter_ns() - start) / 1e6)
        result = interpreter.get_tensor(out["index"]).astype(float)
        if np.issubdtype(out["dtype"], np.integer):
            scale, zero = out["quantization"]
            result = (result - zero) * scale
        predictions.append(result[0])
    result = np.asarray(predictions)
    return result[:, 0] if result.shape[1] == 1 else result, timings, saturated


def export(model_dir: Path, dataset_dir: Path, output: Path, *, representative_count=256) -> dict:
    import tensorflow as tf
    from src.training.train import keras_probabilities
    if output.exists(): raise FileExistsError("Export directory exists")
    if representative_count < 1: raise ValueError("Representative count must be positive")
    output.mkdir(parents=True)
    integrity = json.loads((model_dir / "model-integrity.json").read_text(encoding="utf-8"))
    for name, digest in integrity["files"].items():
        if file_hash(model_dir / name) != digest: raise ValueError("Export model integrity mismatch")
    report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    for name, digest in report["dataset_hashes"].items():
        if file_hash(dataset_dir / name) != digest: raise ValueError("Export dataset integrity mismatch")
    model = tf.keras.models.load_model(model_dir / "best_model.keras")
    original_model = model
    def clone_layer(layer):
        layer_config = layer.get_config()
        if isinstance(layer, tf.keras.layers.LSTM):
            layer_config.update(unroll=True, use_cudnn=False)
        return layer.__class__.from_config(layer_config)
    model = tf.keras.models.clone_model(model, clone_function=clone_layer)
    model.set_weights(original_model.get_weights())
    shape = (1, *model.input_shape[1:])
    # TensorFlow's native Windows filesystem can reject non-ASCII SavedModel
    # paths. Use an owned ASCII staging folder, then copy with Python Unicode IO.
    temporary_root = Path(tempfile.gettempdir()).resolve()
    temporary = Path(tempfile.mkdtemp(prefix="lightning-export-", dir=temporary_root)).resolve()
    if temporary.parent != temporary_root or not str(temporary).isascii():
        raise RuntimeError("TensorFlow export requires an ASCII staging path")
    try:
        saved_model = temporary / "saved_model"
        model.export(saved_model, input_signature=[tf.TensorSpec(shape, tf.float32, name="sensor_sequence")], verbose=False)
        symbolic_saved_model = temporary / "saved_model_symbolic"
        original_model.export(symbolic_saved_model, input_signature=[tf.TensorSpec(shape, tf.float32, name="sensor_sequence")], verbose=False)
        shutil.copytree(saved_model, output / "saved_model")
        restored = tf.saved_model.load(str(saved_model))
        with np.load(dataset_dir / "train.npz", allow_pickle=False) as data: train_X = data["X"]
        # Quantization calibration uses Train only; never use the final test split.
        indices = np.linspace(0, len(train_X) - 1, min(representative_count, len(train_X)), dtype=int)
        np.savez_compressed(temporary / "representative.npz", X=train_X[indices])
        def representative():
            for i in indices: yield [train_X[i:i + 1]]
        with np.load(dataset_dir / "validation.npz", allow_pickle=False) as data: validation = dict(data)
        with np.load(dataset_dir / "test.npz", allow_pickle=False) as data: test = dict(data)
        if not np.allclose(restored.serve(test["X"][:1]).numpy(), model(test["X"][:1], training=False).numpy(), rtol=1e-5, atol=1e-6):
            raise ValueError("SavedModel reload mismatch")
        selection = report["models"]["lstm"]["threshold_selection"]
        threshold = selection.get("selected_threshold")
        baseline = keras_probabilities(original_model, test["X"], 64)
        clone_validation = keras_probabilities(model, validation["X"][:64], 64)
        original_validation = keras_probabilities(original_model, validation["X"][:64], 64)
        if not np.allclose(clone_validation, original_validation, rtol=1e-5, atol=1e-6): raise ValueError("Export unroll changes trained predictions")
        results = {"schema_version": 1, "model_version": report["experiment_id"], "shape": list(shape),
                   "tensorflow": tf.__version__, "litert": importlib.metadata.version("ai-edge-litert"),
                   "conversion_strategy": "compact_float_static_integer_same_trained_weights", "unroll_validation_match": True,
                   "compact_export_verified": True,
                   "representative_split": "train", "representative_indices": indices.tolist(),
                   "synthetic_demo": report["synthetic_demo"], "mcu_verified": False, "saved_model_reload_match": True, "formats": {}}
        for kind in ("float32", "float16", "int8"):
            try:
                worker_output = temporary / f"model-{kind}.tflite"
                conversion_source = saved_model if kind == "int8" else symbolic_saved_model
                worker = subprocess.run([sys.executable, "-m", "src.embedded.convert_worker", "--saved-model", str(conversion_source),
                                         "--representative", str(temporary / "representative.npz"), "--kind", kind, "--output", str(worker_output)],
                                        capture_output=True, timeout=240)
                (output / f"converter-{kind}.log").write_bytes(worker.stdout + worker.stderr)
                if worker.returncode != 0: raise RuntimeError(f"Native converter exit {worker.returncode}; see converter-{kind}.log")
                converted = worker_output.read_bytes()
                path = output / f"model-{kind}.tflite"
                path.write_bytes(converted)
                from ai_edge_litert.interpreter import Interpreter
                interpreter = Interpreter(model_content=converted)
                interpreter.allocate_tensors()
                ops = operator_codes(converted)
                if any(op.startswith("Flex") or op == "CUSTOM" for op in ops): raise ValueError("Non-builtin operator")
                predicted, timings, saturated = run_interpreter(interpreter, test["X"])
                # Repeated-window parity catches accidentally carried recurrent state.
                repeated, _, _ = run_interpreter(interpreter, np.repeat(test["X"][:1], 3, axis=0))
                if not np.allclose(repeated, repeated[0], atol=1e-6): raise ValueError("Stateless repeat parity failed")
                difference = np.abs(predicted - baseline)
                inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
                metrics = classification_metrics(test["y"], predicted, threshold=threshold, class_count=report["class_count"])
                item = {"status": "SUCCESS", "path": str(path.resolve()), "sha256": file_hash(path), "bytes": len(converted),
                        "strategy": "static_unrolled" if kind == "int8" else "compact_symbolic",
                        "operators": ops, "input_dtype": str(inp["dtype"]), "output_dtype": str(out["dtype"]),
                        "input_quantization": list(inp["quantization"]), "output_quantization": list(out["quantization"]),
                        "mean_output_error": float(difference.mean()), "max_output_error": float(difference.max()),
                        "threshold": threshold, "test": metrics, "input_saturations": saturated,
                        "host_latency_ms": {"median": float(np.median(timings)), "p95": float(np.percentile(timings, 95))},
                        "mcu_kernel_verified": False, "stateless_repeat_match": True}
                if report["class_count"] == 2: item["classification_changes"] = int(((predicted >= threshold) != (baseline >= threshold)).sum())
                np.savez_compressed(output / f"predictions-{kind}.npz", y=test["y"], scores=predicted)
                # The file is checked, but allowed performance degradation is external.
                item["deployment_approved"] = False
                results["formats"][kind] = item
            except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired, tf.errors.OpError) as error:
                results["formats"][kind] = {"status": "UNSUPPORTED_OR_FAILED", "error": str(error), "mcu_kernel_verified": False}
        (output / "export-report.json").write_text(json.dumps(results, indent=2, allow_nan=False), encoding="utf-8")
    finally:
        if temporary.resolve().parent != temporary_root or not temporary.name.startswith("lightning-export-"):
            raise RuntimeError("Refusing cleanup outside the owned export staging directory")
        shutil.rmtree(temporary)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.model, args.dataset, args.output)
    print(json.dumps({k: v["status"] for k, v in result["formats"].items()}))
    raise SystemExit(0 if all(v["status"] == "SUCCESS" for v in result["formats"].values()) else 1)
