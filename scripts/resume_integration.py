"""Finish trained models after an export/runtime failure without overwriting evidence."""

import argparse
import json
from pathlib import Path

from src.embedded.export_tflite import export
from src.embedded.resources import resource_report
from scripts.finalize_integration_run import finish
from src.utils.config import read_yaml


def resume(run_dir: Path, config_path=Path("configs/integration.yaml")):
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    settings = read_yaml(config_path)
    selected = json.loads((run_dir / "experiment-comparison.json").read_text(encoding="utf-8"))["selected_lstm"]
    selected_report = json.loads((run_dir / "models" / selected / "report.json").read_text(encoding="utf-8"))
    dataset = Path(selected_report["dataset_directory"])
    bundle_dir = run_dir / "bundle-final" if (run_dir / "bundle-final").is_dir() else run_dir / "bundle"
    state["stages"]["bundle"] = {"status": "SUCCESS", "path": str(bundle_dir.resolve())}
    if state.get("error"): state.setdefault("recovery_history", []).append(state["error"])
    export_dir = run_dir / "export-verified"
    suffix = 2
    while export_dir.exists() and (not (export_dir / "export-report.json").is_file() or json.loads((export_dir / "export-report.json").read_text(encoding="utf-8"))["model_version"] != selected or json.loads((export_dir / "export-report.json").read_text(encoding="utf-8")).get("compact_export_verified") is not True):
        export_dir = run_dir / f"export-verified-{suffix}"
        suffix += 1
    if export_dir.exists():
        exported = json.loads((export_dir / "export-report.json").read_text(encoding="utf-8"))
    else: exported = export(run_dir / "models" / selected, dataset, export_dir)
    state["stages"]["export"] = {"status": "SUCCESS" if all(v["status"] == "SUCCESS" for v in exported["formats"].values()) else "PARTIAL", "path": str(export_dir.resolve())}
    (run_dir / "run.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    resource_dir = run_dir / "resources-verified"
    suffix = 2
    while resource_dir.exists():
        resource_dir = run_dir / f"resources-verified-{suffix}"
        suffix += 1
    resources = resource_report(bundle_dir, export_dir, settings["replay"], config_path.resolve().parent / settings["target_mcu_config"], resource_dir)
    state["stages"]["resources"] = {"status": resources["portable_host"]["status"], "path": str(resource_dir.resolve()), "mcu_feasibility": resources["deployment_feasibility"]}
    (run_dir / "run.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    finish(run_dir, config_path)
    state = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    state.pop("error", None)
    state["status"] = "PC_COMPLETE_HARDWARE_PENDING" if state["stages"]["export"]["status"] == "SUCCESS" and resources["portable_host"]["status"] == "SUCCESS" and state["stages"]["calibrated_replay"]["status"] == "SUCCESS" else "PC_CORE_COMPLETE_VERIFICATION_PENDING"
    (run_dir / "run.json").write_text(json.dumps(state, indent=2, allow_nan=False), encoding="utf-8")
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    status = resume(args.run)["status"]
    print(status)
    raise SystemExit(0 if status == "PC_COMPLETE_HARDWARE_PENDING" else 1)
