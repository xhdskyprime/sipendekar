@echo off
title SiPENDEKAR Web Dashboard
cd /d "%~dp0"
echo Menjalankan SiPENDEKAR Web Dashboard...
echo Silakan buka browser di: http://127.0.0.1:5000
start http://127.0.0.1:5000
python web_dashboard.py
pause
