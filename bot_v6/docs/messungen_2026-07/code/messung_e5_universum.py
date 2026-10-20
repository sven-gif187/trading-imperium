# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
E5 - Coin-Universum.

a) Kennzahlen je Coin, beide Jahre getrennt, aus dem VOLLEN Portfoliolauf
   (11 Coins). Wichtig: diese Zahlen sind durch Cash-Konkurrenz und
   max_open_positions=5 verkoppelt - ein Coin kann Trades nur machen, wenn
   Geld und ein Slot frei sind. Sie sind daher NICHT identisch mit dem,
   was der Coin allein erwirtschaften wuerde.
b) Vier Universen als eigene Portfoliolaeufe.
c) Anteil Trades unter der Reibungsschwelle 0,3 % (0,1 % Gebuehr + 0,05 %
   Slippage je Seite) - je Coin.
d) Korrelation der Tagesrenditen, getrennt nach Marktphase.

SPALTEN: [V] vergleichbar, [!] absolute $-Zahl, nicht live-uebertragbar.
"""
import sys
from harness_ext import (LaufMess, NEUE_LEITER, lade_jahr, kennzahlen,
                         median, COINS, TAG_MS)

REIBUNG = 0.3     # % Brutto-Bewegung, die eine Runde nur die Kosten deckt


def lauf(daten, fg, name):
    L = LaufMess(NEUE_LEITER, name, breakeven=True, stop_loss_pct=2.5)
    L.laufe(daten, fg)
    return L


def je_coin(L):
    d = {}
    for t in L.trades:
        d.setdefault(t["symbol"], []).append(t)
    return d


def tabelle_coins(L, titel):
    print(f"\n  {titel}")
    print(f"    {'Coin':<10s} {'Trad':>5s} {'WR%':>5s} {'R/R':>5s} {'BE-RR':>6s} "
          f"{'EV(R)':>7s} | {'NettoP&L$':>10s} {'EV$/Tr':>8s} {'Geb$':>7s} | "
          f"{'Halt_h':>7s} | {'<0,3%':>6s} {'0..0,3%':>8s}")
    print(f"    {'':<10s} {'[V]':>5s} {'[V]':>5s} {'[V]':>5s} {'[V]':>6s} "
          f"{'[V]':>7s} | {'[!]':>10s} {'[!]':>8s} {'[!]':>7s} | "
          f"{'[V]':>7s} | {'[V]':>6s} {'[V]':>8s}")
    print("    " + "-" * 108)
    rows = []
    for coin, tr in je_coin(L).items():
        k = kennzahlen(tr)
        klein = sum(1 for t in tr if abs(t["brutto_pct"]) < REIBUNG) / len(tr) * 100
        klein_pos = sum(1 for t in tr if 0 <= t["brutto_pct"] < REIBUNG) / len(tr) * 100
        rows.append((k["ev_r"], coin, k, klein, klein_pos))
    rows.sort(reverse=True)
    for ev_r, coin, k, klein, klein_pos in rows:
        be = k["be_rr"]
        be_s = f"{be:6.2f}" if be != float("inf") else "   inf"
        print(f"    {coin:<10s} {k['n']:5d} {k['wr']:5.1f} {k['rr']:5.2f} {be_s} "
              f"{k['ev_r']:+7.3f} | {k['summe']:+10.2f} {k['ev']:+8.3f} "
              f"{k['geb']:7.2f} | {k['halte']:7.1f} | {klein:5.1f}% {klein_pos:7.1f}%")
    return {coin: k for _, coin, k, _, _ in rows}


# ---------------------------------------------------------------- Korrelation
def tagesrenditen(kerzen):
    tage = {}
    for t, o, hi, lo, cl in kerzen:
        tage[t // TAG_MS] = cl
    reihe = sorted(tage.items())
    out = {}
    for i in range(1, len(reihe)):
        d0, c0 = reihe[i - 1]
        d1, c1 = reihe[i]
        if c0 > 0:
            out[d1] = (c1 / c0 - 1)
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / (sxx * syy) ** 0.5


def sma_tage(kerzen, laenge=50):
    tage = {}
    for t, o, hi, lo, cl in kerzen:
        tage[t // TAG_MS] = cl
    reihe = sorted(tage.items())
    out, fenster = {}, []
    for d, c in reihe:
        # nur ABGESCHLOSSENE Vortage -> kein Look-ahead
        out[d] = (sum(fenster) / len(fenster)) if len(fenster) == laenge else None
        fenster.append(c)
        if len(fenster) > laenge:
            fenster.pop(0)
    return out, dict(reihe)


def korrelation(daten, titel):
    ren = {s: tagesrenditen(ks) for s, ks in daten.items()}
    btc = ren.get("BTC/USDC", {})
    sma, closes = sma_tage(daten["BTC/USDC"], 50)

    mengen = {
        "alle Tage": lambda d: True,
        "BTC-Tag positiv": lambda d: btc.get(d, 0) > 0,
        "BTC-Tag negativ": lambda d: btc.get(d, 0) < 0,
        "BTC ueber 50T-SMA": lambda d: sma.get(d) is not None and closes.get(d, 0) > sma[d],
        "BTC unter 50T-SMA": lambda d: sma.get(d) is not None and closes.get(d, 0) <= sma[d],
    }
    syms = sorted(ren)
    print(f"\n  {titel}")
    print(f"    {'Teilmenge':<20s} {'Tage':>5s} {'mittl.Korr':>11s} "
          f"{'min':>7s} {'max':>7s} {'Paare':>6s}")
    for bez, filt in mengen.items():
        tage = [d for d in btc if filt(d)]
        tset = set(tage)
        werte = []
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                a, b = ren[syms[i]], ren[syms[j]]
                gem = [d for d in tset if d in a and d in b]
                if len(gem) < 20:
                    continue
                r = pearson([a[d] for d in gem], [b[d] for d in gem])
                if r is not None:
                    werte.append(r)
        if werte:
            print(f"    {bez:<20s} {len(tage):5d} {sum(werte)/len(werte):11.3f} "
                  f"{min(werte):7.3f} {max(werte):7.3f} {len(werte):6d}")


def main():
    jahre = [("Jahr 2  2025-07..2026-07", ""), ("Jahr 1  2024-07..2025-07", "_v1")]
    ev_je_jahr = {}

    for jahr_bez, marke in jahre:
        daten, fg = lade_jahr(marke)
        print("\n" + "=" * 118)
        print(f" E5a  Kennzahlen je Coin aus dem Portfoliolauf ({len(daten)} Coins)  -  {jahr_bez}")
        print("=" * 118)
        L = lauf(daten, fg, jahr_bez)
        ev_je_jahr[marke] = tabelle_coins(L, "sortiert nach Erwartungswert je Trade in R")
        sys.stdout.flush()

    # ---------------- E5b Universen ----------------
    pos_j1 = [c for c, k in ev_je_jahr["_v1"].items() if k["ev_r"] > 0]
    pos_j2 = [c for c, k in ev_je_jahr[""].items() if k["ev_r"] > 0]
    print("\n" + "=" * 118)
    print(" E5b  Universen")
    print("=" * 118)
    print(f"  Coins mit EV(R) > 0 in Jahr 1: {pos_j1 if pos_j1 else 'KEINE'}")
    print(f"  Coins mit EV(R) > 0 in Jahr 2: {pos_j2 if pos_j2 else 'KEINE'}")
    ueberlapp = sorted(set(pos_j1) & set(pos_j2))
    print(f"  Schnittmenge beider Jahre    : {ueberlapp if ueberlapp else 'LEER'}")

    universen = [
        ("1) nur BTC", ["BTC/USDC"]),
        ("2) BTC+ETH", ["BTC/USDC", "ETH/USDC"]),
        ("3) alle 11 (IST)", COINS),
    ]
    if pos_j1:
        universen.append((f"4) EV>0 aus Jahr 1 (n={len(pos_j1)})", pos_j1))

    for jahr_bez, marke in jahre:
        print(f"\n  {jahr_bez}")
        print(f"    {'Universum':<28s} {'Trad':>5s} {'WR%':>5s} {'R/R':>5s} "
              f"{'BE-RR':>6s} {'EV(R)':>7s} | {'NettoP&L$':>10s} {'EV$/Tr':>8s} "
              f"{'Geb$':>8s} | {'Halt_h':>7s}")
        print(f"    {'':<28s} {'[V]':>5s} {'[V]':>5s} {'[V]':>5s} {'[V]':>6s} "
              f"{'[V]':>7s} | {'[!]':>10s} {'[!]':>8s} {'[!]':>8s} | {'[V]':>7s}")
        print("    " + "-" * 100)
        for bez, liste in universen:
            daten, fg = lade_jahr(marke, coins=liste)
            if not daten:
                continue
            L = lauf(daten, fg, bez)
            k = kennzahlen(L.trades)
            be = k["be_rr"]
            be_s = f"{be:6.2f}" if be != float("inf") else "   inf"
            marker = "  <- In-Sample" if bez.startswith("4)") and marke == "_v1" else ""
            print(f"    {bez:<28s} {k['n']:5d} {k['wr']:5.1f} {k['rr']:5.2f} {be_s} "
                  f"{k['ev_r']:+7.3f} | {k['summe']:+10.2f} {k['ev']:+8.3f} "
                  f"{k['geb']:8.2f} | {k['halte']:7.1f}{marker}")
            sys.stdout.flush()

    # ---------------- E5c Reibung ----------------
    print("\n" + "=" * 118)
    print(" E5c  Reibungsschwelle: Anteil Trades mit |Bruttobewegung| < 0,3 %")
    print("      Kontext: Median der absoluten Tagesrendite je Coin (Volatilitaetsmass)")
    print("=" * 118)
    for jahr_bez, marke in jahre:
        daten, fg = lade_jahr(marke)
        L = lauf(daten, fg, marke)
        print(f"\n  {jahr_bez}")
        print(f"    {'Coin':<10s} {'Trad':>5s} {'|Brutto|<0,3%':>14s} "
              f"{'medAbsTagesRend':>16s} {'medAbs15mRange':>15s}")
        rows = []
        for coin, tr in je_coin(L).items():
            klein = sum(1 for t in tr if abs(t["brutto_pct"]) < REIBUNG) / len(tr) * 100
            tr_d = tagesrenditen(daten[coin])
            mtag = median([abs(x) * 100 for x in tr_d.values()])
            rng = median([(k[2] - k[3]) / k[4] * 100 for k in daten[coin] if k[4] > 0])
            rows.append((klein, coin, len(tr), mtag, rng))
        rows.sort(reverse=True)
        for klein, coin, n, mtag, rng in rows:
            print(f"    {coin:<10s} {n:5d} {klein:13.1f}% {mtag:15.2f}% {rng:14.3f}%")
        sys.stdout.flush()

    # ---------------- E5d Korrelation ----------------
    print("\n" + "=" * 118)
    print(" E5d  Korrelation der Tagesrenditen (Pearson, alle Coin-Paare)")
    print("=" * 118)
    for jahr_bez, marke in jahre:
        daten, fg = lade_jahr(marke)
        korrelation(daten, jahr_bez)
    return 0


if __name__ == "__main__":
    sys.exit(main())
