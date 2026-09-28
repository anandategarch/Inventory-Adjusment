@echo off
setlocal
chcp 65001 >nul
title Inventory Adjusment Tools — SETUP (One-Time)
color 0B
cls
echo ============================================================
echo   SETUP — Install Dependencies (One-Time)
echo ============================================================
echo.
echo  Menginstall dependencies untuk semua tool:
echo    - selenium        (Tool 1, 2, 3 — Accurate Online automation)
echo    - openpyxl, xlrd  (Tool 2 — Excel handling)
echo    - playwright      (Tool 4 — Power BI screenshot)
echo    - Pillow          (Tool 4 — image processing)
echo    - Chromium browser (Tool 4 — Playwright browser)
echo.
echo  Tekan ENTER untuk mulai install...
pause >nul

echo.
echo [1/3] Install Python packages...
python -m pip install --upgrade pip
python -m pip install selenium openpyxl xlrd playwright Pillow
if errorlevel 1 (
    echo [ERROR] Gagal install Python packages. Cek instalasi Python Anda.
    pause
    exit /b 1
)

echo.
echo [2/3] Install Chromium browser for Playwright...
python -m playwright install chromium
if errorlevel 1 (
    echo [WARNING] Playwright chromium install gagal. Tool 4 mungkin tidak jalan.
    echo          Coba manual: python -m playwright install chromium
)

echo.
echo [3/3] Selesai!
echo  Sekarang jalankan MULAI.bat untuk membuka UI.
echo.
pause
endlocal
