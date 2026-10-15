"""Arrival clocks, overloaded queues and bounded writer shutdown."""

import json
import time
from pathlib import Path
from queue import Full
from threading import Event, Thread

import pytest

from src.realtime import replay as replay_module
from src.realtime.decision import DecisionEngine
from src.realtime.recorder import EventRecorder
from src.realtime.service import RealtimeService
from src.realtime.stream import RealtimePipeline
from test_realtime_bugfixes import replay_settings
from test_realtime_integration import FakeEngine, observation, settings


def test_continuous_arrivals_during_blocked_output_are_processing_delay_not_silence():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    service = RealtimeService(pipeline)
    stop, entered, release = Event(), Event(), Event()
    rows, reports, errors = [], [], []
    for t in (0., .1, .2): service.submit(observation(t, .9))
    def emit(row):
        rows.append(row)
        if row.get("prediction") and not entered.is_set():
            entered.set()
            assert release.wait(5), "Output callback was not released"
        if row.get("timestamp") == observation(.8, .9)["timestamp"]: stop.set()
    def run():
        try: reports.append(service.run(stop, emit))
        except Exception as error: errors.append(error)
    worker = Thread(target=run)
    worker.start()
    try:
        assert entered.wait(3)
        for host, sensor in zip((.25, .5, .75, 1., 1.25, 1.5), (.3, .4, .5, .6, .7, .8)):
            now[0] = host
            service.submit(observation(sensor, .9))
    finally:
        release.set()
        worker.join(3)
        stop.set()
    assert not worker.is_alive() and not errors
    report = reports[0]
    assert report["input_timeouts"] == 0 and pipeline.input_timeouts == 0
    assert report["processing_expired_observations"] == 2 and report["status"] == "DEGRADED"
    delays = [r for r in rows if r["input_status"] == "PROCESSING_DELAY"]
    assert len(delays) == 1 and not delays[0]["available"] and delays[0]["decision"]["alarm_active"]
    assert rows[-1]["available"] and pipeline.ring.size == 4
    assert report["accepted_observations"] == 7 and service.inbox.unfinished_tasks == 0
    assert all("received_at" not in r.get("raw_observation", {}) for r in rows)


def test_full_queue_is_not_misreported_as_receiver_silence():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    service = RealtimeService(pipeline, queue_capacity=1)
    service.submit(observation(0., .9))
    now[0] = 1.5
    with pytest.raises(Full): service.submit(observation(.1, .9))
    assert pipeline.poll(last_received_at=service._latest_receive_time()) is None
    assert service.dropped == 1 and service.inbox.qsize() == 1


@pytest.mark.parametrize("bad", ["timestamp", "source", "duplicate", "device"])
def test_invalid_packets_cannot_refresh_receiver_watchdog(bad):
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    service = RealtimeService(pipeline)
    service.submit(observation(0., .9))
    now[0] = .9
    value = observation(.1, .9)
    if bad == "timestamp": value["timestamp"] = "invalid"
    if bad == "source": value["source"] = "wrong"
    if bad == "duplicate": value = observation(0., .9)
    if bad == "device": value["device_id"] = "other"
    service.submit(value)
    now[0] = 1.
    assert pipeline.poll(last_received_at=service._latest_receive_time())["input_status"] == "INPUT_TIMEOUT"


def test_old_queue_entries_do_not_recover_a_real_timeout_when_processing_limit_is_longer():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), {**settings(), "processing_timeout_seconds": 5.}, clock=lambda: now[0])
    service = RealtimeService(pipeline)
    service.submit(observation(0., .9))
    now[0] = 1.5
    stop, rows = Event(), []
    def emit(row):
        rows.append(row)
        if row["input_status"] == "PROCESSING_DELAY": stop.set()
    report = service.run(stop, emit)
    assert report["input_timeouts"] == 1 and report["processing_expired_observations"] == 1
    assert pipeline.timed_out and pipeline.last_observation is None
    assert all(r.get("record_type") == "STATUS" for r in rows)


def test_a_real_gap_is_reported_even_if_a_fresh_packet_arrived_before_processing_resumes():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    service = RealtimeService(pipeline)
    service.submit(observation(0., .9))
    now[0] = 1.5
    service.submit(observation(.1, .9))
    stop, rows = Event(), []
    def emit(row):
        rows.append(row)
        if row.get("timestamp") == observation(.1, .9)["timestamp"]: stop.set()
    report = service.run(stop, emit)
    timeouts = [r for r in rows if r["input_status"] == "INPUT_TIMEOUT"]
    assert report["input_timeouts"] == 1 and len(timeouts) == 1
    assert timeouts[0]["host_silence_seconds"] == 1.5 and timeouts[0]["silence_ended_at_host_time"] == 1.5


def test_distinct_silence_intervals_can_be_reported_before_a_valid_window_recovers():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    now[0] = 1.
    assert pipeline.poll() is not None
    now[0] = 1.5
    assert pipeline.poll(last_received_at=1.5) is None
    now[0] = 2.5
    assert pipeline.poll(last_received_at=1.5) is not None
    assert pipeline.input_timeouts == 2 and pipeline.poll() is None


def test_arrivals_while_a_historical_gap_status_is_blocked_refresh_the_next_poll():
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    service = RealtimeService(pipeline)
    service.submit(observation(0., .9))
    now[0] = 1.5
    service.submit(observation(.1, .9))
    stop, entered, release = Event(), Event(), Event()
    rows, reports, errors = [], [], []
    def emit(row):
        rows.append(row)
        if row["input_status"] == "INPUT_TIMEOUT" and not entered.is_set():
            entered.set()
            assert release.wait(5)
        if row.get("timestamp") == observation(.7, .9)["timestamp"]: stop.set()
    def run():
        try: reports.append(service.run(stop, emit))
        except Exception as error: errors.append(error)
    worker = Thread(target=run)
    worker.start()
    try:
        assert entered.wait(3)
        for host, sensor in zip((1.75, 2., 2.25, 2.5, 2.75, 3.), (.2, .3, .4, .5, .6, .7)):
            now[0] = host
            service.submit(observation(sensor, .9))
    finally:
        release.set()
        worker.join(3)
        stop.set()
    assert not worker.is_alive() and not errors
    assert reports[0]["input_timeouts"] == 1
    assert len([row for row in rows if row["input_status"] == "INPUT_TIMEOUT"]) == 1
    assert service.inbox.unfinished_tasks == 0


@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf")])
def test_invalid_processing_limit_is_rejected(value):
    pipeline = RealtimePipeline(FakeEngine(), {**settings(), "processing_timeout_seconds": value})
    with pytest.raises(ValueError, match="processing_timeout_seconds"): RealtimeService(pipeline)


@pytest.mark.parametrize("value", [True, float("nan"), -1.])
def test_invalid_receiver_clock_fails_without_queuing_data(value):
    now = [0.]
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: now[0])
    service = RealtimeService(pipeline)
    now[0] = value
    with pytest.raises(ValueError, match="clock"): service.submit(observation(0., .9))
    assert service.inbox.empty()


def test_future_receipt_and_out_of_range_sensor_time_are_rejected_before_state_changes():
    pipeline = RealtimePipeline(FakeEngine(), settings(), clock=lambda: 0.)
    with pytest.raises(ValueError, match="Receive time"): pipeline.feed(observation(0., .9), received_at=1.)
    with pytest.raises(ValueError, match="NANOSECOND_RANGE"):
        pipeline.feed({**observation(0., .9), "timestamp": "2500-01-01T00:00:00Z"})
    assert pipeline.last_observation is None and pipeline.ring.size == 0


def test_a_second_live_worker_is_rejected():
    service = RealtimeService(RealtimePipeline(FakeEngine(), settings()))
    stop, entered, release = Event(), Event(), Event()
    service.submit(observation(0., .9))
    def emit(row):
        entered.set()
        assert release.wait(5)
        stop.set()
    worker = Thread(target=service.run, args=(stop, emit))
    worker.start()
    try:
        assert entered.wait(3)
        with pytest.raises(RuntimeError, match="active worker"): service.run(stop, emit)
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()


def enter_alarm(recorder, timestamp=0):
    recorder.consume({"timestamp_ns": timestamp}, DecisionEngine(.7, .4).update(timestamp, .9, available=True))


def test_shutdown_is_bounded_even_with_blocked_io_and_a_full_queue(tmp_path, monkeypatch):
    entered, release = Event(), Event()
    original = Path.open
    def blocked(path, *args, **kwargs):
        if path.suffix == ".partial":
            entered.set()
            assert release.wait(5)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", blocked)
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=.1, queue_capacity=1)
    try:
        enter_alarm(recorder)
        assert entered.wait(3)
        enter_alarm(recorder, 1)
        started = time.monotonic()
        report = recorder.close(timeout_seconds=.1)
        assert time.monotonic() - started < .75
        assert not report["shutdown_complete"] and report["shutdown_timed_out"]
        assert report["status"] == "DEGRADED" and report["pending_events"] == 2
        assert recorder.closed and recorder.storage_disabled
        with pytest.raises(RuntimeError, match="closed"): recorder.observe(2, {})
        second = recorder.close(timeout_seconds=.01)
        assert second["writer_error_count"] == 1
        second["writer_errors"][0]["code"] = "changed by caller"
    finally:
        release.set()
        final = recorder.close(timeout_seconds=3.)
    assert final["shutdown_complete"] and final["pending_events"] == 0
    assert final["shutdown_timed_out"] and final["status"] == "DEGRADED"
    assert final["writer_errors"][0]["code"] == "EVENT_SHUTDOWN_TIMEOUT"
    assert not recorder.worker.is_alive() and recorder.queue.unfinished_tasks == 0


def test_concurrent_close_calls_do_not_enqueue_duplicate_sentinels(tmp_path):
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=.1)
    enter_alarm(recorder)
    start, reports = Event(), []
    def close():
        start.wait(3)
        reports.append(recorder.close(timeout_seconds=2.))
    workers = [Thread(target=close) for _ in range(2)]
    for worker in workers: worker.start()
    start.set()
    for worker in workers: worker.join(3)
    assert all(not worker.is_alive() for worker in workers)
    assert len(reports) == 2 and all(r["shutdown_complete"] and r["saved_events"] == 1 for r in reports)
    assert recorder.queue.unfinished_tasks == 0


def test_unexpected_writer_failure_is_visible_to_the_owner(tmp_path, monkeypatch):
    original = Path.open
    def faulty(path, *args, **kwargs):
        if path.suffix == ".partial": raise KeyError("injected writer bug")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", faulty)
    recorder = EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=.1)
    enter_alarm(recorder)
    report = recorder.close()
    assert report["status"] == "DEGRADED" and report["writer_failed"]
    assert report["saved_events"] == 0 and report["writer_errors"][0]["code"] == "EVENT_WRITER_FAILED"


@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf"), 1e20])
def test_invalid_shutdown_configuration_fails_before_creating_output(tmp_path, value):
    with pytest.raises(ValueError, match="shutdown timeout"):
        EventRecorder(tmp_path / "events", pre_seconds=0, post_seconds=0, period_seconds=.1, shutdown_timeout_seconds=value)
    assert not (tmp_path / "events").exists()


def test_replay_cli_returns_degraded_when_shutdown_is_incomplete(tmp_path, monkeypatch):
    import pandas as pd
    def backend(*args, **kwargs):
        engine = FakeEngine()
        engine.manifest.update(model_version="fake", synthetic_demo=True, files={"scaler.json": "fixture"})
        return engine
    monkeypatch.setattr(replay_module, "InferenceEngine", backend)
    options = {**replay_settings(), "post_event_seconds": 0, "shutdown_timeout_seconds": .05}
    monkeypatch.setattr(replay_module, "read_yaml", lambda _: {"replay": options})
    entered, release = Event(), Event()
    original = Path.open
    def blocked(path, *args, **kwargs):
        if path.suffix == ".partial":
            entered.set()
            assert release.wait(5)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", blocked)
    instances = []
    def recorder(*args, **kwargs):
        instance = EventRecorder(*args, **kwargs)
        instances.append(instance)
        return instance
    monkeypatch.setattr(replay_module, "EventRecorder", recorder)
    raw = tmp_path / "raw"
    raw.mkdir()
    path, output = raw / "input.csv", tmp_path / "out"
    pd.DataFrame([observation(t, .9) for t in (0., .1, .2)]).to_csv(path, index=False)
    try:
        code = replay_module.main(["--input", str(path), "--bundle", str(tmp_path / "bundle"), "--output", str(output)])
        assert entered.is_set() and code == 1
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        assert summary["status"] == "DEGRADED" and not summary["recorder"]["shutdown_complete"]
    finally:
        release.set()
        for instance in instances: assert instance.close(timeout_seconds=3.)["shutdown_complete"]
