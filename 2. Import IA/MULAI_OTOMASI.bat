@echo off
setlocal
chcp 65001 >nul
title Import IA - Accurate Online
color 0A
cls
echo [1/2] Memeriksa dependency Python...
python -m pip install --quiet --disable-pip-version-check --no-input selenium openpyxl xlrd >nul 2>&1
if errorlevel 1 (
    echo [GAGAL] Dependency tidak terpasang. Periksa instalasi Python Anda.
    pause
    exit /b 1
)
echo [2/2] Selesai. Proses lewat aplikasi!
start "" chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile" "https://accurate.id"
python "%~dp0main.py"
if errorlevel 1 (
    echo.
    echo [GAGAL] Aplikasi berhenti karena error.
    pause
)
endlocal