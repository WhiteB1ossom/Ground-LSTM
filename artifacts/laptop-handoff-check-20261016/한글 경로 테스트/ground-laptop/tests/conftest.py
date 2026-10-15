from pathlib import Path

import pytest

from src.utils.config import load_config, read_yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def config():
    return load_config(ROOT / "configs/preprocessing.yaml")


@pytest.fixture
def synthetic_settings():
    return read_yaml(ROOT / "configs/synthetic.yaml")
