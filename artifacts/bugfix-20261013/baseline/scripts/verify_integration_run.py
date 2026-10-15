"""Audit trained artifacts, backend state, tamper rejection and full LiteRT replay."""

import argparse
import copy
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from src.embedded.export_tflite import operator_codes
from src.evaluation.decision_policy import select_policy
from src.realtime.inference import InferenceEngine
from src.realtime.replay import replay
from src.utils.config import read_yaml


def verify(run_dir: Path, output: Path):
    if output.exists(): raise FileExistsError("Audit output exists")
    output.mkdir(parents=True)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    bundle = Path(run["stages"]["bundle"]["path"])
    keras = InferenceEngine(bundle, model="lstm")
    model_dir = run_dir / "models" / keras.manifest["model_version"]
    report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    with np.load(Path(report["dataset_directory"]) / "test.npz", allow_pickle=False) as data:
        samples = np.asarray(data["X"][[0, 100, 0]], dtype=np.float32)
    baseline = []
    for sample in samples:
        tensor = sample[None]
        eager = float(keras.model(tensor, training=False).numpy()[0, 0])
        compiled = keras.predict(tensor)["risk_score"]
        np.testing.assert_allclose(compiled, eager, atol=1e-6, rtol=1e-6)
        baseline.append(compiled)
    assert baseline[0] == baseline[2]
    with tempfile.TemporaryDirectory(prefix="lightning-contract-audit-") as temporary:
        corrupt = Path(temporary) / "bundle"
        shutil.copytree(bundle, corrupt)
        with (corrupt / "scaler.json").open("ab") as handle: handle.write(b" ")
        try: InferenceEngine(corrupt, model="logistic")
        except ValueError as error: assert "integrity" in str(error)
        else: raise AssertionError("Tampered scaler accepted")
        shutil.copyfile(bundle / "scaler.json", corrupt / "scaler.json")
        manifest = json.loads((corrupt / "bundle.json").read_text(encoding="utf-8"))
        manifest["configuration"]["pipeline"]["alignment_period_seconds"] *= 2
        (corrupt / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
        try: InferenceEngine(corrupt, model="logistic")
        except ValueError as error: assert "contract" in str(error)
        else: raise AssertionError("Changed preprocessing contract accepted")
    export_dir = Path(run["stages"]["export"]["path"])
    exports = json.loads((export_dir / "export-report.json").read_text(encoding="utf-8"))
    backends = {}
    for kind, item in exports["formats"].items():
        assert item["status"] == "SUCCESS"
        path = Path(item["path"])
        engine = InferenceEngine(bundle, model="tflite", tflite_path=path)
        values = [engine.predict(sample[None])["risk_score"] for sample in samples]
        assert values[0] == values[2], "A/B/A recurrent state leaked"
        if kind == "float32": np.testing.assert_allclose(values, baseline, atol=1e-6, rtol=1e-6)
        backends[kind] = {"A_B_A_stateless": True, "operators_all_subgraphs": operator_codes(path.read_bytes()),
                          "bytes": item["bytes"], "classification_changes_test": item["classification_changes"]}
    calibrated = Path(run["stages"]["calibrated_replay"]["path"])
    policy = json.loads((calibrated / "decision-policy.json").read_text(encoding="utf-8"))
    recalibrated = select_policy(model_dir, Path(report["dataset_directory"]), model="lstm",
                                minimum_recall=report["config"]["evaluation"]["minimum_recall"])
    assert policy["selected"] == recalibrated["selected"]
    settings = copy.deepcopy(read_yaml(Path("configs/integration.yaml"))["replay"])
    settings.update(risk_on_threshold=policy["selected"]["on"], risk_off_threshold=policy["selected"]["off"],
                    minimum_consecutive_detections=policy["selected"]["consecutive"])
    summary = replay(calibrated / "inputs/heldout.synthetic.csv", bundle, settings, output / "litert-replay",
                     model="tflite", tflite_path=Path(exports["formats"]["float32"]["path"]))
    count, max_error = 0, 0.
    with (calibrated / "replay/heldout/timeline.jsonl").open(encoding="utf-8") as left, (output / "litert-replay/timeline.jsonl").open(encoding="utf-8") as right:
        from itertools import zip_longest
        for a, b in zip_longest(left, right):
            assert a is not None and b is not None, "Trace lengths differ"
            a, b = json.loads(a), json.loads(b)
            for key in ("timestamp_ns", "input_status", "available", "decision"):
                assert a[key] == b[key], f"Replay differs: {key}"
            if a["prediction"]:
                error = abs(a["prediction"]["risk_score"] - b["prediction"]["risk_score"])
                assert error < 1e-6
                max_error = max(max_error, error)
            count += 1
    result = {"schema_version": 1, "status": "SUCCESS", "compiled_eager_parity": True,
              "bundle_tamper_rejected": True, "configuration_tamper_rejected": True,
              "validation_policy_reproduced": True, "backends": backends,
              "keras_litert_replay_rows_identical": count, "max_replay_score_error": max_error,
              "litert_replay": summary, "mcu_verified": False, "physical_performance_verified": False}
    (output / "audit.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    run["stages"]["final_audit"] = {"status": "SUCCESS", "path": str(output.resolve())}
    (run_dir / "run.json").write_text(json.dumps(run, indent=2, allow_nan=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.run, args.output)
    print(json.dumps({"status": result["status"], "replay_rows": result["keras_litert_replay_rows_identical"]}))
