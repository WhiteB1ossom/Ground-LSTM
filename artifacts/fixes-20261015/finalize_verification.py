"""Collect final test evidence and verify protected originals."""

import compileall
import difflib
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


root = Path.cwd()
output = Path(__file__).parent.resolve()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


protected = json.loads((output / "protected-hashes.json").read_text(encoding="utf-8"))
changed = [name for name, before in protected.items() if digest(root / name) != before]
assert len(protected) == 98 and not changed, changed
tests = ET.parse(output / "tests-final.xml").getroot().findall("testsuite")
test_counts = {name: sum(int(suite.attrib[name]) for suite in tests)
               for name in ("tests", "failures", "errors", "skipped")}
assert test_counts == {"tests": 285, "failures": 0, "errors": 0, "skipped": 0}, test_counts
assert compileall.compile_dir(root / "src", quiet=1)
assert compileall.compile_file(root / "tests/test_realtime_lifecycle.py", quiet=1)

runtime = json.loads((output / "verification/runtime-verification.json").read_text(encoding="utf-8"))
portable = json.loads((output / "portable-verification.json").read_text(encoding="utf-8"))
assert runtime["status"] == portable["status"] == "SUCCESS"
assert runtime["aligned_rows"] == 7200 and runtime["events_verified"] == 8 and runtime["raw_event_records_verified"] == 568
assert runtime["recorder"]["shutdown_complete"] and not runtime["recorder"]["shutdown_timed_out"]
assert portable["host_golden_vectors"] == 140 and portable["python_decision_parity_steps"] == 90
assert (output / "resources/lightning_core.hpp").read_bytes() == (root / "src/embedded/portable/lightning_core.hpp").read_bytes()
baseline = json.loads((output / "baseline/hashes.json").read_text(encoding="utf-8"))
diff = []
for name, before in baseline.items():
    saved = output / "baseline" / name
    assert digest(saved) == before
    diff.extend(difflib.unified_diff(saved.read_text(encoding="utf-8").splitlines(True),
                                    (root / name).read_text(encoding="utf-8").splitlines(True),
                                    fromfile="baseline/" + name, tofile=name))
(output / "changed-sources.diff").write_text("".join(diff), encoding="utf-8")
sources = list(baseline) + ["tests/test_realtime_lifecycle.py", "docs/realtime-lifecycle-fixes-20261015.md"]
result = {"schema_version": 1, "date": "2026-10-15", "status": "SUCCESS",
          "tests": {**test_counts, "new_regression_cases": 30, "existing_dependency_warnings": 45,
                    "elapsed_seconds": sum(float(suite.attrib["time"]) for suite in tests)},
          "compileall": "SUCCESS", "protected_files": len(protected), "protected_changed": changed,
          "runtime_verification": runtime, "portable_verification": portable,
          "changed_source_sha256": {name: digest(root / name) for name in sources},
          "model_retrained": False, "thresholds_changed": False, "hardware_actuation_performed": False,
          "mcu_verified": False,
          "limitations": ["Live pipeline cannot preempt a blocked predictor or output callback.",
                          "Recorder timeout reports incomplete work; an in-flight write may finish later.",
                          "Multiple pending receive gaps are coalesced into one bounded record and counted.",
                          "TFLM target build, arena, timing and physical sensor performance remain unverified."]}
(output / "verification.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
print(json.dumps({"status": result["status"], "tests": result["tests"], "protected_files": len(protected),
                  "protected_changed": changed, "real_replay_rows": runtime["aligned_rows"],
                  "portable_host": portable["status"], "mcu_verified": False}))
