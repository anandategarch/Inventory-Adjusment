@echo off
chcp 65001 >nul
title Debug Filter Pembuat Data
cd /d "%~dp0"
python debug_filter.py
pause