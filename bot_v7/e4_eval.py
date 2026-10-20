# -*- coding: utf-8 -*-
"""
e4_eval.py - EPOCHEN-AUSWERTUNG E4 (Stop-Loss 2.5%)
====================================================
Vorregistrierte Kernfrage: War der auf 2.5% gestraffte Stop-Loss
eine RETTUNG (Kurs fiel nach dem Ausstieg weiter -> Stop hat Geld
gerettet) oder VORSCHNELL (Kurs erholte sich sofort -> Stop hat
eine Erholung verschenkt)?

Methode: Fuer jeden STOP-LOSS-Verkauf seit E4-Start (01.07. 15:26)
wird der Kursverlauf der naechsten 48 Stunden aus dem Kerzen-Cache
geholt und klassifiziert:
  RETTUNG:     Kurs fiel danach nochmal >= 2% unter den Exit-Preis
  VORSCHNELL:  Kurs stieg binnen 48h >= 3% ueber den Exit-Preis
               (also zurueck ueber den ungefaehren Einstand),
               ohne vorher nochmal deutlich zu fallen
  GEMISCHT:    beides oder keins davon eindeutig

GRENZEN (ehrlich): Ohne exakten Einstandspreis je Stop ist die
Erholungs-Schwelle eine Naeherung (Exit + 3% ~ Einstand + 0.5%).
Stop-Outs juenger als 48h werden mit verkuerztem Fenster bewertet
und markiert.

Nutzung (V6-Hauptordner, Bot darf laufen - liest nur):
    python e4_eval.py
Braucht: data_store/order_history.json + data_store/charts/*_1h.csv
"""
import os
import csv
import json
import sys
from datetime import datetime

E4_START = datetime(2026, 7, 1, 15, 26).timestamp()
FENSTER_H = 48
RETTUNG_PCT = 2.0     # weiter gefallen um >= 2%  -> Stop war richtig
ERHOLUNG_PCT = 3.0    # erholt um >= 3%           -> Stop war vorschnell


def find_base():
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(here, "data_store", "order_history.json")):
        return here
    print("FEHLER: Skript in den V6-Hauptordner legen (data_store fehlt).")
    sys.exit(1)


def load_candles(base, symbol):
    safe = symbol.replace("/", "")
    for cand in (safe, safe.replace("USDC", "USDT"), safe.replace("USDT", "USDC")):
        p = os.path.join(base, "data_store", "charts", f"{cand}_1h.csv")
        if os.path.exists(p):
            rows = []
            with open(p, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append((int(r["open_time"]) / 1000, float(r["high"]),
                                 float(r["low"]), float(r["close"])))
            rows.sort()
            return rows
    return []


def main():
    base = find_base()
    with open(os.path.join(base, "data_store", "order_history.json"),
              encoding="utf-8") as f:
        oh = json.load(f)

    stops = [o for o in oh
             if o.get("side") == "SELL" and o.get("status") == "filled"
             and "STOP-LOSS" in (o.get("reason") or "").upper()
             and float(o.get("created_at", 0)) >= E4_START
             and (o.get("fill_price") or 0) > 0]
    stops.sort(key=lambda o: o["created_at"])

    print("=" * 66)
    print("E4-AUSWERTUNG: Stop-Loss 2.5% (seit 01.07. 15:26)")
    print("=" * 66)
    print(f"Stop-Outs unter E4: {len(stops)}")
    if len(stops) < 5:
        print("Unter 5 Stop-Outs - vorregistrierte Schwelle nicht erreicht.")
        print("Auswertung verschoben, Epoche laeuft weiter. Geduld.")
        return

    cache = {}
    ergebnisse = []
    print(f"\n{'Zeit':16s} {'Coin':6s} {'Exit':>10s} {'Tief48h':>8s} "
          f"{'Hoch48h':>8s}  Urteil")
    print("-" * 66)
    for o in stops:
        sym = o["symbol"]
        exit_p = float(o["fill_price"])
        t0 = float(o["created_at"])
        if sym not in cache:
            cache[sym] = load_candles(base, sym)
        candles = [c for c in cache[sym] if t0 <= c[0] <= t0 + FENSTER_H * 3600]
        zeit = datetime.fromtimestamp(t0).strftime("%d.%m %H:%M")
        coin = sym.split("/")[0]
        if len(candles) < 3:
            ende = (datetime.fromtimestamp(cache[sym][-1][0]).strftime("%d.%m %H:%M")
                    if cache[sym] else "LEER")
            print(f"{zeit:16s} {coin:6s} {exit_p:>10.4g} {'--':>8s} {'--':>8s}"
                  f"  AUSSTEHEND (Cache endet {ende})")
            continue
        tief = min(c[2] for c in candles)
        hoch = max(c[1] for c in candles)
        fiel = (tief / exit_p - 1) * 100
        stieg = (hoch / exit_p - 1) * 100
        kurz = " (Fenster<48h)" if candles[-1][0] - t0 < (FENSTER_H - 2) * 3600 else ""

        if fiel <= -RETTUNG_PCT and stieg < ERHOLUNG_PCT:
            urteil = "RETTUNG"
        elif stieg >= ERHOLUNG_PCT and fiel > -1.0:
            urteil = "VORSCHNELL"
        elif fiel <= -RETTUNG_PCT and stieg >= ERHOLUNG_PCT:
            # beides passiert: was kam ZUERST?
            erst_tief = next(c[0] for c in candles if c[2] <= exit_p * (1 - RETTUNG_PCT / 100))
            erst_hoch = next(c[0] for c in candles if c[1] >= exit_p * (1 + ERHOLUNG_PCT / 100))
            urteil = "RETTUNG (erst Fall)" if erst_tief <= erst_hoch else "VORSCHNELL (erst Erholung)"
        else:
            urteil = "GEMISCHT"
        ergebnisse.append((urteil, fiel, stieg, coin))
        print(f"{zeit:16s} {coin:6s} {exit_p:>10.4g} {fiel:>+7.1f}% {stieg:>+7.1f}%"
              f"  {urteil}{kurz}")

    if not ergebnisse:
        print("\nKeine bewertbaren Stop-Outs (Kerzen-Cache zu alt?).")
        print("Tipp: Im Bot den CHARTS-Tab oeffnen, damit frische Kerzen geladen werden.")
        return

    n = len(ergebnisse)
    rett = sum(1 for u, *_ in ergebnisse if u.startswith("RETTUNG"))
    vors = sum(1 for u, *_ in ergebnisse if u.startswith("VORSCHNELL"))
    gem = n - rett - vors
    print("-" * 66)
    print(f"BILANZ: {rett}x RETTUNG | {vors}x VORSCHNELL | {gem}x GEMISCHT  (n={n})")
    o_fiel = sum(f for _, f, _, _ in ergebnisse) / n
    o_stieg = sum(s for _, _, s, _ in ergebnisse) / n
    print(f"Oe Kursverlauf nach Stop: Tief {o_fiel:+.1f}% | Hoch {o_stieg:+.1f}%")

    print("\nVORREGISTRIERTES URTEIL:")
    if rett > vors:
        print("  -> Mehrheit RETTUNG: Der 2.5%-Stop hat netto Geld gerettet.")
        print("     E4 BESTANDEN - Stop bleibt. Naechste Epoche: E6 (Coin-Stops).")
    elif vors > rett:
        print("  -> Mehrheit VORSCHNELL: Der Stop wirft uns aus Erholungen.")
        print("     E4-Befund negativ - Datenbasis fuer E6 (per-Coin weiter/enger)")
        print("     wird wichtiger. KEIN sofortiges Zurueckdrehen ohne Analyse.")
    else:
        print("  -> Unentschieden: mehr Stop-Outs abwarten, Epoche laeuft weiter.")
    print("\nHinweis: XRP-Stops gesondert betrachten - XRP ist E6-Entfernungs-")
    print("Kandidat; seine Stops sagen wenig ueber die Stop-Weite der anderen.")


if __name__ == "__main__":
    main()
