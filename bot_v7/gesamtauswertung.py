# -*- coding: utf-8 -*-
"""Gesamtauswertung aller gemessenen und bestaetigten Daten.

Zieht alle Quellen zusammen, die im Projekt tatsaechlich Messwerte enthalten:
  data_store/trades_v5.json      - 977 Trades seit 10.06.2026
  data_store/telemetrie.db       - Kaufpruefungen und Chartanalyse-Signale
  data_store/bot_state.json      - aktueller Zustand

Es wird NICHTS geschaetzt und NICHTS hochgerechnet. Wo Daten fehlen, steht das
ausdruecklich da. Reine Leseoperation, aendert nichts.

Aufruf:  python gesamtauswertung.py
"""
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(HIER, "data_store")


def lade(pfad, standard):
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return standard


def zeit(t):
    try:
        return datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    except Exception:
        return None


def linie(z="=", n=92):
    print(z * n)


def teil(titel):
    print()
    linie()
    print(f" {titel}")
    linie()


# ==================================================================
def handel_je_coin(trades):
    """P&L, Trefferquote und Volumen je Coin - die Kernfrage."""
    teil("1. HANDELSERGEBNIS JE COIN  (Quelle: trades_v5.json)")

    coins = defaultdict(lambda: {"kauf": 0, "verk": 0, "pnl": 0.0, "gew": 0,
                                 "verl": 0, "vol": 0.0, "fee": 0.0,
                                 "erst": None, "letzt": None})
    for t in trades:
        c = str(t.get("coin", "")).split("/")[0]
        if not c:
            continue
        d = coins[c]
        typ = str(t.get("type", "")).upper()
        ts = zeit(t.get("time"))
        if ts:
            if d["erst"] is None or ts < d["erst"]:
                d["erst"] = ts
            if d["letzt"] is None or ts > d["letzt"]:
                d["letzt"] = ts
        d["fee"] += float(t.get("fee") or 0)
        d["vol"] += float(t.get("amount") or 0)
        if typ == "BUY":
            d["kauf"] += 1
        elif typ == "SELL":
            d["verk"] += 1
            p = t.get("pnl")
            if isinstance(p, (int, float)):
                d["pnl"] += p
                if p > 0:
                    d["gew"] += 1
                else:
                    d["verl"] += 1

    print(f"\n  {'Coin':<6s}{'Kauf':>6s}{'Verk':>6s}{'Quote':>8s}"
          f"{'P&L netto':>12s}{'je Verkauf':>12s}{'Gebuehren':>11s}"
          f"{'letzter Trade':>16s}")
    print("  " + "-" * 82)
    gesamt_pnl = 0.0
    zeilen = []
    for c, d in sorted(coins.items(), key=lambda x: -x[1]["pnl"]):
        if d["verk"] == 0 and d["kauf"] == 0:
            continue
        quote = (d["gew"] / d["verk"] * 100) if d["verk"] else 0
        je = (d["pnl"] / d["verk"]) if d["verk"] else 0
        gesamt_pnl += d["pnl"]
        letzt = d["letzt"].strftime("%d.%m.%Y") if d["letzt"] else "-"
        zeilen.append((c, d, quote, je))
        print(f"  {c:<6s}{d['kauf']:6d}{d['verk']:6d}{quote:7.1f}%"
              f"{d['pnl']:+11.2f}${je:+11.3f}${d['fee']:10.2f}${letzt:>16s}")
    print("  " + "-" * 82)
    print(f"  {'SUMME':<6s}{'':>12s}{'':>8s}{gesamt_pnl:+11.2f}$")

    # Die entscheidende Frage: haben die gestrichenen Coins Geld gekostet?
    aktiv = {"BTC", "ETH", "SOL"}
    weg = [(c, d) for c, d in coins.items() if c not in aktiv and d["verk"] > 0]
    if weg:
        pnl_weg = sum(d["pnl"] for _, d in weg)
        verk_weg = sum(d["verk"] for _, d in weg)
        pnl_akt = sum(d["pnl"] for c, d in coins.items() if c in aktiv)
        verk_akt = sum(d["verk"] for c, d in coins.items() if c in aktiv)
        print(f"\n  GESTRICHENE COINS gegen BEHALTENE:")
        print(f"    Gestrichen ({len(weg)} Coins): {verk_weg:4d} Verkaeufe, "
              f"{pnl_weg:+8.2f}$  ({pnl_weg/verk_weg if verk_weg else 0:+.3f}$ je Verkauf)")
        print(f"    Behalten  (BTC/ETH/SOL): {verk_akt:4d} Verkaeufe, "
              f"{pnl_akt:+8.2f}$  ({pnl_akt/verk_akt if verk_akt else 0:+.3f}$ je Verkauf)")
        if verk_weg and verk_akt:
            besser = ("die GESTRICHENEN" if pnl_weg / verk_weg > pnl_akt / verk_akt
                      else "die BEHALTENEN")
            print(f"    -> Je Verkauf liefen {besser} Coins besser.")
    return coins


def zeitverlauf(trades):
    """Monatsweise - wann wurde verdient, wann verloren?"""
    teil("2. ZEITVERLAUF  (Quelle: trades_v5.json)")
    monate = defaultdict(lambda: {"verk": 0, "pnl": 0.0, "gew": 0})
    for t in trades:
        if str(t.get("type", "")).upper() != "SELL":
            continue
        ts = zeit(t.get("time"))
        p = t.get("pnl")
        if not ts or not isinstance(p, (int, float)):
            continue
        m = monate[ts.strftime("%Y-%m")]
        m["verk"] += 1
        m["pnl"] += p
        if p > 0:
            m["gew"] += 1
    print(f"\n  {'Monat':<10s}{'Verkaeufe':>11s}{'Trefferquote':>14s}"
          f"{'P&L':>12s}{'je Verkauf':>12s}")
    print("  " + "-" * 59)
    for m in sorted(monate):
        d = monate[m]
        q = d["gew"] / d["verk"] * 100 if d["verk"] else 0
        print(f"  {m:<10s}{d['verk']:11d}{q:13.1f}%{d['pnl']:+11.2f}$"
              f"{d['pnl']/d['verk'] if d['verk'] else 0:+11.3f}$")


def strategien(trades):
    """Welche Strategie hat tatsaechlich geliefert?"""
    teil("3. STRATEGIEN  (Quelle: trades_v5.json, nur Verkaeufe mit P&L)")
    s = defaultdict(lambda: {"n": 0, "pnl": 0.0, "gew": 0})
    for t in trades:
        if str(t.get("type", "")).upper() != "SELL":
            continue
        p = t.get("pnl")
        if not isinstance(p, (int, float)):
            continue
        k = str(t.get("strategy") or "unbekannt")
        s[k]["n"] += 1
        s[k]["pnl"] += p
        if p > 0:
            s[k]["gew"] += 1
    print(f"\n  {'Ausstiegsgrund':<22s}{'n':>6s}{'Quote':>8s}{'P&L':>11s}{'je Trade':>11s}")
    print("  " + "-" * 58)
    for k, d in sorted(s.items(), key=lambda x: -x[1]["pnl"]):
        q = d["gew"] / d["n"] * 100 if d["n"] else 0
        print(f"  {k:<22s}{d['n']:6d}{q:7.1f}%{d['pnl']:+10.2f}${d['pnl']/d['n']:+10.3f}$")


def telemetrie():
    """Kaufpruefungen und Chartanalyse aus der Datenbank."""
    p = os.path.join(DS, "telemetrie.db")
    if not os.path.exists(p):
        teil("4. TELEMETRIE - Datenbank fehlt")
        return
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=8)

    teil("4. KAUFPRUEFUNGEN  (Quelle: telemetrie.db)")
    r = con.execute("SELECT COUNT(*), SUM(decision='APPROVED'), MIN(ts_utc), "
                    "MAX(ts_utc) FROM evaluations").fetchone()
    print(f"\n  Zeitraum   : {r[2][:16]} bis {r[3][:16]}")
    print(f"  Pruefungen : {r[0]}")
    print(f"  Genehmigt  : {r[1]}  ({(r[1] or 0)/r[0]*100:.4f} %)")
    print(f"\n  {'Blockgrund':<28s}{'Faelle':>9s}{'Anteil':>9s}")
    print("  " + "-" * 46)
    ges = con.execute("SELECT COUNT(*) FROM evaluations "
                      "WHERE decision='REJECTED'").fetchone()[0]
    for x in con.execute("SELECT rule_name, COUNT(DISTINCT evaluation_id) FROM "
                         "rule_evaluations WHERE result='BLOCK' GROUP BY rule_name "
                         "ORDER BY 2 DESC"):
        print(f"  {x[0]:<28s}{x[1]:9d}{x[1]/ges*100:8.1f}%")

    teil("5. CHARTANALYSE  (Quelle: telemetrie.db, reine Messung)")
    print(f"\n  {'Zeitrahmen':<12s}{'Signalart':<18s}{'n':>7s}{'Quote':>8s}"
          f"{'EV brutto':>11s}{'EV netto':>10s}")
    print("  " + "-" * 66)
    for x in con.execute(
            "SELECT timeframe, signal, COUNT(*), "
            "100.0*SUM(ergebnis='ZIEL')/COUNT(*), AVG(rendite_pct), "
            "AVG(rendite_netto) FROM chart_signale GROUP BY timeframe, signal "
            "HAVING COUNT(*)>=20 ORDER BY AVG(rendite_netto) DESC"):
        print(f"  {x[0]:<12s}{x[1]:<18s}{x[2]:7d}{x[3]:7.1f}%"
              f"{x[4]:+10.3f}%{x[5]:+9.3f}%")
    print("\n  EV netto = Erwartungswert je Signal NACH 0,50 % Handelskosten.")
    print("  Negativ heisst: die Regel kostet Geld, unabhaengig von der Quote.")
    con.close()


def bestand():
    teil("6. AKTUELLER STAND  (Quelle: bot_state.json)")
    s = lade(os.path.join(DS, "bot_state.json"), {})
    pos = s.get("open_positions_backup") or {}
    print(f"\n  Zyklusphase     : {s.get('cycle_phase', '?')}")
    print(f"  Realisiert P&L  : {s.get('realized_pnl', 0):+.2f} $")
    print(f"  Trades gesamt   : {s.get('trade_count', 0)}")
    print(f"  Offene Positionen: {len(pos)}")
    for sym, p in pos.items():
        if isinstance(p, dict):
            print(f"    {sym:<11s} qty {p.get('qty', 0):.6f}  "
                  f"Einstand {p.get('entry_price', 0):.2f}  "
                  f"Kennung {p.get('position_id', '-')}")


def main():
    trades = lade(os.path.join(DS, "trades_v5.json"), [])
    if not isinstance(trades, list) or not trades:
        print("Kein Journal gefunden.")
        return 1

    linie()
    print(" GESAMTAUSWERTUNG - alle gemessenen und bestaetigten Daten")
    print(f" Erstellt: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f" Journal: {len(trades)} Eintraege ab {str(trades[0].get('time'))[:10]}")
    linie()

    handel_je_coin(trades)
    zeitverlauf(trades)
    strategien(trades)
    telemetrie()
    bestand()

    teil("HINWEIS ZUR BELASTBARKEIT")
    print("\n  Nicht enthalten, weil nicht gemessen:")
    print("    - Verkaufsentscheidungen in der Telemetrie-DB (nur Kaeufe erfasst)")
    print("    - Trades vor dem 10.06.2026 (aelteres Journal, teils beschaedigt)")
    print("  Das Journal weist Bestandsdifferenzen auf (go_live_check H7);")
    print("  P&L-Zahlen je Trade sind davon nicht betroffen, Mengensalden schon.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
