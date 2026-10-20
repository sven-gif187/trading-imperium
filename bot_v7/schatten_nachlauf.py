#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  SCHATTEN-NACHLAUF - haette der Kauf in GIER getragen?
================================================================
Angelegt 20.08.2026 auf Svens Auftrag: "ich hoffe wir haben alle
Instrumente die wir zur Datensammlung brauchen, das wir daraus
lernen koennen."

Nachgesehen statt gehofft - und genau eines fehlte.

DIE LUECKE
----------
Das Schatten-Universum rechnet stuendlich fuer 18 Muenzen dieselbe
Einstiegs-Punktzahl aus wie der Bot. Es speichert Punktzahl, Preis,
Marktzustand, Zyklus, Fear&Greed, Spanne und Kosten.

Was es NICHT speichert: was danach passierte.

    schatten_universum.db, 809 Signale
      davon in Angst (DCA-Pfad offen)  152   19 %
      davon in Gier  (DCA-Pfad ZU)     657   81 %

Damit liess sich sagen, WIE OFT der Bot in Gier haette kaufen
wollen - aber nicht, ob es sich gelohnt haette. Genau das ist die
Frage hinter Befund 64: der Hauptkaufpfad braucht `fg < 30` und
schliesst damit, wenn der Kurs steigt (Zusammenhang Preis/Gier
+0,85). Ob ein zweiter Pfad fuer steigende Maerkte getragen
haette, war schlicht ungemessen.

WAS DIESES WERKZEUG TUT
-----------------------
Es traegt jedes Schatten-Signal als Ereignis der Art `schatten` in
data_store/nachlauf.db ein. Danach fuellt das VORHANDENE Werkzeug
die Kurse 1/4/24/48 Stunden spaeter:

    python schatten_nachlauf.py --schreiben
    python nachlauf_rueckwirkend.py --schreiben

Bewusst kein zweiter Messapparat. Dieselbe Tabelle, dieselbe Regel
("erste FERTIGE Kerze bei oder nach dem Zielzeitpunkt"), dieselbe
Gegenprobe. Zwei Wege zur selben Zahl waeren zwei Gelegenheiten,
sich zu widersprechen - dieser Fehler ist in diesem Projekt schon
oft genug vorgekommen.

Und es wirkt RUECKWIRKEND: die 809 bereits gesammelten Signale
bekommen ihre Nachlaufwerte aus historischen Kerzen, genau wie am
19.08. die 437 verlorenen Ausstiege.

WAS ES NICHT TUT
----------------
Kein Eingriff in den Bot, kein Handel, keine Verhaltensaenderung.
Es schreibt Messwerte. Freeze-vertraeglich.

Es beantwortet auch NICHT "haette das Depot mehr verdient" - im
Schatten gibt es keine Kapitalkonkurrenz. Es beantwortet: "haette
ein Kauf bei dieser Punktzahl, in dieser Marktlage, nach Kosten
getragen?"

BENUTZUNG
---------
    python schatten_nachlauf.py               Probelauf
    python schatten_nachlauf.py --schreiben   eintragen
    python schatten_nachlauf.py --auswerten   Ergebnis ansehen
    python schatten_nachlauf.py --selbsttest  Gegentest
================================================================
"""
import os
import sys
import sqlite3
import argparse
import collections

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))
SU = os.path.join(HIER, "data_store", "schatten_universum.db")
NL_DB = os.path.join(HIER, "data_store", "nachlauf.db")
K = 0.505
NL = chr(10)


def _lesen(pfad):
    if not os.path.exists(pfad):
        return None
    return sqlite3.connect("file:" + pfad.replace("\\", "/") + "?mode=ro",
                           uri=True, timeout=10)


def uebertragen(schreiben=False, still=False):
    """Schatten-Signale als Ereignisse in nachlauf.db eintragen.

    still=True fuer den stuendlichen Lauf aus schatten_universum.py:
    dort soll nur EINE Zeile im Log stehen, nicht zehn. Ein Werkzeug,
    das jede Stunde zehn Zeilen schreibt, macht das Log unlesbar - und
    ein unlesbares Log liest niemand mehr.
    """
    def _sag(*x):
        if not still:
            print(*x)
    su = _lesen(SU)
    if su is None:
        _sag("schatten_universum.db fehlt.")
        return 1
    signale = su.execute(
        "SELECT id, ts_utc, muenze, preis, score, fear_greed, regime, zyklus "
        "FROM signale WHERE preis > 0 ORDER BY ts_utc").fetchall()
    su.close()

    con = sqlite3.connect(NL_DB, timeout=30)
    schon = {r[0] for r in con.execute(
        "SELECT kennung FROM nachlauf WHERE art='schatten'")}

    _sag("=" * 74)
    _sag("SCHATTEN-SIGNALE IN DIE NACHLAUF-MESSUNG UEBERNEHMEN")
    _sag("=" * 74)
    _sag(NL + "  " + str(len(signale)) + " Signale im Schatten-Universum")
    _sag("  " + str(len(schon)) + " davon schon uebernommen")

    neu = 0
    for sid, ts, muenze, preis, score, fg, regime, zyklus in signale:
        kennung = "schatten_" + str(sid)
        if kennung in schon:
            continue
        # Der Grund traegt die Merkmale, nach denen spaeter sortiert wird:
        # Punktzahl, Gier-Stand, Marktzustand. So bleibt die Auswertung
        # moeglich, ohne die Tabelle um Spalten zu erweitern, die der
        # laufende Bot nicht kennt.
        grund = ("Schatten-Signal | Score " + format(score or 0, ".1f")
                 + " | F&G " + str(fg if fg is not None else "?")
                 + " | " + str(regime or "?") + " | " + str(zyklus or "?"))
        if schreiben:
            con.execute(
                "INSERT OR IGNORE INTO nachlauf (art,kennung,ts_utc,muenze,"
                "preis,grund,vollstaendig,quelle) VALUES (?,?,?,?,?,?,0,?)",
                ("schatten", kennung, ts, muenze, float(preis), grund,
                 "nachgetragen"))
        neu += 1
    if schreiben:
        con.commit()
    con.close()

    _sag("  " + str(neu) + " neu " + ("uebernommen" if schreiben
                                       else "zu uebernehmen"))
    if not schreiben:
        _sag(NL + "  PROBELAUF - mit --schreiben wird es eingetragen.")
    else:
        _sag(NL + "  JETZT die Kurse nachtragen:")
        _sag("      python nachlauf_rueckwirkend.py --schreiben")
    return 0


def auswerten():
    """Die Frage, um die es geht: traegt ein Kauf in GIER nach Kosten?"""
    con = _lesen(NL_DB)
    if con is None:
        print("nachlauf.db fehlt.")
        return 1
    rows = con.execute(
        "SELECT grund, ts_utc, muenze, r1h, r4h, r24h, r48h FROM nachlauf "
        "WHERE art='schatten' AND r4h IS NOT NULL").fetchall()
    con.close()

    print("=" * 82)
    print(" HAETTE EIN KAUF GETRAGEN? - Schatten-Signale nach Kosten")
    print("=" * 82)
    if not rows:
        print(NL + "  Noch keine Nachlaufwerte. Zwei Schritte:")
        print("      python schatten_nachlauf.py --schreiben")
        print("      python nachlauf_rueckwirkend.py --schreiben")
        return 1

    def merkmal(grund, schluessel):
        for teil in (grund or "").split("|"):
            teil = teil.strip()
            if teil.startswith(schluessel):
                return teil[len(schluessel):].strip()
        return "?"

    def gier(grund):
        f = merkmal(grund, "F&G")
        try:
            return "Angst (unter 30)" if int(f) < 30 else "Gier (30 und mehr)"
        except Exception:
            return "unbekannt"

    def stufe(grund):
        try:
            s = float(merkmal(grund, "Score"))
        except Exception:
            return "?"
        return ("Score 3-4" if s < 5 else "Score 5-6" if s < 7
                else "Score 7-8" if s < 9 else "Score 9-10")

    from datetime import datetime, timezone

    def zeige(titel, schluessel):
        g = collections.defaultdict(list)
        for grund, ts, muenze, r1, r4, r24, r48 in rows:
            g[schluessel(grund)].append((r1, r4, r24, r48, ts, muenze))
        print(NL + "  " + titel)
        print("  " + "-" * 78)
        print("  " + "".ljust(22) + "Faelle".rjust(8) + "Tage".rjust(6)
              + "+1h".rjust(9) + "+4h".rjust(9) + "+24h".rjust(9)
              + "+48h".rjust(9))
        for name in sorted(g):
            v = g[name]
            tage = len({str(x[4])[:10] for x in v})

            def mw(i):
                w = [x[i] for x in v if x[i] is not None]
                return (sum(w) / len(w) - K) if w else None

            def f(x):
                return "     -- " if x is None else format(x, "+8.2f")
            print("  " + name.ljust(22) + str(len(v)).rjust(8)
                  + str(tage).rjust(6) + f(mw(0)) + f(mw(1))
                  + f(mw(2)) + f(mw(3)))

    zeige("Nach Marktstimmung - DAS ist die Frage aus Befund 64:", gier)
    zeige("Nach Punktzahl:", stufe)

    print(NL + "  Alle Werte NACH Kosten (" + str(K) + " % je Runde).")
    print("  Positiv heisst: ein Kauf haette sich gelohnt.")
    print(NL + "  ACHTUNG - was hier NICHT steht:")
    print("    * Kapitalkonkurrenz. Im Schatten ist jede Gelegenheit")
    print("      nehmbar, in Wirklichkeit sind hoechstens drei Positionen")
    print("      offen. Die Zahl ueberschaetzt, wie oft man zugegriffen haette.")
    print("    * Der Zeitraum. Faellt er in eine Aufwaertswoche, sieht JEDER")
    print("      Kauf gut aus. Die Spalte 'Tage' sagt, wie breit gestreut")
    print("      die Faelle sind - unter 25 Tagen traegt keine Zeile ein Urteil.")
    return 0


def selbsttest():
    fehler = 0
    print("=" * 70)
    print("SELBSTTEST")
    print("=" * 70)
    su = _lesen(SU)
    n = su.execute("SELECT COUNT(*) FROM signale WHERE preis > 0").fetchone()[0]
    su.close()
    con = _lesen(NL_DB)
    ueber = con.execute("SELECT COUNT(*) FROM nachlauf "
                        "WHERE art='schatten'").fetchone()[0]
    doppelt = con.execute(
        "SELECT COUNT(*) FROM (SELECT kennung FROM nachlauf "
        "WHERE art='schatten' GROUP BY kennung HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    andere = con.execute("SELECT COUNT(*) FROM nachlauf "
                         "WHERE art IN ('exit','blockade')").fetchone()[0]
    con.close()

    faelle = [
        ("Signale mit Preis im Schatten", n > 0, str(n)),
        ("keine Kennung doppelt", doppelt == 0, str(doppelt) + " doppelt"),
        ("uebernommen <= vorhanden", ueber <= n,
         str(ueber) + " von " + str(n)),
        ("bestehende Messungen unberuehrt", andere > 4000,
         str(andere) + " exit/blockade"),
    ]
    for name, ok, wert in faelle:
        print("  " + ("OK  " if ok else "FEHL") + "  " + name.ljust(34) + wert)
        if not ok:
            fehler += 1

    print(NL + "  Gegenprobe: traegt der Grund die Merkmale?")
    con = _lesen(NL_DB)
    r = con.execute("SELECT grund FROM nachlauf WHERE art='schatten' "
                    "LIMIT 1").fetchone()
    con.close()
    if r:
        ok = all(x in r[0] for x in ("Score", "F&G"))
        print("    " + ("OK  " if ok else "FEHL") + "  " + r[0][:62])
        if not ok:
            fehler += 1
    else:
        print("    (noch nichts uebernommen - mit --schreiben nachholen)")

    print(NL + ("SELBSTTEST BESTANDEN" if not fehler
                else str(fehler) + " FEHLER"))
    return 1 if fehler else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--schreiben", action="store_true")
    p.add_argument("--auswerten", action="store_true")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    if a.selbsttest:
        sys.exit(selbsttest())
    if a.auswerten:
        sys.exit(auswerten())
    sys.exit(uebertragen(schreiben=a.schreiben))
