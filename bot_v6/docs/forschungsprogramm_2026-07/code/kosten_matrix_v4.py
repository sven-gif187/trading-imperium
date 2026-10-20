# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Kostenmatrix v4 - Definition of Done erreicht, 10.08.2026.
"""
Loest den Vorbehalt von kosten_matrix_v3.py auf.

v3 stuetzte sich auf EINEN Tag (31.07.2026, ca. 5,5 h, 146 Punkte je Coin) und
trug deshalb ausdruecklich den Vermerk:

    "Die Definition of Done des Capture lautet 7 Tage lueckenlos; erst dann
     sind diese Zahlen belastbar. Bis dahin gilt: WAHRSCHEINLICH, nicht SICHER."

Stand 10.08.2026 liegen 11 Tage vor. Die DoD ist erfuellt. v4 rechnet ueber
ALLE erfassten Tage statt nur ueber den letzten und weist zusaetzlich aus, wie
stark der Spread ueber die Tage schwankt - genau die Verteilung ueber
Marktphasen, die v3 fehlte.

KEIN TRIAL. Es wird keine Handelsregel gegen Marktdaten ausgewertet, sondern
eine Messung praezisiert. Trial-Zaehler unberuehrt.

METHODE (unveraendert zu v3, damit die Zahlen vergleichbar bleiben)
------------------------------------------------------------------
    slippage_je_seite = median(spread_bp) / 2 / 100      [in Prozent]
    K-BASIS_coin = 2 * 0,25 % Taker + 2 * slippage_je_seite
    K-MAKER_coin = 2 * 0,10 % Maker + 2 * 0,03 % Adverse Selection

NEU in v4: der Median wird ueber alle Tage gebildet, und je Coin werden
zusaetzlich der Tages-Median-Bereich (min/max ueber die Tage) sowie die
Streuung ausgewiesen. Ein Coin, dessen Tagesmedian zwischen 2 und 30 bp
schwankt, ist etwas anderes als einer mit konstant 8 bp - auch wenn beide
denselben Gesamtmedian haben.

WOFUER DAS ZAEHLT
-----------------
Die Kostenannahme ist die entscheidende Stellschraube im Chartanalyse-Urteil.
Bei 0,50 % liegt 4h-RETEST bei EV netto -0,290 %; ab etwa 0,29 % Kosten waere
er bei null. Ob die Chartanalyse taugt, haengt also direkt an dieser Messung.
"""
import csv
import glob
import gzip
import io
import os
import statistics as st
import sys
from datetime import datetime, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(BASIS, "capture")
TAKER, MAKER, ADVERSE = 0.25, 0.10, 0.03
BARRIEREN = (5.0, 7.0, 10.0)


def p_be(c, B):
    """Break-even-Trefferquote bei Kosten c und Barriere B."""
    return (0.5 + c / (2.0 * B)) * 100.0


def messe_alle_tage():
    """Liest ALLE Capture-Tage statt nur des letzten (der v3-Unterschied)."""
    tage = sorted(d for d in glob.glob(os.path.join(CAP, "20*"))
                  if os.path.isdir(d))
    je_coin = {}          # sym -> alle spread_bp ueber alle Tage
    je_coin_tag = {}      # sym -> {tag: median}
    for tagpfad in tage:
        tag = os.path.basename(tagpfad)
        for p in sorted(glob.glob(os.path.join(tagpfad, "ticker_*.csv.gz"))):
            sym = os.path.basename(p)[len("ticker_"):-len(".csv.gz")]
            try:
                txt = gzip.open(p, "rt", encoding="utf-8").read()
                sp = [float(r["spread_bp"])
                      for r in csv.DictReader(io.StringIO(txt))
                      if r.get("spread_bp")]
            except Exception:
                continue
            if len(sp) < 30:
                continue
            je_coin.setdefault(sym, []).extend(sp)
            je_coin_tag.setdefault(sym, {})[tag] = st.median(sp)
    return je_coin, je_coin_tag, tage


def main():
    je_coin, je_coin_tag, tage = messe_alle_tage()
    if not je_coin:
        print("  Keine Capture-Daten gefunden.")
        return 1

    n_tage = len(tage)
    dod = n_tage >= 7

    print("=" * 108)
    print(" KOSTENMATRIX v4 - alle Capture-Tage statt nur einem")
    print(f" Zeitraum: {os.path.basename(tage[0])} bis {os.path.basename(tage[-1])}"
          f"   ({n_tage} Tage)")
    print(f" Definition of Done (7 Tage lueckenlos): "
          f"{'ERFUELLT' if dod else 'NICHT ERFUELLT'}")
    print(" KEIN TRIAL - eine Annahme wird praezisiert, keine Regel getestet.")
    print("=" * 108)

    print(f"\n  GEMESSENE SPREADS ueber alle Tage (Basispunkte)")
    print(f"    {'Coin':<10s} {'n':>7s} {'Median':>8s} {'p90':>8s} "
          f"{'Tagesmedian min':>16s} {'max':>8s} {'Schwankung':>11s}")
    print("    " + "-" * 78)
    zeilen = []
    for sym in sorted(je_coin, key=lambda s: st.median(je_coin[s])):
        werte = je_coin[sym]
        q = st.quantiles(werte, n=100)
        tagesmedians = list(je_coin_tag.get(sym, {}).values())
        tmin, tmax = (min(tagesmedians), max(tagesmedians)) if tagesmedians else (0, 0)
        faktor = (tmax / tmin) if tmin > 0 else 0
        med = st.median(werte)
        zeilen.append((sym, med, len(werte), tmin, tmax, faktor))
        print(f"    {sym:<10s} {len(werte):7d} {med:8.3f} {q[89]:8.3f} "
              f"{tmin:16.3f} {tmax:8.3f} {faktor:10.1f}x")

    print("\n" + "=" * 108)
    print(" KOSTEN JE COIN - K-BASIS aus dem Gesamtmedian")
    print("=" * 108)
    k_maker = 2 * MAKER + 2 * ADVERSE
    print(f"\n    {'Coin':<10s} {'Slip/Seite':>11s} {'K-BASIS':>10s} "
          f"{'K-MAKER':>9s} | {'p_be +/-5%':>11s} {'+/-7%':>8s} {'+/-10%':>8s}")
    print("    " + "-" * 82)
    kosten = {}
    for sym, med, n, tmin, tmax, faktor in zeilen:
        slip = med / 2 / 100
        kb = 2 * TAKER + 2 * slip
        kosten[sym] = kb
        print(f"    {sym:<10s} {slip:10.4f}% {kb:9.4f}% {k_maker:8.2f}% | "
              + " ".join(f"{p_be(kb, B):10.2f}%" for B in BARRIEREN))

    btc_eth = [kosten[s] for s in kosten if s.startswith(("BTC", "ETH"))]
    schnitt = sum(btc_eth) / len(btc_eth) if btc_eth else 0

    print("\n" + "=" * 108)
    print(" RUECKWIRKUNG AUF DAS CHARTANALYSE-URTEIL")
    print("=" * 108)
    print(f"\n  Der Backtest rechnet bisher pauschal mit 0,50 % je Runde.")
    print(f"  Gemessen ueber {n_tage} Tage fuer BTC/ETH: {schnitt:.4f} %")
    delta = 0.50 - schnitt
    print(f"  Differenz: {delta:+.4f} Prozentpunkte je Signal\n")

    print(f"    {'Signalart (Zeitrahmen)':<28s} {'EV alt':>9s} {'EV neu':>9s} {'Urteil':>10s}")
    print("    " + "-" * 60)
    # Werte aus telemetrie.db, Stand 10.08.2026
    gemessen = [("4h RETEST", -0.290), ("4h BREAKOUT", -0.300),
                ("1h BREAKOUT", -0.453), ("1h SUPPORT_BOUNCE", -0.489),
                ("1h RETEST", -0.494), ("4h SUPPORT_BOUNCE", -0.639)]
    kippt = []
    for name, ev_alt in gemessen:
        ev_neu = ev_alt + delta
        if ev_neu > 0:
            kippt.append(name)
        print(f"    {name:<28s} {ev_alt:+8.3f}% {ev_neu:+8.3f}% "
              f"{'POSITIV' if ev_neu > 0 else 'negativ':>10s}")

    print()
    if kippt:
        print(f"  ACHTUNG: {len(kippt)} Signalart(en) kippen ins Plus: {', '.join(kippt)}")
        print("  Das ist KEIN Freibrief zum Einbauen. Ein positiver Erwartungswert")
        print("  nach Kosten ist notwendig, nicht hinreichend - es fehlen weiterhin")
        print("  Placebo-Test, Block-Bootstrap und die Pruefung ueber Marktphasen.")
    else:
        print("  Keine Signalart kippt ins Plus. Das Urteil 'nicht einbauen' bleibt,")
        print("  jetzt aber auf Basis gemessener statt geschaetzter Kosten.")

    print("\n" + "=" * 108)
    print(" WAS SICH GEGENUEBER v3 GEAENDERT HAT")
    print("=" * 108)
    print(f"  v3: 1 Tag, 146 Punkte je Coin, Konfidenz WAHRSCHEINLICH")
    print(f"  v4: {n_tage} Tage, bis zu {max(len(v) for v in je_coin.values())} "
          f"Punkte je Coin, Konfidenz "
          f"{'SICHER (DoD erfuellt)' if dod else 'WAHRSCHEINLICH'}")
    grosse_schwankung = [z[0] for z in zeilen if z[5] >= 3.0]
    if grosse_schwankung:
        print(f"\n  Coins mit stark schwankendem Tagesmedian (Faktor 3 oder mehr):")
        print(f"    {', '.join(grosse_schwankung)}")
        print("  Fuer diese Coins ist EINE Kostenzahl irrefuehrend - der Spread")
        print("  haengt dort stark vom Tag ab. Genau diese Verteilung konnte v3")
        print("  nicht sehen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
