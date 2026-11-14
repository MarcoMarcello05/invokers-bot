@echo off
cd /d "%~dp0"
python -m invokers_bot.app --config config\arena.json --mode dry
pause
