@echo off
REM ============================================================
REM  SCHATTEN-UNIVERSUM starten - OHNE Fenster
REM ============================================================
REM  Rechnet stuendlich fuer 18 Muenzen dieselbe Punktzahl aus
REM  wie der Bot und schreibt sie mit. HANDELT NICHT.
REM
REM  [REPARIERT 20.08.2026] Sven: "irgendwie funktioniert der
REM  schattenuniversum.bat nicht!"
REM
REM  Er hatte recht, und der Grund war heimtueckisch. Hier stand
REM  der VOLLE Pfad nach C:\Program Files\WindowsApps\...
REM  Diese Datei EXISTIERT dort (Test-Path sagt True), aber
REM  Windows verweigert den Zugriff beim Starten:
REM
REM      Start-Process ... -> "Zugriff verweigert"
REM
REM  Und "start """ /B" verschluckt genau diesen Fehler. Es sah
REM  also aus, als passiere nichts - es passierte auch nichts.
REM
REM  Die Warnung im alten Kopf war RICHTIG (der 0-Byte-Alias
REM  scheitert ueber die Aufgabenplanung) - nur die daraus
REM  gezogene Lehre war zu breit. Aus einem normalen Fenster
REM  heraus greift der Alias, der geschuetzte Ordner nicht.
REM
REM  Jetzt uebernimmt sammler_pruefen.py den Start: es nimmt
REM  sys.executable, startet nur was fehlt, und sieht 15 Sekunden
REM  spaeter nach, ob wirklich etwas laeuft. Kein stiller Ausfall.
REM
REM  Stand ansehen : SAMMLER_PRUEFEN.bat
REM  Beenden       : schatten_universum_stop.bat
REM ============================================================

cd /d "%~dp0"
python sammler_pruefen.py --starten
echo.
pause
