"""Bounded pre/post capture and a non-blocking, atomic event writer."""

from collections import deque
import json
import logging
import math
from pathlib import Path
from queue import Queue, Full, Empty
from threading import Thread, Event, Lock, TIMEOUT_MAX
import time
from src.realtime.ring_buffer import _positive_integer
from src.realtime.serialization import json_value

LOGGER = logging.getLogger(__name__)


class EventRecorder:
    def __init__(self, directory: Path, *, pre_seconds: float, post_seconds: float, period_seconds: float,
                 queue_capacity=64, max_active=4, max_event_seconds=30, max_saved_events=1000, metadata=None,
                 raw_history_capacity=1024, max_raw_observations_per_event=4096, shutdown_timeout_seconds=5.):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in (pre_seconds, post_seconds)):
            raise ValueError("Invalid event duration")
        queue_capacity = _positive_integer(queue_capacity, "queue_capacity")
        max_active = _positive_integer(max_active, "max_active")
        max_saved_events = _positive_integer(max_saved_events, "max_saved_events")
        raw_history_capacity = _positive_integer(raw_history_capacity, "raw_history_capacity")
        max_raw_observations_per_event = _positive_integer(max_raw_observations_per_event, "max_raw_observations_per_event")
        self._validate_shutdown_timeout(shutdown_timeout_seconds)
        if isinstance(period_seconds, bool) or not math.isfinite(period_seconds) or period_seconds <= 0 or not math.isfinite(max_event_seconds) or max_event_seconds < pre_seconds + post_seconds:
            raise ValueError("Invalid bounded recorder configuration")
        directory = directory.resolve()
        if directory.exists(): raise FileExistsError("Event directory exists")
        directory.mkdir(parents=True)
        self.directory, self.metadata = directory, json_value(metadata or {})
        self.max_saved_events = max_saved_events
        self.pre_ns, self.post_ns = int(pre_seconds * 1e9), int(post_seconds * 1e9)
        self.max_ns = int(max_event_seconds * 1e9)
        self.history = deque(maxlen=math.ceil(pre_seconds / period_seconds) + 1)
        # Raw receive rate can exceed the alignment rate; bound it separately.
        self.raw_history = deque(maxlen=raw_history_capacity)
        self.max_raw_observations = max_raw_observations_per_event
        self.last_raw_timestamp = self.last_raw_evicted = None
        self.raw_observations = self.raw_history_dropped = self.raw_event_dropped = 0
        self.active, self.max_active, self.serial = [], max_active, 0
        self.queue = Queue(maxsize=queue_capacity)
        self.saved, self.errors = deque(maxlen=1024), deque(maxlen=1024)
        self.saved_count, self.error_count, self.dropped, self.closed = 0, 0, 0, False
        self.storage_disabled, self.cleanup_error_count = False, 0
        self.shutdown_timeout = shutdown_timeout_seconds
        self._closing = Event()
        self._close_lock, self._stats_lock = Lock(), Lock()
        self._pending = 0
        self._shutdown_timed_out = self._worker_failed = False
        self.worker = Thread(target=self._write_loop, name="event-writer", daemon=True)
        self.worker.start()

    @staticmethod
    def _validate_shutdown_timeout(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= TIMEOUT_MAX:
            raise ValueError("shutdown timeout must be finite, positive and supported by threading")

    def _write_loop(self):
        try: self._drain_writes()
        except Exception as error:
            # A background thread cannot propagate a failure to the caller.
            # Keep the cause visible and leave unprocessed tasks in the report.
            with self._stats_lock:
                self._worker_failed = self.storage_disabled = True
                self.error_count += 1
                self.errors.append({"code": "EVENT_WRITER_FAILED", "error": f"{type(error).__name__}: {error}"})
            LOGGER.exception("Event writer terminated")

    def _drain_writes(self):
        while True:
            try: event = self.queue.get(timeout=.05)
            except Empty:
                if self._closing.is_set(): return
                continue
            try:
                target = self.directory / (event["event_id"] + ".json")
                temporary = target.with_suffix(".partial")
                owned_temporary = False
                try:
                    with self._stats_lock:
                        disabled, full = self.storage_disabled, self.saved_count >= self.max_saved_events
                    if disabled: raise OSError("EVENT_STORAGE_DISABLED")
                    if full: raise OSError("EVENT_STORAGE_LIMIT")
                    with temporary.open("x", encoding="utf-8") as handle:
                        owned_temporary = True
                        json.dump(event, handle, allow_nan=False)
                    if target.exists(): raise FileExistsError("Event output exists")
                    temporary.rename(target)
                    owned_temporary = False
                    with self._stats_lock:
                        self.saved.append(str(target))
                        self.saved_count += 1
                except (OSError, ValueError, TypeError) as error:
                    with self._stats_lock:
                        self.errors.append({"event_id": event["event_id"], "error": str(error)})
                        self.error_count += 1
                    LOGGER.error("Event save failed: %s", error)
                    if owned_temporary:
                        try: temporary.unlink(missing_ok=True)
                        except OSError as cleanup_error:
                            # Stop creating files when even cleanup is unavailable.
                            with self._stats_lock:
                                self.storage_disabled = True
                                self.cleanup_error_count += 1
                                self.error_count += 1
                                self.errors.append({"event_id": event["event_id"], "code": "EVENT_TEMP_CLEANUP_FAILED", "error": str(cleanup_error)})
                            LOGGER.error("Event temporary cleanup failed: %s", cleanup_error)
            finally:
                with self._stats_lock:
                    self._pending -= 1
                    self.queue.task_done()

    def _enqueue(self, event, *, log_errors=True):
        dropped = False
        with self._stats_lock:
            try:
                self.queue.put_nowait(event)
                self._pending += 1
            except Full:
                dropped = True
                self.dropped += 1
                self.errors.append({"event_id": event["event_id"], "error": "WRITER_QUEUE_FULL"})
                self.error_count += 1
        if dropped and log_errors: LOGGER.error("Event queue full: %s", event["event_id"])

    def _append_raw(self, event, record):
        if len(event["raw_observations"]) < self.max_raw_observations:
            event["raw_observations"].append(record)
        else:
            event["raw_observations_truncated"] = True
            event["dropped_raw_observations"] += 1
            self.raw_event_dropped += 1

    def observe(self, timestamp_ns: int, observation: dict):
        """Capture accepted source observations before alignment, without disk I/O."""
        if self.closed: raise RuntimeError("Recorder is closed")
        if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int): raise ValueError("Invalid raw observation timestamp")
        if self.last_raw_timestamp is not None and timestamp_ns <= self.last_raw_timestamp:
            raise ValueError("Raw observation timestamps must strictly increase")
        record = {"timestamp_ns": timestamp_ns, "raw_observation": json_value(observation)}
        for event in self.active:
            if event["start_ns"] <= timestamp_ns <= event["end_requested_ns"]:
                self._append_raw(event, record)
        while self.raw_history and self.raw_history[0]["timestamp_ns"] < timestamp_ns - self.pre_ns:
            self.raw_history.popleft()
        if len(self.raw_history) == self.raw_history.maxlen:
            self.last_raw_evicted = self.raw_history[0]["timestamp_ns"]
            self.raw_history_dropped += 1
        self.raw_history.append(record)
        self.raw_observations += 1
        self.last_raw_timestamp = timestamp_ns

    def consume(self, row: dict, decision):
        if self.closed: raise RuntimeError("Recorder is closed")
        # The caller may edit an emitted row while this writer is still queued.
        row = json_value(row)
        timestamp = row["timestamp_ns"]
        finished = []
        for event in self.active:
            event["samples"].append(row)
            if timestamp >= event["end_requested_ns"] or timestamp - event["start_ns"] >= self.max_ns:
                event["complete"] = timestamp >= event["end_requested_ns"]
                event["completion_reason"] = "POST_EVENT_COMPLETE" if event["complete"] else "MAX_EVENT_DURATION"
                finished.append(event)
        for event in finished:
            self.active.remove(event)
            self._enqueue(event)
        if decision.transition == "ENTER":
            if len(self.active) >= self.max_active:
                with self._stats_lock:
                    self.dropped += 1
                    self.errors.append({"error": "ACTIVE_EVENT_LIMIT", "timestamp_ns": timestamp})
                    self.error_count += 1
            else:
                self.serial += 1
                history = [r for r in self.history if r["timestamp_ns"] >= timestamp - self.pre_ns]
                event = {"event_id": f"alarm-{self.serial:06d}", "alarm_time_ns": timestamp,
                         "start_ns": timestamp - self.pre_ns, "end_requested_ns": timestamp + self.post_ns,
                         "ground_truth": "UNLABELED", "pre_history_complete": self.pre_ns == 0 or (bool(history) and history[0]["timestamp_ns"] <= timestamp - self.pre_ns),
                         "metadata": self.metadata, "samples": history + [row],
                         "raw_observations": [], "dropped_raw_observations": 0,
                         "raw_observations_truncated": self.last_raw_evicted is not None and self.last_raw_evicted >= timestamp - self.pre_ns}
                for record in self.raw_history:
                    if timestamp - self.pre_ns <= record["timestamp_ns"] <= timestamp:
                        self._append_raw(event, record)
                if self.post_ns == 0:
                    event.update(complete=True, completion_reason="POST_EVENT_COMPLETE")
                    self._enqueue(event)
                else: self.active.append(event)
        self.history.append(row)

    def boundary(self, reason, *, log_errors=True):
        for event in self.active:
            event.update(complete=False, completion_reason=reason)
            self._enqueue(event, log_errors=log_errors)
        self.active.clear()
        self.history.clear()
        self.raw_history.clear()
        self.last_raw_timestamp = self.last_raw_evicted = None

    def close(self, *, timeout_seconds=None):
        timeout = self.shutdown_timeout if timeout_seconds is None else timeout_seconds
        self._validate_shutdown_timeout(timeout)
        deadline = time.monotonic() + timeout
        with self._close_lock:
            if not self.closed:
                self.closed = True
                self.boundary("STREAM_END", log_errors=False)
                self._closing.set()
        # An Event avoids trying to enqueue a sentinel into a full writer queue.
        self.worker.join(max(0., deadline - time.monotonic()))
        with self._stats_lock:
            complete = not self.worker.is_alive() and self._pending == 0
            if not complete and not self._shutdown_timed_out and not self._worker_failed:
                self._shutdown_timed_out = self.storage_disabled = True
                self.error_count += 1
                self.errors.append({"code": "EVENT_SHUTDOWN_TIMEOUT", "error": "Writer did not finish before the shutdown deadline"})
            degraded = not complete or self.error_count or self.raw_history_dropped or self.raw_event_dropped
            return {"status": "DEGRADED" if degraded else "SUCCESS", "shutdown_complete": complete,
                "shutdown_timed_out": self._shutdown_timed_out, "writer_failed": self._worker_failed,
                "pending_events": self._pending, "shutdown_timeout_seconds": timeout,
                "saved_events": self.saved_count, "dropped_events": self.dropped, "writer_errors": json_value(list(self.errors)), "writer_error_count": self.error_count,
                "max_saved_events": self.max_saved_events,
                "storage_disabled": self.storage_disabled, "cleanup_error_count": self.cleanup_error_count,
                "accepted_raw_observations": self.raw_observations, "raw_history_capacity": self.raw_history.maxlen,
                "max_raw_observations_per_event": self.max_raw_observations,
                "raw_history_dropped": self.raw_history_dropped, "raw_event_dropped": self.raw_event_dropped,
                "queue_capacity": self.queue.maxsize, "history_capacity": self.history.maxlen}
