# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit F3 vom 30.07.2026.
# Nicht archivieren - Beleg fuer den Vergleichsmassstab. Siehe ../README.md
"""
F3 - Der Vergleichsmassstab.

Was haetten stures BTC-Kaufen-und-Halten und woechentliches BTC-DCA mit
demselben Startkapital erwirtschaftet? Beide Jahre getrennt.

STARTKAPITAL
------------
500,00 $ - config.json trading.initial_paper_balance, identisch mit dem
Startkapital des Harness (backtest/ausstieg_backtest.py, Lauf(startkapital)).

REIBUNG
-------
Gleiches Modell wie ueberall: 0,100 % Gebuehr + 0,050 % Slippage je Seite
(engine.py:243/251, ausstieg_backtest.py:59/60). Kaufen-und-Halten zahlt
sie einmal beim Kauf; die Endbewertung erfolgt zum Schlusskurs OHNE
Verkaufskosten (Mark-to-Market) UND zusaetzlich mit Verkauf, damit beide
Lesarten nebeneinander stehen.

WOECHENTLICHES DCA
------------------
Startkapital wird in 52 gleiche Tranchen geteilt, je eine pro Woche zum
Schlusskurs des jeweiligen Wochenbeginns. Nicht investiertes Bargeld
verzinst sich nicht (0 %).

ZUSATZ
------
Gleichgewichtetes Halten aller 11 Coins - der fairere Massstab fuer einen
Bot, der 11 Coins handelt. Und das Live-Fenster des Journals
(10.06.-29.07.2026), damit F1e eine Bezugsgroesse hat.
"""
import sys
from datetime import datetime, timezone

from harness_ext import lade_jahr, COINS, TAG_MS
from messung_f_stat import median

START = 500.0
GEBUEHR = 0.001
SLIPPAGE = 0.0005
WOCHE_MS = 7 * TAG_MS


def _kaufkurs(p):
    return p * (1 + SLIPPAGE)


def _verkaufskurs(p):
    return p * (1 - SLIPPAGE)


def kaufen_halten(kerzen, kapital=START):
    """Einmal alles kaufen, bis zum Ende halten."""
    ein = kerzen[0]
    aus = kerzen[-1]
    geb = kapital * GEBUEHR
    menge = (kapital - geb) / _kaufkurs(ein[4])
    wert_mtm = menge * aus[4]
    erloes = menge * _verkaufskurs(aus[4])
    wert_verkauft = erloes - erloes * GEBUEHR
    # Verlauf fuer Drawdown
    verlauf = [menge * k[4] for k in kerzen]
    return {
        "einstieg": ein[4], "ausstieg": aus[4], "menge": menge,
        "mtm": wert_mtm, "verkauft": wert_verkauft,
        "pnl_mtm": wert_mtm - kapital, "pnl_verkauft": wert_verkauft - kapital,
        "gebuehren": geb + erloes * GEBUEHR,
        "mdd": max_drawdown(verlauf),
    }


def dca_woechentlich(kerzen, kapital=START, tranchen=52):
    """Kapital in gleiche Wochentranchen, je eine pro Woche."""
    t0 = kerzen[0][0]
    tranche = kapital / tranchen
    index = {k[0]: k for k in kerzen}
    zeiten = [k[0] for k in kerzen]
    menge = 0.0
    bar = kapital
    geb_summe = 0.0
    kaeufe = 0
    verlauf = []
    naechste = t0
    zeiger = 0
    for t in zeiten:
        while zeiger < len(zeiten) and naechste <= t and kaeufe < tranchen:
            k = index.get(t)
            if k is None:
                break
            geb = tranche * GEBUEHR
            menge += (tranche - geb) / _kaufkurs(k[4])
            bar -= tranche
            geb_summe += geb
            kaeufe += 1
            naechste += WOCHE_MS
        verlauf.append(bar + menge * index[t][4])
    aus = kerzen[-1][4]
    wert_mtm = bar + menge * aus
    erloes = menge * _verkaufskurs(aus)
    wert_verkauft = bar + erloes - erloes * GEBUEHR
    return {
        "kaeufe": kaeufe, "menge": menge, "restbar": bar,
        "mtm": wert_mtm, "verkauft": wert_verkauft,
        "pnl_mtm": wert_mtm - kapital, "pnl_verkauft": wert_verkauft - kapital,
        "gebuehren": geb_summe + erloes * GEBUEHR,
        "mdd": max_drawdown(verlauf),
    }


def gleichgewicht(daten, kapital=START):
    """Alle 11 Coins zu gleichen Teilen kaufen und halten."""
    coins = [c for c in COINS if daten.get(c)]
    je = kapital / len(coins)
    wert = 0.0
    geb = 0.0
    for c in coins:
        r = kaufen_halten(daten[c], je)
        wert += r["mtm"]
        geb += r["gebuehren"]
    return {"coins": len(coins), "mtm": wert, "pnl_mtm": wert - kapital,
            "gebuehren": geb}


def max_drawdown(verlauf):
    hoch = verlauf[0] if verlauf else 0.0
    mdd = 0.0
    for v in verlauf:
        if v > hoch:
            hoch = v
        if hoch > 0:
            mdd = max(mdd, (hoch - v) / hoch)
    return mdd * 100


def fenster(kerzen, von_iso, bis_iso):
    a = datetime.fromisoformat(von_iso).replace(tzinfo=timezone.utc).timestamp() * 1000
    b = datetime.fromisoformat(bis_iso).replace(tzinfo=timezone.utc).timestamp() * 1000
    return [k for k in kerzen if a <= k[0] <= b]


def zeitraum(kerzen):
    a = datetime.fromtimestamp(kerzen[0][0] / 1000, timezone.utc)
    b = datetime.fromtimestamp(kerzen[-1][0] / 1000, timezone.utc)
    return a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")


def main():
    print("=" * 100)
    print(" MESSUNG F3 - DER VERGLEICHSMASSSTAB")
    print(f" Startkapital {START:.2f} $ (config.json initial_paper_balance)")
    print(" Reibung 0,100 % Gebuehr + 0,050 % Slippage je Seite")
    print("=" * 100)

    jahre = [("Jahr 2", ""), ("Jahr 1", "_v1")]
    # Harness, Ist-Stop 2,5 %: J2 = Kontrollanker, J1 aus
    # ausgaben/messung_e2_stops_out.txt Zeile 38
    bot = {"Jahr 2": -450.56, "Jahr 1": -313.44}

    for bez, marke in jahre:
        daten, _fg = lade_jahr(marke)
        btc = daten["BTC/USDC"]
        von, bis = zeitraum(btc)
        print("\n" + "=" * 100)
        print(f" {bez}  {von} .. {bis}   ({len(btc)} 15m-Kerzen)")
        print("=" * 100)
        print(f"  BTC-Kurs: {btc[0][4]:,.2f} $  ->  {btc[-1][4]:,.2f} $   "
              f"({(btc[-1][4] / btc[0][4] - 1) * 100:+.2f} % brutto)")

        bh = kaufen_halten(btc)
        dca = dca_woechentlich(btc)
        eq = gleichgewicht(daten)

        print(f"\n    {'Strategie':<34s} {'Endwert $':>11s} {'P&L $':>10s} "
              f"{'P&L %':>8s} {'Geb. $':>8s} {'MaxDD %':>9s}")
        print("    " + "-" * 84)
        print(f"    {'BTC kaufen & halten (mark-to-market)':<34s} "
              f"{bh['mtm']:11.2f} {bh['pnl_mtm']:+10.2f} "
              f"{bh['pnl_mtm'] / START * 100:+7.2f}% {bh['gebuehren']:8.2f} "
              f"{bh['mdd']:8.1f}%")
        print(f"    {'BTC kaufen & halten (am Ende verk.)':<34s} "
              f"{bh['verkauft']:11.2f} {bh['pnl_verkauft']:+10.2f} "
              f"{bh['pnl_verkauft'] / START * 100:+7.2f}% "
              f"{bh['gebuehren']:8.2f} {bh['mdd']:8.1f}%")
        print(f"    {'BTC-DCA woechentlich (52 Tr., m2m)':<34s} "
              f"{dca['mtm']:11.2f} {dca['pnl_mtm']:+10.2f} "
              f"{dca['pnl_mtm'] / START * 100:+7.2f}% {dca['gebuehren']:8.2f} "
              f"{dca['mdd']:8.1f}%")
        print(f"    {'BTC-DCA woechentlich (am Ende verk.)':<34s} "
              f"{dca['verkauft']:11.2f} {dca['pnl_verkauft']:+10.2f} "
              f"{dca['pnl_verkauft'] / START * 100:+7.2f}% "
              f"{dca['gebuehren']:8.2f} {dca['mdd']:8.1f}%")
        print(f"    {'ZUSATZ: 11 Coins gleichgewichtet':<34s} "
              f"{eq['mtm']:11.2f} {eq['pnl_mtm']:+10.2f} "
              f"{eq['pnl_mtm'] / START * 100:+7.2f}% {eq['gebuehren']:8.2f} "
              f"{'-':>9s}")
        if bot[bez] is not None:
            print("    " + "-" * 84)
            print(f"    {'BOT (Harness, Kontrollanker)':<34s} "
                  f"{START + bot[bez]:11.2f} {bot[bez]:+10.2f} "
                  f"{bot[bez] / START * 100:+7.2f}% {'~93':>8s} {'-':>9s}")
            print(f"    Abstand Bot gegen BTC-Halten (m2m): "
                  f"{bot[bez] - bh['pnl_mtm']:+.2f} $")
            print(f"    Abstand Bot gegen BTC-DCA (m2m)   : "
                  f"{bot[bez] - dca['pnl_mtm']:+.2f} $")

        print(f"\n    DCA-Detail: {dca['kaeufe']} Kaeufe zu je "
              f"{START / 52:.2f} $, Restbar {dca['restbar']:.2f} $, "
              f"Bestand {dca['menge']:.8f} BTC")
        sys.stdout.flush()

    # ---------------- Live-Fenster ----------------
    print("\n" + "=" * 100)
    print(" F3-Zusatz  LIVE-FENSTER DES JOURNALS  10.06.2026 - 29.07.2026")
    print(" Bezugsgroesse fuer F1e. Gleiches Startkapital 500 $.")
    print("=" * 100)
    daten, _ = lade_jahr("")
    btc_f = fenster(daten["BTC/USDC"], "2026-06-10", "2026-07-29")
    von, bis = zeitraum(btc_f)
    print(f"\n  {von} .. {bis}   ({len(btc_f)} 15m-Kerzen, "
          f"{len(btc_f) * 15 / 60 / 24:.0f} Tage)")
    bh = kaufen_halten(btc_f)
    dca = dca_woechentlich(btc_f, tranchen=7)
    print(f"    BTC kaufen & halten : {bh['pnl_mtm']:+8.2f} $  "
          f"({bh['pnl_mtm'] / START * 100:+.2f} %)   MaxDD {bh['mdd']:.1f} %")
    print(f"    BTC-DCA (7 Wochen)  : {dca['pnl_mtm']:+8.2f} $  "
          f"({dca['pnl_mtm'] / START * 100:+.2f} %)   MaxDD {dca['mdd']:.1f} %")
    eqf = {}
    wert = 0.0
    coins = [c for c in COINS if daten.get(c)]
    for c in coins:
        kf = fenster(daten[c], "2026-06-10", "2026-07-29")
        wert += kaufen_halten(kf, START / len(coins))["mtm"]
    print(f"    11 Coins gleichgew. : {wert - START:+8.2f} $  "
          f"({(wert - START) / START * 100:+.2f} %)")
    print("\n    Zum Vergleich aus F1e (gleiches Fenster, gleicher Bot):")
    print("      realisiert + offen, Ist-Kosten (S1)  :   -57.81 $")
    print("      realisiert + offen, ohne jede Reibung:   +34.38 $")
    print("    ACHTUNG: der Bot handelte in diesem Fenster nicht BTC allein,")
    print("    sondern 9 Coins inkl. XRP, und war nie voll investiert.")
    print("    Die Zahlen stehen nebeneinander, sie sind keine saubere")
    print("    Risikoparitaet.")

    print("\n" + "=" * 100)
    print(" ENDE F3")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
