@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -no_logo -arch=x64
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc host_check.cpp model_data.cc /Fe:host_check.exe
if errorlevel 1 exit /b 1
host_check.exe
