@echo off
chcp 65001 > nul
REM ============================================================
REM  VISUAL-C-LAUFZEIT NACHINSTALLIEREN   [UMZUG 01.09.2026]
REM  Einfach doppelklicken. Windows fragt nach Adminrechten -
REM  das ist richtig so, hier wird eine Systemkomponente gesetzt.
REM ============================================================
REM  WARUM
REM  pandas-ta laesst sich nicht laden. Gemessene Ursachenkette:
REM
REM    pandas_ta  ->  numba  ->  llvmlite  ->  llvmlite.dll
REM    FileNotFoundError: Could not find module llvmlite.dll
REM                      (or one of its dependencies)
REM
REM  Die DLL selbst ist da (88,6 MB). Was fehlt, ist eine
REM  Abhaengigkeit: msvcp140.dll, die C++-Laufzeit von Microsoft.
REM  Auf einem fabrikneuen Windows ist sie nicht dabei.
REM
REM  Gegenprobe, warum die Erklaerung traegt:
REM    numpy, pandas und sklearn bringen jeweils IHRE EIGENE
REM    private msvcp140.dll mit (numpy.libs\, pandas.libs\,
REM    sklearn\.libs\) - deshalb laufen die drei.
REM    llvmlite bringt keine mit und braucht die systemweite.
REM
REM  Ohne pandas-ta rechnet der Bot keine Indikatoren.
REM ============================================================
echo.
echo ============================================================
echo    VISUAL-C-LAUFZEIT NACHINSTALLIEREN
echo ============================================================
echo.
echo    Vorher - was in System32 liegt:
if exist "%WINDIR%\System32\msvcp140.dll" (echo      msvcp140.dll        DA) else (echo      msvcp140.dll        FEHLT)
if exist "%WINDIR%\System32\vcruntime140.dll" (echo      vcruntime140.dll    DA) else (echo      vcruntime140.dll    FEHLT)
echo.
echo    Wird jetzt geholt. Windows fragt gleich nach Adminrechten.
echo.

winget install --id Microsoft.VCRedist.2015+.x64 --exact --silent --accept-package-agreements --accept-source-agreements
set RC=%ERRORLEVEL%
echo.
echo    winget-Rueckgabe: %RC%
echo.
echo    Nachher - was in System32 liegt:
if exist "%WINDIR%\System32\msvcp140.dll" (echo      msvcp140.dll        DA) else (echo      msvcp140.dll        FEHLT)
if exist "%WINDIR%\System32\vcruntime140.dll" (echo      vcruntime140.dll    DA) else (echo      vcruntime140.dll    FEHLT)
echo.

if not exist "%WINDIR%\System32\msvcp140.dll" goto misslungen

echo    --- Der eigentliche Beweis: laedt pandas-ta jetzt? ---
call "%~dp0_python_finden.bat"
if errorlevel 1 goto keinpython
"%PY%" -c "import pandas_ta; print('   [OK] pandas_ta laedt.')"
if errorlevel 1 goto ladenichtok
echo.
echo    [FERTIG] Laufzeit da und pandas-ta laedt.
goto ende

:ladenichtok
echo.
echo    [ACHTUNG] Die Laufzeit ist da, pandas-ta laedt trotzdem nicht.
echo              Dann ist es eine andere Ursache. Meldung an Sven,
echo              nichts drumherum basteln.
goto ende

:misslungen
echo    [FEHLER] msvcp140.dll ist immer noch nicht da.
echo             winget-Rueckgabe oben ansehen. Moeglich: Adminfrage
echo             abgelehnt, oder kein Netz.
goto ende

:keinpython
echo    [FEHLER] Python nicht gefunden - _python_finden.bat meldet %ERRORLEVEL%.

:ende
echo.
echo ============================================================
pause
