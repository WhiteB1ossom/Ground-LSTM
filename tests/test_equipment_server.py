"""Equipment criteria, separate thermal causes and causal cumulative-counter handling."""

from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import prepare_equipment_data as generator
from src.features.transform import FeatureTransform
from src.models.rules import evaluate_rules
from src.preprocessing.alignment import CausalAligner
from src.preprocessing.scaling import FrozenScaler
from src.realtime.equipment_server import EquipmentServer, _local
from src.realtime.stream import RealtimePipeline
from src.utils.config import load_config, read_yaml


def profile(): return load_config("configs/preprocessing_equipment_server.yaml")


def normal_values():
    return dict(ground_voltage_a=.5, ground_voltage_b=.6, leakage_current=.0015,
                limiter_temp_a=30., limiter_temp_b=31., limiter_temp_c=32., humidity=50.,
                ambient_temp=25., input_voltage=220., lightning_sensor=1000.)


class Samples:
    def __init__(self, reference=220):
        self.config = profile()
        self.settings = deepcopy(self.config.settings["pipeline"])
        self.settings["equipment_features"]["input_voltage_reference"] = reference
        self.aligner = CausalAligner(self.config.sensors, stale_action="missing_indicator")
        self.features = FeatureTransform(self.config.sensors, self.settings)
    def feed(self, seconds, **values):
        stamp = pd.Timestamp("2026-01-01T00:00:00Z") + pd.Timedelta(seconds=seconds)
        self.aligner.update(stamp, values)
        sample = self.aligner.sample(stamp)
        return sample, self.features.transform(sample), self.features.equipment.last_diagnostics


RULES = read_yaml(Path("configs/equipment_server.yaml"))["replay"]["rules"]
EXPECTED_LIMITS = {"ground_voltage_a": 2, "ground_voltage_b": 2, "leakage_current": .002,
                   "limiter_temp_a": 45, "limiter_temp_b": 45, "limiter_temp_c": 45, "humidity": 70}


@pytest.mark.parametrize("rule", RULES, ids=lambda r:r["sensor"])
def test_requested_boundary_uses_ge_without_turning_the_rule_into_a_label(rule):
    assert rule["value"] == EXPECTED_LIMITS[rule["sensor"]]
    assert rule["operator"] == "ge"
    values = normal_values()
    for offset, expected in ((-1e-7, False), (0., True), (1e-7, True)):
        values[rule["sensor"]] = rule["value"] + offset
        assert evaluate_rules(values, [rule])["condition_met"] is expected
    values[rule["sensor"]] = None
    assert evaluate_rules(values, [rule])["condition_met"] is None


def test_all_sensors_retained_and_lifetime_count_replaced_with_causal_transform():
    s = Samples()
    assert len(s.config.sensors) == 10 and all(v.enabled for v in s.config.sensors)
    assert len(s.features.order) == len(set(s.features.order)) == 39
    assert "lightning_sensor__current_value" not in s.features.order
    s.feed(0., **normal_values())
    _, vector, diagnostic = s.feed(.1, lightning_sensor=1002.)
    assert vector[s.features.order.index("lightning_sensor__log1p_increment")] == pytest.approx(math.log1p(2))
    assert diagnostic["counter"]["increment"] == 2 and diagnostic["counter"]["rate_per_second"] == .2
    assert diagnostic["counter"]["cumulative_count"] == 1002


def test_counter_baseline_and_reset_do_not_create_artificial_surge():
    s = Samples()
    _, _, first = s.feed(0., **normal_values())
    assert not first["counter"]["increment_known"] and math.isnan(first["counter"]["increment"])
    s.feed(.1, lightning_sensor=1002.)
    _, vector, result = s.feed(.2, lightning_sensor=0.)
    assert result["counter"]["reset"] and not result["counter"]["increment_known"]
    assert result["counter"]["recent_count"] is None
    assert math.isnan(vector[s.features.order.index("lightning_sensor__log1p_increment")])
    _, _, recovered = s.feed(.3, lightning_sensor=1.)
    assert recovered["counter"]["increment"] == 1 and not recovered["counter"]["reset"]


@pytest.mark.parametrize("invalid", [-1., .5, float("nan"), float("inf"), float(2 ** 53), True, False])
def test_invalid_counter_invalidates_sample_and_does_not_resume_from_an_old_baseline(invalid):
    s = Samples()
    s.feed(0., **normal_values())
    sample, _, result = s.feed(.1, lightning_sensor=invalid)
    assert not sample.valid and result["counter"]["status"] == "COUNTER_UNAVAILABLE"
    _, _, result = s.feed(.2, lightning_sensor=1005.)
    assert not result["counter"]["increment_known"]


def test_count_gap_is_unknown_even_if_no_missing_grid_was_sampled():
    s = Samples()
    s.feed(0., **normal_values())
    _, _, result = s.feed(1., lightning_sensor=1003., ground_voltage_a=.5, ground_voltage_b=.6)
    assert result["counter"]["status"] == "COUNTER_GAP_UNKNOWN_INCREMENT"
    assert not result["counter"]["increment_known"]


def test_counter_window_expiry_and_held_observations_do_not_duplicate_events():
    s = Samples()
    s.feed(0., **normal_values())
    s.feed(.1, lightning_sensor=1002.)
    _, _, held = s.feed(.2)
    assert held["counter"]["increment"] == 0 and held["counter"]["recent_count"] == 2
    for tick in range(3, 102): _, _, result = s.feed(tick / 10, lightning_sensor=1002.)
    assert result["counter"]["recent_count"] == 0
    assert len(s.features.equipment.events) == 0


def test_independent_temperature_rise_and_ambient_25_do_not_imply_lightning():
    s = Samples()
    values = normal_values()
    s.feed(0., **values)
    _, _, result = s.feed(.1, limiter_temp_b=50., ambient_temp=35., lightning_sensor=1000.)
    assert result["limiters"]["limiter_temp_b"]["rise_over_ambient_degC"] == 15
    assert result["limiters"]["limiter_temp_a"]["temperature_degC"] == 30
    assert result["counter"]["recent_count"] == 0 and result["voltage_response"] is None
    assert result["ambient_deviation_degC"] == 10


def test_input_voltage_reference_is_explicit_and_never_an_inferred_alarm_limit():
    s = Samples(reference=None)
    _, _, result = s.feed(0., **normal_values())
    assert result["input_voltage"]["reference"] is None and math.isnan(result["input_voltage"]["difference"])
    s = Samples(reference=220)
    _, _, result = s.feed(0., **{**normal_values(), "input_voltage": 242.})
    assert result["input_voltage"]["difference"] == 22
    assert result["input_voltage"]["relative_deviation"] == pytest.approx(.1)
    assert "condition_met" not in result["input_voltage"]


def test_zero_voltage_response_is_observed_context_without_protection_success_claim():
    s = Samples()
    s.feed(0., **normal_values())
    _, _, zero = s.feed(.1, ground_voltage_a=0., ground_voltage_b=0., lightning_sensor=1000.)
    assert zero["voltage_response"] is None
    _, _, event = s.feed(.2, ground_voltage_a=0., ground_voltage_b=0., lightning_sensor=1001.)
    assert event["voltage_response"]["distance_to_zero_V"]["ground_voltage_a"] == 0
    assert event["voltage_response"]["protection_success"] is None


@pytest.mark.parametrize("change", [{"counter_window_seconds": 0}, {"input_voltage_reference": 0}, {"ambient_reference_degC": None}, {"response_window_seconds": float("nan")}])
def test_invalid_equipment_configuration_fails_explicitly(change):
    config = profile()
    settings = deepcopy(config.settings["pipeline"])
    settings["equipment_features"].update(change)
    with pytest.raises(ValueError): FeatureTransform(config.sensors, settings)


def test_task_manifests_cannot_escape_the_server_run(tmp_path):
    with pytest.raises(ValueError): _local(tmp_path, "../other")
    (tmp_path / "server-models.json").write_text(json.dumps({"schema_version": 1, "deployment_target": "mcu", "tasks": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"): EquipmentServer(tmp_path)


@pytest.mark.parametrize("heat,surge,available,state", [(False, False, True, "NORMAL"),
    (True, False, True, "EQUIPMENT_REVIEW"), (False, True, True, "SURGE_ACTIVITY"),
    (True, True, True, "EQUIPMENT_REVIEW_AND_SURGE"), (True, False, False, "UNAVAILABLE")])
def test_server_keeps_equipment_and_surge_states_separate(heat, surge, available, state):
    class Pipeline:
        device = last_observation = None
        def __init__(self, alarm, usable): self.alarm, self.usable = alarm, usable
        def validate_observation(self, row): return pd.Timestamp(row["timestamp"])
        def feed(self, row):
            return [{"timestamp_ns": 0, "timestamp": row["timestamp"], "device_id": "d", "session_id": "s",
                     "available": self.usable, "decision": {"alarm_active": self.alarm},
                     "equipment": {"counter": {"increment_known": True, "recent_count": 0}},
                     "sensor_rules": {"condition_met": heat}}]
    server = EquipmentServer.__new__(EquipmentServer)
    server.pipelines = {"degradation": Pipeline(heat, True), "surge": Pipeline(surge, available)}
    source = {"timestamp": "2026-01-01T00:00:00Z", "ground_truth": "risk"}
    rows = server.feed(source)
    assert rows[0]["state"] == state and rows[0]["lightning_confirmed"] is None
    assert rows[0]["observed_surge_activity"] is False
    assert source["ground_truth"] == "risk"


def test_generator_preserves_observation_cadence_and_separates_heat_from_surge(tmp_path, monkeypatch):
    monkeypatch.setattr(generator, "SCENARIOS", ("normal", "heating_without_surge", "surge_only"))
    options = read_yaml(Path("configs/equipment_server.yaml"))
    options["synthetic"]["replicas_by_split"] = {"train": 1, "validation": 1, "test": 1}
    frame, report = generator.prepare(tmp_path / "raw", profile(), options)
    assert report["sessions"] == 9 and report["rows"] == 16200
    heat = frame.loc[frame["scenario"] == "heating_without_surge"]
    assert (heat["surge_truth"] == "normal").all() and (heat["degradation_truth"] == "risk").any()
    assert heat.groupby("session_id")["lightning_sensor"].nunique().eq(1).all()
    assert frame.groupby("session_id")["limiter_temp_a"].apply(lambda v: (v != "").sum()).eq(3).all()
    assert frame.groupby("session_id")["humidity"].apply(lambda v: (v != "").sum()).eq(1).all()
    surge = frame.loc[frame["scenario"] == "surge_only"]
    assert (surge["degradation_truth"] == "normal").all() and (surge["surge_truth"] == "risk").any()
    assert report["zero_response"]["scope"].startswith("hypothetical")


def test_generator_uses_sensor_names_when_configuration_order_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(generator, "SCENARIOS", ("normal",))
    config = profile()
    config = replace(config, sensors=tuple(reversed(config.sensors)))
    options = read_yaml(Path("configs/equipment_server.yaml"))
    options["synthetic"]["replicas_by_split"] = {"train": 1, "validation": 1, "test": 1}
    frame, _ = generator.prepare(tmp_path / "raw", config, options)
    first = frame.iloc[0]
    assert first["lightning_sensor"] >= 100
    assert 0 < first["ground_voltage_a"] < 1
    assert .001 < first["leakage_current"] < .002
    assert 210 < first["input_voltage"] < 230


def test_realtime_equipment_feature_tensor_matches_direct_causal_transform():
    config = profile()
    settings = deepcopy(config.settings["pipeline"])
    direct = FeatureTransform(config.sensors, settings)
    aligner = CausalAligner(config.sensors, stale_action=settings["stale_action"])
    scaler = FrozenScaler(direct.order, "standard").fit(np.stack([np.zeros(39), np.ones(39)]), split="train")
    class Engine:
        manifest = {"configuration": {**config.settings, "pipeline": settings}, "sensors": [vars(s) for s in config.sensors]}
        shape = (1, 64, 39)
        threshold = .5
        def predict(self, tensor): return {"risk_score": .1}
    engine = Engine()
    engine.scaler = scaler
    options = read_yaml(Path("configs/equipment_server.yaml"))["replay"]
    pipeline = RealtimePipeline(engine, options)
    for tick in range(85):
        stamp = pd.Timestamp("2026-01-01T00:00:00Z") + pd.Timedelta(milliseconds=tick * 100)
        row = {**normal_values(), "timestamp": stamp.isoformat(), "lightning_sensor": 1000 + tick // 10}
        aligner.update(stamp, row)
        expected = scaler.transform(direct.transform(aligner.sample(stamp))[None, :], direct.order)[0]
        emitted = pipeline.feed(row)[0]
        np.testing.assert_array_equal(emitted["processed_values"], expected)
        assert emitted["equipment"]["counter"]["meaning"].startswith("surge_counter")
