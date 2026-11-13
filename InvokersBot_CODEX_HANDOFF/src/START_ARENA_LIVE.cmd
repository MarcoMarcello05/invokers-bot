@echo off
cd /d "%~dp0"
echo Live bleibt ohne explizite Aktivierung und frischen Preflight gesperrt.
py arena_runner.py --live %*
pause
