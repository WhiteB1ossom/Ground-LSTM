"""Verify the selected real backends and capture without modifying trained artifacts."""

from itertools import zip_longest
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from src.realtime.inference import InferenceEngine
from src.realtime.stream import RealtimePipeline
from src.realtime.timeline import iter_timeline
from src.utils.config import read_yaml


root = Path.cwd()
output = Path(__file__).parent.resolve() / "verification"
output.mkdir(exist_ok=False)
run = json.loads((root / "artifacts/integrated-20261012/run.json").read_text(encoding="utf-8"))
calibrated = Path(run["stages"]["calibrated_replay"]["path"])
bundle = Path(run["stages"]["bundle"]["path"])
lite_model = Path(run["stages"]["export"]["path"]) / "model-float32.tflite"
config = root / "artifacts/integrated-20261012/replay-selected.yaml"
input_file = root / "artifacts/bugfix-20261013/verification-2/inputs/heldout.parquet"
target = output / "parquet-replay"
process = subprocess.run([sys.executable, "-m", "src.realtime.replay", "--input", str(input_file), "--bundle", str(bundle),
                          "--model", "tflite", "--tflite", str(lite_model), "--config", str(config), "--output", str(target)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
(output / "parquet-replay.log").write_text(process.stdout + process.stderr, encoding="utf-8")
assert process.returncode == 0, "See parquet-replay.log"
summary = json.loads((target / "summary.json").read_text(encoding="utf-8"))
assert summary["status"] == "SUCCESS" and summary["aligned_rows"] == 7200
assert summary["recorder"]["accepted_raw_observations"] == 7200
assert not summary["recorder"]["raw_history_dropped"] and not summary["recorder"]["raw_event_dropped"]
assert not summary["recorder"]["writer_error_count"]
count, maximum_error = 0, 0.
for before, after in zip_longest(iter_timeline(calibrated / "replay/heldout"), iter_timeline(target)):
    assert before is not None and after is not None
    for key in ("timestamp_ns", "processed_values", "input_status", "available", "decision"):
        assert before[key] == after[key], key
    if before["prediction"]:
        error = abs(before["prediction"]["risk_score"] - after["prediction"]["risk_score"])
        assert error < 1e-6
        maximum_error = max(maximum_error, error)
    count += 1
saved_events, saved_raw = 0, 0
source = pd.read_parquet(input_file)
source_ns = pd.to_datetime(source["timestamp"], utc=True).astype("datetime64[ns, UTC]").array.asi8
for path in sorted((target / "events").glob("*.json")):
    event = json.loads(path.read_text(encoding="utf-8"))
    assert not event["raw_observations_truncated"]
    observed = [r["timestamp_ns"] for r in event["raw_observations"]]
    session = event["samples"][-1]["session_id"]
    expected = source_ns[(source_ns >= event["start_ns"]) & (source_ns <= event["end_requested_ns"]) &
                         (source["session_id"].astype(str).to_numpy() == session)].tolist()
    assert observed == expected, path.name
    saved_events += 1
    saved_raw += len(observed)

import tensorflow as tf
engine = InferenceEngine(bundle, model="lstm")
pipeline = RealtimePipeline(engine, read_yaml(config)["replay"])
pipeline.decision.active = True
normal_predict = engine.predict_fn
def fail(tensor): raise tf.errors.InternalError(None, None, "injected real-adapter failure")
engine.predict_fn = fail
failure, recovered = None, None
for observation in source.iloc[:80].to_dict("records"):
    for row in pipeline.feed(observation):
        if row["decision"]["reason"].startswith("INFERENCE_ERROR:InternalError"):
            failure = row
            assert not row["available"] and row["decision"]["alarm_active"]
            engine.predict_fn = normal_predict
        elif failure is not None and row["prediction"] is not None:
            recovered = row
assert failure is not None and recovered is not None and recovered["available"]
result = {"status": "SUCCESS", "aligned_rows": count, "max_score_error_against_saved_keras": maximum_error,
          "cli_exit_code": process.returncode, "recorder": summary["recorder"],
          "events_verified": saved_events, "raw_event_records_verified": saved_raw,
          "real_keras_error_became_unavailable": True, "real_keras_alarm_preserved": True, "real_keras_recovered": True,
          "model_retrained": False, "mcu_verified": False}
(output / "runtime-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k != "recorder"}))
