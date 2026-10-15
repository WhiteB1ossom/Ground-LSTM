@echo off
setlocal
pushd "%~dp0"
py -3.12 -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 goto launcher
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" goto localpython
python -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')==8 else 1)" >nul 2>&1
if not errorlevel 1 goto pathpython
echo Python 3.12 x64 is required. Ask laptop Codex to read LAPTOP_CODEX_HANDOFF.md.
set "setup_result=1"
goto finish
:launcher
py -3.12 -m scripts.setup_laptop %*
set "setup_result=%errorlevel%"
goto finish
:localpython
"%LocalAppData%\Programs\Python\Python312\python.exe" -m scripts.setup_laptop %*
set "setup_result=%errorlevel%"
goto finish
:pathpython
python -m scripts.setup_laptop %*
set "setup_result=%errorlevel%"
:finish
popd
if "%~1"=="" pause
exit /b %setup_result%
