@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" call launch.bat
set "VPY=%CD%\.venv\Scripts\python.exe"
"%VPY%" -m pip install --quiet pyinstaller
"%VPY%" -m PyInstaller --noconfirm --clean --windowed --name PowerBIScreenshotTool app.py
pause
