"""Single-owner causal stream; acquisition resets never use ground-truth IDs."""

from dataclasses import asdict
from copy import deepcopy
import math
import time

import numpy as np
import pandas as pd

from src.data.schema import parse_timestamp
from src.data.quality import _numeric
from src.features.transform import FeatureTransform
from src.models.rules import evaluate_rules, validate_rule
from src.preprocessing.alignment import CausalAligner
from src.preprocessing.scaling import ScalingOverflowError
from src.realtime.decision import DecisionEngine
from src.realtime.ring_buffer import RingBuffer, buffer_capacity
from src.realtime.sequence_builder import SequenceBuilder
from src.realtime.serialization import json_value
from src.utils.config import SensorSpec


class RealtimePipeline:
    def __init__(self, engine, settings: dict, recorder=None, *, clock=time.monotonic):
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
        self.input_timeout = settings.get("input_timeout_seconds", 1.0)
        if isinstance(self.input_timeout, bool) or not isinstance(self.input_timeout, (int, float)) or not math.isfinite(self.input_timeout) or self.input_timeout <= 0:
            raise ValueError("input_timeout_seconds must be finite and positive")
        self.clock = clock
        self._last_clock = None
        self._last_receipt = self._now()
        self.timed_out = False
        self._timeout_reference = None
        self.input_timeouts = 0
        self._reset_transform()

    def _now(self):
        now = self.clock()
        if not math.isfinite(now) or (self._last_clock is not None and now < self._last_clock):
            raise ValueError("Watchdog clock must be finite and monotonic")
        self._last_clock = now
        return now

    @staticmethod
    def _receipt_time(value, now):
        if value is None: return now
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value > now:
            raise ValueError("Receive time must be finite and no later than the host clock")
        return value

    def invalidate_input(self, reason):
        """Single-owner invalidation for either silence or a processing delay."""
        decision = self.decision.invalidate(reason)
        if self.recorder: self.recorder.boundary(reason)
        self._reset_transform()
        self.next_grid = None
        return {"record_type": "STATUS", "input_status": reason, "available": False,
                "prediction": None, "decision": asdict(decision), "device_id": self.device, "session_id": self.session,
                "last_observation_timestamp": self.last_observation.isoformat() if self.last_observation is not None else None,
                "clock": "host_monotonic_not_sensor_clock", "ground_truth": "UNLABELED"}

    def poll(self, *, last_received_at=None):
        """Called by the live timer, including when the input queue is empty.

        Host silence is a status event, not a synthetic sensor observation.
        Its monotonic time must never enter sensor-clock alignment/evaluation.
        """
        return self._poll_at(self._now(), last_received_at)

    def _poll_at(self, now, last_received_at):
        """Consume a host-clock snapshot captured with the receiver reference."""
        if last_received_at is not None:
            self._last_receipt = max(self._last_receipt, self._receipt_time(last_received_at, now))
        elapsed = now - self._last_receipt
        if elapsed < self.input_timeout: return None
        return self.input_timeout_status(self._last_receipt, elapsed)

    def input_timeout_status(self, reference, elapsed):
        """Report a silence interval once, including one observed after it ended."""
        if self._timeout_reference is not None and reference <= self._timeout_reference: return None
        self._timeout_reference = reference
        self.timed_out = True
        self.input_timeouts += 1
        return {**self.invalidate_input("INPUT_TIMEOUT"), "host_silence_seconds": elapsed}

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
        preprocessing_failure = None
        try: scaled = self.engine.scaler.transform(values[None, :], self.features.order)[0]
        except ScalingOverflowError as error:
            # Keep the time grid moving, but never infer on the placeholder row.
            scaled = np.zeros(self.engine.shape[2], dtype=np.float32)
            preprocessing_failure = "PREPROCESSING_ERROR:" + str(error)
        valid = preprocessing_failure is None and sample.valid and (self.p["stale_action"] != "drop_window" or np.isfinite(values).all())
        self.ring.append(timestamp, scaled, valid=bool(valid))
        status = self.builder.build_into(self.tensor)
        prediction, failure = None, preprocessing_failure or status.reason
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
               "session_id": self.session, "input_status": "PREPROCESSING_ERROR" if preprocessing_failure else status.reason, "available": self.score_valid,
               "sample_valid": bool(valid),
               "window_valid": status.reason in {"READY", "WAITING_FOR_STRIDE", "NO_NEW_SAMPLE"},
               "decision": asdict(decision), "prediction": prediction,
               "sensor_rules": rule_result, "physical_values": json_value(physical), "processed_values": scaled.tolist(),
               "observation_age_seconds": json_value(sample.age_seconds),
               # This is the latest source observation, with its own timestamp;
               # holding a feature must not masquerade as a new measurement.
               "raw_observation": dict(self.latest),
               "input_issues": self.input_issues,
               "ground_truth": self.latest.get("ground_truth", "UNLABELED"),
               "event_id": self.latest.get("event_id", ""),
               "host_processing_start_ns": start, "host_decision_done_ns": decision_done_ns,
               "host_clock": "perf_counter_process_local_not_sensor_clock",
               "processing_ms": (time.perf_counter_ns() - start) / 1e6}
        row = json_value(row)
        if self.features.equipment:
            row["equipment"] = json_value(self.features.equipment.last_diagnostics)
        if self.recorder: self.recorder.consume(row, decision)
        return row

    def validate_observation(self, observation: dict):
        """Read-only structural validation, also usable by receiver threads."""
        timestamp, reason = parse_timestamp(observation.get("timestamp"), self.config["timestamp"])
        if reason: raise ValueError(reason)
        try: timestamp.value
        except OverflowError as error: raise ValueError("TIMESTAMP_OUTSIDE_NANOSECOND_RANGE") from error
        source = observation.get("source", self.config["input"]["source"])
        if not isinstance(source, str) or source != self.config["input"]["source"]:
            raise ValueError("Source mismatch")
        declared = observation.get("acquisition_kind", self.config["input"]["acquisition_kind"])
        if not isinstance(declared, str) or declared != self.config["input"]["acquisition_kind"]: raise ValueError("Acquisition provenance mismatch")
        return timestamp

    def feed(self, observation: dict, *, received_at=None):
        observation = deepcopy(observation)
        timestamp = self.validate_observation(observation)
        device = observation.get("device_id", "")
        if self.device is not None and device != self.device: raise ValueError("One device per pipeline; mixed streams rejected")
        session = observation.get("session_id", "")
        if self.last_observation is not None and timestamp <= self.last_observation: raise ValueError("Duplicate/late observation")
        receipt = self._receipt_time(received_at, self._now())
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
        self._last_receipt = max(self._last_receipt, receipt)
        self.timed_out = False
        if self.recorder: self.recorder.observe(int(timestamp.value), observation)
        if self.next_grid == timestamp:
            output.append(self._sample(timestamp))
            self.next_grid += self.period
        return output
