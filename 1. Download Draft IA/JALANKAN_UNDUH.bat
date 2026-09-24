@echo off
setlocal
chcp 65001 >nul
title Unduh XLS Per Transaksi
color 0A
cls
echo ============================================================
echo        UNDUH XLS PER TRANSAKSI (LOOP)
echo ============================================================
echo.
echo  1. Pastikan Chrome debugging terbuka & list SUDAH terfilter
echo     (Pembuat Data: RESTO.PWKTAM, RESTO.KWGGAL).
echo  2. Tekan tombol apa saja untuk mulai.
echo.
pause >nul
python "%~dp0unduh_xls_loop.py"
if errorlevel 1 (
    echo.
    echo Program berhenti karena error.
    pause
)
endlocal