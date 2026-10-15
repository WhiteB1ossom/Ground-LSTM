"""Bounded numeric storage; preprocessing and risk decisions belong elsewhere."""

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def buffer_capacity(sequence_length: int, pre_event_seconds: float, sampling_period_seconds: float) -> int:
    length = _positive_integer(sequence_length, "sequence_length")
    for name, value, allow_zero in (("pre_event_seconds", pre_event_seconds, True),
                                    ("sampling_period_seconds", sampling_period_seconds, False)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (value < 0 if allow_zero else value <= 0):
            raise ValueError(f"Invalid {name}")
    return length + math.ceil(pre_event_seconds / sampling_period_seconds)


@dataclass(frozen=True)
class BufferSnapshot:
    values: np.ndarray
    timestamps_ns: np.ndarray
    valid: np.ndarray


class RingBuffer:
    """Preallocated float32 rows, UTC nanoseconds and per-row validity.

    Single-owner component: ingestion/reads must be serialized by the caller.
    External snapshots are detached copies; copy_latest_into reuses caller memory.
    """

    def __init__(self, capacity: int, feature_count: int):
        self._capacity = _positive_integer(capacity, "capacity")
        self._feature_count = _positive_integer(feature_count, "feature_count")
        self._values = np.empty((self.capacity, self.feature_count), dtype=np.float32)
        self._timestamps = np.empty(self.capacity, dtype=np.int64)
        self._valid = np.empty(self.capacity, dtype=np.bool_)
        self._head = self._size = self._revision = self._since_clear = self._overwritten = 0

    @property
    def capacity(self) -> int: return self._capacity

    @property
    def feature_count(self) -> int: return self._feature_count

    @property
    def size(self) -> int: return self._size

    @property
    def revision(self) -> int: return self._revision

    @property
    def samples_since_clear(self) -> int: return self._since_clear

    @property
    def overwritten_samples(self) -> int: return self._overwritten

    @property
    def storage_bytes(self) -> int:
        """Array payload only, not Python overhead, total process RAM or MCU RAM."""
        return self._values.nbytes + self._timestamps.nbytes + self._valid.nbytes

    def append(self, timestamp: pd.Timestamp, values: np.ndarray, *, valid: bool = True) -> None:
        if not isinstance(timestamp, pd.Timestamp) or pd.isna(timestamp) or timestamp.tzinfo is None:
            raise ValueError("RingBuffer requires a timezone-aware pandas Timestamp")
        stamp = timestamp.value
        if self.size and stamp <= self._timestamps[(self._head - 1) % self.capacity]:
            raise ValueError("Timestamp must strictly increase; duplicates/late samples are rejected")
        if not isinstance(valid, (bool, np.bool_)): raise ValueError("valid must be boolean")
        with np.errstate(over="ignore", invalid="ignore"):
            row = np.asarray(values, dtype=np.float32)
        if row.shape != (self.feature_count,) or not np.isfinite(row).all():
            raise ValueError("Expected a finite float32 feature vector of the configured width")
        # Complete validation before changing an occupied slot or advancing head.
        self._values[self._head] = row
        self._timestamps[self._head], self._valid[self._head] = stamp, valid
        self._head = (self._head + 1) % self.capacity
        if self.size == self.capacity: self._overwritten += 1
        else: self._size += 1
        self._revision += 1
        self._since_clear += 1

    def clear(self) -> None:
        """Start another explicit stream/segment without reallocating storage."""
        self._head = self._size = self._since_clear = 0
        self._revision += 1

    def copy_latest_into(self, values: np.ndarray, timestamps_ns: np.ndarray, valid: np.ndarray) -> None:
        if not all(isinstance(a, np.ndarray) and a.ndim > 0 for a in (values, timestamps_ns, valid)):
            raise ValueError("Output arguments must be arrays with a sample axis")
        count = len(values)
        if values.shape != (count, self.feature_count) or values.dtype != np.float32:
            raise ValueError("Output values must have shape (count, features) and dtype float32")
        if timestamps_ns.shape != (count,) or timestamps_ns.dtype != np.int64 or valid.shape != (count,) or valid.dtype != np.bool_:
            raise ValueError("Output timestamp/valid arrays must be int64/bool vectors")
        if count > self.size: raise ValueError("Requested more samples than available")
        if not all(a.flags.writeable for a in (values, timestamps_ns, valid)):
            raise ValueError("Output arrays must be writable")
        if any(np.shares_memory(out, stored) for out in (values, timestamps_ns, valid) for stored in (self._values, self._timestamps, self._valid)):
            raise ValueError("Output arrays must not alias ring storage")
        if any(np.shares_memory(a, b) for a, b in ((values, timestamps_ns), (values, valid), (timestamps_ns, valid))):
            raise ValueError("Output arrays must not alias one another")
        start = (self._head - count) % self.capacity
        first = min(count, self.capacity - start)
        for out, stored in ((values, self._values), (timestamps_ns, self._timestamps), (valid, self._valid)):
            out[:first] = stored[start:start + first]
            out[first:] = stored[:count - first]

    def snapshot(self, count: int | None = None) -> BufferSnapshot:
        """Detached chronological copy; its allocation is explicit and bounded."""
        if count is None: count = self.size
        if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 0:
            raise ValueError("Snapshot count must be a nonnegative integer")
        if count > self.size: raise ValueError("Requested more samples than available")
        values = np.empty((count, self.feature_count), dtype=np.float32)
        stamps, valid = np.empty(count, dtype=np.int64), np.empty(count, dtype=np.bool_)
        self.copy_latest_into(values, stamps, valid)
        for array in (values, stamps, valid): array.flags.writeable = False
        return BufferSnapshot(values, stamps, valid)
