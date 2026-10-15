"""Check the real selected LiteRT CLI with typed Parquet and rotated traces."""
import copy
from itertools import zip_longest
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.realtime.timeline import iter_timeline

root = Path.cwd()
output = Path(__file__).parent.resolve() / "verification-2"
if output.exists(): raise FileExistsError("Verification output exists")
output.mkdir()
inputs = output / "inputs"
if inputs.exists() and any(inputs.iterdir()): raise FileExistsError("Verification inputs exist")
inputs.mkdir(exist_ok=True)
run = json.loads((root / "artifacts/integrated-20261012/run.json").read_text(encoding="utf-8"))
calibrated = Path(run["stages"]["calibrated_replay"]["path"])
frame = pd.read_csv(calibrated / "inputs/heldout.synthetic.csv", keep_default_na=False)
table = pa.Table.from_pandas(frame, preserve_index=False)
stamps = pd.to_datetime(frame["timestamp"], utc=True, format="ISO8601").astype("datetime64[ns, UTC]")
assert (stamps.array.asi8 % 1000 == 0).all(), "Source timestamps cannot be represented exactly in microseconds"
table = table.set_column(table.schema.get_field_index("timestamp"), "timestamp", pa.array(stamps, type=pa.timestamp("us", tz="UTC")))
pq.write_table(table, inputs / "heldout.parquet")
settings = yaml.safe_load((root / "artifacts/integrated-20261012/replay-selected.yaml").read_text(encoding="utf-8"))
settings["replay"].update(timeline_segment_bytes=2*1024*1024, timeline_max_segments=16)
(inputs / "replay.yaml").write_text(yaml.safe_dump(settings), encoding="utf-8")
bundle = run["stages"]["bundle"]["path"]
model = str(Path(run["stages"]["export"]["path"]) / "model-float32.tflite")

def invoke(name, path, config):
    target = output / name
    result = subprocess.run([sys.executable, "-m", "src.realtime.replay", "--input", str(path), "--bundle", bundle,
                             "--model", "tflite", "--tflite", model, "--config", str(config), "--output", str(target)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    (output / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    return result.returncode, target

code, target = invoke("parquet-replay", inputs / "heldout.parquet", inputs / "replay.yaml")
assert code == 0, (code, "see parquet-replay.log")
summary = json.loads((target / "summary.json").read_text(encoding="utf-8"))
assert summary["status"] == "SUCCESS" and summary["aligned_rows"] == 7200
assert len(summary["timeline"]["files"]) > 1 and not summary["timeline"]["retention_truncated"]
count = 0
maximum_error = 0.
for before, after in zip_longest(iter_timeline(calibrated / "replay/heldout"), iter_timeline(target)):
    assert before is not None and after is not None
    for key in ("timestamp_ns", "input_status", "available", "decision"):
        assert before[key] == after[key], key
    if before["prediction"]:
        error = abs(before["prediction"]["risk_score"] - after["prediction"]["risk_score"])
        assert error < 1e-6
        maximum_error = max(maximum_error, error)
    count += 1
bad = frame.iloc[:2].copy()
bad.loc[bad.index[1], "timestamp"] = bad.iloc[0]["timestamp"]
bad.to_csv(inputs / "duplicate.csv", index=False)
bad_code, _ = invoke("rejected-replay", inputs / "duplicate.csv", inputs / "replay.yaml")
assert bad_code == 1
invalid = copy.deepcopy(settings)
invalid["replay"]["input_timeout_seconds"] = 0
(inputs / "invalid.yaml").write_text(yaml.safe_dump(invalid), encoding="utf-8")
invalid_code, _ = invoke("invalid-config", inputs / "heldout.parquet", inputs / "invalid.yaml")
assert invalid_code == 2
result = {"status":"SUCCESS", "typed_parquet_unit":"us", "aligned_rows":count,
          "max_score_error_against_saved_keras":maximum_error,
          "retained_segments":len(summary["timeline"]["files"]), "timeline":summary["timeline"],
          "cli_exit_codes":{"success":code,"degraded":bad_code,"configuration_error":invalid_code},
          "model_retrained":False, "mcu_verified":False}
(output / "cli-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"status":result["status"], "rows":count, "segments":result["retained_segments"], "exit_codes":result["cli_exit_codes"]}))
