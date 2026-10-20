@echo off
REM ============================================================
REM  POSITIONSVERLAUF-SAMMLER starten - OHNE Fenster
REM ============================================================
REM  [19.08.2026] Angelegt, weil der Sammler bisher von Hand
REM  gestartet wurde und deshalb bei jedem Neustart still stehen
REM  blieb - zuletzt am 19.08. um 21:58. Er liefert die Grundlage
REM  fuer den Vergleich der Ausstiegsregeln; faellt er aus, fehlen
REM  die Daten hinterher unwiederbringlich.
REM
REM  WICHTIG - echter Programmpfad, NICHT der WindowsApps-Verweis:
REM  ...\WindowsApps\pythonw.exe ist eine 0-Byte-Datei (App-Alias)
REM  und greift nicht in jedem Zusammenhang. Am 14.08.2026 hat genau
REM  das drei Versuche ueber die Aufgabenplanung lautlos scheitern
REM  lassen (siehe schatten_universum_start.bat).
REM
REM  Stand ansehen : python positionsverlauf.py --status
REM ============================================================

cd /d "%~dp0"

REM Laeuft schon einer? Dann nicht doppelt starten.
wmic process where "name='pythonw.exe'" get CommandLine 2>nul | find /I "positionsverlauf" >nul
if not errorlevel 1 (
    echo Laeuft bereits - nicht doppelt gestartet.
    exit /b 0
)

start "" /B "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.3824.0_x64__qbz5n2kfra8p0\pythonw.exe" "%~dp0positionsverlauf.py"
echo Positionsverlauf-Sammler gestartet.
exit /b 0
