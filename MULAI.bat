@echo off
setlocal
chcp 65001 >nul
title Inventory Adjusment Tools - Unified UI
color 0A
cls
echo ============================================================
echo   INVENTORY ADJUSEMENT TOOLS - UNIFIED UI
echo ============================================================
echo.
echo  Membuka aplikasi dengan 5 tab:
echo    1. Otomasi (Import IA)
echo    2. Database COA ^& Keterangan
echo    3. Download Draft IA
echo    4. Download SJ GIS
echo    5. Screen Shot Power BI
echo.
echo  Pastikan SETUP.bat sudah dijalankan minimal sekali.
echo.
echo  Tekan ENTER untuk membuka UI...
pause >nul

cd /d "%~dp02. Import IA"
python ui_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] Gagal menjalankan UI. Pastikan:
    echo   - Python terinstall (python --version)
    echo   - SETUP.bat sudah dijalankan (install dependencies)
    pause
)
endlocal
