"""Ordered, trailing-only features. Metadata never enters the tensor."""

from collections import deque

import numpy as np

from src.preprocessing.alignment import AlignedSample
from src.utils.config import SensorSpec
from src.features.equipment import EquipmentFeatures


class FeatureTransform:
    def __init__(self, sensors: tuple[SensorSpec, ...], settings: dict):
        self.sensors = tuple(s for s in sensors if s.enabled)
        self.settings = settings
        self.previous = None
        self.previous_time = None
        self.history = deque(maxlen=settings.get("rolling_window_steps") or 1)
        self.order = [f"{s.name}__{f}" for s in self.sensors for f in settings["features"]]
        self.equipment = EquipmentFeatures(self.sensors, settings) if settings.get("equipment_features") else None
        if self.equipment:
            self.order[self.sensors.index(next(s for s in self.sensors if s.name == self.equipment.counter))] = self.equipment.counter + "__log1p_increment"
        if settings["ground_voltage_difference"]:
            lookup = {s.name: s for s in self.sensors}
            a, b = lookup.get("ground_voltage_a"), lookup.get("ground_voltage_b")
            if a is None or b is None or a.unit is None or a.unit != b.unit:
                raise ValueError("Ground voltage difference requires enabled A/B with identical confirmed units")
            self.difference_indices = (self.sensors.index(a), self.sensors.index(b))
            self.order.append("ground_voltage_difference__current_value")
        if settings["include_missing_indicators"]:
            self.order += [f"{s.name}__missing" for s in self.sensors]
        if settings["include_age_features"]:
            self.order += [f"{s.name}__age_seconds" for s in self.sensors]
        if self.equipment: self.order += self.equipment.extra_order

    def transform(self, sample: AlignedSample) -> np.ndarray:
        if self.previous_time is not None and sample.timestamp <= self.previous_time:
            raise ValueError("Feature samples must strictly increase")
        self.history.append(sample.values.copy())
        equipment_values = self.equipment.transform(sample) if self.equipment else None
        trailing = np.stack(self.history)
        result = []
        for i, sensor in enumerate(self.sensors):
            current = sample.values[i]
            delta = current - self.previous[i] if self.previous is not None else np.nan
            elapsed = (sample.timestamp - self.previous_time).total_seconds() if self.previous_time is not None else None
            history = trailing[:, i]
            history = history[np.isfinite(history)]
            for feature in self.settings["features"]:
                if feature == "current_value": value = self.equipment.counter_log_increment if self.equipment and sensor.name == self.equipment.counter else current
                elif feature == "delta": value = delta
                elif feature == "rate_of_change": value = delta / elapsed if elapsed else np.nan
                elif sample.missing[i] or len(history) == 0: value = np.nan
                elif feature == "rolling_mean": value = history.mean()
                elif feature == "rolling_std": value = history.std(ddof=0)
                elif feature == "rolling_min": value = history.min()
                elif feature == "rolling_max": value = history.max()
                else: raise ValueError(f"Unknown feature: {feature}")
                result.append(value)
        if self.settings["ground_voltage_difference"]:
            a, b = self.difference_indices
            # Only subtract concurrent physical observations; held values from
            # different acquisition instants are not a measured potential gap.
            concurrent = sample.observation_times[a] is not None and sample.observation_times[a] == sample.observation_times[b]
            result.append(sample.values[a] - sample.values[b] if concurrent else np.nan)
        if self.settings["include_missing_indicators"]: result.extend(sample.missing.astype(float))
        if self.settings["include_age_features"]: result.extend(sample.age_seconds)
        if self.equipment: result.extend(equipment_values)
        self.previous, self.previous_time = sample.values.copy(), sample.timestamp
        return np.array(result, dtype=np.float64)
