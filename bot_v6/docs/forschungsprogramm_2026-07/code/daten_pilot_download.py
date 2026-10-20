# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - Phase 3 Pilot-Download 30.07.2026.
"""
Pilot-Download des historischen Datenfundaments (Phase 3, Pfad B).

QUELLEN (alle kostenlos, oeffentlich, ohne API-Key):
  1. Spot-Klines 1d:  https://data-api.binance.vision/api/v3/klines
     (oeffentlicher Marktdaten-Mirror; Kursverlaeufe sind boersenueber-
     greifend nahezu identisch - Beschluss vom 30.07.2026, Binance selbst
     scheidet als Handelsplatz aus)
  2. Funding-Historie: https://fapi.binance.com/fapi/v1/fundingRate
     (oeffentlich, 8h-Funding je USDT-Perp seit Listing)
  3. Makro:            https://fred.stlouisfed.org/graph/fredgraph.csv
     DTWEXBGS (Broad Dollar Index) + DTWEXAFEGS (Advanced Foreign
     Economies) als freier DXY-Ersatz. Der ICE-DXY selbst ist proprietaer.

ABLAGE: docs/forschungsprogramm_2026-07/daten/  (unter docs/ -> von
cleanup.py KEEP_DIRS geschuetzt). Bestehende Dateien werden NIE
ueberschrieben, ausser via --force (Aenderungsstopp-Regel).

Jede Datei bekommt einen Eintrag in QUELLENPROTOKOLL.txt (URL, Zeitpunkt,
Zeilen, Zeitbereich) und in PRUEFSUMMEN.txt (SHA256).

Universum Pilot: die 11 config-Coins + XRP (Journal-Altlast), USDT-Paare.
1d fuer alle; 4h nur BTC/ETH (Pilotumfang, Rest nach Boersen-/
Universums-Entscheid).
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASIS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATEN = os.path.join(BASIS, "daten")
PROTO = os.path.join(BASIS, "QUELLENPROTOKOLL.txt")
SUMMEN = os.path.join(BASIS, "PRUEFSUMMEN.txt")

SYMBOLE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT",
           "LINKUSDT", "DOTUSDT", "DOGEUSDT", "NEARUSDT", "UNIUSDT",
           "ATOMUSDT", "XRPUSDT"]
VIERSTUNDEN = ["BTCUSDT", "ETHUSDT"]

KLINES = "https://data-api.binance.vision/api/v3/klines"
FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_IDS = ["DTWEXBGS", "DTWEXAFEGS"]

UA = {"User-Agent": "forschungsprogramm-pilot/1.0 (privates Research)"}


def hole(url, versuche=4):
    for v in range(versuche):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as e:
            if v == versuche - 1:
                raise
            time.sleep(2 * (v + 1))


def protokoll(zeile):
    with open(PROTO, "a", encoding="utf-8") as f:
        f.write(zeile + "\n")


def pruefsumme(pfad):
    h = hashlib.sha256(open(pfad, "rb").read()).hexdigest()
    rel = os.path.relpath(pfad, BASIS).replace("\\", "/")
    with open(SUMMEN, "a", encoding="utf-8") as f:
        f.write(f"{h}  {rel}\n")


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def lade_klines(symbol, intervall):
    out = []
    start = 0
    while True:
        url = f"{KLINES}?symbol={symbol}&interval={intervall}&startTime={start}&limit=1000"
        rows = json.loads(hole(url))
        if not rows:
            break
        out.extend(rows)
        if len(rows) < 1000:
            break
        start = rows[-1][0] + 1
        time.sleep(0.15)
    return out


def lade_funding(symbol):
    out = []
    start = 0
    while True:
        url = f"{FUNDING}?symbol={symbol}&startTime={start}&limit=1000"
        rows = json.loads(hole(url))
        if not rows:
            break
        out.extend(rows)
        if len(rows) < 1000:
            break
        start = rows[-1]["fundingTime"] + 1
        time.sleep(0.15)
    return out


def schreibe_klines(symbol, intervall, rows, force=False):
    d = os.path.join(DATEN, f"klines_{intervall}")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{symbol}_{intervall}.csv")
    if os.path.exists(p) and not force:
        print(f"  UEBERSPRUNGEN (existiert): {p}")
        return None
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write("zeit,open,high,low,close,volume,quote_volume,trades\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[7]},{r[8]}\n")
    protokoll(f"{datetime.now(timezone.utc).isoformat()[:19]}Z  {symbol} {intervall}  "
              f"{len(rows)} Zeilen  {iso(rows[0][0])}..{iso(rows[-1][0])}  "
              f"Quelle: data-api.binance.vision/api/v3/klines")
    pruefsumme(p)
    return p


def schreibe_funding(symbol, rows, force=False):
    d = os.path.join(DATEN, "funding")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{symbol}_funding8h.csv")
    if os.path.exists(p) and not force:
        print(f"  UEBERSPRUNGEN (existiert): {p}")
        return None
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write("fundingTime,fundingRate,markPrice\n")
        for r in rows:
            f.write(f"{r['fundingTime']},{r['fundingRate']},{r.get('markPrice','')}\n")
    protokoll(f"{datetime.now(timezone.utc).isoformat()[:19]}Z  {symbol} funding  "
              f"{len(rows)} Zeilen  {iso(rows[0]['fundingTime'])}.."
              f"{iso(rows[-1]['fundingTime'])}  Quelle: fapi.binance.com/fapi/v1/fundingRate")
    pruefsumme(p)
    return p


def main():
    force = "--force" in sys.argv
    os.makedirs(DATEN, exist_ok=True)
    print("=" * 78)
    print(" PILOT-DOWNLOAD Phase 3  -  Start",
          datetime.now(timezone.utc).isoformat()[:19] + "Z")
    print("=" * 78)

    # 1d-Klines alle Symbole
    for s in SYMBOLE:
        try:
            rows = lade_klines(s, "1d")
            print(f"  {s} 1d: {len(rows)} Tage "
                  f"({iso(rows[0][0])}..{iso(rows[-1][0])})")
            schreibe_klines(s, "1d", rows, force)
        except Exception as e:
            print(f"  {s} 1d: FEHLER {e}")

    # 4h nur Pilot
    for s in VIERSTUNDEN:
        try:
            rows = lade_klines(s, "4h")
            print(f"  {s} 4h: {len(rows)} Kerzen")
            schreibe_klines(s, "4h", rows, force)
        except Exception as e:
            print(f"  {s} 4h: FEHLER {e}")

    # Funding alle Symbole
    for s in SYMBOLE:
        try:
            rows = lade_funding(s)
            print(f"  {s} funding: {len(rows)} Eintraege "
                  f"({iso(rows[0]['fundingTime'])}..{iso(rows[-1]['fundingTime'])})")
            schreibe_funding(s, rows, force)
        except Exception as e:
            print(f"  {s} funding: FEHLER {e}")

    # Makro
    d = os.path.join(DATEN, "makro")
    os.makedirs(d, exist_ok=True)
    for sid in FRED_IDS:
        p = os.path.join(d, f"{sid}.csv")
        if os.path.exists(p) and not force:
            print(f"  UEBERSPRUNGEN (existiert): {p}")
            continue
        try:
            raw = hole(FRED.format(sid=sid))
            open(p, "wb").write(raw)
            n = raw.count(b"\n")
            print(f"  FRED {sid}: {n} Zeilen")
            protokoll(f"{datetime.now(timezone.utc).isoformat()[:19]}Z  FRED {sid}  "
                      f"{n} Zeilen  Quelle: fred.stlouisfed.org fredgraph.csv")
            pruefsumme(p)
        except Exception as e:
            print(f"  FRED {sid}: FEHLER {e}")

    print("FERTIG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
