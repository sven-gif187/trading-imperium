@echo off
chcp 65001 > nul
REM ============================================================
REM  EINRICHTUNG 3 von 3  -  Ist wirklich alles da?
REM  [UMZUG 01.09.2026]  Einfach doppelklicken.
REM ============================================================
REM  "pip meldet keinen Fehler" ist kein Beleg. Diese Datei
REM  importiert jedes Paket wirklich und liest zusaetzlich alle
REM  .py des Projekts mit ast ein, um zu finden, was der Code
REM  braucht und requirements.txt nicht nennt.
REM
REM  Sie AENDERT NICHTS. Sie misst nur.
REM ============================================================
cd /d "%~dp0"
set "PY="
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul ^| findstr /i /v "WindowsApps"') do if not defined PY set "PY=%%P"
if not defined PY goto keinpython

set PYTHONIOENCODING=utf-8
"%PY%" pakete_pruefen.py
echo.
if errorlevel 1 echo    [ACHTUNG] Es fehlt etwas. Die Tabelle oben sagt was.
if not errorlevel 1 echo    [OK] Vollstaendig.
goto ende

:keinpython
echo    [FEHLER] Kein echtes Python gefunden.
echo             Erst EINRICHTUNG_1_PYTHON_PRUEFEN.bat ausfuehren.

:ende
echo.
echo ============================================================
pause
