@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  FRAKTAL_TOR_EINSCHALTEN.bat   (14.09.2026)
REM
REM  Schaltet Svens Fraktal-Verfahren am Handelspfad scharf und setzt
REM  die dazugehoerige Epochengrenze.
REM
REM  Vorher gemessen:
REM    fraktal_rueckblick.py  4 von 4 Kaeufen des 14.09. abgelehnt
REM    fraktal_oeffnung.py    Tor in 27,2 % der Stunden offen (30 Tage)
REM    fraktal_tor_test.py    21 von 21 Pruefungen bestanden
REM
REM  Es wird NICHTS gestartet und NICHTS gehandelt. Von beiden
REM  geaenderten Dateien wird vorher eine Sicherung gelegt.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Fraktal-Tor scharf stellen

python fraktal_tor_einschalten.py

echo.
pause
