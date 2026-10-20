@echo off
REM ============================================================
REM  Schatten-Universum beenden
REM ============================================================
REM  Beendet NUR den Sammler - Bot und Forschungs-Capture laufen
REM  weiter. Die gesammelten Daten bleiben erhalten.
REM ============================================================

cd /d "%~dp0"
echo Beende das Schatten-Universum ...

for /f "skip=1 tokens=2 delims=," %%P in ('wmic process where "name='pythonw.exe'" get ProcessId^,CommandLine /format:csv 2^>nul ^| find /I "schatten_universum"') do (
    taskkill /PID %%P /F >nul 2>&1
)

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'schatten_universum' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo Beendet. Daten bleiben erhalten.
timeout /t 3 >nul
exit /b 0
