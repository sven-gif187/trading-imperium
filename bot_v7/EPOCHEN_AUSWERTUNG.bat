@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  EPOCHEN_AUSWERTUNG.bat   (15.09.2026)
REM
REM  Teilt data_store/telemetrie.db nach den Epochen aus
REM  config_epochs.json auf - damit nie wieder zwei Epochen in einem
REM  Topf landen.
REM
REM  CLAUDE.md Abschnitt 5: "Jede Verhaltensaenderung braucht eine
REM  Epochengrenze, sonst sind alle Vorher-Nachher-Vergleiche wertlos."
REM  Die Grenzen gab es, die Messdaten auch - nur die Verbindung fehlte.
REM
REM  Das Gegenstueck fuer die JSON-Journale ist epoch_report.py.
REM  Beide benutzen dieselbe Quelle (epochs.py), damit es nie zwei
REM  Wahrheiten gibt.
REM
REM  Liest nur. Aendert nichts. Der Bot darf laufen.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Telemetrie nach Epochen

python epochen_auswertung.py

echo.
pause
