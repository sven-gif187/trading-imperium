# -*- coding: utf-8 -*-
"""
history_harvester.py - Makro-Gedaechtnis: Bitcoin-Zyklen seit 2017
===================================================================
Baut die historische Datengrundlage fuer das Situation-Memory
(Makro-Schicht): laedt Daily-Candles + Fear&Greed-Historie, berechnet
Zyklus-Features, labelt Marktphasen und speichert Forward-Returns
als Outcome ("was kam nach solchen Situationen?").

Datenquellen (alle frei):
  - OHLCV 1d: Binance via ccxt (Fallback: Kraken)
  - Fear&Greed: api.alternative.me (Historie seit Feb 2018)
  - On-Chain (MVRV/SOPR/...): NICHT enthalten - als optionale Schicht
    vorbereitet (fetch_onchain-Stub), braucht spaeter nur einen API-Key.

Annahmen/Grenzen (dokumentiert):
  - Tagesbasis reicht fuer Zyklus-Lernen; Tick-Daten sind Overkill.
  - Phasen-Labels sind eine v1-HEURISTIK (Mayer Multiple + Drawdown +
    Momentum). Roh-Features werden mitgespeichert, damit Labels spaeter
    neu berechnet werden koennen, ohne neu zu downloaden.
  - F&G vor Feb 2018 fehlt -> null (Situation-Memory maskiert das).
  - Ausgabe JSON (~3200 Zeilen) statt Parquet - bewusst, passt zur
    bestehenden V6-Datenhaltung.

Nutzung (auf Svens Rechner, Internet noetig):
    python history_harvester.py
    python history_harvester.py --symbol ETH/USDT --out data_store/situation_history_eth.json

Ziel-Pfad: V6-Hauptordner. Output: data_store/situation_history.json
Der Bot muss dafuer NICHT geschlossen werden (nur neue Datei).
"""
import os
import sys
import json
import time
import math
import argparse
from datetime import datetime, timezone

DAY_MS = 86400000


def log(msg):
    print(f"[HARVEST] {msg}")


# ======================================================================
# 1) DOWNLOAD
# ======================================================================
def fetch_ohlcv_full(symbol="BTC/USDT", exchange_id="binance",
                     since_iso="2017-08-01", max_retries=5):
    """Laedt komplette Daily-History paginiert via ccxt, mit Retry."""
    import ccxt
    ex_cls = getattr(ccxt, exchange_id)
    ex = ex_cls({"enableRateLimit": True})
    since = int(datetime.fromisoformat(since_iso)
                .replace(tzinfo=timezone.utc).timestamp() * 1000)
    now_ms = int(time.time() * 1000)
    all_bars = []
    while since < now_ms:
        bars = None
        for attempt in range(1, max_retries + 1):
            try:
                bars = ex.fetch_ohlcv(symbol, "1d", since=since, limit=1000)
                break
            except Exception as e:
                wait = min(2 ** attempt, 30)
                log(f"  Retry {attempt}/{max_retries} in {wait}s ({str(e)[:60]})")
                time.sleep(wait)
        if bars is None:
            raise RuntimeError(f"{exchange_id}: Download endgueltig fehlgeschlagen")
        if not bars:
            break
        all_bars.extend(bars)
        since = bars[-1][0] + DAY_MS
        log(f"  {len(all_bars)} Kerzen bis "
            f"{datetime.fromtimestamp(bars[-1][0]/1000, tz=timezone.utc).date()}")
        time.sleep((ex.rateLimit or 500) / 1000.0)
    # Dedupe + sortieren
    seen, out = set(), []
    for b in sorted(all_bars, key=lambda x: x[0]):
        if b[0] not in seen:
            seen.add(b[0])
            out.append(b)
    return out


def fetch_candles(symbol, prefer="binance"):
    """Binance zuerst, Kraken als Fallback (dort heisst BTC oft XBT)."""
    try:
        log(f"Lade {symbol} Daily-Candles von Binance...")
        return fetch_ohlcv_full(symbol, "binance")
    except Exception as e:
        log(f"Binance fehlgeschlagen ({str(e)[:80]}) -> Fallback Kraken")
        alt = symbol.replace("USDT", "USD")
        return fetch_ohlcv_full(alt, "kraken", since_iso="2014-01-01")


def fetch_fear_greed(max_retries=4):
    """Komplette F&G-Historie von alternative.me. date_str -> int."""
    import requests
    url = "https://api.alternative.me/fng/?limit=0&format=json"
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json().get("data", [])
            out = {}
            for d in data:
                ts = int(d.get("timestamp", 0))
                day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                out[day] = int(d.get("value", 0))
            log(f"F&G-Historie: {len(out)} Tage geladen")
            return out
        except Exception as e:
            wait = min(2 ** attempt, 20)
            log(f"  F&G Retry {attempt}/{max_retries} in {wait}s ({str(e)[:60]})")
            time.sleep(wait)
    log("F&G-Historie nicht erreichbar - fahre ohne fort (Werte = null)")
    return {}


def fetch_onchain(day_iso):
    """STUB: optionale On-Chain-Schicht (MVRV, SOPR, ...).
    Spaeter: API-Key in .env (z.B. ONCHAIN_API_KEY) + Implementierung.
    Rueckgabe None-Werte -> Situation-Memory maskiert sie sauber."""
    return {"mvrv": None, "sopr": None}


# ======================================================================
# 2) FEATURES
# ======================================================================
def sma(vals, i, n):
    if i + 1 < n:
        return None
    window = vals[i - n + 1:i + 1]
    return sum(window) / n


def rsi14(closes, i, n=14):
    if i < n:
        return None
    gains = losses = 0.0
    for j in range(i - n + 1, i + 1):
        d = closes[j] - closes[j - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100 - 100 / (1 + rs)


def build_rows(bars, fg_map):
    closes = [b[4] for b in bars]
    rows = []
    ath = 0.0
    for i, b in enumerate(bars):
        ts, o, h, l, c, v = b[0], b[1], b[2], b[3], b[4], b[5]
        ath = max(ath, c)
        day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date().isoformat()

        s200 = sma(closes, i, 200)
        s50 = sma(closes, i, 50)
        if s200 is None:
            continue  # Warmup

        # Volatilitaet: Std der Tagesreturns (30d, in %)
        rets = [(closes[j] / closes[j - 1] - 1) * 100
                for j in range(i - 29, i + 1)]
        mean_r = sum(rets) / len(rets)
        vol30 = math.sqrt(sum((r - mean_r) ** 2 for r in rets) / len(rets))

        ret_30d = (c / closes[i - 30] - 1) * 100 if i >= 30 else None
        ret_90d = (c / closes[i - 90] - 1) * 100 if i >= 90 else None
        mayer = c / s200
        drawdown = (c / ath - 1) * 100
        trend = "UP" if (s50 and s50 > s200) else "DOWN"

        rows.append({
            "date": day,
            "close": round(c, 2),
            "features": {
                "rsi": round(rsi14(closes, i) or 50, 1),
                "mayer": round(mayer, 3),
                "drawdown_ath": round(drawdown, 1),
                "vol30": round(vol30, 2),
                "ret_30d": round(ret_30d, 1) if ret_30d is not None else None,
                "ret_90d": round(ret_90d, 1) if ret_90d is not None else None,
                "sma_trend": trend,
                "fear_greed": fg_map.get(day),
                **fetch_onchain(day),
            },
        })
    return rows


# ======================================================================
# 3) LABELS (v1-Heuristik - Annahmen dokumentiert im Header)
# ======================================================================
def label_phase(f):
    dd = f["drawdown_ath"]
    mayer = f["mayer"]
    r30 = f["ret_30d"] if f["ret_30d"] is not None else 0
    trend = f["sma_trend"]

    if dd <= -55 and r30 <= -15:
        return "KAPITULATION"
    if dd <= -45 and mayer < 0.85:
        return "AKKUMULATION"
    if mayer >= 2.4 or (dd > -10 and r30 >= 40):
        return "EUPHORIE"
    if dd > -20 and r30 < 0 and mayer >= 1.3:
        return "DISTRIBUTION"
    if trend == "UP" and r30 > 0:
        return "EXPANSION"
    if trend == "DOWN" and r30 < 0:
        return "BAER_TREND"
    return "UEBERGANG"


def add_labels_and_outcomes(rows):
    closes = [r["close"] for r in rows]
    for i, r in enumerate(rows):
        r["phase"] = label_phase(r["features"])
        r["outcome"] = {
            "fwd_7d": round((closes[i + 7] / closes[i] - 1) * 100, 2)
            if i + 7 < len(rows) else None,
            "fwd_30d": round((closes[i + 30] / closes[i] - 1) * 100, 2)
            if i + 30 < len(rows) else None,
            "fwd_90d": round((closes[i + 90] / closes[i] - 1) * 100, 2)
            if i + 90 < len(rows) else None,
        }
    return rows


# ======================================================================
# 4) QUALITAET + SPEICHERN
# ======================================================================
def quality_report(rows):
    from collections import Counter
    phases = Counter(r["phase"] for r in rows)
    fg_missing = sum(1 for r in rows if r["features"]["fear_greed"] is None)
    gaps = 0
    for a, b in zip(rows, rows[1:]):
        d1 = datetime.fromisoformat(a["date"])
        d2 = datetime.fromisoformat(b["date"])
        if (d2 - d1).days > 1:
            gaps += 1
    log(f"Zeitraum: {rows[0]['date']} -> {rows[-1]['date']} ({len(rows)} Tage)")
    log(f"Datenluecken (>1 Tag): {gaps} | F&G fehlend: {fg_missing} Tage")
    log("Phasen-Verteilung:")
    for p, n in phases.most_common():
        log(f"  {p:14s}: {n:5d} Tage ({n/len(rows)*100:.0f}%)")
    # Sanity: durchschnittlicher 30d-Forward-Return je Phase
    log("Oe Forward-Return 30d je Phase (Plausibilitaets-Check):")
    for p in phases:
        vals = [r["outcome"]["fwd_30d"] for r in rows
                if r["phase"] == p and r["outcome"]["fwd_30d"] is not None]
        if vals:
            log(f"  {p:14s}: {sum(vals)/len(vals):+6.1f}%  (n={len(vals)})")


def save(rows, out_path, symbol):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    payload = {
        "created_at": datetime.now().isoformat(),
        "symbol": symbol,
        "source": "binance/kraken 1d + alternative.me F&G",
        "label_version": "heuristik_v1",
        "count": len(rows),
        "days": rows,
    }
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    with open(tmp, "r", encoding="utf-8") as f:
        json.load(f)  # Validierung vor Ersetzen
    os.replace(tmp, out_path)
    log(f"Gespeichert: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTC/USDT")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    out = args.out or os.path.join(base, "data_store", "situation_history.json")

    print("=" * 60)
    print("HISTORY HARVESTER - Makro-Gedaechtnis fuer das V6-Brain")
    print("=" * 60)
    bars = fetch_candles(args.symbol)
    if len(bars) < 300:
        log(f"FEHLER: nur {len(bars)} Kerzen - zu wenig. Abbruch.")
        sys.exit(1)
    fg = fetch_fear_greed()
    rows = build_rows(bars, fg)
    rows = add_labels_and_outcomes(rows)
    quality_report(rows)
    save(rows, out, args.symbol)
    print("Fertig. Naechster Schritt: Makro-Replay (Sensei baut ihn).")


if __name__ == "__main__":
    main()
