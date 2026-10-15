"""Calibrate on validation and finish a completed training run without retraining."""

import argparse
import copy
import json
from pathlib import Path

import pandas as pd
import yaml

from src.evaluation.decision_policy import select_policy
from src.realtime.replay import replay
from src.utils.config import read_yaml


def finish(run_dir: Path, config_path=Path("configs/integration.yaml")):
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    settings = read_yaml(config_path)
    bundle_dir = Path(run["stages"]["bundle"]["path"])
    bundle = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
    model_dir = run_dir / "models" / bundle["model_version"]
    recommended = bundle["recommendation"]["model"]
    chosen = recommended if recommended in {"logistic", "lstm"} else "lstm"
    model_report = json.loads((model_dir / "report.json").read_text(encoding="utf-8"))
    policy = select_policy(model_dir, Path(model_report["dataset_directory"]), model=chosen, minimum_recall=model_report["config"]["evaluation"]["minimum_recall"])
    output = run_dir / "calibrated"
    suffix = 2
    while output.exists():
        output = run_dir / f"calibrated-{suffix}"
        suffix += 1
    output.mkdir()
    (output / "decision-policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
    replay_settings = copy.deepcopy(settings["replay"])
    replay_settings.update(risk_on_threshold=policy["selected"]["on"], risk_off_threshold=policy["selected"]["off"],
                           minimum_consecutive_detections=policy["selected"]["consecutive"])
    (output / "selected-replay.yaml").write_text(yaml.safe_dump({"schema_version": 1, "replay": replay_settings}), encoding="utf-8")
    raw = Path(run["stages"]["scenarios"]["path"])
    # A fresh chronological holdout session slice; labels never drive live resets.
    frame = pd.read_csv(raw / "training.synthetic.csv", keep_default_na=False)
    test_input = output / "inputs" / "heldout.synthetic.csv"
    test_input.parent.mkdir()
    frame.iloc[28800:].to_csv(test_input, index=False)
    summaries = {}
    for name, path in (("heldout", test_input), ("faults", raw / "faults.synthetic.csv"), ("long-normal", raw / "normal-hour.synthetic.csv")):
        summaries[name] = replay(path, bundle_dir, replay_settings, output / "replay" / name, model=chosen, speed="max")
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    run["stages"]["calibrated_replay"] = {"status": "SUCCESS" if all(v["status"] == "SUCCESS" for v in summaries.values()) else "DEGRADED", "model": chosen, "path": str(output.resolve()),
                                           "decision_policy_split": "validation", "summaries": summaries}
    (run_dir / "run.json").write_text(json.dumps(run, indent=2, allow_nan=False), encoding="utf-8")
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({k: v["evaluation"] for k, v in finish(args.run).items()}))
