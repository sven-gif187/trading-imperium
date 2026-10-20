@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  FRAKTAL_VERVOLLSTAENDIGEN.bat   (15.09.2026)
REM
REM  Die zweite Haelfte von Svens Verfahren: Ausstieg an den
REM  Fibonacci-Zielen der Kaufwelle statt an festen Prozentmarken.
REM  Dazu wird der Regime-Filter abgeschaltet, der seit dem 15.09.
REM  jeden Kauf blockte, den das Fraktal-Tor erlaubt hatte.
REM
REM  Der Ausstieg selbst steckt schon im Programmtext und braucht
REM  keinen Schalter. Dieses Skript aendert nur den Regime-Filter und
REM  setzt die Epochengrenze L3.
REM
REM  Vorher gemessen: 36 von 36 Pruefungen bestanden, Fibonacci-Ziele
REM  gegen eine Handrechnung geprueft (fraktal_tor_test.py).
REM
REM  WICHTIG: Danach den Bot NEU STARTEN - der laufende hat den alten
REM  Programmtext geladen.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Fraktal-System vervollstaendigen

python fraktal_vervollstaendigen.py

echo.
pause
