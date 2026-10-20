# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit G2 vom 30.07.2026.
# Nicht archivieren - letzter offener Horizont-Test. Siehe ../README.md
"""
G2 - Lange Horizonte mit weiten Schranken.

Symmetrisches First-Touch-Barrierenrennen auf den ECHTEN Einstiegen des
Harness (identische Definition wie E2: LaufMess.kauf_events), fuer:

    +/- 2,5 %  /  72 h   (Referenz - MUSS 47,66 (J2) / 50,69 (J1) treffen)
    +/- 5  %   /  7 d
    +/- 7  %   / 14 d
    +/- 10 %   / 30 d

Je Kombination:
  - P(auf) unter den entschiedenen Rennen + Block-Bootstrap-KI (2000,
    Tage mit Zuruecklegen, Seed 20260730 - wie E2)
  - Zensierung: Anteil ohne Schrankenberuehrung, deren Endstand
    (Anteil ueber Einstand, Median-Brutto), P(auf)-Schranken wenn man
    Zensierte komplett als Verlierer bzw. Gewinner zaehlt
  - Randfenster: Events, deren Fenster ueber das Datenende ragt
    (E2-Verhalten: Fenster wird stumm gekuerzt) - zusaetzlich P(auf)
    ohne diese Events
  - E[r] je Runde inkl. Zensierter (auf=+B, ab=-B, zensiert=Endstand)
    gegen die Reibung 0,30 % / 0,15 %
  - Placebo S1 (gleichverteilt uebers Jahr) und S2 (gleiche Tage,
    zufaellige Uhrzeit), je 20 Ziehungen - wie E2
  - Effektive Unabhaengigkeit: Einstiegstage und maximale Zahl
    nicht ueberlappender Fenster im Jahr

WARUM DIE LANGEN KOMBIS MIT VORSICHT ZU LESEN SIND
--------------------------------------------------
1. Ein Jahr enthaelt hoechstens ~12 nicht ueberlappende 30-Tage-Fenster.
   1600 Einstiege in 30-Tage-Rennen sind zu >99 % ueberlappend - die
   nominelle Fallzahl ist Illusion, der Bootstrap ueber Tage faengt das
   nur teilweise (Tage innerhalb eines Fensters sind gekoppelt).
2. Auf 30 Tagen misst das Rennen ueberwiegend die Marktdrift des
   Jahres (J2: BTC -45 %, J1: +74 %), nicht die Einstiegswahl. Der
   Vergleich mit S1/S2 zerlegt das.
3. Break-even p = 0,5 + c/(2B) gilt NUR unter Entschiedenen und nur,
   wenn Gewinn und Verlust exakt +/-B sind. Mit Zensierten ist die
   ehrliche Groesse E[r_brutto] - c.

Reine Standardbibliothek, wie E1-F3 (First-Touch ueber
Block-Max/Min-Dekomposition beschleunigt, numerisch identisch zur
naiven Suche - die Referenzkombination beweist es gegen E2).
"""
import bisect
import random
import sys
from datetime import datetime, timezone

from harness_ext import LaufMess, NEUE_LEITER, lade_jahr, TAG_MS
from messung_f_stat import median, mittel

SEED = 20260730
BOOT = 2000
ZIEHUNGEN = 20
BLOCK = 64

KOMBIS = [
    ("+/-2,5 % / 72 h", 2.5, 288),
    ("+/-5 % / 7 d", 5.0, 672),
    ("+/-7 % / 14 d", 7.0, 1344),
    ("+/-10 % / 30 d", 10.0, 2880),
]
REIBUNGEN = (0.30, 0.15)


# ===========================================================================
# First-Touch mit Blockdekomposition (numerisch identisch zur E2-Schleife)
# ===========================================================================
def baue_bloecke(ks):
    """Block-Hi/Lo ueber je BLOCK Kerzen."""
    n = len(ks)
    nb = (n + BLOCK - 1) // BLOCK
    bhi = [0.0] * nb
    blo = [0.0] * nb
    for b in range(nb):
        a, e = b * BLOCK, min((b + 1) * BLOCK, n)
        bhi[b] = max(ks[x][2] for x in range(a, e))
        blo[b] = min(ks[x][3] for x in range(a, e))
    return bhi, blo


def _linear(ks, a, e, oben, unten):
    """E2-Reihenfolge: Tief vor Hoch (pessimistisch)."""
    for x in range(a, e):
        if ks[x][3] <= unten:
            return "ab", x
        if ks[x][2] >= oben:
            return "auf", x
    return None, e


def rennen(ks, bloecke, zeiten, t0, preis, b_pct, fenster):
    """First-Touch. Gibt (ausgang, letzter_index_im_fenster)."""
    if preis <= 0:
        return "keine", -1
    i = bisect.bisect_right(zeiten, t0)
    j = min(i + fenster, len(ks))
    oben = preis * (1 + b_pct / 100)
    unten = preis * (1 - b_pct / 100)
    bhi, blo = bloecke
    x = i
    while x < j:
        b = x // BLOCK
        be = min((b + 1) * BLOCK, j)
        if x % BLOCK == 0 and be <= j and blo[b] > unten and bhi[b] < oben:
            x = be                      # ganzer Block ohne Beruehrung
            continue
        r, x2 = _linear(ks, x, be, oben, unten)
        if r:
            return r, x2
        x = be
    return "keine", j - 1


def perzentil(xs, q):
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ===========================================================================
def auswerten(idx, bloecke, zt, events, b_pct, fenster, datenende):
    """Alle Kennzahlen einer Kombination fuer eine Eventliste."""
    auf = ab = 0
    zens = []             # Brutto-Endstand der Zensierten in %
    rand = 0              # Events mit verkuerztem Fenster
    auf_voll = ab_voll = 0
    ausgaenge = []        # (tag, 1/0) nur Entschiedene - fuer Bootstrap
    renditen = []         # Brutto je Event inkl. Zensierter
    for s, t, p in events:
        ks = idx.get(s)
        if not ks:
            continue
        r, xe = rennen(ks, bloecke[s], zt[s], t, p, b_pct, fenster)
        i0 = bisect.bisect_right(zt[s], t)
        voll = (i0 + fenster) <= len(ks)
        if not voll:
            rand += 1
        if r == "auf":
            auf += 1
            renditen.append(b_pct)
            ausgaenge.append((t // TAG_MS, 1))
            if voll:
                auf_voll += 1
        elif r == "ab":
            ab += 1
            renditen.append(-b_pct)
            ausgaenge.append((t // TAG_MS, 0))
            if voll:
                ab_voll += 1
        else:
            end = ks[xe][4] if xe >= 0 else p
            zens.append((end / p - 1) * 100)
            renditen.append((end / p - 1) * 100)
    n_ent = auf + ab
    n = n_ent + len(zens)
    return {
        "n": n, "auf": auf, "ab": ab, "zens": zens, "rand": rand,
        "p_auf": auf / n_ent * 100 if n_ent else 0.0,
        "p_auf_voll": (auf_voll / (auf_voll + ab_voll) * 100
                       if (auf_voll + ab_voll) else 0.0),
        "n_voll": auf_voll + ab_voll,
        "p_min": auf / n * 100 if n else 0.0,          # Zensierte = Verlierer
        "p_max": (auf + len(zens)) / n * 100 if n else 0.0,  # = Gewinner
        "er": mittel(renditen),
        "ausgaenge": ausgaenge,
    }


def bootstrap_ki(ausgaenge, rnd):
    nach_tag = {}
    for tag, w in ausgaenge:
        nach_tag.setdefault(tag, []).append(w)
    tage = list(nach_tag)
    qs = []
    for _ in range(BOOT):
        a = g = 0
        for _i in range(len(tage)):
            for w in nach_tag[tage[rnd.randrange(len(tage))]]:
                a += w
                g += 1
        if g:
            qs.append(a / g * 100)
    return perzentil(qs, 0.025), perzentil(qs, 0.975), len(tage)


def main():
    rnd = random.Random(SEED)
    referenz = {"": 47.66, "_v1": 50.69}
    for jahr_bez, marke in (("Jahr 2  2025-07..2026-07", ""),
                            ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        idx = {s: sorted(ks) for s, ks in daten.items()}
        zt = {s: [k[0] for k in ks] for s, ks in idx.items()}
        bloecke = {s: baue_bloecke(ks) for s, ks in idx.items()}
        tage_idx = {}
        for s, ks in idx.items():
            d = {}
            for i, k in enumerate(ks):
                d.setdefault(k[0] // TAG_MS, []).append(i)
            tage_idx[s] = d
        datenende = max(ks[-1][0] for ks in idx.values())
        jahr_tage = (datenende - min(ks[0][0] for ks in idx.values())) // TAG_MS

        L = LaufMess(NEUE_LEITER, "basis", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)
        echt = L.kauf_events
        e_tage = len({t // TAG_MS for _s, t, _p in echt})

        print("\n" + "=" * 118)
        print(f" G2  BARRIERENRENNEN UEBER LANGE HORIZONTE  -  {jahr_bez}")
        print(f" {len(echt)} echte Einstiege an {e_tage} Kalendertagen | "
              f"Seed {SEED} | Bootstrap {BOOT} | Placebo je {ZIEHUNGEN} Ziehungen")
        print("=" * 118)

        for name, b_pct, fenster in KOMBIS:
            e = auswerten(idx, bloecke, zt, echt, b_pct, fenster, datenende)
            lo, hi, n_tage = bootstrap_ki(e["ausgaenge"], rnd)

            # Placebos
            maxstart = {s: max(1, len(ks) - fenster - 1)
                        for s, ks in idx.items()}

            def ziehe_S1():
                ev = []
                for s, _t, _p in echt:
                    i = rnd.randrange(maxstart[s])
                    ev.append((s, idx[s][i][0], idx[s][i][4]))
                return ev

            def ziehe_S2():
                ev = []
                for s, t, _p in echt:
                    kand = tage_idx[s].get(t // TAG_MS)
                    if not kand:
                        continue
                    i = kand[rnd.randrange(len(kand))]
                    ev.append((s, idx[s][i][0], idx[s][i][4]))
                return ev

            p1 = [auswerten(idx, bloecke, zt, ziehe_S1(), b_pct, fenster,
                            datenende)["p_auf"] for _ in range(ZIEHUNGEN)]
            p2 = [auswerten(idx, bloecke, zt, ziehe_S2(), b_pct, fenster,
                            datenende)["p_auf"] for _ in range(ZIEHUNGEN)]

            n_unabh = max(1, int(jahr_tage // (fenster / 96)))
            print(f"\n  {name}")
            print(f"    Rennen: {e['n']} | entschieden {e['auf'] + e['ab']} "
                  f"(auf {e['auf']} / ab {e['ab']}) | ZENSIERT {len(e['zens'])} "
                  f"({len(e['zens']) / e['n'] * 100:.1f} %) | Randfenster "
                  f"{e['rand']} ({e['rand'] / e['n'] * 100:.1f} %)")
            ref = ""
            if abs(b_pct - 2.5) < 1e-9:
                soll = referenz[marke]
                treff = abs(e["p_auf"] - soll) < 0.005
                ref = (f"   [REFERENZ: Soll {soll:.2f} % -> "
                       f"{'TREFFER' if treff else 'ABWEICHUNG!'}]")
            print(f"    P(auf) entschieden      = {e['p_auf']:6.2f} %   "
                  f"95%-KI [{lo:.2f} ; {hi:.2f}] ueber {n_tage} Tage{ref}")
            print(f"    P(auf) nur volle Fenster= {e['p_auf_voll']:6.2f} % "
                  f"  (n={e['n_voll']})")
            print(f"    Schranken mit Zensierten: als Verlierer "
                  f"{e['p_min']:.2f} % | als Gewinner {e['p_max']:.2f} %")
            if e["zens"]:
                z_pos = sum(1 for z in e["zens"] if z > 0)
                print(f"    Zensierte: {z_pos}/{len(e['zens'])} "
                      f"({z_pos / len(e['zens']) * 100:.1f} %) ueber Einstand, "
                      f"Median-Brutto {median(e['zens']):+.2f} %")
            print(f"    Placebo S1 (Jahr, {ZIEHUNGEN}x)  = {mittel(p1):6.2f} % "
                  f"  [{perzentil(p1, 0.025):.2f} ; {perzentil(p1, 0.975):.2f}]")
            print(f"    Placebo S2 (Tage, {ZIEHUNGEN}x)  = {mittel(p2):6.2f} % "
                  f"  [{perzentil(p2, 0.025):.2f} ; {perzentil(p2, 0.975):.2f}]")
            print(f"    Echt minus S2 (Uhrzeitwahl)     = "
                  f"{e['p_auf'] - mittel(p2):+.2f} pp")
            for c in REIBUNGEN:
                p_be = (0.5 + c / (2 * b_pct)) * 100
                urteil = ("KI-Obergrenze darunter -> AUSGESCHLOSSEN"
                          if hi < p_be else
                          ("Punktschaetzer darueber" if e["p_auf"] >= p_be
                           else "nur KI-Obergrenze darueber -> NICHT ENTSCHEIDBAR"))
                print(f"    Break-even c={c:.2f} %: noetig {p_be:5.2f} % | "
                      f"gemessen {e['p_auf']:5.2f} % | {urteil}")
            er_net = [e["er"] - c for c in REIBUNGEN]
            print(f"    E[r] je Runde inkl. Zensierter = {e['er']:+.3f} % "
                  f"brutto -> netto {er_net[0]:+.3f} % (c=0,30) / "
                  f"{er_net[1]:+.3f} % (c=0,15)")
            print(f"    Unabhaengigkeit: {e_tage} Einstiegstage, aber max. "
                  f"{n_unabh} nicht ueberlappende Fenster im Jahr")
            sys.stdout.flush()

    print("\n" + "=" * 118)
    print(" ENDE G2")
    print("=" * 118)
    return 0


if __name__ == "__main__":
    sys.exit(main())
