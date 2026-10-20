# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - Neubewertung unter Register v1.2, 30.07.2026.
"""
NEUBEWERTUNG der H1-Trials unter dem verschaerften Segment-Kriterium (v1.2).
KEIN NEUER TRIAL: identische Signale, identische Runden, identische Kosten
wie in batterie_h1.py. Geaendert wird ausschliesslich die Urteilsregel.

AUFTRAG (Eigentuemer, 30.07.2026):
  "EV je Runde muss in JEDEM Segment (S-A/S-B/S-C) die jeweilige
   Kostenschwelle K-BASIS ueberschreiten, nicht nur positiv sein."

MEHRDEUTIGKEIT - MUSS VOR DEM URTEIL AUFGELOEST WERDEN
------------------------------------------------------
Die in batterie_h1_out.txt berichteten Segmentwerte sind BEREITS NETTO,
also nach Abzug von K-BASIS = 0,60 %:
    netto_evs(runden, c) = (exit/entry - 1)*100 - c        (batterie_h1.py)
Damit gibt es zwei Lesarten der Verschaerfung:

  L1 "Netto ueber Null"      netto_EV > 0      <=> brutto > 0,60 %
     Das ist exakt das ALTE Kriterium (Vorzeichen). Keine Verschaerfung.

  L2 "Netto ueber K-BASIS"   netto_EV > 0,60 % <=> brutto > 1,20 %
     Verlangt einen Sicherheitsaufschlag in Hoehe der Kosten: die Runde
     muss ihre Kosten ZWEIMAL verdienen. Das ist eine echte Verschaerfung
     und entspricht der Rechnung des Eigentuemers, der die berichteten
     Werte 0,504 % / 0,157 % direkt gegen 0,60 % gestellt hat.

Dieses Skript rechnet BEIDE und weist aus, wo sie sich unterscheiden.
Massgeblich fuer das v1.2-Urteil ist L2 (Lesart des Eigentuemers).

ZUSATZ: Segmentweise Bootstrap-KIs (2000, Seed 20260730). Das Kriterium
ist ein Punktschaetzer-Kriterium; die KIs sind Zusatzinformation, kein
Urteilsbestandteil - sie zeigen, wie belastbar ein knappes Bestehen ist.

Reproduktion: python neubewertung_v12.py
"""
import random
import sys

import batterie_h1 as H1

SEED = 20260730
BOOT = 2000
K_BASIS = 0.60
SEGMENTE = H1.SEGMENTE


def ki(xs, rnd):
    n = len(xs)
    ms = []
    for _ in range(BOOT):
        ms.append(sum(xs[rnd.randrange(n)] for _ in range(n)) / n)
    ms.sort()
    return ms[int(0.025 * BOOT)], ms[int(0.975 * BOOT) - 1]


def main():
    print("=" * 104)
    print(" NEUBEWERTUNG UNTER REGISTER v1.2 - verschaerftes Segment-Kriterium")
    print(" Kein neuer Trial. Identische Signale/Runden/Kosten wie batterie_h1.py.")
    print(f" L1: netto_EV > 0 (= altes Kriterium) | L2: netto_EV > {K_BASIS:.2f} %"
          " (Kosten zweimal verdient)")
    print("=" * 104)

    k_map = {s: H1.lade(s) for s in H1.SYMBOLE12}
    regeln = [("R1 Faber 10M-SMA", H1.signal_r1),
              ("R2 MOP 12M-Momentum", H1.signal_r2),
              ("R3 Donchian 20/10", H1.signal_r3)]
    trials = []
    nr = 16
    for rname, fn in regeln:
        for s in ("BTCUSDT", "ETHUSDT"):
            trials.append((f"T-{nr:03d}", f"{rname} | {s}", fn, [s]))
            nr += 1
    for rname, fn in regeln:
        trials.append((f"T-{nr:03d}", f"{rname} | 12er-Portfolio", fn,
                       H1.SYMBOLE12))
        nr += 1

    # Nur die drei bisher CONFIRMED sind neu zu bewerten; die uebrigen
    # waren bereits REJECTED/INCONCLUSIVE und koennen sich nicht verbessern.
    ALT = {"T-016": "INCONCLUSIVE (n<12)", "T-017": "INCONCLUSIVE (n<12)",
           "T-018": "INCONCLUSIVE (n<12)", "T-019": "INCONCLUSIVE (n<12)",
           "T-020": "CONFIRMED", "T-021": "CONFIRMED",
           "T-022": "REJECTED (Segment)", "T-023": "REJECTED (Segment, Placebo)",
           "T-024": "CONFIRMED"}

    ergebnis = {}
    for tnr, name, fn, symbole in trials:
        rnd = random.Random(SEED)
        runden = []
        for s in symbole:
            sig = fn(k_map[s])
            runden.extend(H1.runden_aus_signal(k_map[s], sig))
        segwerte = {}
        for bez, von, bis in SEGMENTE:
            rr = [r for r in runden if von <= H1.monat(r[4]) <= bis]
            if rr:
                evs = H1.netto_evs(rr, K_BASIS)
                lo, hi = ki(evs, rnd)
                segwerte[bez] = (sum(evs) / len(evs), len(evs), lo, hi)
        ergebnis[tnr] = (name, segwerte)

    print(f"\n  {'Trial':<7s} {'Seg':<4s} {'n':>4s} {'netto EV':>10s} "
          f"{'95%-KI':>24s}  {'L1':>4s} {'L2':>4s}")
    print("  " + "-" * 74)
    urteile = {}
    for tnr, (name, segwerte) in ergebnis.items():
        l1_ok = l2_ok = True
        for bez, _v, _b in SEGMENTE:
            if bez not in segwerte:
                continue
            ev, n, lo, hi = segwerte[bez]
            a = ev > 0
            b = ev > K_BASIS
            l1_ok &= a
            l2_ok &= b
            print(f"  {tnr:<7s} {bez:<4s} {n:4d} {ev:+9.3f}% "
                  f"[{lo:+9.3f} ; {hi:+9.3f}]  {'ok' if a else 'FAIL':>4s} "
                  f"{'ok' if b else 'FAIL':>4s}")
        urteile[tnr] = (l1_ok, l2_ok)
        print("  " + "-" * 74)

    print("\n" + "=" * 104)
    print(" URTEILE: ALT (v1.1) gegen NEU (v1.2, Lesart L2)")
    print("=" * 104)
    print(f"\n  {'Trial':<7s} {'Regel/Asset':<34s} {'ALT':<14s} {'NEU v1.2':<14s} Aenderung")
    print("  " + "-" * 92)
    noch_conf = []
    for tnr, (name, _sw) in ergebnis.items():
        alt = ALT.get(tnr, "?")
        l1_ok, l2_ok = urteile[tnr]
        if alt.startswith("CONFIRMED"):
            neu = "CONFIRMED" if l2_ok else "REJECTED (Seg v1.2)"
        elif alt.startswith("INCONCLUSIVE"):
            neu = alt      # n-Schwelle unveraendert, kann sich nicht verbessern
        else:
            neu = alt
        if neu.startswith("CONFIRMED"):
            noch_conf.append((tnr, name))
        aend = "" if neu == alt else "  <== GEAENDERT"
        print(f"  {tnr:<7s} {name:<34s} {alt:<14s} {neu:<20s}{aend}")

    print("\n" + "=" * 104)
    if noch_conf:
        print(f" GATE 1 UNTER v1.2: WEITERHIN POSITIV - "
              f"{len(noch_conf)} Trial(s) ueberleben")
        for t, n in noch_conf:
            print(f"    {t}  {n}")
    else:
        print(" GATE 1 UNTER v1.2: NEGATIV - kein Trial ueberlebt")
    print("=" * 104)

    # Kontrast: was waere unter L1 (altes Kriterium) passiert
    l1_conf = [t for t in ("T-020", "T-021", "T-024") if urteile[t][0]]
    print(f"\n  Kontrollrechnung Lesart L1 (netto>0, altes Kriterium): "
          f"{len(l1_conf)} CONFIRMED {l1_conf}")
    print(f"  Kontrollrechnung Lesart L2 (netto>{K_BASIS:.2f} %): "
          f"{len(noch_conf)} CONFIRMED {[t for t, _n in noch_conf]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
