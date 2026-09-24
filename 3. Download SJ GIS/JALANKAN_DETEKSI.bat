@echo off
setlocal
chcp 65001 >nul
title Deteksi Halaman Pemindahan Barang (SJ GIS) - TRIAL
color 0E
cls
echo ============================================================
echo   DETEKSI HALAMAN - PEMINDAHAN BARANG (SJ GIS) - TRIAL
echo ============================================================
echo.
echo  Tool ini CUMA membaca struktur halaman + ketik kode + klik 1 baris.
echo  TIDAK melakukan download / simpan / hapus apapun. Aman.
echo.
echo  Prasyarat:
echo   - Chrome debugging terbuka (port 9222) & sudah login Accurate
echo   - Halaman LIST Pemindahan Barang sedang terbuka
echo.
echo  Output: cetak struktur halaman + simpan 2 file HTML.
echo  Kirim output + file HTML ke saya (Z.ai) supaya tool asli bisa ditulis.
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
echo [2/2] Menjalankan deteksi...
echo.
python "%~dp0DETEKSI_HALAMAN.py"
if errorlevel 1 (
    echo.
    echo [GAGAL] Program berhenti karena error. Lihat pesan di atas.
    pause
)
endlocal
