import pandas as pd
import pytest

from src.dataset.split import assert_event_isolation, split_raw


def test_reused_ids_across_devices_are_distinct():
    a = pd.DataFrame({"device_id": ["one"], "event_id": ["event"]})
    b = pd.DataFrame({"device_id": ["two"], "event_id": ["event"]})
    assert_event_isolation({"train": a, "test": b})
    with pytest.raises(ValueError, match="leakage"): assert_event_isolation({"train": a, "test": a.copy()})


def test_split_uses_device_event_pair():
    frame = pd.DataFrame({"device_id": ["one", "two", "three"], "event_id": ["event"] * 3,
                          "timestamp": pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")})
    parts, report = split_raw(frame, {"mode": "event", "ratios": [.6, .2, .2], "purge_gap_seconds": 0})
    assert all(len(part) == 1 for part in parts.values())
    assert_event_isolation(parts)
