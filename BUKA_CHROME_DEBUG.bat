@echo off
setlocal EnableExtensions
title Buka Chrome Debug - Inventory Adjusment Tools
chcp 65001 >nul
REM ============================================================
REM  BUKA CHROME DEBUG v2 - SEKALI KLIK (STANDALONE, TANPA APLIKASI)
REM  Tidak butuh chrome_debug.ps1, tidak butuh Python, tidak butuh
REM  PowerShell script-file (aman dari blokir execution policy kantor).
REM  Flow: cek debug hidup -> cari chrome.exe -> bersihkan instance
REM  lama -> pilih port bebas 9222-9225 -> launch -> cek 30 detik.
REM ============================================================

set "CHROME="
set "PORT="
set "ALIVE_PORT="
set "CURL_OK=1"
where curl >nul 2>&1 || set "CURL_OK=0"

echo.
echo ============================================================
echo    BUKA CHROME DEBUG - Inventory Adjusment Tools (v2)
echo    Sekali klik - tanpa buka aplikasi MULAI.bat
echo ============================================================
echo.

REM ---------- 1) Chrome debug sudah hidup di 9222-9225? ----------
for %%P in (9222 9223 9224 9225) do call :probe %%P
if defined ALIVE_PORT goto :already

REM ---------- 2) Cari chrome.exe ----------
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined CHROME call :findpath
if not defined CHROME (
    echo [ERROR] chrome.exe TIDAK DITEMUKAN di lokasi standar:
    echo     C:\Program Files\Google\Chrome\Application\chrome.exe
    echo     C:\Program Files ^(x86^)\Google\Chrome\Application\chrome.exe
    echo     %LocalAppData%\Google\Chrome\Application\chrome.exe
    echo.
    echo Kalau Chrome terinstall di lokasi lain, buat shortcut manual:
    echo     chrome.exe --remote-debugging-port=9223 --user-data-dir="C:\ChromeDebugProfile"
    echo.
    pause
    exit /b 1
)
echo [INFO] Chrome ditemukan: %CHROME%

REM ---------- 3) Tutup Chrome debug lama yang menggantung ----------
REM (instance ChromeDebugProfile TANPA port debug - penyebab klasik
REM  "Chrome kebuka tapi port tidak pernah aktif". Chrome biasamu aman.)
echo [INFO] Bersihkan Chrome debug lama yang menggantung (kalau ada)...
wmic process where "name='chrome.exe' and CommandLine like '%%ChromeDebugProfile%%'" delete >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object {$_.CommandLine -like '*ChromeDebugProfile*'} | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}" >nul 2>&1
ping -n 2 127.0.0.1 >nul

REM ---------- 4) Pilih port BEBAS pertama (9222 -> 9225) ----------
for %%P in (9222 9223 9224 9225) do if not defined PORT call :freeport %%P
if not defined PORT (
    set "PORT=9222"
    echo [WARN] Semua port 9222-9225 dipakai proses lain - tetap coba 9222.
) else (
    echo [INFO] Port debug terpilih: %PORT%
)

REM ---------- 5) Launch Chrome (flags sama dengan UI v5.5) ----------
echo [INFO] Membuka Chrome... menunggu DevTools siap (maks 30 detik).
start "" "%CHROME%" --remote-debugging-port=%PORT% --user-data-dir=C:\ChromeDebugProfile --no-first-run --no-default-browser-check --hide-crash-restore-bubble --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding "https://accurate.id"

REM ---------- 6) Poll /json/version di port terpilih ----------
set /a TRIES=0
:waitloop
ping -n 2 127.0.0.1 >nul
set "ALIVE_PORT="
call :probe %PORT%
if defined ALIVE_PORT goto :success
set /a TRIES+=1
if %TRIES% lss 30 goto :waitloop
goto :fail

:success
echo.
echo [OK] Chrome debug HIDUP di port %PORT% - siap dipakai semua tool.
echo      Semua tool auto-detect port ini (scan 9222-9225).
set "SETTINGS=%~dp02. Import IA\ui_settings.json"
if exist "%SETTINGS%" powershell -NoProfile -Command "$p='%SETTINGS%';try{$j=Get-Content $p -Raw -Encoding UTF8|ConvertFrom-Json;$j|Add-Member -NotePropertyName sj_debug_port -NotePropertyValue %PORT% -Force;[IO.File]::WriteAllText($p,($j|ConvertTo-Json -Depth 5)+[char]10,(New-Object Text.UTF8Encoding($false)));exit 0}catch{exit 1}" >nul 2>&1 && echo [OK] Port %PORT% tersimpan di ui_settings.json - UI akan ikut port ini.
echo.
echo Login Accurate sekali di Chrome tersebut (session persist di
echo C:\ChromeDebugProfile). Jendela ini tutup otomatis 5 detik...
timeout /t 5 >nul
exit /b 0

:already
echo.
echo [OK] Chrome debug SUDAH aktif di port %ALIVE_PORT% - tidak diluncurkan ulang.
echo      Semua tool auto-detect port itu (scan 9222-9225). Aman dipakai.
echo Jendela ini tutup otomatis 5 detik...
timeout /t 5 >nul
exit /b 0

:fail
echo.
echo [FAIL] Chrome TIDAK menjawab http://127.0.0.1:%PORT%/json/version dalam 30 detik.
echo.
echo [DIAG] Yang listen di port %PORT% saat ini:
netstat -ano -p TCP | findstr /c:":%PORT% " | findstr /i "LISTENING"
echo.
echo   Solusi (1): tutup SEMUA Chrome (Task Manager -^> end task chrome.exe),
echo               lalu double-click shortcut ini lagi.
echo   Solusi (2): cek policy kantor yang bisa memblokir debugging (CMD):
echo       reg query HKLM\SOFTWARE\Policies\Google\Chrome /v DevToolsRemoteDebuggingAllowed
echo               Nilai 0 = diblokir IT/admin - hubungi IT.
echo   Solusi (3): cek manual di browser: http://127.0.0.1:%PORT%/json/version
echo               (harus muncul JSON berisi "Chrome/").
echo.
pause
exit /b 1

REM ---------- SUBROUTINE: probe DevTools di port %1 ----------
REM ALIVE_PORT ter-set kalau /json/version menjawab JSON berisi "Chrome/"
:probe
set "ALIVE_PORT="
if "%CURL_OK%"=="1" (
    curl -s -m 2 "http://127.0.0.1:%1/json/version" 2>nul | find /i "Chrome" >nul && set "ALIVE_PORT=%1"
) else (
    powershell -NoProfile -Command "try{if((Invoke-WebRequest -Uri 'http://127.0.0.1:%1/json/version' -TimeoutSec 2 -UseBasicParsing).Content -match 'Chrome/'){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1 && set "ALIVE_PORT=%1"
)
goto :eof

REM ---------- SUBROUTINE: port %1 bebas? kalau ya, set PORT ----------
:freeport
netstat -ano -p TCP | findstr /c:":%1 " | findstr /i "LISTENING" >nul && goto :eof
set "PORT=%1"
goto :eof

REM ---------- SUBROUTINE: cari chrome.exe di PATH ----------
:findpath
for /f "delims=" %%F in ('where chrome.exe 2^>nul') do (
    set "CHROME=%%F"
    goto :eof
)
goto :eof
