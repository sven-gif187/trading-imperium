@echo off
chcp 65001 > nul
REM ============================================================
REM  EINRICHTUNG 1 von 3  -  Ist Python richtig installiert?
REM  [UMZUG 01.09.2026]  Einfach doppelklicken.
REM ============================================================
REM  Prueft drei Dinge:
REM    1) Gibt es ueberhaupt ein Python?
REM    2) Ist es das ECHTE - oder nur der Store-Platzhalter unter
REM       WindowsApps, der den Store oeffnet statt zu starten und
REM       in geplanten Aufgaben still scheitert?
REM    3) Ist es Version 3.13, wie auf dem Quellrechner?
REM
REM  Absichtlich flach gebaut: keine verschachtelten Klammern mit
REM  Umleitung. Genau daran brechen .bat-Dateien lautlos.
REM ============================================================
cd /d "%~dp0"
echo.
echo ============================================================
echo    SCHRITT 1 - PYTHON PRUEFEN
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 goto keinpython

echo    --- Alle gefundenen python.exe ---
where python
echo.

where python 2>nul | findstr /i "WindowsApps" >nul
if errorlevel 1 goto keinalias
echo    [WARNUNG] Ein Store-Platzhalter unter WindowsApps ist noch aktiv.
echo              Abschalten unter:
echo                Einstellungen / Apps / Erweiterte App-Einstellungen
echo                / App-Ausfuehrungsaliase
echo              Dort python.exe und python3.exe auf AUS stellen.
echo.
:keinalias

set "PY="
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul ^| findstr /i /v "WindowsApps"') do if not defined PY set "PY=%%P"
if not defined PY goto nurplatzhalter

echo    --- Das echte Python, das ab jetzt benutzt wird ---
echo    %PY%
echo.
echo    --- Version ---
"%PY%" --version
echo.
echo    --- Wo es wirklich liegt. Darf NICHT WindowsApps enthalten ---
"%PY%" -c "import sys; print(sys.executable)"
echo.
"%PY%" -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,13) else 1)"
if errorlevel 1 goto falscheversion
echo    [OK] Version 3.13 - passt zum Quellrechner.
goto ende

:falscheversion
echo    [WARNUNG] Das ist nicht 3.13. Der Quellrechner laeuft auf 3.13.14.
echo              Gepinnte Pakete koennen auf einer anderen Version nicht
echo              bauen. Sven Bescheid sagen, nichts eigenmaechtig aendern.
goto ende

:keinpython
echo    [FEHLT] Es gibt gar kein "python" im Suchpfad.
echo.
echo    Was zu tun ist: Python 3.13 von python.org installieren und
echo    dabei den Haken "Add python.exe to PATH" setzen.
goto ende

:nurplatzhalter
echo    [FEHLER] Es ist nur der Store-Platzhalter da, kein echtes Python.
echo.
echo    Was zu tun ist: Python 3.13 von python.org installieren,
echo    Haken "Add python.exe to PATH" setzen, danach die
echo    App-Ausfuehrungsaliase abschalten.
goto ende

:ende
echo.
echo ============================================================
pause
