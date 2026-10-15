"""Produce the latest contiguous valid LSTM tensor without refitting transforms."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.realtime.ring_buffer import RingBuffer, _positive_integer


@dataclass(frozen=True)
class SequenceStatus:
    reason: str
    end_timestamp_ns: int | None = None

    @property
    def ready(self) -> bool: return self.reason == "READY"


class SequenceBuilder:
    def __init__(self, buffer: RingBuffer, sequence_length: int, period_seconds: float, *, stride: int = 1):
        self.buffer = buffer
        self.length = _positive_integer(sequence_length, "sequence_length")
        self.stride = _positive_integer(stride, "stride")
        if self.length > buffer.capacity: raise ValueError("Ring capacity is smaller than sequence length")
        period = pd.Timedelta(seconds=period_seconds)
        if pd.isna(period) or period.value <= 0 or isinstance(period_seconds, bool): raise ValueError("Invalid sampling period")
        self.period_ns = period.value
        self._timestamps = np.empty(self.length, dtype=np.int64)
        self._valid = np.empty(self.length, dtype=np.bool_)
        self._last_emitted_revision = None

    @property
    def workspace_bytes(self) -> int: return self._timestamps.nbytes + self._valid.nbytes

    def build_into(self, output: np.ndarray) -> SequenceStatus:
        """Reuse (1, length, features) float32 output; consume only on READY.

        On invalid/gap status the output may contain the rejected candidate.
        Callers must check status.ready before inference or storing a sequence.
        """
        if output.shape != (1, self.length, self.buffer.feature_count) or output.dtype != np.float32 or not output.flags.writeable:
            raise ValueError("Output must be a writable float32 tensor (1, sequence_length, features)")
        if self.buffer.size < self.length: return SequenceStatus("WARMING_UP")
        if self._last_emitted_revision == self.buffer.revision: return SequenceStatus("NO_NEW_SAMPLE")
        self.buffer.copy_latest_into(output[0], self._timestamps, self._valid)
        if not self._valid.all(): return SequenceStatus("INVALID_WINDOW")
        if any(int(b) - int(a) != self.period_ns for a, b in zip(self._timestamps[:-1], self._timestamps[1:])):
            return SequenceStatus("TIMESTAMP_GAP")
        if (self.buffer.samples_since_clear - self.length) % self.stride: return SequenceStatus("WAITING_FOR_STRIDE")
        self._last_emitted_revision = self.buffer.revision
        return SequenceStatus("READY", int(self._timestamps[-1]))
