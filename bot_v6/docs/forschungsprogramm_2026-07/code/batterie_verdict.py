# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsprogramm Pfad B - Gate-1-Gesamtauswertung, 30.07.2026.
"""
Gate-1-Verdict: BH-FDR (q=0,10) ueber die 13 H1/H2-Trials und
Zusammenfassung aller Urteile. Kein neuer Trial - reine Zusammenfassung
bereits gerechneter p-Werte aus batterie_h1_out.txt / batterie_h2_out.txt.
T-030 (H4) hat ein Calmar-Kriterium und laeuft ausserhalb der FDR
(Register v1.0 Paragraf 3: FDR ueber H1/H2-Familie).
"""
import sys

Q = 0.10
TRIALS = [
    ("T-016", 0.0060, "INCONCLUSIVE (n<12)", "R1 Faber | BTC"),
    ("T-017", 0.3355, "INCONCLUSIVE (n<12)", "R1 Faber | ETH"),
    ("T-018", 0.0470, "INCONCLUSIVE (n<12)", "R2 MOP | BTC"),
    ("T-019", 0.2180, "INCONCLUSIVE (n<12)", "R2 MOP | ETH"),
    ("T-020", 0.0135, "CONFIRMED*", "R3 Donchian | BTC"),
    ("T-021", 0.0115, "CONFIRMED*", "R3 Donchian | ETH"),
    ("T-022", 0.0000, "REJECTED (Segment)", "R1 Faber | Portfolio"),
    ("T-023", 0.0000, "REJECTED (Segment, Placebo)", "R2 MOP | Portfolio"),
    ("T-024", 0.0000, "CONFIRMED*", "R3 Donchian | Portfolio"),
    ("T-025", 0.0185, "REJECTED (Placebo)", "H2 E-neg | BTC"),
    ("T-026", 0.0865, "INCONCLUSIVE (n<30)", "H2 E-neg | ETH"),
    ("T-027", 0.2000, "INCONCLUSIVE (n<30)", "H2 E-pos | BTC"),
    ("T-028", 0.9250, "INCONCLUSIVE (n<30)", "H2 E-pos | ETH"),
]


def main():
    print("=" * 100)
    print(" GATE-1-GESAMTAUSWERTUNG  |  BH-FDR q=0,10 ueber 13 H1/H2-Trials")
    print("=" * 100)
    m = len(TRIALS)
    srt = sorted(TRIALS, key=lambda x: x[1])
    kmax = 0
    for k, (_t, p, _u, _n) in enumerate(srt, 1):
        if p <= k * Q / m:
            kmax = k
    schwelle = srt[kmax - 1][1] if kmax else 0.0
    print(f"\n  BH: groesstes k mit p(k) <= k*q/m: k={kmax} "
          f"-> Signifikanzschwelle p <= {schwelle:.4f}\n")
    print(f"  {'Trial':<7s} {'p':>7s} {'FDR':>6s}  {'Urteil (Kriterien)':<30s} Name")
    print("  " + "-" * 90)
    final = []
    for k, (t, p, u, n) in enumerate(srt, 1):
        sig = p <= schwelle and kmax > 0
        endg = u
        if u.startswith("CONFIRMED") and not sig:
            endg = "REJECTED (FDR)"
        final.append((t, endg, n))
        print(f"  {t:<7s} {p:7.4f} {'JA' if sig else 'nein':>6s}  {endg:<30s} {n}")
    print("\n  T-029 H3: NICHT AUSGEFUEHRT (Universum 12 < 30, Registerbedingung "
          "nicht erfuellt; Trial unverbraucht)")
    print("  T-030 H4: REJECTED (Calmar-KI enthaelt 0; EV-Differenz signifikant "
          "negativ) - siehe batterie_h4_out.txt")
    conf = [x for x in final if x[1].startswith("CONFIRMED")]
    print("\n" + "=" * 100)
    print(f" GATE 1: {'POSITIV' if conf else 'NEGATIV'} - "
          f"{len(conf)} Trial(s) CONFIRMED nach FDR")
    for t, _u, n in conf:
        print(f"    {t}  {n}")
    print("=" * 100)
    print("""
  Verbrauchte Trials dieser Batterie: T-016..T-028 (13) + T-030 (1) = 14.
  T-029 unverbraucht. Budget 15 -> 1 Trial verbleibt.
  Naechster Schritt laut Programm: Walk-Forward-Protokoll + Einfrieren der
  Regel + 90-Tage-Forward-Paper (Gate 2). Ein Bericht der Regel auf der
  kontaminierten Zeit 2024-26 waere eine weitere Auswertung und braucht
  eine Registerversion v1.2 mit Freigabe.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
