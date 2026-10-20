@echo off
REM ====================================================================
REM  CHARTTEST.bat - prueft, ob der Analyse-Chart sauber gezeichnet wird
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab - das ist hier schon passiert.
REM ====================================================================
cd /d "%~dp0"
title Chart-Zeichentest

echo.
echo  ============================================================
echo   CHART-ZEICHENTEST
echo  ============================================================
echo.
echo   Es oeffnet sich KEIN Fenster und es wird NICHTS gehandelt.
echo   Der Chart wird nur im Speicher gezeichnet und ausgemessen.
echo.
echo   1  Schnellpruefung   (Selbst- und Gegentest, ca. 1 Minute)
echo   2  Nur Bitcoin       (5 Zeitrahmen, ca. 3 Minuten)
echo   3  Vollauf           (3 Muenzen, 5 Zeitrahmen, ca. 8 Minuten)
echo.
set /p wahl=  Was soll es sein? [1/2/3, Enter = 1] :

if "%wahl%"=="3" goto voll
if "%wahl%"=="2" goto btc
goto schnell

:schnell
echo.
echo  --- Selbsttest: bewertet das Werkzeug richtig? ---
python chart_zeichentest.py --selbsttest
echo.
echo  --- Gegentest: findet es den bekannten Fehler wieder? ---
python chart_zeichentest.py --gegentest
goto ende

:btc
echo.
python chart_zeichentest.py --muenzen BTC/USDT
goto ende

:voll
echo.
python chart_zeichentest.py
goto ende

:ende
echo.
echo  ============================================================
echo   Steht unten ALLE ... SAUBER, sitzen alle Linien richtig.
echo   Steht dort etwas anderes, sagt die Zeile daneben was fehlt.
echo.
echo   ACHTUNG: Geprueft wird die LAGE der Linien im Bild -
echo   nicht, ob sie inhaltlich richtig sind. Das kann nur ein
echo   Vergleich mit einem bekannten Wert (siehe Handbuch 6.9).
echo  ============================================================
echo.
pause
