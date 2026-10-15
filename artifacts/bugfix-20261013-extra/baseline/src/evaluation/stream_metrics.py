"""Constant-size live counters; complete traces remain on disk for offline plots."""

from collections import deque
import numpy as np


class StreamMetrics:
    def __init__(self, threshold: float, period_seconds: float):
        self.threshold, self.period = threshold, period_seconds
        self.cm = np.zeros((2, 2), dtype=np.int64)
        self.total = self.valid = self.normal = self.normal_valid = self.alarm_normal = self.alarm_normal_all = 0
        self.unclassified = self.risk_intervals = self.detected = self.alarm_episodes = self.false_alarms = 0
        self.incomplete_risk = self.missed_covered_risk = 0
        self.false_alarm_starts = 0
        self.current_risk = self.current_alarm = self.session = None
        self.delays = deque(maxlen=1024)
        self.rule_cube = np.zeros((2, 2, 2), dtype=np.int64)
        self.rule_unknown_scored = 0

    def _finish_risk(self):
        if self.current_risk is not None:
            first = self.current_risk["first"]
            fully_covered = self.current_risk["covered"] == self.current_risk["rows"]
            self.incomplete_risk += not fully_covered
            self.missed_covered_risk += first is None and fully_covered
            if first is not None:
                self.detected += 1
                self.delays.append((first - self.current_risk["start"]) / 1e9)
            self.current_risk = None

    def _finish_alarm(self):
        if self.current_alarm is not None:
            self.false_alarms += int(not self.current_alarm["risk_overlap"] and self.current_alarm["normal_covered"])
            self.current_alarm = None

    def consume(self, row):
        session = (row["device_id"], row["session_id"])
        if session != self.session:
            self._finish_risk(); self._finish_alarm()
            self.session = session
        label = row["ground_truth"]
        normal, risk, available = label == "normal", label == "risk", bool(row["available"])
        active = row["decision"]["alarm_active"]
        self.total += 1; self.valid += available; self.normal += normal
        self.normal_valid += normal and available
        self.alarm_normal += normal and available and active
        self.alarm_normal_all += normal and active
        self.unclassified += not (normal or risk)
        if row["prediction"] is not None and (normal or risk):
            predicted = int(row["prediction"]["risk_score"] >= self.threshold)
            self.cm[int(risk), predicted] += 1
            rule = row.get("sensor_rules", {}).get("condition_met")
            if rule is None: self.rule_unknown_scored += 1
            else: self.rule_cube[int(bool(rule)), int(risk), predicted] += 1
        if risk:
            if self.current_risk is None:
                self.risk_intervals += 1
                self.current_risk = {"start": row["timestamp_ns"], "first": None, "rows": 0, "covered": 0}
            self.current_risk["rows"] += 1
            self.current_risk["covered"] += available
            if active and available and self.current_risk["first"] is None: self.current_risk["first"] = row["timestamp_ns"]
        else: self._finish_risk()
        if active:
            if self.current_alarm is None:
                self.alarm_episodes += 1
                self.false_alarm_starts += bool(normal and available and row["decision"].get("transition", "ENTER") == "ENTER")
                self.current_alarm = {"risk_overlap": False, "normal_covered": False}
            self.current_alarm["risk_overlap"] |= risk and available
            self.current_alarm["normal_covered"] |= normal and available
        else: self._finish_alarm()

    def finish(self):
        self._finish_risk(); self._finish_alarm()
        tn, fp, fn, tp = map(int, self.cm.ravel())
        n = tn + fp + fn + tp
        precision, recall = tp / (tp + fp) if tp + fp else 0., tp / (tp + fn) if tp + fn else 0.
        window = {"samples": n, "confusion_matrix": self.cm.tolist(), "false_positives": fp, "false_negatives": fn,
                  "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.,
                  "accuracy": (tn + tp) / n if n else None, "risk_false_positive_rate": fp / (fp + tn) if fp + tn else None,
                  "threshold": self.threshold, "scope": "window_level"} if n else None
        return {"scope": "timestamp_replay_not_mcu_or_physical_validation", "window": window,
                "total_seconds": self.total * self.period, "normal_seconds": self.normal * self.period,
                "normal_valid_seconds": self.normal_valid * self.period, "available_seconds": self.valid * self.period,
                "coverage": self.valid / self.total if self.total else None, "risk_intervals": self.risk_intervals,
                "detected_risk_intervals": self.detected, "missed_risk_intervals": self.risk_intervals - self.detected,
                "incompletely_covered_risk_intervals": self.incomplete_risk, "missed_fully_covered_risk_intervals": self.missed_covered_risk,
                "alarm_episodes": self.alarm_episodes, "false_alarm_episodes": self.false_alarm_starts,
                "unmatched_alarm_episodes": self.false_alarms,
                "false_alarm_per_normal_valid_hour": self.false_alarm_starts / (self.normal_valid * self.period / 3600) if self.normal_valid else None,
                "normal_alarm_seconds": self.alarm_normal * self.period,
                "normal_alarm_seconds_including_unavailable": self.alarm_normal_all * self.period,
                "normal_alarm_fraction": self.alarm_normal / self.normal_valid if self.normal_valid else None,
                "detection_delays_seconds": list(self.delays), "delay_sample_limit": self.delays.maxlen,
                "median_detection_delay_seconds": float(np.median(self.delays)) if self.delays else None,
                "unclassified_rows": self.unclassified,
                "rule_condition_by_truth_by_prediction": self.rule_cube.tolist(),
                "rule_unknown_scored_windows": self.rule_unknown_scored,
                "rule_cube_axes": ["condition_met:false/true", "truth:normal/risk", "prediction:normal/risk"],
                "matching_rule": "False alarm = ENTER during available labeled-normal time. Risk detection = available alarm overlap. Unmatched episodes and normal alarm duration are separately reported."}
