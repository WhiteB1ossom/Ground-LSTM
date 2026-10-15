"""Normalized packet boundary, not an invented UART/CAN wire decoder."""

import pandas as pd


class PacketAssembler:
    def __init__(self, sensor_names, *, device_id, source, acquisition_kind):
        self.sensors = frozenset(sensor_names)
        self.metadata = {"device_id": device_id, "source": source, "acquisition_kind": acquisition_kind}
        self.timestamp, self.pending, self.last_flushed = None, {}, None

    def push(self, timestamp: pd.Timestamp, sensor: str, value):
        if sensor not in self.sensors: raise ValueError("Unknown packet sensor")
        if not isinstance(timestamp, pd.Timestamp) or timestamp.tzinfo is None or pd.isna(timestamp): raise ValueError("Invalid packet timestamp")
        if self.last_flushed is not None and timestamp <= self.last_flushed: raise ValueError("Late packet after flush")
        if self.timestamp is not None and timestamp < self.timestamp: raise ValueError("Late packet")
        completed = []
        if self.timestamp is not None and timestamp > self.timestamp: completed = self.flush()
        self.timestamp = timestamp
        if sensor in self.pending: raise ValueError("Duplicate sensor packet")
        self.pending[sensor] = value
        return completed

    def flush(self):
        if self.timestamp is None or not self.pending: return []
        row = {"timestamp": self.timestamp.isoformat(), **self.metadata, **self.pending}
        self.pending = {}
        self.last_flushed = self.timestamp
        return [row]
