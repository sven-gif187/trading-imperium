@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  FRAKTAL_PRUEFEN.bat  -  alles zum Fraktal-Tor am Stueck
REM
REM  WARUM ES DIESE DATEI GIBT (14.09.2026)
REM  Am 14.09. stellte sich heraus, dass Svens Fraktal-Verfahren gar
REM  nicht am Handel haengt: features/fraktal_konfluenz.py wurde von
REM  keinem Handelspfad importiert. Der Bot kaufte nach Trendfolge -
REM  also NACH dem Anstieg - und damit am Hoch.
REM
REM  Diese Datei startet die vier Pruefungen dazu:
REM    1. Was liegt wirklich auf dem Konto (bestand_pruefen.py)
REM    2. Tut das Tor, was es soll (fraktal_tor_test.py)
REM    3. Haette es die Kaeufe vom 14.09. verhindert (fraktal_rueckblick.py)
REM    4. Geht es ueberhaupt jemals auf (fraktal_oeffnung.py)
REM
REM  Pruefung 4 ist die wichtigste Gegenprobe: Ein Tor, das JEDEN Kauf
REM  ablehnt, besteht Pruefung 3 muehelos und ist trotzdem wertlos.
REM
REM  Sie aendert NICHTS und handelt NICHT. Der Bot darf laufen.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Fraktal-Tor pruefen

echo.
echo ======================================================================
echo   FRAKTAL-TOR - DREI PRUEFUNGEN
echo ======================================================================
echo.
echo   Nichts hiervon handelt oder aendert etwas. Reines Lesen.
echo.

set FEHLER=0

echo ----------------------------------------------------------------------
echo   1 von 4   Was liegt wirklich auf dem Bybit-Konto?
echo ----------------------------------------------------------------------
python bestand_pruefen.py
if errorlevel 1 set /a FEHLER+=1
echo.

echo ----------------------------------------------------------------------
echo   2 von 4   Tut das Tor, was es soll? (beide Richtungen)
echo ----------------------------------------------------------------------
python fraktal_tor_test.py
if errorlevel 1 set /a FEHLER+=1
echo.

echo ----------------------------------------------------------------------
echo   3 von 4   Haette es die Kaeufe vom 14.09. verhindert?
echo ----------------------------------------------------------------------
echo   (holt echte Kerzen von Binance - dauert etwa eine Minute)
python fraktal_rueckblick.py
if errorlevel 1 set /a FEHLER+=1
echo.

echo ----------------------------------------------------------------------
echo   4 von 4   Geht das Tor ueberhaupt jemals auf?
echo ----------------------------------------------------------------------
echo   (30 Tage, Stunde fuer Stunde - dauert einige Minuten)
python fraktal_oeffnung.py
if errorlevel 1 set /a FEHLER+=1
echo.

echo ======================================================================
if %FEHLER%==0 (
  echo   ALLE PRUEFUNGEN DURCH.
) else (
  echo   %FEHLER% PRUEFUNG^(EN^) MIT FEHLER - bitte oben nachlesen.
)
echo ======================================================================
echo.
pause
