@echo off
chcp 65001 > nul
REM [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
REM ============================================================
REM  BOT BEWUSST AUS / WIEDER AUTOMATISCH  -  doppelklicken
REM ============================================================
REM  Seit 14.10.2026 startet die Aufgabe "TI-Bots-Autostart" nach
REM  jeder Anmeldung v6 und v7, wenn sie nicht laufen.
REM  Seit 15.10.2026 prueft zusaetzlich "TI-Bots-Neustart" alle
REM  15 Minuten und startet einen ausgefallenen Bot neu (Sven F5b).
REM  Deshalb IMMER zuerst hier die Sperre setzen, DANN den Bot schliessen.
REM
REM  Willst du einen Bot ABSICHTLICH aus lassen (z. B. vor einem
REM  Patch - Regel: Bot muss geschlossen sein, sonst ueberschreibt
REM  er die Korrektur aus dem Speicher), legst du hier die Sperre.
REM  Dann laesst ihn der Autostart in Ruhe, bis du sie aufhebst.
REM
REM  Die Sperre ist nur eine kleine Textdatei:
REM      pruefstand\autostart\v6.BEWUSST_AUS   bzw.  v7.BEWUSST_AUS
REM  mit deinem Grund darin. Sie stoppt KEINEN laufenden Bot - sie
REM  verhindert nur den automatischen Start.
REM ============================================================
cd /d "%~dp0"

echo.
echo  Aktueller Stand:
if exist "v6.BEWUSST_AUS" (echo    v6: BEWUSST AUS) else (echo    v6: startet automatisch)
if exist "v7.BEWUSST_AUS" (echo    v7: BEWUSST AUS) else (echo    v7: startet automatisch)
echo.
echo  1 = v6 bewusst aus        3 = v6 wieder automatisch
echo  2 = v7 bewusst aus        4 = v7 wieder automatisch
echo  0 = nichts aendern
echo.
set /p WAHL=Auswahl:

if "%WAHL%"=="1" set INST=v6& goto aus
if "%WAHL%"=="2" set INST=v7& goto aus
if "%WAHL%"=="3" set INST=v6& goto an
if "%WAHL%"=="4" set INST=v7& goto an
echo  Nichts geaendert.
goto ende

:aus
set /p GRUND=Grund (ein Satz):
if "%GRUND%"=="" set GRUND=ohne Grund
> "%INST%.BEWUSST_AUS" echo %DATE% %TIME% %GRUND%
echo.
echo  %INST% ist jetzt BEWUSST AUS. Grund: %GRUND%
echo  Den laufenden Bot schliesst du jetzt wie gewohnt selbst.
echo  Er startet nicht neu, solange die Sperre liegt.
goto ende

:an
if exist "%INST%.BEWUSST_AUS" del "%INST%.BEWUSST_AUS"
echo.
echo  %INST% startet spaetestens in 15 Minuten wieder von selbst.
echo  Jetzt sofort starten: start_bot.bat im Bot-Ordner doppelklicken.

:ende
echo.
pause
