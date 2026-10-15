"""Train/evaluate all-sensor server models with separate degradation and surge targets."""

import argparse
from copy import deepcopy
from dataclasses import replace
import gc
import json
import logging
from pathlib import Path

import pandas as pd
import yaml

from scripts.prepare_equipment_data import prepare
from src.dataset.build import build_dataset
from src.evaluation.decision_policy import select_policy
from src.realtime.inference import create_bundle
from src.realtime.replay import replay
from src.training.train import train
from src.utils.config import load_config, read_yaml

LOGGER = logging.getLogger(__name__)


def run(output: Path, config_path: Path):
    options = read_yaml(config_path)
    if options.get("purpose") != "SERVER_SOFTWARE_EQUIPMENT_REVIEW_NOT_CERTIFIED_DIAGNOSIS" or options.get("deployment_target") != "server":
        raise ValueError("Explicit advisory server purpose required")
    if options["selection"] != {"split": "validation", "metric": "f1", "size_penalty": False, "mcu_gate": False}:
        raise ValueError("Server model selection must use validation, without MCU/size filtering")
    if output.exists(): raise FileExistsError("Server run exists; use a new output")
    output = output.resolve()
    output.mkdir(parents=True)
    state = {"schema_version": 1, "status": "RUNNING", "deployment_target": "server", "synthetic_demo": True,
             "physical_validation": False, "options": options, "stages": {}}
    def checkpoint(): (output / "run.json").write_text(json.dumps(state, indent=2, allow_nan=False), encoding="utf-8")
    checkpoint()
    try:
        base = load_config(config_path.resolve().parent / options["preprocessing_config"])
        base = replace(base, settings=deepcopy(base.settings))
        base.settings["pipeline"]["equipment_features"]["input_voltage_reference"] = options["synthetic"]["input_voltage_reference"]
        raw = Path("data/raw/equipment-server") / output.name
        frame, scenarios = prepare(raw, base, options)
        state["stages"]["scenarios"] = {"status": "SUCCESS", "path": str(raw.resolve()), "rows": scenarios["rows"], "sessions": scenarios["sessions"]}
        recipe = output / "recipe"
        recipe.mkdir()
        (recipe / "preprocessing.yaml").write_text(yaml.safe_dump(base.settings), encoding="utf-8")
        test_sessions = {s["session_id"] for s in scenarios["session_index"] if s["split"] == "test"}
        heldout = frame.loc[frame["session_id"].isin(test_sessions)].copy()
        heldout.to_csv(raw / "heldout.synthetic.csv", index=False)
        manifest = {"schema_version": 1, "deployment_target": "server", "synthetic_demo": True,
                    "criteria_provenance": options["criteria_provenance"], "tasks": {}}
        checkpoint()
        training_base = read_yaml(config_path.resolve().parent / options["model_base_config"])
        training_base["training"].update(options["training"])
        training_base["model"]["sequence_length"] = base.settings["pipeline"]["windows"]["sequence_length"]
        training_base["input_contract"] = {"minimum_context_seconds": 6.4, "require_slow_sensor_age": True}
        for task in ("degradation", "surge"):
            task_dir = output / task
            task_dir.mkdir()
            LOGGER.info("Building %s dataset with all ten sensors", task)
            dataset = build_dataset(base, [raw / (task + ".synthetic.csv")], output=task_dir / "dataset")
            state["stages"][task] = {"status": "TRAINING", "dataset": str(dataset), "candidates": []}
            checkpoint()
            candidates = []
            for experiment in options["experiments"]:
                name = experiment["name"]
                if not name or Path(name).name != name or name in {".", ".."}: raise ValueError("Invalid experiment name")
                candidate = deepcopy(training_base)
                candidate["seed"] = experiment["seed"]
                candidate["model"]["hidden_units"] = experiment["hidden_units"]
                candidate["baseline"]["threshold_rules"] = options["replay"]["rules"] if task == "degradation" else []
                model_config = task_dir / (name + ".yaml")
                model_config.write_text(yaml.safe_dump(candidate), encoding="utf-8")
                LOGGER.info("Training %s/%s", task, name)
                model_dir = train(dataset, model_config, task_dir / "models" / name, synthetic_demo=True)
                report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
                metric = report["models"]["lstm"]["validation"]
                candidate_result = {"name": name, "directory": str(model_dir), "validation": metric, "parameters": report["resources"]["parameters"],
                                    "epochs_completed": report["epochs_completed"], "best_epoch": report["best_epoch"]}
                candidates.append(candidate_result)
                state["stages"][task]["candidates"].append(candidate_result)
                checkpoint()
                import tensorflow as tf
                tf.keras.backend.clear_session()
                gc.collect()
            selected = max(candidates, key=lambda c: (c["validation"]["recall"] >= training_base["evaluation"]["minimum_recall"],
                                                      c["validation"]["f1"], c["validation"]["recall"], -c["validation"]["false_positives"]))
            comparison = {"selection_split": "validation", "selected": selected["name"], "size_penalty": False,
                          "mcu_feasibility_gate": False, "candidates": candidates, "test_used_for_ranking": False}
            (task_dir / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
            selected_dir = Path(selected["directory"])
            create_bundle(selected_dir, dataset, task_dir / "bundle")
            policy = select_policy(selected_dir, dataset, model="lstm", minimum_recall=training_base["evaluation"]["minimum_recall"])
            (task_dir / "decision-policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
            settings = deepcopy(options["replay"])
            settings.update(risk_on_threshold=policy["selected"]["on"], risk_off_threshold=policy["selected"]["off"],
                            minimum_consecutive_detections=policy["selected"]["consecutive"])
            if task == "surge": settings["rules"] = []
            (task_dir / "replay-selected.yaml").write_text(yaml.safe_dump({"schema_version": 1, "replay": settings}), encoding="utf-8")
            test_view = heldout.copy()
            test_view["ground_truth"] = test_view[task + "_truth"]
            test_input = raw / (task + ".heldout.synthetic.csv")
            test_view.to_csv(test_input, index=False)
            LOGGER.info("Replaying held-out %s input", task)
            summary = replay(test_input, task_dir / "bundle", settings, task_dir / "heldout-replay", model="lstm")
            if summary["status"] != "SUCCESS": raise RuntimeError("Held-out replay degraded: " + task)
            state["stages"][task].update(status="SUCCESS", selected=selected["name"], test_replay=summary)
            manifest["tasks"][task] = {"bundle": f"{task}/bundle", "replay_config": f"{task}/replay-selected.yaml",
                                       "meaning": "equipment_review_not_confirmed_failure" if task == "degradation" else "surge_activity_not_lightning_confirmation"}
            checkpoint()
            tf.keras.backend.clear_session()
            gc.collect()
        (output / "server-models.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        state.update(status="SERVER_SOFTWARE_COMPLETE_PHYSICAL_VALIDATION_PENDING", heldout_input=str((raw / "heldout.synthetic.csv").resolve()))
        checkpoint()
    except Exception as error:
        state.update(status="FAILED", error=f"{type(error).__name__}: {error}")
        checkpoint()
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/equipment_server.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(run(args.output, args.config))


if __name__ == "__main__": main()
