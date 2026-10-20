# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Werkzeugvalidierung A/B, 05.08.2026. Read-only auf Daten.
"""
WERKZEUGPRUEFUNG, kein neuer Trial, keine Hypothese.

Frage: Wie stark verzerrt der Backtest-Harness das Ergebnis, bevor
ueberhaupt eine Strategie bewertet wird?

BLOCKER 1 - KAPITALTOD
  backtest/ausstieg_backtest.py:193-195
      betrag = min(eigenkapital * groesse_pct / 100, self.bar)
      if betrag < 10: return False
  Mindestordergroesse 10 $. Bei groesse_pct=20 heisst das: faellt das
  Eigenkapital unter 50 $, ist JEDER weitere Einstieg blockiert. Der Lauf
  misst ab da nicht mehr die Strategie, sondern die Kapitalkurve.
  Bekannt aus Block A: Jahr 2 war an 143 von 366 Tagen betroffen.

  A/B: derselbe Datensatz, dieselbe Strategie, nur die Einsatzregel
  wechselt.
    A = Original, prozentual vom Eigenkapital (verzerrt)
    B = konstanter Einsatz je Trade (kapitalunabhaengig)
  Die Differenz IST die Werkzeugverzerrung.

  Variante B wird als Subklasse gebaut, backtest/ausstieg_backtest.py
  bleibt UNVERAENDERT.

BLOCKER 2 - LOOK-AHEAD
  Bereits gemessen in messung_t034b_strategien.py (Spalte q_la): bis
  4,77 pp, Richtung durchweg negativ. Hier wird nur die Zusammenfassung
  aus dem vorhandenen Zwischenstand neu ausgewiesen, damit beide Blocker
  in einer Tabelle stehen. Keine Neurechnung.

AUSGABE: ../ausgaben/messung_werkzeug_ab_out.txt
"""
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
from harness_ext import LaufMess, lade_jahr, kennzahlen        # noqa: E402
from backtest.ausstieg_backtest import NEUE_LEITER             # noqa: E402

AUS = os.path.join(HIER, "..", "ausgaben")
JSONL = os.path.join(AUS, "messung_t034b_zwischenstand.jsonl")


class LaufKonstant(LaufMess):
    """Variante B: konstanter Einsatz je Trade.

    Einzige Aenderung gegenueber Lauf._kaufe (:191-211): der Einsatz haengt
    nicht mehr am aktuellen Eigenkapital. Alles andere - Slippage, Gebuehr,
    Mittelung, Stufen, Hoechststaende - ist woertlich uebernommen, damit die
    Differenz ausschliesslich aus der Einsatzregel stammt.
    """

    def __init__(self, *a, fix_einsatz=100.0, **kw):
        super().__init__(*a, **kw)
        self.fix_einsatz = fix_einsatz
        self.abgelehnt_kapital = 0        # Einstiege, die A verloren haette

    def _kaufe(self, symbol, preis, zeit):
        from backtest.ausstieg_backtest import Position, SLIPPAGE, GEBUEHR
        kurs = preis * (1 + SLIPPAGE)
        betrag = min(self.fix_einsatz, self.bar)
        # Gegenprobe: haette die ORIGINAL-Regel hier abgelehnt?
        orig = min(self.eigenkapital(preis_map=None) * self.groesse_pct / 100,
                   self.bar)
        if orig < 10:
            self.abgelehnt_kapital += 1
        if betrag < 10:
            return False
        neu = symbol not in self.positionen
        geb = betrag * GEBUEHR
        menge = (betrag - geb) / kurs
        self.bar -= betrag
        p = self.positionen.get(symbol)
        if p is None:
            self.positionen[symbol] = Position(symbol, menge, kurs, betrag)
        else:
            gesamt = p.menge + menge
            p.einstand = (p.einstand * p.menge + kurs * menge) / gesamt
            p.menge = gesamt
            p.kosten += betrag
            p.stufen += 1
            p.hoch = p.tief = p.einstand
            p.hoechst_pnl = 0.0
        # Buchhaltung der Messinstrumentierung wie in LaufMess._kaufe
        if neu:
            self.eintritt[symbol] = zeit
        self.stop_pos[symbol] = self.stop_loss_pct
        self.stop_pcts.append(self.stop_loss_pct)
        self.kauf_events.append((symbol, zeit, preis))
        return True


def lauf(klasse, daten, fg, **kw):
    L = klasse(NEUE_LEITER, kw.pop("name", "X"), **kw)
    L.laufe(daten, fg)
    return L


def kopf(t, p):
    p("\n" + "=" * 96)
    p(" " + t)
    p("=" * 96)


def main():
    zeilen = []

    def p(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        sys.stdout.flush()
        zeilen.append(s)

    p("WERKZEUGVALIDIERUNG A/B - kein Trial, keine Hypothese")
    p("Frage: wie stark verzerrt der Harness, bevor eine Strategie bewertet wird?")

    for jahr, marke in (("J2", ""), ("J1", "_v1")):
        daten, fg = lade_jahr(marke)
        kopf(f"BLOCKER 1 - KAPITALTOD, Jahr {jahr}", p)
        p(f"\n  Datenbasis: {len(daten)} Coins, "
          f"{sum(len(v) for v in daten.values())} 15m-Kerzen")

        A = lauf(LaufMess, daten, fg, name=f"A_prozentual_{jahr}",
                 startkapital=500.0, groesse_pct=20.0)
        B = lauf(LaufKonstant, daten, fg, name=f"B_konstant_{jahr}",
                 startkapital=500.0, groesse_pct=20.0, fix_einsatz=100.0)

        ka, kb = kennzahlen(A.trades), kennzahlen(B.trades)
        p(f"\n  {'Kennzahl':<26s} {'A prozentual':>15s} {'B konstant':>15s} "
          f"{'Differenz':>14s}")
        p("  " + "-" * 74)
        for feld, name, fmt in (
                ("n", "Trades", "{:>15.0f}"),
                ("wr", "Trefferquote %", "{:>15.2f}"),
                ("rr", "R/R", "{:>15.3f}"),
                ("ev_r", "EV in R", "{:>15.4f}"),
                ("summe", "Summe $", "{:>15.2f}"),
                ("geb", "Gebuehren $", "{:>15.2f}"),
                ("halte", "Haltedauer h", "{:>15.1f}")):
            va, vb = ka[feld], kb[feld]
            p(f"  {name:<26s}" + fmt.format(va) + fmt.format(vb)
              + f"{vb - va:>14.4f}")
        p(f"\n  Endkapital A: {A.bar + sum(x.menge * x.einstand for x in A.positionen.values()):.2f}$")
        p(f"  Endkapital B: {B.bar + sum(x.menge * x.einstand for x in B.positionen.values()):.2f}$")
        p(f"\n  Einstiege, die die PROZENTUALE Regel wegen Kapitalmangel")
        p(f"  abgelehnt haette (in B mitgezaehlt): {B.abgelehnt_kapital}")
        if ka["n"]:
            p(f"  Trade-Differenz: {kb['n'] - ka['n']:+d} "
              f"({(kb['n'] - ka['n']) / ka['n'] * 100:+.1f} %)")
        p(f"\n  LESART: Was hier als Differenz steht, ist KEINE Aussage ueber")
        p(f"  die Strategie. Es ist der Anteil des Ergebnisses, der allein")
        p(f"  von der Einsatzregel des Werkzeugs kommt.")

    # -------------------------------------------------- Blocker 2
    kopf("BLOCKER 2 - LOOK-AHEAD, Zusammenfassung aus dem Zwischenstand", p)
    if not os.path.isfile(JSONL):
        p("\n  messung_t034b_zwischenstand.jsonl fehlt - uebersprungen.")
    else:
        e = []
        with open(JSONL, encoding="utf-8") as f:
            for z in f:
                z = z.strip()
                if z:
                    e.append(json.loads(z))
        d = [(x["q_la"] - x["q"], x) for x in e]
        d.sort(key=lambda t: t[0])
        p(f"\n  {len(e)} Tests. Delta = P(auf) OHNE Look-ahead minus MIT.")
        p(f"  Negativ heisst: der Look-ahead hat P(auf) UEBERSCHAETZT.\n")
        p(f"  {'Strategie':<18s} {'Jahr':<4s} {'Barriere':<12s} "
          f"{'mit LA':>8s} {'ohne LA':>8s} {'Delta':>9s}")
        for dd, x in d[:5]:
            p(f"  {x['name']:<18s} {x['jahr']:<4s} {x['kombi']:<12s} "
              f"{x['q']:7.2f}% {x['q_la']:7.2f}% {dd:+8.2f}pp")
        p("  ...")
        for dd, x in d[-3:]:
            p(f"  {x['name']:<18s} {x['jahr']:<4s} {x['kombi']:<12s} "
              f"{x['q']:7.2f}% {x['q_la']:7.2f}% {dd:+8.2f}pp")
        neg = sum(1 for dd, _ in d if dd < 0)
        p(f"\n  Deltas negativ: {neg} von {len(d)} "
          f"({neg / len(d) * 100:.0f} %)")
        p(f"  Groesster Betrag: {max(abs(dd) for dd, _ in d):.2f} pp")
        p(f"  Mittleres Delta:  {sum(dd for dd, _ in d) / len(d):+.2f} pp")
        p(f"\n  LESART: Der Look-ahead hat die Ergebnisse ueberwiegend zu GUT")
        p(f"  aussehen lassen. Die negativen Urteile werden dadurch")
        p(f"  bestaetigt, nicht entwertet.")

    with open(os.path.join(AUS, "messung_werkzeug_ab_out.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
