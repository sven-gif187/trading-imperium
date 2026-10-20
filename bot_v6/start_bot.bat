@echo off
chcp 65001 > nul
REM ============================================================
REM  BOT STARTEN  -  einfach doppelklicken
REM ============================================================
REM  Startet app.py. Der Bot faehrt seine Waechter selbst hoch:
REM  sammler_pruefen.py:54 wird beim Hochfahren gerufen und
REM  startet Schatten-Universum und Positionsverlauf mit.
REM  Es gibt also keinen Handstart-Marathon.
REM
REM  [UMZUG 01.09.2026] Zwei Aenderungen gegenueber der alten
REM  Fassung, beide gegen stilles Scheitern:
REM
REM   1) "cd /d %~dp0". Vorher stand hier nur "python app.py" -
REM      das setzt voraus, dass das Arbeitsverzeichnis schon der
REM      Projektordner ist. Beim Doppelklick stimmt das, bei
REM      jedem anderen Aufrufweg nicht.
REM
REM   2) Nicht mehr blankes "python", sondern der aufgeloeste
REM      Pfad aus _python_finden.bat.
REM
REM  [KONSOLENSPERRE 02.09.2026] Die dritte und wichtigste:
REM
REM   3) Die Ausgabe geht in eine DATEI, nicht ins Fenster.
REM
REM      WARUM. Der Bot blieb dreimal hintereinander im Start
REM      stehen - immer an derselben Stelle, direkt nach
REM      "[REBAL] Zustand wiederhergestellt" und VOR
REM      "Trading Imperium V6 startet...". Threads, die nichts
REM      ausgeben (Buecher-Check, Ticket-Waechter), liefen weiter;
REM      alles, was schreibt, stand. Der Prozess verbrauchte dabei
REM      weiter CPU und das Fenster meldete "reagiert".
REM
REM      Ursache: In der Windows-Konsole ist der
REM      Schnellbearbeitungsmodus (QuickEdit) eingeschaltet
REM      (HKCU\Console\QuickEdit = 1). Wird darin Text markiert -
REM      auch versehentlich, durch einen Klick ins Fenster -,
REM      blockiert JEDE weitere Ausgabe, und der schreibende
REM      Prozess friert an seiner naechsten Zeile ein.
REM
REM      Belegt durch A/B-Test am 02.09.2026: derselbe Bot,
REM      dieselbe Maschine, dieselbe Minute.
REM        Ausgabe ins Fenster  -> haengt, "V6 startet" kommt nie
REM        Ausgabe in eine Datei -> "V6 startet" nach 50 s,
REM                                 danach DXY, WebSocket, XGBoost
REM
REM      Eine Pipe oder Datei kann nicht blockiert werden. Damit
REM      ist die ganze Fehlerklasse weg - unabhaengig davon, ob
REM      jemand ins Fenster klickt.
REM
REM      Der Bot fuehrt sein eigenes Protokoll ohnehin in
REM      data_store\system.log. Die hier umgeleitete Ausgabe ist
REM      nur das, was daneben auf die Konsole ginge.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

call "%~dp0_python_finden.bat"
if errorlevel 1 goto keinpython

if not exist "%~dp0data_store\jobs" mkdir "%~dp0data_store\jobs" 2>nul
set "KONSOLE=%~dp0data_store\jobs\bot_konsole.log"

REM Vorherigen Lauf aufheben, statt ihn zu ueberschreiben - sonst
REM ist nach einem Absturz genau das weg, was man braucht.
if exist "%KONSOLE%" move /y "%KONSOLE%" "%KONSOLE%.vorher" >nul 2>&1

echo.
echo ============================================================
echo    TRADING IMPERIUM V6
echo ============================================================
echo.
echo    Python : %PY%
echo    Ausgabe: data_store\jobs\bot_konsole.log
echo.
echo    Das Cockpit-Fenster oeffnet sich gleich.
echo    Dieses Fenster bitte OFFEN LASSEN - es haelt den Bot.
echo    NICHT hineinklicken.
echo.
echo    Laeuft der Bot? Nicht hier nachsehen, sondern:
echo        SAMMLER_PRUEFEN.bat   doppelklicken
echo.
echo ============================================================

"%PY%" app.py > "%KONSOLE%" 2>&1
set RC=%ERRORLEVEL%

echo.
echo    Bot beendet, Rueckgabewert %RC%.
if not "%RC%"=="0" (
    echo.
    echo    Das war KEIN sauberes Ende. Die letzten Zeilen:
    echo    ------------------------------------------------------
    powershell -NoProfile -Command "Get-Content '%KONSOLE%' -Tail 25" 2>nul
    echo    ------------------------------------------------------
    echo    Vollstaendig in: %KONSOLE%
)
goto ende

:keinpython
echo.
echo [FEHLER] Kein Python 3.13 gefunden - _python_finden.bat meldet %ERRORLEVEL%.
echo          1 = gar nichts gefunden, 2 = gefunden aber nicht 3.13.
echo          Erst EINRICHTUNG_0_PYTHON_313_HOLEN.bat ausfuehren.

:ende
echo.
pause
