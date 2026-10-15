"""Machine-readable and human-readable quality reports."""

import json
from pathlib import Path
import os
import tempfile


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def save_report(report: dict, directory: str | Path) -> tuple[Path, Path]:
    directory = Path(directory).resolve()
    source_path = Path(report["dataset"]["path"])
    stem = source_path.stem + "." + report["dataset"]["sha256"][:12]
    json_path, md_path = directory / f"{stem}.quality.json", directory / f"{stem}.quality.md"
    if directory == source_path.parent:
        raise ValueError("Reports must be stored outside the raw input directory")
    lines = ["# Data Quality Report", "", f"- File: `{_cell(source_path.name)}`",
             f"- SHA-256: `{report['dataset']['sha256']}`",
             f"- Source: {_cell(report['dataset']['source'])}",
             f"- Rows: {report['dataset']['rows']}",
             f"- Synthetic: {report['dataset']['synthetic']}",
             f"- Label status: {report['label_status']}",
             f"- Invalid data detected: {report['summary']['has_invalid_data']}", "",
             "## Reason counts", "", "| Reason | Count |", "|---|---:|"]
    lines += [f"| {code} | {count} |" for code, count in sorted(report["summary"]["reason_counts"].items())]
    lines += ["", "## Sensors", "", "| Sensor | Observations | Missing/unavailable ratio | Interval median (s) |", "|---|---:|---:|---:|"]
    for name, sensor in report["sensors"].items():
        lines.append(f"| {_cell(name)} | {sensor.get('observations', 'column missing')} | {sensor.get('missing_value_ratio')} | {sensor.get('observed_interval_seconds', {}).get('median')} |")
    lines += ["", "## Interpretation", ""] + [f"- {note}" for note in report["notes"]]
    lines += ["", "## Issue examples", "", "Row indexes are 0-based original data rows. Complete details are in JSON.", "",
              "| Row | Field | Reason | Category |", "|---:|---|---|---|"]
    lines += [f"| {i['row']} | {_cell(i['field'])} | {i['reason_code']} | {i['category']} |" for i in report["issues"][:100]]
    _write_atomic(json_path, json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    _write_atomic(md_path, "\n".join(lines) + "\n")
    return json_path, md_path
