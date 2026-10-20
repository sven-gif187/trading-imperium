# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - H1-Batterie (T-016..T-024), 30.07.2026.
"""
H1 - Zeitreihen-Trend Long/Flat. Vorregistrierte Trials T-016..T-024.

REGISTERBINDUNG (v1.0 Paragraf 3 + v1.1 Paragraf 2):
  R1  Faber 2007:   Monatsschluss > 10-Monats-SMA -> long, sonst flat.
  R2  MOP 2012:     12-Monats-Rendite > 0 -> long, sonst flat (monatlich).
  R3  Donchian:     Schluss > Max(High der letzten 20 Tage, ohne heute)
                    -> Einstieg; Schluss < Min(Low der letzten 10 Tage,
                    ohne heute) -> Ausstieg.
  Parameter EXAKT {10M}, {12M}, {20/10}. Keine weiteren Werte.
  Signal am Tagesschluss UTC, Ausfuehrung am NAECHSTEN Tages-Open.
  Entwicklungszeitraum 2017-08-17..2023-12-31 (Signale; offene Runde am
  Periodenende wird zum letzten Open geschlossen, MIT Exit-Kosten -
  konservativ).
  Kosten je Runde (additiv, Prozentpunkte): K-MAKER 0,26 / K-BASIS 0,60 /
  K-KONSERVATIV 0,75. CONFIRMED entscheidet sich NUR unter K-BASIS.
  Segmente: S-A 2017-08..2019-12, S-B 2020-01..2021-12, S-C 2022-01..2023-12.

AUSWERTUNGSKONVENTIONEN (Implementierungsentscheidungen im Registerrahmen,
hier dokumentiert, KEINE Parametererweiterung):
  * EV je Entscheidung = mittlere Netto-Rundenrendite (Runde = Kauf->Verkauf).
    Bootstrap: Runden mit Zuruecklegen, 2000 Ziehungen, Seed 20260730.
    Jede Runde ist ein zusammenhaengender Kalendertagblock -> das ist der
    Block-Bootstrap ueber Kalendertage in natuerlicher Blockung.
  * p-Wert (einseitig) = Anteil der Bootstrap-Mittel <= 0. FDR (BH, q=0,10)
    ueber alle 13 Batterie-Trials in der Gesamtauswertung.
  * Placebo: 200 Long/Flat-Masken als 2-Zustands-Markov-Kette, kalibriert
    auf Long-Quote und mittlere Block-Laengen der echten Signalserie
    (Seed 20260730). Kriterium: echter EV je Runde (K-BASIS) > 95. Perzentil
    der Placebo-EVs. Placebo-Masken tragen dieselben Rundenkosten.
  * Lag-Robustheit: Ausfuehrung +1 Tag (t+2-Open). Look-ahead-Detektor.
  * MaxDD auf der taeglichen Netto-Equity (K-BASIS); Vergleich gegen
    Kaufen-und-Halten desselben Assets und Zeitraums (Register 0.3).
  * Urteil: CONFIRMED nur wenn (KI>0 unter K-BASIS) UND (Vorzeichen EV>0
    in allen verfuegbaren Segmenten) UND (Placebo geschlagen) UND
    (MaxDD < Halten). REJECTED wenn EV<=0 oder KI enthaelt 0 bei n>=12
    Runden oder Vorzeichenwechsel oder Placebo verfehlt. INCONCLUSIVE nur
    wenn EV>0, aber n<12 Runden (zu wenig Power fuer ein ehrliches
    REJECTED). Diese n-Schwelle ist Auswertungshygiene und lockert
    CONFIRMED nicht.

Reine Standardbibliothek. Reproduktion: python batterie_h1.py
"""
import csv
import math
import os
import random
import sys
from datetime import datetime, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATEN = os.path.join(BASIS, "daten", "klines_1d")

SEED = 20260730
BOOT = 2000
PLACEBO_N = 200
ENDE_MS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
SZENARIEN = [("K-MAKER", 0.26), ("K-BASIS", 0.60), ("K-KONSERVATIV", 0.75)]
K_BASIS = 0.60
SEGMENTE = [("S-A", "2017-08", "2019-12"), ("S-B", "2020-01", "2021-12"),
            ("S-C", "2022-01", "2023-12")]
SYMBOLE12 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT",
             "LINKUSDT", "DOTUSDT", "DOGEUSDT", "NEARUSDT", "UNIUSDT",
             "ATOMUSDT", "XRPUSDT"]


def lade(symbol):
    p = os.path.join(DATEN, f"{symbol}_1d.csv")
    out = []
    for r in csv.DictReader(open(p, encoding="utf-8")):
        t = int(r["zeit"])
        if t >= ENDE_MS:
            break
        out.append((t, float(r["open"]), float(r["high"]),
                    float(r["low"]), float(r["close"])))
    return out


def monat(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m")


# ---------------------------------------------------------------- Signale
def signal_r1(k):
    """Faber: Monatsende, Schluss > SMA der letzten 10 Monatsschluesse
    (inkl. aktuellem). Signalserie je Tag (Entscheid am Monatsletzten)."""
    letzte = {}
    for i, (t, o, h, l, c) in enumerate(k):
        letzte[monat(t)] = i
    mon = sorted(letzte)
    mclose = {m: k[letzte[m]][4] for m in mon}
    sig = [None] * len(k)
    stand = 0
    for j, m in enumerate(mon):
        if j >= 9:
            sma = sum(mclose[x] for x in mon[j - 9:j + 1]) / 10.0
            stand = 1 if mclose[m] > sma else 0
        # gilt ab dem Tag NACH dem Monatsletzten bis zum naechsten Entscheid
        start = letzte[m] + 1
        ende = letzte[mon[j + 1]] + 1 if j + 1 < len(mon) else len(k)
        for i in range(start, min(ende, len(k))):
            sig[i] = stand
    # sig[i] = gewuenschte Position, ENTSCHIEDEN am Vortag oder frueher
    return sig


def signal_r2(k):
    """MOP: Monatsende, 12-Monats-Rendite > 0 -> long."""
    letzte = {}
    for i, (t, o, h, l, c) in enumerate(k):
        letzte[monat(t)] = i
    mon = sorted(letzte)
    mclose = {m: k[letzte[m]][4] for m in mon}
    sig = [None] * len(k)
    stand = 0
    for j, m in enumerate(mon):
        if j >= 12:
            stand = 1 if mclose[m] > mclose[mon[j - 12]] else 0
        start = letzte[m] + 1
        ende = letzte[mon[j + 1]] + 1 if j + 1 < len(mon) else len(k)
        for i in range(start, min(ende, len(k))):
            sig[i] = stand
    return sig


def signal_r3(k):
    """Donchian 20/10: Entscheid am Tagesschluss t, gilt ab t+1."""
    sig = [None] * len(k)
    stand = 0
    for i in range(len(k)):
        if i >= 20:
            hi20 = max(k[x][2] for x in range(i - 20, i))
            lo10 = min(k[x][3] for x in range(i - 10, i))
            c = k[i][4]
            if stand == 0 and c > hi20:
                stand = 1
            elif stand == 1 and c < lo10:
                stand = 0
        if i + 1 < len(k):
            sig[i + 1] = stand
    return sig


# ---------------------------------------------------------------- Runden
def runden_aus_signal(k, sig, lag=0):
    """Position am Tag i = sig[i-lag]. Ein-/Ausstieg zum Open des Tages,
    an dem die neue Position erstmals gilt. Gibt Liste (entry_i, exit_i,
    entry_open, exit_open, entry_ms)."""
    runden = []
    pos = 0
    e_i = None
    for i in range(len(k)):
        s = sig[i - lag] if i - lag >= 0 else None
        if s is None:
            s = 0
        if pos == 0 and s == 1:
            pos, e_i = 1, i
        elif pos == 1 and s == 0:
            runden.append((e_i, i, k[e_i][1], k[i][1], k[e_i][0]))
            pos = 0
    if pos == 1:
        i = len(k) - 1
        runden.append((e_i, i, k[e_i][1], k[i][1], k[e_i][0]))  # Zwangsexit
    return runden


def netto_evs(runden, c_pct):
    return [(x[3] / x[2] - 1) * 100 - c_pct for x in runden]


def equity_und_dd(k, sig, c_pct, lag=0):
    """Taegliche Netto-Equity; MaxDD in %."""
    eq = 1.0
    peak = 1.0
    dd = 0.0
    pos = 0
    for i in range(len(k)):
        s = sig[i - lag] if i - lag >= 0 else None
        if s is None:
            s = 0
        t, o, h, l, c = k[i]
        if pos == 0 and s == 1:
            eq *= (c / o) * (1 - c_pct / 200.0)   # halbe Rundenkosten
            pos = 1
        elif pos == 1 and s == 0:
            eq *= (o / k[i - 1][4]) * (1 - c_pct / 200.0)
            pos = 0
        elif pos == 1:
            eq *= c / k[i - 1][4]
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak)
    return eq, dd * 100


def halten_dd(k):
    peak = dd = 0.0
    peak = k[0][4]
    for _t, _o, _h, _l, c in k:
        peak = max(peak, c)
        dd = max(dd, (peak - c) / peak)
    return (k[-1][4] / k[0][4] - 1) * 100, dd * 100


def bootstrap_ki(evs, rnd):
    if not evs:
        return 0.0, 0.0, 1.0
    ms = []
    n = len(evs)
    for _ in range(BOOT):
        ms.append(sum(evs[rnd.randrange(n)] for _ in range(n)) / n)
    ms.sort()
    lo = ms[int(0.025 * BOOT)]
    hi = ms[int(0.975 * BOOT) - 1]
    p = sum(1 for m in ms if m <= 0) / BOOT
    return lo, hi, p


def blocklaengen(sig):
    """(long_quote, mittlere Long-Blocklaenge, mittlere Flat-Blocklaenge)"""
    s = [x if x is not None else 0 for x in sig]
    laengen = {0: [], 1: []}
    cur, n = s[0], 1
    for x in s[1:]:
        if x == cur:
            n += 1
        else:
            laengen[cur].append(n)
            cur, n = x, 1
    laengen[cur].append(n)
    lq = sum(s) / len(s)
    ml = sum(laengen[1]) / len(laengen[1]) if laengen[1] else 1.0
    mf = sum(laengen[0]) / len(laengen[0]) if laengen[0] else 1.0
    return lq, ml, mf


def placebo_evs(k, sig, c_pct, rnd):
    """200 Markov-Masken mit gleicher mittlerer Block-Laenge; EV je Runde."""
    _lq, ml, mf = blocklaengen(sig)
    p_ll = 1.0 - 1.0 / max(ml, 1.0001)     # bleib long
    p_ff = 1.0 - 1.0 / max(mf, 1.0001)     # bleib flat
    out = []
    for _ in range(PLACEBO_N):
        m = [None] * len(sig)
        stand = 1 if rnd.random() < ml / (ml + mf) else 0
        for i in range(len(sig)):
            if sig[i] is None:
                m[i] = None
                continue
            m[i] = stand
            if stand == 1:
                if rnd.random() > p_ll:
                    stand = 0
            else:
                if rnd.random() > p_ff:
                    stand = 1
        r = runden_aus_signal(k, m)
        evs = netto_evs(r, c_pct)
        if evs:
            out.append(sum(evs) / len(evs))
    out.sort()
    return out


def perz(xs, q):
    if not xs:
        return 0.0
    i = min(int(q * len(xs)), len(xs) - 1)
    return xs[i]


# ---------------------------------------------------------------- Trial
def trial(nr, name, k_map, regel_fn, symbole):
    """Ein Trial: symbole=[s] Einzelasset oder Liste (Portfolio, Runden
    gepoolt). Rueckgabe: (p_wert_K_BASIS, urteil, zeilen)."""
    rnd = random.Random(SEED)
    alle_runden = []
    sigs = {}
    for s in symbole:
        k = k_map[s]
        sig = regel_fn(k)
        sigs[s] = sig
        for r in runden_aus_signal(k, sig):
            alle_runden.append((s, r))
    n = len(alle_runden)
    Z = [f"\n  {nr}  {name}   Runden={n}"]
    if n == 0:
        Z.append("    KEINE RUNDEN -> INCONCLUSIVE")
        return 1.0, "INCONCLUSIVE", Z

    erg = {}
    for bez, c in SZENARIEN:
        evs = netto_evs([r for _s, r in alle_runden], c)
        lo, hi, p = bootstrap_ki(evs, random.Random(SEED))
        erg[bez] = (sum(evs) / n, lo, hi, p)
    Z.append(f"    {'Szenario':<14s} {'EV/Runde':>10s} {'95%-KI':>22s} {'p(einseitig)':>13s}")
    for bez, _c in SZENARIEN:
        ev, lo, hi, p = erg[bez]
        Z.append(f"    {bez:<14s} {ev:+9.3f}% [{lo:+8.3f} ; {hi:+8.3f}]% {p:13.4f}")

    # Segmente (K-BASIS)
    seg_ev = {}
    for bez, von, bis in SEGMENTE:
        rr = [r for _s, r in alle_runden if von <= monat(r[4]) <= bis]
        if rr:
            evs = netto_evs(rr, K_BASIS)
            seg_ev[bez] = (sum(evs) / len(evs), len(evs))
    Z.append("    Segmente (K-BASIS): " + "  ".join(
        f"{b}: {v[0]:+.3f}% (n={v[1]})" for b, v in seg_ev.items()) or "keine")
    stabil = all(v[0] > 0 for v in seg_ev.values()) if seg_ev else False

    # Placebo (K-BASIS) - fuer Portfolio: je Coin eigene Maske, gepoolt
    pls = []
    for _i in range(1):
        pass
    if len(symbole) == 1:
        pls = placebo_evs(k_map[symbole[0]], sigs[symbole[0]], K_BASIS, rnd)
    else:
        # Portfolio: 200 Ziehungen, je Ziehung Masken fuer alle Coins, EV gepoolt
        for _z in range(PLACEBO_N):
            pool = []
            for s in symbole:
                _lq, ml, mf = blocklaengen(sigs[s])
                p_ll = 1.0 - 1.0 / max(ml, 1.0001)
                p_ff = 1.0 - 1.0 / max(mf, 1.0001)
                k = k_map[s]
                stand = 1 if rnd.random() < ml / (ml + mf) else 0
                m = []
                for i in range(len(sigs[s])):
                    if sigs[s][i] is None:
                        m.append(None)
                        continue
                    m.append(stand)
                    if stand == 1 and rnd.random() > p_ll:
                        stand = 0
                    elif stand == 0 and rnd.random() > p_ff:
                        stand = 1
                pool.extend(netto_evs(runden_aus_signal(k, m), K_BASIS))
            if pool:
                pls.append(sum(pool) / len(pool))
        pls.sort()
    p95 = perz(pls, 0.95)
    ev_basis = erg["K-BASIS"][0]
    plc_ok = ev_basis > p95
    rang = sum(1 for x in pls if x < ev_basis) / len(pls) * 100 if pls else 0
    Z.append(f"    Placebo (200 Masken, K-BASIS): 95.P = {p95:+.3f}%  "
             f"echt = {ev_basis:+.3f}%  Rang {rang:.0f}. Perzentil  "
             f"-> {'GESCHLAGEN' if plc_ok else 'NICHT geschlagen'}")

    # Lag +1 (K-BASIS)
    lag_pool = []
    for s in symbole:
        lag_pool.extend(netto_evs(runden_aus_signal(k_map[s], sigs[s], lag=1),
                                  K_BASIS))
    ev_lag = sum(lag_pool) / len(lag_pool) if lag_pool else 0.0
    Z.append(f"    Lag+1 (K-BASIS): EV/Runde = {ev_lag:+.3f}%  "
             f"(Kollaps-Verdacht wenn Vorzeichen kippt und |Delta| gross)")

    # MaxDD (K-BASIS) vs Halten - fuer Portfolio: gleichgew. Mittel der DDs
    dds, hdds, hrets = [], [], []
    for s in symbole:
        _eq, dd = equity_und_dd(k_map[s], sigs[s], K_BASIS)
        hret, hdd = halten_dd(k_map[s])
        dds.append(dd)
        hdds.append(hdd)
        hrets.append(hret)
    dd_s = sum(dds) / len(dds)
    dd_h = sum(hdds) / len(hdds)
    Z.append(f"    MaxDD Regel {dd_s:.1f}%  vs Halten {dd_h:.1f}%  "
             f"({'kleiner' if dd_s < dd_h else 'NICHT kleiner'}) | "
             f"Halten-Gesamtrendite {sum(hrets)/len(hrets):+.0f}%")

    # Urteil
    ev, lo, hi, p = erg["K-BASIS"]
    if ev > 0 and lo > 0 and stabil and plc_ok and dd_s < dd_h:
        urteil = "CONFIRMED*"      # * vorbehaltlich FDR ueber alle 13 Trials
    elif ev > 0 and n < 12:
        urteil = "INCONCLUSIVE (n<12)"
    else:
        grund = []
        if ev <= 0:
            grund.append("EV<=0")
        if lo <= 0:
            grund.append("KI enthaelt 0")
        if not stabil:
            grund.append("Segment-Vorzeichen")
        if not plc_ok:
            grund.append("Placebo")
        if dd_s >= dd_h:
            grund.append("MaxDD")
        urteil = "REJECTED (" + ", ".join(grund) + ")"
    Z.append(f"    URTEIL {nr}: {urteil}")
    return p, urteil, Z


def main():
    print("=" * 100)
    print(" H1-BATTERIE  T-016..T-024  |  Register v1.0/v1.1  |  Seed", SEED)
    print(" Entwicklungszeitraum 2017-08-17..2023-12-31 | Ausfuehrung next-open")
    print(" CONFIRMED* = alle Kriterien unter K-BASIS erfuellt, FDR folgt in der")
    print(" Gesamtauswertung ueber alle 13 Batterie-Trials.")
    print("=" * 100)
    k_map = {s: lade(s) for s in SYMBOLE12}
    for s in SYMBOLE12:
        k = k_map[s]
        print(f"  {s:<10s} {len(k)} Tage bis {monat(k[-1][0])}")

    regeln = [("R1 Faber 10M-SMA", signal_r1),
              ("R2 MOP 12M-Momentum", signal_r2),
              ("R3 Donchian 20/10", signal_r3)]
    trials = []
    nr = 16
    for rname, fn in regeln:
        for s in ("BTCUSDT", "ETHUSDT"):
            trials.append((f"T-{nr:03d}", f"{rname} | {s}", fn, [s]))
            nr += 1
    for rname, fn in regeln:
        trials.append((f"T-{nr:03d}", f"{rname} | 12er-Portfolio (ab Listing)",
                       fn, SYMBOLE12))
        nr += 1

    ps = []
    for tnr, name, fn, symbole in trials:
        p, urteil, zeilen = trial(tnr, name, k_map, fn, symbole)
        ps.append((tnr, name, p, urteil))
        for z in zeilen:
            print(z)
        sys.stdout.flush()

    print("\n" + "=" * 100)
    print(" p-WERTE FUER DIE GEMEINSAME FDR (mit H2 in der Gesamtauswertung)")
    print("=" * 100)
    for tnr, name, p, urteil in ps:
        print(f"    {tnr}  p={p:.4f}  {urteil:<28s} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
