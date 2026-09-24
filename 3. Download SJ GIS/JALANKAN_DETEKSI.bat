@echo off
chcp 65001 >nul
title Deteksi SJ GIS (trial)
python -m pip install --quiet selenium 2>nul
python "%~dp0DETEKSI_HALAMAN.py"
pause
