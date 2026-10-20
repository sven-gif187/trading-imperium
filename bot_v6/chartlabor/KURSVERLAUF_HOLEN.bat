@echo off
chcp 65001 > nul
REM ============================================================
REM  KURSVERLAUF HOLEN  -  einfach doppelklicken
REM ============================================================
REM  Holt den kompletten Bitcoin-Verlauf von Binance (oeffentlich,
REM  kein Zugangsschluessel noetig) und legt ihn unter daten/ ab.
REM
REM  Reine Datenbeschaffung. Es wird NICHTS am Bot und NICHTS in
REM  data_store veraendert - das Messfenster bleibt unberuehrt.
REM
REM  Beim ersten Mal dauert es ein bis zwei Minuten.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
call "%~dp0..\_python_finden.bat"
if errorlevel 1 goto keinpython
"%PY%" chartlabor_daten.py
echo.
echo    Fertig. Jetzt CHARTLABOR.bat doppelklicken.
goto ende
:keinpython
echo.
echo [FEHLER] Kein Python 3.13 gefunden.
:ende
echo.
pause
