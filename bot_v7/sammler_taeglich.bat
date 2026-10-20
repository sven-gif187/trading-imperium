@echo off
REM ===========================================================
REM  TI6-Sammler - taeglicher Start fuer sammler.py
REM  [AUDIT 06.08.2026]
REM
REM  Warum diese Datei:
REM    1) Der Projektpfad enthaelt Klammern - das bricht das
REM       Quoting von schtasks /tr. Ein Starter umgeht das.
REM    2) "python" ist hier ein Windows-Store-Alias
REM       (WindowsApps\python.exe). Diese Aliase versagen in
REM       geplanten Aufgaben haeufig, weil die Aufgabe ohne
REM       vollstaendige Benutzer-Umgebung startet. Darum der
REM       aufgeloeste, absolute Interpreterpfad.
REM
REM  Faesst den Bot NICHT an. Schreibt nur in die drei
REM  Sammel-Dateien und in data_store\sammler.log.
REM
REM  Aufgabe wieder entfernen:
REM    schtasks /Delete /TN "TI6-Sammler" /F
REM ===========================================================

REM [17.09.2026] Hier stand der PAPIER-Ordner fest eingetragen:
REM   set "PROJ=C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)"
REM Diese Datei liegt im LIVE-Ordner. Ein Doppelklick haette also den
REM Sammler des Papier-Ordners gestartet - und im LIVE-Ordner waere
REM nichts passiert, ohne Fehlermeldung. %~dp0 ist der Ordner, in dem
REM DIESE Datei liegt; damit stimmt es in beiden Ordnern und auch nach
REM einem Umzug auf einen anderen Rechner.
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"
set "PY=%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"

cd /d "%PROJ%" || exit /b 9

REM Falls der aufgeloeste Pfad nach einem Python-Update nicht mehr
REM stimmt: auf das normale "python" zurueckfallen, statt still
REM nichts zu tun.
if not exist "%PY%" set "PY=python"

REM [FENSTER-FIX 11.08.2026] Ruft jetzt job_sammler.py statt sammler.py
REM direkt. Der Starter uebernimmt Log-Umleitung, Log-Rotation,
REM Doppelstart-Sperre und den Status-Eintrag in telemetrie.db (Tabelle
REM jobs). Damit ist der Job unsichtbar UND beobachtbar.
REM
REM ACHTUNG: Diese Datei wird von der Aufgabenplanung NICHT mehr
REM aufgerufen. Die Aufgabe "TI6-Sammler" startet seit dem 11.08.2026
REM direkt pythonw.exe mit job_sammler.py - pythonw hat keine Konsole,
REM also erscheint kein Fenster. Diese .bat bleibt nur als Starter von
REM Hand (Doppelklick), und dort ist ein Fenster ja erwuenscht.
REM
REM KORREKTUR 11.08.2026: Eine Zwischenfassung behauptete hier, der
REM pythonw-Weg schlage fehl, weil der WindowsApps-Pfad ein
REM Alias-Platzhalter sei. Das war eine Fehldiagnose. Der Job lief
REM (Beleg: data_store\jobs\forschung_capture.log, START 03:24:34Z mit
REM genau diesem Pfad) - er brauchte nur lange, weil die Maschine an
REM dem Vormittag extrem traege war. Es wurde zu frueh nachgesehen.
"%PY%" job_sammler.py
set RC=%ERRORLEVEL%
exit /b %RC%
