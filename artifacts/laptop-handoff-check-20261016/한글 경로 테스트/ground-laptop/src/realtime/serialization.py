"""Normalize Arrow, pandas and Python scalar values for strict JSON records."""

from datetime import date, datetime, time

import numpy as np
import pandas as pd


def json_value(value):
    if value is pd.NaT or value is pd.NA: return None
    if isinstance(value, dict): return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)): return [json_value(v) for v in value]
    if isinstance(value, (float, np.floating)): return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_): return bool(value)
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.datetime64): return None if np.isnat(value) else pd.Timestamp(value).isoformat()
    if isinstance(value, (pd.Timestamp, datetime, date, time)): return value.isoformat()
    return value
