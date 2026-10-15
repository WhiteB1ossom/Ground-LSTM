from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data.loader import load_raw
from src.data.compare import compare_sources
from src.data.synthetic import generate_frame, save_synthetic
from src.dataset.build import build_dataset, main
from src.dataset.events import extract_events
from src.dataset.labeling import map_labels
from src.dataset.split import assert_event_isolation, split_raw
from src.dataset.windows import build_windows
from src.features.transform import FeatureTransform
from src.preprocessing.alignment import CausalAligner, align_block
from src.preprocessing.offline import interpolate_for_analysis
from src.preprocessing.scaling import FrozenScaler
from src.preprocessing.settings import validate_pipeline
from src.utils.config import load_config, read_yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo(tmp_path):
    config = load_config(ROOT / "configs/preprocessing_demo.yaml")
    settings = deepcopy(config.settings)
    settings["report"]["directory"] = str(tmp_path / "reports")
    settings["pipeline"]["output_directory"] = str(tmp_path / "processed")
    settings["pipeline"]["scaler_directory"] = str(tmp_path / "scalers")
    return replace(config, settings=settings)


def stamp(seconds=0):
    return pd.Timestamp("2026-01-01T00:00:00Z") + pd.Timedelta(seconds=seconds)


def test_production_profile_fails_on_unconfirmed_values(config):
    with pytest.raises(ValueError, match="explicitly configured"):
        validate_pipeline(config)


def test_inheritance_preserves_paths_and_overrides(demo):
    assert Path(demo.settings["sensors_config"]).name == "sensors_demo.yaml"
    assert demo.settings["input"]["acquisition_kind"] == "synthetic"
    assert validate_pipeline(demo)["windows"]["sequence_length"] == 16


def test_hold_age_stale_boundary_and_no_future(demo):
    aligner = CausalAligner((demo.sensors[0],), stale_action="missing_indicator")
    aligner.update(stamp(), {"ground_voltage_a": "10"})
    aligner.update(stamp(.1), {"ground_voltage_a": ""})
    sample = aligner.sample(stamp(.2))
    assert sample.values[0] == 10 and not sample.missing[0]
    assert sample.age_seconds[0] == .2 and sample.observation_times[0] == stamp()
    assert aligner.sample(stamp(.3)).missing[0]  # age >= limit
    aligner.update(stamp(.4), {"ground_voltage_a": "999"})
    with pytest.raises(ValueError, match="future"):
        aligner.sample(stamp(.35))
    assert aligner.sample(stamp(.4)).values[0] == 999


@pytest.mark.parametrize("values,status_ok", [({"ground_voltage_a": "Inf"}, True), ({"ground_voltage_a": "bad"}, True), ({}, False)])
def test_bad_observation_does_not_reuse_old_valid_value(demo, values, status_ok):
    aligner = CausalAligner((demo.sensors[0],), stale_action="drop_window")
    aligner.update(stamp(), {"ground_voltage_a": "1"})
    aligner.update(stamp(.1), values, status_ok=status_ok)
    assert not aligner.sample(stamp(.1)).valid
    aligner.update(stamp(.2), {"ground_voltage_a": "2"})
    assert aligner.sample(stamp(.2)).valid


def test_offline_stream_prefix_parity_and_future_independence(demo):
    sensor = demo.sensors[0]
    config = deepcopy(demo.settings["pipeline"])
    config["features"] = ["current_value", "delta", "rate_of_change", "rolling_mean", "rolling_std", "rolling_min", "rolling_max"]
    config["rolling_window_steps"] = 3
    frame = pd.DataFrame({"timestamp": [stamp(0), stamp(.2), stamp(.4)], "ground_voltage_a": ["1", "3", "1000000"],
                          "source": ["monitoring"] * 3, "acquisition_kind": ["synthetic"] * 3, "raw_row": [0, 1, 2]})
    metadata, offline = align_block(frame, (sensor,), config, demo.settings["quality"])
    prefix_meta, prefix = align_block(frame.iloc[:2], (sensor,), config, demo.settings["quality"])
    a, b = FeatureTransform((sensor,), config), FeatureTransform((sensor,), config)
    for off, pre in zip(offline, prefix):
        np.testing.assert_allclose(a.transform(off), b.transform(pre), equal_nan=True)
    live, transform = CausalAligner((sensor,), stale_action="missing_indicator"), FeatureTransform((sensor,), config)
    full = FeatureTransform((sensor,), config)
    cursor = 0
    for sample in offline:
        while cursor < len(frame) and frame.iloc[cursor]["timestamp"] <= sample.timestamp:
            live.update(frame.iloc[cursor]["timestamp"], frame.iloc[cursor].to_dict())
            cursor += 1
        np.testing.assert_allclose(transform.transform(live.sample(sample.timestamp)), full.transform(sample), equal_nan=True)
    assert not any("event" in name or "truth" in name for name in a.order)


def test_ground_difference_only_concurrent_confirmed_observations(demo, config):
    settings = deepcopy(demo.settings["pipeline"])
    settings["ground_voltage_difference"] = True
    with pytest.raises(ValueError, match="confirmed units"):
        FeatureTransform(config.sensors, settings)
    sensors = demo.sensors[:2]
    transform = FeatureTransform(sensors, settings)
    aligner = CausalAligner(sensors, stale_action="missing_indicator")
    aligner.update(stamp(), {"ground_voltage_a": "3", "ground_voltage_b": "1"})
    first = transform.transform(aligner.sample(stamp()))
    assert first[transform.order.index("ground_voltage_difference__current_value")] == 2
    aligner.update(stamp(.1), {"ground_voltage_a": "4"})
    second = transform.transform(aligner.sample(stamp(.1)))
    assert np.isnan(second[transform.order.index("ground_voltage_difference__current_value")])


def event_frame():
    return pd.DataFrame({"timestamp": [stamp(i) for i in range(30)], "event_id": [f"e{i//5}" for i in range(30)], "device_id": ["d"] * 30})


def test_event_split_before_windows_is_disjoint(demo):
    parts, report = split_raw(event_frame(), demo.settings["pipeline"]["split"])
    assert set(parts["train"]["event_id"]).isdisjoint(parts["test"]["event_id"])
    assert sum(len(p) for p in parts.values()) == 30
    assert report["mode"] == "event"
    assert_event_isolation(parts)
    corrupt = {name: frame.copy() for name, frame in parts.items()}
    corrupt["test"].iloc[0, corrupt["test"].columns.get_loc("event_id")] = "e0"
    with pytest.raises(ValueError, match="Data leakage"):
        assert_event_isolation(corrupt)


def test_chronological_split_purge_and_crossing_event_rejection(demo):
    frame = event_frame().drop(columns="event_id")
    settings = {"mode": "chronological", "ratios": [.6, .2, .2], "purge_gap_seconds": 1}
    parts, report = split_raw(frame, settings)
    assert parts["train"]["timestamp"].max() < parts["validation"]["timestamp"].min()
    assert report["purged_rows"] == 6
    frame["event_id"] = "same_event"
    with pytest.raises(ValueError, match="Data leakage"):
        split_raw(frame, settings)


@pytest.mark.parametrize("method", ["standard", "minmax", "robust"])
def test_scaler_train_only_and_saved_realtime_parity(tmp_path, method):
    order = ["sensor__current_value", "sensor__missing"]
    values = np.array([[1, 0], [3, 0], [np.nan, 1]], dtype=float)
    scaler = FrozenScaler(order, method)
    with pytest.raises(ValueError, match="only on train"):
        scaler.fit(np.array([[10000, 0]]), split="test")
    scaler.fit(values, split="train")
    before = scaler.offset.copy()
    holdout = np.array([[10000, 0], [np.nan, 1]])
    result = scaler.transform(holdout, order)
    np.testing.assert_array_equal(scaler.offset, before)
    assert scaler.fill[0] == 2 and result[1, 1] == 1
    path = tmp_path / "scaler.json"
    scaler.save(path)
    np.testing.assert_allclose(FrozenScaler.load(path).transform(holdout, order), result)
    with pytest.raises(ValueError, match="order"):
        scaler.transform(holdout, order[::-1])
    with pytest.raises(ValueError, match="refitted"):
        scaler.fit(values, split="train")


def test_scaler_rejects_feature_missing_in_all_training_rows():
    with pytest.raises(ValueError, match="no valid training"):
        FrozenScaler(["sensor__current_value"], "standard").fit(np.array([[np.nan]]), split="train")


def test_window_shape_horizon_and_gaps():
    metadata = pd.DataFrame({"timestamp": [stamp(i) for i in range(6)]})
    X = np.arange(12, dtype=np.float32).reshape(6, 2)
    labels = [0, 0, 1, 1, 0, 1]
    settings = {"sequence_length": 3, "stride": 1, "label_horizon_seconds": 1}
    result = build_windows(X, metadata, labels, np.ones(6, dtype=bool), settings, period_seconds=1)
    assert result["X"].shape == (3, 3, 2)
    np.testing.assert_array_equal(result["X"][0], X[:3])
    assert result["y"][0] == labels[3]
    assert result["end_timestamp"][0] == stamp(2).isoformat()
    assert result["target_timestamp"][0] == stamp(3).isoformat()
    valid = np.array([True, False, True, True, True, True])
    assert len(build_windows(X, metadata, labels, valid, settings, period_seconds=1)["y"]) == 1
    metadata.loc[2, "timestamp"] = stamp(2.5)
    assert not len(build_windows(X, metadata, labels, np.ones(6, bool), settings, period_seconds=1)["y"])


def test_unlabeled_and_unknown_labels_never_normal():
    labels, status = map_labels(pd.Series(["", "UNLABELED", "normal"]), {"mapping": None})
    assert labels == [-1, -1, -1] and status == "UNLABELED"
    with pytest.raises(ValueError, match="Unknown"):
        map_labels(pd.Series(["invented"]), {"mapping": {"normal": 0, "risk": 1}})
    assert map_labels(pd.Series(["normal", "risk", ""]), {"mapping": {"normal": 0, "risk": 1}})[0] == [0, 1, -1]


def test_event_export_pre_post_and_detection_truth():
    frame = pd.DataFrame({"timestamp": [stamp(i) for i in range(5)], "event_timestamp": [stamp(2).isoformat()] * 5,
                          "event_id": ["../untrusted"] * 5, "device_id": ["d"] * 5, "source": ["monitoring"] * 5,
                          "ground_truth": ["normal", "normal", "risk", "normal", "normal"], "acquisition_kind": ["lab_experiment"] * 5})
    index, segments = extract_events(frame, {"pre_event_seconds": 1, "post_event_seconds": 1}, {"naive_policy": "reject", "output_timezone": "UTC"})
    assert index.iloc[0]["ground_truth"] == "risk"
    assert segments["../untrusted"]["event_phase"].tolist() == ["pre", "detection", "post"]


def test_parquet_null_is_non_observation_but_nan_invalid(tmp_path):
    path = tmp_path / "null.parquet"
    table = pa.table({"timestamp": [stamp(i).isoformat() for i in range(3)], "ground_voltage_a": pa.array([1.0, None, float("nan")], type=pa.float64())})
    pq.write_table(table, path)
    values = load_raw(path, source="monitoring").frame["ground_voltage_a"]
    assert values.iloc[1] is None and np.isnan(values.iloc[2])


def test_offline_interpolation_is_marked_noncausal():
    frame = pd.DataFrame({"x": [1, np.nan, 3]}, index=pd.date_range("2026-01-01", periods=3, freq="s"))
    result = interpolate_for_analysis(frame)
    assert result.iloc[1, 0] == 2 and result.attrs["causal"] is False


def prepare_synthetic(demo, tmp_path):
    settings = read_yaml(ROOT / "configs/synthetic_phase2.yaml")
    frame = generate_frame(demo, settings)
    path = tmp_path / "raw" / "sample.csv"
    save_synthetic(frame, path, demo, settings, inject_faults=False)
    return path


def test_full_dataset_build_manifest_artifacts_and_no_leakage(demo, tmp_path):
    path = prepare_synthetic(demo, tmp_path)
    original = path.read_bytes()
    output = build_dataset(demo, [path])
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert not manifest["supervised_training_ready"] and manifest["label_status"] == "UNLABELED"
    scaler = json.loads((output / "scaler.json").read_text())
    assert scaler["fit_split"] == "train"
    assert scaler["training_rows"] == manifest["aligned_rows"]["train"]
    events = {}
    for split in ["train", "validation", "test"]:
        with np.load(output / f"{split}.npz", allow_pickle=False) as data:
            assert data["X"].shape[1:] == (16, 20)
            assert np.isfinite(data["X"]).all() and (data["y"] == -1).all()
            assert data["feature_order"].tolist() == manifest["feature_order"]
            events[split] = set(data["event_id"].tolist())
            assert set(data["acquisition_kind"]) == {"synthetic"}
    assert events["train"].isdisjoint(events["test"])
    assert events["validation"].isdisjoint(events["test"])
    assert path.read_bytes() == original
    with pytest.raises(FileExistsError):
        build_dataset(demo, [path])


def test_build_rejects_overlap_provenance_and_unusable_output(demo, tmp_path):
    path = prepare_synthetic(demo, tmp_path)
    with pytest.raises(ValueError, match="Overlapping"):
        build_dataset(demo, [path, path])
    settings = deepcopy(demo.settings)
    settings["input"]["acquisition_kind"] = "field_measurement"
    with pytest.raises(ValueError, match="provenance|Synthetic"):
        build_dataset(replace(demo, settings=settings), [path])
    with pytest.raises(ValueError, match="outside"):
        build_dataset(demo, [path], output=path.parent / "processed")
    settings = deepcopy(demo.settings)
    settings["pipeline"]["windows"]["sequence_length"] = 100000
    output = tmp_path / "failed-output"
    with pytest.raises(ValueError, match="no usable windows"):
        build_dataset(replace(demo, settings=settings), [path], output=output)
    assert not output.exists()
    assert not list(tmp_path.glob(".dataset-build-*"))


def test_production_cli_reports_configuration_failure(config):
    assert main(["--config", str(config.path)]) == 2


def test_window_module_defends_against_cross_event_input():
    values = np.arange(6, dtype=np.float32).reshape(6, 1)
    metadata = pd.DataFrame({"timestamp": [stamp(i) for i in range(6)], "event_id": ["a"] * 3 + ["b"] * 3})
    result = build_windows(values, metadata, [0] * 6, np.ones(6, bool),
                           {"sequence_length": 3, "stride": 1, "label_horizon_seconds": 0}, period_seconds=1)
    assert len(result["y"]) == 2


@pytest.mark.parametrize("method", ["standard", "minmax", "robust"])
def test_validation_outlier_does_not_change_train_scaler(demo, tmp_path, method):
    path = prepare_synthetic(demo, tmp_path)
    settings = deepcopy(demo.settings)
    settings["pipeline"]["scaler"] = method
    cfg = replace(demo, settings=settings)
    original = build_dataset(cfg, [path], output=tmp_path / "first")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.loc[frame["event_id"].eq("synthetic-0003"), "ground_voltage_a"] = "100000000"
    changed = tmp_path / "changed-raw" / "changed.csv"
    changed.parent.mkdir()
    frame.to_csv(changed, index=False)
    result = build_dataset(cfg, [changed], output=tmp_path / "second")
    assert (original / "scaler.json").read_bytes() == (result / "scaler.json").read_bytes()


def test_drop_window_removes_sequences_touching_missing_row():
    values = np.arange(8, dtype=np.float32).reshape(8, 1)
    meta = pd.DataFrame({"timestamp": [stamp(i) for i in range(8)]})
    valid = np.ones(8, bool)
    valid[3] = False
    output = build_windows(values, meta, [0] * 8, valid,
                           {"sequence_length": 3, "stride": 1, "label_horizon_seconds": 0}, period_seconds=1)
    assert output["start_timestamp"].tolist() == [stamp(0).isoformat(), stamp(4).isoformat(), stamp(5).isoformat()]


def test_source_comparison_preserves_independent_rates(tmp_path, config):
    configs = []
    for kind, period in [("field_measurement", .1), ("lab_experiment", 1)]:
        folder = tmp_path / kind
        folder.mkdir()
        pd.DataFrame({"timestamp": [stamp(0).isoformat(), stamp(period).isoformat()], "ground_voltage_a": ["1", "2"],
                      "acquisition_kind": [kind] * 2}).to_csv(folder / "raw.csv", index=False)
        settings = deepcopy(config.settings)
        settings["input"].update(directory=str(folder), acquisition_kind=kind)
        configs.append(replace(config, settings=settings, sensors=(replace(config.sensors[0], nominal_sampling_period=period),)))
    result = compare_sources(*configs)
    assert result["sensor_comparison"][0]["field_nominal_period"] == .1
    assert result["sensor_comparison"][0]["lab_nominal_period"] == 1
    assert not result["sensor_comparison"][0]["units_confirmed_equal"]


def test_source_comparison_rejects_synthetic_measurements(tmp_path, config):
    configs = []
    for kind in ["field_measurement", "lab_experiment"]:
        folder = tmp_path / kind
        folder.mkdir()
        pd.DataFrame({"timestamp": [stamp().isoformat()], "ground_voltage_a": ["1"], "is_synthetic": ["true"]}).to_csv(folder / "raw.csv", index=False)
        settings = deepcopy(config.settings)
        settings["input"].update(directory=str(folder), acquisition_kind=kind)
        configs.append(replace(config, settings=settings, sensors=(config.sensors[0],)))
    with pytest.raises(ValueError, match="synthetic"):
        compare_sources(*configs)


def test_fractional_duration_includes_final_synthetic_tick(demo):
    settings = read_yaml(ROOT / "configs/synthetic_phase2.yaml")
    frame = generate_frame(demo, settings)
    assert len(frame) == 3600
    assert pd.Timestamp(frame["timestamp"].iloc[-1]) == stamp(359.9)


def test_metadata_labels_do_not_change_features_and_synthetic_never_ready(demo, tmp_path):
    path = prepare_synthetic(demo, tmp_path)
    settings = deepcopy(demo.settings)
    settings["pipeline"]["labeling"]["mapping"] = {"normal": 0, "risk": 1}
    cfg = replace(demo, settings=settings)
    before = build_dataset(cfg, [path], output=tmp_path / "unlabeled")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame["ground_truth"] = "risk"
    changed = tmp_path / "changed-raw" / "labels.csv"
    changed.parent.mkdir()
    frame.to_csv(changed, index=False)
    after = build_dataset(cfg, [changed], output=tmp_path / "labeled")
    manifest = json.loads((after / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["label_status"] == "LABELED" and not manifest["supervised_training_ready"]
    for split in ["train", "validation", "test"]:
        with np.load(before / f"{split}.npz", allow_pickle=False) as a, np.load(after / f"{split}.npz", allow_pickle=False) as b:
            np.testing.assert_array_equal(a["X"], b["X"])
            assert (a["y"] == -1).all() and (b["y"] == 1).all()
