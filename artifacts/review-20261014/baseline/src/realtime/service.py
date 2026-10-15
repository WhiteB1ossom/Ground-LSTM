"""Single-owner live receive loop with a timer independent of packet arrival."""

import math
from queue import Queue, Empty, Full

from src.realtime.ring_buffer import _positive_integer


class RealtimeService:
    def __init__(self, pipeline, *, queue_capacity=64, poll_interval_seconds=None):
        self.pipeline = pipeline
        self.inbox = Queue(maxsize=_positive_integer(queue_capacity, "queue_capacity"))
        self.interval = poll_interval_seconds if poll_interval_seconds is not None else min(.1, pipeline.input_timeout / 2)
        if isinstance(self.interval, bool) or not isinstance(self.interval, (int, float)) or not math.isfinite(self.interval) or not 0 < self.interval <= pipeline.input_timeout:
            raise ValueError("Poll interval must be positive and no greater than input timeout")
        self.accepted = self.rejected = self.dropped = 0
        self.output_failures = self.processing_failures = 0

    def submit(self, observation):
        # Receiver threads enqueue observations; only run() changes pipeline state.
        try: self.inbox.put_nowait(dict(observation))
        except Full:
            self.dropped += 1
            raise

    def run(self, stop_event, emit):
        """Run on the acquisition worker; emit receives aligned rows or STATUS.

        The caller stops and joins this worker before closing the recorder/sink.
        Actual wire decoding remains the source adapter's responsibility.
        A callback returning False reports a failed write; None remains valid.
        """
        def publish(record):
            if record.get("decision", {}).get("reason", "").startswith(("INFERENCE_ERROR:", "PREPROCESSING_ERROR:")):
                self.processing_failures += 1
            if emit(record) is False: self.output_failures += 1

        while not stop_event.is_set():
            status = self.pipeline.poll()
            if status is not None: publish(status)
            if stop_event.is_set(): break
            try: observation = self.inbox.get(timeout=self.interval)
            except Empty: continue
            try:
                try: samples = self.pipeline.feed(observation)
                except ValueError as error:
                    self.rejected += 1
                    publish({"record_type": "STATUS", "input_status": "INPUT_REJECTED", "reason": str(error)})
                else:
                    self.accepted += 1
                    for sample in samples: publish(sample)
            finally: self.inbox.task_done()
        pending = self.inbox.qsize()
        degraded = self.rejected or self.dropped or self.output_failures or self.processing_failures or self.pipeline.input_timeouts or pending
        return {"status": "DEGRADED" if degraded else "SUCCESS", "accepted_observations": self.accepted, "rejected_observations": self.rejected,
                "queue_full_count": self.dropped, "input_timeouts": self.pipeline.input_timeouts,
                "pending_observations": pending,
                "output_failure_count": self.output_failures, "processing_failure_count": self.processing_failures}
