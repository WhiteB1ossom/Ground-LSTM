"""Causal equipment context and cumulative-surge features for server models."""

from collections import deque
import math

import numpy as np


MAX_EXACT_COUNT = 2 ** 53 - 1


def valid_count(value):
    return math.isfinite(value) and 0 <= value <= MAX_EXACT_COUNT and float(value).is_integer()


class EquipmentFeatures:
    """Keep raw counters in records, but expose increments rather than lifetime age."""

    def __init__(self, sensors, settings):
        self.options = dict(settings["equipment_features"])
        self.lookup = {s.name: i for i, s in enumerate(sensors)}
        self.counter = self.options["counter_sensor"]
        self.ambient = self.options["ambient_sensor"]
        self.limiters = tuple(self.options["limiter_sensors"])
        self.voltage = self.options["input_voltage_sensor"]
        self.ground = tuple(self.options["response_sensors"])
        required = [self.counter, self.ambient, self.voltage, *self.limiters, *self.ground]
        if any(name not in self.lookup for name in required) or len(set(self.limiters)) != 3:
            raise ValueError("Equipment features require all ten independently named sensors")
        specs = {s.name: s for s in sensors}
        if specs[self.counter].unit != "count" or any(specs[n].unit != "degC" for n in (*self.limiters, self.ambient)):
            raise ValueError("Equipment counter/temperature units mismatch")
        if specs[self.voltage].unit != "V_AC" or any(specs[n].unit != "V_AC" for n in self.ground):
            raise ValueError("Equipment voltage units mismatch")
        if settings["features"] != ["current_value"]:
            raise ValueError("Equipment counter transform requires current_value base features")
        for key in ("counter_window_seconds", "response_window_seconds"):
            v = self.options[key]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
                raise ValueError("Invalid equipment " + key)
        for key in ("ambient_reference_degC", "input_voltage_reference"):
            v = self.options[key]
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)):
                raise ValueError("Invalid equipment " + key)
        if self.options["ambient_reference_degC"] is None or (self.options["input_voltage_reference"] is not None and self.options["input_voltage_reference"] <= 0):
            raise ValueError("Equipment references require ambient temperature and positive voltage or null")
        self.window_ns = int(self.options["counter_window_seconds"] * 1e9)
        self.max_counter_gap = specs[self.counter].max_staleness
        self.response_ns = int(self.options["response_window_seconds"] * 1e9)
        period = settings["alignment_period_seconds"]
        self.events = deque(maxlen=math.ceil(self.options["counter_window_seconds"] / period) + 1)
        self.previous_count = self.previous_observed = None
        self.previous_ground = None
        self.response = None
        self.counter_log_increment = math.nan
        self.last_diagnostics = None
        self.extra_order = [self.counter + "__recent_rate_per_second", self.counter + "__reset", self.counter + "__increment_known"]
        self.extra_order += [name + "__minus_ambient_degC" for name in self.limiters]
        self.extra_order += [self.ambient + "__minus_reference_degC", self.voltage + "__minus_reference", self.voltage + "__relative_deviation"]

    def transform(self, sample):
        now = int(sample.timestamp.value)
        def value(name): return float(sample.values[self.lookup[name]])
        count = value(self.counter)
        observed = sample.observation_times[self.lookup[self.counter]]
        increment, reset, known, status = math.nan, 0., 0., "BASELINE_UNKNOWN"
        if not valid_count(count) or observed is None:
            self.events.clear()
            self.previous_count = self.previous_observed = None
            status = "COUNTER_UNAVAILABLE"
        elif self.previous_observed == observed:
            increment, known, status = 0., 1., "HELD_OBSERVATION"
        else:
            current = int(count)
            if self.previous_observed is not None and self.max_counter_gap is not None and (observed - self.previous_observed).total_seconds() >= self.max_counter_gap:
                self.events.clear()
                status = "COUNTER_GAP_UNKNOWN_INCREMENT"
            elif self.previous_count is not None:
                if current < self.previous_count:
                    reset, status = 1., "COUNTER_RESET_UNKNOWN_INCREMENT"
                    self.events.clear()
                else:
                    increment, known, status = float(current - self.previous_count), 1., "OK"
                    if increment: self.events.append((now, increment))
            self.previous_count, self.previous_observed = current, observed
        while self.events and self.events[0][0] <= now - self.window_ns: self.events.popleft()
        recent = sum(v for _, v in self.events)
        rate = recent / self.options["counter_window_seconds"] if known else math.nan
        self.counter_log_increment = math.log1p(increment) if known else math.nan
        temperatures = {name: {"temperature_degC": value(name), "rise_over_ambient_degC": value(name) - value(self.ambient)} for name in self.limiters}
        reference = self.options["input_voltage_reference"]
        voltage_delta = value(self.voltage) - reference if reference is not None else math.nan
        grounds = {name: value(name) for name in self.ground}
        if known and increment > 0:
            self.response = {"event_timestamp_ns": now, "pre_event_values": dict(self.previous_ground or {n: math.nan for n in self.ground})}
        response = None
        if self.response and now - self.response["event_timestamp_ns"] <= self.response_ns:
            response = {**self.response, "seconds_since_count_increase": (now - self.response["event_timestamp_ns"]) / 1e9,
                        "observed_values": grounds, "distance_to_zero_V": {name: abs(v) for name, v in grounds.items()},
                        "change_from_pre_event_V": {n: grounds[n] - self.response["pre_event_values"][n] for n in self.ground},
                        "protection_success": None, "scope": "observations_not_energy_conversion_or_zero_voltage_guarantee"}
        self.previous_ground = grounds
        self.last_diagnostics = {"counter": {"cumulative_count": count, "increment": increment, "increment_known": bool(known),
                                             "reset": bool(reset), "status": status, "recent_count": recent if known else None,
                                             "window_seconds": self.options["counter_window_seconds"], "rate_per_second": rate,
                                             "meaning": "surge_counter_not_independent_lightning_confirmation"},
                                 "limiters": temperatures, "ambient_reference_degC": self.options["ambient_reference_degC"],
                                 "ambient_deviation_degC": value(self.ambient) - self.options["ambient_reference_degC"],
                                 "input_voltage": {"measured": value(self.voltage), "reference": reference, "difference": voltage_delta,
                                                   "relative_deviation": voltage_delta / reference if reference is not None else math.nan},
                                 "voltage_response": response}
        return np.array([rate, reset, known, *[temperatures[n]["rise_over_ambient_degC"] for n in self.limiters],
                         value(self.ambient) - self.options["ambient_reference_degC"], voltage_delta,
                         voltage_delta / reference if reference is not None else math.nan], dtype=np.float64)
