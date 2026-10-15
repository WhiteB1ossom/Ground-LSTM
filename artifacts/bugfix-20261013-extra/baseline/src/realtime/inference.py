"""Hash-checked inference bundles and fixed-shape, stateless prediction."""

import json
from pathlib import Path
import shutil
import time

import numpy as np

from src.models.baselines import LogisticBaseline
from src.preprocessing.scaling import FrozenScaler
from src.training.data import file_hash


def create_bundle(model_dir: Path, dataset_dir: Path, output: Path) -> Path:
    output = output.resolve()
    if output.exists(): raise FileExistsError("Bundle already exists")
    report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    integrity = json.loads((model_dir / "model-integrity.json").read_text(encoding="utf-8"))
    required_models = {"best_model.keras", "logistic.json", "scaler.json", "feature_order.json", "report.json"}
    if not required_models.issubset(integrity.get("files", {})): raise ValueError("Incomplete model integrity contract")
    for name, digest in integrity["files"].items():
        path = (model_dir / name).resolve()
        if path.parent != model_dir.resolve() or file_hash(path) != digest: raise ValueError("Model integrity mismatch")
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["dataset_version"] != report["dataset_version"]: raise ValueError("Bundle dataset mismatch")
    for name, digest in report["dataset_hashes"].items():
        path = (dataset_dir / name).resolve()
        if path.parent != dataset_dir.resolve() or file_hash(path) != digest: raise ValueError("Dataset integrity mismatch")
    output.mkdir(parents=True)
    names = ["best_model.keras", "logistic.json", "scaler.json", "feature_order.json", "report.json"]
    for name in names: shutil.copyfile(model_dir / name, output / name)
    shutil.copyfile(dataset_dir / "manifest.json", output / "dataset-manifest.json")
    names.append("dataset-manifest.json")
    bundle = {"schema_version": 1, "model_version": report["experiment_id"], "dataset_version": report["dataset_version"],
              "shape": [1, report["sequence_length"], len(report["feature_order"])], "feature_order": report["feature_order"],
              "class_count": report["class_count"], "synthetic_demo": report["synthetic_demo"],
              "configuration": manifest["configuration"], "sensors": manifest["sensors"],
              "models": report["models"], "recommendation": report["validation_recommendation"],
              "files": {n: file_hash(output / n) for n in names}}
    (output / "bundle.json").write_text(json.dumps(bundle, indent=2, allow_nan=False), encoding="utf-8")
    return output


class InferenceEngine:
    def __init__(self, bundle_dir: Path, *, model="lstm", tflite_path: Path | None = None):
        self.directory, self.kind = bundle_dir.resolve(), model
        self.manifest = json.loads((self.directory / "bundle.json").read_text(encoding="utf-8"))
        if self.manifest.get("schema_version") != 1: raise ValueError("Invalid bundle schema")
        required = {"best_model.keras", "logistic.json", "scaler.json", "feature_order.json", "report.json", "dataset-manifest.json"}
        if not required.issubset(self.manifest.get("files", {})): raise ValueError("Incomplete bundle integrity contract")
        for name, digest in self.manifest["files"].items():
            path = (self.directory / name).resolve()
            if path.parent != self.directory or file_hash(path) != digest: raise ValueError("Bundle integrity mismatch")
        report = json.loads((self.directory / "report.json").read_text(encoding="utf-8"))
        dataset = json.loads((self.directory / "dataset-manifest.json").read_text(encoding="utf-8"))
        expected = {"configuration": dataset["configuration"], "sensors": dataset["sensors"],
                    "dataset_version": report["dataset_version"], "feature_order": report["feature_order"],
                    "shape": [1, report["sequence_length"], len(report["feature_order"])], "models": report["models"],
                    "class_count": report["class_count"], "synthetic_demo": report["synthetic_demo"],
                    "model_version": report["experiment_id"], "recommendation": report["validation_recommendation"]}
        if any(self.manifest.get(k) != v for k, v in expected.items()): raise ValueError("Bundle manifest contract mismatch")
        source_model = "lstm" if model == "tflite" else model
        self.threshold = self.manifest["models"][source_model]["threshold_selection"].get("selected_threshold", .5)
        self.scaler = FrozenScaler.load(self.directory / "scaler.json")
        contract = json.loads((self.directory / "feature_order.json").read_text(encoding="utf-8"))
        self.shape = tuple(self.manifest["shape"])
        if self.scaler.order != self.manifest["feature_order"] or contract["feature_order"] != self.scaler.order or self.shape != (1, contract["sequence_length"], len(self.scaler.order)):
            raise ValueError("Bundle input contract mismatch")
        if model == "logistic": self.model = LogisticBaseline.load(self.directory / "logistic.json")
        elif model == "lstm":
            import tensorflow as tf
            self.model = tf.keras.models.load_model(self.directory / "best_model.keras")
            if tuple(self.model.input_shape[1:]) != self.shape[1:]: raise ValueError("Keras input shape mismatch")
            self.predict_fn = tf.function(lambda x: self.model(x, training=False),
                                          input_signature=[tf.TensorSpec(self.shape, tf.float32)])
            self.predict_fn(tf.zeros(self.shape, dtype=tf.float32)).numpy()
        elif model == "tflite":
            from ai_edge_litert.interpreter import Interpreter
            if tflite_path is None: raise ValueError("LiteRT model path required")
            export_report = json.loads((tflite_path.parent / "export-report.json").read_text(encoding="utf-8"))
            matched = [v for v in export_report["formats"].values() if v.get("status") == "SUCCESS" and Path(v["path"]).resolve() == tflite_path.resolve()]
            if export_report["model_version"] != self.manifest["model_version"] or not matched or file_hash(tflite_path) != matched[0]["sha256"]:
                raise ValueError("LiteRT provenance/integrity mismatch")
            self.model = Interpreter(model_content=tflite_path.read_bytes())
            self.model.allocate_tensors()
            self.input = self.model.get_input_details()[0]
            self.output = self.model.get_output_details()[0]
            if tuple(self.input["shape"]) != self.shape: raise ValueError("LiteRT input shape mismatch")
        else: raise ValueError("Unknown model backend")

    def predict(self, tensor: np.ndarray) -> dict:
        if tensor.shape != self.shape or tensor.dtype != np.float32 or not np.isfinite(tensor).all():
            raise ValueError("Inference input contract mismatch")
        start = time.perf_counter_ns()
        saturation = 0
        if self.kind == "logistic": values = np.asarray(self.model.predict(tensor)).reshape(-1)
        elif self.kind == "lstm": values = self.predict_fn(tensor).numpy().reshape(-1)
        else:
            self.model.reset_all_variables()
            data = tensor
            if np.issubdtype(self.input["dtype"], np.integer):
                scale, zero = self.input["quantization"]
                if scale <= 0: raise ValueError("Invalid input quantization scale")
                limits = np.iinfo(self.input["dtype"])
                quantized = np.rint(tensor / scale + zero)
                saturation = int(((quantized < limits.min) | (quantized > limits.max)).sum())
                data = np.clip(quantized, limits.min, limits.max).astype(self.input["dtype"])
            self.model.set_tensor(self.input["index"], data)
            self.model.invoke()
            values = self.model.get_tensor(self.output["index"]).reshape(-1).astype(float)
            if np.issubdtype(self.output["dtype"], np.integer):
                scale, zero = self.output["quantization"]
                if scale <= 0: raise ValueError("Invalid output quantization scale")
                values = (values - zero) * scale
        if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any(): raise ValueError("Invalid model output")
        if self.manifest["class_count"] == 2:
            if len(values) != 1: raise ValueError("Binary output shape mismatch")
            score, predicted = float(values[0]), int(values[0] >= self.threshold)
        else:
            if len(values) != self.manifest["class_count"] or not np.isclose(values.sum(), 1, atol=0.02): raise ValueError("Multiclass output mismatch")
            score, predicted = float(values[1:].sum()), int(values.argmax())
        return {"risk_score": score, "predicted_class": predicted, "model_version": self.manifest["model_version"],
                "inference_ms": (time.perf_counter_ns() - start) / 1e6, "quantization_saturation": saturation}
