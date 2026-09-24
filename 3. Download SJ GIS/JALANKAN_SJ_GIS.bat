@echo off
setlocal
chcp 65001 >nul
title Download SJ GIS - Pemindahan Barang (TRIAL v3)
color 0A
cls
echo ============================================================
echo   DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v3 TRIAL)
echo ============================================================
echo.
echo  Alur: search kode ^> klik baris ^> buka detail ^> klik tombol
echo  "Dokumen/Komentar" ^> cari link download SJ ^> unduh file.
echo.
echo  Prasyarat (PASTIKAN sebelum tekan ENTER):
echo   1. Chrome debugging SUDAH terbuka (port 9222)
echo   2. SUDAH login Accurate Online
echo   3. Halaman LIST Pemindahan Barang SUDAH terbuka
echo.
echo  Output: file PDF/XLS tersimpan di folder Downloads.
echo.
echo  ----------------------------------------------------------
echo  Tekan ENTER untuk mulai...
echo  ----------------------------------------------------------
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
echo  ^> Saat ditanya "Masukkan kode SJ", TEKAN ENTER saja buat pakai
echo    default IT.2026.09.19805, atau ketik kode lain lalu ENTER.
echo.
python "%~dp0download_sj_gis.py"
if errorlevel 1 (
    echo.
    echo [GAGAL] Program berhenti karena error. Lihat pesan di atas.
)
pause
endlocal
