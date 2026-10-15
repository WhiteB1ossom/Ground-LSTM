@echo off
setlocal
pushd "%~dp0"
if not exist ".venv-ml\Scripts\python.exe" (
  echo Missing .venv-ml. See docs\windows-laptop-setup.md
  pause
  popd
  exit /b 1
)
".venv-ml\Scripts\python.exe" -m src.realtime.demo --open
if errorlevel 1 pause
popd
