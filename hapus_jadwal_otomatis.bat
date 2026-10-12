@echo off
title Hapus Jadwal Otomatis SiPENDEKAR
cd /d "%~dp0"
echo =============================================================
echo   MENGHAPUS JADWAL AUTO-ISI SiPENDEKAR DARI WINDOWS
echo =============================================================
echo.
python bot.py --remove-task
echo.
pause
