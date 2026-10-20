@echo off
chcp 65001 > nul
REM [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
REM ============================================================
REM  LEITSTAND ANMELDEN  -  einmal doppelklicken
REM ============================================================
REM  Die taegliche und woechentliche Pruefung (Aufgaben
REM  TI-Leitstand-Tag 07:30 und TI-Leitstand-Woche So 10:00)
REM  laufen ohne die Claude-App. Dafuer muss sich das
REM  Kommandozeilen-Claude EINMAL mit deinem Claude-Konto
REM  anmelden. Das macht dieses Fenster:
REM
REM   1. Ein Browser oeffnet sich: mit deinem Claude-Konto
REM      anmelden und "Zulassen" klicken (wie bei der App).
REM      Falls ein Code angezeigt wird: hier einfuegen, Enter.
REM   2. Danach prueft Claude einmal die Rechte (1-3 Minuten):
REM      darf nur lesen und nur nach pruefstand\berichte schreiben.
REM   3. Wenn alles passt, startet die Tagespruefung einmal
REM      sofort. Die Kurzfassung kommt in 5-15 Minuten per Telegram.
REM
REM  Dein Passwort sieht dabei niemand ausser der Anmeldeseite.
REM  Nochmal doppelklicken ist harmlos.
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

echo.
echo === Schritt 1: Anmeldung ===
"%PY%" "%~dp0skripte\leitstand_lauf.py" anmelden
if errorlevel 1 (
    echo.
    echo [FEHLER] Anmeldung hat nicht geklappt. Fenster offen lassen und Claude im Chat Bescheid geben.
    goto ende
)

echo.
echo === Schritt 2: Rechteprobe (1-3 Minuten) ===
"%PY%" "%~dp0skripte\leitstand_lauf.py" rechteprobe
if errorlevel 1 (
    echo.
    echo [STOPP] Rechteprobe NICHT bestanden. Die Tagespruefung startet deshalb nicht.
    echo         Claude im Chat Bescheid geben.
    goto ende
)

echo.
echo === Schritt 3: Tagespruefung einmal sofort starten ===
schtasks /run /tn "TI-Leitstand-Tag"
echo.
echo Fertig. Die Kurzfassung kommt in 5-15 Minuten per Telegram,
echo der Bericht liegt dann in pruefstand\berichte\ (Datum_lage.md).

:ende
echo.
pause
