import numpy as np
import pandas as pd
import pytest

from src.dataset.build import _blocks
from src.dataset.windows import build_windows
from src.realtime.reader import PacketAssembler


def test_acquisition_blocks_ignore_truth_event_boundaries():
    frame = pd.DataFrame({"device_id": ["one"] * 5, "session_id": ["session"] * 5, "event_id": ["normal", "normal", "risk", "risk", "normal"]})
    assert len(list(_blocks(frame, "acquisition"))) == 1
    assert len(list(_blocks(frame, "event_fixture"))) == 3


def test_event_transition_allowed_only_with_explicit_policy():
    metadata = pd.DataFrame({"timestamp": pd.date_range("2026-01-01", periods=4, freq="s", tz="UTC"),
                             "device_id": ["one"] * 4, "session_id": ["session"] * 4, "event_id": ["normal", "normal", "risk", "risk"]})
    options = {"sequence_length": 3, "stride": 1, "label_horizon_seconds": 0}
    assert len(build_windows(np.ones((4, 1)), metadata, [0, 0, 1, 1], np.ones(4, dtype=bool), options, period_seconds=1)["y"]) == 0
    result = build_windows(np.ones((4, 1)), metadata, [0, 0, 1, 1], np.ones(4, dtype=bool), {**options, "allow_event_crossing": True}, period_seconds=1)
    assert result["y"].tolist() == [1, 1]


def test_packet_merge_and_duplicate_late_errors():
    reader = PacketAssembler(["a", "b"], device_id="one", source="monitoring", acquisition_kind="lab_experiment")
    t = pd.Timestamp("2026-01-01T00:00:00Z")
    assert reader.push(t, "a", 1) == []
    assert reader.push(t, "b", 2) == []
    with pytest.raises(ValueError, match="Duplicate"): reader.push(t, "a", 3)
    ready = reader.push(t + pd.Timedelta(seconds=1), "a", 3)
    assert ready[0]["a"] == 1 and ready[0]["b"] == 2
    with pytest.raises(ValueError, match="Late"): reader.push(t, "b", 1)
