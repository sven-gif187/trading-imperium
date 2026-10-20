@echo off
chcp 65001 > nul
REM ============================================================
REM  CHARTLABOR  -  einfach doppelklicken
REM ============================================================
REM  Oeffnet den Kerzenchart mit den Zeichenwerkzeugen im Browser.
REM
REM  Der Bot wird dabei NICHT angefasst: eigener Prozess, eigener
REM  Port (8777, niemals 5050). Dieses Fenster haelt den kleinen
REM  Server - offen lassen, solange der Chart benutzt wird.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
call "%~dp0..\_python_finden.bat"
if errorlevel 1 goto keinpython
"%PY%" chartlabor_start.py
goto ende
:keinpython
echo.
echo [FEHLER] Kein Python 3.13 gefunden - erst EINRICHTUNG_0_PYTHON_313_HOLEN.bat.
echo.
pause
:ende
