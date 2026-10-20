# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Belege zur Bug-Liste (Block 2) und zum Logzeilen-Diff (Block 3).
"""
Read-only. Schreibt keine Datei, aendert nichts, startet nichts.

Beantwortet mit Zahlen:
  2.4  Wie viele Nachkaeufe stehen im Journal, und wie viele haette der
       Exposure-Check bei der aktuellen Positionsgroesse blockiert?
  2.6  Zieht das Projekt Gebuehren aus ccxt-Metadaten?
  3.1  Logvolumen-Hochrechnung fuer die drei zusaetzlichen Logzeilen in
       risk/engine.py, aus dem realen Laufzeit-Log.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
JOURNAL = os.path.join(PROJEKT, "data_store", "trades_v5.json")
LOG = os.path.join(PROJEKT, "data_store", "system.log")
CONFIG = os.path.join(PROJEKT, "data_store", "config.json")


def kopf(t):
    print("\n" + "=" * 96)
    print(" " + t)
    print("=" * 96)


def punkt_24():
    kopf("2.4  E8-Nachkauf-Stop - ist er ueberhaupt noch noetig?")
    cfg = {}
    if os.path.isfile(CONFIG):
        try:
            cfg = json.load(open(CONFIG, encoding="utf-8"))
        except ValueError as e:
            print("  config.json nicht lesbar:", e)

    def hole(pfad, default):
        d = cfg
        for teil in pfad.split("."):
            if not isinstance(d, dict) or teil not in d:
                return default, "settings.py-Default"
            d = d[teil]
        return d, "data_store/config.json"

    psize, q1 = hole("trading.position_size_pct", 30.0)
    mcoin, q2 = hole("risk.max_exposure_per_coin_pct", 35.0)
    mlev, q3 = hole("trading.dca_max_levels", 3)
    print(f"  position_size_pct          = {psize}   ({q1})")
    print(f"  max_exposure_per_coin_pct  = {mcoin}   ({q2})")
    print(f"  dca_max_levels             = {mlev}   ({q3})")
    print(f"\n  Rechnung app.py:1814-1818: blockiert wird, wenn")
    print(f"  (aktueller Coin-Wert + Nachkaufbetrag) / Equity * 100 > "
          f"{mcoin}")
    print(f"  Eine frische Position bindet {psize} % der Equity. Ein "
          f"Nachkauf gleicher Groesse")
    print(f"  ergibt {2*float(psize):.0f} % -> {'BLOCKIERT' if 2*float(psize) > float(mcoin) else 'ERLAUBT'} "
          f"(Schwelle {mcoin} %).")
    n = float(mcoin) / float(psize) if float(psize) else 0
    print(f"  Erst ab einer Positionsgroesse unter {float(mcoin)/2:.1f} % "
          f"waere ein erster Nachkauf moeglich;")
    print(f"  rechnerisch passen {n:.2f} Positionsgroessen unter die "
          f"Coin-Grenze.")

    if not os.path.isfile(JOURNAL):
        print("  Journal fehlt:", JOURNAL)
        return
    trades = json.load(open(JOURNAL, encoding="utf-8", errors="ignore"))
    print(f"\n  Journal: {len(trades)} Eintraege, "
          f"{trades[0].get('time', '?')[:16]} .. "
          f"{trades[-1].get('time', '?')[:16]}")
    # Nachkauf = BUY auf einen Coin, der zu diesem Zeitpunkt schon offen ist
    offen = defaultdict(float)
    nachkauf = Counter()
    erst = Counter()
    nachkauf_zeiten = []
    for t in sorted(trades, key=lambda x: (x.get("time", ""),
                                           x.get("_id", 0))):
        c = t.get("coin")
        typ = t.get("type")
        try:
            q = float(t.get("qty", 0))
        except (TypeError, ValueError):
            continue
        if typ == "BUY":
            if offen[c] > 1e-12:
                nachkauf[c] += 1
                nachkauf_zeiten.append(t.get("time", "")[:10])
            else:
                erst[c] += 1
            offen[c] += q
        elif typ == "SELL":
            offen[c] = max(0.0, offen[c] - q)
    print(f"  Erstkaeufe: {sum(erst.values())}   "
          f"Nachkaeufe: {sum(nachkauf.values())}")
    if nachkauf:
        print(f"  Nachkaeufe je Coin: "
              f"{dict(nachkauf.most_common(8))}")
        tage = Counter(nachkauf_zeiten)
        letzte = sorted(tage)[-6:]
        print(f"  Letzte Nachkauf-Tage: "
              f"{[(d, tage[d]) for d in letzte]}")
    else:
        print("  KEIN einziger Nachkauf im Journal.")

    # Wann trat der Exposure-Check in Kraft?
    if os.path.isfile(LOG):
        n_block = 0
        n_limit = 0
        with open(LOG, encoding="utf-8", errors="ignore") as f:
            for z in f:
                if "kein Nachkauf" in z and "Exposure-Limit" in z:
                    n_block += 1
                elif "Nachkauf-Limit erreicht" in z:
                    n_limit += 1
        print(f"\n  Im aktuellen system.log:")
        print(f"    'Exposure-Limit ... kein Nachkauf'  {n_block} mal")
        print(f"    'Nachkauf-Limit erreicht'           {n_limit} mal")


def punkt_26():
    kopf("2.6  Werden Gebuehren aus ccxt-Metadaten gezogen?")
    treffer = []
    muster = re.compile(
        r"\.fees\b|fetch_trading_fees|fetchTradingFees|"
        r"\[['\"]taker['\"]\]|\[['\"]maker['\"]\]|"
        r"markets\[[^\]]+\]\s*\.?\s*get\(['\"](taker|maker)")
    for wurzel, dirs, dateien in os.walk(PROJEKT):
        dirs[:] = [d for d in dirs if d not in
                   ("__pycache__", ".git", "data_store", "v4_data")]
        for d in dateien:
            if not d.endswith(".py"):
                continue
            p = os.path.join(wurzel, d)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if "ccxt" not in txt:
                continue
            for i, z in enumerate(txt.splitlines(), 1):
                if muster.search(z):
                    treffer.append((os.path.relpath(p, PROJEKT), i,
                                    z.strip()[:100]))
    print(f"  Dateien mit ccxt-Import UND Gebuehrenzugriff: {len(treffer)}")
    for p, i, z in treffer:
        print(f"    {p}:{i}  {z}")
    if not treffer:
        print("    KEINE. Gebuehren kommen ausschliesslich aus statischen")
        print("    Tabellen: backtest/fees.py:9-13 und")
        print("    backtest/ausstieg_backtest.py:59-60 (GEBUEHR=0,001).")


def punkt_31():
    kopf("3.1  Logvolumen-Hochrechnung fuer die drei neuen Logzeilen")
    if not os.path.isfile(LOG):
        print("  system.log fehlt")
        return
    n_ges = 0
    n_buy = 0
    n_sell_sig = 0
    n_risk = 0
    n_risk_buy = 0
    n_sleep = 0
    n_kill = 0
    erste = letzte = None
    with open(LOG, encoding="utf-8", errors="ignore") as f:
        for z in f:
            n_ges += 1
            if z.startswith("[2"):
                if erste is None:
                    erste = z[1:20]
                letzte = z[1:20]
            if "[SIGNAL]" in z and "-> BUY" in z:
                n_buy += 1
            if "[SIGNAL]" in z and "SELL " in z:
                n_sell_sig += 1
            if "[RISK]" in z:
                n_risk += 1
                if "BUY" in z:
                    n_risk_buy += 1
            if "Sleep-Mode" in z or "Schlafmodus" in z:
                n_sleep += 1
            if "Kill-Switch" in z:
                n_kill += 1
    print(f"  Datei: data_store/system.log, {n_ges} Zeilen, "
          f"{os.path.getsize(LOG)} Bytes")
    print(f"  Zeitraum: {erste} .. {letzte}")
    print(f"    [SIGNAL] ... -> BUY          {n_buy:7d}")
    print(f"    [SIGNAL] ... SELL            {n_sell_sig:7d}")
    print(f"    [RISK] gesamt                {n_risk:7d}")
    print(f"    [RISK] mit 'BUY'             {n_risk_buy:7d}")
    print(f"    Zeilen mit Sleep-Mode        {n_sleep:7d}")
    print(f"    Zeilen mit Kill-Switch       {n_kill:7d}")
    if n_buy:
        mittel = os.path.getsize(LOG) / max(n_ges, 1)
        zusatz = n_buy * 95            # ~95 Byte je neuer RISK-Zeile
        print(f"\n  Mittlere Zeilenlaenge: {mittel:.0f} Byte")
        print(f"  Eine zusaetzliche Ablehnungszeile je BUY-Intent:")
        print(f"    + {n_buy} Zeilen  =  +{zusatz/1024/1024:.2f} MB "
              f"ueber denselben Zeitraum")
        print(f"    Logwachstum: {os.path.getsize(LOG)/1024/1024:.2f} MB -> "
              f"{(os.path.getsize(LOG)+zusatz)/1024/1024:.2f} MB "
              f"(+{zusatz/os.path.getsize(LOG)*100:.1f} %)")


def main():
    print("AUDIT BUG-LISTE - read-only, keine Aenderung")
    print("Projekt:", PROJEKT)
    punkt_24()
    punkt_26()
    punkt_31()
    return 0


if __name__ == "__main__":
    sys.exit(main())
