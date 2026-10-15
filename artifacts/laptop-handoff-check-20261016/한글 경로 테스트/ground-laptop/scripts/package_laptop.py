"""Build a small, hashed laptop handoff without copying environments or old runs."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUN = Path("artifacts/server-equipment-20261015")
RAW = Path("data/raw/equipment-server/server-equipment-20261015")
MANIFEST = "TRANSFER-MANIFEST.json"
TOP = "ground-laptop"
ROOT_FILES = ("README.md", "START_HERE.md", "LAPTOP_CODEX_HANDOFF.md", "setup-laptop.cmd", "run-demo.cmd",
              "pyproject.toml", ".gitignore", "requirements.txt", "requirements-lock.txt",
              "requirements-ml-lock.txt", "requirements-integration-lock.txt")


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def contained(root, relative):
    name = PurePosixPath(relative)
    if not relative or name.is_absolute() or ".." in name.parts or "\\" in relative or ":" in relative:
        raise ValueError("Invalid transfer path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Transfer path escaped its project")
    return path


def verify_transfer(root):
    manifest_path = root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if manifest.get("schema_version") != 1 or not isinstance(files, dict) or not files:
        raise ValueError("Invalid transfer manifest")
    for name, digest in files.items():
        path = contained(root, name)
        if not path.is_file() or sha256(path.read_bytes()) != digest:
            raise ValueError(f"Missing or changed transfer file: {name}")
    return len(files)


def transfer_files(root):
    paths = [root / name for name in ROOT_FILES]
    for name in ("src", "scripts", "configs", "tests", "docs", "output/presentations"):
        paths.extend(p for p in (root / name).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"})
    paths.append(root / RUN / "server-models.json")
    for task in ("degradation", "surge"):
        paths.append(root / RUN / task / "replay-selected.yaml")
        paths.extend(p for p in (root / RUN / task / "bundle").rglob("*") if p.is_file())
    paths.append(root / RUN / "recipe/preprocessing.yaml")
    paths.extend(root / RAW / name for name in ("heldout.synthetic.csv", "scenarios.json"))
    result = {}
    for path in paths:
        relative = path.relative_to(root).as_posix()
        actual = contained(root, relative)
        if not actual.is_file():
            raise FileNotFoundError(relative)
        result[relative] = actual
    # Never produce an apparently complete archive with missing model assets.
    for task in ("degradation", "surge"):
        for name in ("bundle.json", "best_model.keras", "scaler.json", "dataset-manifest.json"):
            if (RUN / task / "bundle" / name).as_posix() not in result:
                raise FileNotFoundError(f"Incomplete {task} bundle: {name}")
    return dict(sorted(result.items()))


def build(root, output):
    files = transfer_files(root)
    manifest = {"schema_version": 1, "purpose": "windows_x64_python312_actual_model_synthetic_demo",
                "created_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
                "files": {name: sha256(path.read_bytes()) for name, path in files.items()},
                "excluded": ["Python environments", "caches", "historical experiment runs", "full training datasets"],
                "entry_points": {"setup": "setup-laptop.cmd", "demo": "run-demo.cmd", "handoff": "LAPTOP_CODEX_HANDOFF.md"}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, path in files.items():
            archive.write(path, f"{TOP}/{name}")
        archive.writestr(f"{TOP}/{MANIFEST}", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        expected = {f"{TOP}/{name}" for name in files} | {f"{TOP}/{MANIFEST}"}
        if set(archive.namelist()) != expected or archive.testzip() is not None:
            raise RuntimeError("Archive integrity check failed")
        for name, digest in manifest["files"].items():
            if sha256(archive.read(f"{TOP}/{name}")) != digest:
                raise RuntimeError(f"Archive hash mismatch: {name}")
    return {"archive": str(output.resolve()), "files": len(files), "bytes": output.stat().st_size,
            "sha256": sha256(output.read_bytes())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    stamp = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d-%H%M%S-%f")
    parser.add_argument("--output", type=Path, default=ROOT / "output/transfer" / f"ground-laptop-{stamp}.zip")
    args = parser.parse_args(argv)
    print(json.dumps(build(ROOT, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
