"""Build updated portable delivery files and compare decisions with Python."""

import json
import math
from pathlib import Path
import subprocess

from src.embedded.resources import resource_report
from src.realtime.decision import DecisionEngine
from src.utils.config import read_yaml


root = Path.cwd()
output = Path(__file__).parent.resolve()
run = json.loads((root / "artifacts/integrated-20261012/run.json").read_text(encoding="utf-8"))
resources = output / "resources"
report = resource_report(Path(run["stages"]["bundle"]["path"]),
                         Path(run["stages"]["export"]["path"]),
                         read_yaml(root / "artifacts/integrated-20261012/replay-selected.yaml")["replay"],
                         root / "configs/target_mcu.yaml", resources)
assert report["portable_host"]["status"] == "SUCCESS", "See resources/host-build.log"


def literal(value):
    if math.isnan(value):
        return "std::numeric_limits<double>::quiet_NaN()"
    if math.isinf(value):
        return ("-" if value < 0 else "") + "std::numeric_limits<double>::infinity()"
    return format(value, ".17g")


invalid = [(0.7, 0.4, 0), (math.nan, 0.4, 2), (0.7, math.nan, 2),
           (math.inf, 0.4, 2), (-math.inf, 0.4, 2), (0.7, math.inf, 2),
           (0.7, -math.inf, 2), (-0.1, 0., 2), (0.7, -0.1, 2),
           (1.1, 0.4, 2), (1., 1.1, 2), (0.3, 0.7, 1)]
valid = [(0.7, 0.4, 2), (0.5, 0.5, 2), (0., 0., 2), (1., 1., 1),
         (0.1741286814212799, 0.1741286814212799, 2)]
source = ['#include "lightning_core.hpp"', '#include <limits>', '#include <iostream>', 'int main() {']
checks = 0
for on, off, required in invalid:
    source += ['{', f'lightning::Decision d({literal(on)}, {literal(off)}, {required});',
               'if (d.configuration_valid()) return 1;']
    for score in (0., 0.1, 0.5, 0.9, 1.):
        source += [f'{{ auto r = d.update({literal(score)}, true);',
                   f'if (r.available || r.alarm || r.transition) {{ std::cerr << "invalid case {checks}"; return 2; }} }}']
        checks += 1
    source += ['}']

steps = 0
for on, off, required in valid:
    policy = DecisionEngine(on, off, consecutive=required)
    sequence = [(on, True), (on, True), (off, True), (0., False),
                (max(0., off - 0.01), True), (on, True), (math.nan, True),
                (on, True), (math.inf, True), (on, True), (-0.1, True),
                (on, True), (1.1, True), (on, True), (on, True),
                (off, True), (0., True), (0., True)]
    source += ['{', f'lightning::Decision d({literal(on)}, {literal(off)}, {required});',
               'if (!d.configuration_valid()) return 3;']
    for timestamp, (score, available) in enumerate(sequence, start=1):
        usable = available and math.isfinite(score) and 0 <= score <= 1
        decision = policy.update(timestamp, score if usable else None, available=usable)
        transition = {None: 0, "ENTER": 1, "EXIT": -1}[decision.transition]
        source += [f'{{ auto r = d.update({literal(score)}, {str(available).lower()});',
                   f'if (r.available != {str(usable).lower()} || r.alarm != {str(decision.alarm_active).lower()} || r.transition != {transition})',
                   f'{{ std::cerr << "Python parity step {steps}"; return 4; }} }}']
        steps += 1
    source += ['}']
source += [f'std::cout << "PASS: {len(invalid)} invalid configurations, {checks} rejected decisions, {steps} Python parity steps";',
           'return 0;', '}']
(resources / "decision_boundaries.cpp").write_text("\n".join(source) + "\n", encoding="utf-8")

original = (resources / "build_host.cmd").read_text(encoding="utf-8")
environment = original.split("cl /nologo", 1)[0]
batch = (environment + "cl /nologo /std:c++17 /EHsc /utf-8 decision_boundaries.cpp /Fe:decision_boundaries.exe\n"
         "if errorlevel 1 exit /b 1\ndecision_boundaries.exe\n")
(resources / "build_decision_boundaries.cmd").write_text(batch, encoding="utf-8")
process = subprocess.run(["cmd.exe", "/d", "/c", "build_decision_boundaries.cmd"], cwd=resources,
                         capture_output=True, text=True, errors="replace", timeout=60)
(resources / "decision-build.log").write_text(process.stdout + process.stderr, encoding="utf-8")
assert process.returncode == 0, "See resources/decision-build.log"
assert (resources / "lightning_core.hpp").read_bytes() == (root / "src/embedded/portable/lightning_core.hpp").read_bytes()
result = {"status": "SUCCESS", "compiler": "MSVC C++17", "host_golden_vectors": 140,
          "invalid_configuration_cases": len(invalid), "invalid_configuration_decisions": checks,
          "valid_configuration_cases": len(valid), "python_decision_parity_steps": steps,
          "updated_delivery_directory": str(resources), "delivery_header_matches_source": True,
          "model_bytes": report["model_bytes"], "mcu_verified": False}
(output / "portable-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
