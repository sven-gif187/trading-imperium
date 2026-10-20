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

REM ===========================================================
REM  [UMZUG 01.09.2026 - neuer Rechner, neuer Ordnername]
REM  Vorher standen hier zwei feste Pfade auf den alten Rechner
REM  (Benutzer sven7, Ordner trading_imperium_v6(21)). Auf dieser
REM  Maschine zeigen sie ins Leere: "cd /d" waere mit Exit-Code 9
REM  abgebrochen - die geplante Aufgabe haette ausgesehen, als
REM  liefe sie, und nichts getan. Genau das stille Scheitern.
REM
REM  Jetzt findet sich die Datei selbst: "%~dp0" ist der Ordner,
REM  in dem DIESE .bat liegt. Damit ist sie umzugsfest.
REM ===========================================================
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"

REM  Python NICHT blind als "python" aufrufen. Windows liefert unter
REM  WindowsApps einen Platzhalter mit, der den Store oeffnet statt zu
REM  starten - in geplanten Aufgaben scheitert er still. Deshalb:
REM  bekannte Installationsorte zuerst, danach "where python" OHNE
REM  WindowsApps-Treffer. Wird nichts gefunden, bricht die Datei mit
REM  Meldung und Exit-Code 8 ab, statt lautlos nichts zu tun.
REM  [UMZUG 02.09.2026] Die Suche stand hier frueher ausgeschrieben.
REM  Sie fand auf diesem Rechner NICHTS und haette die Aufgabe bei
REM  jedem Lauf mit Exit-Code 8 abgebrochen: hier laeuft der
REM  Python-Verwalter (Python Install Manager), der legt Python nach
REM  %LOCALAPPDATA%\Python\pythoncore-3.13-64\ - nicht nach
REM  ...\Programs\Python\Python3*. Und der Rueckfall "where python
REM  ohne WindowsApps" verwarf die einzige vorhandene Weiche.
REM  Jetzt ueber die gemeinsame Suche - eine Quelle statt fuenf Kopien.
call "%~dp0_python_finden.bat"
if errorlevel 2 (
    echo [FEHLER] Python gefunden, aber es ist nicht 3.13.
    exit /b 8
)
if errorlevel 1 (
    echo [FEHLER] Kein Python 3.13 gefunden.
    echo          EINRICHTUNG_0_PYTHON_313_HOLEN.bat doppelklicken.
    exit /b 8
)

cd /d "%PROJ%" || exit /b 9

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
