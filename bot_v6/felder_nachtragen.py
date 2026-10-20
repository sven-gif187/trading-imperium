# -*- coding: utf-8 -*-
"""Traegt vier Analysefelder in das Handelsjournal nach.

WORUM ES GEHT (Befund 88)
-------------------------
Zwei Schreibwege schreiben einen Verkauf, und jeder schreibt nur seine
Haelfte der Felder. Vier davon lassen sich aus `positionsverlauf.db`
nachtragen:

    position_id      <- positionen.pos_id
    haltedauer_min   <- geschlossen minus eroeffnet
    entry_strategie  <- positionen.strategie
    entry_score      <- positionen.score

Die drei uebrigen (`stop_initial`, `trailing_stop_pct`, `decision_id`)
lassen sich NICHT nachtragen - sie stehen am Kauf, aber es gibt keine
belastbare Verbindung Verkauf -> Kauf. Siehe Befund 88.

DIE ZUORDNUNG
-------------
Uebernommen aus `vollstaendigkeit.py`, wo sie sich bewaehrt hat:
gleiche Muenze, Schlusszeit innerhalb von 600 Sekunden, und nur wenn es
GENAU EINEN Kandidaten gibt. Gaebe es zwei, waere das Ergebnis geraten.

    Warum nicht einfach der aelteste offene Kauf (FIFO)? Weil das am
    29.08. ausprobiert wurde und falsch war: Positionen werden per
    Nachkauf aufgebaut und teilweise verkauft, die Mengen passen nicht
    (Verkauf SOL 1,357 gegen Kauf 0,714). Die Zuordnung meldete
    trotzdem 62 von 62 - weil immer irgendein Kauf uebrigbleibt.

WAS DIESES PROGRAMM NICHT TUT
-----------------------------
  - Es ueberschreibt NIE einen vorhandenen Wert. Nur `None` wird gefuellt.
  - Es fasst den Bot nicht an, aendert kein Verhalten, keine Regel.
  - Ohne `--schreiben` aendert es gar nichts, sondern zeigt nur, was es
    tun WUERDE.

JEDER NACHGETRAGENE WERT WIRD MARKIERT
--------------------------------------
Der Eintrag bekommt ein Feld `_nachgetragen` mit Datum und der Liste der
gefuellten Felder. Ein rekonstruierter Wert darf nicht wie ein gemessener
aussehen - sonst weiss in drei Monaten niemand mehr, was echt war.

DER BOT LAEUFT WAEHRENDDESSEN
-----------------------------
`trades_v5.json` wird vom laufenden Bot beschrieben. Deshalb:
  1. Sicherung anlegen
  2. Datei lesen, hoechste `_id` merken
  3. Aenderungen vorbereiten
  4. VOR dem Schreiben erneut lesen: sind neue Eintraege dazugekommen,
     werden sie uebernommen statt ueberschrieben
  5. Erst in eine temporaere Datei schreiben, dann umbenennen

    python felder_nachtragen.py                 nur zeigen (Probelauf)
    python felder_nachtragen.py --schreiben     wirklich eintragen
    python felder_nachtragen.py --selbsttest
"""
import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime

STORE = "data_store"
JOURNAL = os.path.join(STORE, "trades_v5.json")
POSITIONEN = os.path.join(STORE, "positionsverlauf.db")
TOLERANZ_SEK = 600          # wie in vollstaendigkeit.py

FELDER = ("position_id", "haltedauer_min", "entry_strategie", "entry_score")


def _dt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def lade_positionen(pfad=POSITIONEN):
    if not os.path.isfile(pfad):
        return []
    c = sqlite3.connect(pfad)
    try:
        # quelle='echt' - die Tabelle enthaelt auch SCHATTEN-Positionen
        # (58 echt, 28 schatten). Ohne diesen Filter koennte ein echter
        # Verkauf einer Schattenposition zugeordnet werden. Gemessen am
        # 29.08. passiert das derzeit nicht - die Schlusszeiten liegen
        # auseinander -, aber darauf will man sich nicht verlassen.
        rows = c.execute(
            "SELECT pos_id,muenze,eroeffnet,einstieg,menge,strategie,score,"
            "geschlossen,quelle FROM positionen "
            "WHERE geschlossen IS NOT NULL AND quelle='echt'").fetchall()
    except Exception:
        return []
    finally:
        c.close()
    return [dict(zip(["pos_id", "muenze", "eroeffnet", "einstieg", "menge",
                      "strategie", "score", "geschlossen", "quelle"], r)) for r in rows]


def zuordnen(verkauf, positionen):
    """Genau eine Position - oder nichts. Nie raten."""
    tv = _dt(verkauf.get("time"))
    if not tv:
        return None, False
    treffer = []
    for p in positionen:
        if p["muenze"] != verkauf.get("coin"):
            continue
        tp = _dt(p["geschlossen"])
        if not tp:
            continue
        if abs((tv - tp).total_seconds()) <= TOLERANZ_SEK:
            treffer.append(p)
    if not treffer:
        return None, False
    return treffer[0], len(treffer) == 1


def haltedauer(pos):
    """Minuten zwischen Eroeffnen und Schliessen - oder None."""
    a, b = _dt(pos.get("eroeffnet")), _dt(pos.get("geschlossen"))
    if not a or not b:
        return None
    m = (b - a).total_seconds() / 60.0
    return round(m, 1) if m >= 0 else None


def _echt(w):
    """Leere Zeichenkette ist KEIN Wert.

    [29.08.2026] Im Probelauf haette `entry_strategie` bei 12 Verkaeufen
    eine LEERE Zeichenkette bekommen - `positionen.strategie` ist bei
    allen 58 echten Positionen leer, gefuellt ist sie nur bei den 28
    Schattenpositionen. Das Feld haette danach als "vorhanden" gezaehlt,
    ohne etwas zu enthalten: die Vollstaendigkeitsstatistik waere
    geschoent worden, und zwar von dem Werkzeug, das sie verbessern soll.
    """
    if w is None:
        return None
    if isinstance(w, str) and not w.strip():
        return None
    return w


def werte_aus(pos):
    """Was diese Position wirklich liefern kann - Leeres zaehlt nicht."""
    return {
        "position_id": _echt(pos.get("pos_id")),
        "haltedauer_min": _echt(haltedauer(pos)),
        "entry_strategie": _echt(pos.get("strategie")),
        "entry_score": _echt(pos.get("score")),
    }


def planen(journal, positionen):
    """Was waere zu tun? Gibt (plan, statistik) zurueck.

    plan: {_id: {feld: wert}}  -  nur fehlende Felder, nur eindeutige
    Zuordnungen.
    """
    plan = {}
    stat = {"verkaeufe": 0, "ohne_position": 0, "mehrdeutig": 0,
            "nichts_zu_tun": 0, "je_feld": {f: 0 for f in FELDER}}
    for t in journal:
        if t.get("type") != "SELL":
            continue
        stat["verkaeufe"] += 1
        pos, eindeutig = zuordnen(t, positionen)
        if pos is None:
            stat["ohne_position"] += 1
            continue
        if not eindeutig:
            stat["mehrdeutig"] += 1
            continue
        neu = {}
        moeglich = werte_aus(pos)
        for f in FELDER:
            # NIE ueberschreiben. Nur was fehlt.
            if t.get(f) is None and moeglich.get(f) is not None:
                neu[f] = moeglich[f]
                stat["je_feld"][f] += 1
        if neu:
            plan[t.get("_id")] = neu
        else:
            stat["nichts_zu_tun"] += 1
    return plan, stat


def anwenden(journal, plan, heute):
    """Traegt den Plan in die Liste ein. Markiert jeden Eintrag."""
    n = 0
    for t in journal:
        neu = plan.get(t.get("_id"))
        if not neu:
            continue
        for f, w in neu.items():
            t[f] = w
        # Ein rekonstruierter Wert darf nicht wie ein gemessener aussehen.
        t["_nachgetragen"] = {"am": heute, "felder": sorted(neu.keys()),
                              "quelle": "positionsverlauf.db",
                              "befund": 88}
        n += 1
    return n


def schreiben(journal_neu, pfad=JOURNAL):
    """Schreibt sicher - der Bot haengt waehrenddessen weiter an.

    Vor dem Ersetzen wird die Datei ERNEUT gelesen. Kamen dort neue
    Eintraege dazu, werden sie uebernommen. Sonst waere jeder Handel,
    den der Bot in der Zwischenzeit geschrieben hat, verloren.
    """
    aktuell = json.load(open(pfad, encoding="utf-8"))
    bekannte = {t.get("_id") for t in journal_neu}
    dazu = [t for t in aktuell if t.get("_id") not in bekannte]
    if dazu:
        journal_neu = journal_neu + dazu
    journal_neu.sort(key=lambda t: (t.get("_id") is None, t.get("_id") or 0))

    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(journal_neu, f, ensure_ascii=False, indent=1)
    os.replace(tmp, pfad)
    return len(dazu)


def bot_laeuft():
    """Laeuft app.py gerade? Dann darf NICHT geschrieben werden.

    [29.08.2026 - die Lehre aus dem ersten Versuch]
    `TradeJournal` (core/state_store.py:108) laedt trades_v5.json EINMAL
    beim Start in den Speicher und schreibt bei jedem Speichern die ganze
    Datei neu. Eine Aenderung von aussen ist damit beim naechsten Handel
    weg - ohne Fehlermeldung, ohne Spur.

    Gemessen: Schreibung um 16:55:17, der Bot ueberschrieb sie um
    16:55:58. Einundvierzig Sekunden. Die Gegenprobe unmittelbar nach dem
    Schreiben meldete noch Erfolg - erst der zweite Blick zeigte, dass
    nichts geblieben war.

    Deshalb diese Sperre. Ein Nachtrag, der still verschwindet, ist
    schlimmer als einer, der gar nicht stattfindet: man haelt die Luecke
    fuer geschlossen.
    """
    try:
        import subprocess
        r = subprocess.run(
            # [29.08.2026 korrigiert] Der Filter "Name like 'python%'" ist
            # NICHT kosmetisch. Ohne ihn fand die Pruefung SICH SELBST:
            # die Befehlszeile des powershell.exe, das sie ausfuehrt,
            # enthaelt die Zeichenkette "app.py" - sie steht ja im
            # Suchmuster. Ergebnis: "der Bot laeuft" auch dann, wenn er
            # laengst zu war. Sven ist genau darauf hereingefallen.
            ["powershell", "-NoProfile", "-Command",
             "if (Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
             "Where-Object { $_.CommandLine -like '*app.py*' }) "
             "{ exit 1 } else { exit 0 }"],
            capture_output=True, timeout=30)
        return r.returncode == 1
    except Exception:
        return None          # unbekannt - lieber warnen als schweigen


def bericht(plan, stat, journal):
    print("=" * 76)
    print(" VIER ANALYSEFELDER NACHTRAGEN  (Befund 88)")
    print("=" * 76)
    print("  Verkaeufe im Journal          : %d" % stat["verkaeufe"])
    print("  ohne passende Position        : %d" % stat["ohne_position"])
    print("  mehrdeutig (wird uebergangen) : %d" % stat["mehrdeutig"])
    print("  schon vollstaendig            : %d" % stat["nichts_zu_tun"])
    print("  zu ergaenzen                  : %d" % len(plan))
    print()
    print("  Feld                 wird gefuellt   vorher vorhanden")
    print("  " + "-" * 54)
    for f in FELDER:
        vorher = sum(1 for t in journal
                     if t.get("type") == "SELL" and t.get(f) is not None)
        print("    %-18s %8d          %8d von %d"
              % (f, stat["je_feld"][f], vorher, stat["verkaeufe"]))
    print("  " + "-" * 54)
    print()
    if plan:
        print("  Beispiele (die ersten drei):")
        for i, (pid, neu) in enumerate(sorted(plan.items())[:3]):
            t = next((x for x in journal if x.get("_id") == pid), {})
            print("    _id %-5s %s %s" % (pid, t.get("time", "")[:16], t.get("coin", "")))
            for f, w in sorted(neu.items()):
                print("        %-18s -> %s" % (f, w))
    print("=" * 76)


def lauf(wirklich):
    if not os.path.isfile(JOURNAL):
        print("FEHLER: %s fehlt." % JOURNAL)
        return 1
    positionen = lade_positionen()
    if not positionen:
        print("FEHLER: keine geschlossenen Positionen in %s." % POSITIONEN)
        return 1
    journal = json.load(open(JOURNAL, encoding="utf-8"))
    print("  Journal: %d Eintraege   Positionen: %d geschlossen\n"
          % (len(journal), len(positionen)))

    plan, stat = planen(journal, positionen)
    bericht(plan, stat, journal)

    if not plan:
        print("\n  Nichts zu tun.")
        return 0
    if not wirklich:
        print("\n  PROBELAUF - es wurde NICHTS geaendert.")
        print("  Zum wirklichen Eintragen:  python felder_nachtragen.py --schreiben")
        return 0

    laeuft = bot_laeuft()
    if laeuft is None:
        print("\n  WARNUNG: Konnte nicht pruefen, ob der Bot laeuft.")
        print("  Wenn er laeuft, wird dieser Nachtrag binnen Sekunden ueberschrieben.")
        return 1
    if laeuft:
        print("\n" + "=" * 76)
        print("  ABGEBROCHEN - der Bot laeuft.")
        print("=" * 76)
        print("  app.py haelt das Journal im Arbeitsspeicher und schreibt die")
        print("  ganze Datei neu, sobald ein Handel stattfindet. Ein Nachtrag")
        print("  waere binnen Sekunden weg - lautlos.")
        print()
        print("  So geht es:")
        print("    1. Bot beenden")
        print("    2. python felder_nachtragen.py --schreiben")
        print("    3. Bot wieder starten - er liest die ergaenzte Datei ein")
        print("=" * 76)
        return 1

    heute = datetime.now().strftime("%Y-%m-%d")
    sich = JOURNAL + ".vor_nachtrag_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(JOURNAL, sich)
    print("\n  Sicherung: %s" % os.path.basename(sich))

    n = anwenden(journal, plan, heute)
    dazu = schreiben(journal)
    print("  %d Eintraege ergaenzt." % n)
    if dazu:
        print("  %d Eintraege kamen waehrenddessen vom Bot dazu - uebernommen." % dazu)

    # Gegenprobe: neu lesen und nachzaehlen
    kontrolle = json.load(open(JOURNAL, encoding="utf-8"))
    print("\n  GEGENPROBE nach dem Schreiben:")
    print("    Eintraege jetzt: %d  (vorher %d)" % (len(kontrolle), len(journal) - dazu))
    verk = [t for t in kontrolle if t.get("type") == "SELL"]
    for f in FELDER:
        k = sum(1 for t in verk if t.get(f) is not None)
        print("    %-18s %4d von %d  = %5.1f %%" % (f, k, len(verk), 100.0*k/max(len(verk), 1)))
    fehlt = [t for t in journal if t.get("_id") not in {x.get("_id") for x in kontrolle}]
    print("    verlorene Eintraege: %d  %s" % (len(fehlt), "OK" if not fehlt else "ACHTUNG"))
    return 0


def selbsttest():
    print("SELBSTTEST")
    print("-" * 60)
    f = 0
    pos = [{"pos_id": "P1", "muenze": "BTC/USDC", "eroeffnet": "2026-08-20T10:00:00+00:00",
            "geschlossen": "2026-08-20T12:30:00+00:00", "strategie": "RSI", "score": 4,
            "einstieg": 1.0, "menge": 1.0}]

    ok = haltedauer(pos[0]) == 150.0
    print("  %s Haltedauer 10:00 bis 12:30 -> 150,0 Minuten (ist: %s)"
          % ("OK  " if ok else "FEHL", haltedauer(pos[0]))); f += 0 if ok else 1

    v = {"type": "SELL", "coin": "BTC/USDC", "time": "2026-08-20T12:33:00+00:00", "_id": 1}
    p, e = zuordnen(v, pos)
    ok = p is not None and e
    print("  %s Verkauf 3 Min nach Schluss -> eindeutig zugeordnet" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    v2 = {"type": "SELL", "coin": "BTC/USDC", "time": "2026-08-20T13:30:00+00:00", "_id": 2}
    p2, _ = zuordnen(v2, pos)
    ok = p2 is None
    print("  %s Verkauf 60 Min spaeter -> keine Zuordnung (Toleranz 600 s)" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    doppelt = pos + [dict(pos[0], pos_id="P2")]
    _, e2 = zuordnen(v, doppelt)
    ok = not e2
    print("  %s zwei Kandidaten -> NICHT eindeutig, wird uebergangen" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    v3 = {"type": "SELL", "coin": "BTC/USDC", "time": "2026-08-20T12:33:00+00:00",
          "_id": 3, "entry_strategie": "SCHON_DA"}
    plan, _ = planen([v3], pos)
    ok = "entry_strategie" not in plan.get(3, {})
    print("  %s vorhandener Wert wird NICHT ueberschrieben" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    j = [dict(v)]
    plan, _ = planen(j, pos)
    anwenden(j, plan, "2026-08-29")
    ok = j[0].get("_nachgetragen", {}).get("befund") == 88 and j[0]["position_id"] == "P1"
    print("  %s Eintrag wird markiert und gefuellt" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    kauf = [{"type": "BUY", "coin": "BTC/USDC", "time": "2026-08-20T10:00:00+00:00", "_id": 9}]
    plan, st = planen(kauf, pos)
    ok = not plan and st["verkaeufe"] == 0
    print("  %s Kaeufe werden nicht angefasst" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    print("-" * 60)
    print("ALLE TESTS BESTANDEN" if f == 0 else "%d TEST(S) FEHLGESCHLAGEN" % f)
    return 0 if f == 0 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schreiben", action="store_true",
                   help="wirklich eintragen (ohne: nur zeigen)")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    if a.selbsttest:
        return selbsttest()
    return lauf(a.schreiben)


if __name__ == "__main__":
    sys.exit(main())
