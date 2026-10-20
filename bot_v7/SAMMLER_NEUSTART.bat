@echo off
REM ============================================================
REM  SAMMLER NEU STARTEN  -  einfach doppelklicken
REM ============================================================
REM  Nur noetig, wenn die Pruefung meldet:
REM     "laeuft - ABER mit altem Programmtext!"
REM
REM  Das passiert, wenn an einem Sammler etwas repariert wurde,
REM  waehrend er lief. Der Prozess kennt die Reparatur dann nicht -
REM  er laeuft weiter mit dem Stand von vorher und schreibt
REM  weiter falsche oder leere Werte.
REM
REM  Diese Datei beendet die Sammler und startet sie frisch.
REM  Sie fasst den Bot NICHT an.
REM ============================================================
cd /d "%~dp0"
python sammler_pruefen.py --neustart
echo.
echo ============================================================
pause
