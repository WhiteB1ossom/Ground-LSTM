"""Read CSV/Parquet without filling, sorting, dropping or relabeling raw data."""

import hashlib
from pathlib import Path

import pandas as pd

from src.data.schema import RawDataset
from src.utils.config import PipelineConfig


def load_raw(path: str | Path, *, source: str) -> RawDataset:
    path = Path(path).resolve()
    if path.suffix.lower() == ".csv":
        # Keep empty cells, literal NaN/Inf, labels and identifiers distinguishable.
        # Reject duplicate headers instead of letting pandas silently rename them.
        import csv
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, [])
            if not header or any(not name.strip() for name in header):
                raise ValueError(f"{path}: empty file or unnamed column")
            if len(header) != len(set(header)):
                raise ValueError(f"{path}: duplicate column names")
            for record, fields in enumerate(reader, start=2):
                if len(fields) != len(header):
                    raise ValueError(f"{path}: CSV record {record} has {len(fields)} fields; expected {len(header)}")
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", skip_blank_lines=False)
    elif path.suffix.lower() == ".parquet":
        import pyarrow.parquet as parquet
        table = parquet.read_table(path)
        frame = table.to_pandas()
        # Retain Parquet's null bitmap: pandas float columns otherwise collapse
        # acquisition non-observations and an explicit IEEE NaN into the same value.
        for name in table.column_names:
            nulls = table[name].is_null().to_numpy()
            if nulls.any():
                frame[name] = frame[name].astype(object)
                frame.loc[nulls, name] = None
    else:
        raise ValueError(f"Unsupported input format: {path.suffix}")
    if "timestamp" not in frame.columns:
        raise ValueError(f"{path}: required timestamp column missing")
    if not frame.columns.is_unique:
        raise ValueError(f"{path}: duplicate column names")
    # A config represents one source; fail if source metadata disagrees.
    if "source" in frame:
        declared = set(frame["source"].dropna().astype(str)) - {""}
        if declared - {source}:
            raise ValueError(f"{path}: source {declared} conflicts with configured {source!r}; use a separate source config")
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return RawDataset(frame, path, source, digest)


def discover_inputs(config: PipelineConfig) -> list[Path]:
    settings = config.settings["input"]
    directory = config.resolve(settings["directory"])
    paths = {p.resolve() for pattern in settings["patterns"] for p in directory.glob(pattern) if p.is_file()}
    return sorted(paths)
