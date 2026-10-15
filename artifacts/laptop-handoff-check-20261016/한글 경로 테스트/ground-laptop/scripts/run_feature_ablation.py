"""Predeclared fast-input ablation, selected only with validation metrics."""

import argparse
import copy
from dataclasses import replace, asdict
import json
from pathlib import Path

import yaml

from src.dataset.build import build_dataset
from src.realtime.inference import create_bundle
from src.training.config import load_training_config
from src.training.train import train
from src.utils.config import load_config, read_yaml


def ablate(run_dir: Path, config_path=Path("configs/integration.yaml")):
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    raw = Path(state["stages"]["scenarios"]["path"])
    options = read_yaml(config_path)
    config_root = config_path.resolve().parent
    base = load_config(config_root / options["preprocessing_config"])
    sensors = tuple(replace(s, enabled=s.group == "fast") for s in base.sensors)
    config = replace(base, sensors=sensors, settings=copy.deepcopy(base.settings))
    recipe_dir = run_dir / "ablation-recipe"
    if recipe_dir.exists(): raise FileExistsError("Ablation already exists")
    recipe_dir.mkdir()
    sensor_path = (recipe_dir / "sensors.yaml").resolve()
    sensor_path.write_text(yaml.safe_dump({"schema_version": 1, "sensors": [asdict(s) for s in sensors]}), encoding="utf-8")
    config.settings["sensors_config"] = str(sensor_path)
    (recipe_dir / "preprocessing.yaml").write_text(yaml.safe_dump(config.settings), encoding="utf-8")
    dataset = build_dataset(config, [raw / "training.synthetic.csv"], output=run_dir / "dataset-fast-only")
    training = load_training_config(config_root / options["model_overrides_config"])
    model_config = recipe_dir / "model.yaml"
    model_config.write_text(yaml.safe_dump(training), encoding="utf-8")
    model_dir = train(dataset, model_config, run_dir / "models/lstm16-fast-only", synthetic_demo=True)
    report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    comparison_path = run_dir / "experiment-comparison.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["candidates"].append({"name": model_dir.name, "directory": str(model_dir), "hidden_units": 16, "seed": 42,
                                     "feature_count": len(report["feature_order"]), "dataset_directory": str(dataset),
                                     "validation": report["models"]["lstm"]["validation"], "resources": report["resources"]})
    selected = max(comparison["candidates"], key=lambda c: (c["validation"]["recall"] >= .9, c["validation"]["f1"],
                                                          c["validation"]["recall"], -c["resources"]["parameters"]))
    comparison["selected_lstm"] = selected["name"]
    comparison["note"] = "Hidden/seed and fast-only ablation selected only on validation; no physical/MCU approval."
    comparison_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    selected_model = Path(selected["directory"])
    selected_report = json.loads((selected_model / "report.json").read_text(encoding="utf-8"))
    selected_dataset = Path(selected_report["dataset_directory"])
    create_bundle(selected_model, selected_dataset, run_dir / "bundle-final")
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    state["stages"]["feature_ablation"] = {"status": "SUCCESS", "path": str(model_dir), "input_features": len(report["feature_order"])}
    state["stages"]["bundle"] = {"status": "SUCCESS", "path": str((run_dir / "bundle-final").resolve())}
    (run_dir / "run.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(ablate(args.run)["selected_lstm"])
