"""Reproducible arbitrary-unit fixtures, never physical lightning simulation."""

import hashlib
import json
import math
from pathlib import Path
import random
from decimal import Decimal

import pandas as pd

from src.utils.config import PipelineConfig, read_yaml

PURPOSE = "SOFTWARE_PIPELINE_TEST_ONLY_NOT_PHYSICAL_LIGHTNING_DATA"


def generate_frame(config: PipelineConfig, settings: dict, *, inject_faults: bool = False) -> pd.DataFrame:
    if settings.get("purpose") != PURPOSE:
        raise ValueError("synthetic purpose must explicitly mark software-only test data")
    step, duration, cycle = (float(settings[k]) for k in ("base_period_seconds", "duration_seconds", "cycle_seconds"))
    if not all(math.isfinite(v) and v > 0 for v in (step, duration, cycle)):
        raise ValueError("Synthetic periods and duration must be positive finite numbers")
    fractions = [settings[k] for k in ("approaching_fraction", "event_fraction", "recovery_fraction")]
    if not 0 < fractions[0] < fractions[1] < fractions[2] < 1:
        raise ValueError("Synthetic state fractions must be ordered within (0,1)")
    start = pd.Timestamp(settings["start_timestamp"])
    if start.tzinfo is None or pd.isna(start):
        raise ValueError("Synthetic start_timestamp must be timezone aware")
    periods = {}
    for spec in config.sensors:
        if not spec.enabled:
            continue
        period = spec.nominal_sampling_period or settings["test_period_seconds"].get(spec.name)
        if period is None or not math.isfinite(period) or period <= 0:
            raise ValueError(f"{spec.name}: provide an explicit synthetic test period")
        ratio = period / step
        if ratio < 1 or not math.isclose(ratio, round(ratio), abs_tol=1e-8):
            raise ValueError("Synthetic periods must be integer multiples of base_period_seconds")
        periods[spec.name] = round(ratio)
    rng = random.Random(settings["seed"])
    rows = []
    # Decimal avoids losing the final tick (e.g. 359.9 / 0.1) to float rounding.
    ticks = int(Decimal(str(duration)) / Decimal(str(step)))
    for index in range(ticks + 1):
        elapsed = index * step
        fraction = elapsed % cycle / cycle
        state = "normal" if fraction < fractions[0] else "approaching_risk" if fraction < fractions[1] else "lightning_event" if fraction < fractions[2] else "recovery"
        amplitude = {"normal": 0.0, "approaching_risk": 1.0, "lightning_event": 4.0, "recovery": 0.5}[state]
        cycle_index = math.floor(elapsed / cycle)
        row = {"timestamp": (start + pd.Timedelta(seconds=elapsed)).isoformat()}
        for sensor, ticks in periods.items():
            # Slow channels have sparse observations, not repeated filled values.
            row[sensor] = "" if index % ticks else f"{amplitude + rng.gauss(0, 0.05):.6f}"
        row.update({"event_id": f"synthetic-{cycle_index:04d}",
                    "event_timestamp": (start + pd.Timedelta(seconds=cycle_index * cycle + fractions[1] * cycle)).isoformat(),
                    "ground_truth": "UNLABELED", "device_id": "SYNTHETIC_DEVICE",
                    "sensor_status": "OK", "communication_status": "OK",
                    "source": config.settings["input"]["source"], "acquisition_kind": "synthetic", "is_synthetic": "true", "synthetic_state": state})
        rows.append(row)
    frame = pd.DataFrame(rows)
    if inject_faults:
        if len(frame) < 12 or not periods:
            raise ValueError("Fault fixture needs at least 12 rows and one enabled sensor")
        sensor = next(iter(periods))
        frame.loc[1, "timestamp"] = "invalid-timestamp"
        frame.loc[3, "timestamp"] = frame.loc[2, "timestamp"]
        frame.loc[5, "timestamp"] = frame.loc[0, "timestamp"]
        frame.loc[6, sensor] = "NaN"
        frame.loc[7, sensor] = "Inf"
        frame.loc[8, sensor] = "invalid-number"
        frame.loc[9, "sensor_status"] = "FAULT"
        frame.loc[10, "communication_status"] = "ERROR"
        frame.loc[11, sensor] = ""
    return frame


def save_synthetic(frame: pd.DataFrame, output: Path, config: PipelineConfig, settings: dict, *, inject_faults: bool) -> Path:
    output = output.resolve()
    metadata = output.with_suffix(output.suffix + ".metadata.json")
    if output.exists() or metadata.exists():
        raise FileExistsError("Synthetic generator refuses to overwrite existing raw data or metadata")
    if output.suffix.lower() not in {".csv", ".parquet"}:
        raise ValueError("Synthetic output must be CSV or Parquet")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        if output.suffix.lower() == ".csv":
            handle.write(frame.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        else:
            frame.to_parquet(handle, engine="pyarrow", index=False)
    with output.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    with metadata.open("x", encoding="utf-8") as handle:
        json.dump({"purpose": PURPOSE, "is_synthetic": True, "labels": "UNLABELED",
                   "warning": "Arbitrary units and demonstration states. Not suitable for evaluating real detection performance.",
                   "source": config.settings["input"]["source"], "sha256": digest,
                   "generator_settings": settings, "faults_injected": inject_faults}, handle, indent=2)
        handle.write("\n")
    return metadata
