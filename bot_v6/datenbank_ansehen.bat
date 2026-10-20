@echo off
REM Telemetrie-Datenbank ansehen - ohne Zusatzprogramm, ohne SQL.
REM Doppelklick genuegt. Reines Lesen, aendert nie etwas.
cd /d "%~dp0"
:menu
cls
echo ==========================================================
echo   TELEMETRIE - was hat der Bot gemacht und warum?
echo ==========================================================
echo.
echo   1  Uebersicht        (wie viele Pruefungen, wie viele Kaeufe)
echo   2  Warum nicht?      (alle Ablehnungsgruende, haeufigste zuerst)
echo   3  Kaeufe            (was wurde tatsaechlich gekauft)
echo   4  Verlauf           (die letzten 30 Entscheidungen)
echo   5  Ein Coin          (alles zu BTC, ETH oder SOL)
echo.
echo   0  Beenden
echo.
set /p wahl=Zahl eingeben und Enter:

if "%wahl%"=="1" (python telemetrie_frage.py status & pause & goto menu)
if "%wahl%"=="2" (python telemetrie_frage.py gruende & pause & goto menu)
if "%wahl%"=="3" (python telemetrie_frage.py kaeufe & pause & goto menu)
if "%wahl%"=="4" (python telemetrie_frage.py verlauf & pause & goto menu)
if "%wahl%"=="5" (
    set /p coin=Welcher Coin [BTC/ETH/SOL]:
    python telemetrie_frage.py coin !coin!
    pause
    goto menu
)
if "%wahl%"=="0" exit
goto menu
