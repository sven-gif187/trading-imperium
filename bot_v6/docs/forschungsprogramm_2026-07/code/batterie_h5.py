# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Runde 2 - H5-Batterie (T-031..T-033), 31.07.2026.
"""
H5 - Volatilitaetskontraktion und Ausbruch. Trials T-031, T-032, T-033.

VERBINDLICHE LESART (Register v2.0, woertlich):
  Runde 2 testet KEINE neue Richtung, sondern die Teilfrage, ob
  Volatilitaetskontraktion die Selektivitaet liefert, die Donchian fehlte.

REGEL (Crabel 1990, "Day Trading with Short Term Price Patterns and
Opening Range Breakout", Futures, vor 2015 - die 7 steht in der Quelle):
  NR7-Balken: Tagesbalken, dessen Spanne (High-Low) die kleinste der
              letzten 7 Balken ist, inklusive sich selbst.
  Einstieg:   Schlusskurs > High des juengsten NR7-Balkens -> long ab
              dem naechsten Tages-Open.
  Ausstieg:   Schlusskurs < Low des juengsten NR7-Balkens -> flat ab dem
              naechsten Tages-Open.
  Long/Flat, Spot, keine Shorts. Parameterraum ausschliesslich {7}.

Der "juengste NR7-Balken" wird bei jedem neuen NR7 aktualisiert; die
Schwellen wandern also mit. Kein zweiter Parameter, keine zweite Quelle.

TESTDESIGN (Register v1.2 Klauseln A und B, v2.0 unveraendert):
  Entwicklung 2017-08-17..2023-12-31. Ausfuehrung next-open.
  K-MAKER 0,26 / K-BASIS 0,60 / K-KONSERVATIV 0,75 - alle berichtet.
  CONFIRMED nur, wenn Netto-EV je Runde in JEDEM Segment > 0,60 %.
  Sekundaere Trials (Portfolio) tragen kein Gate (Klausel B).
  Placebo 200 Markov-Masken, Seed 20260730, echt > 95. Perzentil.
  Block-Bootstrap 2000 ueber Runden. Lag+1 als Look-ahead-Detektor.
  n < 12 Runden -> INCONCLUSIVE.
  MaxDD < MaxDD Halten (Regel 12).

PFLICHTKENNZAHLEN Runde 2 (Register v2.0 Par. 3): Haltedauerverteilung,
MFE/MAE je Runde, realisiertes R/R, Trefferquote UND Payoff getrennt.
Die externe Referenz "23-46 Tage bei 65 %" wird NICHT zur Kalibrierung
verwendet - nichts wird darauf eingestellt.

Reine Standardbibliothek. Reproduktion: python batterie_h5.py
"""
import random
import sys

import batterie_h1 as H1

SEED = 20260730
BOOT = 2000
PLACEBO_N = 200
NR = 7
K_BASIS = 0.60
SZENARIEN = [("K-MAKER", 0.26), ("K-BASIS", 0.60), ("K-KONSERVATIV", 0.75)]


def signal_h5(k):
    """NR7-Ausbruch. sig[i] = gewuenschte Position am Tag i, entschieden
    aus Daten bis einschliesslich Tag i-1. Kein Look-ahead."""
    sig = [None] * len(k)
    stand = 0
    nr_hi = nr_lo = None
    for i in range(len(k)):
        if i >= NR - 1:
            spanne = k[i][2] - k[i][3]
            ist_nr7 = all(spanne <= (k[x][2] - k[x][3])
                          for x in range(i - NR + 1, i))
            if ist_nr7:
                nr_hi, nr_lo = k[i][2], k[i][3]
            c = k[i][4]
            if nr_hi is not None:
                if stand == 0 and c > nr_hi:
                    stand = 1
                elif stand == 1 and c < nr_lo:
                    stand = 0
        if i + 1 < len(k):
            sig[i + 1] = stand
    return sig


def kennzahlen_runden(k, runden, c_pct):
    """MFE/MAE, R/R, Haltedauer je Runde."""
    out = []
    for e_i, a_i, e_o, a_o, _t in runden:
        hoch = max(k[x][2] for x in range(e_i, a_i + 1))
        tief = min(k[x][3] for x in range(e_i, a_i + 1))
        mfe = (hoch / e_o - 1) * 100
        mae = (tief / e_o - 1) * 100
        netto = (a_o / e_o - 1) * 100 - c_pct
        out.append({"tage": a_i - e_i, "mfe": mfe, "mae": mae,
                    "netto": netto,
                    "rr": (mfe / abs(mae)) if mae < -1e-9 else None})
    return out


def perz(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(int(q * len(s)), len(s) - 1)
    return s[i]


def trial(nr, name, k_map, symbole, sekundaer=False):
    rnd = random.Random(SEED)
    alle = []
    sigs = {}
    for s in symbole:
        k = k_map[s]
        sig = signal_h5(k)
        sigs[s] = sig
        for r in H1.runden_aus_signal(k, sig):
            alle.append((s, r))
    n = len(alle)
    Z = [f"\n  {nr}  {name}   Runden={n}"
         + ("   [SEKUNDAER - traegt kein Gate, Klausel B]" if sekundaer else "")]
    if n == 0:
        Z.append("    KEINE RUNDEN -> INCONCLUSIVE")
        return 1.0, "INCONCLUSIVE", Z

    erg = {}
    for bez, c in SZENARIEN:
        evs = H1.netto_evs([r for _s, r in alle], c)
        lo, hi, p = H1.bootstrap_ki(evs, random.Random(SEED))
        erg[bez] = (sum(evs) / n, lo, hi, p)
    Z.append(f"    {'Szenario':<14s} {'EV/Runde':>10s} {'95%-KI':>22s} {'p':>9s}")
    for bez, _c in SZENARIEN:
        ev, lo, hi, p = erg[bez]
        Z.append(f"    {bez:<14s} {ev:+9.3f}% [{lo:+8.3f} ; {hi:+8.3f}]% {p:9.4f}")

    # --- Klausel A: jedes Segment > K-BASIS ---
    seg = {}
    for bez, von, bis in H1.SEGMENTE:
        rr = [r for _s, r in alle if von <= H1.monat(r[4]) <= bis]
        if rr:
            evs = H1.netto_evs(rr, K_BASIS)
            lo, hi, _p = H1.bootstrap_ki(evs, random.Random(SEED))
            seg[bez] = (sum(evs) / len(evs), len(evs), lo, hi)
    Z.append(f"\n    KLAUSEL A - Netto-EV je Segment muss > {K_BASIS:.2f} % sein:")
    klausel_a = bool(seg)
    for bez, von, bis in H1.SEGMENTE:
        if bez not in seg:
            Z.append(f"      {bez}: keine Runden -> Kriterium NICHT erfuellbar")
            klausel_a = False
            continue
        ev, m, lo, hi = seg[bez]
        ok = ev > K_BASIS
        klausel_a &= ok
        Z.append(f"      {bez}  n={m:4d}  EV {ev:+9.3f} %  "
                 f"KI [{lo:+8.3f} ; {hi:+8.3f}]  "
                 f"{'ok' if ok else 'FAIL'}")

    # --- Placebo ---
    if len(symbole) == 1:
        pls = H1.placebo_evs(k_map[symbole[0]], sigs[symbole[0]], K_BASIS, rnd)
    else:
        pls = []
        for _z in range(PLACEBO_N):
            pool = []
            for s in symbole:
                _lq, ml, mf = H1.blocklaengen(sigs[s])
                p_ll = 1.0 - 1.0 / max(ml, 1.0001)
                p_ff = 1.0 - 1.0 / max(mf, 1.0001)
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
                pool.extend(H1.netto_evs(
                    H1.runden_aus_signal(k_map[s], m), K_BASIS))
            if pool:
                pls.append(sum(pool) / len(pool))
        pls.sort()
    ev_b = erg["K-BASIS"][0]
    p95 = perz(pls, 0.95)
    plc_ok = ev_b > p95
    rang = sum(1 for x in pls if x < ev_b) / len(pls) * 100 if pls else 0
    Z.append(f"\n    Placebo (200 Masken): 95.P {p95:+.3f} %  echt {ev_b:+.3f} %  "
             f"Rang {rang:.0f}. Perz. -> "
             f"{'GESCHLAGEN' if plc_ok else 'NICHT geschlagen'}")

    # --- Lag+1 ---
    lag = []
    for s in symbole:
        lag.extend(H1.netto_evs(
            H1.runden_aus_signal(k_map[s], sigs[s], lag=1), K_BASIS))
    Z.append(f"    Lag+1 (Look-ahead-Detektor): EV {sum(lag)/len(lag):+.3f} %"
             if lag else "    Lag+1: keine Runden")

    # --- MaxDD gegen Halten ---
    dds, hdds = [], []
    for s in symbole:
        _eq, dd = H1.equity_und_dd(k_map[s], sigs[s], K_BASIS)
        _hr, hdd = H1.halten_dd(k_map[s])
        dds.append(dd)
        hdds.append(hdd)
    dd_s, dd_h = sum(dds) / len(dds), sum(hdds) / len(hdds)
    Z.append(f"    MaxDD Regel {dd_s:.1f} % vs Halten {dd_h:.1f} % "
             f"({'kleiner' if dd_s < dd_h else 'NICHT kleiner'})")

    # --- Pflichtkennzahlen Runde 2 ---
    km = []
    for s in symbole:
        km.extend(kennzahlen_runden(
            k_map[s], H1.runden_aus_signal(k_map[s], sigs[s]), K_BASIS))
    tage = [x["tage"] for x in km]
    rrs = [x["rr"] for x in km if x["rr"] is not None]
    gew = [x["netto"] for x in km if x["netto"] > 0]
    ver = [x["netto"] for x in km if x["netto"] <= 0]
    Z.append(f"\n    PFLICHTKENNZAHLEN (Register v2.0 Par. 3)")
    Z.append(f"      Haltedauer Tage: Median {perz(tage,0.5):.0f}  "
             f"25./75. {perz(tage,0.25):.0f}/{perz(tage,0.75):.0f}  "
             f"Min/Max {min(tage)}/{max(tage)}")
    Z.append(f"      MFE Median {perz([x['mfe'] for x in km],0.5):+.2f} %  "
             f"MAE Median {perz([x['mae'] for x in km],0.5):+.2f} %")
    Z.append(f"      realisiertes R/R: Median {perz(rrs,0.5):.2f}  "
             f"25./75. {perz(rrs,0.25):.2f}/{perz(rrs,0.75):.2f}" if rrs
             else "      realisiertes R/R: nicht berechenbar")
    tq = len(gew) / len(km) * 100
    payoff = ((sum(gew) / len(gew)) / abs(sum(ver) / len(ver))
              if gew and ver else None)
    Z.append(f"      Trefferquote {tq:.1f} %   Payoff "
             + (f"{payoff:.2f}" if payoff else "-")
             + f"   (getrennt ausgewiesen, nicht kalibriert)")
    kurz = perz(tage, 0.5) < 23
    Z.append(f"      Referenzband 23-46 Handelstage: Median liegt "
             f"{'DARUNTER -> BEFUND' if kurz else 'im/ueber dem Band'}")

    # --- Urteil ---
    ev, lo, hi, p = erg["K-BASIS"]
    if sekundaer:
        urteil = ("NICHT GATE-TRAGEND (Klausel B)"
                  if klausel_a and plc_ok else
                  "REJECTED (Klausel B + Kriterien)")
    elif n < 12:
        urteil = f"INCONCLUSIVE (n={n} < 12)"
    elif klausel_a and lo > 0 and plc_ok and dd_s < dd_h:
        urteil = "CONFIRMED*"
    else:
        g = []
        if not klausel_a:
            g.append("Klausel A")
        if lo <= 0:
            g.append("KI enthaelt 0")
        if not plc_ok:
            g.append("Placebo")
        if dd_s >= dd_h:
            g.append("MaxDD")
        urteil = "REJECTED (" + ", ".join(g) + ")"
    Z.append(f"\n    URTEIL {nr}: {urteil}")
    return p, urteil, Z


def main():
    print("=" * 100)
    print(" H5-BATTERIE  T-031..T-033  |  Register v2.0 (freigegeben, ohne H8)")
    print(" Crabel 1990, NR7-Kontraktion + Ausbruch  |  Seed", SEED)
    print(" LESART: Runde 2 testet KEINE neue Richtung, sondern die Teilfrage,")
    print(" ob Volatilitaetskontraktion die Selektivitaet liefert, die")
    print(" Donchian fehlte.  Vorabschaetzung im Register: 10 %.")
    print("=" * 100)
    k_map = {s: H1.lade(s) for s in H1.SYMBOLE12}
    ps = []
    for nr, name, syms, sek in (
            ("T-031", "H5 NR7-Ausbruch | BTCUSDT", ["BTCUSDT"], False),
            ("T-032", "H5 NR7-Ausbruch | ETHUSDT", ["ETHUSDT"], False),
            ("T-033", "H5 NR7-Ausbruch | 12er-Portfolio", H1.SYMBOLE12, True)):
        p, u, Z = trial(nr, name, k_map, syms, sek)
        ps.append((nr, name, p, u))
        for z in Z:
            print(z)
        sys.stdout.flush()

    print("\n" + "=" * 100)
    print(" BH-FDR ueber die Runde-2-Trials (q=0,10)")
    print("=" * 100)
    q, m = 0.10, len(ps)
    srt = sorted(ps, key=lambda x: x[2])
    kmax = 0
    for i, (_t, _n, p, _u) in enumerate(srt, 1):
        if p <= i * q / m:
            kmax = i
    schwelle = srt[kmax - 1][2] if kmax else 0.0
    print(f"\n  Schwelle p <= {schwelle:.4f} (k={kmax} von m={m})\n")
    conf = []
    for t, nme, p, u in srt:
        sig = kmax > 0 and p <= schwelle
        end = u
        if u.startswith("CONFIRMED") and not sig:
            end = "REJECTED (FDR)"
        if end.startswith("CONFIRMED"):
            conf.append(t)
        print(f"  {t}  p={p:.4f}  {'JA ' if sig else 'nein'}  {end:<34s} {nme}")
    print("\n" + "=" * 100)
    print(f" GATE 2 (H5-Teil): {'POSITIV' if conf else 'NEGATIV'}"
          + (f" - {conf}" if conf else " - kein gate-tragender Trial CONFIRMED"))
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
