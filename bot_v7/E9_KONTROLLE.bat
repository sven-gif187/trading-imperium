@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  E9_KONTROLLE.bat  -  ist die neue Epoche wirklich scharf?
REM
REM  WARUM ES DIESE DATEI GIBT (12.09.2026)
REM  Am 12.09. wurden fuenf Aenderungen gleichzeitig scharf gestellt und
REM  EINE Epochengrenze E9 gesetzt. Quelltext und Schalter liest der Bot
REM  aber nur BEIM START. Ohne Neustart laeuft alles Alte weiter - und
REM  die Epochengrenze steht trotzdem schon in der Datei. Dann waeren
REM  Trades unter alten Regeln in der neuen Epoche gezaehlt.
REM
REM  Diese Datei beantwortet genau eine Frage: Laeuft der Bot mit dem
REM  neuen Stand, oder muss er noch neu gestartet werden?
REM
REM  Sie startet und stoppt NICHTS - das bleibt Svens Entscheidung
REM  (Bestandsschutz, CLAUDE.md 4).
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title E9 - Kontrolle

cls
echo.
echo  ============================================================
echo   EPOCHE E9  -  laeuft der Bot schon mit dem neuen Stand?
echo  ============================================================
echo.

python e9_kontrolle.py

echo.
pause
