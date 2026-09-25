@echo off
setlocal
chcp 65001 >nul
title Download SJ GIS - Pemindahan Barang (v8.10)
color 0A
cls
echo ============================================================
echo   DOWNLOAD SJ GIS - PEMINDAHAN BARANG (v8.10)
echo ============================================================
echo  v8.10 — remove step 4.5 dump + 4.6 verify (focus shift fix for E_DOWNLOAD_ICON)
echo.
echo  Alur (berdasarkan recording manual user):
echo    search ^> klik cell ^> detail ^> btnCommentAttachment
echo    ^> dropdown ^> attachment panel ^> icon-download-2 ^> file
echo    ^> tutup overlay ^> tab Info Lainnya ^> extract Cabang + Tanggal ^> rename
echo.
echo  Prasyarat (PASTIKAN sebelum tekan ENTER):
echo   1. Chrome debugging SUDAH terbuka (port 9222)
echo   2. SUDAH login Accurate Online
echo   3. Halaman LIST Pemindahan Barang SUDAH terbuka
echo.
echo  Output: file PDF/XLS di folder Downloads (1 per kode).
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
echo  ^> Saat ditanya "Masukkan kode SJ", ketik 1 kode, ATAU
echo    multi-kode dipisah koma. Lalu ENTER.
echo    Contoh: IT.2026.09.19805
echo    Contoh: IT.2026.09.19805, IT.2026.09.20451, IT.2026.09.20447
echo.
python "%~dp0download_sj_gis.py"
if errorlevel 1 (
    echo.
    echo [GAGAL] Program berhenti karena error. Lihat pesan di atas.
)
pause
endlocal
