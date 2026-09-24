@echo off
setlocal
chcp 65001 >nul
title Download SJ GIS - Pemindahan Barang (TRIAL)
color 0A
cls
echo ============================================================
echo   DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v1 TRIAL)
echo ============================================================
echo.
echo  Tool ini: search kode -> klik baris -> cetak -> unduh SJ.
echo.
echo  Prasyarat:
echo   - Chrome debugging terbuka (port 9222) & sudah login Accurate
echo   - Halaman LIST Pemindahan Barang sedang terbuka
echo.
echo  Output: file PDF/XLS tersimpan di folder Downloads.
echo.
echo  Tekan tombol apa saja untuk mulai...
pause >nul

echo.
echo [1/2] Memeriksa dependency Python (selenium)...
python -m pip install --quiet --disable-pip-version-check --no-input selenium >nul 2>&1
if errorlevel 1 (
    echo [GAGAL] Dependency tidak terpasang. Periksa instalasi Python Anda.
    pause
    exit /b 1
)
echo [2/2] Menjalankan tool...
echo.
python "%~dp0download_sj_gis.py"
if errorlevel 1 (
    echo.
    echo [GAGAL] Program berhenti karena error. Lihat pesan di atas.
    pause
)
endlocal
