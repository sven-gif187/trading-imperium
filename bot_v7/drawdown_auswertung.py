# -*- coding: utf-8 -*-
"""
drawdown_auswertung.py — wie tief ging es vom Hoechststand herunter?
=====================================================================

WARUM ES DIESES PROGRAMM GIBT
-----------------------------
Der groesste Rueckschlag (Drawdown) ist eine von Svens Zielgroessen:
hart 15 %, absolute Schmerzgrenze 20 %. Er stand bisher als UNGEMESSEN
im Terminal-Reiter, weil niemand ihn ausgerechnet hat.

WELCHE QUELLE - UND WARUM NICHT DIE NAHELIEGENDE
------------------------------------------------
data_store/equity_history.json sieht nach der richtigen Datei aus. Sie
ist es nicht: ein Ringpuffer mit 500 Punkten, gemessen am 19.08.2026
waren das **6,6 Stunden**. Fuer einen Rueckschlag ueber Wochen unbrauchbar.

Die brauchbare Quelle ist telemetrie.db, Spalte evaluations.total_equity:
189.726 Punkte ueber 12 Tage. Gegengeprueft im Ueberlappungsbereich -
beide Quellen weichen um 0,01 $ voneinander ab (0,00 %).

EPOCHEN
-------
Ein Rueckschlag ueber eine Epochengrenze hinweg mischt zwei Regelwerke.
Deshalb wird zusaetzlich JE EPOCHE gerechnet. Die Gesamtzahl steht dabei,
aber die Epochenzahlen sind die ehrlicheren.

WAS ES NICHT KANN
-----------------
Vor dem 06.08.2026 gibt es keine Kapitalwerte - die Telemetrie begann
erst dann. Frueheres bleibt unbekannt, nicht "null".

AUFRUF
------
    python drawdown_auswertung.py              volle Auswertung
    python drawdown_auswertung.py --kurz       nur die Kernzahlen
    python drawdown_auswertung.py --selbsttest Gegentest in beide Richtungen

NUR LESEND.
"""
import json
import os
import sqlite3
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "data_store", "telemetrie.db")
EPOCHEN = os.path.join(HIER, "config_epochs.json")
ZIELE = os.path.join(HIER, "config_zielgroessen.json")


def kapitalkurve(ab=None, bis=None):
    """(Zeitstempel, Kapital) aufsteigend. Nur echte Werte, keine Nullen."""
    if not os.path.exists(DB):
        return []
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=30)
    # [BEFUND 55, 19.08.2026] Messungen waehrend einer laufenden
    # Verkaufsbuchung ausschliessen. Dort steht der Verkaufserloes schon
    # im Cash, waehrend die Position noch mitgezaehlt wird - das Kapital
    # ist doppelt. Zwei solche Messungen von 203.432 liessen den groessten
    # Rueckschlag von 13,11 % auf 23,20 % springen.
    # Kennzeichen des Zwischenzustands: offene_positionen IS NULL.
    sql = ("SELECT ts_utc, total_equity FROM evaluations "
           "WHERE total_equity IS NOT NULL AND total_equity > 0 "
           "AND offene_positionen IS NOT NULL")
    args = []
    if ab:
        sql += " AND ts_utc >= ?"; args.append(ab)
    if bis:
        sql += " AND ts_utc < ?"; args.append(bis)
    sql += " ORDER BY ts_utc"
    out = [(r[0], float(r[1])) for r in con.execute(sql, args)]
    con.close()
    return out


def drawdown(kurve):
    """Groesster Rueckschlag vom jeweiligen Hoechststand.

    Rueckgabe: dict mit max_dd_pct, max_dd_usd, gipfel/tal (Zeit+Wert),
    aktuellem Rueckschlag und der laengsten Zeit unter Wasser (Stunden).
    """
    if len(kurve) < 2:
        return None
    gipfel_wert = kurve[0][1]
    gipfel_zeit = kurve[0][0]
    max_dd = 0.0
    max_dd_usd = 0.0
    bester_gipfel = (gipfel_zeit, gipfel_wert)
    tiefstes_tal = kurve[0]
    unterwasser_seit = None
    laengste_uw = 0.0
    laengste_uw_ab = None

    for ts, wert in kurve:
        if wert >= gipfel_wert:
            if unterwasser_seit is not None:
                try:
                    dauer = ((datetime.fromisoformat(ts)
                              - datetime.fromisoformat(unterwasser_seit))
                             .total_seconds() / 3600)
                    if dauer > laengste_uw:
                        laengste_uw = dauer
                        laengste_uw_ab = unterwasser_seit
                except Exception:
                    pass
                unterwasser_seit = None
            gipfel_wert, gipfel_zeit = wert, ts
            continue
        if unterwasser_seit is None:
            unterwasser_seit = ts
        dd = (gipfel_wert - wert) / gipfel_wert * 100
        if dd > max_dd:
            max_dd = dd
            max_dd_usd = gipfel_wert - wert
            bester_gipfel = (gipfel_zeit, gipfel_wert)
            tiefstes_tal = (ts, wert)

    # noch laufender Unterwasser-Abschnitt
    if unterwasser_seit is not None:
        try:
            dauer = ((datetime.fromisoformat(kurve[-1][0])
                      - datetime.fromisoformat(unterwasser_seit))
                     .total_seconds() / 3600)
            if dauer > laengste_uw:
                laengste_uw, laengste_uw_ab = dauer, unterwasser_seit
        except Exception:
            pass

    letzter = kurve[-1][1]
    hoechster = max(w for _, w in kurve)
    aktuell = (hoechster - letzter) / hoechster * 100 if hoechster else 0.0
    return {"n": len(kurve),
            "max_dd_pct": max_dd, "max_dd_usd": max_dd_usd,
            "gipfel": bester_gipfel, "tal": tiefstes_tal,
            "aktuell_pct": aktuell, "letzter": letzter, "hoechster": hoechster,
            "erster": kurve[0][1], "von": kurve[0][0], "bis": kurve[-1][0],
            "laengste_uw_h": laengste_uw, "laengste_uw_ab": laengste_uw_ab}


def zwei_niveaus(kurve, mindest_sprung_pct=5.0):
    """Erkennt, ob in der Spalte ZWEI verschiedene Groessen stecken.

    [BEFUND 19.08.2026] evaluations.total_equity enthaelt zwei verschiedene
    Kapitalbegriffe: app.py:952 rechnet Cash + Positionen OHNE Sparplan-BTC
    (der Kommentar app.py:931 sagt das ausdruecklich), portfolio/manager.py
    get_total_capital() rechnet MIT. Der Unterschied betrug am 19.08. rund
    97 $ bei ~590 $ Kapital - also 16 %.

    Folge: Ein naiv gerechneter Rueckschlag misst nicht den Markt, sondern
    den Wechsel zwischen zwei Definitionen. Deshalb wird hier zuerst
    geprueft, ob das Problem vorliegt - und die Zahl nur ausgegeben, wenn
    sie etwas bedeutet.

    Rueckgabe: (verdacht: bool, anteil_spruenge: float, hoch, tief)
    """
    if len(kurve) < 10:
        return False, 0.0, None, None
    spruenge = 0
    for i in range(1, len(kurve)):
        a, b = kurve[i - 1][1], kurve[i][1]
        if a > 0 and abs(b - a) / a * 100 >= mindest_sprung_pct:
            spruenge += 1
    anteil = spruenge / (len(kurve) - 1) * 100
    werte = sorted(w for _, w in kurve)
    mitte = (werte[0] + werte[-1]) / 2
    unten = [w for w in werte if w < mitte]
    oben = [w for w in werte if w >= mitte]
    hoch = sum(oben) / len(oben) if oben else None
    tief = sum(unten) / len(unten) if unten else None
    # Verdacht, wenn haeufig gesprungen wird UND zwei klar getrennte Wolken
    verdacht = anteil > 1.0 and hoch and tief and (hoch - tief) / hoch * 100 > 5
    return verdacht, anteil, hoch, tief


def niveaus_zaehlen(kurve, mindest_luecke_pct=3.0):
    """Wieviele getrennte Kapitalniveaus stecken in der Spalte?

    [FIX 19.08.2026, abends] Am Abend tauchte ein DRITTES Niveau auf
    (~776 $ neben ~601 $ und ~493 $). Die Zwei-Niveau-Annahme reichte
    nicht mehr, und geteilte_kurven() lieferte eine Haelfte mit drei
    Punkten - Drawdown 0,0 %, obwohl er bei 19,5 % lag.

    Eine Kennzahl, die ploetzlich null ist, ist fast nie null.

    Jetzt wird erst GEZAEHLT. Sind es mehr als zwei, gibt es keine Zahl,
    sondern die Auskunft, dass die Quelle nicht auswertbar ist.
    """
    werte = sorted(w for _, w in kurve)
    if len(werte) < 10:
        return [(werte[0], werte[-1], len(werte))] if werte else []
    gruppen, start, vorher = [], werte[0], werte[0]
    for w in werte[1:]:
        if vorher > 0 and (w - vorher) / vorher * 100 >= mindest_luecke_pct:
            gruppen.append((start, vorher))
            start = w
        vorher = w
    gruppen.append((start, vorher))
    # Zahl der Punkte je Gruppe ergaenzen
    out = []
    for lo, hi in gruppen:
        n = sum(1 for w in werte if lo <= w <= hi)
        out.append((lo, hi, n))
    return out


def geteilte_kurven(kurve):
    """Teilt die Kurve in die zwei Kapitaldefinitionen auf.

    [FIX 19.08.2026, abends] Die erste Fassung teilte an der MITTE
    zwischen Min und Max. Das ist nicht robust: Ein einzelner Ausreisser
    nach oben verschiebt die Grenze so weit, dass fast alles in eine
    Haelfte faellt. Genau das ist passiert - die obere Haelfte enthielt
    3 von 203.401 Punkten, und stichtag.py meldete daraufhin einen
    groessten Rueckschlag von 0,0 %, waehrend er in Wahrheit bei 19,5 %
    lag. Eine Kennzahl, die ploetzlich null ist, ist fast nie null.

    Jetzt: Trennung an der groessten LUECKE zwischen zwei benachbarten
    Werten in der oberen Haelfte der sortierten Liste. Das findet den
    Sprung zwischen den beiden Niveaus, nicht die Mitte der Spannweite.
    """
    werte = sorted(w for _, w in kurve)
    if len(werte) < 10:
        mitte = (werte[0] + werte[-1]) / 2 if werte else 0
        return ([p for p in kurve if p[1] >= mitte],
                [p for p in kurve if p[1] < mitte])
    # groesste Luecke suchen - aber nur zwischen dem 5. und 95. Perzentil,
    # damit einzelne Ausreisser an den Raendern sie nicht bestimmen.
    lo, hi = int(len(werte) * 0.05), int(len(werte) * 0.95)
    beste_luecke, grenze = 0.0, None
    for i in range(max(lo, 1), hi):
        luecke = werte[i] - werte[i - 1]
        if luecke > beste_luecke:
            beste_luecke, grenze = luecke, (werte[i] + werte[i - 1]) / 2
    if grenze is None or beste_luecke <= 0:
        grenze = werte[len(werte) // 2]
    return ([p for p in kurve if p[1] >= grenze],
            [p for p in kurve if p[1] < grenze])


def epochen():
    try:
        d = json.load(open(EPOCHEN, encoding="utf-8"))
        eps = d.get("epochs") or []
        return [(e.get("id", "?"), e.get("start", "")) for e in eps
                if e.get("start")]
    except Exception:
        return []


def ziele():
    try:
        return json.load(open(ZIELE, encoding="utf-8"))
    except Exception:
        return {}


def _urteil(dd_pct, z):
    d = (z.get("max_drawdown_pct") or {})
    ziel, warn = d.get("ziel"), d.get("warnung")
    if ziel is None:
        return ""
    if dd_pct <= ziel:
        return f"im Ziel (<= {ziel:.0f} %)"
    if warn is not None and dd_pct <= warn:
        return f"UEBER Ziel {ziel:.0f} %, unter Schmerzgrenze {warn:.0f} %"
    return f"UEBER der Schmerzgrenze {warn:.0f} %" if warn else f"ueber Ziel {ziel:.0f} %"


def bericht(kurz=False):
    kurve = kapitalkurve()
    if not kurve:
        print("Keine Kapitalwerte in telemetrie.db - nichts auszuwerten.")
        return
    z = ziele()

    # ------------------------------------------------ Vorpruefung der Quelle
    verdacht, anteil, hoch, tief = zwei_niveaus(kurve)
    if verdacht:
        print("\n" + "!" * 72)
        print("  DIE QUELLE IST NICHT EINDEUTIG - die Zahl unten waere falsch.")
        print("!" * 72)
        print(f"\n  In {anteil:.0f} % der Messungen springt der Kapitalwert um ueber 5 %.")
        print(f"  Es gibt zwei Niveaus: ~{hoch:.2f} $ und ~{tief:.2f} $ "
              f"(Unterschied {hoch-tief:.2f} $).")
        print("\n  Ursache (BOT-HANDBUCH.md 4.63): In evaluations.total_equity landen")
        print("  ZWEI verschiedene Kapitalbegriffe:")
        print("    app.py:952                    Cash + Positionen OHNE Sparplan-BTC")
        print("    portfolio/manager.py:70       Cash + Positionen MIT Sparplan-BTC")
        print("  Der Kommentar app.py:931 nennt den Ausschluss ausdruecklich.")
        print("\n  Ein Rueckschlag ueber beide Niveaus misst nicht den Markt,")
        print("  sondern den Wechsel zwischen zwei Definitionen.")
        gruppen = [g for g in niveaus_zaehlen(kurve) if g[2] >= len(kurve) * 0.01]
        print(f"\n  Gefundene Kapitalniveaus: {len(gruppen)}")
        for lo, hi, n in gruppen:
            print(f"    {lo:8.2f} bis {hi:8.2f} $   ({n:>7} Messungen, "
                  f"{n/len(kurve)*100:4.1f} %)")
        if len(gruppen) > 2:
            print("\n  MEHR ALS ZWEI NIVEAUS - die Quelle ist nicht auswertbar.")
            print("  Ein Rueckschlag ueber drei Definitionen misst nichts.")
            print("  Erst Befund 44 klaeren (getrennte Spalten), dann messen.\n")
            print("  " + "-" * 68 + "\n")
            return

        print("\n  Deshalb wird getrennt gerechnet:\n")
        oben, unten = geteilte_kurven(kurve)
        for name, teil in (("MIT Sparplan-BTC   ", oben), ("OHNE Sparplan-BTC  ", unten)):
            t = drawdown(teil)
            if t:
                print(f"    {name} n={t['n']:>7}  groesster Rueckschlag "
                      f"{t['max_dd_pct']:5.2f} %  ({t['max_dd_usd']:6.2f} $)   "
                      f"{_urteil(t['max_dd_pct'], z)}")
            else:
                print(f"    {name} zu wenige Punkte")
        print("\n  Diese beiden Zahlen sind belastbar. Die Gesamtzahl unten NICHT.")
        print("  " + "-" * 68)

    g = drawdown(kurve)
    print("\n=== GROESSTER RUECKSCHLAG (Drawdown) ===\n")
    if verdacht:
        print("  ACHTUNG: ueber beide Kapitaldefinitionen gerechnet - nicht belastbar.\n")
    print(f"  Quelle    : telemetrie.db, evaluations.total_equity")
    print(f"  Punkte    : {g['n']:,}".replace(",", "."))
    print(f"  Zeitraum  : {g['von'][:16]} bis {g['bis'][:16]}")
    print(f"  Kapital   : {g['erster']:.2f} $  ->  {g['letzter']:.2f} $"
          f"   (Hoechststand {g['hoechster']:.2f} $)")
    print()
    print(f"  Groesster Rueckschlag : {g['max_dd_pct']:6.2f} %   "
          f"({g['max_dd_usd']:.2f} $)   {_urteil(g['max_dd_pct'], z)}")
    print(f"    vom Gipfel {g['gipfel'][1]:.2f} $ am {g['gipfel'][0][:16]}")
    print(f"    zum Tal    {g['tal'][1]:.2f} $ am {g['tal'][0][:16]}")
    print(f"  Aktueller Rueckschlag : {g['aktuell_pct']:6.2f} %")
    if g["laengste_uw_h"]:
        print(f"  Laengste Zeit unter dem Hoechststand: {g['laengste_uw_h']:.1f} h"
              f" ({g['laengste_uw_h']/24:.1f} Tage), ab {str(g['laengste_uw_ab'])[:16]}")
    if kurz:
        print()
        return

    print("\n=== JE EPOCHE ===")
    print("  (Ein Rueckschlag ueber eine Epochengrenze mischt zwei Regelwerke.)\n")
    eps = epochen()
    print(f"  {'Epoche':<26}{'n':>8}{'max DD':>9}{'aktuell':>9}  {'Kapital von -> bis':<26}")
    print("  " + "-" * 80)
    for i, (name, start) in enumerate(eps):
        ende = eps[i + 1][1] if i + 1 < len(eps) else None
        k = kapitalkurve(ab=start, bis=ende)
        if len(k) < 2:
            print(f"  {name:<26}{len(k):>8}{'-':>9}{'-':>9}  (zu wenige Punkte)")
            continue
        e = drawdown(k)
        print(f"  {name:<26}{e['n']:>8}{e['max_dd_pct']:>8.2f}%{e['aktuell_pct']:>8.2f}%"
              f"  {e['erster']:.2f} $ -> {e['letzter']:.2f} $")
    print()


def selbsttest():
    """Gegentest in beide Richtungen."""
    fehler = 0
    print("\n=== Richtung 1: rechnet die Formel BEKANNTE Faelle richtig? ===")
    faelle = [
        ("nur aufwaerts, kein Rueckschlag",
         [("t1", 100.0), ("t2", 110.0), ("t3", 120.0)], 0.0),
        ("100 -> 80, also 20 %",
         [("t1", 100.0), ("t2", 80.0), ("t3", 90.0)], 20.0),
        ("zwei Taeler, das tiefere zaehlt",
         [("t1", 100.0), ("t2", 90.0), ("t3", 100.0), ("t4", 70.0)], 30.0),
        ("neuer Gipfel setzt zurueck",
         [("t1", 100.0), ("t2", 95.0), ("t3", 200.0), ("t4", 180.0)], 10.0),
    ]
    for name, k, soll in faelle:
        g = drawdown(k)
        ist = g["max_dd_pct"] if g else -1
        ok = abs(ist - soll) < 0.001
        print(f"  {'OK  ' if ok else 'FEHL'} {name:<36} ist {ist:6.2f} %  soll {soll:6.2f} %")
        if not ok:
            fehler += 1

    print("\n=== Richtung 2: faellt sie sauber aus, wenn Daten fehlen? ===")
    for name, k in [("leere Kurve", []), ("ein einziger Punkt", [("t1", 100.0)])]:
        g = drawdown(k)
        ok = g is None
        print(f"  {'OK  ' if ok else 'FEHL'} {name:<36} -> {'None' if ok else 'Daten?!'}")
        if not ok:
            fehler += 1

    print("\n=== Richtung 3: stimmt die echte Quelle mit equity_history.json? ===")
    try:
        j = json.load(open(os.path.join(HIER, "data_store", "equity_history.json"),
                           encoding="utf-8"))["total"]
        ab = datetime.fromtimestamp(j[0][0]).astimezone().isoformat()
        k = kapitalkurve(ab=ab)
        # [FIX 19.08.2026] equity_history.json fuehrt NUR den Kapitalbegriff
        # MIT Sparplan-BTC. telemetrie.db mischt beide (Befund 44). Ein
        # Vergleich ueber alles waere Aepfel gegen Birnen - der Test schlug
        # deshalb mit 12 % Abweichung fehl, obwohl beide Quellen stimmen.
        # Verglichen wird jetzt gegen die obere Teilmenge.
        if k:
            verdacht, _, _, _ = zwei_niveaus(k)
            if verdacht:
                k = geteilte_kurven(k)[0]
        m_db = sum(w for _, w in k) / len(k) if k else 0
        m_js = sum(x[1] for x in j) / len(j)
        abw = abs(m_db - m_js) / m_js * 100 if m_js else 99
        ok = abw < 2.0
        print(f"  telemetrie.db Mittel : {m_db:.2f} $")
        print(f"  equity_history Mittel: {m_js:.2f} $")
        print(f"  {'OK  ' if ok else 'FEHL'} Abweichung {abw:.2f} % (erlaubt bis 2 %)")
        if not ok:
            fehler += 1
    except Exception as e:
        print("  uebersprungen:", str(e)[:60])

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)
    bericht(kurz=(arg == "--kurz"))
