@echo off
title SiPENDEKAR Background Scheduler
cd /d "%~dp0"
python bot.py --daemon
pause
