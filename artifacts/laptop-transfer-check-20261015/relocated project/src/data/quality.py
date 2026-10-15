"""Diagnostic flags preserve extreme physical values and asynchronous observations."""

from collections import Counter
import math
from typing import Any

import pandas as pd

from src.data.schema import RawDataset, parse_timestamp
from src.utils.config import PipelineConfig


def _numeric(value: object) -> tuple[float | None, str | None]:
    if isinstance(value, str) and not value.strip():
        return None, "MISSING_VALUE"
    if value is None or value is pd.NA:
        return None, "MISSING_VALUE"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, "NON_NUMERIC_VALUE"
    if math.isnan(number):
        return None, "NAN_VALUE"
    if math.isinf(number):
        return None, "INF_VALUE"
    return number, None


def inspect_quality(dataset: RawDataset, config: PipelineConfig) -> dict[str, Any]:
    frame = dataset.frame
    issues: list[dict[str, Any]] = []

    def flag(row: int | None, field: str, code: str, category: str, detail: str = "") -> None:
        issues.append({"row": row, "field": field, "reason_code": code, "category": category, "detail": detail})

    timestamps = []
    for row, value in enumerate(frame["timestamp"]):
        stamp, reason = parse_timestamp(value, config.settings["timestamp"])
        timestamps.append(stamp)
        if reason:
            flag(row, "timestamp", reason, "invalid")
    # Row numbers always refer to original file order (0-based), never sorted order.
    devices = frame["device_id"].fillna("").astype(str).tolist() if "device_id" in frame else [""] * len(frame)
    groups: dict[str, list[int]] = {}
    for row, device in enumerate(devices):
        groups.setdefault(device, []).append(row)
    intervals = []
    for rows in groups.values():
        seen = set()
        previous = None
        for row in rows:
            stamp = timestamps[row]
            if pd.isna(stamp):
                previous = None
                continue
            if stamp in seen:
                flag(row, "timestamp", "TIMESTAMP_DUPLICATE", "invalid")
            seen.add(stamp)
            if previous is not None:
                elapsed = (stamp - previous).total_seconds()
                if elapsed < 0:
                    flag(row, "timestamp", "TIMESTAMP_REVERSED", "invalid")
                elif elapsed > 0:
                    intervals.append(elapsed)
            previous = stamp

    quality = config.settings["quality"]
    sensor_reports = {}
    for spec in config.sensors:
        if not spec.enabled:
            continue
        if spec.name not in frame:
            flag(None, spec.name, "SENSOR_COLUMN_MISSING", "invalid")
            sensor_reports[spec.name] = {"column_present": False}
            continue
        values = []
        numeric_reasons = []
        value_reasons: Counter = Counter()
        for row, raw in enumerate(frame[spec.name]):
            value, reason = _numeric(raw)
            values.append(value)
            numeric_reasons.append(reason)
            if reason:
                value_reasons[reason] += 1
                # Empty cells mean 'no observation at this row' in the wide sparse
                # schema; missing packets need cadence/status evidence as well.
                flag(row, spec.name, reason, "unavailable" if reason == "MISSING_VALUE" else "invalid")
                continue
            if (spec.expected_min is not None and value < spec.expected_min) or (spec.expected_max is not None and value > spec.expected_max):
                flag(row, spec.name, "OUTSIDE_EXPECTED_RANGE", "review", "Preserved; may be an extreme physical signal. Range alone does not prove invalidity.")
        observed_intervals = []
        for rows in groups.values():
            previous = None
            run_start = None
            last_value = None
            flatline_reported = False
            for row in rows:
                value, stamp = values[row], timestamps[row]
                if pd.isna(stamp):
                    previous = run_start = last_value = None
                    flatline_reported = False
                    continue
                if value is None:
                    # An asynchronous blank isn't another measurement; do not
                    # count it as flatline or reset an otherwise valid cadence.
                    if numeric_reasons[row] != "MISSING_VALUE":
                        run_start, last_value, flatline_reported = None, None, False
                    continue
                elapsed = (stamp - previous).total_seconds() if previous is not None else None
                if elapsed is not None and elapsed > 0:
                    observed_intervals.append(elapsed)
                    nominal = spec.nominal_sampling_period
                    if nominal is not None and abs(elapsed - nominal) > nominal * quality["sampling_relative_tolerance"]:
                        flag(row, spec.name, "SAMPLING_INTERVAL_DEVIATION", "review", f"observed={elapsed:g}s nominal={nominal:g}s")
                if elapsed is not None and elapsed <= 0:
                    run_start = None
                    flatline_reported = False
                nominal = spec.nominal_sampling_period
                if elapsed is not None and nominal is not None and elapsed > nominal * (1 + quality["sampling_relative_tolerance"]):
                    run_start, flatline_reported = None, False
                if run_start is None or value != last_value:
                    run_start, flatline_reported = stamp, False
                duration = quality["flatline_seconds"]
                if duration is not None and not flatline_reported and (stamp - run_start).total_seconds() >= duration:
                    flag(row, spec.name, "FLATLINE", "review", "Repeated observations; constant value alone does not establish sensor failure.")
                    flatline_reported = True
                previous, last_value = stamp, value
        total = len(frame)
        unavailable = sum(value_reasons.values())
        sensor_reports[spec.name] = {
            "column_present": True, "group": spec.group, "unit": spec.unit,
            "observations": total - unavailable,
            "empty_cells": value_reasons["MISSING_VALUE"],
            "missing_value_ratio": unavailable / total if total else None,
            "nan_count": value_reasons["NAN_VALUE"], "inf_count": value_reasons["INF_VALUE"],
            "non_numeric_count": value_reasons["NON_NUMERIC_VALUE"],
            "nominal_sampling_period_seconds": spec.nominal_sampling_period,
            "observed_interval_seconds": _interval_summary(observed_intervals),
            "range_check_enabled": spec.expected_min is not None or spec.expected_max is not None,
            "risk_threshold_configured": spec.threshold is not None,
        }
    for field, healthy_key, code in (
        ("communication_status", "healthy_communication_status", "COMMUNICATION_ERROR"),
        ("sensor_status", "healthy_sensor_status", "SENSOR_STATUS_ABNORMAL"),
    ):
        if field in frame:
            for row, value in enumerate(frame[field]):
                if pd.isna(value) or str(value).strip() == "":
                    flag(row, field, "STATUS_MISSING", "unavailable")
                elif str(value) not in quality[healthy_key]:
                    flag(row, field, code, "invalid", str(value))
    if frame.empty:
        flag(None, "dataset", "EMPTY_DATASET", "invalid")
    labels = frame["ground_truth"] if "ground_truth" in frame else pd.Series(dtype=str)
    labeled = labels.notna() & labels.astype(str).str.strip().ne("") & labels.astype(str).str.upper().ne("UNLABELED")
    synthetic = False
    if "is_synthetic" in frame:
        synthetic = frame["is_synthetic"].astype(str).str.lower().isin(["true", "1"]).any()
    return {
        "report_schema_version": 1,
        "dataset": {"path": str(dataset.path), "sha256": dataset.sha256, "source": dataset.source,
                    "rows": len(frame), "columns": list(frame.columns), "synthetic": bool(synthetic)},
        "label_status": "UNLABELED" if not labeled.any() else "PARTIALLY_LABELED" if not labeled.all() else "LABELED",
        "summary": {"reason_counts": dict(Counter(i["reason_code"] for i in issues)),
                    "category_counts": dict(Counter(i["category"] for i in issues)),
                    "has_invalid_data": any(i["category"] == "invalid" for i in issues)},
        "timestamp": {"output_timezone": config.settings["timestamp"]["output_timezone"],
                      "valid_count": sum(not pd.isna(t) for t in timestamps),
                      "stream_interval_seconds": _interval_summary(intervals)},
        "sensors": sensor_reports, "issues": issues,
        "notes": ["Raw values and order are unchanged. No filtering or interpolation occurred.",
                  "Empty cells may be asynchronous non-observations, not sensor faults. Ratio uses all file rows.",
                  "Range/flatline/cadence warnings require physical and acquisition context review.",
                  "The raw loader preserves the Parquet null bitmap separately from explicit NaN values.",
                  "Quality inspection does not authorize supervised training or certify MCU suitability."],
    }


def _interval_summary(values: list[float]) -> dict:
    return {"count": len(values), "min": min(values) if values else None,
            "max": max(values) if values else None,
            "median": float(pd.Series(values).median()) if values else None}
