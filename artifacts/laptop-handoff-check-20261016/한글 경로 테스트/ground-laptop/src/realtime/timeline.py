"""Bounded UTF-8 trace segments; retention never touches source observations."""

from collections import deque
import json
import logging
from pathlib import Path
import re

from src.realtime.ring_buffer import _positive_integer
from src.realtime.serialization import json_value

LOGGER = logging.getLogger(__name__)
DEFAULT_SEGMENT_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_SEGMENTS = 8


class TimelineWriter:
    def __init__(self, directory: Path, *, segment_bytes=DEFAULT_SEGMENT_BYTES, max_segments=DEFAULT_MAX_SEGMENTS):
        self.directory = directory.resolve()
        self.limit = _positive_integer(segment_bytes, "timeline_segment_bytes")
        self.maximum = _positive_integer(max_segments, "timeline_max_segments")
        self.files, self.errors = deque(), deque(maxlen=16)
        self.handle = None
        self.index = self.written = self.evicted = self.dropped = self.error_count = 0
        self.closed = self.disabled = False
        self._open_segment()

    def _open_segment(self):
        name = "timeline.jsonl" if self.index == 0 else f"timeline.{self.index:06d}.jsonl"
        self.handle = (self.directory / name).open("xb")
        self.files.append({"file": name, "bytes": 0, "records": 0})
        self.index += 1

    def _close_segment(self):
        handle, self.handle = self.handle, None
        if handle is not None: handle.close()

    def _error(self, code, error):
        self.error_count += 1
        self.errors.append({"code": code, "error": str(error)})
        LOGGER.error("%s: %s", code, error)

    def write(self, record):
        if self.closed: raise RuntimeError("Timeline writer is closed")
        if self.disabled:
            self.dropped += 1
            return False
        try: payload = (json.dumps(json_value(record), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        except (TypeError, ValueError) as error:
            self.dropped += 1
            self._error("TIMELINE_SERIALIZATION_ERROR", error)
            return False
        if len(payload) > self.limit:
            self.dropped += 1
            self._error("TIMELINE_RECORD_TOO_LARGE", "Record exceeds segment byte limit")
            return False
        try:
            if self.files[-1]["bytes"] + len(payload) > self.limit:
                self._close_segment()
                if len(self.files) >= self.maximum:
                    previous = self.files[0]
                    path = self.directory / previous["file"]
                    if path.resolve().parent != self.directory: raise OSError("Refusing deletion outside owned trace directory")
                    path.unlink()
                    self.files.popleft()
                    self.evicted += previous["records"]
                self._open_segment()
            self.handle.write(payload)
            self.files[-1]["bytes"] += len(payload)
            self.files[-1]["records"] += 1
            self.written += 1
            return True
        except OSError as error:
            self.dropped += 1
            self.disabled = True
            self._error("TIMELINE_IO_ERROR", error)
            return False

    def close(self):
        if not self.closed:
            try: self._close_segment()
            except OSError as error: self._error("TIMELINE_CLOSE_ERROR", error)
            self.closed = True
        return self.summary()

    def summary(self):
        return {"segment_bytes": self.limit, "max_segments": self.maximum,
                "maximum_retained_bytes": self.limit * self.maximum,
                "files": [f["file"] for f in self.files], "retained_records": sum(f["records"] for f in self.files),
                "retained_payload_bytes": sum(f["bytes"] for f in self.files), "written_records": self.written,
                "evicted_records": self.evicted, "dropped_records": self.dropped,
                "retention_truncated": bool(self.evicted or self.dropped or self.error_count),
                "error_count": self.error_count, "errors": list(self.errors), "disabled": self.disabled}


def iter_timeline(directory: Path, *, require_complete=True):
    """Read declared segments in order, including legacy single-file replays."""
    directory = directory.resolve()
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    trace = summary.get("timeline", {})
    if require_complete and trace.get("retention_truncated"):
        raise ValueError("Timeline retention removed records; complete-trace analysis is unavailable")
    for name in trace.get("files", ["timeline.jsonl"]):
        if not re.fullmatch(r"timeline(?:\.\d{6,})?\.jsonl", name): raise ValueError("Invalid timeline segment name")
        path = (directory / name).resolve()
        if path.parent != directory: raise ValueError("Timeline segment is outside replay directory")
        with path.open(encoding="utf-8") as handle:
            for line in handle: yield json.loads(line)
