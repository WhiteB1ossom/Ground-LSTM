"""Portable constants/golden vectors and honest host versus MCU resource audit."""

import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pandas as pd

from src.features.transform import FeatureTransform
from src.preprocessing.alignment import CausalAligner
from src.realtime.inference import InferenceEngine
from src.realtime.ring_buffer import buffer_capacity
from src.utils.config import SensorSpec, read_yaml


def _array(name, values, dtype="double"):
    literals = ["true" if v else "false" for v in values] if dtype == "bool" else [format(float(v), ".17g") for v in values]
    return f"inline constexpr std::array<{dtype}, {len(values)}> {name} = {{{', '.join(literals)}}};\n"


def resource_report(bundle: Path, export_dir: Path, realtime: dict, target_config: Path, output: Path) -> dict:
    if output.exists(): raise FileExistsError("Resource output exists")
    output.mkdir(parents=True)
    engine = InferenceEngine(bundle, model="logistic")
    m = engine.manifest
    p = m["configuration"]["pipeline"]
    sensors = tuple(SensorSpec(**s) for s in m["sensors"] if s["enabled"])
    if p["features"] != ["current_value"] or not p["include_missing_indicators"] or not p["include_age_features"] or p["ground_voltage_difference"]:
        raise ValueError("Portable core currently supports current/missing/age features only")
    length, width = engine.shape[1:]
    capacity = buffer_capacity(length, realtime["pre_event_seconds"], p["alignment_period_seconds"])
    target = read_yaml(target_config)
    for key in ("usable_flash_bytes", "usable_ram_bytes", "flash_kb", "ram_kb", "cpu_mhz", "tensor_arena_bytes"):
        value = target.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
            raise ValueError(f"Invalid target resource budget: {key}")
    header = "#pragma once\n#include <array>\nnamespace fixture {\n"
    for name in ("fill", "offset", "scale"): header += _array(name, getattr(engine.scaler, name))
    header += _array("stale", [s.max_staleness for s in sensors])
    header += _array("critical", [s.missing_value_policy == "drop_window" for s in sensors], "bool")
    header += "}\n"
    (output / "preprocessing_constants.hpp").write_text(header, encoding="utf-8")
    portable = Path(__file__).parent / "portable"
    for name in ("lightning_core.hpp", "tflm_adapter.hpp"): shutil.copyfile(portable / name, output / name)
    exports = json.loads((export_dir / "export-report.json").read_text(encoding="utf-8"))
    chosen_kind = next((kind for kind in ("float32", "int8", "float16") if exports["formats"][kind]["status"] == "SUCCESS"), None)
    chosen = exports["formats"][chosen_kind] if chosen_kind else None
    if chosen:
        payload = Path(chosen["path"]).read_bytes()
        (output / "model_data.hpp").write_text("#pragma once\n#include <cstddef>\nextern const unsigned char lightning_model[];\nextern const std::size_t lightning_model_size;\n", encoding="utf-8")
        code = '#include "model_data.hpp"\nalignas(16) const unsigned char lightning_model[] = {\n'
        code += "\n".join(",".join(str(v) for v in payload[i:i + 32]) + "," for i in range(0, len(payload), 32))
        code += "\n};\nconst std::size_t lightning_model_size = sizeof(lightning_model);\n"
        (output / "model_data.cc").write_text(code, encoding="utf-8")
    # Generated observations cover absent data, invalid values, staleness and recovery.
    aligner, transform = CausalAligner(sensors, stale_action=p["stale_action"]), FeatureTransform(sensors, p)
    start = pd.Timestamp("2026-01-01T00:00:00Z")
    vectors = []
    for tick in range(140):
        timestamp = start + pd.Timedelta(seconds=tick * p["alignment_period_seconds"])
        values, modes, row = [], [], {}
        for i, sensor in enumerate(sensors):
            observed = tick == 0 or tick % int(round(sensor.nominal_sampling_period / p["alignment_period_seconds"])) == 0
            invalid = i == 0 and 80 <= tick < 84
            v = (i + 1) * .125 + tick * .002
            values.append(v)
            modes.append(2 if invalid else 1 if observed else 0)
            row[sensor.name] = "NaN" if invalid else v if observed else ""
        aligner.update(timestamp, row)
        sample = aligner.sample(timestamp)
        expected = engine.scaler.transform(transform.transform(sample)[None, :], transform.order)[0]
        vectors.append({"timestamp_ns": timestamp.value, "values": values, "modes": modes, "expected": expected.tolist(), "valid": sample.valid})
    (output / "golden-vectors.json").write_text(json.dumps(vectors), encoding="utf-8")
    test = '#include "lightning_core.hpp"\n#include "preprocessing_constants.hpp"\n#include <iostream>\nint main(){\n'
    test += f"lightning::CausalCurrent<{len(sensors)}> state; lightning::Ring<{capacity},{width}> ring; std::array<float,{width}> out;\n"
    for vector in vectors:
        vals = ",".join(format(v, ".17g") for v in vector["values"])
        modes = ",".join(str(v) for v in vector["modes"])
        expected = ",".join(format(v, ".17g") for v in vector["expected"])
        test += "{\n"
        test += f"state.update({vector['timestamp_ns']}LL, {{{vals}}}, {{{modes}}});\n"
        test += f"bool valid=state.features<{width}>({vector['timestamp_ns']}LL,fixture::stale,fixture::critical,fixture::fill,fixture::offset,fixture::scale,out);\n"
        test += f"if(valid != {'true' if vector['valid'] else 'false'}) return 2; std::array<double,{width}> expected={{{expected}}};\n"
        test += f"for(std::size_t j=0;j<{width};++j) if(std::abs(out[j]-expected[j])>1e-5) return 3;\n"
        test += f"if(!ring.append({vector['timestamp_ns']}LL,out,valid)) return 4;\n}}\n"
    test += f"std::array<float,{length * width}> seq; if(ring.latest<{length}>(seq.data(),{int(p['alignment_period_seconds'] * 1e9)}LL)) return 5;\n"
    test += "lightning::Decision decision(.7,.4,2); if(decision.update(.8,true).alarm) return 6; if(!decision.update(.8,true).alarm) return 7; if(!decision.update(0,false).alarm) return 8; if(decision.update(.2,true).alarm) return 9;\n"
    test += 'std::cout << "{\\\"ring_sizeof_bytes\\\":" << sizeof(ring) << ",\\\"golden_vectors\\\":140}"; return 0;}\n'
    (output / "host_check.cpp").write_text(test, encoding="utf-8")
    host = {"status": "TOOLCHAIN_UNAVAILABLE", "mcu_verified": False}
    vswhere = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft Visual Studio/Installer/vswhere.exe"
    if vswhere.is_file():
        probe = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"], capture_output=True, text=True, check=True)
        installation = Path(probe.stdout.strip())
        developer = installation / "Common7/Tools/VsDevCmd.bat"
        if developer.is_file():
            # Fixed local source names; shell only establishes the MSVC environment.
            model_source = " model_data.cc" if chosen else ""
            batch = '@echo off\ncall "' + str(developer) + '" -no_logo -arch=x64\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /EHsc host_check.cpp' + model_source + ' /Fe:host_check.exe\nif errorlevel 1 exit /b 1\nhost_check.exe\n'
            (output / "build_host.cmd").write_text(batch, encoding="utf-8")
            built = subprocess.run(["cmd.exe", "/d", "/c", "build_host.cmd"], cwd=output, capture_output=True, text=True, errors="replace")
            (output / "host-build.log").write_text(built.stdout + built.stderr, encoding="utf-8")
            host = {"status": "SUCCESS" if built.returncode == 0 else "FAILED", "exit_code": built.returncode, "mcu_verified": False}
    report = {"schema_version": 1, "deployment_feasibility": "UNKNOWN", "target": target,
              "ring_array_payload_bytes": capacity * (width * 4 + 8 + 1), "ring_capacity": capacity,
              "input_tensor_bytes": length * width * 4, "sequence_workspace_bytes": length * 9,
              "portable_host": host, "tensor_arena_bytes": None, "firmware_flash_bytes": None,
              "raw_history_and_recorder_total_bytes": None, "total_mcu_ram_bytes": None, "mcu_latency": None,
              "model_bytes": chosen["bytes"] if chosen else None, "c_array_candidate_format": chosen_kind,
              "notes": ["Host core compiled separately from TFLM adapter; target kernels/board not verified.",
                        "Arena includes state/scratch: do not double count.", "Raw history, writer, stack and firmware require a target implementation."]}
    flash_budget = target.get("usable_flash_bytes")
    ram_budget = target.get("usable_ram_bytes")
    if flash_budget is None and target.get("flash_kb") is not None: flash_budget = target["flash_kb"] * 1024
    if ram_budget is None and target.get("ram_kb") is not None: ram_budget = target["ram_kb"] * 1024
    lower_ram = report["ring_array_payload_bytes"] + report["input_tensor_bytes"] + report["sequence_workspace_bytes"]
    report["ram_known_lower_bound_bytes"] = lower_ram
    if (flash_budget is not None and chosen and chosen["bytes"] > flash_budget) or (ram_budget is not None and lower_ram > ram_budget):
        report["deployment_feasibility"] = "INFEASIBLE_KNOWN_LOWER_BOUND"
    (output / "resource-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
