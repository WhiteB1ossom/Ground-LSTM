"""Single-owner causal stream; acquisition resets never use ground-truth IDs."""

from dataclasses import asdict
import math
import time

import numpy as np
import pandas as pd

from src.data.schema import parse_timestamp
from src.data.quality import _numeric
from src.features.transform import FeatureTransform
from src.models.rules import evaluate_rules, validate_rule
from src.preprocessing.alignment import CausalAligner
from src.realtime.decision import DecisionEngine
from src.realtime.ring_buffer import RingBuffer, buffer_capacity
from src.realtime.sequence_builder import SequenceBuilder
from src.utils.config import SensorSpec


def json_value(value):
    if isinstance(value, dict): return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)): return [json_value(v) for v in value]
    if isinstance(value, (float, np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, pd.Timestamp): return value.isoformat()
    return value


class RealtimePipeline:
    def __init__(self, engine, settings: dict, recorder=None):
        if settings.get("mode") != "advisory" or settings.get("hardware_actuation_enabled") is not False:
            raise ValueError("Only advisory mode without hardware actuation is supported")
        self.engine, self.settings, self.recorder = engine, settings, recorder
        self.manifest = engine.manifest
        self.config = self.manifest["configuration"]
        self.p = self.config["pipeline"]
        self.sensors = tuple(SensorSpec(**s) for s in self.manifest["sensors"])
        self.period = pd.Timedelta(seconds=self.p["alignment_period_seconds"])
        self.ring = RingBuffer(buffer_capacity(engine.shape[1], settings["pre_event_seconds"], self.period.total_seconds()), engine.shape[2])
        self.builder = SequenceBuilder(self.ring, engine.shape[1], self.period.total_seconds(), stride=self.p["windows"]["stride"])
        self.tensor = np.empty(engine.shape, dtype=np.float32)
        on = settings.get("risk_on_threshold", engine.threshold)
        off = settings.get("risk_off_threshold", on * settings.get("off_threshold_ratio", 1))
        self.decision = DecisionEngine(on, off, consecutive=settings["minimum_consecutive_detections"])
        self.rules = settings.get("rules", [])
        for rule in self.rules: validate_rule(rule, {s.name: asdict(s) for s in self.sensors})
        self.session, self.device, self.next_grid, self.last_observation, self.latest = None, None, None, None, None
        self.input_issues = []
        self.score_valid = False
        self._reset_transform()

    def _reset_transform(self):
        self.score_valid = False
        self.aligner = CausalAligner(self.sensors, stale_action=self.p["stale_action"])
        self.features = FeatureTransform(self.sensors, self.p)
        if self.features.order != self.engine.scaler.order: raise ValueError("Realtime feature order mismatch")
        self.ring.clear()

    def _sample(self, timestamp):
        start = time.perf_counter_ns()
        sample = self.aligner.sample(timestamp)
        values = self.features.transform(sample)
        scaled = self.engine.scaler.transform(values[None, :], self.features.order)[0]
        valid = sample.valid and (self.p["stale_action"] != "drop_window" or np.isfinite(values).all())
        self.ring.append(timestamp, scaled, valid=bool(valid))
        status = self.builder.build_into(self.tensor)
        prediction, failure = None, status.reason
        if status.ready:
            try:
                prediction = self.engine.predict(self.tensor)
                self.score_valid = True
            except (ValueError, RuntimeError) as error: failure = "INFERENCE_ERROR:" + str(error)
        if not valid or status.reason in {"INVALID_WINDOW", "TIMESTAMP_GAP"} or (status.ready and prediction is None):
            self.score_valid = False
        # Waiting for stride is scheduling, not a new unavailable observation.
        if status.reason in {"WAITING_FOR_STRIDE", "NO_NEW_SAMPLE"} and valid and self.score_valid:
            from src.realtime.decision import Decision
            decision = Decision("RISK" if self.decision.active else "NORMAL", self.decision.active, None, status.reason)
        else:
            decision = self.decision.update(int(timestamp.value), prediction["risk_score"] if prediction else None,
                                            available=prediction is not None, reason=failure)
        physical = {s.name: sample.values[i] for i, s in enumerate(s for s in self.sensors if s.enabled)}
        rule_result = evaluate_rules(physical, self.rules, combination=self.settings.get("rule_combination", "any"))
        decision_done_ns = time.perf_counter_ns()
        row = {"timestamp_ns": int(timestamp.value), "timestamp": timestamp.isoformat(), "device_id": self.device,
               "session_id": self.session, "input_status": status.reason, "available": self.score_valid,
               "window_valid": bool(valid), "decision": asdict(decision), "prediction": prediction,
               "sensor_rules": rule_result, "physical_values": json_value(physical), "processed_values": scaled.tolist(),
               "observation_age_seconds": json_value(sample.age_seconds),
               "raw_observation": dict(self.latest) if self.last_observation == timestamp else None,
               "input_issues": self.input_issues,
               "ground_truth": self.latest.get("ground_truth", "UNLABELED"),
               "event_id": self.latest.get("event_id", ""),
               "host_processing_start_ns": start, "host_decision_done_ns": decision_done_ns,
               "host_clock": "perf_counter_process_local_not_sensor_clock",
               "processing_ms": (time.perf_counter_ns() - start) / 1e6}
        row = json_value(row)
        if self.recorder: self.recorder.consume(row, decision)
        return row

    def feed(self, observation: dict):
        timestamp, reason = parse_timestamp(observation.get("timestamp"), self.config["timestamp"])
        if reason: raise ValueError(reason)
        if observation.get("source", self.config["input"]["source"]) != self.config["input"]["source"]:
            raise ValueError("Source mismatch")
        declared = observation.get("acquisition_kind", self.config["input"]["acquisition_kind"])
        if declared != self.config["input"]["acquisition_kind"]: raise ValueError("Acquisition provenance mismatch")
        device = observation.get("device_id", "")
        if self.device is not None and device != self.device: raise ValueError("One device per pipeline; mixed streams rejected")
        session = observation.get("session_id", "")
        if self.last_observation is not None and timestamp <= self.last_observation: raise ValueError("Duplicate/late observation")
        output = []
        if self.next_grid is None or session != self.session:
            if self.recorder and self.next_grid is not None: self.recorder.boundary("ACQUISITION_RESET")
            self._reset_transform()
            self.next_grid = timestamp.ceil(self.period)
        else:
            count = max(0, (timestamp.value - self.next_grid.value) // self.period.value)
            if count > 10000: raise ValueError("Gap exceeds bounded catch-up budget; explicit acquisition restart required")
            while self.next_grid < timestamp:
                output.append(self._sample(self.next_grid))
                self.next_grid += self.period
        self.device, self.session, self.latest = device, session, dict(observation)
        quality = self.config["quality"]
        healthy = all(observation.get(field, "OK") in quality[key] for field, key in
                      (("sensor_status", "healthy_sensor_status"), ("communication_status", "healthy_communication_status")))
        issues = []
        if not healthy: issues.append({"code": "INVALID_SENSOR_OR_COMMUNICATION_STATUS"})
        for sensor in self.sensors:
            value, issue = _numeric(observation.get(sensor.name))
            if issue and issue != "MISSING_VALUE": issues.append({"sensor": sensor.name, "code": issue})
            elif issue is None and ((sensor.expected_min is not None and value < sensor.expected_min) or (sensor.expected_max is not None and value > sensor.expected_max)):
                issues.append({"sensor": sensor.name, "code": "RANGE_REVIEW"})
        self.input_issues = issues
        self.aligner.update(timestamp, observation, status_ok=healthy)
        self.last_observation = timestamp
        if self.next_grid == timestamp:
            output.append(self._sample(timestamp))
            self.next_grid += self.period
        return output
