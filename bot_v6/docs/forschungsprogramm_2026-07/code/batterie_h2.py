# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - H2-Batterie (T-025..T-028), 30.07.2026.
"""
H2 - Funding-Extreme als Richtungssignal. Trials T-025..T-028.

REGISTERBINDUNG (v1.0 Paragraf 3, Schwellen FIX):
  E-neg: Funding <= 0 in 3 aufeinanderfolgenden 8h-Intervallen
         -> Long-Ereignis, Halten 7 Tage.
  E-pos: Funding >= +0,05 %/8h in 3 aufeinanderfolgenden Intervallen
         -> Kein-Long-/Warn-Ereignis, Horizont 7 Tage.
  Assets BTC, ETH. Entwicklungszeitraum bis 2023-12-31.
  Event-Study Forward 1/3/7/14 d gegen volatilitaets-gematchtes Placebo
  (gleiche Vol-Dezile, zufaellige Tage, 40 Ziehungen) + Bootstrap-KI.
  Ereigniszahl < 30 -> INCONCLUSIVE. FDR gemeinsam mit H1 (q=0,10).
  Kosten (v1.1): CONFIRMED nur unter K-BASIS 0,60 %; K-MAKER 0,26 %
  wird mitberichtet (Auflage des Eigentuemers).

AUSWERTUNGSKONVENTIONEN (dokumentiert, keine Parametererweiterung):
  * Trigger = 3. konsekutives Extrem-Intervall. DE-OVERLAP: nach einem
    Trigger sperrt derselbe Ereignistyp 14 Tage (laengster Messhorizont) -
    sonst zaehlte derselbe Zustand mehrfach.
  * Ausfuehrung: naechster Tages-Open (00:00 UTC) nach dem Trigger.
  * Forward-Rendite h Tage: Open_{t0} -> Close_{t0+h-1}.
  * Vol-Matching: Dezile der 20-Tage-Realized-Vol (Tagesrenditen) im
    Entwicklungszeitraum; Placebo zieht je Ziehung fuer jedes Event einen
    Zufallstag aus demselben Dezil (Seed 20260730, 40 Ziehungen).
  * Primaerkennzahl fuer Urteil: 7d-Forward. E-neg: netto (7d - c) mit
    Bootstrap-KI > 0 UND Brutto-Forward > 95. Perzentil des Placebos.
    E-pos: Information = Forward SCHLECHTER als Placebo (5. Perzentil,
    einseitig negativ); kein Kostenabzug (Vermeidungssignal, kein Trade).
  * Segmente S-B (2020-01..2021-12) / S-C (2022-01..2023-12); S-A entfaellt
    (Funding beginnt 2019-09/11) - im Register antizipiert.
  * p-Wert fuer FDR: E-neg = Anteil Bootstrap-Mittel(netto) <= 0.
    E-pos = Placebo-Rang-p (Anteil Placebo-Mittel <= Event-Mittel).

Reine Standardbibliothek. Reproduktion: python batterie_h2.py
"""
import bisect
import csv
import math
import os
import random
import sys
from datetime import datetime, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SEED = 20260730
BOOT = 2000
ZIEH = 40
SPERRE_T = 14
HORIZONTE = (1, 3, 7, 14)
ENDE_MS = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
K_MAKER, K_BASIS = 0.26, 0.60
TAG_MS = 86_400_000
SCHWELLE_POS = 0.0005          # +0,05 % je 8h


def lade_kerzen(symbol):
    p = os.path.join(BASIS, "daten", "klines_1d", f"{symbol}_1d.csv")
    out = []
    for r in csv.DictReader(open(p, encoding="utf-8")):
        t = int(r["zeit"])
        if t >= ENDE_MS + 20 * TAG_MS:   # 14d-Forward am Jahresende erlaubt
            break
        out.append((t, float(r["open"]), float(r["high"]),
                    float(r["low"]), float(r["close"])))
    return out


def lade_funding(symbol):
    p = os.path.join(BASIS, "daten", "funding", f"{symbol}_funding8h.csv")
    out = []
    for r in csv.DictReader(open(p, encoding="utf-8")):
        t = int(r["fundingTime"])
        if t >= ENDE_MS:
            break
        out.append((t, float(r["fundingRate"])))
    return out


def monat(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m")


def events_finden(fund, typ):
    """Trigger-Zeitpunkte (ms) mit 14-Tage-De-Overlap je Typ."""
    ev = []
    sperre_bis = 0
    lauf = 0
    for t, r in fund:
        ok = (r <= 0.0) if typ == "neg" else (r >= SCHWELLE_POS)
        lauf = lauf + 1 if ok else 0
        if lauf >= 3 and t >= sperre_bis:
            ev.append(t)
            sperre_bis = t + SPERRE_T * TAG_MS
    return ev


def vol_dezile(k):
    """Index i -> Dezil der 20d-Realized-Vol; und Dezil -> [Indices]."""
    rets = [0.0] * len(k)
    for i in range(1, len(k)):
        rets[i] = k[i][4] / k[i - 1][4] - 1
    vols = [None] * len(k)
    for i in range(20, len(k)):
        w = rets[i - 19:i + 1]
        m = sum(w) / 20
        vols[i] = math.sqrt(sum((x - m) ** 2 for x in w) / 20)
    gueltig = sorted((v, i) for i, v in enumerate(vols)
                     if v is not None and k[i][0] < ENDE_MS - 15 * TAG_MS)
    dez_von_i = {}
    i_von_dez = {d: [] for d in range(10)}
    n = len(gueltig)
    for rang, (_v, i) in enumerate(gueltig):
        d = min(9, rang * 10 // n)
        dez_von_i[i] = d
        i_von_dez[d].append(i)
    return dez_von_i, i_von_dez


def forward(k, i0, h):
    """Open_{i0} -> Close_{i0+h-1}, in %."""
    j = i0 + h - 1
    if i0 >= len(k) or j >= len(k):
        return None
    return (k[j][4] / k[i0][1] - 1) * 100


def bootstrap(xs, rnd):
    n = len(xs)
    ms = []
    for _ in range(BOOT):
        ms.append(sum(xs[rnd.randrange(n)] for _ in range(n)) / n)
    ms.sort()
    return (ms[int(0.025 * BOOT)], ms[int(0.975 * BOOT) - 1],
            sum(1 for m in ms if m <= 0) / BOOT)


def trial(nr, symbol, typ):
    rnd = random.Random(SEED)
    k = lade_kerzen(symbol)
    zeiten = [x[0] for x in k]
    fund = lade_funding(symbol)
    ev_ms = events_finden(fund, typ)
    # Ausfuehrungsindex: naechster Tages-Open nach Trigger
    ev_idx = []
    for t in ev_ms:
        i = bisect.bisect_right(zeiten, t)
        if i < len(k) and k[i][0] < ENDE_MS:
            ev_idx.append(i)
    n = len(ev_idx)
    bez = "E-neg (Long nach Kapitulations-Funding)" if typ == "neg" \
        else "E-pos (Warnsignal bei Ueberhitzung)"
    Z = [f"\n  {nr}  {bez} | {symbol}   Events={n} (nach 14d-De-Overlap)"]
    if n == 0:
        Z.append("    KEINE EVENTS -> INCONCLUSIVE")
        return 1.0, "INCONCLUSIVE", Z

    dez_von_i, i_von_dez = vol_dezile(k)

    # Forward-Tabelle + Placebo je Horizont
    Z.append(f"    {'Horizont':>8s} {'Event-Mittel':>13s} {'Placebo-Mittel':>15s} "
             f"{'Plc 5.P':>9s} {'Plc 95.P':>9s}")
    plc7 = []
    ev7 = None
    for h in HORIZONTE:
        evs = [f for i in ev_idx if (f := forward(k, i, h)) is not None]
        if not evs:
            continue
        plc_mittel = []
        for _z in range(ZIEH):
            zieh = []
            for i in ev_idx:
                d = dez_von_i.get(i)
                if d is None:
                    d = rnd.randrange(10)
                kand = i_von_dez[d]
                j = kand[rnd.randrange(len(kand))]
                f = forward(k, j, h)
                if f is not None:
                    zieh.append(f)
            if zieh:
                plc_mittel.append(sum(zieh) / len(zieh))
        plc_mittel.sort()
        em = sum(evs) / len(evs)
        p5 = plc_mittel[max(0, int(0.05 * len(plc_mittel)))]
        p95 = plc_mittel[min(len(plc_mittel) - 1, int(0.95 * len(plc_mittel)))]
        Z.append(f"    {h:7d}d {em:+12.3f}% {sum(plc_mittel)/len(plc_mittel):+14.3f}% "
                 f"{p5:+8.3f}% {p95:+8.3f}%")
        if h == 7:
            ev7, plc7 = evs, plc_mittel

    # Segmente (7d brutto)
    seg = {}
    for b, von, bis in (("S-B", "2020-01", "2021-12"), ("S-C", "2022-01", "2023-12")):
        xs = [f for i in ev_idx if von <= monat(k[i][0]) <= bis
              and (f := forward(k, i, 7)) is not None]
        if xs:
            seg[b] = (sum(xs) / len(xs), len(xs))
    Z.append("    Segmente (7d brutto): " + "  ".join(
        f"{b}: {v[0]:+.3f}% (n={v[1]})" for b, v in seg.items()))

    if typ == "neg":
        netto_b = [x - K_BASIS for x in ev7]
        netto_m = [x - K_MAKER for x in ev7]
        lo_b, hi_b, p_b = bootstrap(netto_b, random.Random(SEED))
        lo_m, hi_m, p_m = bootstrap(netto_m, random.Random(SEED))
        Z.append(f"    7d NETTO K-BASIS : EV {sum(netto_b)/n:+.3f}%  "
                 f"KI [{lo_b:+.3f} ; {hi_b:+.3f}]  p={p_b:.4f}")
        Z.append(f"    7d NETTO K-MAKER : EV {sum(netto_m)/n:+.3f}%  "
                 f"KI [{lo_m:+.3f} ; {hi_m:+.3f}]  p={p_m:.4f}")
        em7 = sum(ev7) / len(ev7)
        p95 = plc7[min(len(plc7) - 1, int(0.95 * len(plc7)))]
        plc_ok = em7 > p95
        rang = sum(1 for x in plc7 if x < em7) / len(plc7) * 100
        Z.append(f"    Placebo 7d: echt {em7:+.3f}% vs 95.P {p95:+.3f}%  "
                 f"Rang {rang:.0f}. Perzentil -> "
                 f"{'GESCHLAGEN' if plc_ok else 'NICHT geschlagen'}")
        stabil = all(v[0] > 0 for v in seg.values()) if seg else False
        if n < 30:
            urteil = "INCONCLUSIVE (n<30)"
        elif sum(netto_b) / n > 0 and lo_b > 0 and plc_ok and stabil:
            urteil = "CONFIRMED*"
        else:
            grund = []
            if sum(netto_b) / n <= 0:
                grund.append("EV<=0")
            elif lo_b <= 0:
                grund.append("KI enthaelt 0")
            if not plc_ok:
                grund.append("Placebo")
            if not stabil:
                grund.append("Segment-Vorzeichen")
            urteil = "REJECTED (" + ", ".join(grund) + ")"
        p_fdr = p_b
    else:
        # E-pos: Information, wenn Forward SCHLECHTER als Placebo
        em7 = sum(ev7) / len(ev7)
        p5 = plc7[max(0, int(0.05 * len(plc7)))]
        rang_p = sum(1 for x in plc7 if x <= em7) / len(plc7)
        Z.append(f"    Placebo 7d: echt {em7:+.3f}% vs 5.P {p5:+.3f}%  "
                 f"Rang-p (einseitig, schlechter=Info) = {rang_p:.3f}")
        stabil = all(v[0] < 0 for v in seg.values()) if seg else False
        if n < 30:
            urteil = "INCONCLUSIVE (n<30)"
        elif em7 < p5 and stabil:
            urteil = "CONFIRMED*"
        else:
            grund = []
            if em7 >= p5:
                grund.append("nicht unter Placebo-5.P")
            if not stabil:
                grund.append("Segment-Vorzeichen")
            urteil = "REJECTED (" + ", ".join(grund) + ")"
        p_fdr = rang_p
    Z.append(f"    URTEIL {nr}: {urteil}")
    return p_fdr, urteil, Z


def main():
    print("=" * 100)
    print(" H2-BATTERIE  T-025..T-028  |  Register v1.0/v1.1  |  Seed", SEED)
    print(" Funding-Historie ab 2019-09/11; Entwicklungszeitraum bis 2023-12-31")
    print("=" * 100)
    ps = []
    nr = 25
    for typ in ("neg", "pos"):
        for s in ("BTCUSDT", "ETHUSDT"):
            tnr = f"T-{nr:03d}"
            p, urteil, Z = trial(tnr, s, typ)
            ps.append((tnr, f"{typ} {s}", p, urteil))
            for z in Z:
                print(z)
            sys.stdout.flush()
            nr += 1
    print("\n" + "=" * 100)
    print(" p-WERTE FUER DIE GEMEINSAME FDR")
    print("=" * 100)
    for tnr, name, p, urteil in ps:
        print(f"    {tnr}  p={p:.4f}  {urteil:<24s} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
