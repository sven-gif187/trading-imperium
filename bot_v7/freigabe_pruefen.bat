@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo.
echo   Freigabe-Pruefung Live-Betrieb
echo   (liest nur - aendert nichts, Bot darf laufen)
echo.
python go_live_check.py
echo.
pause
