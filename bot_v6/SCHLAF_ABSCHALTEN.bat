@echo off
chcp 65001 > nul
REM ============================================================
REM  SCHLAF ABSCHALTEN  -  damit die Sammler nachts durchlaufen
REM  [UMZUG 02.09.2026]   Einfach doppelklicken.
REM ============================================================
REM  WARUM ES DIESE DATEI GIBT
REM
REM  In der ersten Nacht auf diesem Rechner fehlten Daten. Die
REM  Luecken deckten sich auf die Minute mit dem Windows-
REM  Ereignisprotokoll:
REM
REM    Datenluecke (UTC)      Ereignisprotokoll
REM    01.09. 22:50 - 23:07   Standby 22:53:21 - 23:05:26
REM    01.09. 23:18 - 23:54   Standby 23:20:56 - 23:51:55
REM    02.09. 00:46 - 10:37   Standby 00:48:29 - 10:33:41
REM
REM  Die letzte Luecke war 9 3/4 Stunden lang. Solange der Rechner
REM  schlaeft, sammelt hier nichts - der Bot laeuft nicht, die
REM  Waechter schreiben nicht, die geplanten Aufgaben starten nicht.
REM
REM  WAS DIESE DATEI AENDERT
REM    Nur EINE Einstellung: Standby am Netzbetrieb -> nie.
REM    Der Bildschirm darf weiter ausgehen (spart Strom, stoert
REM    nichts). Im Akkubetrieb bleibt alles, wie es war.
REM
REM  UMKEHRBAR: der alte Wert wird vorher angezeigt und unten
REM  genannt. Zum Zuruecksetzen den Befehl mit dem alten Wert
REM  ausfuehren - er steht in der Ausgabe.
REM ============================================================
cd /d "%~dp0"
echo.
echo ============================================================
echo    SCHLAF ABSCHALTEN - damit die Sammler durchlaufen
echo ============================================================
echo.
echo    JETZIGER STAND
echo    --------------
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | findstr /C:"Index"
echo.
echo    Der Wert ist hexadezimal und in Sekunden.
echo      0x384 = 900 Sekunden = 15 Minuten
echo      0x0   = nie
echo.
echo    Die erste Zeile ist der Netzbetrieb (Wechselstrom),
echo    die zweite der Akku (Gleichstrom).
echo.
echo ============================================================
echo    Es wird NUR der Netzbetrieb auf "nie" gesetzt.
echo    Der Akkubetrieb bleibt unveraendert.
echo ============================================================
echo.
choice /C JN /N /M "    Jetzt umstellen? [J]a / [N]ein: "
if errorlevel 2 goto abbruch

powercfg /change standby-timeout-ac 0
if errorlevel 1 goto fehler

echo.
echo    NEUER STAND
echo    -----------
powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | findstr /C:"Index"
echo.
echo    [OK] Standby am Netz steht jetzt auf "nie" (0x0).
echo.
echo    Rueckgaengig machen - diese Datei bearbeiten und den
echo    Befehl mit dem alten Wert in MINUTEN aufrufen, z.B.:
echo        powercfg /change standby-timeout-ac 15
echo.
echo    NOCH ZU PRUEFEN, wenn nachts weiter Daten fehlen:
echo      - Ruhezustand (Hibernate) hat einen EIGENEN Zeitgeber
echo      - "Moderner Standby" mancher Geraete ignoriert diese
echo        Einstellung teilweise
echo      Beides erst pruefen, wenn es wieder auftritt - nicht
echo      auf Verdacht umstellen.
goto ende

:fehler
echo.
echo    [FEHLER] powercfg hat abgelehnt. Meldung oben lesen.
echo             Manche Einstellungen sperrt eine Gruppenrichtlinie.
goto ende

:abbruch
echo.
echo    Abgebrochen. Nichts geaendert.

:ende
echo.
echo ============================================================
pause
