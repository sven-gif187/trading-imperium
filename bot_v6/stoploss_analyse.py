# -*- coding: utf-8 -*-
"""Stop-Loss-Analyse: Wo genau entsteht der Verlust - und was wuerde helfen?

AUSGANGSLAGE (Gesamtauswertung 10.08.2026, trades_v5.json)
    TRAILING_STOP    169 Faelle   +156,51 $   +0,926 $ je Trade
    DCA_FEAR_GREED   137 Faelle    +52,20 $   +0,381 $ je Trade
    STOP_LOSS         68 Faelle   -187,63 $   -2,759 $ je Trade   <- hier
    TREND_EXIT        46 Faelle    -36,08 $   -0,784 $ je Trade

Ein Stop-Loss frisst drei Trailing-Gewinne. Sinkt der mittlere Verlust von
2,76 auf 1,80 $, steht das System bei +43 statt -22 $ - bei GLEICHER
Trefferquote und ohne eine einzige neue Regel.

DIE ZENTRALE FRAGE - und warum "Stop enger" nicht automatisch richtig ist
------------------------------------------------------------------------
Ein engerer Stop macht jeden Einzelverlust kleiner. Er wirft aber auch
Positionen raus, die sich danach noch erholt haetten. Ob sich das lohnt,
haengt daran, WIE TIEF spaetere Gewinner zwischendurch im Minus standen.

Genau das steht seit dem 25.07.2026 im Journal: mae_pct (max adverse
excursion, tiefster Punkt) und mfe_pct (max favorable, hoechster Punkt).

Dieses Skript beantwortet drei Fragen:
  1. Wie verteilen sich die Stop-Loss-Verluste? Sind es viele mittlere
     oder wenige grosse?
  2. Wie tief mussten spaetere GEWINNER durchhalten? Das ist die Untergrenze
     fuer jeden sinnvollen Stop.
  3. Was haette ein anderer Stop-Abstand konkret bewirkt?

EHRLICHKEITSVERMERK
-------------------
MFE/MAE gibt es erst seit dem 25.07. Fuer aeltere Trades fehlen die Werte;
sie werden ausgewiesen, aber nicht mitgerechnet. Ist die Stichprobe klein,
steht das ausdruecklich dabei. Reine Leseoperation, aendert nichts.
"""
import json
import os
import statistics as st
import sys
from collections import defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HIER, "data_store", "trades_v5.json")

# Kosten je Runde, gemessen ueber 11 Capture-Tage (kosten_matrix_v4.py)
KOSTEN_PCT = 0.32


def linie(z="=", n=88):
    print(z * n)


def teil(t):
    print()
    linie()
    print(f" {t}")
    linie()


def lade():
    with open(JOURNAL, "r", encoding="utf-8") as f:
        return json.load(f)


def verkaeufe(trades):
    out = []
    for t in trades:
        if str(t.get("type", "")).upper() != "SELL":
            continue
        p = t.get("pnl")
        if not isinstance(p, (int, float)):
            continue
        out.append(t)
    return out


def verteilung(werte, name, einheit="$"):
    if not werte:
        print(f"  {name}: keine Daten")
        return
    w = sorted(werte)
    n = len(w)
    print(f"  {name}  (n={n})")
    print(f"    kleinster {w[0]:+8.3f}{einheit}   groesster {w[-1]:+8.3f}{einheit}")
    print(f"    Median    {st.median(w):+8.3f}{einheit}   Mittel    "
          f"{sum(w)/n:+8.3f}{einheit}")
    if n >= 4:
        q = st.quantiles(w, n=4)
        print(f"    25 % unter {q[0]:+7.3f}{einheit}   75 % unter "
              f"{q[2]:+7.3f}{einheit}")


def main():
    trades = lade()
    v = verkaeufe(trades)

    linie()
    print(" STOP-LOSS-ANALYSE")
    print(f" Journal: {len(trades)} Eintraege, davon {len(v)} Verkaeufe mit P&L")
    linie()

    # ---------------------------------------------------------------
    teil("1. WIE VERTEILEN SICH DIE STOP-LOSS-VERLUSTE?")
    sl = [t for t in v if str(t.get("strategy")) == "STOP_LOSS"]
    if not sl:
        print("  Keine STOP_LOSS-Verkaeufe gefunden.")
        return 1
    pnl_usd = [float(t["pnl"]) for t in sl]
    pnl_pct = [float(t["pnl_pct"]) for t in sl
               if isinstance(t.get("pnl_pct"), (int, float))]
    print()
    verteilung(pnl_usd, "Verlust in Dollar")
    if pnl_pct:
        print()
        verteilung(pnl_pct, "Verlust in Prozent", "%")

    # Wie viel machen die schlimmsten 10 aus?
    schlimm = sorted(pnl_usd)[:10]
    print(f"\n  Die 10 groessten Einzelverluste: {sum(schlimm):+.2f} $ "
          f"von {sum(pnl_usd):+.2f} $ gesamt "
          f"({sum(schlimm)/sum(pnl_usd)*100:.0f} %)")
    print(f"  -> {'Wenige grosse Ausreisser' if sum(schlimm)/sum(pnl_usd) > 0.4 else 'Breit verteilt'}"
          f" dominieren das Bild.")

    # ---------------------------------------------------------------
    teil("2. WIE TIEF MUSSTEN SPAETERE GEWINNER DURCHHALTEN?")
    print("\n  Das ist die Untergrenze fuer jeden Stop: Wer enger stoppt als")
    print("  der tiefste Punkt spaeterer Gewinner, wirft Gewinner raus.\n")
    gewinner_mae = [abs(float(t["mae_pct"])) for t in v
                    if isinstance(t.get("mae_pct"), (int, float))
                    and float(t["pnl"]) > 0]
    verlierer_mae = [abs(float(t["mae_pct"])) for t in v
                     if isinstance(t.get("mae_pct"), (int, float))
                     and float(t["pnl"]) <= 0]
    if not gewinner_mae:
        print("  KEINE MAE-Daten bei Gewinnern vorhanden.")
        print("  MFE/MAE wird erst seit 25.07.2026 protokolliert.")
    else:
        verteilung(gewinner_mae, "Tiefster Punkt spaeterer GEWINNER", "%")
        if len(gewinner_mae) < 20:
            print(f"\n  ACHTUNG: nur {len(gewinner_mae)} Gewinner mit MAE-Daten.")
            print("  Das ist zu wenig fuer eine belastbare Entscheidung.")
    if verlierer_mae:
        print()
        verteilung(verlierer_mae, "Tiefster Punkt der VERLIERER", "%")

    # ---------------------------------------------------------------
    teil("3. WAS HAETTE EIN ANDERER STOP BEWIRKT?")
    print("\n  Simulation ueber alle Verkaeufe MIT MAE-Daten. Ein Trade waere")
    print("  bei Stop X ausgestoppt worden, wenn sein tiefster Punkt unter")
    print("  -X % lag. Gewinner, die das trifft, verlieren ihren Gewinn.\n")
    mit_mae = [t for t in v if isinstance(t.get("mae_pct"), (int, float))]
    if len(mit_mae) < 10:
        print(f"  Nur {len(mit_mae)} Trades mit MAE-Daten - Simulation nicht")
        print("  aussagekraeftig. Erst weiter Daten sammeln.")
    else:
        print(f"  {'Stop':<7s}{'ausgestoppt':>13s}{'davon Gewinner':>16s}"
              f"{'P&L simuliert':>15s}{'gegen heute':>13s}")
        print("  " + "-" * 64)
        ist_pnl = sum(float(t["pnl"]) for t in mit_mae)
        for stop in (1.0, 1.5, 2.0, 2.5, 3.0):
            summe = 0.0
            getroffen = 0
            gew_getroffen = 0
            for t in mit_mae:
                mae = abs(float(t["mae_pct"]))
                pnl = float(t["pnl"])
                betrag = float(t.get("amount") or 0)
                if mae >= stop:
                    getroffen += 1
                    if pnl > 0:
                        gew_getroffen += 1
                    # Ausgestoppt: Verlust = Stop-Abstand plus Kosten
                    summe -= betrag * (stop + KOSTEN_PCT) / 100
                else:
                    summe += pnl
            print(f"  {stop:>4.1f}%{getroffen:13d}{gew_getroffen:16d}"
                  f"{summe:+14.2f}${summe - ist_pnl:+12.2f}$")
        print(f"\n  Heute (Stop 2.0 %, real gebucht): {ist_pnl:+.2f} $")
        print("  Die Simulation nimmt an, dass am Stop exakt gefuellt wird.")
        print("  In Wirklichkeit gibt es Gaps - die reale Zahl faellt schlechter aus.")

    # ---------------------------------------------------------------
    teil("4. TREND_EXIT - lohnt die Regel ueberhaupt?")
    te = [t for t in v if str(t.get("strategy")) == "TREND_EXIT"]
    if te:
        p = [float(t["pnl"]) for t in te]
        gew = sum(1 for x in p if x > 0)
        print(f"\n  {len(te)} Faelle, {gew} davon im Plus "
              f"({gew/len(te)*100:.1f} %), Summe {sum(p):+.2f} $")
        print(f"  Mittlerer Verlust je Fall: {sum(p)/len(p):+.3f} $")
        te_mae = [abs(float(t["mae_pct"])) for t in te
                  if isinstance(t.get("mae_pct"), (int, float))]
        if te_mae:
            print(f"  Tiefster Punkt dieser Trades: Median "
                  f"{st.median(te_mae):.2f} %, groesster {max(te_mae):.2f} %")
            unter_stop = sum(1 for m in te_mae if m < 2.0)
            print(f"  {unter_stop} von {len(te_mae)} waeren vom 2-%-Stop NICHT")
            print(f"  erfasst worden - die Regel steigt also frueher aus als noetig.")
    else:
        print("\n  Keine TREND_EXIT-Verkaeufe gefunden.")

    # ---------------------------------------------------------------
    teil("5. POSITIONSGROESSE - haengt der Verlust an der Groesse?")
    print("\n  Der Bot kauft mit 30 % unabhaengig vom Score. Wenn schwache")
    print("  Signale genauso gross gekauft werden wie starke, kostet das.\n")
    nach_score = defaultdict(lambda: {"n": 0, "pnl": 0.0, "gew": 0})
    for t in v:
        s = t.get("score") or t.get("signal_score")
        if not isinstance(s, (int, float)):
            continue
        d = nach_score[int(s)]
        d["n"] += 1
        d["pnl"] += float(t["pnl"])
        if float(t["pnl"]) > 0:
            d["gew"] += 1
    if nach_score:
        print(f"  {'Score':<8s}{'n':>6s}{'Quote':>8s}{'P&L':>11s}{'je Trade':>11s}")
        print("  " + "-" * 44)
        for s in sorted(nach_score):
            d = nach_score[s]
            print(f"  {s:<8d}{d['n']:6d}{d['gew']/d['n']*100:7.1f}%"
                  f"{d['pnl']:+10.2f}${d['pnl']/d['n']:+10.3f}$")
    else:
        print("  Keine Score-Daten in den Verkaufszeilen.")

    teil("FAZIT - was die Zahlen hergeben")
    print("\n  Entscheide NICHTS allein aus dieser Ausgabe, wenn oben ein")
    print("  ACHTUNG zur Stichprobengroesse steht. Bei duenner Datenlage ist")
    print("  weiter messen die bessere Wahl als eine Regel zu verstellen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
