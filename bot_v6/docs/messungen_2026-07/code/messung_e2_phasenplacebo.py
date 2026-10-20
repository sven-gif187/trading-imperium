# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
E2 - PHASENGLEICHES PLACEBO + KONFIDENZINTERVALLE.

Der offene Angriff auf Befund 8: die bisherige Zufallsziehung war ueber das
ganze Jahr gleichverteilt, die echten Einstiege haeufen sich in Angstphasen.
Die Verteidigung "das Barrierenrennen ist skaleninvariant" deckt
VOLATILITAETS-Unterschiede ab, aber KEINE DRIFT-Unterschiede: haben
Angstphasen systematisch anderen Drift, vergleicht der Test Phasenwahl
statt Zeitpunktwahl.

LEITER (jede Stufe haelt eine Auswahlentscheidung mehr fest):
  S1  gleichverteilt ueber das ganze Jahr        (= alter Placebo)
  S3  gleichverteilt ueber alle Tage mit F&G<30  (Signalbedingung fixiert)
  S2  gleichverteilt INNERHALB der Tage, an denen der Bot real kaufte
      (Tagesverteilung exakt erhalten, nur Uhrzeit zufaellig)
  S0  die echten Einstiege
Differenz S1->S3 = Beitrag des F&G-Tagesfilters
Differenz S3->S2 = Beitrag der Auswahl WELCHER Angsttage
Differenz S2->S0 = Beitrag der Uhrzeitwahl  <- das ist der Rest, der dem
                   Einstiegssignal ueberhaupt noch zugerechnet werden kann

KONFIDENZINTERVALLE - warum nicht backtest/monte_carlo.py:
MonteCarloSim.run() mischt die Reihenfolge fertiger Trade-P&Ls
(monte_carlo.py:34-37). Das beantwortet "wie haette sich dieselbe
Trademenge anders aufreihen koennen" und zerstoert dabei genau die
Zeitstruktur, aus der hier die Unsicherheit stammt. Fuer den Anteil
gewonnener Barrierenrennen liefert es gar keine Statistik. Verwendet wird
deshalb ein BLOCK-BOOTSTRAP ueber Kalendertage: ganze Tage werden mit
Zuruecklegen gezogen, samt aller Einstiege/Trades dieses Tages. Damit
bleibt die Abhaengigkeit innerhalb eines Tages erhalten - unabhaengiges
Ziehen einzelner Trades wuerde die Streuung unterschaetzen.
"""
import bisect
import random
import sys
from harness_ext import LaufMess, NEUE_LEITER, lade_jahr, kennzahlen, TAG_MS

ZIEHUNGEN = 40
BOOT = 2000
SEED = 20260730
FENSTER_KERZEN = 288          # 72 h
AUF = AB = 2.5                # symmetrische Schranken


# ---------------------------------------------------------------- Rennen
def rennen(ks, zeiten, t0, preis, auf_pct, ab_pct):
    """Welche Schranke zuerst? Pessimistisch: Tief vor Hoch (wie Harness)."""
    if preis <= 0:
        return "keine"
    i = bisect.bisect_right(zeiten, t0)
    j = min(i + FENSTER_KERZEN, len(ks))
    oben, unten = preis * (1 + auf_pct / 100), preis * (1 - ab_pct / 100)
    for x in range(i, j):
        if ks[x][3] <= unten:
            return "ab"
        if ks[x][2] >= oben:
            return "auf"
    return "keine"


def quote(idx, zt, events):
    auf = ab = 0
    for s, t, p in events:
        ks = idx.get(s)
        if not ks:
            continue
        r = rennen(ks, zt[s], t, p, AUF, AB)
        if r == "auf":
            auf += 1
        elif r == "ab":
            ab += 1
    return (auf / (auf + ab) * 100) if (auf + ab) else 0.0, auf + ab


def perzentil(xs, q):
    s = sorted(xs)
    if not s:
        return 0.0
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ---------------------------------------------------------------- Ziehungen
def kerzen_je_tag(ks):
    d = {}
    for i, k in enumerate(ks):
        d.setdefault(k[0] // TAG_MS, []).append(i)
    return d


def main():
    rnd = random.Random(SEED)
    for jahr_bez, marke in (("Jahr 2  2025-07..2026-07", ""),
                            ("Jahr 1  2024-07..2025-07", "_v1")):
        daten, fg = lade_jahr(marke)
        idx = {s: sorted(ks) for s, ks in daten.items()}
        zt = {s: [k[0] for k in ks] for s, ks in idx.items()}
        tage_idx = {s: kerzen_je_tag(ks) for s, ks in idx.items()}
        maxstart = {s: max(1, len(ks) - FENSTER_KERZEN - 1) for s, ks in idx.items()}

        L = LaufMess(NEUE_LEITER, "basis", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)
        echt = L.kauf_events

        # F&G-Tage bestimmen (Tagesschluessel, an denen der Index unter 30 lag)
        alle_tage = sorted({k[0] // TAG_MS for ks in idx.values() for k in ks})
        import datetime as _dt
        def fg_am(tag):
            s = _dt.datetime.fromtimestamp(tag * TAG_MS / 1000,
                                           _dt.timezone.utc).strftime("%Y-%m-%d")
            return fg.get(s, 50)
        angst_tage = [t for t in alle_tage if fg_am(t) < 30]
        echte_tage = {}
        for s, t, p in echt:
            echte_tage.setdefault(s, []).append(t // TAG_MS)

        print("\n" + "=" * 112)
        print(f" E2 PHASENGLEICHES PLACEBO  -  {jahr_bez}")
        print(f" {len(echt)} echte Kaeufe | {len(alle_tage)} Tage gesamt | "
              f"{len(angst_tage)} Tage mit F&G<30 | {ZIEHUNGEN} Ziehungen je Szenario")
        print("=" * 112)

        q0, n0 = quote(idx, zt, echt)

        def ziehe_S1():
            ev = []
            for s, _t, _p in echt:
                i = rnd.randrange(maxstart[s])
                ev.append((s, idx[s][i][0], idx[s][i][4]))
            return ev

        def ziehe_S3():
            ev = []
            for s, _t, _p in echt:
                for _versuch in range(20):
                    tag = angst_tage[rnd.randrange(len(angst_tage))]
                    kand = tage_idx[s].get(tag)
                    if kand:
                        i = kand[rnd.randrange(len(kand))]
                        ev.append((s, idx[s][i][0], idx[s][i][4]))
                        break
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

        print(f"  {'Szenario':<44s} {'P(auf) %':>9s} {'n entsch.':>10s} "
              f"{'2,5%-P':>8s} {'97,5%-P':>8s}")
        print("  " + "-" * 92)
        print(f"  {'S0  ECHTE Einstiege':<44s} {q0:9.2f} {n0:10d} "
              f"{'-':>8s} {'-':>8s}")
        ergebnis = {}
        for bez, fn in (("S1  gleichverteilt ueber das ganze Jahr", ziehe_S1),
                        ("S3  gleichverteilt ueber alle F&G<30-Tage", ziehe_S3),
                        ("S2  gleiche Tage, nur Uhrzeit zufaellig", ziehe_S2)):
            qs = []
            for _ in range(ZIEHUNGEN):
                q, _n = quote(idx, zt, fn())
                qs.append(q)
            ergebnis[bez[:2]] = qs
            print(f"  {bez:<44s} {sum(qs)/len(qs):9.2f} {'':>10s} "
                  f"{perzentil(qs, 0.025):8.2f} {perzentil(qs, 0.975):8.2f}")
            sys.stdout.flush()

        print(f"\n  Zerlegung des Unterschieds (Prozentpunkte):")
        m = {k: sum(v) / len(v) for k, v in ergebnis.items()}
        print(f"    F&G-Tagesfilter        S1 -> S3 : {m['S3']-m['S1']:+6.2f} pp")
        print(f"    Auswahl WELCHER Angsttage S3 -> S2 : {m['S2']-m['S3']:+6.2f} pp")
        print(f"    Uhrzeitwahl            S2 -> S0 : {q0-m['S2']:+6.2f} pp")
        print(f"    gesamt                 S1 -> S0 : {q0-m['S1']:+6.2f} pp")

        # ---------- Block-Bootstrap: KI fuer die ECHTE Quote ----------
        aus = []
        for s, t, p in echt:
            ks = idx.get(s)
            if not ks:
                continue
            r = rennen(ks, zt[s], t, p, AUF, AB)
            if r != "keine":
                aus.append((t // TAG_MS, 1 if r == "auf" else 0))
        nach_tag = {}
        for tag, w in aus:
            nach_tag.setdefault(tag, []).append(w)
        tage = list(nach_tag)
        qs = []
        for _ in range(BOOT):
            auf = ges = 0
            for _i in range(len(tage)):
                for w in nach_tag[tage[rnd.randrange(len(tage))]]:
                    auf += w
                    ges += 1
            if ges:
                qs.append(auf / ges * 100)
        print(f"\n  Block-Bootstrap ueber {len(tage)} Kalendertage, {BOOT} Ziehungen:")
        print(f"    P(auf) echt = {q0:.2f} %   95%-KI = "
              f"[{perzentil(qs, 0.025):.2f} ; {perzentil(qs, 0.975):.2f}] %")
        print(f"    Zufallsniveau S2 (Mittel) = {m['S2']:.2f} %  -> "
              f"{'INNERHALB des KI' if perzentil(qs,0.025) <= m['S2'] <= perzentil(qs,0.975) else 'AUSSERHALB des KI'}")
        sys.stdout.flush()

        # ---------- Block-Bootstrap: KI fuer EV(R)-Differenz Stop 2,0 vs 5,0 ----------
        laeufe = {}
        for sl in (2.0, 5.0):
            Lx = LaufMess(NEUE_LEITER, "x", breakeven=True, stop_loss_pct=sl)
            Lx.laufe(daten, fg)
            d = {}
            for t in Lx.trades:
                d.setdefault(t["eintritt"] // TAG_MS, []).append(t)
            laeufe[sl] = d
        alle_t = sorted(set(laeufe[2.0]) | set(laeufe[5.0]))
        roh = {sl: kennzahlen([t for v in laeufe[sl].values() for t in v])["ev_r"]
               for sl in (2.0, 5.0)}
        diffs = []
        for _ in range(BOOT):
            wahl = [alle_t[rnd.randrange(len(alle_t))] for _i in range(len(alle_t))]
            a = [t for tag in wahl for t in laeufe[2.0].get(tag, [])]
            b = [t for tag in wahl for t in laeufe[5.0].get(tag, [])]
            if len(a) < 30 or len(b) < 30:
                continue
            diffs.append(kennzahlen(b)["ev_r"] - kennzahlen(a)["ev_r"])
        print(f"\n  Block-Bootstrap EV(R)-Differenz Stop 5,0 % minus Stop 2,0 %:")
        print(f"    Punktschaetzer = {roh[5.0]-roh[2.0]:+.4f} R  "
              f"(EV(R) 2,0 % = {roh[2.0]:+.4f} / 5,0 % = {roh[5.0]:+.4f})")
        print(f"    95%-KI = [{perzentil(diffs, 0.025):+.4f} ; "
              f"{perzentil(diffs, 0.975):+.4f}] R  aus {len(diffs)} Ziehungen")
        null_drin = perzentil(diffs, 0.025) <= 0 <= perzentil(diffs, 0.975)
        print(f"    Null im Intervall: {'JA - Unterschied nicht gesichert' if null_drin else 'NEIN - Unterschied gesichert'}")
        print(f"\n  Zum Vergleich: bis Break-even fehlen ab Stop 5,0 % noch "
              f"{-roh[5.0]:+.4f} R")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
