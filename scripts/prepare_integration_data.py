"""Diverse labeled software scenarios, never physical lightning ground truth."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.training.data import file_hash
from src.utils.config import load_config


def prepare(output: Path, config_path=Path("configs/preprocessing_integration_demo.yaml"), *, seed=20261012) -> dict:
    if output.exists(): raise FileExistsError("Scenario output already exists")
    config = load_config(config_path)
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-02-01T00:00:00Z")
    scenarios = []
    # Each chronological partition contains all classes and scenario categories.
    for fold, counts in enumerate(([12, 6, 6, 6, 6], [4, 2, 2, 2, 2], [4, 2, 2, 2, 2])):
        kinds = [kind for kind, n in zip(("normal", "boundary", "single", "compound", "transition"), counts) for _ in range(n)]
        rng.shuffle(kinds)
        scenarios.extend((kind, ("train", "validation", "test")[fold]) for kind in kinds)
    rows, index = [], []
    for case, (kind, split) in enumerate(scenarios + [("fault", "fault") for _ in range(10)]):
        onset = float(rng.uniform(18, 30))
        duration = float(rng.uniform(6, 12))
        offset = case * 60
        phase = rng.uniform(0, 2 * np.pi)
        baseline = rng.uniform(.25, .9)
        temp, humidity, ambient = rng.uniform(28, 45), rng.uniform(35, 65), rng.uniform(8, 30)
        changed = int(rng.integers(0, 3))
        index.append({"session_id": f"case-{case:03d}", "kind": kind, "planned_split": split, "onset_seconds": onset,
                      "duration_seconds": duration, "rows": 600, "fixture_label_only": True})
        for tick in range(600):
            t = tick / 10
            risk = kind in {"single", "compound", "transition"} and onset <= t < onset + duration
            if kind == "transition": risk |= onset + 16 <= t < onset + 20
            wave = np.sin(t * rng.uniform(.25, .3) + phase)
            a = baseline + .07 * wave + rng.normal(0, .025)
            b = baseline * rng.uniform(.6, .8) + .06 * np.cos(t + phase) + rng.normal(0, .025)
            leak = .0015 + abs(rng.normal(0, .00015))
            if kind == "boundary":
                a = 2 + .09 * np.sin(t * 2) + rng.normal(0, .025)
                leak = .001 + abs(rng.normal(0, .00005))
            pulse = float(risk) * (1 + .2 * np.sin(t * 3))
            if kind in {"compound", "transition"} or changed == 0: a += pulse * rng.uniform(1.3, 2.3)
            if kind in {"compound", "transition"} or changed == 1: b += pulse * rng.uniform(1.1, 1.8)
            if kind in {"compound", "transition"} or changed == 2: leak += pulse * .003
            values = [max(0, a), max(0, b), leak, temp, temp + rng.normal(0, .5), temp + rng.normal(0, .5),
                      humidity, ambient, 230 + rng.normal(0, 2), int(rng.random() < (.05 if risk else .002))]
            row = {"timestamp": (start + pd.Timedelta((case * 600 + tick) * 100_000_000, unit="ns")).isoformat()}
            for sensor, value in zip(config.sensors, values):
                cadence = int(round(sensor.nominal_sampling_period / .1))
                # Every acquisition session has a genuine initial observation.
                row[sensor.name] = float(value) if tick == 0 or tick % cadence == 0 else ""
            row.update(event_id=f"fixture-{case:03d}", session_id=f"case-{case:03d}", device_id="SOFTWARE_DEVICE",
                       ground_truth="UNLABELED" if kind == "fault" else "risk" if risk else "normal",
                       source="monitoring", acquisition_kind="synthetic", is_synthetic="true",
                       sensor_status="OK", communication_status="OK", scenario=kind)
            if kind == "fault" and 200 <= tick < 230:
                fault = case % 5
                if fault == 0: row["ground_voltage_a"] = "NaN"
                elif fault == 1: row["ground_voltage_b"] = ""
                elif fault == 2: row["communication_status"] = "ERROR"
                elif fault == 3: row["leakage_current"] = "Inf"
                else: row["sensor_status"] = "FAULT"
            rows.append(row)
    output.mkdir(parents=True)
    frame = pd.DataFrame(rows)
    train = frame.iloc[:36000]
    faults = frame.iloc[36000:]
    train.to_csv(output / "training.synthetic.csv", index=False)
    faults.to_csv(output / "faults.synthetic.csv", index=False)
    # An uninterrupted two-hour NORMAL trace covers the hourly context update.
    normal_id = train.loc[train["scenario"].eq("normal"), "event_id"].iloc[0]
    long_rows = train.loc[train["event_id"].eq(normal_id)].copy()
    long_rows["event_id"], long_rows["session_id"] = "background", "continuous-hour"
    long_rows["ground_truth"] = "normal"
    long_parts = []
    for minute in range(120):
        part = long_rows.copy()
        part["timestamp"] = [(start + pd.Timedelta((minute * 600 + tick) * 100_000_000, unit="ns")).isoformat() for tick in range(600)]
        if minute % 60:
            for s in config.sensors:
                if s.nominal_sampling_period >= 3600: part[s.name] = ""
        long_parts.append(part)
    pd.concat(long_parts, ignore_index=True).to_csv(output / "normal-hour.synthetic.csv", index=False)
    report = {"schema_version": 1, "purpose": "SOFTWARE_SCENARIOS_NOT_PHYSICAL_PERFORMANCE", "seed": seed,
              "scenario_count": 60, "fault_scenario_count": 10, "training_rows": len(train), "fault_rows": len(faults),
              "total_scenario_rows": len(frame), "long_normal_rows": 72000, "scenario_index": index,
              "sensors": [asdict(s) for s in config.sensors],
              "files": {p.name: file_hash(p) for p in output.glob("*.csv")},
              "notes": ["Source range/unit fixture only; thresholds and labels have no physical validation.",
                        "Staleness overrides are software test settings.", "Input-voltage unit remains source-name interpretation."]}
    (output / "scenarios.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({k: v for k, v in prepare(args.output).items() if k.endswith("count") or k.endswith("rows")}))
