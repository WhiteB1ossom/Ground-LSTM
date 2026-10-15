"""Fail closed on unconfirmed deployment settings; demos use explicit overrides."""

import math

from src.utils.config import PipelineConfig


def validate_pipeline(config: PipelineConfig) -> dict:
    p = config.settings.get("pipeline", {})
    if p.get("segment_policy", "acquisition") not in {"acquisition", "event_fixture"}: raise ValueError("Invalid segment policy")
    if type(p["windows"].get("allow_event_crossing", False)) is not bool: raise ValueError("Invalid event-crossing policy")
    def positive(value, name, integer=False, zero=False):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be explicitly configured")
        if (value < 0 if zero else value <= 0) or (integer and int(value) != value):
            raise ValueError(f"Invalid {name}")
    positive(p.get("alignment_period_seconds"), "alignment_period_seconds")
    positive(p["windows"].get("sequence_length"), "sequence_length", integer=True)
    positive(p["windows"].get("stride"), "stride", integer=True)
    positive(p["windows"].get("label_horizon_seconds"), "label_horizon_seconds", zero=True)
    for name in ("pre_event_seconds", "post_event_seconds"):
        positive(p["events"].get(name), name, zero=True)
    positive(p["split"].get("purge_gap_seconds"), "purge_gap_seconds", zero=True)
    ratios = p["split"]["ratios"]
    if len(ratios) != 3 or any(isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) or r <= 0 for r in ratios) or not math.isclose(sum(ratios), 1):
        raise ValueError("split.ratios must contain three positive fractions summing to 1")
    if p["split"]["mode"] not in {"auto", "event", "chronological"}:
        raise ValueError("Invalid split mode")
    if p["scaler"] not in {"standard", "minmax", "robust"}:
        raise ValueError("Invalid scaler")
    if p["stale_action"] not in {"missing_indicator", "drop_window"}:
        raise ValueError("Invalid stale action")
    allowed = {"current_value", "delta", "rate_of_change", "rolling_mean", "rolling_std", "rolling_min", "rolling_max"}
    if not p["features"] or len(set(p["features"])) != len(p["features"]) or set(p["features"]) - allowed:
        raise ValueError("Unknown, duplicate or metadata feature requested")
    if any(f.startswith("rolling_") for f in p["features"]):
        positive(p["rolling_window_steps"], "rolling_window_steps", integer=True)
    for key in ("include_missing_indicators", "include_age_features", "ground_voltage_difference"):
        if not isinstance(p[key], bool):
            raise ValueError(f"{key} must be boolean")
    if p["stale_action"] == "missing_indicator" and not p["include_missing_indicators"]:
        raise ValueError("missing_indicator stale action requires include_missing_indicators")
    if p["labeling"]["mode"] not in {"binary", "multiclass"}:
        raise ValueError("Invalid labeling mode")
    mapping = p["labeling"]["mapping"]
    if mapping is not None:
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError("label mapping must be a nonempty mapping or null")
        if len({str(k) for k in mapping}) != len(mapping):
            raise ValueError("Label mapping keys must be unambiguous after string normalization")
        classes = set(mapping.values())
        if any(type(v) is not int or v < 0 for v in mapping.values()) or classes != set(range(max(classes) + 1)):
            raise ValueError("Label classes must be contiguous integers starting at zero")
        if p["labeling"]["mode"] == "binary" and classes != {0, 1}:
            raise ValueError("binary mapping must define normal/risk classes 0 and 1")
    enabled = [s for s in config.sensors if s.enabled]
    if not enabled:
        raise ValueError("At least one enabled sensor is required")
    for sensor in enabled:
        if sensor.max_staleness is None:
            raise ValueError(f"{sensor.name}.max_staleness is unconfirmed; set it explicitly (demo settings are not physical limits)")
        if sensor.missing_value_policy == "interpolation":
            raise ValueError("Dataset build for realtime models only supports causal preprocessing")
    if config.settings["input"].get("acquisition_kind", "unknown") == "unknown":
        raise ValueError("input.acquisition_kind must distinguish field_measurement, lab_experiment or synthetic")
    return p
