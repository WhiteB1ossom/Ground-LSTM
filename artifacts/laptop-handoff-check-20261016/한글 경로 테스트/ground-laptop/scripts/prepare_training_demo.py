"""Create explicitly labeled SOFTWARE fixtures; never infer labels in real data."""

import argparse
import logging
from pathlib import Path

from src.data.synthetic import generate_frame, save_synthetic
from src.dataset.build import build_dataset
from src.utils.config import load_config, read_yaml


def prepare_demo(output: Path, dataset_output: Path | None = None) -> Path:
    config = load_config("configs/preprocessing_training_demo.yaml")
    settings = read_yaml(Path("configs/synthetic_phase2.yaml"))
    fixture = read_yaml(Path("configs/training_fixture.yaml"))
    if fixture["purpose"] != "SOFTWARE_TRAINING_TEST_ONLY_NOT_PHYSICAL_PERFORMANCE":
        raise ValueError("Fixture purpose must explicitly forbid physical performance claims")
    frame = generate_frame(config, settings)
    frame["ground_truth"] = frame["synthetic_state"].map(fixture["synthetic_state_mapping"])
    if frame["ground_truth"].isna().any(): raise ValueError("Unknown synthetic fixture state")
    metadata = save_synthetic(frame, output, config, settings, inject_faults=False)
    import json
    document = json.loads(metadata.read_text(encoding="utf-8"))
    document.update(labels="SOFTWARE_FIXTURE_LABELS_ONLY", labeling_fixture=fixture)
    metadata.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return build_dataset(config, [output], output=dataset_output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/phase3-training.synthetic.csv"))
    parser.add_argument("--dataset-output", type=Path)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        result = prepare_demo(args.output, args.dataset_output)
        logging.getLogger(__name__).info("Prepared SOFTWARE-ONLY labeled dataset: %s", result)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        logging.getLogger(__name__).error("Preparation failed: %s", error)
        return 2


if __name__ == "__main__": raise SystemExit(main())
