# -*- coding: utf-8 -*-
"""fraktal_konfluenz_test.py - Stufe 1 des neuen Handelswegs, nachgerechnet.

WOZU
----
Svens Prompt vom 14.09.2026 verlangt in Abschnitt 1: *"Implementiere
deterministische Pruefungen fuer jede Berechnung. Bei identischen
OHLCV-Eingabedaten und identischer Konfiguration muessen immer exakt
dieselben Resultate entstehen."*

Diese Datei prueft die drei geforderten Bereiche an synthetischen Daten,
bei denen das richtige Ergebnis von Hand bekannt ist:

  A  Fraktal-Mathematik      2n+1 Kerzen, Raender, Ties, Look-ahead
  B  Fibonacci-Mathematik    beide Richtungen, Golden Pocket, Sortierung
  C  Konfluenz-Mathematik    Toleranz-Grenzfaelle, keine Doppelzaehlung

Jede Pruefung geht in BEIDE Richtungen: sie muss schweigen, wenn es
stimmt, und anschlagen, wenn jemand die Regel aendert.

AENDERT NICHTS. Rechnet auf erfundenen Kerzen.

    python fraktal_konfluenz_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd                                          # noqa: E402

from features.chartanalyse import swing_punkte               # noqa: E402
from features.fraktal_konfluenz import (                     # noqa: E402
    GOLDEN_POCKET, STUFEN_HANDEL, golden_pocket, im_golden_pocket,
    konfluenz, stufen_einer_welle, wellen_aus_fraktalen)


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("    %-50s ok   %s" % (was, zusatz))
        else:
            self.fehler.append((was, zusatz))
            print("    %-50s FEHL %s" % (was, zusatz))


def kerzen(hochs, tiefs=None):
    """Baut einen DataFrame aus Hoch-Werten. Tiefs = Hochs minus 1."""
    tiefs = [h - 1.0 for h in hochs] if tiefs is None else tiefs
    return pd.DataFrame({"High": hochs, "Low": tiefs,
                         "Close": [(h + t) / 2 for h, t in zip(hochs, tiefs)]})


# ==================================================================== A
def teil_a(p):
    print()
    print("  A  FRAKTAL-MATHEMATIK")
    print("  " + "-" * 68)

    # Ein klares Hoch in der Mitte: Index 4 ist hoeher als 2,3 und 5,6
    hochs = [10, 11, 12, 13, 20, 13, 12, 11, 10]
    df = kerzen(hochs)
    h, t = swing_punkte(df, weite=2)
    p.sage("Ein Swing-Hoch bei n=2 wird gefunden",
           len(h) == 1 and h[0][0] == 4,
           "Index %s, Preis %s" % (h[0][0] if h else "-", h[0][1] if h else "-"))

    # 2n+1: bei n=2 braucht es zwei Kerzen links UND rechts
    p.sage("Es braucht 2*n+1 = 5 Kerzen",
           len(swing_punkte(kerzen([10, 20, 10]), weite=2)[0]) == 0,
           "drei Kerzen reichen bei n=2 nicht")

    # Raender: das erste und letzte Hoch darf kein Fraktal sein
    rand = kerzen([99, 11, 12, 13, 12, 11, 99])
    h, t = swing_punkte(rand, weite=2)
    p.sage("Raender erzeugen kein bestaetigtes Fraktal",
           not any(x[0] in (0, len(rand) - 1) for x in h),
           "die 99 an beiden Enden zaehlen nicht")

    # Look-ahead: bestaetigt_ab muss i+n sein
    df = kerzen([10, 11, 12, 13, 20, 13, 12, 11, 10])
    h, _ = swing_punkte(df, weite=2)
    p.sage("bestaetigt_ab liegt n Kerzen spaeter",
           h and h[0][2] == h[0][0] + 2,
           "Punkt bei %d, bestaetigt ab %d" % (h[0][0], h[0][2]))

    # Und die Folge daraus: vor der Bestaetigung gibt es die Welle nicht.
    #
    # [Berichtigt 14.09.] Die erste Fassung nahm dieselben Kerzen wie oben -
    # die haben ein Swing-HOCH, aber kein Swing-TIEF, weil die Tiefs dort
    # monoton verlaufen. Ohne Paar entsteht gar keine Welle, und der Test
    # verglich 0 mit 0. Das war ein Befund ueber die TESTDATEN, nicht ueber
    # den Code. Hier also Kerzen mit BEIDEM:
    #   Swing-Tief  bei Index 4 (Low 5),  bestaetigt ab Index 6
    #   Swing-Hoch  bei Index 8 (High 20), bestaetigt ab Index 10
    welle_df = pd.DataFrame({
        "High": [15, 14, 13, 12,  6, 12, 13, 14, 20, 14, 13, 12, 11],
        "Low":  [14, 13, 12, 11,  5, 11, 12, 13, 19, 13, 12, 11, 10],
        "Close": [14.5, 13.5, 12.5, 11.5, 5.5, 11.5, 12.5, 13.5, 19.5,
                  13.5, 12.5, 11.5, 10.5]})
    hh, tt = swing_punkte(welle_df, weite=2)
    p.sage("Testkerzen haben Tief UND Hoch",
           len(tt) == 1 and tt[0][0] == 4 and len(hh) == 1 and hh[0][0] == 8,
           "Tief bei %s, Hoch bei %s"
           % (tt[0][0] if tt else "-", hh[0][0] if hh else "-"))

    frueh = wellen_aus_fraktalen(welle_df, weite=2, jetzt_index=9)
    spaet = wellen_aus_fraktalen(welle_df, weite=2, jetzt_index=10)
    p.sage("Vor der Bestaetigung existiert die Welle nicht",
           len(frueh) == 0 and len(spaet) == 1,
           "Index 9: %d Wellen, Index 10: %d (Hoch ist ab 10 bestaetigt)"
           % (len(frueh), len(spaet)))

    # Allgemeines n
    lang = kerzen([1, 2, 3, 4, 5, 30, 5, 4, 3, 2, 1])
    for n in (2, 3, 4):
        hh, _ = swing_punkte(lang, weite=n)
        p.sage("      n=%d findet das Hoch (2n+1=%d Kerzen)" % (n, 2 * n + 1),
               len(hh) == 1 and hh[0][0] == 5, "")

    # Ties: gleich hohe Kerzen duerfen kein Fraktal erzeugen
    gleich = kerzen([10, 11, 20, 20, 20, 11, 10])
    hh, _ = swing_punkte(gleich, weite=2)
    p.sage("Gleich hohe Kerzen (Ties) -> kein Fraktal",
           len(hh) == 0,
           "Regel ist 'strict': %d gefunden" % len(hh))


# ==================================================================== B
def teil_b(p):
    print()
    print("  B  FIBONACCI-MATHEMATIK")
    print("  " + "-" * 68)

    hoch, tief = 200.0, 100.0        # Spanne genau 100, alles von Hand pruefbar

    # Aufwaerts: 0 am Hoch, Stufen nach unten
    auf = {s["verhaeltnis"]: s["preis"]
           for s in stufen_einer_welle(hoch, tief, aufwaerts=True)}
    p.sage("Aufwaerts: 0,5 liegt bei 150",
           abs(auf[0.5] - 150.0) < 1e-9, "%.4f" % auf[0.5])
    p.sage("Aufwaerts: 0,618 liegt bei 138,2",
           abs(auf[0.618] - 138.2) < 1e-9, "%.4f" % auf[0.618])
    p.sage("Aufwaerts: 0,65 liegt bei 135",
           abs(auf[0.65] - 135.0) < 1e-9, "%.4f" % auf[0.65])

    # Abwaerts: 0 am Tief, Stufen nach oben
    ab = {s["verhaeltnis"]: s["preis"]
          for s in stufen_einer_welle(hoch, tief, aufwaerts=False)}
    p.sage("Abwaerts: 0,618 liegt bei 161,8",
           abs(ab[0.618] - 161.8) < 1e-9, "%.4f" % ab[0.618])
    p.sage("Abwaerts ist das Spiegelbild von aufwaerts",
           all(abs((auf[r] - tief) - (hoch - ab[r])) < 1e-9
               for r in (0.236, 0.382, 0.5, 0.618, 0.786)),
           "fuer alle fuenf klassischen Stufen")

    # Golden Pocket: das BAND zwischen 0,618 und 0,65
    band_auf = golden_pocket(hoch, tief, aufwaerts=True)
    p.sage("Golden Pocket aufwaerts = 135,0 bis 138,2",
           abs(band_auf[0] - 135.0) < 1e-9 and abs(band_auf[1] - 138.2) < 1e-9,
           "%.2f bis %.2f" % band_auf)

    band_ab = golden_pocket(hoch, tief, aufwaerts=False)
    p.sage("Golden Pocket abwaerts = 161,8 bis 165,0",
           abs(band_ab[0] - 161.8) < 1e-9 and abs(band_ab[1] - 165.0) < 1e-9,
           "%.2f bis %.2f" % band_ab)

    p.sage("Unten ist IMMER kleiner als oben",
           band_auf[0] < band_auf[1] and band_ab[0] < band_ab[1],
           "in beiden Richtungen sortiert")

    p.sage("Ein Preis im Band wird erkannt",
           im_golden_pocket(136.5, hoch, tief, True)
           and not im_golden_pocket(150.0, hoch, tief, True), "")
    p.sage("Die Raender zaehlen dazu",
           im_golden_pocket(135.0, hoch, tief, True)
           and im_golden_pocket(138.2, hoch, tief, True), "")

    # Marks Satz bleibt unangetastet
    from features.chartanalyse import FIB_RUECK
    p.sage("Marks Stufensatz ist unveraendert",
           0.65 not in FIB_RUECK and 0.707 in FIB_RUECK and 0.866 in FIB_RUECK,
           "FIB_RUECK ohne 0,65 - Befund 102 bleibt vergleichbar")
    p.sage("Der Handelssatz hat die 0,65 zusaetzlich",
           0.65 in STUFEN_HANDEL and 0.707 in STUFEN_HANDEL,
           "%d Stufen" % len(STUFEN_HANDEL))

    # Unmoegliche Eingaben
    p.sage("Hoch gleich Tief gibt nichts zurueck",
           golden_pocket(100.0, 100.0) is None
           and stufen_einer_welle(100.0, 100.0) == [], "")


# ==================================================================== C
def teil_c(p):
    print()
    print("  C  KONFLUENZ-MATHEMATIK")
    print("  " + "-" * 68)

    def stufe(preis, tf, welle, r=0.5):
        return {"verhaeltnis": r, "preis": preis, "zeitrahmen": tf,
                "welle": welle, "richtung": "auf",
                "golden": r in GOLDEN_POCKET, "anker": False}

    # Grenzfall: genau AN der Toleranz
    an_der_grenze = [[stufe(100.0, "1d", "a")], [stufe(100.35, "4h", "b")]]
    z = konfluenz(an_der_grenze, toleranz_pct=0.35)
    p.sage("Genau an der Toleranz -> eine Zone",
           len(z) == 1, "%d Zone(n)" % len(z))

    # Knapp darueber
    knapp_drueber = [[stufe(100.0, "1d", "a")], [stufe(100.5, "4h", "b")]]
    z = konfluenz(knapp_drueber, toleranz_pct=0.35)
    p.sage("Knapp ausserhalb -> zwei Zonen",
           len(z) == 2, "%d Zone(n)" % len(z))

    # DER WICHTIGSTE FALL: drei Stufen DERSELBEN Welle
    dieselbe = [[stufe(100.0, "1d", "a", 0.5),
                 stufe(100.1, "1d", "a", 0.618),
                 stufe(100.2, "1d", "a", 0.786)]]
    z = konfluenz(dieselbe, toleranz_pct=0.35)
    p.sage("Drei Stufen DERSELBEN Welle zaehlen als EINE",
           len(z) == 1 and z[0]["quellen"] == 1,
           "Score %d, %d Quelle(n) aus %d Linien"
           % (z[0]["score"], z[0]["quellen"], z[0]["stufen_roh"]))

    # Gegenprobe: drei Stufen aus DREI Quellen
    drei_quellen = [[stufe(100.0, "1d", "a")], [stufe(100.1, "4h", "b")],
                    [stufe(100.2, "1h", "c")]]
    z3 = konfluenz(drei_quellen, toleranz_pct=0.35)
    p.sage("Drei Stufen aus DREI Quellen zaehlen als drei",
           len(z3) == 1 and z3[0]["quellen"] == 3,
           "Score %d, %d Quellen" % (z3[0]["score"], z3[0]["quellen"]))

    p.sage("... und geben einen HOEHEREN Score als eine Quelle",
           z3[0]["score"] > z[0]["score"],
           "%d gegen %d" % (z3[0]["score"], z[0]["score"]))

    # Golden Pocket gibt Zuschlag - aber nur einmal
    ohne = konfluenz([[stufe(100.0, "1d", "a", 0.5)]], toleranz_pct=0.35)
    mit = konfluenz([[stufe(100.0, "1d", "a", 0.618)]], toleranz_pct=0.35)
    zweimal = konfluenz([[stufe(100.0, "1d", "a", 0.618),
                          stufe(100.1, "1d", "a", 0.65)]], toleranz_pct=0.35)
    p.sage("Golden Pocket gibt einen Zuschlag",
           mit[0]["score"] > ohne[0]["score"],
           "%d gegen %d" % (mit[0]["score"], ohne[0]["score"]))
    p.sage("... aber nur EINMAL, auch bei beiden Stufen",
           zweimal[0]["score"] == mit[0]["score"],
           "%d, nicht %d" % (zweimal[0]["score"], mit[0]["score"] + 1))

    # Herkunft vollstaendig gespeichert
    p.sage("Die Zone kennt ihre ganze Herkunft",
           len(z[0]["herkunft"]) == 3
           and all("welle" in h and "zeitrahmen" in h for h in z[0]["herkunft"]),
           "%d Eintraege, alle mit Welle und Zeitrahmen" % len(z[0]["herkunft"]))

    # Relativ, nicht absolut
    gross = konfluenz([[stufe(64000.0, "1d", "a")], [stufe(64100.0, "4h", "b")]],
                      toleranz_pct=0.35)
    klein = konfluenz([[stufe(100.0, "1d", "a")], [stufe(200.0, "4h", "b")]],
                      toleranz_pct=0.35)
    p.sage("Die Toleranz ist relativ, nicht in Dollar",
           len(gross) == 1 and len(klein) == 2,
           "100 $ bei BTC = eine Zone, 100 $ bei SOL = zwei")

    # Determinismus
    a = konfluenz(drei_quellen, toleranz_pct=0.35)
    b = konfluenz(drei_quellen, toleranz_pct=0.35)
    p.sage("Gleiche Eingabe gibt gleiches Ergebnis",
           [x["mitte"] for x in a] == [x["mitte"] for x in b], "")


def main():
    print("=" * 78)
    print("  FRAKTALE + FIBONACCI-KONFLUENZ - Stufe 1 nachgerechnet")
    print("=" * 78)
    p = Pruefung()
    teil_a(p)
    teil_b(p)
    teil_c(p)

    print()
    print("  Gegentest - wuerden die Pruefungen einen Fehler finden?")
    print("    Die Werte oben sind von Hand nachrechenbar: Spanne 100,")
    print("    also liegt 0,618 bei 138,20 und 0,65 bei 135,00. Wer eine")
    print("    Stufe verstellt, aendert diese Zahlen - und faellt durch.")
    print("    Die Doppelzaehlungs-Pruefung ist die schaerfste: sie")
    print("    vergleicht dieselbe Zone einmal aus einer und einmal aus")
    print("    drei Quellen. Ein Score, der nur Linien zaehlt, gaebe")
    print("    beide Male dasselbe - und faellt durch.")

    print()
    print("-" * 78)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d" % (len(p.fehler), p.ok + len(p.fehler)))
        for was, z in p.fehler:
            print("    %s  %s" % (was, z))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Das ist Stufe 1: die Mathematik stimmt. Was es NICHT sagt,")
    print("  ist ob die Methode Geld verdient - dafuer braucht es Stufe 2")
    print("  (Schattenbetrieb) und Stufe 3 (Backtest mit Out-of-Sample).")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
