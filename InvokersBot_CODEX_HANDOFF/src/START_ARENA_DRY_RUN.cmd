@echo off
cd /d "%~dp0"
py arena_runner.py --dry-run %*
pause
