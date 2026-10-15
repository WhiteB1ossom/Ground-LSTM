"""Training contracts, frozen threshold selection and actual Keras roundtrip."""

import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.evaluation.metrics import classification_metrics, select_threshold
from src.models.baselines import LogisticBaseline, ThresholdBaseline
from src.preprocessing.scaling import FrozenScaler
from src.training.config import load_training_config
from src.training.data import load_dataset

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prepared(tmp_path):
    directory = tmp_path / "prepared"
    directory.mkdir()
    config = load_training_config(ROOT / "configs/model_demo.yaml")
    config["model"].update(sequence_length=4, hidden_units=4)
    config["training"].update(epochs=2, batch_size=8)
    config["evaluation"]["latency_repetitions"] = 2
    order = ["voltage__current_value", "voltage__missing"]
    scaler = FrozenScaler(order, "standard").fit(np.array([[0., 0.], [2., 0.]]), split="train")
    scaler.save(directory / "scaler.json")
    (directory / "feature_order.json").write_text(json.dumps({"feature_order": order, "sequence_length": 4}), encoding="utf-8")
    manifest = {"schema_version": 1, "scaler_fit_split": "train", "label_status": "LABELED",
                "supervised_training_ready": False, "dataset_version": "software-test", "feature_order": order, "inputs": [],
                "configuration": {"input": {"acquisition_kind": "synthetic", "source": "monitoring"},
                                  "pipeline": {"labeling": {"mapping": {"normal": 0, "risk": 1}, "mode": "binary"}}},
                "sensors": [{"name": "voltage", "threshold": None, "enabled": True}]}
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for index, split in enumerate(("train", "validation", "test")):
        y = np.tile([0, 1], 12).astype(np.int64)
        X = np.zeros((len(y), 4, 2), dtype=np.float32)
        X[:, :, 0] = (y * 2 - 1)[:, None]
        times = np.arange(len(y)) + index * 1000
        np.savez_compressed(directory / f"{split}.npz", X=X, y=y, feature_order=order,
                            event_id=np.repeat(split, len(y)), device_id=np.repeat("device", len(y)),
                            start_timestamp=times, end_timestamp=times + 3, target_timestamp=times + 4,
                            source=np.repeat("monitoring", len(y)), acquisition_kind=np.repeat("synthetic", len(y)))
    config_path = tmp_path / "model.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return directory, config, config_path


def rewrite_npz(path, **updates):
    with np.load(path, allow_pickle=False) as data: values = dict(data)
    values.update(updates)
    np.savez_compressed(path, **values)


def test_synthetic_requires_both_opt_ins(prepared):
    directory, config, _ = prepared
    with pytest.raises(ValueError, match="Synthetic"): load_dataset(directory, config)
    config["training"]["allow_synthetic_demo"] = False
    with pytest.raises(ValueError, match="Synthetic"): load_dataset(directory, config, synthetic_demo=True)


@pytest.mark.parametrize("corruption", ["unlabeled", "event_leak", "order", "nan", "provenance", "sequence", "mapping"])
def test_dataset_rejects_invalid_contract(prepared, corruption):
    directory, config, _ = prepared
    if corruption == "unlabeled": rewrite_npz(directory / "test.npz", y=np.full(24, -1, dtype=int))
    elif corruption == "event_leak": rewrite_npz(directory / "test.npz", event_id=np.repeat("train", 24))
    elif corruption == "order": rewrite_npz(directory / "test.npz", feature_order=["other", "voltage__missing"])
    elif corruption == "nan": rewrite_npz(directory / "test.npz", X=np.full((24, 4, 2), np.nan))
    elif corruption == "provenance": rewrite_npz(directory / "test.npz", acquisition_kind=np.repeat("field", 24))
    elif corruption == "sequence": config["model"]["sequence_length"] = 8
    else: config["labeling"]["ground_truth_mapping"] = {"normal": 1, "risk": 0}
    with pytest.raises(ValueError): load_dataset(directory, config, synthetic_demo=True)


def test_partial_labels_rejected(prepared):
    directory, config, _ = prepared
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["label_status"] = "PARTIALLY_LABELED"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="labeled"): load_dataset(directory, config, synthetic_demo=True)


def test_metrics_count_missed_risk_and_false_alarm():
    scores = classification_metrics(np.array([0, 0, 1, 1]), np.array([.1, .8, .3, .9]), threshold=.5, class_count=2)
    assert scores["confusion_matrix"] == [[1, 1], [1, 1]]
    assert scores["false_negatives"] == scores["false_positives"] == 1
    assert scores["precision"] == scores["recall"] == scores["f1"] == .5


def test_pr_auc_single_class_is_undefined():
    scores = classification_metrics(np.zeros(2, dtype=int), np.array([.1, .2]), threshold=.5, class_count=2)
    assert scores["risk_pr_auc_trapezoidal"] is None


def test_multiclass_macro_includes_absent_classes():
    result = classification_metrics(np.array([0, 1]), np.array([[1., 0, 0], [0, 1., 0]]), threshold=None, class_count=3)
    assert result["f1"] == pytest.approx(2 / 3)
    assert len(result["confusion_matrix"]) == 3


def test_threshold_selection_refuses_test_labels():
    with pytest.raises(ValueError, match="validation"):
        select_threshold(np.array([0, 1]), np.array([.1, .9]), {}, split="test")


def test_recall_target_and_unreachable_target():
    settings = {"validation_threshold_candidates": [.3, .5, .7], "threshold_objective": "recall_then_f1", "minimum_recall": 1.}
    selected = select_threshold(np.array([0, 1, 1]), np.array([.2, .4, .8]), settings, split="validation")
    assert selected["selected_threshold"] == .3
    assert selected["recall_target_met"] is True
    settings["validation_threshold_candidates"] = [.5, .7]
    selected = select_threshold(np.array([0, 1, 1]), np.array([.2, .4, .8]), settings, split="validation")
    assert selected["recall_target_met"] is False


def test_logistic_json_roundtrip(prepared, tmp_path):
    directory, config, _ = prepared
    part = load_dataset(directory, config, synthetic_demo=True).splits["train"]
    baseline = LogisticBaseline().fit(part["X"], part["y"], max_iter=1000, class_weight=None, seed=42)
    path = tmp_path / "logistic.json"
    baseline.save(path)
    np.testing.assert_allclose(baseline.predict(part["X"]), LogisticBaseline.load(path).predict(part["X"]))
    assert ((baseline.predict(part["X"]) >= .5) == part["y"]).all()


def test_threshold_rules_use_physical_units_and_abstain(prepared):
    directory, config, _ = prepared
    data = load_dataset(directory, config, synthetic_demo=True)
    scaler = FrozenScaler.load(directory / "scaler.json")
    disabled = ThresholdBaseline(data.manifest, scaler, [])
    assert disabled.rules == []
    with pytest.raises(ValueError, match="disabled"): disabled.predict(data.splits["test"]["X"])
    baseline = ThresholdBaseline(data.manifest, scaler, [{"sensor": "voltage", "operator": "ge", "value": 1.5}])
    X = data.splits["test"]["X"].copy()
    X[0, -1, 1] = 1
    p = baseline.predict(X)
    assert np.isnan(p[0])
    np.testing.assert_array_equal(p[1:], data.splits["test"]["y"][1:])


@pytest.mark.parametrize("section,key,value", [("model", "bidirectional", True), ("training", "learning_rate", -1), ("evaluation", "minimum_recall", True), ("labeling", "ground_truth_mapping", {"normal": False, "risk": True})])
def test_config_rejects_invalid_values(prepared, section, key, value):
    _, config, path = prepared
    config[section][key] = value
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError): load_training_config(path)


def test_actual_training_reload_and_integrity(prepared, tmp_path):
    from src.training.train import train
    from src.evaluation.evaluate import evaluate
    directory, _, config_path = prepared
    experiment = train(directory, config_path, tmp_path / "experiment", synthetic_demo=True)
    original = json.loads((experiment / "report.json").read_text())
    reloaded = evaluate(experiment, directory, tmp_path / "evaluation.json")
    assert reloaded["thresholds_retuned"] is False
    assert reloaded["models"] == original["models"]
    assert original["epochs_completed"] == 2
    assert original["resources"]["parameters"] > 0
    with pytest.raises(FileExistsError): train(directory, config_path, experiment, synthetic_demo=True)
    with pytest.raises(FileExistsError): evaluate(experiment, directory, tmp_path / "evaluation.json")
    rewrite_npz(directory / "test.npz", y=1 - np.tile([0, 1], 12))
    with pytest.raises(ValueError, match="Dataset changed"): evaluate(experiment, directory, tmp_path / "changed.json")
    (experiment / "logistic.json").write_text("{}")
    with pytest.raises(ValueError, match="artifact changed"): evaluate(experiment, directory, tmp_path / "tampered.json")


def test_multiclass_training_and_reload(prepared, tmp_path):
    from src.training.train import train
    from src.evaluation.evaluate import evaluate
    directory, config, config_path = prepared
    mapping = {"normal": 0, "approaching": 1, "event": 2}
    config["labeling"].update(mode="multiclass", ground_truth_mapping=mapping, multiclass_semantics_confirmed=True)
    config["training"]["epochs"] = 1
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["configuration"]["pipeline"]["labeling"] = {"mode": "multiclass", "mapping": mapping}
    manifest_path.write_text(json.dumps(manifest))
    for split in ("train", "validation", "test"):
        y = np.tile([0, 1, 2], 8)
        X = np.zeros((24, 4, 2), dtype=np.float32)
        X[:, :, 0] = (y - 1)[:, None]
        rewrite_npz(directory / f"{split}.npz", y=y, X=X)
    experiment = train(directory, config_path, tmp_path / "multi", synthetic_demo=True)
    original = json.loads((experiment / "report.json").read_text())
    replay = evaluate(experiment, directory, tmp_path / "multi-evaluation.json")
    assert replay["models"] == original["models"]
    assert original["models"]["lstm"]["test"]["averaging"] == "macro"
    assert len(original["models"]["lstm"]["test"]["confusion_matrix"]) == 3


def test_adaptive_learning_rate_and_early_stop(prepared, tmp_path):
    from src.training.train import train
    from src.evaluation.evaluate import evaluate
    directory, config, path = prepared
    # Force a plateau under the significant-improvement definition while
    # allowing the checkpoint to retain smaller strict loss improvements.
    config["training"].update(epochs=10, early_stopping_patience=3, early_stopping_min_delta=100.)
    config["training"]["lr_schedule"]["patience"] = 1
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    experiment = train(directory, path, tmp_path / "adaptive", synthetic_demo=True)
    report = json.loads((experiment / "report.json").read_text())
    history = json.loads((experiment / "history.json").read_text())
    assert report["training_control"]["stop_reason"] == "early_stopping"
    assert report["epochs_completed"] == 4
    assert min(history["learning_rate"]) < history["learning_rate"][0]
    assert evaluate(experiment, directory, tmp_path / "adaptive-reloaded.json")["models"] == report["models"]
