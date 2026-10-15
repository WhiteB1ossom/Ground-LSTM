@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -no_logo -arch=x64
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /utf-8 decision_boundaries.cpp /Fe:decision_boundaries.exe
if errorlevel 1 exit /b 1
decision_boundaries.exe
