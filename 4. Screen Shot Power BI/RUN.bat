@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    call launch.bat
    exit /b %errorlevel%
)

".venv\Scripts\python.exe" app.py
if errorlevel 1 (
    echo.
    echo Aplikasi berhenti dengan error.
    echo Detail ada di setup.log
    pause
)
