"""Boundary tests for input ownership, file schemas and whole-window validity."""

from collections import deque
import json
from threading import Event

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.realtime.decision import DecisionEngine
from src.realtime.recorder import EventRecorder
from src.realtime.replay import observations
from src.realtime.ring_buffer import RingBuffer
from src.realtime.sequence_builder import SequenceBuilder
from src.realtime.service import RealtimeService
from src.realtime.stream import RealtimePipeline
from test_realtime_integration import FakeEngine, observation, settings


@pytest.mark.parametrize("suffix", [".csv", ".CSV", ".parquet", ".PARQUET"])
def test_stream_reader_supports_case_insensitive_formats(tmp_path, suffix):
    path = tmp_path / ("input" + suffix)
    frame = pd.DataFrame([observation(0., .9)])
    if suffix.lower() == ".csv": frame.to_csv(path, index=False)
    else: frame.to_parquet(path, index=False)
    rows = list(observations(path, ["v"]))
    assert len(rows) == 1 and float(rows[0]["v"]) == .9
    assert rows[0]["timestamp"] == frame["timestamp"].iloc[0]


@pytest.mark.parametrize("names", [["v"], ["timestamp", "v", "v"], ["timestamp", "v", " "]])
def test_parquet_schema_errors_are_rejected_before_yielding_rows(tmp_path, names):
    path = tmp_path / "input.parquet"
    arrays = [pa.array(["2026-01-01T00:00:00Z"] if name == "timestamp" else [.9]) for name in names]
    pq.write_table(pa.Table.from_arrays(arrays, names=names), path)
    with pytest.raises(ValueError, match="header"):
        next(observations(path, ["v"]))


@pytest.mark.parametrize("text", [
    'timestamp,v\n"2026-01-01T00:00:00Z,.9\n',
    "timestamp,v, \n2026-01-01T00:00:00Z,.9,x\n",
    "timestamp,v,v\n2026-01-01T00:00:00Z,.9,.1\n",
    "timestamp,v\n2026-01-01T00:00:00Z,.9,extra\n",
])
def test_malformed_csv_is_rejected_with_a_value_error(tmp_path, text):
    path = tmp_path / "input.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError): next(observations(path, ["v"]))


def test_unsupported_stream_format_fails_explicitly(tmp_path):
    path = tmp_path / "input.txt"
    path.write_text("timestamp,v\n2026-01-01T00:00:00Z,.9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported input format"):
        list(observations(path, ["v"]))


def test_queued_nested_metadata_is_detached_from_the_receiver():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    source = {**observation(0., .9), "metadata": {"tags": ["original"]}}
    service.submit(source)
    source["metadata"]["tags"][0] = "changed"
    stop, rows = Event(), []
    def emit(row):
        rows.append(row)
        stop.set()
    report = service.run(stop, emit)
    assert report["status"] == "SUCCESS"
    assert rows[0]["raw_observation"]["metadata"]["tags"] == ["original"]


def test_direct_off_grid_input_owns_metadata_until_the_next_sample():
    pipeline = RealtimePipeline(FakeEngine(), settings())
    source = {**observation(.05, .9), "metadata": {"tag": "original"}}
    assert not pipeline.feed(source)
    source["metadata"]["tag"] = "changed"
    row = pipeline.feed(observation(.15, .9))[0]
    assert row["raw_observation"]["metadata"]["tag"] == "original"


@pytest.mark.parametrize("value,valid", [(float("nan"), False), (None, True)])
def test_queue_copy_preserves_invalid_measurement_vs_non_observation(value, valid):
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    for t, v in [(0., .9), (.1, value)]: service.submit(observation(t, v))
    stop, rows = Event(), []
    def emit(row):
        rows.append(row)
        if len(rows) == 2: stop.set()
    service.run(stop, emit)
    assert rows[-1]["sample_valid"] is valid
    assert rows[-1]["physical_values"]["v"] == (.9 if valid else None)


def test_sample_and_window_flags_separate_warmup_error_and_recovery():
    pipeline = RealtimePipeline(FakeEngine(), settings())
    first = pipeline.feed(observation(0., .9))[0]
    assert first["sample_valid"] and not first["window_valid"]
    pipeline.feed(observation(.1, .9))
    assert pipeline.feed(observation(.2, .9))[0]["window_valid"]
    bad = pipeline.feed(observation(.3, "NaN"))[0]
    assert not bad["sample_valid"] and not bad["window_valid"]
    for t in (.4, .5):
        row = pipeline.feed(observation(t, .9))[0]
        assert row["sample_valid"] and not row["window_valid"] and not row["available"]
        assert row["input_status"] == "INVALID_WINDOW"
    recovered = pipeline.feed(observation(.6, .9))[0]
    assert recovered["sample_valid"] and recovered["window_valid"] and recovered["available"]


def test_inference_failure_does_not_mislabel_a_valid_input_window():
    engine = FakeEngine()
    def fail(tensor): raise RuntimeError("model unavailable")
    engine.predict = fail
    pipeline = RealtimePipeline(engine, settings())
    for t in (0., .1, .2): row = pipeline.feed(observation(t, .9))[0]
    assert row["sample_valid"] and row["window_valid"] and not row["available"]


def test_stride_wait_still_rejects_a_timestamp_gap():
    ring = RingBuffer(3, 1)
    builder = SequenceBuilder(ring, 3, .1, stride=2)
    output = np.empty((1, 3, 1), dtype=np.float32)
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    for i in (0, 1, 2): ring.append(start + pd.Timedelta(i * 100_000_000, unit="ns"), [1.])
    assert builder.build_into(output).ready
    ring.append(start + pd.Timedelta(400_000_000, unit="ns"), [1.])
    assert builder.build_into(output).reason == "TIMESTAMP_GAP"


def test_no_pre_history_required_means_pre_capture_is_complete(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=.1)
    recorder.consume({"timestamp_ns": 0}, DecisionEngine(.7, .4).update(0, .9, available=True))
    assert recorder.close()["saved_events"] == 1
    event = json.loads(next((tmp_path / "events").glob("*.json")).read_text(encoding="utf-8"))
    assert event["pre_history_complete"] and event["complete"]


def test_many_faults_and_wraps_keep_memory_bounded_and_window_flags_truthful(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=.2, post_seconds=.2, period_seconds=.1)
    pipeline = RealtimePipeline(FakeEngine(), settings(), recorder)
    ring = pipeline.ring
    allocation = (id(ring._values), id(ring._timestamps), id(ring._valid), ring.storage_bytes)
    recent = deque(maxlen=3)
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    try:
        for i in range(5000):
            is_bad = i % 47 == 46
            value = float("nan") if is_bad else .9
            source = {**observation(0., value), "timestamp": (start + pd.Timedelta(i * 100_000_000, unit="ns")).isoformat(),
                      "metadata": {"index": i}}
            row = pipeline.feed(source)[0]
            source["metadata"]["index"] = -1
            recent.append(not is_bad)
            assert row["window_valid"] is (len(recent) == 3 and all(recent))
            if not row["window_valid"]: assert not row["available"] and row["prediction"] is None
            assert ring.size <= ring.capacity
            assert len(recorder.history) <= recorder.history.maxlen
            assert len(recorder.raw_history) <= recorder.raw_history.maxlen
            assert len(recorder.active) <= recorder.max_active
    finally: report = recorder.close()
    assert allocation == (id(ring._values), id(ring._timestamps), id(ring._valid), ring.storage_bytes)
    assert ring.overwritten_samples > 4000 and report["accepted_raw_observations"] == 5000
    assert pipeline.latest["metadata"]["index"] == 4999
    assert report["saved_events"] == 1 and not report["writer_error_count"]
    assert not recorder.worker.is_alive() and recorder.queue.unfinished_tasks == 0
