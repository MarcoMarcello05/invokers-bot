@echo off
cd /d "%~dp0"
py -m pip install rapidocr_onnxruntime opencv-python pyautogui numpy >nul 2>nul
py arena_runner.py --once
pause
