@echo off
setlocal
chcp 65001 >nul
title Filter Pembuat Data - Accurate Online
color 0B
cls
echo ============================================================
echo        FILTER PEMBUAT DATA - ACCURATE ONLINE
echo ============================================================
echo.
echo [1/2] Memeriksa dependency...
python -m pip install selenium --quiet
echo [2/2] Membuka Chrome dengan Remote Debugging...
start "" chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile" "https://accurate.id"
echo.
echo  1. Login ke Accurate Online di Chrome yang terbuka.
echo  2. Buka LIST Penyesuaian Persediaan (halaman dengan tabel).
echo  3. Tekan tombol apa saja untuk menjalankan filter.
echo.
pause >nul
python "%~dp0filter_pembuat_data.py"
if errorlevel 1 (
    echo.
    echo Program berhenti karena error.
    pause
)
endlocal