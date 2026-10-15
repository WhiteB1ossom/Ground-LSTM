"""CLI: inspect original CSV/Parquet files before any preprocessing."""

import argparse
import csv
from dataclasses import asdict
import logging
from pathlib import Path

from src.data.loader import discover_inputs, load_raw
from src.data.quality import inspect_quality
from src.data.report import save_report
from src.utils.config import load_config

LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/preprocessing.yaml")
    parser.add_argument("--input", type=Path, help="One CSV/Parquet; default: discover configured raw directory")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(name)s: %(message)s")
    try:
        config = load_config(args.config)
        paths = [args.input.resolve()] if args.input else discover_inputs(config)
        if not paths:
            raise ValueError("No CSV/Parquet input found; supply --input or populate data/raw")
        output = args.report_dir.resolve() if args.report_dir else config.resolve(config.settings["report"]["directory"])
        raw_directory = config.resolve(config.settings["input"]["directory"])
        if output == raw_directory or raw_directory in output.parents:
            raise ValueError("Reports must be stored outside data/raw")
        exit_code = 0
        for path in paths:
            dataset = load_raw(path, source=config.settings["input"]["source"])
            report = inspect_quality(dataset, config)
            report["configuration"] = {"settings": config.settings, "sensors": [asdict(s) for s in config.sensors]}
            json_path, md_path = save_report(report, output)
            LOGGER.info("Inspected %s: %s rows; reports: %s, %s", path.name, len(dataset.frame), json_path, md_path)
            if report["summary"]["has_invalid_data"]:
                LOGGER.warning("Invalid data detected in %s; review JSON reason codes", path.name)
                exit_code = 1
        return exit_code
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as error:
        LOGGER.error("Inspection failed: %s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
