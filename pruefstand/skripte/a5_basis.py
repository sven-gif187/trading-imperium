# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 ausstiegs-pruefer · gemeinsame Grundlage (nur lesen).

- Runden v6 E7 (136, Verkaeufe 2026-08-13T13:21:19Z .. 2026-10-14T09:18:25Z) ueber runden_lib,
  angereichert um Verkaufs- und Kaufsatz aus trades_v5.json (mfe/mae/pnl_pct/Grund/Regime/...).
- Kerzen aus pruefstand/daten (binance_1m_*, binance_1h_*), nur abgeschlossene Kerzen.
- Netto-Rechnung je Kostenlatte K: netto_pct = brutto_pct - K ; netto_usd = kauf_nominal * netto_pct/100
  (Gebuehrentausch wie A6; Kasse bleibt die Referenz fuer K = Ist).
- Block-Bootstrap nach Kalendertagen.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runden_lib import lade, runden  # noqa: E402

V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
V7 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v7")
DATEN = Path(r"C:\Users\<BENUTZER>\Desktop\pruefstand\daten")
VON, BIS = "2026-08-13T13:21:19", "2026-10-14T09:18:25"
PHASE_GRENZE = "2026-09-01"          # Kauf vor 01.09. = August-Anstieg, danach September/Oktober
K_BITVAVO, K_BYBIT = 0.150, 0.505
ABSCHLAG_NACHSPIELUNG = 0.15


def ts_ms(s: str) -> int:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return int(d.timestamp() * 1000)


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M")


def phase(kauf_t: str) -> str:
    return "A_Aug" if kauf_t < PHASE_GRENZE else "B_SepOkt"


def runden_e7() -> list[dict]:
    rows = lade(V6)
    R = runden(rows, VON, BIS)
    sells = {(r["time"], r["coin"]): r for r in rows if str(r.get("type", "")).upper() == "SELL"}
    buys = {}
    for r in rows:
        if str(r.get("type", "")).upper() == "BUY":
            buys.setdefault((r["time"], r["coin"]), r)
    # Kauf-Menge je Runde: alle Kaeufe der Muenze seit dem letzten Verkauf (runden_lib-Logik)
    offen: dict[str, list] = {}
    kauf_qty = {}
    for r in rows:
        typ = str(r.get("type", "")).upper()
        if typ == "BUY":
            offen.setdefault(r["coin"], []).append(r)
        elif typ == "SELL" and offen.get(r["coin"]):
            ks = offen.pop(r["coin"])
            kauf_qty[(r["time"], r["coin"])] = sum(float(k.get("qty") or 0) for k in ks)
    out = []
    for r in R:
        s = sells[(r["t"], r["coin"])]
        b = buys.get((r["kauf_t"], r["coin"]), {})
        q = kauf_qty[(r["t"], r["coin"])]
        e_preis = r["kauf_nominal"] / q
        v_preis = float(s["price"])
        x = dict(r)
        x.update({
            "einstieg_preis": e_preis,
            "verkauf_preis": v_preis,
            # runden_lib nimmt Verkaufs-amount als qty*Kurs. Auf dem Schreibpfad execute_approved_trade
            # (21 Signal-Verkaeufe) ist amount aber schon OHNE Verkaufsgebuehr (engine.py:439-451,
            # filled_cost = net) -> dort wird die Verkaufsgebuehr doppelt abgezogen (a5_kasse_signalpfad.py).
            # Deshalb gilt hier brutto_pct = Kursbewegung Verkauf/Kauf (gegengeprueft: 115 exit_monitor-
            # Runden identisch, 21 Signal-Runden +0,25 Punkte).
            "brutto_pct_lib": (r["verkauf_nominal"] / r["kauf_nominal"] - 1) * 100,
            "brutto_pct": (v_preis / e_preis - 1) * 100,
            "kurs_pct": (v_preis / e_preis - 1) * 100,
            "pnl_pct_bot": s.get("pnl_pct"),
            "mfe_bot": s.get("mfe_pct"),
            "mae_bot": s.get("mae_pct"),
            "grund": s.get("reason", ""),
            "regime": s.get("market_regime"),
            "zyklus": s.get("cycle_phase"),
            "position_id": s.get("position_id"),
            "haltedauer_min": s.get("haltedauer_min"),
            "schlupf_verkauf": s.get("slippage_pct"),
            "schlupf_kauf": b.get("slippage_pct"),
            "kauf_score": b.get("signal_score", b.get("score")),
            "phase": phase(r["kauf_t"]),
            "kauf_ms": ts_ms(r["kauf_t"]),
            "verkauf_ms": ts_ms(r["t"]),
        })
        out.append(x)
    return out


def netto_pct(brutto_pct: float, K: float) -> float:
    return brutto_pct - K


# ---------------------------------------------------------------- Kerzen
class Kerzen:
    """Abgeschlossene Binance-Kerzen eines Zeitrahmens je Muenze als numpy-Arrays."""

    def __init__(self, tf: str):
        self.tf = tf
        self.step = {"1m": 60_000, "1h": 3_600_000}[tf]
        self.d = {}
        for coin in ("BTC/USDC", "ETH/USDC", "SOL/USDC"):
            p = DATEN / f"binance_{tf}_{coin.replace('/', '_')}.csv"
            z = []
            with open(p, encoding="utf-8") as f:
                rd = csv.reader(f)
                kopf = next(rd)
                pos = [kopf.index(n) for n in ("ts_ms", "open", "high", "low", "close")]   # A4-Format hat open_utc
                for row in rd:
                    if row and row[0].isdigit():
                        z.append([float(row[i]) for i in pos])
            a = np.array(z, dtype=float)
            a = a[np.argsort(a[:, 0])]
            _, idx = np.unique(a[:, 0], return_index=True)
            a = a[idx]
            self.d[coin] = {"t": a[:, 0].astype(np.int64), "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4]}

    def ab(self, coin: str, t_ms: int) -> int:
        """Index der ersten Kerze, die bei oder nach t_ms beginnt."""
        return int(np.searchsorted(self.d[coin]["t"], t_ms, side="left"))

    def kurs_bei(self, coin: str, t_ms: int) -> float | None:
        """Schlusskurs der letzten abgeschlossenen Kerze vor t_ms + step (Kerze, in der t_ms liegt)."""
        t = self.d[coin]["t"]
        i = int(np.searchsorted(t, t_ms, side="right")) - 1
        if i < 0 or t_ms > t[-1] + self.step:
            return None
        return float(self.d[coin]["c"][i])

    def ende(self, coin: str) -> int:
        return int(self.d[coin]["t"][-1] + self.step)


def atr_pct_1h(k1h: Kerzen, coin: str, n: int = 14) -> tuple[np.ndarray, np.ndarray]:
    """ATR(n) nach Wilder (RMA) auf 1h-Kerzen in % vom Schluss; Wert gilt NACH Abschluss der Kerze.
    Rueckgabe (t_gueltig_ab_ms, atr_pct)."""
    d = k1h.d[coin]
    h, l, c = d["h"], d["l"], d["c"]
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = np.empty_like(tr)
    atr[:n] = np.nan
    atr[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    return d["t"] + k1h.step, atr / c * 100


def atr_bei(t_gueltig: np.ndarray, atrp: np.ndarray, t_ms: int) -> float:
    i = int(np.searchsorted(t_gueltig, t_ms, side="right")) - 1
    return float(atrp[i]) if i >= 0 else float("nan")


# ---------------------------------------------------------------- Statistik
def block_bootstrap(tage: list[str], werte: list[float], stat="mittel", B: int = 10000,
                    alpha: float = 0.05, seed: int = 7) -> tuple[float, float, float]:
    """Block-Bootstrap nach Kalendertagen. stat='mittel' (je Runde) oder 'summe'.
    Rueckgabe (Punktwert, untere, obere Grenze) fuer (1-alpha)-Bereich."""
    rng = np.random.default_rng(seed)
    by: dict[str, list[float]] = {}
    for t, w in zip(tage, werte):
        by.setdefault(t, []).append(w)
    keys = sorted(by)
    sums = np.array([sum(by[k]) for k in keys])
    cnts = np.array([len(by[k]) for k in keys])
    if len(keys) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, len(keys), size=(B, len(keys)))
    s = sums[idx].sum(axis=1)
    if stat == "mittel":
        n = cnts[idx].sum(axis=1)
        v = s / np.maximum(n, 1)
        punkt = sums.sum() / cnts.sum()
    else:
        v = s
        punkt = sums.sum()
    lo, hi = np.quantile(v, [alpha / 2, 1 - alpha / 2])
    return float(punkt), float(lo), float(hi)


def speichere(name: str, obj) -> Path:
    p = DATEN / name
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    os.replace(tmp, p)
    return p


def pv_verbindung(bot: Path = V6):
    return sqlite3.connect(f"file:{bot / 'data_store' / 'positionsverlauf.db'}?mode=ro", uri=True)


def nl_verbindung(bot: Path = V6):
    return sqlite3.connect(f"file:{bot / 'data_store' / 'nachlauf.db'}?mode=ro", uri=True)
