"""Isolated conversion: a native converter failure cannot kill the whole run."""

import argparse
from pathlib import Path

import numpy as np


def convert(saved_model: Path, representative: Path, kind: str, output: Path):
    import tensorflow as tf
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model))
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
    if kind == "float16":
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
    elif kind == "int8":
        with np.load(representative, allow_pickle=False) as data: values = data["X"]
        def samples():
            for row in values: yield [row[None, :]]
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.representative_dataset = samples
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.int8
        converter.inference_output_type = tf.int8
    output.write_bytes(converter.convert())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--saved-model", type=Path, required=True)
    parser.add_argument("--representative", type=Path, required=True)
    parser.add_argument("--kind", choices=("float32", "float16", "int8"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    convert(args.saved_model, args.representative, args.kind, args.output)
