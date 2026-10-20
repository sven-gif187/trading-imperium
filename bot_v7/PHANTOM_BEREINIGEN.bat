@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  PHANTOM_BEREINIGEN.bat   (15.09.2026)
REM
REM  Raeumt Positionen auf, die verkauft wurden, aber im Register des
REM  Bots stehengeblieben sind.
REM
REM  ANLASS: Am 15.09. um 14:23 verkaufte der Bot 0,0041 ETH fuer
REM  9,99 Dollar - erfolgreich. Eine Sekunde spaeter meldete er
REM  "Order NICHT gefuellt", weil die Boerse die Ausfuehrung in der
REM  Handelshistorie noch nicht zeigte. Die Position blieb im
REM  Register, der Stop-Loss loeste zwei Stunden lang alle 30 Sekunden
REM  aus, und die Buchhaltung wies 27 Prozent Gewinn aus, den es nicht
REM  gab.
REM
REM  DER BOT MUSS DABEI AUS SEIN. Er haelt die Positionen im
REM  Arbeitsspeicher; eine Aenderung an der Datei waere beim naechsten
REM  Speichern wieder weg (Befund 97). Das Werkzeug prueft das selbst
REM  und bricht ab, wenn der Bot laeuft.
REM
REM  Es fragt vor jeder Aenderung nach und legt Sicherungen an.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Phantom-Positionen bereinigen

python phantom_position_bereinigen.py

echo.
pause
