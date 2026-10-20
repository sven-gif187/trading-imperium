@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  LOG_SAEUBERN.bat   (15.09.2026)
REM
REM  Entfernt Testmeldungen aus data_store/system.log - erfundene
REM  Kaeufe auf TEST/USDC und RESTORE-Zeilen aus Attrappen-Faellen, die
REM  in der Nacht zum 15.09. von fraktal_tor_test.py hineingeschrieben
REM  wurden.
REM
REM  Die URSACHE ist behoben: core/logger.py liest jetzt TI_LOG_FILE,
REM  und fraktal_tor_test.py lenkt sein Log nach data_store/test.log um.
REM  Diese Datei raeumt nur noch Altes auf.
REM
REM  Der Bot darf dabei laufen. Vorher wird eine Sicherung gelegt, und
REM  am Ende prueft das Skript gegen, dass die ECHTE Bestandsuebernahme
REM  noch im Log steht.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Log saeubern

python log_saeubern.py

echo.
pause
