@echo off
REM ================================================================
REM GITHUB_ANMELDEN.bat - meldet diesen Rechner EINMAL bei GitHub an
REM ================================================================
REM WARUM: Damit Claude dein Repository auf PRIVAT stellen und den
REM Bot hochladen kann, braucht das GitHub-Programm (gh) einmal deine
REM Anmeldung. Dein Passwort gibst du nur im Browser bei GitHub ein,
REM nirgends sonst.
REM
REM ABLAUF:
REM   1. Frage "Authenticate Git with your GitHub credentials?" -> Enter
REM   2. Ein Code wie ABCD-1234 erscheint. Enter druecken.
REM   3. Der Browser oeffnet GitHub: Code eingeben, "Continue",
REM      dann "Authorize github" klicken.
REM   4. Zurueck in diesem Fenster steht "Logged in". Fertig.
REM ================================================================
chcp 65001 > nul
setlocal
set "GH="
for /f "delims=" %%G in ('where gh 2^>nul') do if not defined GH set "GH=%%G"
if not defined GH for /f "delims=" %%G in ('where /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" gh.exe 2^>nul') do if not defined GH set "GH=%%G"
if not defined GH goto keingh

echo.
echo  GitHub-Anmeldung startet. Einfach den Anweisungen folgen:
echo  Enter druecken, Code im Browser eingeben, "Authorize" klicken.
echo.
"%GH%" auth login --hostname github.com --git-protocol https --web
if errorlevel 1 goto fehler
"%GH%" auth setup-git
echo.
"%GH%" auth status
echo.
echo  ============================================================
echo   FERTIG. Schreib Claude jetzt einfach: angemeldet
echo  ============================================================
goto ende

:keingh
echo.
echo  [FEHLER] Das GitHub-Programm gh.exe wurde nicht gefunden.
echo           Sag Claude Bescheid, dann wird es neu installiert.
goto ende

:fehler
echo.
echo  [FEHLER] Die Anmeldung wurde nicht abgeschlossen.
echo           Einfach noch einmal doppelklicken und neu versuchen.

:ende
echo.
pause
