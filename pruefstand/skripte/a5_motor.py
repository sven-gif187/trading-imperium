# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
A5 · Nachspiel-Motor fuer Ausstiegsregeln auf 1m-Kerzen (Binance, abgeschlossen).

Regel-Logik wie risk/exit_rules.py + runtime/exit_monitor.py (v6):
  - Verlustbremse: Kurs <= Einstieg * (1 - sl)
  - Nullsicherung: scharf ab Hoechststand >= be_ab, Ausstieg bei Gewinn <= puffer
  - Nachzieh-Stopp: ab Hoechststand >= start, Abstand = trail * Leiter-Faktor(Hoechststand)
    gemessen vom Hoechstkurs (Ratsche)
  - Verkaufssignal (optional): RSI(14, 1h, laufende Kerze) > 80 und Gewinn > 1,0 %  (agents/signal_agent.py:227)
Reihenfolge je Minute (vorsichtig): Stopp-Linie aus dem Stand VOR der Kerze gegen Eroeffnung/Tief,
erst danach Hoch fortschreiben; neue Linie nur gegen den Schluss. Signal nur auf dem Schluss.
Kein Blick in die Zukunft: jede Entscheidung nutzt nur Kerzen bis zur laufenden Minute.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LEITER = ((1.2, 1.0), (3.0, 1.3), (5.0, 1.7), (8.0, 2.2))


@dataclass
class Regel:
    name: str
    sl: float | None = 2.5                 # % ; None -> sl_fn je Runde
    start: float = 1.2                     # Nachzieh-Start (Hoechststand in %)
    trail: float = 1.0                     # Grundabstand in %
    leiter: bool = True
    be_ab: float | None = 1.0              # None = keine Nullsicherung
    puffer: float = 0.35
    signal: bool = True                    # RSI-Verkaufssignal nachbilden
    sl_fn: object = None                   # f(runde) -> sl in %
    trail_fn: object = None                # f(runde) -> trail in %
    notiz: str = ""
    extra: dict = field(default_factory=dict)


def leiter_faktor(hoch: float) -> float:
    f = LEITER[0][1]
    for s, x in LEITER:
        if hoch >= s:
            f = x
    return f


class RSIStunde:
    """RSI(14) nach Wilder auf 1h-Schlusskursen; die laufende Stunde nimmt den aktuellen Minutenschluss."""

    def __init__(self, k1h, k1m, coin: str, n: int = 14):
        d = k1h.d[coin]
        c = d["c"]
        delta = np.diff(c, prepend=c[0])
        g = np.maximum(delta, 0)
        lo = np.maximum(-delta, 0)
        ag = np.empty_like(c)
        al = np.empty_like(c)
        ag[0], al[0] = g[0], lo[0]
        a = 1.0 / n
        for i in range(1, len(c)):            # ewm(alpha=1/n, adjust=False) = Wilder-RMA
            ag[i] = ag[i - 1] * (1 - a) + g[i] * a
            al[i] = al[i - 1] * (1 - a) + lo[i] * a
        self.t = d["t"]                       # Beginn der Stunde
        self.c, self.ag, self.al, self.a = c, ag, al, a
        m = k1m.d[coin]
        # fuer jede Minute: Index der vorigen abgeschlossenen Stunde
        stunde = (m["t"] // 3_600_000) * 3_600_000
        idx = np.searchsorted(self.t, stunde, side="left") - 1
        ok = idx >= 0
        idx = np.clip(idx, 0, len(c) - 1)
        dlt = m["c"] - c[idx]
        ag_m = ag[idx] * (1 - a) + np.maximum(dlt, 0) * a
        al_m = al[idx] * (1 - a) + np.maximum(-dlt, 0) * a
        rsi = 100 - 100 / (1 + ag_m / np.maximum(al_m, 1e-12))
        rsi[~ok] = 50.0
        self.rsi_min = rsi                    # gleiche Laenge wie k1m.d[coin]


def spiele(r: dict, p: Regel, k1m, rsi: RSIStunde | None, ende_ms: int | None = None) -> dict:
    """Spielt EINE Runde mit Regel p nach. Rueckgabe: Ausstieg, Kurs-%, Zeit, Art."""
    coin = r["coin"]
    d = k1m.d[coin]
    t, O, H, L, C = d["t"], d["o"], d["h"], d["l"], d["c"]
    e = r["einstieg_preis"]
    i0 = int(np.searchsorted(t, r["kauf_ms"] - (r["kauf_ms"] % 60_000) + 60_000, side="left"))
    n = len(t) if ende_ms is None else int(np.searchsorted(t, ende_ms, side="left"))
    sl = p.sl_fn(r) if p.sl_fn else p.sl
    trail = p.trail_fn(r) if p.trail_fn else p.trail
    sl_lvl = e * (1 - sl / 100) if sl is not None else -1.0
    be_lvl = e * (1 + p.puffer / 100)
    hi = e
    hoch = 0.0
    R = rsi.rsi_min if (p.signal and rsi is not None) else None

    def linie(hi, hoch):
        lv, art = sl_lvl, "STOP_LOSS"
        if p.be_ab is not None and hoch >= p.be_ab and be_lvl > lv:
            lv, art = be_lvl, "BREAKEVEN_LOCK"
        if hoch >= p.start:
            f = leiter_faktor(hoch) if p.leiter else 1.0
            tl = hi * (1 - trail * f / 100)
            if tl > lv:
                lv, art = tl, "TRAILING_STOP"
        return lv, art

    lv, art = linie(hi, hoch)
    for j in range(i0, n):
        o, h, l, c = O[j], H[j], L[j], C[j]
        if o <= lv:
            return {"aus_ms": int(t[j]), "preis": o, "art": art, "offen": False, "mfe": hoch}
        if l <= lv:
            return {"aus_ms": int(t[j]) + 30_000, "preis": lv, "art": art, "offen": False, "mfe": hoch}
        if h > hi:
            hi = h
            hoch = (hi / e - 1) * 100
            lv, art = linie(hi, hoch)
            if c <= lv:
                return {"aus_ms": int(t[j]) + 60_000, "preis": c, "art": art, "offen": False, "mfe": hoch}
        if R is not None and R[j] > 80 and (c / e - 1) * 100 > 1.0:
            return {"aus_ms": int(t[j]) + 60_000, "preis": c, "art": "SIGNAL", "offen": False, "mfe": hoch}
    j = n - 1
    return {"aus_ms": int(t[j]) + 60_000, "preis": C[j], "art": "OFFEN_ENDE", "offen": True, "mfe": hoch}


def spiele_alle(R: list[dict], p: Regel, k1m, rsis: dict, bindung: bool = True, max_pos: int = 3) -> list[dict]:
    """Alle Runden chronologisch. Mit Kapitalbindung: Kauf entfaellt, solange die Muenze in der
    Nachspielung noch gehalten wird oder schon max_pos Positionen offen sind."""
    aus = []
    belegt: dict[str, int] = {}
    for r in sorted(R, key=lambda x: x["kauf_ms"]):
        if bindung:
            offen = [c for c, bis in belegt.items() if bis > r["kauf_ms"]]
            if r["coin"] in offen or len(offen) >= max_pos:
                continue
        z = spiele(r, p, k1m, rsis.get(r["coin"]))
        z["kurs_pct"] = (z["preis"] / r["einstieg_preis"] - 1) * 100
        z["runde"] = r
        belegt[r["coin"]] = z["aus_ms"]
        aus.append(z)
    return aus
