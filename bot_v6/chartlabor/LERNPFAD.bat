@echo off
chcp 65001 > nul
REM ============================================================
REM  LERNPFAD PROGRAMMIEREN  -  einfach doppelklicken
REM ============================================================
REM  Acht Lektionen am eigenen Chartlabor. Jede hat ein
REM  Probierfeld, in dem echter Code laeuft - im Browser, ohne
REM  Server, ohne Claude. Tippen kostet hier nichts.
REM
REM  Startet denselben kleinen Server wie CHARTLABOR.bat und
REM  oeffnet nur eine andere Seite. Port 8777, niemals 5050.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
call "%~dp0..\_python_finden.bat"
if errorlevel 1 goto keinpython
"%PY%" chartlabor_start.py --lernpfad
goto ende
:keinpython
echo.
echo [FEHLER] Kein Python 3.13 gefunden.
echo.
pause
:ende
