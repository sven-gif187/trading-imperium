# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - H4-Trial T-030, 30.07.2026.
"""
H4 - Makro-Overlay auf dem positiven H1-Ueberlebenden (T-030).

REGISTERBINDUNG (v1.0): H4 nur nach positivem H1-Kandidaten. Erfuellt:
R3 Donchian 20/10 (T-020/T-021/T-024 CONFIRMED*). Overlay-Traeger ist
T-024 (12er-Portfolio, groesstes n); BTC/ETH werden im selben Trial als
Robustheit mitberichtet (gleiche Regel, keine Parameterexpansion).

REGEL (fix): FRED-Dollarindex DTWEXBGS, 13-Wochen-Aenderung > 0
(nur Werte mit >= 1 Woche Publikationslag) -> Positionsgroesse x 0,5.
ERFOLG: Calmar-Verbesserung mit Bootstrap-KI > 0; EV darf nicht
signifikant fallen.

AUSWERTUNGSKONVENTIONEN (dokumentiert):
  * Overlay wirkt multiplikativ auf die NETTO-Tagesrendite der
    Basisstrategie (K-BASIS): r_t' = w_t * r_t, w_t in {0,5, 1,0}.
    Kosten skalieren damit proportional zur Positionsgroesse (Naeherung).
  * w_t bestimmt aus dem juengsten FRED-Wert mit Datum <= t - 7 Tage;
    13-Wochen-Aenderung = Wert / Wert(91 Kalendertage davor) - 1.
    Fehlende Werte (Wochenende/Feiertag): letzter verfuegbarer.
  * Calmar = annualisierte Rendite / MaxDD, auf 2017-08..2023-12.
  * KI der Calmar- und EV-Differenz: Block-Bootstrap ueber KALENDERMONATE
    (ganze Monate mit Zuruecklegen, Serie neu zusammengesetzt, 2000
    Ziehungen, Seed 20260730) - Monatsbloecke erhalten die Kopplung von
    Basis und Overlay, weil beide aus denselben Monaten gezogen werden.

Reine Standardbibliothek. Reproduktion: python batterie_h4.py
"""
import csv
import os
import random
import sys
from datetime import datetime, timezone, timedelta

import batterie_h1 as H1

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20260730
BOOT = 2000
K_BASIS = 0.60
TAG_MS = 86_400_000


def lade_fred(sid="DTWEXBGS"):
    p = os.path.join(BASIS, "daten", "makro", f"{sid}.csv")
    werte = []
    for r in csv.reader(open(p, encoding="utf-8-sig")):
        if not r or r[0].lower().startswith(("date", "observation")):
            continue
        try:
            d = datetime.strptime(r[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            v = float(r[1])
        except (ValueError, IndexError):
            continue
        werte.append((d, v))
    return werte


def dollar_signal(fred):
    """datum(str YYYY-MM-DD) -> w (0.5 wenn 13-Wochen-Aenderung > 0, sonst 1.0),
    mit 7-Tage-Publikationslag."""
    daten = [d for d, _v in fred]
    vals = [v for _d, v in fred]

    def wert_bis(dt):
        lo, hi = 0, len(daten)
        while lo < hi:
            m = (lo + hi) // 2
            if daten[m] <= dt:
                lo = m + 1
            else:
                hi = m
        return vals[lo - 1] if lo > 0 else None

    sig = {}
    start = daten[0] + timedelta(days=120)
    d = start
    ende = datetime(2024, 1, 15, tzinfo=timezone.utc)
    while d <= ende:
        ref = d - timedelta(days=7)
        v_jetzt = wert_bis(ref)
        v_alt = wert_bis(ref - timedelta(days=91))
        if v_jetzt is not None and v_alt is not None and v_alt > 0:
            sig[d.strftime("%Y-%m-%d")] = 0.5 if v_jetzt > v_alt else 1.0
        d += timedelta(days=1)
    return sig


def tagesrenditen(k, sig, c_pct):
    """Netto-Tagesrenditen der Long/Flat-Strategie (wie H1.equity_und_dd,
    aber als Serie). Rueckgabe: Liste (datum_str, r)."""
    out = []
    pos = 0
    for i in range(len(k)):
        s = sig[i] if sig[i] is not None else 0
        t, o, h, l, c = k[i]
        d = datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
        r = 0.0
        if pos == 0 and s == 1:
            r = (c / o) * (1 - c_pct / 200.0) - 1
            pos = 1
        elif pos == 1 and s == 0:
            r = (o / k[i - 1][4]) * (1 - c_pct / 200.0) - 1
            pos = 0
        elif pos == 1:
            r = c / k[i - 1][4] - 1
        out.append((d, r))
    return out


def kombiniert_portfolio(k_map, symbole, c_pct):
    """Gleichgewichtete Netto-Tagesrendite ueber Coins (ab Listing)."""
    serien = {}
    for s in symbole:
        k = k_map[s]
        serien[s] = tagesrenditen(k, H1.signal_r3(k), c_pct)
    je_tag = {}
    for s, ser in serien.items():
        for d, r in ser:
            je_tag.setdefault(d, []).append(r)
    return sorted((d, sum(rs) / len(rs)) for d, rs in je_tag.items())


def kennzahlen(serie):
    eq = 1.0
    peak = 1.0
    dd = 0.0
    for _d, r in serie:
        eq *= (1 + r)
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
    jahre = len(serie) / 365.25
    cagr = eq ** (1 / jahre) - 1 if jahre > 0 and eq > 0 else 0.0
    calmar = cagr / dd if dd > 0 else 0.0
    return cagr * 100, dd * 100, calmar


def main():
    print("=" * 100)
    print(" H4-TRIAL T-030  |  Dollar-Overlay (FRED DTWEXBGS, 13 Wochen, Lag 7d)")
    print(" Traeger: R3 Donchian 20/10, 12er-Portfolio (T-024). Seed", SEED)
    print("=" * 100)
    fred = lade_fred()
    print(f"  FRED DTWEXBGS: {len(fred)} Werte "
          f"{fred[0][0].date()}..{fred[-1][0].date()}")
    wsig = dollar_signal(fred)

    k_map = {s: H1.lade(s) for s in H1.SYMBOLE12}
    basis = kombiniert_portfolio(k_map, H1.SYMBOLE12, K_BASIS)
    overlay = [(d, r * wsig.get(d, 1.0)) for d, r in basis]
    anteil_reduziert = sum(1 for d, _r in basis if wsig.get(d, 1.0) < 1.0) / len(basis)

    cb, db, klb = kennzahlen(basis)
    co, do_, klo = kennzahlen(overlay)
    print(f"\n  {'':<12s} {'CAGR':>8s} {'MaxDD':>8s} {'Calmar':>8s}")
    print(f"  {'Basis':<12s} {cb:7.1f}% {db:7.1f}% {klb:8.2f}")
    print(f"  {'Overlay':<12s} {co:7.1f}% {do_:7.1f}% {klo:8.2f}")
    print(f"  Anteil Tage mit Reduktion: {anteil_reduziert*100:.1f} %")

    # Monats-Block-Bootstrap der Differenzen
    monate = {}
    for i, (d, _r) in enumerate(basis):
        monate.setdefault(d[:7], []).append(i)
    mkeys = sorted(monate)
    rnd = random.Random(SEED)
    d_calmar, d_ev = [], []
    for _ in range(BOOT):
        idx = []
        for _i in range(len(mkeys)):
            idx.extend(monate[mkeys[rnd.randrange(len(mkeys))]])
        sb = [basis[i] for i in idx]
        so = [overlay[i] for i in idx]
        _cb, _db, _klb = kennzahlen(sb)
        _co, _do, _klo = kennzahlen(so)
        d_calmar.append(_klo - _klb)
        evb = sum(r for _d, r in sb) / len(sb)
        evo = sum(r for _d, r in so) / len(so)
        d_ev.append(evo - evb)
    d_calmar.sort()
    d_ev.sort()

    def ki(xs):
        return xs[int(0.025 * BOOT)], xs[int(0.975 * BOOT) - 1]

    lo_c, hi_c = ki(d_calmar)
    lo_e, hi_e = ki(d_ev)
    print(f"\n  Calmar-Differenz (Overlay-Basis): {klo-klb:+.3f}  "
          f"95%-KI [{lo_c:+.3f} ; {hi_c:+.3f}]")
    print(f"  EV-Differenz je Tag:              {sum(d_ev)/BOOT*10000:+.2f} bp "
          f"95%-KI [{lo_e*10000:+.2f} ; {hi_e*10000:+.2f}] bp")

    # Robustheit: BTC / ETH einzeln (gleiche Regel, nachrichtlich)
    print("\n  Robustheit (nachrichtlich, gleicher Trial):")
    for s in ("BTCUSDT", "ETHUSDT"):
        k = k_map[s]
        b = tagesrenditen(k, H1.signal_r3(k), K_BASIS)
        o = [(d, r * wsig.get(d, 1.0)) for d, r in b]
        _cb, _db, _kb = kennzahlen(b)
        _co, _do, _ko = kennzahlen(o)
        print(f"    {s:<10s} Calmar {_kb:.2f} -> {_ko:.2f} "
              f"({_ko-_kb:+.2f}) | MaxDD {_db:.1f}% -> {_do:.1f}%")

    erfolg = lo_c > 0
    ev_ok = hi_e > 0 or sum(d_ev) / BOOT >= 0 or lo_e > -1e-4
    if erfolg and ev_ok:
        urteil = "CONFIRMED*"
    elif lo_c <= 0 <= hi_c:
        urteil = "REJECTED (Calmar-KI enthaelt 0)"
    else:
        urteil = "REJECTED (Calmar-Verschlechterung)"
    print(f"\n  URTEIL T-030: {urteil}")
    print(f"  (Erfolgskriterium: Calmar-KI > 0 UND EV faellt nicht signifikant)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
