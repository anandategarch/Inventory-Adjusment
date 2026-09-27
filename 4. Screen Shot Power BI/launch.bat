@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Power BI Screenshot Tool - Setup

set "LOG=%CD%\setup.log"
echo ================================================== > "%LOG%"
echo Power BI Screenshot Tool - Setup Log >> "%LOG%"
echo Started: %date% %time% >> "%LOG%"
echo Folder: %CD% >> "%LOG%"
echo ================================================== >> "%LOG%"

echo.
echo Folder:
echo %CD%
echo.

set "PY="

where py.exe >nul 2>&1
if not errorlevel 1 (
    py -3.13 --version >nul 2>&1
    if not errorlevel 1 set "PY=py -3.13"
)

if not defined PY if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python313-64\python.exe" set "PY=%LocalAppData%\Programs\Python\Python313-64\python.exe"

if not defined PY (
    where python.exe >nul 2>&1
    if not errorlevel 1 (
        python --version 2>nul | findstr /b /c:"Python 3.13" >nul
        if not errorlevel 1 set "PY=python"
    )
)

if not defined PY goto NO_PYTHON

echo [1/4] Python:
%PY% --version
%PY% --version >> "%LOG%" 2>&1

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [2/4] Membuat virtual environment lokal...
    %PY% -m venv .venv >> "%LOG%" 2>&1
    if errorlevel 1 goto FAIL_VENV
) else (
    echo.
    echo [2/4] Virtual environment sudah ada.
)

set "VPY=%CD%\.venv\Scripts\python.exe"

echo.
echo [3/4] Memasang Playwright secara lokal...
"%VPY%" -m pip install --disable-pip-version-check --quiet --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 goto FAIL_PIP
"%VPY%" -m pip install --disable-pip-version-check --quiet -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto FAIL_PIP

echo.
echo [4/4] Memasang Chromium Playwright...
echo First run dapat membutuhkan beberapa menit.
"%VPY%" -m playwright install chromium >> "%LOG%" 2>&1
if errorlevel 1 goto FAIL_CHROMIUM

echo.
echo ==================================================
echo   SETUP BERHASIL
echo   Menjalankan aplikasi...
echo ==================================================
echo.

"%VPY%" app.py >> "%LOG%" 2>&1
if errorlevel 1 goto FAIL_APP

echo.
echo Aplikasi ditutup.
pause
exit /b 0

:NO_PYTHON
echo.
echo Python 3.13 tidak ditemukan untuk user saat ini.
echo Install Python 3.13 x64 lalu coba START_HERE.vbs lagi.
echo.
echo Detail ada di setup.log
pause
exit /b 1

:FAIL_VENV
echo.
echo Gagal membuat .venv. Detail ada di setup.log
pause
exit /b 1

:FAIL_PIP
echo.
echo Gagal memasang Playwright. Detail ada di setup.log
pause
exit /b 1

:FAIL_CHROMIUM
echo.
echo Gagal memasang Chromium. Detail ada di setup.log
pause
exit /b 1

:FAIL_APP
echo.
echo Aplikasi berhenti dengan error. Detail ada di setup.log
pause
exit /b 1
