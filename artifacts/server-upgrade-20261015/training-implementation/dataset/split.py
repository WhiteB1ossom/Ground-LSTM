"""Partition raw observations before alignment, scaling or sliding windows."""

import numpy as np
import pandas as pd

NAMES = ("train", "validation", "test")


def event_keys(frame: pd.DataFrame) -> pd.Series:
    ids = frame["event_id"].fillna("").astype(str)
    devices = frame.get("device_id", pd.Series("", index=frame.index)).fillna("").astype(str)
    sessions = frame.get("session_id", pd.Series("", index=frame.index)).fillna("").astype(str)
    return pd.Series(list(zip(devices, sessions, ids)), index=frame.index)


def assert_event_isolation(parts: dict[str, pd.DataFrame]) -> None:
    seen = {}
    for split, frame in parts.items():
        if "event_id" not in frame: continue
        for value in event_keys(frame).unique():
            if not value[-1].strip(): continue
            if value in seen and seen[value] != split:
                raise ValueError(f"Data leakage: event_id {value!r} occurs in {seen[value]} and {split}")
            seen[value] = split


def split_raw(frame: pd.DataFrame, settings: dict) -> tuple[dict[str, pd.DataFrame], dict]:
    if frame.empty: raise ValueError("Cannot split an empty dataset")
    ids = frame["event_id"].fillna("").astype(str) if "event_id" in frame else pd.Series("", index=frame.index)
    mode = settings["mode"]
    if mode == "auto": mode = "event" if ids.str.strip().ne("").all() else "chronological"
    ratios = settings["ratios"]
    if mode == "event":
        if not ids.str.strip().ne("").all():
            raise ValueError("Event split requires event_id for every row, including explicit background group IDs")
        keys = event_keys(frame)
        # Explicit acquisition sessions stay together even with several labels/events.
        keys = keys.map(lambda key: (key[0], key[1], "") if key[1].strip() else key)
        groups = frame.assign(_event_key=keys).groupby("_event_key")["timestamp"].min().sort_values(kind="stable").index.tolist()
        if len(groups) < 3: raise ValueError("At least three event groups are required")
        first = min(max(1, int(len(groups) * ratios[0])), len(groups) - 2)
        second = min(max(first + 1, int(len(groups) * (ratios[0] + ratios[1]))), len(groups) - 1)
        assignments = {g: name for name, chunk in zip(NAMES, [groups[:first], groups[first:second], groups[second:]]) for g in chunk}
        assigned = keys.map(assignments)
        boundaries = [frame.loc[assigned.eq(name), "timestamp"].min() for name in NAMES[1:]]
    else:
        times = pd.Index(frame["timestamp"].unique()).sort_values()
        if len(times) < 3: raise ValueError("At least three unique timestamps are required")
        first = min(max(1, int(len(times) * ratios[0])), len(times) - 2)
        second = min(max(first + 1, int(len(times) * (ratios[0] + ratios[1]))), len(times) - 1)
        boundaries = [times[first], times[second]]
        assigned = pd.Series(np.where(frame["timestamp"] < boundaries[0], "train", np.where(frame["timestamp"] < boundaries[1], "validation", "test")), index=frame.index)
    # Apply a symmetric time embargo to all devices. Event rows can be trimmed,
    # but the remaining rows of an event never move to a different partition.
    gap = pd.Timedelta(seconds=settings["purge_gap_seconds"])
    keep = pd.Series(True, index=frame.index)
    if gap > pd.Timedelta(0):
        for boundary in boundaries:
            keep &= ~frame["timestamp"].between(boundary - gap, boundary + gap, inclusive="both")
    parts = {name: frame.loc[assigned.eq(name) & keep].copy() for name in NAMES}
    if any(part.empty for part in parts.values()): raise ValueError("Split or purge gap leaves an empty partition")
    assert_event_isolation(parts)
    return parts, {"mode": mode, "boundaries": [t.isoformat() for t in boundaries], "purged_rows": int((~keep).sum()),
                   "raw_rows": {name: len(part) for name, part in parts.items()},
                   "events": {name: sorted(set(part.get("event_id", pd.Series(dtype=str)).dropna().astype(str)) - {""}) for name, part in parts.items()}}
