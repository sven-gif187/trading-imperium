@echo off
REM ====================================================================
REM  V4_START.bat - startet den V4-Referenzbot
REM
REM  WARUM ES DIESE DATEI GIBT (28.08.2026)
REM  Der V4 war der einzige Dauerlaeufer OHNE Startdatei. Nach jedem
REM  Rechner-Neustart lief er einfach nicht mehr, und im Cockpit sah das
REM  aus wie ein "Ruecksetzer". Seine Daten waren nie verloren - es lief
REM  nur niemand, der sie fortschreibt.
REM
REM  V4 UND V6 KOENNEN SICH NICHT VERMISCHEN - geprueft am 28.08.:
REM    - alle 15 Dateipfade im V4 gehen ueber _SCRIPT_DIR, also seinen
REM      eigenen Ordner. Kein einziger Zugriff nach draussen.
REM    - er importiert kein einziges V6-Modul, nur Fremdbibliotheken.
REM    - Port 5000 (V4) gegen 5050 (V6).
REM
REM  DIE DOPPELSTART-SPERRE ist der wichtigste Teil dieser Datei.
REM  Zwei V4-Prozesse wuerden gleichzeitig dieselben JSON-Dateien
REM  schreiben - genau die Beschaedigung, die am 28.08. auftrat.
REM  Die erste Fassung benutzte "tasklist /v" und war WERTLOS: das
REM  zeigt nur den Fenstertitel, nicht den Skriptnamen. Jetzt wird die
REM  Befehlszeile durchsucht, in beide Richtungen getestet.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title V4-Referenzbot

echo.
echo  ============================================================
echo   V4-REFERENZBOT
echo  ============================================================
echo.
echo   Das ist NICHT der Hauptbot. Der V4 laeuft nebenher und
echo   liefert die Vergleichszahlen, an denen der V6 gemessen wird.
echo   Er schreibt ausschliesslich in seinen eigenen Ordner.
echo.

if not exist "v4_referenz\trading_imperium_v4_25_ALARM.py" (
   echo   FEHLER: v4_referenz\trading_imperium_v4_25_ALARM.py fehlt.
   echo.
   pause
   exit /b 1
)

echo   Pruefe, ob er schon laeuft...
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*trading_imperium_v4*' }) { exit 1 } else { exit 0 }"
if errorlevel 1 (
   echo.
   echo   ER LAEUFT BEREITS. Es wird NICHTS gestartet.
   echo.
   echo   Ein zweiter V4 wuerde dieselben Dateien gleichzeitig
   echo   beschreiben und sie beschaedigen.
   echo.
   pause
   exit /b 0
)

echo   Laeuft noch nicht - starte ihn.
cd /d "%~dp0v4_referenz"
start "V4-Referenzbot" python trading_imperium_v4_25_ALARM.py
cd /d "%~dp0"

echo.
echo   Gestartet. Es oeffnet sich ein eigenes Fenster.
echo   Dieses Fenster NICHT schliessen, solange er laufen soll.
echo.
echo   Nachsehen, ob er wirklich laeuft: SAMMLER_PRUEFEN.bat
echo  ============================================================
echo.
pause
