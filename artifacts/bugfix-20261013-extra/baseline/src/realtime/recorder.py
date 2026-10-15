"""Bounded pre/post capture and a non-blocking, atomic event writer."""

from collections import deque
from dataclasses import asdict
import json
import logging
import math
from pathlib import Path
from queue import Queue, Full
from threading import Thread
from src.realtime.ring_buffer import _positive_integer

LOGGER = logging.getLogger(__name__)


class EventRecorder:
    def __init__(self, directory: Path, *, pre_seconds: float, post_seconds: float, period_seconds: float,
                 queue_capacity=64, max_active=4, max_event_seconds=30, max_saved_events=1000, metadata=None):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in (pre_seconds, post_seconds)):
            raise ValueError("Invalid event duration")
        queue_capacity = _positive_integer(queue_capacity, "queue_capacity")
        max_active = _positive_integer(max_active, "max_active")
        max_saved_events = _positive_integer(max_saved_events, "max_saved_events")
        if isinstance(period_seconds, bool) or not math.isfinite(period_seconds) or period_seconds <= 0 or not math.isfinite(max_event_seconds) or max_event_seconds < pre_seconds + post_seconds:
            raise ValueError("Invalid bounded recorder configuration")
        directory = directory.resolve()
        if directory.exists(): raise FileExistsError("Event directory exists")
        directory.mkdir(parents=True)
        self.directory, self.metadata = directory, metadata or {}
        self.max_saved_events = max_saved_events
        self.pre_ns, self.post_ns = int(pre_seconds * 1e9), int(post_seconds * 1e9)
        self.max_ns = int(max_event_seconds * 1e9)
        self.history = deque(maxlen=math.ceil(pre_seconds / period_seconds) + 1)
        self.active, self.max_active, self.serial = [], max_active, 0
        self.queue = Queue(maxsize=queue_capacity)
        self.saved, self.errors = deque(maxlen=1024), deque(maxlen=1024)
        self.saved_count, self.error_count, self.dropped, self.closed = 0, 0, 0, False
        self.worker = Thread(target=self._write_loop, name="event-writer", daemon=True)
        self.worker.start()

    def _write_loop(self):
        while True:
            event = self.queue.get()
            try:
                if event is None: return
                target = self.directory / (event["event_id"] + ".json")
                temporary = target.with_suffix(".partial")
                try:
                    if self.saved_count >= self.max_saved_events: raise OSError("EVENT_STORAGE_LIMIT")
                    with temporary.open("x", encoding="utf-8") as handle:
                        json.dump(event, handle, allow_nan=False)
                    if target.exists(): raise FileExistsError("Event output exists")
                    temporary.rename(target)
                    self.saved.append(str(target))
                    self.saved_count += 1
                except (OSError, ValueError, TypeError) as error:
                    self.errors.append({"event_id": event["event_id"], "error": str(error)})
                    self.error_count += 1
                    LOGGER.error("Event save failed: %s", error)
            finally: self.queue.task_done()

    def _enqueue(self, event):
        try: self.queue.put_nowait(event)
        except Full:
            self.dropped += 1
            self.errors.append({"event_id": event["event_id"], "error": "WRITER_QUEUE_FULL"})
            self.error_count += 1
            LOGGER.error("Event queue full: %s", event["event_id"])

    def consume(self, row: dict, decision):
        if self.closed: raise RuntimeError("Recorder is closed")
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
                self.dropped += 1
                self.errors.append({"error": "ACTIVE_EVENT_LIMIT", "timestamp_ns": timestamp})
                self.error_count += 1
            else:
                self.serial += 1
                history = [r for r in self.history if r["timestamp_ns"] >= timestamp - self.pre_ns]
                event = {"event_id": f"alarm-{self.serial:06d}", "alarm_time_ns": timestamp,
                         "start_ns": timestamp - self.pre_ns, "end_requested_ns": timestamp + self.post_ns,
                         "ground_truth": "UNLABELED", "pre_history_complete": bool(history) and history[0]["timestamp_ns"] <= timestamp - self.pre_ns,
                         "metadata": self.metadata, "samples": history + [row]}
                if self.post_ns == 0:
                    event.update(complete=True, completion_reason="POST_EVENT_COMPLETE")
                    self._enqueue(event)
                else: self.active.append(event)
        self.history.append(row)

    def boundary(self, reason):
        for event in self.active:
            event.update(complete=False, completion_reason=reason)
            self._enqueue(event)
        self.active.clear()
        self.history.clear()

    def close(self):
        if not self.closed:
            self.boundary("STREAM_END")
            self.queue.put(None)  # shutdown only; live ingestion never waits on disk
            self.queue.join()
            self.worker.join()
            self.closed = True
        return {"saved_events": self.saved_count, "dropped_events": self.dropped, "writer_errors": list(self.errors), "writer_error_count": self.error_count,
                "max_saved_events": self.max_saved_events,
                "queue_capacity": self.queue.maxsize, "history_capacity": self.history.maxlen}
