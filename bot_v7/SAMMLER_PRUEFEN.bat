@echo off
REM ============================================================
REM  SAMMLER PRUEFEN  -  einfach doppelklicken
REM ============================================================
REM  [20.08.2026] Sven: "das mit den ganzen Befehlen wird mir echt
REM  viel und bringt mich durcheinander."
REM
REM  Diese Datei ersetzt den Befehl. Doppelklick genuegt.
REM  Sie zeigt fuer jeden Sammler: laeuft er, schreibt er, gibt es
REM  Luecken, fehlen Pflichtfelder.
REM
REM  Der Ordnername enthaelt Klammern - "%~dp0" faengt das ab.
REM  Ohne Anfuehrungszeichen bricht cmd genau daran ab.
REM ============================================================
cd /d "%~dp0"
python sammler_pruefen.py
echo.
echo ============================================================
pause
