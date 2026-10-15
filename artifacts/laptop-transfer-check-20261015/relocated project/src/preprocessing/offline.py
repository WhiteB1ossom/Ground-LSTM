"""Noncausal inspection only. Dataset/realtime builders never call this module."""

import pandas as pd


def interpolate_for_analysis(values: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(values.index, pd.DatetimeIndex) or not values.index.is_monotonic_increasing or not values.index.is_unique:
        raise ValueError("Offline analysis requires a unique ascending DatetimeIndex")
    result = values.interpolate(method="time", limit_area="inside")
    result.attrs["causal"] = False
    result.attrs["purpose"] = "OFFLINE_ANALYSIS_ONLY_NOT_MODEL_INPUT"
    return result
