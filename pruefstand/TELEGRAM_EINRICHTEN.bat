@echo off
chcp 65001 > nul
REM [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
REM ============================================================
REM  TELEGRAM-WAECHTER EINRICHTEN  -  einfach doppelklicken
REM ============================================================
REM  Traegt den Token deines neuen Telegram-Bots (von @BotFather)
REM  und deine Chat-ID in  pruefstand\.env  ein. Dorthin schreiben
REM  die Waechter ihre Alarme, z. B. "Bot v6 laeuft nicht".
REM
REM  Ablauf:
REM   1. Token einfuegen (Rechtsklick oder Strg+V) - die Eingabe
REM      bleibt unsichtbar, das ist Absicht. Enter.
REM   2. Das Skript prueft den Token direkt bei Telegram.
REM   3. Dann in Telegram deinem neuen Bot "hallo" schicken.
REM   4. Es kommt eine Testnachricht aufs Handy. Fertig.
REM
REM  Der Token wird nirgends angezeigt und nicht in Berichte
REM  geschrieben. Nochmal doppelklicken ist harmlos.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

set "PY=C:\Users\<BENUTZER>\AppData\Local\Python\pythoncore-3.13-64\python.exe"
if not exist "%PY%" (
    where py >nul 2>&1 && (set "PY=py") || (
        echo.
        echo [FEHLER] Kein Python gefunden. Erwartet: %PY%
        goto ende
    )
)

"%PY%" "%~dp0waechter\telegram_einrichten.py"

:ende
echo.
pause
