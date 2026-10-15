"""Extract pre/post segments for inspection, never post-event input leakage."""

import pandas as pd
import json

from src.data.schema import parse_timestamp


def extract_events(frame: pd.DataFrame, settings: dict, timestamp_settings: dict) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    records, segments = [], {}
    if "event_timestamp" not in frame or "event_id" not in frame: return pd.DataFrame(), segments
    frame = frame.copy()
    if "session_id" not in frame: frame["session_id"] = ""
    frame["session_id"] = frame["session_id"].fillna("").astype(str)
    annotated = frame.loc[frame["event_id"].fillna("").astype(str).str.strip().ne("")]
    namespaces = annotated[["device_id", "session_id", "event_id"]].drop_duplicates()
    repeated_ids = namespaces.groupby("event_id").size()
    for (device_id, session_id, event_id), group in annotated.groupby(["device_id", "session_id", "event_id"], sort=False):
        raw_times = group["event_timestamp"].dropna().astype(str)
        raw_times = raw_times[raw_times.str.strip().ne("")].unique()
        if not len(raw_times): continue
        parsed = []
        for raw in raw_times:
            stamp, reason = parse_timestamp(raw, timestamp_settings)
            if reason: raise ValueError(f"Invalid event_timestamp for {event_id}")
            parsed.append(stamp)
        if len(set(parsed)) != 1: raise ValueError(f"event_id {event_id} has multiple event times")
        event_time = parsed[0]
        pre = event_time - pd.Timedelta(seconds=settings["pre_event_seconds"])
        post = event_time + pd.Timedelta(seconds=settings["post_event_seconds"])
        # Only extract within this split and the involved devices. An event's
        # requested history may be truncated by the split/purge boundary.
        segment = frame.loc[frame["device_id"].eq(device_id) & frame["session_id"].eq(session_id) & frame["timestamp"].between(pre, post)].copy()
        segment["event_phase"] = segment["timestamp"].map(lambda t: "pre" if t < event_time else "detection" if t == event_time else "post")
        key = json.dumps([str(device_id), str(session_id), str(event_id)]) if repeated_ids.loc[event_id] > 1 else str(event_id)
        segments[key] = segment
        detection = group.loc[group["timestamp"].eq(event_time)]
        truth = detection["ground_truth"].iloc[0] if "ground_truth" in detection and not detection.empty else "UNLABELED"
        records.append({"event_id": str(event_id), "device_id": str(device_id), "session_id": str(session_id), "event_key": key, "event_time": event_time.isoformat(), "pre_event_start": pre.isoformat(),
                        "post_event_end": post.isoformat(), "source": str(group["source"].iloc[0]),
                        "acquisition_kind": str(group["acquisition_kind"].iloc[0]),
                        "ground_truth": str(truth),
                        "observed_rows": len(segment), "purpose": "offline_inspection_and_post_event_verification"})
    return pd.DataFrame(records), segments
