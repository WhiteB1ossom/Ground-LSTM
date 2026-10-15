"""Transfer integrity and bootstrap failure behavior, without installing packages."""

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import zipfile

import pytest

from scripts import package_laptop as package
from scripts import setup_laptop as bootstrap


@pytest.mark.parametrize("system,version,bits,machine", [("Linux", (3, 12), 64, "x86_64"),
    ("Windows", (3, 14), 64, "AMD64"), ("Windows", (3, 12), 32, "AMD64"),
    ("Windows", (3, 12), 64, "ARM64")])
def test_bootstrap_rejects_unverified_python_targets(system, version, bits, machine):
    with pytest.raises(RuntimeError, match="Python 3.12"):
        bootstrap.check_python(system, version, bits, machine)


def test_bootstrap_accepts_windows_x64_python312():
    bootstrap.check_python("Windows", (3, 12, 10), 64, "AMD64")


@pytest.mark.parametrize("name", ["../outside", "/absolute", "C:/outside", "sub\\outside"])
def test_transfer_rejects_paths_outside_its_root(tmp_path, name):
    with pytest.raises(ValueError):
        package.contained(tmp_path, name)


def test_manifest_detects_changed_and_missing_files(tmp_path):
    payload = b"verified code"
    file = tmp_path / "code.py"
    file.write_bytes(payload)
    (tmp_path / package.MANIFEST).write_text(json.dumps({"schema_version": 1, "files": {"code.py": package.sha256(payload)}}))
    assert package.verify_transfer(tmp_path) == 1
    file.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        package.verify_transfer(tmp_path)
    file.unlink()
    with pytest.raises(ValueError, match="Missing"):
        package.verify_transfer(tmp_path)


def test_zip_contains_models_and_test_input_without_environments_or_history(tmp_path):
    root = tmp_path / "source"
    def write(name):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    for name in package.ROOT_FILES:
        write(name)
    for name in ("src/realtime/demo.html", "src/__pycache__/ignored.pyc", ".venv-ml/ignored", "artifacts/old/ignored.log"):
        write(name)
    write(package.RUN / "server-models.json")
    write(package.RUN / "recipe/preprocessing.yaml")
    for task in ("degradation", "surge"):
        write(package.RUN / task / "replay-selected.yaml")
        for name in ("bundle.json", "best_model.keras", "scaler.json", "dataset-manifest.json"):
            write(package.RUN / task / "bundle" / name)
    for name in ("heldout.synthetic.csv", "scenarios.json", "observations.synthetic.csv"):
        write(package.RAW / name)
    output = tmp_path / "transfer.zip"
    report = package.build(root, output)
    assert report["bytes"] > 0
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert any(n.endswith("best_model.keras") for n in names)
        assert not any(".venv" in n or "__pycache__" in n or "ignored.log" in n or n.endswith("/observations.synthetic.csv") for n in names)
        archive.extractall(tmp_path / "extracted")
    assert package.verify_transfer(tmp_path / "extracted" / package.TOP) == report["files"]
    with pytest.raises(FileExistsError):
        package.build(root, output)


def bootstrap_root(tmp_path):
    for name in ("pyproject.toml", "requirements-integration-lock.txt", "src/realtime/demo.html",
                 package.RUN / "server-models.json", package.RAW / "heldout.synthetic.csv",
                 ".venv-ml/Scripts/python.exe", ".venv-ml/pyvenv.cfg"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    return tmp_path


def install_probe(monkeypatch, root, calls, *, pip_fails=False):
    monkeypatch.setattr(bootstrap, "check_python", lambda *_args: None)
    def invoke(arguments, **_kwargs):
        calls.append(arguments)
        if "-c" in arguments:
            return SimpleNamespace(stdout=json.dumps({"version": [3, 12], "bits": 64,
                                                       "prefix": str(root / ".venv-ml"), "base": str(root / "base-python")}))
        if pip_fails and "install" in arguments:
            raise subprocess.CalledProcessError(1, arguments)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(bootstrap.subprocess, "run", invoke)


def test_setup_installs_only_inside_local_environment_then_verifies(monkeypatch, tmp_path):
    root, calls = bootstrap_root(tmp_path), []
    install_probe(monkeypatch, root, calls)
    bootstrap.setup(root)
    assert all(Path(c[0]) == root / ".venv-ml/Scripts/python.exe" for c in calls)
    assert any("requirements-integration-lock.txt" in c and "--only-binary=:all:" in c for c in calls)
    assert calls[-2][-3:] == ["-m", "pip", "check"]
    assert calls[-1][-2:] == ["-m", "scripts.verify_laptop"]


def test_setup_stops_on_pip_failure_without_claiming_model_verification(monkeypatch, tmp_path):
    root, calls = bootstrap_root(tmp_path), []
    install_probe(monkeypatch, root, calls, pip_fails=True)
    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.setup(root)
    assert not any("scripts.verify_laptop" in c for c in calls)


def test_existing_environment_can_be_checked_without_installing(monkeypatch, tmp_path):
    root, calls = bootstrap_root(tmp_path), []
    install_probe(monkeypatch, root, calls)
    bootstrap.setup(root, skip_install=True)
    assert not any("install" in c for c in calls)
    assert calls[-1][-1] == "scripts.verify_laptop"


def test_broken_environment_is_preserved(monkeypatch, tmp_path):
    root = bootstrap_root(tmp_path)
    monkeypatch.setattr(bootstrap, "check_python", lambda *_args: None)
    (root / ".venv-ml/pyvenv.cfg").unlink()
    with pytest.raises(RuntimeError, match="incomplete"):
        bootstrap.setup(root)
    assert (root / ".venv-ml/Scripts/python.exe").is_file()
