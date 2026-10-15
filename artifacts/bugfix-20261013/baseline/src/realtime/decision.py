"""Advisory hysteresis; unavailable data cannot clear an existing alarm."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Decision:
    status: str
    alarm_active: bool
    transition: str | None
    reason: str


class DecisionEngine:
    def __init__(self, on: float, off: float, *, consecutive: int = 1):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (on, off)) or not 0 <= off <= on <= 1:
            raise ValueError("Require 0 <= off <= on <= 1")
        if isinstance(consecutive, bool) or not isinstance(consecutive, int) or consecutive < 1:
            raise ValueError("Consecutive detections must be a positive integer")
        self.on, self.off, self.consecutive = on, off, consecutive
        self.active, self.count, self.last_timestamp = False, 0, None

    def update(self, timestamp_ns: int, score: float | None, *, available: bool, reason="") -> Decision:
        if self.last_timestamp is not None and timestamp_ns <= self.last_timestamp:
            raise ValueError("Decision timestamps must strictly increase")
        self.last_timestamp = timestamp_ns
        if not available:
            self.count = 0
            return Decision("UNAVAILABLE", self.active, None, reason or "INPUT_UNAVAILABLE")
        if score is None or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Available decisions require a finite score in [0, 1]")
        transition = None
        if self.active:
            if score < self.off:
                self.active, transition = False, "EXIT"
        else:
            self.count = self.count + 1 if score >= self.on else 0
            if self.count >= self.consecutive:
                self.active, self.count, transition = True, 0, "ENTER"
        return Decision("RISK" if self.active else "NORMAL", self.active, transition, "ADVISORY")
