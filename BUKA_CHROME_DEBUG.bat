@echo off
setlocal
chcp 65001 >nul
title Buka Chrome Debug - Inventory Adjusment Tools
REM ============================================================
REM  BUKA CHROME DEBUG - SEKALI KLIK (tanpa buka aplikasi)
REM  Double-click file ini -> Chrome debugging langsung jalan
REM  dengan auto-port 9222-9225 + anti-throttle flags.
REM  Logika lengkap ada di chrome_debug.ps1 (harus satu folder).
REM ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0chrome_debug.ps1"
endlocal
