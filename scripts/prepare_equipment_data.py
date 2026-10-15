"""Independent equipment/surge software causes; not measured failure labels."""

from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.training.data import file_hash


SCENARIOS = ("normal", "hot_ambient", "high_count_only", "counter_reset", "temp_a", "temp_b", "temp_c",
             "heating_without_surge", "leakage", "ground_a", "ground_b", "humidity", "mixed",
             "surge_only", "both", "response_failure", "voltage_deviation")


def prepare(output: Path, config, options):
    if output.exists(): raise FileExistsError("Equipment raw output exists")
    settings = options["synthetic"]
    seconds = settings["session_seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 180:
        raise ValueError("Equipment sessions must cover at least three real minute observations")
    replicas = settings["replicas_by_split"]
    if set(replicas) != {"train", "validation", "test"} or any(type(n) is not int or n < 1 for n in replicas.values()):
        raise ValueError("Explicit positive split replicas required")
    rng = np.random.default_rng(settings["seed"])
    start = pd.Timestamp("2026-03-01T00:00:00Z")
    rows, sessions = [], []
    period = config.settings["pipeline"]["alignment_period_seconds"]
    ticks = int(round(seconds / period))
    serial = 0
    for split in ("train", "validation", "test"):
        kinds = list(SCENARIOS) * replicas[split]
        rng.shuffle(kinds)
        for kind in kinds:
            serial += 1
            session = f"equipment-{serial:04d}"
            ambient = rng.uniform(15, 29) if kind != "hot_ambient" else rng.uniform(32, 38)
            baseline_temps = np.maximum(25, ambient + rng.uniform(3, 7, size=3))
            baseline_temps = np.minimum(baseline_temps, 43)
            # Offsets and time constants are independent for the three components.
            phases = rng.uniform(0, 6.28, size=3)
            time_constants = rng.uniform(45, 80, size=3)
            amplitude = rng.uniform(.05, .6, size=3)
            count = int(rng.integers(100, 10000))
            count = count + 100000 if kind == "high_count_only" else count
            event_ticks = {int(round(t / period)): int(rng.integers(1, 4)) for t in (65., 105., 145.)} if kind in {"surge_only", "both", "response_failure"} else {}
            most_recent = None
            onset = 60.
            sessions.append({"session_id": session, "split": split, "scenario": kind,
                             "rows": ticks, "degradation_cause": kind not in {"normal", "hot_ambient", "high_count_only", "counter_reset", "surge_only"},
                             "surge_ticks": list(event_ticks), "label_source": "declared_software_cause_not_threshold_comparison"})
            for tick in range(ticks):
                t = tick * period
                active = t >= onset
                degradation = kind not in {"normal", "hot_ambient", "high_count_only", "counter_reset", "surge_only"} and (active or kind == "humidity")
                if tick in event_ticks:
                    count += event_ticks[tick]
                    most_recent = t
                if kind == "counter_reset" and tick == int(round(90 / period)): count = 0
                surge = most_recent is not None and t - most_recent < config.settings["pipeline"]["equipment_features"]["counter_window_seconds"]
                temps = baseline_temps + amplitude * np.sin(t / time_constants + phases)
                if active:
                    if kind in {"temp_a", "temp_b", "temp_c"}: temps[ord(kind[-1]) - ord("a")] = rng.uniform(48, 58)
                    if kind in {"heating_without_surge", "both", "response_failure"}: temps[0] = rng.uniform(48, 58)
                    if kind == "mixed": temps += rng.uniform(18, 24, size=3)
                a, b = rng.uniform(.15, .7) + rng.normal(0, .02, size=2)
                leak = rng.uniform(.0011, .0016)
                humidity = rng.uniform(35, 62)
                voltage = settings["input_voltage_reference"] + rng.normal(0, 1.2)
                if active and kind in {"ground_a", "mixed", "response_failure"}: a = rng.uniform(2.2, 3.6)
                if active and kind in {"ground_b", "mixed"}: b = rng.uniform(2.2, 3.6)
                if active and kind in {"leakage", "mixed"}: leak = rng.uniform(.0023, .0045)
                if kind == "humidity": humidity = rng.uniform(74, 84)
                if active and kind == "voltage_deviation": voltage *= rng.uniform(1.16, 1.23)
                zero = settings["zero_response"]
                if surge and zero["enabled"] and kind != "response_failure":
                    factor = np.exp(-(t - most_recent) / zero["decay_seconds"])
                    a = zero["target_V"] + (a - zero["target_V"]) * factor
                    b = zero["target_V"] + (b - zero["target_V"]) * factor
                values = dict(ground_voltage_a=max(0., a), ground_voltage_b=max(0., b), leakage_current=leak,
                              limiter_temp_a=temps[0], limiter_temp_b=temps[1], limiter_temp_c=temps[2],
                              humidity=humidity, ambient_temp=ambient, input_voltage=voltage, lightning_sensor=count)
                row = {"timestamp": (start + pd.Timedelta(seconds=(serial - 1) * seconds + t)).isoformat()}
                for sensor in config.sensors:
                    cadence = max(1, int(round(sensor.nominal_sampling_period / period)))
                    row[sensor.name] = float(values[sensor.name]) if tick % cadence == 0 else ""
                row.update(event_id=session, session_id=session, device_id="SERVER_SOFTWARE_DEVICE", source="monitoring",
                           acquisition_kind="synthetic", is_synthetic=True, sensor_status="OK", communication_status="OK",
                           scenario=kind, degradation_truth="risk" if degradation else "normal", surge_truth="risk" if surge else "normal",
                           ground_truth="risk" if degradation or surge else "normal", input_voltage_reference=settings["input_voltage_reference"])
                rows.append(row)
    output.mkdir(parents=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "observations.synthetic.csv", index=False)
    for task in ("degradation", "surge"):
        view = frame.copy()
        view["ground_truth"] = view[task + "_truth"]
        view.to_csv(output / (task + ".synthetic.csv"), index=False)
    report = {"schema_version": 1, "purpose": "SOFTWARE_CAUSES_NOT_VERIFIED_EQUIPMENT_DEGRADATION_OR_LIGHTNING",
              "seed": settings["seed"], "rows": len(frame), "sessions": len(sessions), "scenario_kinds": list(SCENARIOS),
              "session_index": sessions, "sensors": [asdict(s) for s in config.sensors],
              "zero_response": settings["zero_response"], "input_voltage_reference": {"value": settings["input_voltage_reference"], "provenance": "synthetic_fixture_nominal_not_confirmed_customer_device"},
              "files": {p.name: file_hash(p) for p in output.glob("*.csv")},
              "notes": ["Causes are declared before measurements are generated; thresholds do not generate labels.",
                        "A cumulative surge counter also counts overvoltage surges: labels are surge activity, not lightning confirmation.",
                        "Minute/hourly measurements retain real cadence; a short model window learns current context, not hourly trends."]}
    (output / "scenarios.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return frame, report
