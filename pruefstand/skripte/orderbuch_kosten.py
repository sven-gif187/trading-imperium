# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A6 Kosten-Analyst: Was kostet ein Marktauftrag ZUSAETZLICH zur Gebuehr?

Je Boerse und Muenze aus dem oeffentlichen Orderbuch (ccxt, kein Konto):
  - Spanne (best ask - best bid) / Mitte
  - Schlupf je Seite fuer einen Marktkauf von N $: (Durchschnittskurs - Mitte) / Mitte
    = halbe Spanne + Kursverschiebung durch die Groesse
Mehrere Schnappschuesse im Abstand, Median.

Nur oeffentliche Endpunkte, keine Schluessel. Ergebnis: berichte/<datum>_orderbuch.json
Aufruf: python orderbuch_kosten.py [--runden 3] [--abstand 20]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
BERICHTE = HIER.parent / "berichte"

# ccxt-Kennung, Optionen (EU-Einstiege, wo ccxt sie kennt), Muenzen
BOERSEN = {
    "bitvavo":  ("bitvavo", {}, ["BTC/USDC", "ETH/USDC", "SOL/USDC", "BTC/EUR", "ETH/EUR", "SOL/EUR"]),
    "okx_eea":  ("myokx", {}, ["BTC/USDC", "ETH/USDC", "SOL/USDC"]),
    "bybit_eu": ("bybit", {"hostname": "bybit.eu"}, ["BTC/USDC", "ETH/USDC", "SOL/USDC"]),
    "kraken":   ("kraken", {}, ["BTC/USDC", "ETH/USDC", "SOL/USDC"]),
    "gate":     ("gate", {}, ["BTC/USDC", "ETH/USDC", "SOL/USDC"]),
    "binance":  ("binance", {}, ["BTC/USDC", "ETH/USDC", "SOL/USDC"]),   # nur Vergleich (Kursquelle)
}
GROESSEN = (161.0, 250.0)


def schlupf(asks: list, mitte: float, usd: float) -> float | None:
    """Durchschnittlicher Fuellkurs eines Marktkaufs von usd, als % ueber der Mitte."""
    rest, kosten, menge = usd, 0.0, 0.0
    for preis, vol, *_ in asks:
        wert = preis * vol
        nimm = min(rest, wert)
        kosten += nimm
        menge += nimm / preis
        rest -= nimm
        if rest <= 1e-9:
            break
    if rest > 1e-6 or menge <= 0:
        return None                      # Buch zu duenn
    return ((kosten / menge) / mitte - 1) * 100


def messen(runden: int, abstand: int) -> dict:
    """[14.10.2026] Je Boerse ein eigener Faden - nacheinander dauerte es > 1 h."""
    from concurrent.futures import ThreadPoolExecutor
    erg: dict = {}
    with ThreadPoolExecutor(max_workers=len(BOERSEN)) as pool:
        for name, teil in zip(BOERSEN, pool.map(lambda kv: messe_boerse(kv[0], *kv[1], runden, abstand),
                                                BOERSEN.items())):
            erg[name] = teil
    return erg


def messe_boerse(name: str, cid: str, opt: dict, muenzen: list, runden: int, abstand: int) -> dict:
    erg = {name: {}}
    if True:
        if not hasattr(ccxt, cid):
            return {"fehler": f"ccxt kennt '{cid}' nicht"}
        try:
            ex = getattr(ccxt, cid)({"enableRateLimit": True, "timeout": 30000, **opt})
            t0 = time.time()
            ex.load_markets()
            erg[name] = {"_ladezeit_s": round(time.time() - t0, 1)}
            print(f"{time.strftime('%H:%M:%S')} {name}: Maerkte geladen in {erg[name]['_ladezeit_s']} s", flush=True)
        except Exception as e:
            print(f"{time.strftime('%H:%M:%S')} {name}: fehler {type(e).__name__}", flush=True)
            return {"fehler": f"{type(e).__name__}: {str(e)[:120]}"}
        for sym in muenzen:
            if sym not in ex.markets:
                erg[name][sym] = {"vorhanden": False}; continue
            proben = []
            for _ in range(runden):
                try:
                    ob = ex.fetch_order_book(sym, limit=50)
                    bid, ask = ob["bids"][0][0], ob["asks"][0][0]
                    mitte = (bid + ask) / 2
                    proben.append({"spanne": (ask - bid) / mitte * 100,
                                   **{f"schlupf_{int(g)}": schlupf(ob["asks"], mitte, g) for g in GROESSEN}})
                except Exception as e:
                    proben.append({"fehler": type(e).__name__})
                time.sleep(abstand if runden > 1 else 0)
            gut = [p for p in proben if "fehler" not in p]
            def med(k):
                w = [p[k] for p in gut if p.get(k) is not None]
                return round(st.median(w), 4) if w else None
            erg[name][sym] = {"vorhanden": True, "proben": len(gut), "spanne_pct": med("spanne"),
                              **{f"schlupf_{int(g)}_pct": med(f"schlupf_{int(g)}") for g in GROESSEN}}
            print(f"{time.strftime('%H:%M:%S')} {name:9s} {sym:9s} Spanne {erg[name][sym]['spanne_pct']} % | "
                  f"Schlupf 161$ {erg[name][sym]['schlupf_161_pct']} % | 250$ {erg[name][sym]['schlupf_250_pct']} %",
                  flush=True)
    return erg[name]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runden", type=int, default=3)
    ap.add_argument("--abstand", type=int, default=20)
    a = ap.parse_args()
    jetzt = datetime.now(timezone.utc)
    erg = messen(a.runden, a.abstand)
    BERICHTE.mkdir(exist_ok=True)
    ziel = BERICHTE / f"{jetzt:%Y-%m-%d}_orderbuch.json"
    ziel.write_text(json.dumps({"datum_utc": jetzt.isoformat(), "agent": "kosten-analyst",
                                "methode": __doc__.strip().splitlines()[0], "runden": a.runden,
                                "abstand_s": a.abstand, "ergebnis": erg}, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("gespeichert:", ziel)
