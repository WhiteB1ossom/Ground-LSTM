"""Generate a software-only multi-rate CSV/Parquet fixture."""

import argparse
import logging
from pathlib import Path

from src.data.synthetic import generate_frame, save_synthetic
from src.utils.config import load_config, read_yaml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/preprocessing.yaml")
    parser.add_argument("--synthetic-config", default="configs/synthetic.yaml")
    parser.add_argument("--output", type=Path, default=Path("data/raw/sample.synthetic.csv"))
    parser.add_argument("--inject-faults", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        config = load_config(args.config)
        settings = read_yaml(Path(args.synthetic_config))
        frame = generate_frame(config, settings, inject_faults=args.inject_faults)
        metadata = save_synthetic(frame, args.output, config, settings, inject_faults=args.inject_faults)
        logging.getLogger(__name__).info("Wrote %s rows to %s; metadata: %s; SOFTWARE TEST ONLY", len(frame), args.output, metadata)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        logging.getLogger(__name__).error("Generation failed: %s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
