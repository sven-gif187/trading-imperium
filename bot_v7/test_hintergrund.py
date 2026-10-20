# -*- coding: utf-8 -*-
"""Test fuer core/hintergrund.py (Hintergrundjobs ohne Fenster, 11.08.2026).

Prueft genau das, was in Aufgabe 7g verlangt ist:
  - Job startet erfolgreich
  - Log wird geschrieben
  - ein ERZWUNGENER Fehler ist im Log sichtbar (stderr wird nicht verworfen)
  - doppelter Start wird verhindert
  - sauberer Abbruch moeglich (Timeout)
  - Status landet in der Telemetrie-Tabelle `jobs`

Laeuft in einem Wegwerf-Ordner. Der Bot darf dabei laufen.

Aufruf:  python test_hintergrund.py
"""
import os
import shutil
import sqlite3
import sys
import tempfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

import core.hintergrund as hg                     # noqa: E402
from core.telemetrie import Telemetrie            # noqa: E402

fehler = []


def pruefe(bedingung, text):
    print(("  OK   " if bedingung else "  FEHLT") + "  " + text)
    if not bedingung:
        fehler.append(text)


def main():
    ordner = tempfile.mkdtemp(prefix="hintergrund_test_")
    original_log = hg.LOG_ORDNER
    original_tickets = hg.TICKETS
    hg.LOG_ORDNER = os.path.join(ordner, "jobs")
    hg.TICKETS = os.path.join(ordner, "tickets.txt")
    try:
        tel = Telemetrie(db_datei=os.path.join(ordner, "t.db"))

        print("\n1) Erfolgreicher Job")
        skript = os.path.join(ordner, "gut.py")
        with open(skript, "w", encoding="utf-8") as f:
            f.write("print('ich habe gearbeitet')\n")
        code = hg.starte_still("test_gut", [sys.executable, skript],
                               cwd=ordner, telemetrie=tel, timeout=60)
        log = os.path.join(hg.LOG_ORDNER, "test_gut.log")
        inhalt = open(log, encoding="utf-8", errors="replace").read()
        pruefe(code == 0, "Exit-Code 0")
        pruefe(os.path.exists(log), "Logdatei angelegt")
        pruefe("ich habe gearbeitet" in inhalt, "Ausgabe steht im Log")
        pruefe("START" in inhalt and "ENDE" in inhalt, "Start und Ende vermerkt")

        print("\n2) Erzwungener Fehler MUSS sichtbar sein")
        kaputt = os.path.join(ordner, "kaputt.py")
        with open(kaputt, "w", encoding="utf-8") as f:
            f.write("raise RuntimeError('ABSICHTLICH KAPUTT')\n")
        code = hg.starte_still("test_kaputt", [sys.executable, kaputt],
                               cwd=ordner, telemetrie=tel, timeout=60)
        inhalt = open(os.path.join(hg.LOG_ORDNER, "test_kaputt.log"),
                      encoding="utf-8", errors="replace").read()
        pruefe(code != 0, "Exit-Code ungleich 0")
        pruefe("ABSICHTLICH KAPUTT" in inhalt, "Fehlertext im Log (stderr nicht verworfen)")
        pruefe("Traceback" in inhalt, "vollstaendiger Stacktrace im Log")
        pruefe(os.path.exists(hg.TICKETS), "Fehlschlag als Ticket festgehalten")
        pruefe("test_kaputt" in open(hg.TICKETS, encoding="utf-8").read(),
               "Ticket nennt den Job")

        print("\n3) Doppelter Start wird verhindert")
        with hg.Sperre("test_doppelt") as s:
            pruefe(s.gehalten, "erste Sperre wird gehalten")
            code = hg.starte_still("test_doppelt", [sys.executable, skript],
                                   cwd=ordner, telemetrie=tel, timeout=60)
            pruefe(code == 0, "zweiter Start bricht sauber ab (0, kein Fehler)")
            inhalt = open(os.path.join(hg.LOG_ORDNER, "test_doppelt.log"),
                          encoding="utf-8", errors="replace").read()
            pruefe("UEBERSPRUNGEN" in inhalt, "Ueberspringen steht im Log")

        print("\n4) Sauberer Abbruch bei Zeitueberschreitung")
        lang = os.path.join(ordner, "lang.py")
        with open(lang, "w", encoding="utf-8") as f:
            f.write("import time\ntime.sleep(30)\n")
        code = hg.starte_still("test_timeout", [sys.executable, lang],
                               cwd=ordner, telemetrie=tel, timeout=2)
        inhalt = open(os.path.join(hg.LOG_ORDNER, "test_timeout.log"),
                      encoding="utf-8", errors="replace").read()
        pruefe(code == -1, "Abbruch meldet -1")
        pruefe("ABBRUCH" in inhalt, "Abbruch steht im Log")

        print("\n5) Status in der Telemetrie")
        con = sqlite3.connect(os.path.join(ordner, "t.db"))
        zeilen = con.execute("SELECT job_name,status,exit_code,pid,laufzeit_sek,"
                             "logpfad FROM jobs ORDER BY id").fetchall()
        con.close()
        namen = {z[0]: z for z in zeilen}
        pruefe(len(zeilen) >= 4, f"{len(zeilen)} Job-Zeilen geschrieben")
        pruefe(namen.get("test_gut", ("", ""))[1] == "OK", "guter Job als OK")
        pruefe(namen.get("test_kaputt", ("", ""))[1] == "FEHLER", "kaputter Job als FEHLER")
        pruefe(namen.get("test_doppelt", ("", ""))[1] == "UEBERSPRUNGEN",
               "Doppelstart als UEBERSPRUNGEN")
        pruefe(namen.get("test_timeout", ("", ""))[1] == "ABGEBROCHEN",
               "Timeout als ABGEBROCHEN")
        g = namen.get("test_gut")
        pruefe(g and g[3] and g[3] > 0, "PID festgehalten")
        pruefe(g and g[4] is not None, "Laufzeit festgehalten")
        pruefe(g and g[5], "Logpfad festgehalten")

        print("\n6) Gesundheitsampel")
        amp = {a["job"]: a for a in tel.job_gesundheit()}
        pruefe("test_gut" in amp, "guter Job in der Ampel")
        pruefe(amp["test_kaputt"]["fehler"] == 1, "Fehlerzahl stimmt")
        pruefe(amp["test_gut"]["letzter_erfolg"] is not None, "letzter Erfolg vermerkt")

        print("\n7) Kein Fenster-Flag fehlt")
        pruefe(hg.CREATE_NO_WINDOW == 0x08000000, "CREATE_NO_WINDOW gesetzt")

        print("\n8) Prozesspruefung (Doppelstart-Sperre haengt daran)")
        pruefe(hg._laeuft_noch(os.getpid()) is True, "eigene PID gilt als laufend")
        pruefe(hg._laeuft_noch(999999) is False, "Fantasie-PID gilt als tot")

        print("\n10) Erwartete Exit-Codes loesen KEIN Ticket aus")
        # capture_daemon endet mit 3, wenn schon eine Instanz laeuft - das ist
        # der Normalfall alle 10 Minuten, kein Fehler.
        drei = os.path.join(ordner, "code3.py")
        with open(drei, "w", encoding="utf-8") as f:
            f.write("import sys\nprint('laeuft schon')\nsys.exit(3)\n")
        vorher = (open(hg.TICKETS, encoding="utf-8").read()
                  if os.path.exists(hg.TICKETS) else "")
        code = hg.starte_still("test_code3", [sys.executable, drei],
                               cwd=ordner, telemetrie=tel, timeout=60,
                               ok_codes=(0, 3))
        nachher = (open(hg.TICKETS, encoding="utf-8").read()
                   if os.path.exists(hg.TICKETS) else "")
        pruefe(code == 3, "Exit-Code 3 wird durchgereicht")
        pruefe(vorher == nachher, "KEIN neues Ticket fuer erwarteten Code")
        con = sqlite3.connect(os.path.join(ordner, "t.db"))
        st, ec = con.execute("SELECT status,exit_code FROM jobs "
                             "WHERE job_name='test_code3'").fetchone()
        con.close()
        pruefe(st == "OK", "Status OK statt FEHLER")
        pruefe(ec == 3, "echter Exit-Code bleibt sichtbar (3, nicht 0)")
        # Gegenprobe: ohne ok_codes ist derselbe Code sehr wohl ein Fehler
        code = hg.starte_still("test_code3b", [sys.executable, drei],
                               cwd=ordner, telemetrie=tel, timeout=60)
        pruefe("test_code3b" in open(hg.TICKETS, encoding="utf-8").read(),
               "ohne ok_codes erzeugt derselbe Code ein Ticket")

        print("\n9) Verwaiste LAEUFT-Zeilen werden geschlossen")
        zid = tel.job_start("test_verwaist", 999999, "x.log", "nix")
        con = sqlite3.connect(os.path.join(ordner, "t.db"))
        vorher = con.execute("SELECT status FROM jobs WHERE id=?", (zid,)).fetchone()[0]
        con.close()
        anzahl = tel.jobs_aufraeumen()
        con = sqlite3.connect(os.path.join(ordner, "t.db"))
        nachher = con.execute("SELECT status FROM jobs WHERE id=?", (zid,)).fetchone()[0]
        con.close()
        pruefe(vorher == "LAEUFT", "Zeile stand auf LAEUFT")
        pruefe(anzahl >= 1, f"{anzahl} verwaiste Zeile(n) erkannt")
        pruefe(nachher == "ABGEBROCHEN", "Zeile jetzt ABGEBROCHEN")

    finally:
        hg.LOG_ORDNER = original_log
        hg.TICKETS = original_tickets
        shutil.rmtree(ordner, ignore_errors=True)

    print("\n" + "=" * 52)
    if fehler:
        print("FEHLGESCHLAGEN: %d" % len(fehler))
        for f in fehler:
            print("   -", f)
        return 1
    print("ALLE TESTS BESTANDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
