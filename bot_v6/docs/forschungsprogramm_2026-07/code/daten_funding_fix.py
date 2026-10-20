# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - Phase 3, Funding-Korrektur 30.07.2026.
"""
KORREKTUR des Funding-Downloads aus daten_pilot_download.py.

FEHLERBILD (dokumentiert, kein stiller Ersatz): Der Erstlauf paginierte ab
startTime=0. fapi/v1/fundingRate liefert bei startTime=0 nur die JUENGSTEN
~500 Eintraege (2026-02..2026-07) statt der Historie ab Perp-Listing. Die
Erstdateien waren daher unbrauchbar verkuerzt.

KORREKTUR: explizite Zeitfenster (90 Tage) von 2019-09-01 bis heute; je
Fenster < 1000 Eintraege (90 x 3 = 270), damit greift kein Limit.
Verifiziert am 30.07.2026: expliziter Range-Abruf liefert 2019er-Daten.

Die fehlerhaften Erstdateien werden ERSETZT; alte Pruefsummen bleiben in
PRUEFSUMMEN.txt stehen und werden dort als ERSETZT markiert, neue Summen
angehaengt. QUELLENPROTOKOLL.txt erhaelt einen Korrektureintrag.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATEN = os.path.join(BASIS, "daten", "funding")
PROTO = os.path.join(BASIS, "QUELLENPROTOKOLL.txt")
SUMMEN = os.path.join(BASIS, "PRUEFSUMMEN.txt")

SYMBOLE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT",
           "LINKUSDT", "DOTUSDT", "DOGEUSDT", "NEARUSDT", "UNIUSDT",
           "ATOMUSDT", "XRPUSDT"]
URL = "https://fapi.binance.com/fapi/v1/fundingRate"
START = 1567296000000            # 2019-09-01 (vor dem ersten USDT-Perp-Funding)
FENSTER_MS = 90 * 86_400_000
UA = {"User-Agent": "forschungsprogramm-pilot/1.0 (privates Research)"}


def hole(url, versuche=4):
    for v in range(versuche):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception:
            if v == versuche - 1:
                raise
            time.sleep(2 * (v + 1))


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def main():
    jetzt = int(time.time() * 1000)
    stamp = datetime.now(timezone.utc).isoformat()[:19] + "Z"
    with open(PROTO, "a", encoding="utf-8") as f:
        f.write(f"{stamp}  KORREKTUR: Funding-Erstdateien waren auf ~500 "
                f"juengste Eintraege verkuerzt (startTime=0-Fehler). "
                f"Neuabruf mit 90-Tage-Fenstern ab 2019-09-01.\n")
    for s in SYMBOLE:
        rows = []
        t = START
        while t < jetzt:
            u = f"{URL}?symbol={s}&startTime={t}&endTime={min(t + FENSTER_MS, jetzt)}&limit=1000"
            try:
                chunk = json.loads(hole(u))
            except Exception as e:
                print(f"  {s}: FEHLER Fenster {iso(t)}: {e}")
                chunk = []
            rows.extend(chunk)
            t += FENSTER_MS
            time.sleep(0.12)
        # Duplikate (Fenstergrenzen) entfernen, sortieren
        ded = {}
        for r in rows:
            ded[r["fundingTime"]] = r
        rows = [ded[k] for k in sorted(ded)]
        if not rows:
            print(f"  {s}: KEINE DATEN")
            continue
        p = os.path.join(DATEN, f"{s}_funding8h.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("fundingTime,fundingRate,markPrice\n")
            for r in rows:
                f.write(f"{r['fundingTime']},{r['fundingRate']},{r.get('markPrice','')}\n")
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        rel = os.path.relpath(p, BASIS).replace("\\", "/")
        with open(SUMMEN, "a", encoding="utf-8") as f:
            f.write(f"{h}  {rel}  (v2, ersetzt fehlerhafte Erstversion)\n")
        with open(PROTO, "a", encoding="utf-8") as f:
            f.write(f"{stamp}  {s} funding v2  {len(rows)} Zeilen  "
                    f"{iso(rows[0]['fundingTime'])}..{iso(rows[-1]['fundingTime'])}  "
                    f"Quelle: fapi.binance.com/fapi/v1/fundingRate (Fenster-Pagination)\n")
        print(f"  {s}: {len(rows)} Eintraege  {iso(rows[0]['fundingTime'])}.."
              f"{iso(rows[-1]['fundingTime'])}")
    print("FERTIG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
