@echo off
chcp 65001 > nul
REM ============================================================
REM  EINRICHTUNG 0 von 3  -  Python 3.13 holen
REM  [UMZUG 01.09.2026]  Einfach doppelklicken.
REM ============================================================
REM  Auf diesem Rechner ist der Python-Verwalter (Python Install
REM  Manager) installiert, nicht der klassische Installer. Der
REM  Verwalter wollte von sich aus 3.14 installieren - das waere
REM  falsch gewesen:
REM
REM    requirements.txt pinnt numpy==2.2.6, pandas==2.3.3,
REM    scikit-learn==1.8.0. Fuer 3.14 gibt es zu diesen Versionen
REM    keine fertigen Pakete. pip muesste aus dem Quelltext bauen,
REM    dafuer fehlt der Compiler - die Installation bricht ab.
REM    Der Quellrechner laeuft auf 3.13.14.
REM
REM  Diese Datei holt deshalb gezielt 3.13 und sonst nichts.
REM  Sie laedt aus dem Netz - das dauert ein paar Minuten.
REM ============================================================
cd /d "%~dp0"
echo.
echo ============================================================
echo    SCHRITT 0 - PYTHON 3.13 HOLEN
echo ============================================================
echo.

set "PYM="
where py >nul 2>&1
if not errorlevel 1 set "PYM=py"
if not defined PYM if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\py.exe" set "PYM=%LOCALAPPDATA%\Microsoft\WindowsApps\py.exe"
if not defined PYM goto keinverwalter

echo    Verwalter: %PYM%
echo.
echo    --- Was ist schon installiert? ---
"%PYM%" list
echo.
echo    --- 3.13 holen. Das laedt aus dem Netz, bitte warten. ---
echo.
"%PYM%" install 3.13
if errorlevel 1 goto installfehler

echo.
echo    --- Was ist jetzt installiert? ---
"%PYM%" list
echo.
echo    --- Wo liegt die 3.13 wirklich? ---
"%PYM%" -V:3.13 -c "import sys; print(sys.version); print(sys.executable)"
if errorlevel 1 goto keine313
echo.
echo    [OK] 3.13 ist da.
echo         Als naechstes: EINRICHTUNG_1_PYTHON_PRUEFEN.bat
goto ende

:installfehler
echo.
echo    [FEHLER] Der Verwalter konnte 3.13 nicht installieren.
echo             Meldung oben lesen und Sven schicken.
echo             NICHT auf 3.14 ausweichen.
goto ende

:keine313
echo.
echo    [FEHLER] Installation lief durch, aber 3.13 laesst sich
echo             nicht starten. Das ist genau die Sorte stilles
echo             Scheitern, die hier nicht durchgehen darf.
echo             Meldung oben an Sven.
goto ende

:keinverwalter
echo    [FEHLER] Kein "py" gefunden - der Python-Verwalter ist nicht
echo             im Suchpfad. Hast du den Rechner nach der
echo             Installation neu gestartet? Der Suchpfad wirkt
echo             erst in einem neu geoeffneten Fenster.

:ende
echo.
echo ============================================================
pause
