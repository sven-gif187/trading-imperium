@echo off
chcp 65001 > nul
REM ============================================================
REM  ONEDRIVE-PRUEFUNG  -  einfach doppelklicken
REM ============================================================
REM  Prueft, ob OneDrive wieder auf den Projektordner zugreift.
REM  Hintergrund steht oben in onedrive_wacht.py.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
call "%~dp0_python_finden.bat"
if errorlevel 1 goto keinpython
"%PY%" onedrive_wacht.py
goto ende
:keinpython
echo.
echo [FEHLER] Kein Python 3.13 gefunden.
:ende
echo.
pause
