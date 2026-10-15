"""Train-only scalers, explicit missing imputation and safe portable JSON state."""

import json
from pathlib import Path

import numpy as np
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler


class FrozenScaler:
    def __init__(self, order: list[str], method: str):
        self.order, self.method = list(order), method
        self.fitted = False

    def fit(self, values: np.ndarray, *, split: str) -> "FrozenScaler":
        if split != "train": raise ValueError("Scaler fit is allowed only on train")
        if self.fitted: raise ValueError("FrozenScaler cannot be refitted")
        if values.ndim != 2 or values.shape[1] != len(self.order) or not len(values):
            raise ValueError("Invalid training feature matrix")
        self.indicators = np.array([name.endswith("__missing") for name in self.order])
        finite = np.isfinite(values)
        if (~finite.any(axis=0)).any():
            absent = [name for name, available in zip(self.order, finite.any(axis=0)) if not available]
            raise ValueError(f"Features have no valid training observations: {absent}; adjust sensors/features or data")
        self.fill = np.array([np.median(column[np.isfinite(column)]) for column in values.T])
        filled = np.where(finite, values, self.fill)
        estimators = {"standard": StandardScaler, "minmax": MinMaxScaler, "robust": RobustScaler}
        estimator = estimators[self.method]().fit(filled)
        if self.method == "standard": self.offset, self.scale = estimator.mean_, estimator.scale_
        elif self.method == "robust": self.offset, self.scale = estimator.center_, estimator.scale_
        else:
            self.scale = 1 / estimator.scale_
            self.offset = -estimator.min_ / estimator.scale_
        # Keep missing flags binary, even if all train rows happen to be healthy.
        self.offset[self.indicators], self.scale[self.indicators] = 0, 1
        self.training_rows = len(values)
        self.fitted = True
        return self

    def transform(self, values: np.ndarray, order: list[str]) -> np.ndarray:
        if not self.fitted: raise ValueError("Scaler is not fitted")
        if list(order) != self.order: raise ValueError("Feature order differs from training artifact")
        if values.ndim != 2 or values.shape[1] != len(self.order): raise ValueError("Feature matrix shape mismatch")
        result = (np.where(np.isfinite(values), values, self.fill) - self.offset) / self.scale
        result = result.astype(np.float32)
        if not np.isfinite(result).all(): raise ValueError("Scaling overflow/nonfinite result")
        return result

    def save(self, path: Path) -> None:
        if not self.fitted: raise ValueError("Scaler is not fitted")
        path.write_text(json.dumps({"schema_version": 1, "method": self.method, "feature_order": self.order,
                                   "fill": self.fill.tolist(), "offset": self.offset.tolist(), "scale": self.scale.tolist(),
                                   "training_rows": self.training_rows, "fit_split": "train"}, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "FrozenScaler":
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["schema_version"] != 1 or data["fit_split"] != "train": raise ValueError("Invalid scaler artifact")
        scaler = cls(data["feature_order"], data["method"])
        for name in ("fill", "offset", "scale"):
            array = np.asarray(data[name], dtype=float)
            if array.shape != (len(scaler.order),) or not np.isfinite(array).all(): raise ValueError("Invalid scaler coefficients")
            setattr(scaler, name, array)
        if (scaler.scale <= 0).any(): raise ValueError("Invalid scaler scales")
        scaler.training_rows, scaler.fitted = data["training_rows"], True
        return scaler
