@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  LIVE_EINRICHTEN.bat  -  zweite Instanz fuer den Echtgeld-Betrieb
REM
REM  WARUM ZWEI INSTANZEN (14.09.2026)
REM  `trading.mode` ist EINE Einstellung: ein Bot ist entweder Papier
REM  oder Echtgeld, nie beides. Wuerde dieser Bot umgeschaltet, endete
REM  die laufende Messung E9 - am 14.09. standen dort 3 von 100
REM  noetigen Verkaeufen.
REM
REM  Deshalb ein zweiter Ordner:
REM    hier                          Papier, E9 laeuft weiter
REM    ..\trading_imperium_LIVE      Echtgeld, Deckel 25/200 $
REM
REM  Sie stoeren einander nicht: die Doppelstart-Sperre legt ihre
REM  Sperrdatei in data_store ab, also pro Ordner.
REM
REM  KOPIERT KEINE SCHLUESSEL. Die .env muss von Hand herueber.
REM
REM  Der Ordnername enthaelt Klammern - daher die Anfuehrungszeichen.
REM ====================================================================
cd /d "%~dp0"
title Echtgeld-Instanz einrichten

cls
echo.
echo  ============================================================
echo   ZWEITE INSTANZ FUER DEN ECHTGELD-BETRIEB
echo  ============================================================
echo.
echo   Es wird ein neuer Ordner angelegt:
echo     ..\trading_imperium_LIVE
echo.
echo   Darin: der Programmcode (rund 20 MB), eine eigene
echo   Konfiguration mit mode=live und den Deckeln 25 $ je
echo   Order / 200 $ Kapital, und ein frisches Datenverzeichnis.
echo.
echo   NICHT kopiert werden: die Messdaten (808 MB), die
echo   Versionsgeschichte - und die .env mit den Schluesseln.
echo   Die kommt von Hand herueber.
echo.
echo   DIESER Bot hier bleibt unberuehrt und laeuft im
echo   Papiermodus weiter.
echo.
echo  ------------------------------------------------------------
echo.
echo   Zuerst ein Trockenlauf - es wird noch nichts angelegt.
echo.
pause

python live_einrichten.py --pruefen

echo.
echo  ============================================================
echo   JETZT WIRKLICH ANLEGEN?
echo  ============================================================
echo.
echo   Weiter mit einer beliebigen Taste, Abbruch mit Strg+C.
echo.
pause

python live_einrichten.py --anlegen

echo.
pause
