"""Ground truth mapping is explicit; unknown labels never become normal."""

import pandas as pd


def map_labels(values: pd.Series, settings: dict) -> tuple[list[int], str]:
    mapping = settings["mapping"]
    lookup = {} if mapping is None else {str(k): v for k, v in mapping.items()}
    mapped = []
    for value in values:
        text = "" if pd.isna(value) else str(value).strip()
        if not text or text.upper() == "UNLABELED" or mapping is None:
            mapped.append(-1)
        elif text in lookup:
            mapped.append(lookup[text])
        else:
            raise ValueError(f"Unknown ground_truth label {text!r}; update explicit labeling.mapping")
    status = "UNLABELED" if all(v < 0 for v in mapped) else "PARTIALLY_LABELED" if any(v < 0 for v in mapped) else "LABELED"
    return mapped, status
