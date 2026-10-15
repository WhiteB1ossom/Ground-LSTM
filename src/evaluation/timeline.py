"""Offline traces use exactly the same definitions as live evaluation."""

from src.evaluation.stream_metrics import StreamMetrics


def timeline_metrics(rows: list[dict], *, threshold: float, period_seconds: float) -> dict:
    accumulator = StreamMetrics(threshold, period_seconds)
    for row in rows:
        accumulator.consume(row)
    return {"schema_version": 1, **accumulator.finish()}
