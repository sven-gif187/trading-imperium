@echo off
REM ===========================================================
REM  Prueft, warum keine Telegram-Nachricht ankommt.
REM  Aendert nichts - liest nur die .env und fragt Telegram.
REM  Der Ordnername enthaelt Klammern, deshalb die
REM  Anfuehrungszeichen um den Pfad.
REM ===========================================================
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
python telegram_pruefen.py
