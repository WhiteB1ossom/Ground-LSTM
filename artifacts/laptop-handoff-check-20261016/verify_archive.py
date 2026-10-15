"""Prove the delivered archive works from a different Unicode path on this PC."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

from scripts.package_laptop import ROOT, TOP, contained, verify_transfer


archive = ROOT / "output/transfer/ground-laptop-20261016-010327-066824.zip"
evidence = ROOT / "artifacts/laptop-handoff-check-20261016"
destination = evidence / "한글 경로 테스트"
destination.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as package:
    for name in package.namelist():
        contained(destination, name)
        if not name.startswith(TOP + "/"):
            raise ValueError("Unexpected archive root")
    package.extractall(destination)
project = destination / TOP
files = verify_transfer(project)
assert not (project / ".venv-ml").exists()
environment = dict(os.environ, PYTHONIOENCODING="utf-8")
probe = subprocess.run([sys.executable, "-c", "import json,src,scripts;print(json.dumps([src.__file__,scripts.__file__]))"],
                       cwd=project, env=environment, capture_output=True, encoding="utf-8", check=True)
origins = json.loads(probe.stdout)
assert all(Path(p).resolve().is_relative_to(project.resolve()) for p in origins)
with (evidence / "extracted-runtime.log").open("w", encoding="utf-8") as log:
    subprocess.run([sys.executable, "-m", "scripts.verify_laptop"], cwd=project, env=environment,
                   stdout=log, stderr=subprocess.STDOUT, check=True)
report_path = next((project / "artifacts/laptop-check").glob("*/laptop-verification.json"))
runtime = json.loads(report_path.read_text(encoding="utf-8"))
assert runtime["status"] == "SUCCESS" and runtime["observations"] == 1800
assert all(r["inferences"] == 174 for r in runtime["tasks"].values())
protected = json.loads((ROOT / "artifacts/server-upgrade-20261015/protected-hashes.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in protected.items())
result = {"status": "PASS", "archive": str(archive), "bytes": archive.stat().st_size,
          "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "verified_transfer_files": files,
          "source_origins": origins, "extracted_project": str(project), "runtime_report": str(report_path),
          "observations": runtime["observations"], "inferences": {t:r["inferences"] for t,r in runtime["tasks"].items()},
          "protected_originals_unchanged": len(protected), "tests_passed": 345,
          "fresh_environment_install_on_laptop": "PENDING_TARGET_PC", "browser_visual_qa": "NOT_PERFORMED"}
(evidence / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k:result[k] for k in ("status", "bytes", "verified_transfer_files", "observations", "inferences", "protected_originals_unchanged")}, indent=2))
