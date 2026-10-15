from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from src.data.loader import load_raw
from src.data.quality import inspect_quality
from src.data.schema import RawDataset
from src.data.synthetic import generate_frame
from src.data.inspect import main as inspect_main
from src.utils.config import read_yaml


@pytest.mark.parametrize("body", ["timestamp,value\na,1,extra\n", "timestamp,value\na\n", "timestamp,value\n\n", "timestamp,\na,1\n", ""])
def test_malformed_csv_never_silently_discards_data(tmp_path, body):
    path = tmp_path / "bad.csv"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        load_raw(path, source="monitoring")


def test_disabled_sensor_does_not_require_column(config):
    cfg = replace(config, sensors=(replace(config.sensors[0], enabled=False),))
    raw = RawDataset(pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z"]}), Path("raw.csv"), "monitoring", "a" * 64)
    assert not inspect_quality(raw, cfg)["summary"]["has_invalid_data"]


@pytest.mark.parametrize("middle", ["NaN", "Inf", "bad"])
def test_invalid_observation_breaks_flatline(config, middle):
    settings = deepcopy(config.settings)
    settings["quality"]["flatline_seconds"] = 0.2
    cfg = replace(config, sensors=(config.sensors[0],), settings=settings)
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=3, freq="100ms", tz="UTC"),
                          "ground_voltage_a": ["1", middle, "1"]})
    raw = RawDataset(frame, Path("raw.csv"), "monitoring", "a" * 64)
    assert "FLATLINE" not in inspect_quality(raw, cfg)["summary"]["reason_counts"]


def test_unobserved_gap_does_not_prove_flatline(config):
    settings = deepcopy(config.settings)
    settings["quality"]["flatline_seconds"] = 1
    cfg = replace(config, sensors=(config.sensors[0],), settings=settings)
    frame = pd.DataFrame({"timestamp": ["2026-01-01T00:00:00Z", "2026-01-01T00:00:30Z"], "ground_voltage_a": ["1", "1"]})
    raw = RawDataset(frame, Path("raw.csv"), "monitoring", "a" * 64)
    assert "FLATLINE" not in inspect_quality(raw, cfg)["summary"]["reason_counts"]


def test_nonintegral_synthetic_period_rejected(config, synthetic_settings):
    settings = deepcopy(synthetic_settings)
    settings["base_period_seconds"] = 0.3
    with pytest.raises(ValueError, match="integer multiples"):
        generate_frame(config, settings)


def test_malformed_quoting_returns_cli_error(tmp_path, config):
    path = tmp_path / "bad.csv"
    path.write_text('timestamp,value\n"unfinished,1\n', encoding="utf-8")
    assert inspect_main(["--config", str(config.path), "--input", str(path)]) == 2


@pytest.mark.parametrize("content", ["schema_version: 1\nx: [", "schema_version: true\n"])
def test_malformed_yaml_returns_clear_error(tmp_path, content):
    path = tmp_path / "bad.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        read_yaml(path)
