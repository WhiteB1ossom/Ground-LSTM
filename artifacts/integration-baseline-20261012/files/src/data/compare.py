"""Compare acquisition schemas/quality without pretending synthetic data is measured."""

import argparse
import csv
import json
import logging
from pathlib import Path

from src.data.loader import discover_inputs, load_raw
from src.data.quality import inspect_quality
from src.utils.config import load_config


def compare_sources(field_config, lab_config) -> dict:
    configs = {"field_measurement": field_config, "lab_experiment": lab_config}
    summaries = {}
    for kind, config in configs.items():
        if config.settings["input"].get("acquisition_kind") != kind:
            raise ValueError(f"Expected {kind} configuration")
        files = discover_inputs(config)
        if not files: raise ValueError(f"No {kind} input files found")
        reports = []
        for path in files:
            raw = load_raw(path, source=config.settings["input"]["source"])
            if "acquisition_kind" in raw.frame:
                declared = set(raw.frame["acquisition_kind"].dropna().astype(str)) - {""}
                if declared - {kind}: raise ValueError(f"{path}: acquisition provenance mismatch")
            report = inspect_quality(raw, config)
            if report["dataset"]["synthetic"]: raise ValueError("Cannot use synthetic data as a measured-data comparison")
            reports.append({"dataset": report["dataset"], "label_status": report["label_status"],
                            "summary": report["summary"], "sensors": report["sensors"]})
        summaries[kind] = reports
    specs = {kind: {s.name: s for s in c.sensors if s.enabled} for kind, c in configs.items()}
    comparison = []
    for name in sorted(set(specs["field_measurement"]) | set(specs["lab_experiment"])):
        field, lab = specs["field_measurement"].get(name), specs["lab_experiment"].get(name)
        comparison.append({"sensor": name, "field_unit": field.unit if field else None, "lab_unit": lab.unit if lab else None,
                           "field_nominal_period": field.nominal_sampling_period if field else None,
                           "lab_nominal_period": lab.nominal_sampling_period if lab else None,
                           "units_confirmed_equal": bool(field and lab and field.unit is not None and field.unit == lab.unit)})
    return {"schema_version": 1, "purpose": "acquisition_schema_and_quality_comparison", "sources": summaries,
            "sensor_comparison": comparison,
            "notes": ["No forced resampling across acquisition sources.", "Equal units alone do not prove equal calibration/reference or physical distributions."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field-config", default="configs/preprocessing_field.yaml")
    parser.add_argument("--lab-config", default="configs/preprocessing_lab.yaml")
    parser.add_argument("--output", type=Path, default=Path("artifacts/reports/source-comparison.json"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        field, lab = load_config(args.field_config), load_config(args.lab_config)
        output = args.output.resolve()
        for config in (field, lab):
            raw_dir = config.resolve(config.settings["input"]["directory"])
            if output == raw_dir or raw_dir in output.parents: raise ValueError("Comparison output must be outside raw inputs")
        result = compare_sources(field, lab)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
        logging.getLogger(__name__).info("Saved source comparison: %s", output)
        return 0
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as error:
        logging.getLogger(__name__).error("Comparison failed: %s", error)
        return 2


if __name__ == "__main__": raise SystemExit(main())
