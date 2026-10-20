@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
REM ====================================================================
REM  ALLES_PRUEFEN.bat  -  jede Reparatur der letzten zwei Tage, am Stueck
REM
REM  WARUM ES DIESE DATEI GIBT (13.09.2026)
REM  Am 12./13.09. sind neun Baustellen angefasst worden, jede mit eigenem
REM  Test. Neun Doppelklicks liest niemand durch - und ein Test, den
REM  niemand startet, ist kein Test.
REM
REM  Diese Datei startet sie alle nacheinander und sagt am Ende EINE Zahl.
REM  Sie aendert nichts, liest nur. Der Bot darf weiterlaufen.
REM
REM  Der Ordnername enthaelt Klammern. Ohne die Anfuehrungszeichen um
REM  "%~dp0" bricht cmd genau daran ab.
REM ====================================================================
cd /d "%~dp0"
title Alles pruefen

cls
echo.
echo  ============================================================
echo   ALLE PRUEFUNGEN  -  12. und 13.09.2026
echo  ============================================================
echo.
echo   1. Laeuft alles?               prozess_frische
echo   2. Epoche E9 scharf?           e9_kontrolle
echo   3. Warte-Auftraege             warteauftrag_test  (10 Punkte)
echo   4. Warte-Auftraege, Maschine   warteauftrag_maschine_test (11)
echo   5. entry_score ueberlebt       whitelist_test      (6 Felder)
echo   6. Kleine Reparaturen          reparaturen_test    (13 Punkte)
echo   7. Config-Wachposten           config_wachposten_test (7)
echo   8. Doppelstart-Sperre          startsperre_test    (10 Punkte)
echo   9. Kostenzahlen                core\kosten
echo  10. Marks Formel                mark_gegenprobe     (16 Stufen)
echo  11. Fraktale + Konfluenz        fraktal_konfluenz_test (33)
echo  12. Hold/Recovery               hold_recovery_test  (17 Punkte)
echo  13. Doppelkauf-Schutz           befund68_test       (11 Punkte)
echo.
echo   1 und 2 sind HINWEISE, keine Pruefungen: sie melden, ob ein
echo   Neustart faellig ist. Nach jeder Codeaenderung ist er das.
echo.
echo   Es wird nichts geaendert. Der Bot darf weiterlaufen.
echo.
pause

set FEHLER=0

call :hinweis "1/13  Laufen alle Prozesse mit dem neuen Text?" prozess_frische.py
call :hinweis "2/13  Ist Epoche E9 wirklich scharf?" e9_kontrolle.py
call :lauf "3/13  Warte-Auftraege, Warteschlange allein" warteauftrag_test.py
call :lauf "4/13  Warte-Auftraege durch die echte Maschine" warteauftrag_maschine_test.py
call :lauf "5/13  Ueberlebt entry_score einen Neustart?" whitelist_test.py
call :lauf "6/13  Befunde 41, 95 und 97" reparaturen_test.py
call :lauf "7/13  Config-Wachposten (Befund 97)" config_wachposten_test.py
call :lauf "8/13  Doppelstart-Sperre (Befund 93)" startsperre_test.py
call :lauf "9/13  Stimmen alle Kostenzahlen?" core\kosten.py
call :lauf "10/13 Marks Formel gegen seine Zahlen" mark_gegenprobe.py
call :lauf "11/13 Fraktale + Fibonacci-Konfluenz (Stufe 1)" fraktal_konfluenz_test.py
call :lauf "12/13 Hold/Recovery (Stufe 2)" hold_recovery_test.py
call :lauf "13/13 Doppelkauf-Schutz (Befund 68)" befund68_test.py

echo.
echo  ============================================================
if %FEHLER%==0 (
  echo   ALLE PRUEFUNGEN BESTANDEN
  echo  ============================================================
  echo.
  echo   Zwei Dinge, die trotzdem offen sind:
  echo     - Befund 97: die URSACHE ist nicht gefunden, nur der
  echo       Schaden abgefangen.
  echo     - Befund 104: das Chartlabor kennt Marks zwei Wurzel-
  echo       stufen 0,707 und 0,866 nicht. Dafuer wird die Vorlage
  echo       chartlabor.html vom Laptop gebraucht.
) else (
  echo   %FEHLER% PRUEFUNG^(EN^) DURCHGEFALLEN
  echo  ============================================================
  echo.
  echo   Oben steht bei jeder, woran es lag. Vor dem Weiterarbeiten
  echo   klaeren - ein durchgefallener Test ist ein Befund.
)
echo.
pause
goto :eof

:lauf
echo.
echo  ------------------------------------------------------------
echo   %~1
echo  ------------------------------------------------------------
python %2 < nul
if errorlevel 1 (
  echo   ^>^> DURCHGEFALLEN: %2
  set /a FEHLER+=1
)
goto :eof

REM  Ein HINWEIS ist keine Pruefung. prozess_frische.py und
REM  e9_kontrolle.py melden "Neustart faellig", sobald seit dem
REM  Bot-Start eine Datei geaendert wurde - das ist dann RICHTIG
REM  und kein Fehler. Wuerden sie als Durchfall zaehlen, stuende
REM  am Ende nach jeder Arbeit eine rote Zahl, und eine Warnung,
REM  die immer kommt, liest nach drei Tagen niemand mehr.
:hinweis
echo.
echo  ------------------------------------------------------------
echo   %~1   (Hinweis, keine Pruefung)
echo  ------------------------------------------------------------
python %2 < nul
if errorlevel 1 echo   ^>^> Es ist ein Neustart faellig. Das ist nach
if errorlevel 1 echo      Codeaenderungen normal und kein Fehler.
goto :eof
