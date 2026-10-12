@echo off
title Pasang Jadwal Otomatis SiPENDEKAR (Jam 17:00 Sore)
cd /d "%~dp0"
echo =============================================================
echo   MEMASANG JADWAL AUTO-ISI SiPENDEKAR SETIAP JAM 17:00 SORE
echo =============================================================
echo.
python bot.py --install-task
echo.
pause
