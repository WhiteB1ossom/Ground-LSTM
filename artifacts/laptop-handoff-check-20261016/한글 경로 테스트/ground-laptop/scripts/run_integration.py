"""One versioned software run: scenarios, datasets, training, export and replay."""

import argparse
import copy
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

import yaml

from scripts.prepare_integration_data import prepare
from src.dataset.build import build_dataset
from src.realtime.inference import create_bundle
from src.training.train import train
from src.utils.config import load_config, read_yaml

LOGGER = logging.getLogger(__name__)


def merge(base, overrides):
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if key == "extends": continue
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def run(output: Path, config_path: Path):
    if output.exists(): raise FileExistsError("Run exists; use a new output directory")
    output = output.resolve()
    output.mkdir(parents=True)
    settings = read_yaml(config_path)
    if settings.get("purpose") != "SOFTWARE_INTEGRATION_NOT_PHYSICAL_PERFORMANCE": raise ValueError("Explicit software purpose required")
    root = config_path.resolve().parent
    config = load_config(root / settings["preprocessing_config"])
    raw = Path("data/raw/integration") / output.name
    status = {"schema_version": 1, "run_id": output.name, "synthetic_demo": True, "settings": settings, "stages": {}}
    def checkpoint(): (output / "run.json").write_text(json.dumps(status, indent=2, allow_nan=False), encoding="utf-8")
    try:
        scenario_report = prepare(raw, root / settings["preprocessing_config"])
        status["stages"]["scenarios"] = {"status": "SUCCESS", "path": str(raw.resolve()), "rows": scenario_report["total_scenario_rows"]}
        checkpoint()
        dataset = build_dataset(config, [raw / "training.synthetic.csv"], output=output / "dataset")
        status["stages"]["dataset"] = {"status": "SUCCESS", "path": str(dataset)}
        checkpoint()
        base = merge(read_yaml(root / settings["model_base_config"]), read_yaml(root / settings["model_overrides_config"]))
        candidates = []
        for experiment in settings["experiments"]:
            candidate = copy.deepcopy(base)
            candidate["seed"] = experiment["seed"]
            candidate["model"]["hidden_units"] = experiment["hidden_units"]
            candidate_path = output / (experiment["name"] + ".yaml")
            candidate_path.write_text(yaml.safe_dump(candidate), encoding="utf-8")
            directory = train(dataset, candidate_path, output / "models" / experiment["name"], synthetic_demo=True)
            report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
            candidates.append({"name": experiment["name"], "directory": str(directory), "hidden_units": experiment["hidden_units"],
                               "seed": experiment["seed"], "validation": report["models"]["lstm"]["validation"], "resources": report["resources"]})
            status["stages"][experiment["name"]] = {"status": "SUCCESS", "path": str(directory)}
            checkpoint()
        selected = max(candidates, key=lambda c: (c["validation"]["recall"] >= base["evaluation"]["minimum_recall"],
                                                 c["validation"]["f1"], c["validation"]["recall"], -c["resources"]["parameters"]))
        selection = {"selection_split": "validation", "selected_lstm": selected["name"], "candidates": candidates,
                     "deployment_approved": False, "note": "Test never ranks experiments; actual MCU/physical validation pending."}
        (output / "experiment-comparison.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
        model_dir = Path(selected["directory"])
        create_bundle(model_dir, dataset, output / "bundle")
        status["stages"]["bundle"] = {"status": "SUCCESS", "path": str(output / "bundle")}
        checkpoint()
        from scripts.run_feature_ablation import ablate
        ablate(output, config_path)
        from scripts.resume_integration import resume
        completed = resume(output, config_path)
        if completed["status"] != "PC_COMPLETE_HARDWARE_PENDING":
            raise RuntimeError("Integration verification incomplete; inspect run.json stages")
    except Exception as error:
        status = json.loads((output / "run.json").read_text(encoding="utf-8")) if (output / "run.json").is_file() else status
        status.update(status="FAILED", error=f"{type(error).__name__}: {error}")
        checkpoint()
        raise
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/integration.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(run(args.output, args.config))
