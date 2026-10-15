from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.data.inspect import main as inspect_main
from src.data.loader import discover_inputs, load_raw
from src.data.quality import inspect_quality
from src.data.report import save_report
from src.data.schema import RawDataset, parse_timestamp
from src.data.synthetic import generate_frame, save_synthetic
from src.utils.config import load_config
from scripts.generate_synthetic_data import main as generate_main


def dataset(frame):
    return RawDataset(frame, Path("fixture.csv").resolve(), "monitoring", "a" * 64)


def sensor_config(config, **overrides):
    return replace(config, sensors=(replace(config.sensors[0], **overrides),))


def reasons(report):
    return report["summary"]["reason_counts"]


def test_unknown_physical_values_remain_null(config):
    for sensor in config.sensors:
        assert sensor.threshold is sensor.expected_min is sensor.expected_max is sensor.max_staleness is sensor.unit is None
    assert config.sensors[6].nominal_sampling_period is None


@pytest.mark.parametrize("format", ["csv", "parquet"])
def test_raw_loader_preserves_values_order_and_file(tmp_path, config, format):
    frame = pd.DataFrame({"timestamp": ["2026-01-01T00:00:02Z", "bad", "2026-01-01T00:00:01Z"],
                          "ground_voltage_a": ["999999", "NaN", "Inf"], "event_id": ["001", "", "002"]})
    path = tmp_path / f"raw.{format}"
    if format == "csv":
        frame.to_csv(path, index=False)
    else:
        frame.to_parquet(path, index=False)
    original = path.read_bytes()
    raw = load_raw(path, source="monitoring")
    pd.testing.assert_frame_equal(raw.frame, frame)
    before = raw.frame.copy(deep=True)
    inspect_quality(raw, sensor_config(config, expected_max=1))
    pd.testing.assert_frame_equal(raw.frame, before)
    assert path.read_bytes() == original
    assert raw.sha256 == hashlib.sha256(original).hexdigest()


def test_timestamp_error_codes_and_device_isolation(config):
    frame = pd.DataFrame({"timestamp": ["bad", "2026-01-01T00:00:00", "2026-01-01T00:00:02Z",
                                       "2026-01-01T00:00:02Z", "2026-01-01T00:00:01Z", "2026-01-01T00:00:01Z"],
                          "device_id": ["a", "a", "a", "a", "a", "b"], "ground_voltage_a": ["1"] * 6})
    counts = reasons(inspect_quality(dataset(frame), sensor_config(config)))
    assert counts["TIMESTAMP_PARSE_FAILED"] == counts["TIMESTAMP_TIMEZONE_MISSING"] == 1
    assert counts["TIMESTAMP_DUPLICATE"] == counts["TIMESTAMP_REVERSED"] == 1


def test_explicit_timezone_localization(config):
    settings = {"naive_policy": "localize", "naive_timezone": "Asia/Seoul", "output_timezone": "UTC"}
    stamp, reason = parse_timestamp("2026-01-01T09:00:00", settings)
    assert reason is None and stamp == pd.Timestamp("2026-01-01T00:00:00Z")
    stamp, reason = parse_timestamp("2026-01-01T09:00:00+09:00", config.settings["timestamp"])
    assert reason is None and stamp == pd.Timestamp("2026-01-01T00:00:00Z")


@pytest.mark.parametrize("value", ["", "NaT", "invalid", "1700000000", 1700000000])
def test_bad_timestamp_never_assumes_epoch_units(value, config):
    stamp, reason = parse_timestamp(value, config.settings["timestamp"])
    assert pd.isna(stamp) and reason == "TIMESTAMP_PARSE_FAILED"


@pytest.mark.parametrize("stamp", ["2026-03-08T02:30:00", "2026-11-01T01:30:00"])
def test_dst_ambiguity_is_not_silently_guessed(stamp):
    parsed, reason = parse_timestamp(stamp, {"naive_policy": "localize", "naive_timezone": "America/New_York", "output_timezone": "UTC"})
    assert pd.isna(parsed) and reason == "TIMESTAMP_PARSE_FAILED"


def test_missing_nan_inf_non_numeric_range_and_status(config):
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=6, freq="100ms", tz="UTC"),
                          "ground_voltage_a": ["", "NaN", "Inf", "broken", "-2", "999999"],
                          "sensor_status": ["OK", "FAULT", "OK", "OK", "OK", ""],
                          "communication_status": ["OK", "OK", "ERROR", "OK", "OK", "OK"]})
    report = inspect_quality(dataset(frame), sensor_config(config, expected_min=0, expected_max=1))
    counts = reasons(report)
    for code in ["MISSING_VALUE", "NAN_VALUE", "INF_VALUE", "NON_NUMERIC_VALUE", "SENSOR_STATUS_ABNORMAL", "COMMUNICATION_ERROR", "STATUS_MISSING"]:
        assert counts[code] == 1
    assert counts["OUTSIDE_EXPECTED_RANGE"] == 2
    assert all(issue["category"] == "review" for issue in report["issues"] if issue["reason_code"] == "OUTSIDE_EXPECTED_RANGE")
    assert report["sensors"]["ground_voltage_a"]["missing_value_ratio"] == pytest.approx(4 / 6)


def test_large_jump_has_no_automatic_invalidity(config):
    frame = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:00.1Z"],
                          "ground_voltage_a": ["0", "1000000000"]})
    report = inspect_quality(dataset(frame), sensor_config(config))
    assert not report["summary"]["has_invalid_data"]
    assert reasons(report) == {}


def test_multirate_cadence_uses_actual_observations(config, synthetic_settings):
    frame = generate_frame(config, synthetic_settings)
    report = inspect_quality(dataset(frame), config)
    assert "SAMPLING_INTERVAL_DEVIATION" not in reasons(report)
    sensors = report["sensors"]
    assert sensors["ground_voltage_a"]["observed_interval_seconds"]["median"] == pytest.approx(0.1)
    assert sensors["leakage_current"]["observed_interval_seconds"]["median"] == 1
    assert sensors["limiter_temp_a"]["observed_interval_seconds"]["median"] == 60
    assert frame["limiter_temp_a"].ne("").sum() == 4
    assert not report["summary"]["has_invalid_data"]


def test_missing_observation_cadence_deviation(config):
    frame = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:00.1Z", "2026-01-01T00:00:00.2Z"],
                          "ground_voltage_a": ["1", "", "2"]})
    report = inspect_quality(dataset(frame), sensor_config(config))
    assert reasons(report)["SAMPLING_INTERVAL_DEVIATION"] == 1


def test_flatline_only_when_configured(config):
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=5, freq="100ms", tz="UTC"),
                          "ground_voltage_a": ["1"] * 5})
    cfg = sensor_config(config)
    assert "FLATLINE" not in reasons(inspect_quality(dataset(frame), cfg))
    settings = deepcopy(cfg.settings)
    settings["quality"]["flatline_seconds"] = 0.2
    report = inspect_quality(dataset(frame), replace(cfg, settings=settings))
    assert reasons(report)["FLATLINE"] == 1
    assert report["issues"][0]["category"] == "review"


def test_sensor_and_empty_schema_report(config):
    report = inspect_quality(dataset(pd.DataFrame({"timestamp": []})), config)
    assert reasons(report)["SENSOR_COLUMN_MISSING"] == 10
    assert reasons(report)["EMPTY_DATASET"] == 1
    assert report["label_status"] == "UNLABELED"


@pytest.mark.parametrize("values,expected", [([], "UNLABELED"), (["", "UNLABELED"], "UNLABELED"), (["0", ""], "PARTIALLY_LABELED"), (["0", "1"], "LABELED")])
def test_no_labels_invented(config, values, expected):
    frame = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"] * len(values), "ground_truth": values})
    assert inspect_quality(dataset(frame), config)["label_status"] == expected


def test_synthetic_reproducible_and_explicitly_unlabeled(config, synthetic_settings):
    a, b = generate_frame(config, synthetic_settings), generate_frame(config, synthetic_settings)
    pd.testing.assert_frame_equal(a, b)
    assert set(a["synthetic_state"]) == {"normal", "approaching_risk", "lightning_event", "recovery"}
    assert set(a["ground_truth"]) == {"UNLABELED"}
    assert set(a["is_synthetic"]) == {"true"}


@pytest.mark.parametrize("format", ["csv", "parquet"])
def test_synthetic_file_metadata_and_overwrite_protection(config, synthetic_settings, tmp_path, format):
    output = tmp_path / f"synthetic.{format}"
    frame = generate_frame(config, synthetic_settings, inject_faults=True)
    metadata = save_synthetic(frame, output, config, synthetic_settings, inject_faults=True)
    document = json.loads(metadata.read_text(encoding="utf-8"))
    assert document["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert document["is_synthetic"] and document["labels"] == "UNLABELED"
    raw = load_raw(output, source="monitoring")
    report = inspect_quality(raw, config)
    assert report["dataset"]["synthetic"]
    for code in ["TIMESTAMP_PARSE_FAILED", "TIMESTAMP_DUPLICATE", "TIMESTAMP_REVERSED", "NAN_VALUE", "INF_VALUE", "COMMUNICATION_ERROR", "SENSOR_STATUS_ABNORMAL"]:
        assert code in reasons(report)
    with pytest.raises(FileExistsError):
        save_synthetic(frame, output, config, synthetic_settings, inject_faults=False)


def test_source_isolation_and_required_timestamp(tmp_path):
    path = tmp_path / "raw.csv"
    path.write_text("timestamp,source\n2026-01-01T00:00:00Z,surge\n", encoding="utf-8")
    with pytest.raises(ValueError, match="separate source"):
        load_raw(path, source="monitoring")
    path.write_text("value\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="timestamp column"):
        load_raw(path, source="monitoring")
    path.write_text("timestamp,timestamp\na,b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_raw(path, source="monitoring")


def test_reports_json_markdown_and_raw_directory_guard(tmp_path, config):
    frame = pd.DataFrame({"timestamp": ["bad"], "ground_voltage_a": ["Inf"]})
    raw_path = tmp_path / "input.csv"
    frame.to_csv(raw_path, index=False)
    report = inspect_quality(load_raw(raw_path, source="monitoring"), sensor_config(config))
    json_path, md_path = save_report(report, tmp_path / "reports")
    assert json.loads(json_path.read_text(encoding="utf-8")) == report
    assert "INF_VALUE" in md_path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="outside"):
        save_report(report, tmp_path)


def test_cli_end_to_end_and_exit_codes(tmp_path, config):
    sample = tmp_path / "raw" / "sample.csv"
    assert generate_main(["--config", str(config.path), "--output", str(sample)]) == 0
    assert inspect_main(["--config", str(config.path), "--input", str(sample), "--report-dir", str(tmp_path / "reports")]) == 0
    faulty = tmp_path / "raw" / "faulty.csv"
    assert generate_main(["--config", str(config.path), "--output", str(faulty), "--inject-faults"]) == 0
    assert inspect_main(["--config", str(config.path), "--input", str(faulty), "--report-dir", str(tmp_path / "reports")]) == 1
    assert inspect_main(["--config", str(config.path), "--input", str(tmp_path / "missing.csv")]) == 2
    assert generate_main(["--config", str(config.path), "--output", str(sample)]) == 2


@pytest.mark.parametrize("change", ["duplicate", "reserved", "negative_period", "inverted_range", "noncausal", "boolean_threshold", "string_enabled"])
def test_bad_sensor_config_rejected(tmp_path, config, change):
    settings = deepcopy(config.settings)
    sensors = [vars(spec).copy() for spec in config.sensors]
    if change == "duplicate":
        sensors[1]["name"] = sensors[0]["name"]
    elif change == "reserved":
        sensors[0]["name"] = "ground_truth"
    elif change == "negative_period":
        sensors[0]["nominal_sampling_period"] = -1
    elif change == "inverted_range":
        sensors[0].update(expected_min=10, expected_max=1)
    elif change == "noncausal":
        sensors[0]["missing_value_policy"] = "interpolation"
    elif change == "boolean_threshold":
        sensors[0]["threshold"] = True
    else:
        sensors[0]["enabled"] = "false"
    (tmp_path / "sensors.yaml").write_text(yaml.safe_dump({"schema_version": 1, "sensors": sensors}), encoding="utf-8")
    path = tmp_path / "preprocessing.yaml"
    path.write_text(yaml.safe_dump(settings), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_discovery_resolves_relative_to_config_not_cwd(tmp_path, config):
    settings = deepcopy(config.settings)
    settings["input"]["directory"] = "raw"
    cfg = replace(config, path=tmp_path / "config.yaml", settings=settings)
    folder = tmp_path / "raw"
    folder.mkdir()
    for file in ["a.csv", "b.parquet", "c.txt", "a.csv.metadata.json"]:
        (folder / file).touch()
    assert [p.name for p in discover_inputs(cfg)] == ["a.csv", "b.parquet"]
