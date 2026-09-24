@echo off
setlocal
chcp 65001 >nul
title FULL PIPELINE - Filter + Unduh XLS
color 0A
cls
echo ============================================================
echo   FULL PIPELINE: FILTER PEMBUAT DATA -^> UNDUH XLS PER BARIS
echo ============================================================
echo.
echo   TAHAP 1 : Filter Pembuat Data (PWKTAM, KWGGAL)
echo   TAHAP 2 : Loop unduh XLS per transaksi
echo.
echo   Prasyarat:
echo    - Chrome debugging terbuka & sudah login Accurate
echo    - Halaman list Penyesuaian Persediaan sedang terbuka
echo.
echo   Tekan tombol apa saja untuk mulai...
pause >nul

echo.
echo ============================================================
echo   TAHAP 1/2 : FILTER PEMBUAT DATA...
echo ============================================================
python "%~dp0filter_pembuat_data.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Tahap 1 gagal. Pipeline dihentikan.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   TAHAP 2/2 : LOOP UNDUH XLS PER TRANSAKSI...
echo ============================================================
python "%~dp0unduh_xls_loop.py"
if errorlevel 1 (
    echo.
    echo [ERROR] Tahap 2 gagal.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   PIPELINE SELESAI.
echo ============================================================
pause
endlocal