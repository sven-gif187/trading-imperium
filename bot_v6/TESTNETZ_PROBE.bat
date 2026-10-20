@echo off
REM ============================================================
REM  TESTNETZ-PROBE  -  einfach doppelklicken
REM ============================================================
REM  Prueft den Order-Pfad an einer ECHTEN Boerse mit SPIELGELD.
REM  Kein Euro im Feuer, kein Eingriff in den laufenden Bot.
REM
REM  Beim ersten Mal brauchst du Testnetz-Schluessel:
REM    1. https://testnet.binance.vision
REM    2. mit GitHub anmelden
REM    3. "Generate HMAC_SHA256 Key"
REM    4. in die Datei .env eintragen:
REM         BINANCE_TESTNET_KEY=...
REM         BINANCE_TESTNET_SECRET=...
REM
REM  Das sind EIGENE Testnetz-Schluessel - NICHT die echten.
REM ============================================================
cd /d "%~dp0"
echo.
echo   Schritt 1 von 2 - Verbindung pruefen
echo   ============================================================
python testnetz_probe.py --pruefen
echo.
echo   ============================================================
echo   Sieht das oben gut aus? Dann die sechs Pruefungen starten:
echo       python testnetz_probe.py --echt
echo   ============================================================
echo.
pause
