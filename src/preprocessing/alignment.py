"""Shared causal transform for offline datasets and future realtime sampling."""

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd

from src.data.quality import _numeric
from src.utils.config import SensorSpec
from src.features.equipment import valid_count


@dataclass(frozen=True)
class AlignedSample:
    timestamp: pd.Timestamp
    values: np.ndarray
    missing: np.ndarray
    age_seconds: np.ndarray
    observation_times: tuple[pd.Timestamp | None, ...]
    valid: bool


class CausalAligner:
    """Hold observations with explicit ages/stale masks; no future interpolation.

    Empty cells are asynchronous non-observations. Explicit invalid measurements
    invalidate the stored reading until a new valid observation arrives.
    """

    def __init__(self, sensors: tuple[SensorSpec, ...], *, stale_action: str):
        self.sensors = tuple(s for s in sensors if s.enabled)
        self.stale_action = stale_action
        self._values = [math.nan] * len(self.sensors)
        self._times = [None] * len(self.sensors)
        self._latest_update = None
        self._latest_sample = None

    def update(self, timestamp: pd.Timestamp, values: dict, *, status_ok: bool = True) -> None:
        if timestamp.tzinfo is None or pd.isna(timestamp):
            raise ValueError("Aligner requires a timezone-aware timestamp")
        if self._latest_update is not None and timestamp <= self._latest_update:
            raise ValueError("Observation timestamps must strictly increase")
        if self._latest_sample is not None and timestamp <= self._latest_sample:
            raise ValueError("Cannot insert late observations into already sampled history")
        self._latest_update = timestamp
        for i, sensor in enumerate(self.sensors):
            value, reason = _numeric(values.get(sensor.name))
            if reason is None and sensor.unit == "count" and (isinstance(values.get(sensor.name), (bool, np.bool_)) or not valid_count(value)):
                reason = "INVALID_COUNTER"
            if not status_ok:
                self._values[i], self._times[i] = math.nan, timestamp
            elif reason == "MISSING_VALUE":
                continue
            else:
                self._values[i], self._times[i] = value if reason is None else math.nan, timestamp

    def sample(self, timestamp: pd.Timestamp) -> AlignedSample:
        if timestamp.tzinfo is None or pd.isna(timestamp):
            raise ValueError("Sample timestamp must be timezone-aware")
        if self._latest_update is not None and timestamp < self._latest_update:
            raise ValueError("A sample cannot use a future observation")
        if self._latest_sample is not None and timestamp <= self._latest_sample:
            raise ValueError("Sample timestamps must strictly increase")
        self._latest_sample = timestamp
        values, masks, ages = [], [], []
        valid = True
        for sensor, value, observed in zip(self.sensors, self._values, self._times):
            age = (timestamp - observed).total_seconds() if observed is not None else math.nan
            missing = not math.isfinite(value) or observed is None or (sensor.max_staleness is not None and age >= sensor.max_staleness)
            if missing and (self.stale_action == "drop_window" or sensor.missing_value_policy == "drop_window"):
                valid = False
            values.append(math.nan if missing else value)
            masks.append(missing)
            ages.append(age)
        return AlignedSample(timestamp, np.array(values, dtype=np.float64), np.array(masks, dtype=bool),
                             np.array(ages, dtype=np.float64), tuple(self._times), valid)


def align_block(frame: pd.DataFrame, sensors: tuple[SensorSpec, ...], settings: dict, quality: dict) -> tuple[pd.DataFrame, list[AlignedSample]]:
    period = pd.Timedelta(seconds=settings["alignment_period_seconds"])
    grid = pd.date_range(frame["timestamp"].iloc[0].ceil(period), frame["timestamp"].iloc[-1].floor(period), freq=period)
    aligner = CausalAligner(sensors, stale_action=settings["stale_action"])
    rows = frame.to_dict("records")
    cursor = 0
    latest = None
    samples, metadata = [], []
    for timestamp in grid:
        while cursor < len(rows) and rows[cursor]["timestamp"] <= timestamp:
            latest = rows[cursor]
            status_ok = all(field not in latest or (not pd.isna(latest[field]) and str(latest[field]) in quality[key])
                            for field, key in (("sensor_status", "healthy_sensor_status"), ("communication_status", "healthy_communication_status")))
            aligner.update(latest["timestamp"], latest, status_ok=status_ok)
            cursor += 1
        samples.append(aligner.sample(timestamp))
        metadata.append({"timestamp": timestamp, "event_id": latest.get("event_id", ""),
                         "session_id": latest.get("session_id", ""),
                         "ground_truth": latest.get("ground_truth", "UNLABELED"),
                         "device_id": latest.get("device_id", ""), "raw_row": latest["raw_row"],
                         "source": latest["source"], "acquisition_kind": latest["acquisition_kind"]})
    return pd.DataFrame(metadata), samples
