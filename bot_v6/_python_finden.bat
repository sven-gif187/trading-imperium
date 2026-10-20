@echo off
REM ============================================================
REM  _python_finden.bat - setzt %PY% und %PYW% auf das Python
REM  3.13 dieses Rechners. Wird von den anderen .bat per "call"
REM  eingebunden.   [UMZUG 01.09.2026]
REM ============================================================
REM  WARUM EINE EIGENE DATEI
REM  Diese Suche stand vorher in fuenf Dateien nebeneinander.
REM  Fuenf Kopien laufen auseinander - und dann sucht die geplante
REM  Aufgabe woanders als die Pruefdatei, ohne dass es auffaellt.
REM
REM  WARUM NICHT EINFACH "python"
REM  Auf diesem Rechner laeuft der Python-Verwalter (Python
REM  Install Manager). "python" im Suchpfad ist dessen Weiche
REM  unter WindowsApps - eine Indirektion mehr. Geplante Aufgaben
REM  starten ohne volle Benutzerumgebung; genau dort scheitern
REM  Weichen still. Deshalb der aufgeloeste, absolute Pfad.
REM
REM  GEMESSEN am 01.09.2026:
REM    %LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe
REM    -> Python 3.13.15   (Quellrechner: 3.13.14, gleiches cp313)
REM
REM  SETZT:  PY   python.exe   - mit Konsolenfenster
REM          PYW  pythonw.exe  - ohne Fenster, fuer Hintergrundjobs
REM  RUECKGABE: 0 = gefunden und geprueft
REM             1 = nichts gefunden
REM             2 = gefunden, aber es ist nicht 3.13
REM
REM  Kein "setlocal" - die Variablen muessen beim Aufrufer ankommen.
REM ============================================================
set "PY="
set "PYW="

REM 1) Der gemessene Interpreter dieses Rechners.
if exist "%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe" set "PY=%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe"

REM 2) Andere 3.13-Laufzeit des Verwalters, falls der Ordner mal anders heisst.
if not defined PY for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-3.13*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"

REM 3) Klassischer python.org-Installer, falls spaeter dazuinstalliert.
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%ProgramFiles%\Python313\python.exe" set "PY=%ProgramFiles%\Python313\python.exe"

REM 4) Weiche des Verwalters. Funktioniert, ist aber eine Indirektion
REM    mehr - nur als Rueckfall, nie als erste Wahl.
if not defined PY if exist "%LOCALAPPDATA%\Python\bin\python3.13.exe" set "PY=%LOCALAPPDATA%\Python\bin\python3.13.exe"

if not defined PY exit /b 1

REM Gegenprobe. "Die Datei existiert" ist kein Beleg dafuer, dass sie
REM startet - und schon gar nicht dafuer, dass es 3.13 ist.
"%PY%" -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,13) else 1)" >nul 2>&1
if errorlevel 1 exit /b 2

REM pythonw liegt daneben, gleicher Ordner.
for %%F in ("%PY%") do set "PYW=%%~dpFpythonw.exe"
if not exist "%PYW%" set "PYW=%PY%"
exit /b 0
