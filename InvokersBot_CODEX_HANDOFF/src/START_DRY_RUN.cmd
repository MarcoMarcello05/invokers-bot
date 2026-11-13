@echo off
cd /d "%~dp0"
py -m pip install brotli >nul 2>nul
py autonomy_bridge.py
pause
