@echo off
cd /d "%~dp0"
echo ACHTUNG: Arena-Liveaktor. Maus oben links = Not-Aus.
echo Er greift nur Gegner unter eigener Kampfkraft an und nimmt den niedrigsten Wert.
echo Ohne passenden Gegner: max. 3x Aktualisieren, danach STOP.
pause
py arena_runner.py --live
pause
