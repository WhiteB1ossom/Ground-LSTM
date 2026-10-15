"""Load explicit, versioned configuration without guessing sensor limits."""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        try:
            value = yaml.safe_load(handle)
        except yaml.YAMLError as error:
            raise ValueError(f"{path}: malformed YAML") from error
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise ValueError(f"{path}: expected a mapping with schema_version: 1")
    return value


def _read_inherited(path: Path, seen: set[Path] | None = None) -> dict[str, Any]:
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        raise ValueError("Configuration inheritance cycle")
    seen.add(path)
    value = read_yaml(path)
    parent = value.pop("extends", None)
    if parent is None:
        return value
    base = _read_inherited(path.parent / parent, seen)
    # Resolve path settings against the file in which they were declared.
    def absolutize(data: dict, root: Path) -> None:
        if "sensors_config" in data:
            data["sensors_config"] = str((root / data["sensors_config"]).resolve())
        for section, keys in (("input", ["directory"]), ("report", ["directory"]),
                              ("pipeline", ["output_directory", "scaler_directory"])):
            for key in keys:
                if key in data.get(section, {}):
                    data[section][key] = str((root / data[section][key]).resolve())
    absolutize(base, (path.parent / parent).resolve().parent)
    absolutize(value, path.parent)
    def merge(left: dict, right: dict) -> dict:
        result = dict(left)
        for key, item in right.items():
            result[key] = merge(result[key], item) if isinstance(item, dict) and isinstance(result.get(key), dict) else item
        return result
    return merge(base, value)


def _number(value: Any, name: str, *, positive: bool = False) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a finite number or null")
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{name}: expected {'positive ' if positive else ''}finite number")
    return float(value)


def read_inherited_yaml(path: str | Path) -> dict[str, Any]:
    """Shared inheritance with cycle checking and declaration-relative paths."""
    return _read_inherited(Path(path))


@dataclass(frozen=True)
class SensorSpec:
    name: str
    unit: str | None
    expected_min: float | None
    expected_max: float | None
    nominal_sampling_period: float | None
    threshold: float | None
    missing_value_policy: str
    max_staleness: float | None
    enabled: bool
    group: str


@dataclass(frozen=True)
class PipelineConfig:
    path: Path
    sensors: tuple[SensorSpec, ...]
    settings: dict[str, Any]

    def resolve(self, value: str) -> Path:
        return (self.path.parent / value).resolve()


def load_config(path: str | Path) -> PipelineConfig:
    path = Path(path).resolve()
    settings = _read_inherited(path)
    raw_sensors = read_yaml(path.parent / settings["sensors_config"])["sensors"]
    if not isinstance(raw_sensors, list) or not raw_sensors:
        raise ValueError("sensors must be a nonempty list")
    sensors = []
    names = set()
    from src.data.schema import RESERVED_COLUMNS
    policies = {"forward_fill", "limited_forward_fill", "interpolation", "missing_indicator", "drop_window"}
    for item in raw_sensors:
        spec = SensorSpec(**item)
        if not isinstance(spec.name, str) or not spec.name or spec.name in names:
            raise ValueError("sensor names must be unique nonempty strings")
        names.add(spec.name)
        if spec.name in RESERVED_COLUMNS:
            raise ValueError(f"{spec.name}: metadata cannot be a sensor feature")
        if not isinstance(spec.enabled, bool):
            raise ValueError(f"{spec.name}: enabled must be boolean")
        if spec.unit is not None and not isinstance(spec.unit, str):
            raise ValueError(f"{spec.name}: unit must be text or null")
        for field in ("expected_min", "expected_max", "threshold"):
            _number(getattr(spec, field), f"{spec.name}.{field}")
        for field in ("nominal_sampling_period", "max_staleness"):
            _number(getattr(spec, field), f"{spec.name}.{field}", positive=True)
        if spec.expected_min is not None and spec.expected_max is not None and spec.expected_min > spec.expected_max:
            raise ValueError(f"{spec.name}: expected_min exceeds expected_max")
        if spec.missing_value_policy not in policies or spec.group not in {"fast", "slow_context"}:
            raise ValueError(f"{spec.name}: invalid missing policy or sensor group")
        if spec.missing_value_policy == "interpolation" and settings["future_pipeline"]["causal"]:
            raise ValueError("interpolation is reserved for noncausal offline analysis")
        sensors.append(spec)
    timestamp = settings["timestamp"]
    if timestamp["naive_policy"] not in {"reject", "localize"}:
        raise ValueError("timestamp.naive_policy must be reject or localize")
    ZoneInfo(timestamp["output_timezone"])
    if timestamp["naive_policy"] == "localize":
        if not timestamp["naive_timezone"]:
            raise ValueError("naive_timezone is required when localizing timestamps")
        ZoneInfo(timestamp["naive_timezone"])
    quality = settings["quality"]
    tolerance = _number(quality["sampling_relative_tolerance"], "sampling_relative_tolerance")
    if tolerance is None or tolerance < 0:
        raise ValueError("sampling_relative_tolerance must be nonnegative")
    _number(quality["flatline_seconds"], "flatline_seconds", positive=True)
    for key in ("healthy_sensor_status", "healthy_communication_status"):
        statuses = quality[key]
        if not isinstance(statuses, list) or not statuses or not all(isinstance(s, str) for s in statuses):
            raise ValueError(f"{key} must be a nonempty list of strings")
    if not isinstance(settings["input"]["source"], str) or not settings["input"]["source"]:
        raise ValueError("input.source must be a nonempty string")
    if settings["input"].get("acquisition_kind", "unknown") not in {"unknown", "field_measurement", "lab_experiment", "synthetic"}:
        raise ValueError("Invalid input.acquisition_kind")
    return PipelineConfig(path, tuple(sensors), settings)
