"""Windows never cross a stream, event segment, partition or time gap."""

import numpy as np
import pandas as pd


def build_windows(values: np.ndarray, metadata: pd.DataFrame, labels: list[int], valid: np.ndarray, settings: dict, *, period_seconds: float) -> dict:
    length, stride = int(settings["sequence_length"]), int(settings["stride"])
    horizon = settings["label_horizon_seconds"] / period_seconds
    if not np.isclose(horizon, round(horizon)):
        raise ValueError("label_horizon_seconds must be an integer multiple of alignment period")
    horizon = round(horizon)
    X, y, starts, ends, targets = [], [], [], [], []
    expected = pd.Timedelta(seconds=period_seconds)
    for start in range(0, len(values) - length - horizon + 1, stride):
        end, target = start + length - 1, start + length - 1 + horizon
        times = metadata["timestamp"].iloc[start:target + 1]
        if not valid[start:end + 1].all(): continue
        guarded = ["segment_id", "device_id", "session_id", "source", "split"]
        if not settings.get("allow_event_crossing", False): guarded.append("event_id")
        if any(metadata[column].iloc[start:target + 1].nunique(dropna=False) > 1
               for column in guarded if column in metadata):
            continue
        if len(times) > 1 and not times.diff().iloc[1:].eq(expected).all(): continue
        X.append(values[start:end + 1]); y.append(labels[target])
        starts.append(metadata["timestamp"].iloc[start].isoformat())
        ends.append(metadata["timestamp"].iloc[end].isoformat())
        targets.append(metadata["timestamp"].iloc[target].isoformat())
    return {"X": np.stack(X) if X else np.empty((0, length, values.shape[1]), dtype=np.float32),
            "y": np.asarray(y, dtype=np.int64), "start_timestamp": np.array(starts, dtype=str),
            "end_timestamp": np.array(ends, dtype=str), "target_timestamp": np.array(targets, dtype=str)}
