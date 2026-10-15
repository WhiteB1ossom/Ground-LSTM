"""Standard wide, sparse observation schema. Metadata is never a model feature."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


OPTIONAL_COLUMNS = (
    "event_id", "event_timestamp", "ground_truth", "device_id", "sensor_status",
    "communication_status", "source", "acquisition_kind", "is_synthetic", "synthetic_state",
    "session_id", "scenario", "degradation_truth", "surge_truth", "input_voltage_reference",
)
RESERVED_COLUMNS = {"timestamp", *OPTIONAL_COLUMNS}


@dataclass(frozen=True)
class RawDataset:
    frame: pd.DataFrame
    path: Path
    source: str
    sha256: str


def parse_timestamp(value: object, settings: dict) -> tuple[pd.Timestamp, str | None]:
    """Reject ambiguous naive/DST values; retain reason instead of silently sorting."""
    try:
        # Numeric epoch units must be normalized by a future explicit source adapter.
        if not isinstance(value, (str, pd.Timestamp)):
            from datetime import datetime
            if not isinstance(value, datetime):
                raise ValueError("timestamp must be ISO text or datetime")
        if isinstance(value, str) and (not value.strip() or value.strip().isdigit()):
            raise ValueError("missing timestamp or unspecified epoch unit")
        stamp = pd.Timestamp(value)
        if pd.isna(stamp):
            raise ValueError("missing timestamp")
        if stamp.tzinfo is None:
            if settings["naive_policy"] == "reject":
                return pd.NaT, "TIMESTAMP_TIMEZONE_MISSING"
            stamp = stamp.tz_localize(settings["naive_timezone"], ambiguous="raise", nonexistent="raise")
        return stamp.tz_convert(settings["output_timezone"]), None
    except (ValueError, TypeError, OverflowError):
        return pd.NaT, "TIMESTAMP_PARSE_FAILED"
    except Exception as error:
        # pandas timezone backends use different DST exception types.
        if type(error).__name__ in {"AmbiguousTimeError", "NonExistentTimeError"}:
            return pd.NaT, "TIMESTAMP_PARSE_FAILED"
        raise
