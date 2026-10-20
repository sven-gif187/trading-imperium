@echo off
REM ============================================================
REM  VOLLSTAENDIGKEIT PRUEFEN  -  einfach doppelklicken
REM ============================================================
REM  [21.08.2026] Sven: "helfe mir doch bitte einfach das so
REM  aufzustellen damit wir dann alles haben!"
REM
REM  Beantwortet VOR dem Stichtag, was sonst erst AM Stichtag
REM  auffiel: fehlt uns etwas, und reicht das Tempo?
REM
REM  Fasst nichts an. Liest nur. Kann waehrend des Freeze
REM  jederzeit laufen.
REM
REM  Der Ordnername enthaelt Klammern - "%~dp0" faengt das ab.
REM  Ohne Anfuehrungszeichen bricht cmd genau daran ab.
REM ============================================================
cd /d "%~dp0"
python vollstaendigkeit.py
echo.
echo ============================================================
pause
