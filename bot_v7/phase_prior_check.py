# -*- coding: utf-8 -*-
"""
phase_prior_check.py - Letzter vorregistrierter Makro-Test
============================================================
Nach dem Scheitern der kNN-Aehnlichkeit (30d + 90d) bleibt eine
letzte, VORAB festgelegte Frage: Traegt die PHASE selbst Signal -
out-of-sample, ohne Lookahead?

Methode (Walk-Forward, expandierendes Fenster):
  Fuer jeden Tag t (ab Warmup):
    - Nimm alle Tage s <= t - 30 mit derselben Phase wie t.
    - Prior = deren durchschnittlicher Forward-Return (nur Vergangenheit!).
    - Vorhersage: Richtung des Priors. Vergleich mit echtem Outcome von t.
  Mindestens 60 historische Phasen-Tage noetig, sonst keine Vorhersage.

Bewertung: Trefferquote vs. Baseline, Geld-Frage (Realverlauf wenn
Prior negativ vs. positiv), je Phase und je Horizont (30d + 90d).

DANACH IST SCHLUSS: Besteht der Test nicht, wird die Makro-Schicht
geparkt (nur noch Kontext-Anzeige, keine Trading-Naehe). Kein weiteres
Parameter-Drehen - Overfitting-Schutz.

Nutzung (V6-Hauptordner, Bot darf laufen - liest nur):
    python phase_prior_check.py
"""
import os
import sys
import json
from collections import defaultdict

GAP_DAYS = 30
WARMUP = 365
MIN_HISTORY = 60


def run(days, key_out):
    # Vorbereitung: kumulative Phasen-Statistik waehrend des Durchlaufs
    # (expandierendes Fenster, Eintrag erst GAP_DAYS spaeter sichtbar)
    evaluated = hits = ups = 0
    money = {"go": [], "avoid": []}
    per_phase = defaultdict(lambda: [0, 0, []])  # phase -> [hits, n, reals]
    hist = defaultdict(list)  # phase -> [fwd, ...] (nur sichtbare Vergangenheit)
    pending = []              # (freigabe_index, phase, fwd)

    for i, d in enumerate(days):
        # Eintraege freigeben, deren Outcome-Fenster abgeschlossen ist
        while pending and pending[0][0] <= i:
            _, ph, fw = pending.pop(0)
            hist[ph].append(fw)

        out = (d.get("outcome") or {}).get(key_out)
        ph_t = d.get("phase", "?")
        if out is not None:
            # Dieser Tag wird erst nach GAP_DAYS + Horizont sichtbar
            horizon = int(key_out.split("_")[1].rstrip("d"))
            pending.append((i + GAP_DAYS + horizon, ph_t, out))

        if i < WARMUP or out is None:
            continue
        past = hist.get(ph_t, [])
        if len(past) < MIN_HISTORY:
            continue
        prior = sum(past) / len(past)

        evaluated += 1
        actual_up = out > 0
        pred_up = prior > 0
        ups += int(actual_up)
        hit = pred_up == actual_up
        hits += int(hit)
        money["go" if pred_up else "avoid"].append(out)
        st = per_phase[ph_t]
        st[0] += int(hit)
        st[1] += 1
        st[2].append(out)

    return evaluated, hits, ups, money, per_phase


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "data_store", "situation_history.json")
    if not os.path.exists(path):
        path = os.path.join(base, "situation_history.json")
    if not os.path.exists(path):
        print("FEHLER: situation_history.json nicht gefunden.")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        days = json.load(f).get("days", [])
    print(f"Historie: {path} ({len(days)} Tage)")

    for key_out in ("fwd_30d", "fwd_90d"):
        evaluated, hits, ups, money, per_phase = run(days, key_out)
        if not evaluated:
            print(f"\n[{key_out}] zu wenig Daten.")
            continue
        base_up = ups / evaluated
        baseline = max(base_up, 1 - base_up)
        print()
        print("=" * 62)
        print(f"PHASEN-PRIOR WALK-FORWARD ({key_out}, Gap {GAP_DAYS}d, "
              f"min. {MIN_HISTORY} Historie-Tage)")
        print("=" * 62)
        print(f"Bewertete Tage:             {evaluated}")
        print(f"Trefferquote Phasen-Prior:  {hits/evaluated*100:.1f}%")
        print(f"Baseline (haeufigste Richtung): {baseline*100:.1f}%")
        go, avoid = money["go"], money["avoid"]
        if go:
            print(f"Prior sagt GO     -> real Oe: "
                  f"{sum(go)/len(go):+6.2f}%  (n={len(go)})")
        if avoid:
            print(f"Prior sagt MEIDEN -> real Oe: "
                  f"{sum(avoid)/len(avoid):+6.2f}%  (n={len(avoid)})")
        if go and avoid:
            spread = sum(go)/len(go) - sum(avoid)/len(avoid)
            print(f"Spread (GO - MEIDEN):        {spread:+6.2f}%  "
                  f"(positiv = Phase traegt Signal)")
        print("Je Phase (Trefferquote | realer Oe-Forward):")
        for ph, (h, n, reals) in sorted(per_phase.items(), key=lambda x: -x[1][1]):
            print(f"  {ph:14s}: {h/n*100:5.1f}% | "
                  f"{sum(reals)/len(reals):+6.1f}%  (n={n})")

    print("\nEINORDNUNG: Positiver Spread auf BEIDEN Horizonten = Phasen-")
    print("Signal existiert out-of-sample -> als Kontext-Schicht behalten.")
    print("Sonst: Makro-Schicht ehrlich parken, zurueck zur Haupt-Roadmap.")


if __name__ == "__main__":
    main()
