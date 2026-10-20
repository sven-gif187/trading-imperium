@echo off
chcp 65001 > nul
REM ============================================================
REM  SICHERUNG AUF USB-STICK          [angelegt 02.09.2026]
REM  Einfach doppelklicken. Stick vorher einstecken.
REM ============================================================
REM  WARUM ES DIESE DATEI GIBT
REM
REM  Befund 28 war erledigt - auf dem ALTEN Rechner. Dort lag der
REM  Code in einem Git-Repository und eine 854-MB-Kopie in
REM  OneDrive. Auf diesem Rechner ist beides nicht mehr da:
REM    - kein .git im Projektordner
REM    - ~/OneDrive enthaelt nur desktop.ini
REM    - nur ein einziges Laufwerk C:
REM
REM  Damit haengt die gesamte Messung ab dem 01.09. an einer
REM  einzigen Platte. Der alte Rechner hat den Stand bis zum
REM  Umzug - alles danach gibt es nur hier, einmal.
REM
REM  WAS SIE TUT
REM  Ruft sicherung.py auf, das bereits gebaut und geprueft ist.
REM  Das kopiert den ganzen Projektordner auf den Stick UND legt
REM  zusaetzlich saubere Abzuege aller Datenbanken an - denn der
REM  Bot schreibt waehrenddessen weiter, und eine roh kopierte
REM  SQLite-Datei mitten im Schreibvorgang ist wertlos.
REM
REM  Die .env mit dem Telegram-Token wird NICHT mitkopiert.
REM  Ein Stick geht verloren; ein Token darin waere endgueltig
REM  draussen. Neu erzeugen dauert bei BotFather eine Minute.
REM
REM  SIE AENDERT NICHTS AM BOT. Sie liest und kopiert nur - der
REM  Freeze des Messfensters bleibt also unberuehrt.
REM
REM  Beim zweiten Lauf werden nur Aenderungen uebertragen.
REM ============================================================
cd /d "%~dp0"

echo.
echo ============================================================
echo    SICHERUNG AUF USB-STICK
echo ============================================================
echo.

REM --- 1. Python finden (eine einzige Quelle, siehe _python_finden.bat)
call "%~dp0_python_finden.bat"
if errorlevel 2 (
    echo    [FEHLER] Gefundenes Python ist nicht 3.13.
    goto ende
)
if errorlevel 1 (
    echo    [FEHLER] Kein Python 3.13 gefunden.
    echo             Erst EINRICHTUNG_1_PYTHON_PRUEFEN.bat ausfuehren.
    goto ende
)
echo    Python : "%PY%"

REM --- 2. USB-Stick suchen (DriveType 2 = Wechseldatentraeger)
set "USB="
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=2' | Select-Object -First 1 -ExpandProperty DeviceID)" 2^>nul`) do set "USB=%%D"

if not defined USB (
    echo.
    echo    [KEIN STICK] Es steckt kein USB-Stick in diesem Rechner.
    echo.
    echo    Windows meldet nur die feste Platte C:. Bitte einen
    echo    Stick einstecken, kurz warten, bis Windows ihn zeigt,
    echo    und diese Datei erneut doppelklicken.
    echo.
    echo    Platzbedarf: rund 2,5 GB.
    goto ende
)
echo    Stick  : %USB%

REM --- 3. Freien Platz pruefen, bevor irgendetwas kopiert wird
set "FREIGB="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='%USB%'\").FreeSpace/1GB,1)" 2^>nul`) do set "FREIGB=%%F"
echo    frei   : %FREIGB% GB   (gebraucht werden rund 2,5 GB)
echo.

set "ZIEL=%USB%\trading_imperium_sicherung"
echo    Ziel   : "%ZIEL%"
echo.
echo ============================================================
echo    Der Bot laeuft dabei ungestoert weiter.
echo    Es wird NUR gelesen und kopiert.
echo ============================================================
echo.
choice /C JN /N /M "    Jetzt sichern? [J]a / [N]ein: "
if errorlevel 2 goto abbruch

echo.
echo    --- Sicherung laeuft, das kann beim ersten Mal einige
echo        Minuten dauern ---
echo.
"%PY%" "%~dp0sicherung.py" "%ZIEL%"
if errorlevel 1 (
    echo.
    echo    [FEHLER] sicherung.py hat einen Fehler gemeldet.
    echo             Meldung oben lesen. Nichts geloescht.
    goto ende
)

echo.
echo    [OK] Sicherung abgeschlossen.
echo.
echo    Gegenprobe von Hand - bitte einmal selbst nachsehen:
echo      1. "%ZIEL%" im Explorer oeffnen
echo      2. Es muss einen Ordner _datenbank_schnappschuss geben
echo      3. Darin liegen die .db-Abzuege
echo.
echo    Den Stick danach abmelden ("Hardware sicher entfernen")
echo    und NICHT dauerhaft steckenlassen - ein Stick, der immer
echo    drinsteckt, faellt mit demselben Rechner aus.
goto ende

:abbruch
echo.
echo    Abgebrochen. Nichts kopiert.

:ende
echo.
echo ============================================================
pause
