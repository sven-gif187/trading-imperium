# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] V4-Journal-Forensik zu Block 1.3/1.4, 04.08.2026.
"""
Read-only. Liest ausschliesslich v4_referenz/ und schreibt nichts dorthin.

Beantwortet:
  1.3  Sind die V4-Zahlen brutto oder netto? Wieviel DCA haengt an den
       drei positiven Strategien?
  1.4  Gewinn-/Verlustverteilung, Tail-Risiko, Stabilitaet der Trefferquote.

GEBUEHRENBEFUND, der die Rechnung traegt:
  PaperExchange verrechnet Kosten implizit in der Ausfuehrung
  (trading_imperium_v4_25_ALARM.py:741-767):
      BUY   price*1.001 (Slippage)  und  qty=(quote/price)*0.999 (Fee)
      SELL  price*0.999 (Slippage)  und  quote=qty*price*0.999 (Fee)
  ABER _execute_sell:6151-6154 verwirft den Order-Rueckgabewert und rechnet
      pnl = (qty * price) - (qty * entry)
  mit dem MARKTPREIS statt dem Fill-Preis. Die Verkaufsseite (0,1 %
  Slippage + 0,1 % Fee) fehlt damit vollstaendig in der journalisierten
  pnl, die Kaufseiten-Fee wurde als Mengenabzug realisiert und faellt aus
  der Differenzformel heraus.
  Dieses Skript beziffert die Luecke je Strategie.

KEINE Hypothesenpruefung, kein p-Wert, kein neuer Trial - reine
deskriptive Journal-Forensik.
"""
import json
import os
import sys
from collections import defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
V4 = os.path.join(PROJEKT, "v4_referenz")
JOURNAL = os.path.join(V4, "trades_log_v4.json")
STATS = os.path.join(V4, "strategy_stats.json")
STATS_V6 = os.path.join(PROJEKT, "v4_data", "strategy_stats.json")

# Aus der Ausfuehrung, nicht geschaetzt:
FEE_VERKAUF = 0.002      # 0,1 % Slippage + 0,1 % Fee, in pnl NICHT enthalten
FEE_KAUF = 0.001         # 0,1 % Fee, als Mengenabzug realisiert


def perz(xs, q):
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def kopf(t):
    print("\n" + "=" * 100)
    print(" " + t)
    print("=" * 100)


def main():
    trades = json.load(open(JOURNAL, encoding="utf-8"))
    trades.sort(key=lambda x: x.get("time", ""))
    print(f"Journal: {len(trades)} Eintraege, "
          f"{trades[0]['time'][:19]} .. {trades[-1]['time'][:19]}")

    # ---------------------------------------------------------------- 1.3
    # Positionsverfolgung je Coin: Erstkauf traegt die Strategie, DCA nicht.
    kopf("1.3  DCA-ZUORDNUNG - welcher Strategie gehoert der Nachkauf?")
    offen = {}                      # coin -> dict(strategie, einsatz, dca_n, dca_summe)
    zu_strategie = defaultdict(lambda: dict(
        erst_n=0, erst_summe=0.0, dca_n=0, dca_summe=0.0,
        sells=0, pnl=0.0, einsatz_bei_sell=[]))
    waise_dca = dict(n=0, summe=0.0)
    verkaeufe = defaultdict(list)   # strategie -> [(pnl, einsatz, coin, zeit)]

    for t in trades:
        typ = t.get("type")
        coin = t.get("coin")
        if typ == "BUY":
            s = t.get("strategy") or "OHNE"
            betrag = float(t.get("amount", 0) or 0)
            if coin in offen:
                # Zweiter BUY auf offene Position: wie ein Nachkauf behandeln
                offen[coin]["einsatz"] += betrag
                offen[coin]["dca_n"] += 1
                offen[coin]["dca_summe"] += betrag
                zu_strategie[offen[coin]["strategie"]]["dca_n"] += 1
                zu_strategie[offen[coin]["strategie"]]["dca_summe"] += betrag
            else:
                offen[coin] = dict(strategie=s, einsatz=betrag,
                                   dca_n=0, dca_summe=0.0)
                zu_strategie[s]["erst_n"] += 1
                zu_strategie[s]["erst_summe"] += betrag
        elif typ == "DCA":
            betrag = float(t.get("amount", 0) or 0)
            if coin in offen:
                offen[coin]["einsatz"] += betrag
                offen[coin]["dca_n"] += 1
                offen[coin]["dca_summe"] += betrag
                zu_strategie[offen[coin]["strategie"]]["dca_n"] += 1
                zu_strategie[offen[coin]["strategie"]]["dca_summe"] += betrag
            else:
                waise_dca["n"] += 1
                waise_dca["summe"] += betrag
        elif typ in ("SELL", "MANUAL_SELL"):
            s = t.get("strategy") or "OHNE"
            pnl = float(t.get("pnl", 0) or 0)
            pos = offen.pop(coin, None)
            einsatz = pos["einsatz"] if pos else 0.0
            # Der Verkauf wird der Strategie zugeschrieben, die das Journal
            # nennt - genau wie in der externen Auswertung.
            zu_strategie[s]["sells"] += 1
            zu_strategie[s]["pnl"] += pnl
            zu_strategie[s]["einsatz_bei_sell"].append(einsatz)
            verkaeufe[s].append((pnl, einsatz, coin, t.get("time", "")))

    print(f"\n  DCA-Eintraege ohne offene Position (nicht zuordenbar): "
          f"{waise_dca['n']}, Volumen {waise_dca['summe']:.2f}$")
    print(f"\n  {'Strategie':<20s} {'Erst':>5s} {'ErstVol':>10s} "
          f"{'DCA':>5s} {'DCA-Vol':>11s} {'DCA/Erst':>9s}")
    for s in sorted(zu_strategie, key=lambda x: -zu_strategie[x]["dca_summe"]):
        d = zu_strategie[s]
        if d["erst_n"] == 0 and d["dca_n"] == 0:
            continue
        q = d["dca_summe"] / d["erst_summe"] if d["erst_summe"] else 0.0
        print(f"  {s:<20s} {d['erst_n']:5d} {d['erst_summe']:10.0f}$ "
              f"{d['dca_n']:5d} {d['dca_summe']:11.0f}$ {q:8.2f}x")

    # ---------------------------------------------------------- Gebuehren
    kopf("1.3  BRUTTO ODER NETTO? Gebuehrenluecke je Strategie")
    print("\n  Formel: fehlend = Einsatz * (FEE_VERKAUF + FEE_KAUF)")
    print(f"          FEE_VERKAUF={FEE_VERKAUF:.3f} (Slippage+Fee, in pnl "
          f"NICHT enthalten)")
    print(f"          FEE_KAUF   ={FEE_KAUF:.3f} (als Mengenabzug realisiert, "
          f"faellt aus der Differenzformel)")
    print(f"\n  {'Strategie':<20s} {'Sells':>6s} {'pnl roh':>10s} "
          f"{'Einsatz':>11s} {'Gebuehr':>10s} {'pnl netto':>11s} "
          f"{'je Trade':>9s}")
    netto = {}
    for s in sorted(zu_strategie, key=lambda x: -zu_strategie[x]["pnl"]):
        d = zu_strategie[s]
        if d["sells"] == 0:
            continue
        einsatz = sum(d["einsatz_bei_sell"])
        geb = einsatz * (FEE_VERKAUF + FEE_KAUF)
        n = d["pnl"] - geb
        netto[s] = n
        print(f"  {s:<20s} {d['sells']:6d} {d['pnl']:9.2f}$ "
              f"{einsatz:10.0f}$ {geb:9.2f}$ {n:10.2f}$ "
              f"{n/d['sells']:8.3f}$")
    print(f"\n  SUMME netto ueber alle Strategien: "
          f"{sum(netto.values()):.2f}$")

    # ---------------------------------------------------------------- 1.4
    kopf("1.4  VERTEILUNG UND TAIL-RISIKO je Strategie")
    print(f"\n  {'Strategie':<20s} {'n':>4s} {'Summe':>9s} {'Median':>8s} "
          f"{'p10':>8s} {'p90':>8s} {'maxVerl':>9s} {'Top3 %':>7s} "
          f"{'nachTop3':>9s}")
    for s in sorted(verkaeufe, key=lambda x: -zu_strategie[x]["pnl"]):
        v = [x[0] for x in verkaeufe[s]]
        if len(v) < 3:
            continue
        summe = sum(v)
        gew = sorted([x for x in v if x > 0], reverse=True)
        top3 = sum(gew[:3])
        ohne_top3 = summe - top3
        anteil = top3 / summe * 100 if summe > 0 else float("nan")
        print(f"  {s:<20s} {len(v):4d} {summe:8.2f}$ {perz(v,0.5):7.2f}$ "
              f"{perz(v,0.1):7.2f}$ {perz(v,0.9):7.2f}$ {min(v):8.2f}$ "
              f"{anteil:6.1f}% {ohne_top3:8.2f}$")

    kopf("1.4  TAIL-RISIKO: wie viele Gewinner frisst der groesste Verlust?")
    print(f"\n  {'Strategie':<20s} {'maxVerl':>9s} {'avgGewinn':>10s} "
          f"{'frisst':>8s} {'Gewinner':>9s} {'Puffer':>8s}")
    for s in sorted(verkaeufe, key=lambda x: -zu_strategie[x]["pnl"]):
        v = [x[0] for x in verkaeufe[s]]
        if len(v) < 3:
            continue
        gew = [x for x in v if x > 0]
        if not gew:
            continue
        avg_g = sum(gew) / len(gew)
        mv = min(v)
        frisst = abs(mv) / avg_g if avg_g > 0 else float("inf")
        puffer = len(gew) / frisst if frisst > 0 else float("inf")
        print(f"  {s:<20s} {mv:8.2f}$ {avg_g:9.3f}$ {frisst:7.1f}x "
              f"{len(gew):9d} {puffer:7.1f}x")
    print("\n  'frisst' = wieviele Durchschnittsgewinne der groesste "
          "Einzelverlust aufzehrt.")
    print("  'Puffer'  = Zahl der Gewinner geteilt durch 'frisst'. "
          "Unter 2 ist die Serie fragil.")

    # ------------------------------------------------- Stats-Gegenprobe
    kopf("QUELLENVERGLEICH: V6 liest andere Zahlen als V4 heute fuehrt")
    a = json.load(open(STATS_V6, encoding="utf-8"))
    b = json.load(open(STATS, encoding="utf-8"))
    print(f"\n  v4_data/strategy_stats.json      mtime "
          f"{os.path.getmtime(STATS_V6):.0f} -> "
          f"{__import__('datetime').datetime.fromtimestamp(os.path.getmtime(STATS_V6)):%Y-%m-%d %H:%M}")
    print(f"  v4_referenz/strategy_stats.json  mtime -> "
          f"{__import__('datetime').datetime.fromtimestamp(os.path.getmtime(STATS)):%Y-%m-%d %H:%M}")
    print(f"\n  {'Strategie':<20s} {'V6-Quelle pnl':>14s} {'V4 heute pnl':>14s} "
          f"{'Journal 1M netto':>17s}")
    for s in sorted(set(a) | set(b)):
        pa = a.get(s, {}).get("total_pnl")
        pb = b.get(s, {}).get("total_pnl")
        pj = netto.get(s)
        print(f"  {s:<20s} "
              f"{('%.2f$' % pa) if pa is not None else '-':>14s} "
              f"{('%.2f$' % pb) if pb is not None else '-':>14s} "
              f"{('%.2f$' % pj) if pj is not None else '-':>17s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
