from collections import deque
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.realtime.ring_buffer import RingBuffer, buffer_capacity
from src.realtime.sequence_builder import SequenceBuilder
from src.realtime.buffer_demo import run_demo


def stamp(i): return pd.Timestamp("2026-01-01T00:00:00Z") + pd.Timedelta(milliseconds=100 * i)


@pytest.mark.parametrize("capacity", [1, 2, 7])
def test_wraparound_matches_reference_and_storage_never_grows(capacity):
    ring, reference = RingBuffer(capacity, 2), deque(maxlen=capacity)
    storage = (id(ring._values), id(ring._timestamps), id(ring._valid), ring.storage_bytes)
    for i in range(100):
        vector = np.array([i, -i], dtype=np.float32)
        ring.append(stamp(i), vector, valid=i % 3 != 0)
        reference.append((vector.copy(), stamp(i).value, i % 3 != 0))
        snapshot = ring.snapshot()
        assert ring.size <= capacity
        np.testing.assert_array_equal(snapshot.values, np.stack([row[0] for row in reference]))
        np.testing.assert_array_equal(snapshot.timestamps_ns, [row[1] for row in reference])
        np.testing.assert_array_equal(snapshot.valid, [row[2] for row in reference])
    assert ring.overwritten_samples == 100 - capacity
    assert storage == (id(ring._values), id(ring._timestamps), id(ring._valid), ring.storage_bytes)
    assert ring.storage_bytes == capacity * (2 * 4 + 8 + 1)


@pytest.mark.parametrize("capacity,features", [(0, 1), (-1, 1), (True, 1), (1, 0), (1.5, 2)])
def test_invalid_dimensions(capacity, features):
    with pytest.raises(ValueError): RingBuffer(capacity, features)


def test_rejected_sample_does_not_modify_full_ring():
    ring = RingBuffer(2, 1)
    ring.append(stamp(0), [1])
    ring.append(stamp(1), [2])
    before = ring.snapshot()
    revision = ring.revision
    for time, row in [(stamp(1), [3]), (stamp(0), [3]), (stamp(2), [np.nan]), (stamp(2), [1e100]), (stamp(2), [1, 2]), (pd.Timestamp("2026-01-01"), [1])]:
        with pytest.raises(ValueError): ring.append(time, row)
        np.testing.assert_array_equal(ring.snapshot().values, before.values)
        assert ring.revision == revision and ring.overwritten_samples == 0


def test_snapshot_is_detached_and_clear_reuses_storage():
    ring = RingBuffer(2, 1)
    assert ring.snapshot().values.shape == (0, 1)
    source = np.array([1], dtype=np.float32)
    ring.append(stamp(0), source)
    source[0] = 99
    snapshot = ring.snapshot()
    assert snapshot.values[0, 0] == 1
    with pytest.raises(ValueError): snapshot.values[0, 0] = 99
    snapshot.values.flags.writeable = True
    snapshot.values[0, 0] = 99
    assert ring.snapshot().values[0, 0] == 1
    storage = id(ring._values)
    ring.clear()
    assert ring.size == 0 and id(ring._values) == storage
    ring.append(stamp(0), [2])
    assert ring.snapshot().values[0, 0] == 2


def test_latest_subset_and_copy_into_reusable_arrays():
    ring = RingBuffer(4, 1)
    for i in range(7): ring.append(stamp(i), [i])
    output, times, valid = np.empty((2, 1), np.float32), np.empty(2, np.int64), np.empty(2, bool)
    ring.copy_latest_into(output, times, valid)
    np.testing.assert_array_equal(output[:, 0], [5, 6])
    np.testing.assert_array_equal(times, [stamp(5).value, stamp(6).value])
    for count in [-1, 5, True]:
        with pytest.raises(ValueError): ring.snapshot(count)
    with pytest.raises(ValueError): ring.copy_latest_into(output.astype(float), times, valid)


def test_sequence_warmup_stride_duplicate_and_wrap():
    ring = RingBuffer(5, 2)
    builder = SequenceBuilder(ring, 3, .1, stride=2)
    tensor = np.empty((1, 3, 2), np.float32)
    ready = []
    for i in range(10):
        ring.append(stamp(i), [i, -i])
        status = builder.build_into(tensor)
        if i < 2: assert status.reason == "WARMING_UP"
        elif (i - 2) % 2: assert status.reason == "WAITING_FOR_STRIDE"
        else:
            assert status.ready and status.end_timestamp_ns == stamp(i).value
            np.testing.assert_array_equal(tensor[0, :, 0], [i - 2, i - 1, i])
            assert builder.build_into(tensor).reason == "NO_NEW_SAMPLE"
            ready.append(i)
    assert ready == [2, 4, 6, 8]


def test_invalid_and_time_gap_windows_recover_when_old_rows_expire():
    ring = RingBuffer(3, 1)
    builder = SequenceBuilder(ring, 3, .1)
    tensor = np.empty((1, 3, 1), np.float32)
    for i in range(3): ring.append(stamp(i), [i], valid=i != 1)
    assert builder.build_into(tensor).reason == "INVALID_WINDOW"
    ring.append(stamp(4), [4])
    ring.append(stamp(5), [5])
    assert builder.build_into(tensor).reason == "TIMESTAMP_GAP"
    ring.append(stamp(6), [6])
    assert builder.build_into(tensor).ready
    ring.clear()
    assert builder.build_into(tensor).reason == "WARMING_UP"
    for i in range(3): ring.append(stamp(i), [i])
    assert builder.build_into(tensor).ready


def test_capacity_and_sequence_config_checks():
    assert buffer_capacity(16, 5, .1) == 66
    assert buffer_capacity(16, 0, .1) == 16
    assert buffer_capacity(16, .25, .1) == 19
    for args in [(0, 5, .1), (16, -1, .1), (16, 5, 0), (16, float("nan"), .1)]:
        with pytest.raises(ValueError): buffer_capacity(*args)
    with pytest.raises(ValueError): SequenceBuilder(RingBuffer(2, 1), 3, .1)
    with pytest.raises(ValueError): SequenceBuilder(RingBuffer(3, 1), 3, 0)


def test_e2e_buffer_demo_matches_offline_final_window(tmp_path):
    root = Path(__file__).resolve().parents[1]
    # Generate independent fixtures: tests must also pass in a clean checkout
    # where ignored raw data and previously built artifacts do not exist.
    from dataclasses import replace
    from src.utils.config import load_config, read_yaml
    from src.data.synthetic import generate_frame, save_synthetic
    from src.dataset.build import build_dataset
    config = load_config(root / "configs/preprocessing_demo.yaml")
    settings = deepcopy(config.settings)
    settings["report"]["directory"] = str(tmp_path / "quality")
    settings["pipeline"]["output_directory"] = str(tmp_path / "processed")
    settings["pipeline"]["scaler_directory"] = str(tmp_path / "scalers")
    config = replace(config, settings=settings)
    synthetic = read_yaml(root / "configs/synthetic_phase2.yaml")
    raw = tmp_path / "raw" / "synthetic.csv"
    save_synthetic(generate_frame(config, synthetic), raw, config, synthetic, inject_faults=False)
    dataset = build_dataset(config, [raw])
    result = run_demo(dataset, root / "configs/realtime_demo.yaml", tmp_path / "demo.json")
    assert result["replayed_samples"] == 3600
    assert result["buffer_capacity"] == result["final_buffer_size"] == 66
    assert result["overwritten_samples"] == 6 * (600 - 66)
    assert result["status_counts"]["READY"] == 441 + 147 + 294
    assert result["buffer_storage_bytes"] == 66 * (20 * 4 + 8 + 1)
    assert not result["model_inference_performed"]
    with np.load(tmp_path / "demo.snapshot.npz", allow_pickle=False) as snapshot:
        # Check a retained timestamp against offline data, not just buffer code.
        frame = pd.read_parquet(dataset / "test.aligned.parquet")
        from src.preprocessing.scaling import FrozenScaler
        scaler = FrozenScaler.load(dataset / "scaler.json")
        expected = scaler.transform(frame.iloc[-66:][scaler.order].to_numpy(dtype=float), scaler.order)
        np.testing.assert_allclose(snapshot["values"], expected)
    with pytest.raises(FileExistsError): run_demo(dataset, root / "configs/realtime_demo.yaml", tmp_path / "demo.json")
