# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit F1e vom 30.07.2026.
# Nicht archivieren - Beleg fuer die Kostenhuerden-Messung. Siehe ../README.md
"""
F1e - Rueckrechnung der realen Trades auf Maker-Gebuehr statt Taker.

Datenbasis: eingangsdaten/trades_v5_snapshot_2026-07-30.json (950 Eintraege,
eingefroren). Das Original waechst weiter - hier wird ausschliesslich der
Snapshot gelesen.

WAS HIER GERECHNET WIRD
-----------------------
Die Positionen werden chronologisch je Coin rekonstruiert (mengengewichteter
Einstand, wie execution/engine.py:270-278 es im Paper-Pfad tut). Nur
GESCHLOSSENE Positionen gehen in die P&L ein; die 5 offenen bleiben aussen vor.

Der im Journal stehende Preis enthaelt bereits die simulierte Slippage
(engine.py:243-248: BUY = mid*(1+s), SELL = mid*(1-s), s ~ U(0,02;0,08) %).
Das je Trade tatsaechlich gezogene s ist NICHT protokolliert. Fuer die
Rueckrechnung wird der Erwartungswert 0,05 % verwendet - die Bandbreite
0,02/0,08 % wird als Unter-/Obergrenze mitgerechnet.

SZENARIEN
---------
  S0  Ist, wie protokolliert (Gebuehr aus dem Journal, unvollstaendig)
  S1  Ist, Gebuehr konsistent mit 0,100 % nachgerechnet (Taker, Market)
  S2  Maker-Gebuehr 0,100 % - nach backtest/fees.py:9 IDENTISCH zum Taker
  S3  Limit ohne Slippage, Gebuehr 0,100 %
  S4  Limit ohne Slippage, Gebuehr 0,075 % (BNB-Rabatt aus fees.py:9)

FILL-RISIKO
-----------
Eine Limit-Order wird nicht garantiert gefuellt. Der Anteil ungefuellter
Orders wird auf den Kerzendaten geschaetzt (Beruehrungsquote) und um die
adverse Selektion ergaenzt: Fuellungen passieren bevorzugt dann, wenn der
Kurs weiterlaeuft - der Vorteil ist also systematisch kleiner als die reine
Gebuehrenersparnis.
"""
import os
import sys
import json
from datetime import datetime

from harness_ext import lade_jahr, COINS, PROJEKT
from messung_f_stat import median, mittel

SNAPSHOT = os.path.join(PROJEKT, "docs", "messungen_2026-07", "eingangsdaten",
                        "trades_v5_snapshot_2026-07-30.json")

SLIP_ERW = 0.0005     # Erwartungswert der Paper-Slippage je Seite
SLIP_MIN = 0.0002
SLIP_MAX = 0.0008
GEB_TAKER = 0.0010
GEB_MAKER = 0.0010    # fees.py:9 - auf Binance Spot identisch zum Taker
GEB_BNB = 0.00075


# ===========================================================================
# Journal
# ===========================================================================
def lade_journal():
    with open(SNAPSHOT, encoding="utf-8") as f:
        roh = json.load(f)
    out = []
    for e in roh:
        typ = (e.get("type") or e.get("side") or "").upper()
        if typ not in ("BUY", "SELL"):
            continue
        coin = e.get("coin") or e.get("symbol") or "?"
        try:
            preis = float(e.get("price") or 0)
            menge = float(e.get("qty") or 0)
        except (TypeError, ValueError):
            continue
        if preis <= 0 or menge <= 0:
            continue
        geb = e.get("fee")
        try:
            geb = float(geb) if geb is not None else None
        except (TypeError, ValueError):
            geb = None
        t = e.get("time") or ""
        try:
            ts = datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = 0.0
        out.append({"typ": typ, "coin": coin, "preis": preis, "menge": menge,
                    "geb": geb, "ts": ts, "zeit": t})
    out.sort(key=lambda x: x["ts"])
    return out


def positionen(eintraege):
    """Chronologische Rekonstruktion. Gibt (geschlossene, offene) zurueck.

    Eine geschlossene Position ist eine Folge von Kaeufen bis zu dem Verkauf,
    der den Bestand auf ~0 bringt. Teilverkaeufe werden anteilig verrechnet.
    """
    lauf = {}      # coin -> {"menge", "kauf_notional", "verk_notional",
                   #          "geb_journal", "kauf_menge", "verk_menge", "n_buy", "n_sell"}
    zu, offen = [], []
    geister = []   # Verkaeufe ohne Bestand bzw. ueber den Bestand hinaus
    for e in eintraege:
        c = e["coin"]
        p = lauf.get(c)
        if p is None:
            p = lauf[c] = {"menge": 0.0, "kauf_notional": 0.0,
                           "verk_notional": 0.0, "geb_journal": 0.0,
                           "kauf_menge": 0.0, "verk_menge": 0.0,
                           "n_buy": 0, "n_sell": 0, "start": e["zeit"],
                           "geb_fehlt": 0}
        notional = e["preis"] * e["menge"]
        if e["geb"] is None:
            p["geb_fehlt"] += 1
        else:
            p["geb_journal"] += e["geb"]
        if e["typ"] == "BUY":
            p["menge"] += e["menge"]
            p["kauf_notional"] += notional
            p["kauf_menge"] += e["menge"]
            p["n_buy"] += 1
        else:
            # Geister-Verkauf: mehr (oder ueberhaupt) verkauft als gehalten.
            # Wird NICHT als Erloes gewertet - sonst bucht die Rueckrechnung
            # Umsatz, den es nie gab. Der Paper-Pfad kappt seit 29.07. selbst
            # (engine.py:291-299), vorher nicht.
            verk = min(e["menge"], p["menge"]) if p["menge"] > 0 else 0.0
            fehl = e["menge"] - verk
            if fehl > 1e-10:
                geister.append((c, e["zeit"], fehl, fehl * e["preis"]))
            if verk <= 0:
                continue
            p["menge"] -= verk
            p["verk_notional"] += e["preis"] * verk
            p["verk_menge"] += verk
            p["n_sell"] += 1
            if p["menge"] <= 1e-10:
                p["coin"] = c
                p["ende"] = e["zeit"]
                zu.append(p)
                del lauf[c]
    for c, p in lauf.items():
        p["coin"] = c
        offen.append(p)
    return zu, offen, geister


def szenario(pos_liste, geb_rate, slip, journal_geb=False):
    """P&L-Summe ueber alle geschlossenen Positionen unter einem Kostenmodell.

    slip = angenommene Paper-Slippage je Seite, die aus den protokollierten
    Preisen HERAUSGERECHNET wird (slip=0 -> Ausfuehrung zum Mittelkurs).
    """
    summe = 0.0
    geb_summe = 0.0
    for p in pos_liste:
        # protokollierte Preise enthalten SLIP_ERW; auf gewuenschtes slip umskalieren
        kauf = p["kauf_notional"] / (1.0 + SLIP_ERW) * (1.0 + slip)
        verk = p["verk_notional"] / (1.0 - SLIP_ERW) * (1.0 - slip)
        if journal_geb:
            geb = p["geb_journal"]
        else:
            geb = (kauf + verk) * geb_rate
        summe += verk - kauf - geb
        geb_summe += geb
    return summe, geb_summe


# ===========================================================================
# Fill-Schaetzung auf Kerzen
# ===========================================================================
def fill_analyse(daten, k_balken):
    """Beruehrungsquote einer passiven Limit-Order + adverse Selektion.

    BUY-Limit auf Close(t): gefuellt, wenn min(Low[t+1..t+k]) <= Close(t).
    SELL-Limit auf Close(t): gefuellt, wenn max(High[t+1..t+k]) >= Close(t).
    Zusaetzlich eine echte passive Variante 0,05 % besser als Close.

    Adverse Selektion: mittlere Rendite Close(t) -> Close(t+k)
      (a) unbedingt, (b) nur auf den gefuellten BUY-Faellen.
      Ist (b) schlechter als (a), frisst die Selektion die Ersparnis an.
    """
    varianten = (("am Close", 0.0), ("0,05 % passiver", 0.0005))
    z = {name: {"n": 0, "tb": 0, "ts": 0, "sr": 0.0, "sg": 0.0, "ng": 0}
         for name, _ in varianten}
    for coin in COINS:
        ks = daten.get(coin)
        if not ks:
            continue
        m = len(ks)
        lows = [k[3] for k in ks]
        highs = [k[2] for k in ks]
        closes = [k[4] for k in ks]
        for i in range(0, m - k_balken):
            cl = closes[i]
            if cl <= 0:
                continue
            a, b = i + 1, i + 1 + k_balken
            lo = min(lows[a:b])
            hi = max(highs[a:b])
            ende = closes[i + k_balken]
            r = (ende / cl - 1.0) * 100.0
            for name, versatz in varianten:
                d = z[name]
                d["n"] += 1
                d["sr"] += r
                lim_b = cl * (1.0 - versatz)
                if lo <= lim_b:
                    d["tb"] += 1
                    # Einstand ist der Limitpreis, nicht der Close
                    d["sg"] += (ende / lim_b - 1.0) * 100.0
                    d["ng"] += 1
                if hi >= cl * (1.0 + versatz):
                    d["ts"] += 1
    erg = {}
    for name, _ in varianten:
        d = z[name]
        n = d["n"] or 1
        erg[name] = {
            "n": d["n"],
            "fill_buy": d["tb"] / n * 100,
            "fill_sell": d["ts"] / n * 100,
            "r_alle": d["sr"] / n,
            "r_gefuellt": d["sg"] / d["ng"] if d["ng"] else 0.0,
        }
    return erg


# ===========================================================================
def main():
    print("=" * 100)
    print(" MESSUNG F1e - Maker statt Taker auf den realen Trades")
    print(" Snapshot: eingangsdaten/trades_v5_snapshot_2026-07-30.json")
    print("=" * 100)

    eintraege = lade_journal()
    zu, offen, geister = positionen(eintraege)
    n_buy = sum(1 for e in eintraege if e["typ"] == "BUY")
    n_sell = len(eintraege) - n_buy
    ohne_geb = sum(1 for e in eintraege if e["geb"] is None)

    print(f"\n  Journal: {len(eintraege)} verwertbare Eintraege "
          f"({n_buy} BUY / {n_sell} SELL)")
    print(f"  Eintraege OHNE Gebuehrenfeld: {ohne_geb} "
          f"({ohne_geb / len(eintraege) * 100:.1f} %) "
          "- bekannte Protokolluecke, app.py:1860-1865")
    print(f"  Geschlossene Positionen: {len(zu)}   offene: {len(offen)} "
          f"({', '.join(sorted(p['coin'] for p in offen))})")
    print(f"  Geister-Verkaeufe (ohne Bestand, NICHT als Erloes gewertet): "
          f"{len(geister)}")
    for c, t, menge, wert in geister:
        print(f"    {c:<10s} {t[:19]}  {menge:.6f} Stueck  {wert:,.2f} $")

    kauf_n = sum(p["kauf_notional"] for p in zu)
    verk_n = sum(p["verk_notional"] for p in zu)
    print(f"  Umgeschlagenes Volumen (geschlossene Pos.): "
          f"Kauf {kauf_n:,.2f} $ / Verkauf {verk_n:,.2f} $ "
          f"= {kauf_n + verk_n:,.2f} $ Gesamtnotional")

    # ---------------- Offene Positionen bewerten ----------------
    # WARNUNG: ohne diesen Block liest sich die realisierte P&L als Gewinn.
    # Die 5 offenen Positionen sind genau die, die nicht verkauft wurden -
    # der Bot sitzt seit dem Snapshot mit 5/5 Positionen im Leerlauf.
    daten_j2, _ = lade_jahr("")
    letzter = {c: ks[-1][4] for c, ks in daten_j2.items() if ks}
    print("\n  OFFENE POSITIONEN - Bewertung zum letzten Kerzen-Close"
          " (2026-07-29)")
    print(f"    {'Coin':<10s} {'Menge':>14s} {'Einstand $':>12s} "
          f"{'Kurs $':>12s} {'Wert $':>10s} {'unreal. P&L $':>14s}")
    print("    " + "-" * 78)
    unreal = 0.0
    for p in sorted(offen, key=lambda x: x["coin"]):
        c = p["coin"]
        kurs = letzter.get(c)
        einstand = (p["kauf_notional"] / p["kauf_menge"]
                    if p["kauf_menge"] > 0 else 0.0)
        rest = p["menge"]
        if kurs is None:
            print(f"    {c:<10s} {rest:14.6f} {einstand:12.4f} "
                  f"{'keine Kerzen':>12s} {'-':>10s} {'-':>14s}")
            continue
        wert = rest * kurs
        # anteilige Kosten des noch gehaltenen Bestands
        kosten = einstand * rest
        pnl = wert - kosten
        unreal += pnl
        print(f"    {c:<10s} {rest:14.6f} {einstand:12.4f} {kurs:12.4f} "
              f"{wert:10.2f} {pnl:+14.2f}")
    print("    " + "-" * 78)
    print(f"    {'SUMME':<10s} {'':>14s} {'':>12s} {'':>12s} {'':>10s} "
          f"{unreal:+14.2f}")
    print("    Diese Zahl ist NICHT in den Szenarien unten enthalten -"
          " dort stehen")
    print("    ausschliesslich realisierte Ergebnisse geschlossener"
          " Positionen.")

    # ---------------- Szenarien ----------------
    print("\n" + "=" * 100)
    print(" F1e-1  P&L der geschlossenen Positionen je Kostenmodell")
    print("=" * 100)
    s0, g0 = szenario(zu, 0.0, SLIP_ERW, journal_geb=True)
    zeilen = [
        ("S0  Ist, Gebuehr aus dem Journal (unvollstaendig)", s0, g0, "-"),
        ("S1  Ist, Gebuehr konsistent 0,100 % Taker", ) + szenario(zu, GEB_TAKER, SLIP_ERW) + ("Basis",),
    ]
    s1 = zeilen[1][1]
    for name, rate, slip in (
            ("S2  Maker 0,100 % (fees.py:9: = Taker), Market-Slippage",
             GEB_MAKER, SLIP_ERW),
            ("S3  Limit, keine Slippage, Gebuehr 0,100 %", GEB_MAKER, 0.0),
            ("S4  Limit, keine Slippage, Gebuehr 0,075 % (BNB)", GEB_BNB, 0.0),
            ("S5  Gebuehr 0 %, keine Slippage (physikalische Grenze)", 0.0, 0.0)):
        s, g = szenario(zu, rate, slip)
        zeilen.append((name, s, g, f"{s - s1:+.2f}"))

    print(f"\n    {'Szenario':<52s} {'P&L $':>10s} {'Gebuehren $':>12s} "
          f"{'vs S1':>10s}")
    print("    " + "-" * 88)
    for name, s, g, delta in zeilen:
        print(f"    {name:<52s} {s:+10.2f} {g:12.2f} {delta:>10s}")

    print("\n    Slippage-Bandbreite (Unsicherheit ueber das je Trade gezogene s):")
    for bez, sl in (("s = 0,02 % (Untergrenze engine.py:243)", SLIP_MIN),
                    ("s = 0,05 % (Erwartungswert)", SLIP_ERW),
                    ("s = 0,08 % (Obergrenze engine.py:243)", SLIP_MAX)):
        ist, _ = szenario(zu, GEB_TAKER, sl)
        lim, _ = szenario(zu, GEB_MAKER, 0.0)
        print(f"      {bez:<42s} Ist {ist:+9.2f} $   Limit {lim:+9.2f} $   "
              f"Ersparnis {lim - ist:+8.2f} $")
    print("      (Der Limit-Wert haengt nicht von s ab - dort gibt es keine"
          " Slippage.)")

    print("\n    Kostenanteile bezogen auf S1")
    ges_notional = kauf_n + verk_n
    print(f"      Gebuehren 0,100 % auf {ges_notional:,.2f} $ Notional : "
          f"{ges_notional * GEB_TAKER:8.2f} $")
    print(f"      Slippage  0,050 % auf {ges_notional:,.2f} $ Notional : "
          f"{ges_notional * SLIP_ERW:8.2f} $")
    print(f"      Summe Reibung                                    : "
          f"{ges_notional * (GEB_TAKER + SLIP_ERW):8.2f} $")
    print(f"      P&L ohne jede Reibung (S5)                       : "
          f"{zeilen[-1][1]:+8.2f} $")

    brutto = zeilen[-1][1]                     # S5, ohne jede Reibung
    print("\n    DIE ENTSCHEIDENDE RELATION - Bruttovorteil gegen Reibung")
    print(f"      Bruttoergebnis vor jeder Reibung        : {brutto:+8.2f} $")
    print(f"      auf {kauf_n:,.2f} $ Kaufnotional        = "
          f"{brutto / kauf_n * 100:+.4f} % je Positionsrunde")
    print(f"      Reibung Ist                             = "
          f"{(GEB_TAKER + SLIP_ERW) * 2 * 100:.4f} % je Positionsrunde")
    print(f"      Reibung Untergrenze (Limit + BNB)       = "
          f"{GEB_BNB * 2 * 100:.4f} % je Positionsrunde")
    print(f"      -> Bruttovorteil deckt {brutto / kauf_n * 100 / 0.30 * 100:.0f} %"
          f" der Ist-Reibung und {brutto / kauf_n * 100 / 0.15 * 100:.0f} %"
          " der Untergrenze.")

    print("\n    GESAMTBILD - realisiert PLUS offene Positionen")
    print(f"      {'Szenario':<52s} {'realisiert':>11s} {'offen':>9s} "
          f"{'gesamt':>9s}")
    print("      " + "-" * 84)
    for name, s, _g, _d in zeilen:
        print(f"      {name:<52s} {s:+11.2f} {unreal:+9.2f} "
              f"{s + unreal:+9.2f}")
    print("      Die offenen Positionen sind in allen Szenarien gleich"
          " angesetzt -")
    print("      ihr Ergebnis haengt vom Ausstieg ab, den es noch nicht gibt.")

    # ---------------- Fill-Risiko ----------------
    print("\n" + "=" * 100)
    print(" F1e-2  Wie viele Limit-Orders waeren NICHT gefuellt worden?")
    print("=" * 100)
    print("\n  Geschaetzt auf den 15m-Kerzen beider Jahre. Eine Limit-Order gilt")
    print("  als beruehrt, wenn der Kurs sie innerhalb des Wartefensters erreicht.")
    print("  Beruehrung ist die OBERGRENZE der Fuellquote: Warteschlangenposition,")
    print("  Teilfuellung und Ordergroesse sind hier nicht abgebildet.")

    for jahr, marke in (("Jahr 2  2025-07..2026-07", ""),
                        ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, _ = lade_jahr(marke)
        print(f"\n  {jahr}")
        print(f"    {'Wartefenster':<14s} {'Variante':<18s} {'Fill BUY':>10s} "
              f"{'Fill SELL':>10s} {'nicht gefuellt':>15s} | "
              f"{'E[r] alle':>10s} {'E[r] gefuellt':>14s} {'Selektion':>11s}")
        print("    " + "-" * 108)
        for fenster, kb in (("15 min", 1), ("1 h", 4), ("4 h", 16)):
            erg = fill_analyse(daten, kb)
            for variante, d in erg.items():
                sel = d["r_gefuellt"] - d["r_alle"]
                print(f"    {fenster:<14s} {variante:<18s} "
                      f"{d['fill_buy']:9.1f}% {d['fill_sell']:9.1f}% "
                      f"{100 - d['fill_buy']:14.1f}% | "
                      f"{d['r_alle']:+9.3f}% {d['r_gefuellt']:+13.3f}% "
                      f"{sel:+10.3f}%")
            sys.stdout.flush()

    print("\n  LESART")
    print("    'Selektion' ist die Differenz zwischen der Rendite auf allen")
    print("    Zeitpunkten und der Rendite nur auf den gefuellten BUY-Faellen,")
    print("    gerechnet ab dem Limitpreis. Ist sie negativ, wird bevorzugt")
    print("    dann gefuellt, wenn der Kurs weiterfaellt - der Preisvorteil der")
    print("    Limit-Order wird dadurch teilweise oder ganz aufgezehrt.")
    print("    Die 0,05-%-Variante zeigt beides zugleich: hoehere Ersparnis,")
    print("    niedrigere Fuellquote, staerkere Selektion.")

    print("\n" + "=" * 100)
    print(" ENDE F1e")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
