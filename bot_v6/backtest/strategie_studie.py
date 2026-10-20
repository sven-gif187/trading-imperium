# -*- coding: utf-8 -*-
"""
backtest/strategie_studie.py - Was traegt wirklich?  [E11 29.07.2026]
====================================================================
    python backtest/strategie_studie.py

Der Ausstiegsvergleich hat gezeigt, dass die Frage falsch gestellt war.
Alte und neue Leiter enden im Testjahr beide bei rund -450 $ von 500 $
und 90 % Rueckgang - der Unterschied zwischen ihnen ist Rauschen auf
einem Totalschaden.

Der Grund steht in den Daten:

    Testzeitraum 2025-07-29 .. 2026-07-29
    BTC  -45 %   ETH  -49 %   SOL  -59 %   ADA  -79 %   DOGE -68 %
    Fear & Greed unter 30 an 242 von 366 Tagen (66 %)

Die Einstiegsregel des Bots lautet "kaufe, wenn der Index unter 30 steht,
und mittle nach, wenn es 2 % weiter faellt". In diesem Jahr heisst das:
ein Jahr lang in einen Absturz hineinkaufen und die Verluste vergroessern.

Diese Studie prueft deshalb der Reihe nach, WELCHE Aenderung traegt:
Ausstieg, Nachkauf-Verhalten, oder Einstiegsfilter. Alles gegen dieselben
Kerzen, jeweils nur eine Variable veraendert.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.ausstieg_backtest import Lauf, ALTE_LEITER, NEUE_LEITER, lade_kerzen, lade_fear_greed

COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "ADA/USDC", "AVAX/USDC",
         "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC", "UNI/USDC",
         "ATOM/USDC"]

TAG = 96          # 15m-Kerzen je Tag


def lade(von=None, bis=None, marke=""):
    d = {}
    for c in COINS:
        k = lade_kerzen(c, marke=marke)
        if not k:
            continue
        if von or bis:
            k = [x for x in k if (von is None or x[0] >= von) and (bis is None or x[0] < bis)]
        if k:
            d[c] = k
    return d, lade_fear_greed()


def kopf(titel):
    print("\n" + "=" * 104)
    print(" " + titel)
    print("=" * 104)
    print(f"  {'Variante':<40s} {'Trades':>6s} {'Ende$':>8s} {'Summe':>9s} "
          f"{'WR%':>5s} {'R/R':>5s} {'PF':>5s} {'MaxDD':>6s}")
    print("  " + "-" * 100)


def zeile(bez, e):
    print(f"  {bez:<40s} {e['trades']:6d} {e['endkapital']:8.0f} {e['summe']:+9.2f} "
          f"{e['wr']:5.1f} {e['rr']:5.2f} {e['profitfaktor']:5.2f} {e['drawdown']:6.1f}")
    return e


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--marke", default="", help='"" = letztes Jahr, "_v1" = Vorjahr')
    a = ap.parse_args()
    daten, fg = lade(marke=a.marke)
    if not daten:
        print("Keine Daten. Erst: python backtest/daten_holen.py")
        return 1
    z = sorted({k[0] for ks in daten.values() for k in ks})
    v = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")
    print(f"Daten: {len(daten)} Coins, {v(z[0])} .. {v(z[-1])}")

    ergebnisse = {}

    # ---------------------------------------------------------------
    kopf("SCHRITT 1 - Ausstiegsregel (die urspruengliche Frage)")
    ergebnisse["alt"] = zeile("alte Leiter, alles andere wie Bot",
                              Lauf(ALTE_LEITER, "alt", breakeven=False).laufe(daten, fg))
    ergebnisse["neu"] = zeile("neue Ratsche + Breakeven",
                              Lauf(NEUE_LEITER, "neu", breakeven=True).laufe(daten, fg))
    print("\n  -> Der Unterschied ist Rauschen. Die Ausstiegsregel ist nicht das Problem.")

    # ---------------------------------------------------------------
    kopf("SCHRITT 2 - Nachkaufen (Mitteln nach unten)")
    for stufen, bez in ((3, "bis 3 Nachkauf-Stufen (wie Bot)"),
                        (2, "bis 2 Stufen"),
                        (1, "GAR KEIN Nachkaufen")):
        ergebnisse[f"stufen{stufen}"] = zeile(
            bez, Lauf(NEUE_LEITER, "x", breakeven=True, max_stufen=stufen).laufe(daten, fg))

    # ---------------------------------------------------------------
    kopf("SCHRITT 3 - Stop-Loss-Weite")
    for sl in (1.5, 2.5, 4.0, 6.0):
        ergebnisse[f"sl{sl}"] = zeile(
            f"Stop-Loss {sl} %",
            Lauf(NEUE_LEITER, "x", breakeven=True, stop_loss_pct=sl).laufe(daten, fg))

    # ---------------------------------------------------------------
    kopf("SCHRITT 4 - EINSTIEGSFILTER (der eigentliche Hebel)")
    ergebnisse["kein_filter"] = zeile(
        "ohne Filter (wie Bot heute)",
        Lauf(NEUE_LEITER, "x", breakeven=True).laufe(daten, fg))
    for bars, bez in ((5 * TAG, "Coin ueber 5-Tage-Schnitt"),
                      (20 * TAG, "Coin ueber 20-Tage-Schnitt"),
                      (50 * TAG, "Coin ueber 50-Tage-Schnitt")):
        ergebnisse[f"trend{bars}"] = zeile(
            bez, Lauf(NEUE_LEITER, "x", breakeven=True, trend_sma_bars=bars).laufe(daten, fg))
    for bars, bez in ((20 * TAG, "BTC ueber 20-Tage-Schnitt (Marktfilter)"),
                      (50 * TAG, "BTC ueber 50-Tage-Schnitt (Marktfilter)"),
                      (100 * TAG, "BTC ueber 100-Tage-Schnitt (Marktfilter)")):
        ergebnisse[f"markt{bars}"] = zeile(
            bez, Lauf(NEUE_LEITER, "x", breakeven=True, markt_sma_bars=bars).laufe(daten, fg))

    # ---------------------------------------------------------------
    kopf("SCHRITT 5 - Kombination der besten Bausteine")
    ergebnisse["kombi"] = zeile(
        "Marktfilter 50T + kein Nachkauf",
        Lauf(NEUE_LEITER, "x", breakeven=True, markt_sma_bars=50 * TAG,
             max_stufen=1).laufe(daten, fg))
    ergebnisse["kombi2"] = zeile(
        "Marktfilter 50T + Coinfilter 20T + kein NK",
        Lauf(NEUE_LEITER, "x", breakeven=True, markt_sma_bars=50 * TAG,
             trend_sma_bars=20 * TAG, max_stufen=1).laufe(daten, fg))
    ergebnisse["kombi3"] = zeile(
        "wie oben + Stop 4 %",
        Lauf(NEUE_LEITER, "x", breakeven=True, markt_sma_bars=50 * TAG,
             trend_sma_bars=20 * TAG, max_stufen=1, stop_loss_pct=4.0).laufe(daten, fg))
    ergebnisse["kombi_alt"] = zeile(
        "wie oben, aber ALTE Ausstiegsleiter",
        Lauf(ALTE_LEITER, "x", breakeven=False, markt_sma_bars=50 * TAG,
             trend_sma_bars=20 * TAG, max_stufen=1, stop_loss_pct=4.0).laufe(daten, fg))

    print("\n" + "=" * 104)
    print(" Zum Vergleich: einfach BTC kaufen und liegen lassen (Buy & Hold)")
    btc = daten["BTC/USDC"]
    bh = (btc[-1][4] / btc[0][4] - 1) * 100
    print(f"   BTC ueber denselben Zeitraum: {bh:+.1f} %  ->  aus 500 $ werden {500*(1+bh/100):.0f} $")
    print("=" * 104)
    return 0


if __name__ == "__main__":
    sys.exit(main())
