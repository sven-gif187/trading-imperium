@echo off
REM ====================================================================
REM  FELDER_NACHTRAGEN.bat  -  Analysefelder ins Handelsjournal nachtragen
REM
REM  WARUM ES DIESE DATEI GIBT (29.08.2026, Befund 88)
REM  Der Nachtrag muss bei GESTOPPTEM Bot laufen. Laeuft app.py, haelt er
REM  das Journal im Arbeitsspeicher und schreibt die ganze Datei neu -
REM  ein Nachtrag ist dann binnen Sekunden weg. Beim ersten Versuch hielt
REM  er genau 41 Sekunden, und die Erfolgsmeldung kam trotzdem.
REM
REM  Diese Datei nimmt die Reihenfolge ab. Sie beendet den Bot NICHT
REM  selbst - das bleibt Svens Entscheidung (Bestandsschutz, CLAUDE.md 4).
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Felder nachtragen

:anfang
cls
echo.
echo  ============================================================
echo   ANALYSEFELDER NACHTRAGEN   (Befund 88)
echo  ============================================================
echo.
echo   Traegt position_id und haltedauer_min bei Verkaeufen nach,
echo   bei denen sie fehlen. Quelle: positionsverlauf.db
echo.
echo   Vorhandene Werte werden NIE ueberschrieben.
echo   Jeder nachgetragene Wert wird als solcher markiert.
echo.

echo   Pruefe, ob der Bot laeuft ...
REM  Der Filter "Name like 'python%%'" ist NICHT kosmetisch: ohne ihn
REM  findet die Pruefung SICH SELBST. Die Befehlszeile des powershell.exe,
REM  das sie ausfuehrt, enthaelt die Zeichenkette "app.py" - sie steht ja
REM  im Suchmuster. Ergebnis: "der Bot laeuft", auch wenn er zu ist.
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Where-Object { $_.CommandLine -like '*app.py*' }) { exit 1 } else { exit 0 }"
if errorlevel 1 (goto laeuft) else (goto aus)

:laeuft
echo.
echo   ------------------------------------------------------------
echo    DER BOT LAEUFT.
echo   ------------------------------------------------------------
echo.
echo    Nachtragen geht jetzt nicht. app.py haelt das Journal im
echo    Arbeitsspeicher und schreibt die ganze Datei neu, sobald ein
echo    Handel stattfindet - der Nachtrag waere sofort wieder weg.
echo.
echo    RICHTIGE REIHENFOLGE:
echo      1. Bot beenden  (sein Fenster schliessen)
echo      2. diese Datei nochmal starten
echo      3. Bot wieder starten - er liest die ergaenzte Datei ein
echo.
echo    Ein PROBELAUF geht trotzdem - er aendert nichts.
echo.
set /p pl=  Probelauf jetzt ansehen? [j/n, Enter = j] :
if /i "%pl%"=="n" goto ende
echo.
python felder_nachtragen.py
goto ende

:aus
echo   Der Bot laeuft nicht - Nachtragen ist moeglich.
echo.
echo   1  Probelauf     nur zeigen, was passieren wuerde
echo   2  Nachtragen    wirklich eintragen (mit Sicherung)
echo.
set /p wahl=  Was soll es sein? [1/2, Enter = 1] :
echo.
if "%wahl%"=="2" goto schreiben

python felder_nachtragen.py
echo.
echo   Das war nur der Probelauf. Es wurde nichts geaendert.
goto ende

:schreiben
python felder_nachtragen.py --schreiben
echo.
echo   ------------------------------------------------------------
echo    Nicht vergessen: den Bot wieder STARTEN.
echo    Er liest die ergaenzte Datei beim Start ein.
echo   ------------------------------------------------------------
goto ende

:ende
echo.
echo  ============================================================
echo   Nachsehen, was noch fehlt:  VOLLSTAENDIGKEIT.bat
echo  ============================================================
echo.
pause
