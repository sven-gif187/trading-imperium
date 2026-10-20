# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Stufe 5b: Ueberlebenden-Gegenprobe und Messlatten je Teilzeitraum.
  - Universum NUR BTC+ETH (2017 schon die Groessten - kaum Auswahl im Rueckblick): M1/M2/M3/K1/K2/K3
  - alle Strategien je Teilzeitraum P1 2018-2020, P2 2021, P3 2022-heute, K = 0,15 und 0,50
Ergebnis: ergebnisse/stufe5b.json
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import backtest as bt  # noqa: E402
from stufe5 import PERIODEN  # noqa: E402

FABRIK = {"M1 BTC halten": bt.M1BTCHalten, "M2 Korb gleich": bt.M2Korb, "M3 BTC-200": bt.M3BTC200,
          "K1 Trend": bt.K1Trend, "K2 Trend+Filter": lambda: bt.K1Trend(filter_btc200=True),
          "K3 Rotation": bt.K3Rotation}


def main():
    m = bt.Markt.laden()
    start = m.datum[200]
    alle = list(bt.COINS)
    out = {}
    for universum, coins in (("12 Coins", alle), ("nur BTC+ETH", ["BTC", "ETH"])):
        for name, f in FABRIK.items():
            if universum == "nur BTC+ETH" and name == "K3 Rotation":
                f = lambda: bt.K3Rotation(top=1, band=2)          # Top 3 aus 2 Coins geht nicht -> Top 1, Band 2
                name = "K3 Rotation (Top 1/Band 2)"
            bt.COINS[:] = coins
            try:
                s = f()
                z = bt.ziele_berechnen(s, m, start)
                for k in (0.15, 0.50):
                    e = bt.simuliere(s, m, k, start, ziele=z)
                    g = bt.kennzahlen(e)
                    zeile = {"jahr": g["rendite_jahr_pct"], "mdd": g["max_rueckgang_pct"], "sharpe": g["sharpe"]}
                    for p, (a, b) in PERIODEN.items():
                        x = bt.kennzahlen(e, a, b)
                        zeile[p] = (x.get("rendite_jahr_pct"), x.get("sharpe"), x.get("max_rueckgang_pct"))
                    out[f"{universum} | {name} | K{k}"] = zeile
                    print(f"{universum:11s} {name:28s} K{k:4.2f} Jahr {zeile['jahr']:7.1f} % MaxDD {zeile['mdd']:6.1f} % "
                          f"Sharpe {zeile['sharpe']:5.2f} | P1 {zeile['P1 2018-2020'][0]} / {zeile['P1 2018-2020'][1]} "
                          f"| P2 {zeile['P2 2021'][0]} / {zeile['P2 2021'][1]} | P3 {zeile['P3 2022-heute'][0]} / {zeile['P3 2022-heute'][1]}",
                          flush=True)
            finally:
                bt.COINS[:] = alle
    (HIER / "ergebnisse" / "stufe5b.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
