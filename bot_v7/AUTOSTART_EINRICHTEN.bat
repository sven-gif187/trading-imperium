@echo off
chcp 65001 > nul
setlocal
REM ====================================================================
REM  AUTOSTART_EINRICHTEN.bat   (16.09.2026)
REM
REM  Legt die geplante Aufgabe "SchattenUniversumLIVE" an. Sie ruft
REM  alle 15 Minuten schatten_starter.py auf - und der startet das
REM  Schatten-Universum NUR, wenn es gerade nicht laeuft.
REM
REM  WOZU
REM  Sven am 16.09.: "ist es aber nicht besser das er von selbst
REM  startet damit wir immer alle daten haben falls ich das jemals
REM  vergessen sollte". Genau dafuer.
REM
REM  WARUM ALLE 15 MINUTEN UND NICHT "BEIM HOCHFAHREN"
REM  Der Ausloeser "beim Hochfahren" braucht Adminrechte und scheitert
REM  hier an "Zugriff verweigert" - steht so in OFFEN.md Zeile 161.
REM  Der Ersatz laeuft seit dem 18.08. im Papier-Ordner. Die Luecke
REM  nach einem Neustart betraegt hoechstens eine Viertelstunde.
REM
REM  WICHTIG: Die vorhandene Aufgabe "SchattenUniversumWacht" zeigt auf
REM  den PAPIER-Ordner und bleibt unangetastet. Diese hier ist die
REM  zweite, fuer den Live-Ordner. Beide stoeren einander nicht - der
REM  Starter prueft seit dem 16.09. das Arbeitsverzeichnis und
REM  verwechselt die zwei Ordner nicht mehr.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Autostart fuer das Schatten-Universum einrichten

set "PYW=%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\pythonw.exe"
set "ZIEL=%~dp0schatten_starter.py"

echo.
echo ======================================================================
echo   AUTOSTART FUER DAS SCHATTEN-UNIVERSUM (LIVE-Ordner)
echo ======================================================================
echo.
echo   Aufgabe : SchattenUniversumLIVE
echo   Takt    : alle 15 Minuten
echo   Ruft auf: %ZIEL%
echo.
echo   Der Starter prueft, ob der Sammler laeuft, und startet ihn nur,
echo   wenn nicht. Er kann keinen zweiten erzeugen.
echo.

if not exist "%PYW%" (
  echo   FEHLER: pythonw nicht gefunden unter
  echo   %PYW%
  echo.
  echo   Ohne pythonw wuerde bei jedem Lauf ein Konsolenfenster
  echo   aufpoppen. Bitte den Pfad pruefen.
  echo.
  pause
  exit /b 1
)

if not exist "%ZIEL%" (
  echo   FEHLER: schatten_starter.py nicht gefunden.
  echo.
  pause
  exit /b 1
)

echo   Lege die Aufgabe an...
echo.
schtasks /create /tn "SchattenUniversumLIVE" /tr "\"%PYW%\" \"%ZIEL%\"" /sc minute /mo 15 /f

if errorlevel 1 (
  echo.
  echo   ANLEGEN FEHLGESCHLAGEN.
  echo   Haeufigste Ursache: fehlende Rechte. Dann diese Datei mit
  echo   Rechtsklick und "Als Administrator ausfuehren" starten.
) else (
  echo.
  echo   ANGELEGT. Zur Gegenprobe der aktuelle Stand:
  echo.
  schtasks /query /tn "SchattenUniversumLIVE" /fo LIST
  echo.
  echo   Einmal sofort ausfuehren, damit es nicht bis zum naechsten
  echo   Viertelstundentakt dauert:
  schtasks /run /tn "SchattenUniversumLIVE"
)

echo.
echo ======================================================================
echo   Entfernen liesse sich die Aufgabe spaeter so:
echo     schtasks /delete /tn "SchattenUniversumLIVE" /f
echo ======================================================================
echo.
pause
