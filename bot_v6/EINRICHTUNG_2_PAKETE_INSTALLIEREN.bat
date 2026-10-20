@echo off
chcp 65001 > nul
REM ============================================================
REM  EINRICHTUNG 2 von 3  -  Pakete installieren
REM  [UMZUG 01.09.2026]  Einfach doppelklicken.
REM ============================================================
REM  Installiert GENAU das, was in requirements.txt steht - mit den
REM  dort gepinnten Versionen. Kein --upgrade, kein Nachziehen.
REM  Die Pins sind Absicht: ein Update soll nie heimlich etwas
REM  Neueres ziehen, das etwas zerschiesst.
REM
REM  Dauert beim ersten Mal mehrere Minuten. Das Fenster bleibt
REM  am Ende offen - die letzte Zeile ist die wichtige.
REM ============================================================
cd /d "%~dp0"
echo.
echo ============================================================
echo    SCHRITT 2 - PAKETE INSTALLIEREN
echo ============================================================
echo.

set "PY="
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if not defined PY for /d %%D in ("%ProgramFiles%\Python3*") do if not defined PY if exist "%%~fD\python.exe" set "PY=%%~fD\python.exe"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul ^| findstr /i /v "WindowsApps"') do if not defined PY set "PY=%%P"
if not defined PY goto keinpython

echo    Benutzt: %PY%
"%PY%" --version
echo.
echo    --- pip selbst aktualisieren ---
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto pipfehler
echo.
echo    --- die gepinnten Pakete installieren ---
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto installfehler
echo.
echo    [OK] pip meldet keinen Fehler.
echo         Das heisst NICHT, dass alles da ist - das sagt erst
echo         EINRICHTUNG_3_PAKETE_PRUEFEN.bat. Jetzt die starten.
goto ende

:pipfehler
echo.
echo    [FEHLER] pip liess sich nicht aktualisieren. Meldung oben lesen.
goto ende

:installfehler
echo.
echo    [FEHLER] Mindestens ein Paket liess sich nicht installieren.
echo             Die Meldung oben nennt welches. NICHTS an
echo             requirements.txt aendern - Sven Bescheid sagen.
goto ende

:keinpython
echo    [FEHLER] Kein echtes Python gefunden.
echo             Erst EINRICHTUNG_1_PYTHON_PRUEFEN.bat ausfuehren.
goto ende

:ende
echo.
echo ============================================================
pause
