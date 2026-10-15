"""Verify both trained models on a complete held-out synthetic acquisition."""

import argparse
from datetime import datetime, timedelta, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import secrets
import sys

from scripts.package_laptop import ROOT, RUN, RAW


def verify(root, output):
    from src.realtime.demo import DemoSession, load_cases
    from src.realtime.equipment_server import EquipmentServer, TASKS
    if output.exists():
        raise FileExistsError("Verification output already exists")
    if output.resolve().is_relative_to((root / "data").resolve()) or output.resolve().is_relative_to((root / RUN).resolve()):
        raise ValueError("Verification output must be outside source data and trained models")
    server = EquipmentServer(root / RUN)
    sensors = [s.name for s in server.pipelines["degradation"].sensors if s.enabled]
    cases = load_cases(root / RAW / "heldout.synthetic.csv", sensors)
    selected = next((c for c in cases.values() if c["scenario"] == "both"), None)
    if selected is None:
        raise ValueError("Expected complete 'both' Test acquisition")
    session = DemoSession(server, selected, output)
    states = set()
    try:
        while not session.done:
            session.step()
            if session.latest:
                states.add(session.latest["state"])
        snapshot = session.snapshot()
        if snapshot["processing_failures"] or not all(snapshot["tasks"][t]["inferences"] > 0 for t in TASKS):
            raise RuntimeError("Actual model inference was unavailable or failed")
        if "EQUIPMENT_REVIEW_AND_SURGE" not in states:
            raise RuntimeError("Expected independent equipment and surge alarms were not observed")
        if snapshot["ring"]["size"] != snapshot["ring"]["capacity"] or snapshot["ring"]["overwritten"] <= 0:
            raise RuntimeError("Ring buffer did not reach its overwrite stage")
    except Exception:
        session.close("ERROR")
        raise
    session.close("COMPLETE")
    report = {"status": "SUCCESS", "python": sys.version, "executable": sys.executable,
              "platform": platform.platform(), "packages": {name: importlib.metadata.version(name) for name in
                  ("tensorflow", "keras", "numpy", "pandas", "scikit-learn")},
              "actual_lstm_inference": True, "synthetic_demo": True, "physical_validation": False,
              "observations": snapshot["progress"], "states": sorted(states), "ring": snapshot["ring"],
              "tasks": {t: {k: snapshot["tasks"][t][k] for k in ("model_version", "inferences", "threshold_on", "threshold_off", "consecutive")} for t in TASKS},
              "processing_failures": snapshot["processing_failures"], "hardware_actuation_performed": False}
    (output / "laptop-verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    stamp = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d-%H%M%S-%f")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/laptop-check" / (stamp + "-" + secrets.token_hex(3)))
    args = parser.parse_args(argv)
    report = verify(ROOT, args.output)
    print(json.dumps({"status": report["status"], "observations": report["observations"],
                      "inferences": {t: r["inferences"] for t, r in report["tasks"].items()},
                      "report": str(args.output.resolve() / "laptop-verification.json")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
