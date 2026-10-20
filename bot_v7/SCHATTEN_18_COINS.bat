@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  SCHATTEN_18_COINS.bat   (15.09.2026)
REM
REM  Misst das Einstiegssignal UND das Fraktal-Tor auf 18 Muenzen -
REM  ohne zu handeln. Laeuft stuendlich weiter, bis das Fenster
REM  geschlossen wird.
REM
REM  WOZU
REM  Der Bot handelt drei Muenzen. Bis 100 Verkaeufe zusammenkommen
REM  (Freigabe-Kriterium A), vergehen Monate. Dieses Programm sammelt
REM  auf 18 Muenzen stuendlich Beobachtungen - nach zwei Wochen liegen
REM  Tausende vor statt vierzig.
REM
REM  Seit dem 15.09. misst es AUCH das Fraktal-Tor mit: zu jedem Signal
REM  steht daneben, ob das Tor den Kauf erlaubt haette, in welcher
REM  Konfluenzzone, und wo die Fibonacci-Ziele lagen.
REM
REM  WICHTIG: Das Tor filtert hier NICHTS. Es urteilt nur. Beide
REM  Gruppen - erlaubt und abgelehnt - landen in der Datenbank, denn
REM  ohne die abgelehnten laesst sich nicht pruefen, ob die Ablehnung
REM  richtig war.
REM
REM  Es handelt NICHT, fasst den Bot NICHT an und schreibt in eine
REM  eigene Datenbank (data_store/schatten_universum.db). Der
REM  Live-Bot darf ungestoert weiterlaufen.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Schatten-Universum - 18 Muenzen mit Fraktal-Tor

echo.
echo ======================================================================
echo   SCHATTEN-UNIVERSUM - 18 Muenzen, stuendlich
echo ======================================================================
echo.
echo   Misst mit, handelt nicht. Eigene Datenbank.
echo   Der Live-Bot wird nicht angefasst.
echo.
echo   Beenden: dieses Fenster schliessen oder Strg+C
echo.

python schatten_universum.py --dauer

echo.
echo   Beendet.
pause
