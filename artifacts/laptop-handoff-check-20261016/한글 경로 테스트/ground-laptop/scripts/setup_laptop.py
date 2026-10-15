"""Create a local Python 3.12 environment, install the lock and verify real models."""

import argparse
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys
import venv

from scripts.package_laptop import MANIFEST, ROOT, RUN, RAW, verify_transfer


def check_python(system, version, bits, machine):
    if system != "Windows" or tuple(version[:2]) != (3, 12) or bits != 64 or machine.lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("Use Windows x64 and Python 3.12 x64. See LAPTOP_CODEX_HANDOFF.md")


def run(arguments, root):
    subprocess.run([str(a) for a in arguments], cwd=root, check=True)


def setup(root, *, skip_install=False):
    check_python(platform.system(), sys.version_info, struct.calcsize("P") * 8, platform.machine())
    required = ["pyproject.toml", "requirements-integration-lock.txt", "src/realtime/demo.html",
                RUN / "server-models.json", RAW / "heldout.synthetic.csv"]
    for name in required:
        if not (root / name).is_file():
            raise FileNotFoundError(f"Unpack the entire project first; missing: {name}")
    if (root / MANIFEST).exists():
        print(f"Transfer SHA256 checked: {verify_transfer(root)} files", flush=True)
    environment = root / ".venv-ml"
    python = environment / "Scripts/python.exe"
    if not environment.exists():
        if skip_install:
            raise RuntimeError("No .venv-ml found. Run setup-laptop.cmd without --skip-install first")
        print("Creating .venv-ml using Python 3.12...", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    if not python.is_file() or not (environment / "pyvenv.cfg").is_file():
        raise RuntimeError("Existing .venv-ml is incomplete. Preserve it and choose a clean project folder")
    probe = subprocess.run([str(python), "-c", "import json,sys,struct;print(json.dumps({'version':list(sys.version_info[:2]),'bits':struct.calcsize('P')*8,'prefix':sys.prefix,'base':sys.base_prefix}))"],
                           cwd=root, capture_output=True, text=True, check=True)
    actual = json.loads(probe.stdout)
    if (actual["version"] != [3, 12] or actual["bits"] != 64
            or Path(actual["prefix"]).resolve() != environment.resolve() or actual["prefix"] == actual["base"]):
        raise RuntimeError("Existing .venv-ml does not match this Windows Python 3.12 project")
    if not skip_install:
        print("Installing pinned packages (internet required)...", flush=True)
        run([python, "-m", "pip", "install", "--only-binary=:all:", "-r", "requirements-integration-lock.txt"], root)
        run([python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", "."], root)
    run([python, "-m", "pip", "check"], root)
    run([python, "-m", "scripts.verify_laptop"], root)
    print("\nSETUP SUCCESS. Run run-demo.cmd to open the presentation. No retraining needed.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-install", action="store_true", help="Check an existing environment and run actual model verification")
    parser.add_argument("--non-interactive", action="store_true", help="Tell the CMD launcher not to pause on completion")
    args = parser.parse_args(argv)
    try:
        setup(ROOT, skip_install=args.skip_install)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nSETUP FAILED: {error}\nRead LAPTOP_CODEX_HANDOFF.md. Keep the exact error; do not loosen the lock or retrain.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
