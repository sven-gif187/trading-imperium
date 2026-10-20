@echo off
REM ====================================================================
REM  WARTEAUFTRAEGE_PRUEFEN.bat  -  alle drei Pruefungen nacheinander
REM
REM  WARUM ES DIESE DATEI GIBT (11.09.2026)
REM  Die Warte-Auftraege (Limit-Orders) sind ein Zustandsspeicher IM
REM  Handelspfad - das gefaehrlichste Bauteil, das es hier gibt. Es
REM  merkt sich etwas ueber Neustarts hinweg, und wenn es dabei falsch
REM  aufraeumt, wird ein laengst verfallener Auftrag spaeter scharf.
REM
REM  Deshalb drei Pruefungen, jede in BEIDE Richtungen: sie muss
REM  schweigen, wenn alles stimmt, und den Fehler finden, wenn er da
REM  ist. Ein Test, der nur "ok" sagen kann, beweist nichts.
REM
REM  AENDERT NICHTS. Liest nur, rechnet nur, eigene Temp-Dateien.
REM  Laeuft auch bei laufendem Bot.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Warte-Auftraege pruefen

cls
echo.
echo  ============================================================
echo   WARTE-AUFTRAEGE  -  drei Pruefungen
echo  ============================================================
echo.
echo   1. Die Warteschlange allein      10 Punkte
echo   2. Durch die echte Maschine      11 Punkte
echo   3. Der Schalter                  steht er auf aus?
echo.
echo   Es wird nichts geaendert. Der Bot darf weiterlaufen.
echo.
echo  ------------------------------------------------------------
echo.
pause

echo.
echo  ============================================================
echo   1 von 3  -  DIE WARTESCHLANGE ALLEIN
echo  ============================================================
echo.
python warteauftrag_test.py
if errorlevel 1 goto fehler

echo.
echo  ============================================================
echo   2 von 3  -  DURCH DIE ECHTE MASCHINE
echo  ============================================================
echo.
python warteauftrag_maschine_test.py
if errorlevel 1 goto fehler

echo.
echo  ============================================================
echo   3 von 3  -  DER SCHALTER
echo  ============================================================
echo.
python -c "import json,io; d=json.load(io.open('data_store/config.json',encoding='utf-8')).get('warteauftraege',{}); print('   aktiv          ', d.get('aktiv')); print('   abstand_pct    ', d.get('abstand_pct'), '%%'); print('   gueltig_kerzen ', d.get('gueltig_kerzen'), '(=', int(d.get('gueltig_kerzen',0))*int(d.get('kerze_minuten',15)), 'Minuten)'); print(); print('   ACHTUNG: Der Schalter steht auf AN.' if d.get('aktiv') else '   Der Schalter steht auf AUS - der Bot kauft wie bisher sofort.')"

echo.
echo  ============================================================
echo   ALLE DREI DURCH
echo  ============================================================
echo.
echo   Zum Scharfschalten braucht es VORHER eine Epochengrenze E9
echo   in config_epochs.json. Ohne sie sind alle Vorher-Nachher-
echo   Vergleiche ueber die Grenze hinweg wertlos.
echo.
echo   Danach: data_store\config.json  ^-^>  warteauftraege.aktiv
echo   auf true, und den Bot neu starten.
echo.
goto ende

:fehler
echo.
echo  ============================================================
echo   DURCHGEFALLEN  -  nicht scharfschalten
echo  ============================================================
echo.
echo   Oben steht, welche Pruefung gefehlt hat. Der Schalter
echo   bleibt auf aus, bis das geklaert ist.
echo.

:ende
pause
