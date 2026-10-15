"""Simple causal baselines with JSON state; physical thresholds are never invented."""

import json
from pathlib import Path
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from src.preprocessing.scaling import FrozenScaler
from src.models.rules import compare, validate_rule


def sequence_summary(X: np.ndarray) -> np.ndarray:
    return np.concatenate([X[:, -1, :], X.mean(axis=1), X.std(axis=1), X[:, -1, :] - X[:, 0, :]], axis=1)


class LogisticBaseline:
    def fit(self, X, y, *, max_iter: int, class_weight, seed: int):
        model = LogisticRegression(max_iter=max_iter, class_weight=class_weight, random_state=seed)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(sequence_summary(X), y)
        if any(issubclass(w.category, ConvergenceWarning) for w in captured):
            raise ValueError("Logistic baseline did not converge; inspect inputs and logistic_max_iter")
        # JSON reload uses float64; keep the live path identical at threshold boundaries.
        self.coefficients = np.asarray(model.coef_, dtype=np.float64)
        self.intercepts = np.asarray(model.intercept_, dtype=np.float64)
        self.classes = model.classes_
        return self

    def predict(self, X):
        logits = sequence_summary(X) @ self.coefficients.T + self.intercepts
        if len(self.classes) == 2: return np.exp(-np.logaddexp(0, -logits[:, 0]))
        shifted = logits - logits.max(axis=1, keepdims=True)
        scores = np.exp(shifted)
        return scores / scores.sum(axis=1, keepdims=True)

    def save(self, path: Path):
        path.write_text(json.dumps({"schema_version": 1, "summary": "last_mean_std_delta",
                                   "coefficients": self.coefficients.tolist(), "intercepts": self.intercepts.tolist(),
                                   "classes": self.classes.tolist()}, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["schema_version"] != 1 or data["summary"] != "last_mean_std_delta": raise ValueError("Invalid logistic artifact")
        model = cls()
        model.coefficients, model.intercepts = np.asarray(data["coefficients"]), np.asarray(data["intercepts"])
        model.classes = np.asarray(data["classes"])
        return model


class ThresholdBaseline:
    def __init__(self, manifest: dict, scaler: FrozenScaler, configured_rules: list[dict]):
        self.scaler = scaler
        self.rules = list(configured_rules)
        sensors = {s["name"]: s for s in manifest["sensors"]}
        for rule in self.rules:
            validate_rule(rule, sensors)
            name = rule["sensor"] + "__current_value"
            reference = rule.get("reference_sensor")
            if name not in scaler.order or (reference and reference + "__current_value" not in scaler.order):
                raise ValueError("Invalid threshold rule; enabled current-value feature and finite explicit limit are required")

    def predict(self, X):
        if not self.rules: raise ValueError("Threshold baseline disabled: no confirmed threshold rules")
        risk = np.zeros(len(X), dtype=bool)
        all_known = np.ones(len(X), dtype=bool)
        for rule in self.rules:
            known = np.ones(len(X), dtype=bool)
            index = self.scaler.order.index(rule["sensor"] + "__current_value")
            raw = X[:, -1, index] * self.scaler.scale[index] + self.scaler.offset[index]
            missing = rule["sensor"] + "__missing"
            if missing in self.scaler.order: known &= X[:, -1, self.scaler.order.index(missing)] < .5
            reference = rule.get("reference_sensor")
            if reference:
                ref_index = self.scaler.order.index(reference + "__current_value")
                raw -= X[:, -1, ref_index] * self.scaler.scale[ref_index] + self.scaler.offset[ref_index]
                ref_missing = reference + "__missing"
                if ref_missing in self.scaler.order: known &= X[:, -1, self.scaler.order.index(ref_missing)] < .5
            known &= np.isfinite(raw)
            risk |= known & compare(raw, rule)
            all_known &= known
        return np.where(risk | all_known, risk.astype(float), np.nan)
