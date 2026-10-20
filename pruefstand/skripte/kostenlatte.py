# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Kostenlatte K je Zielboerse und die daraus folgenden Ausstiegsgrenzen (Abschnitt 3.1/3.9).

  K           = gebuehr_kauf + gebuehr_verkauf + 2 * schlupf_je_seite (gemessen, Mittel BTC/ETH/SOL)
  Puffer      = K + 0,045            (Regel aus v7 exit_rules.py: BREAKEVEN_MARGE_PCT)
  Trail-Start = ((1 + K/100) / (1 - Trail/100) - 1) * 100 + 0,05   (Patch 45, Trail 1,0 %)
  I1 Soll     = K + 0,10 ; I2 Soll = Nulllinie + 0,10   (Masterprompt 3.9, Startwerte VERMUTUNG)
  Break-even-Trefferquote bei heutigem Ø Gewinn/Verlust brutto (aus 136 Runden)

Liest berichte/<datum>_orderbuch.json. Aufruf: python kostenlatte.py <orderbuch.json>
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TRAIL = 1.0
# (Anzeige, Schluessel im Orderbuch-JSON, Kauf %, Verkauf %, Symbole)
PLAENE = [
    ("Bybit EU (heute)", "bybit_eu", 0.25, 0.25, ("BTC/USDC", "ETH/USDC", "SOL/USDC")),
    ("Bitvavo USDC-Maerkte", "bitvavo", 0.05, 0.05, ("BTC/USDC", "ETH/USDC", "SOL/USDC")),
    ("Bitvavo EUR-Maerkte", "bitvavo", 0.25, 0.25, ("BTC/EUR", "ETH/EUR", "SOL/EUR")),
    ("OKX EEA mit X-Perps", "okx_eea", 0.10, 0.10, ("BTC/USDC", "ETH/USDC", "SOL/USDC")),
    ("OKX EEA ohne X-Perps", "okx_eea", 0.35, 0.35, ("BTC/USDC", "ETH/USDC", "SOL/USDC")),
    ("Gate EU VIP 0", "gate", 0.10, 0.10, ("BTC/USDC", "ETH/USDC", "SOL/USDC")),
    ("Kraken Pro Stufe 3", "kraken", 0.38, 0.38, ("BTC/USDC", "ETH/USDC", "SOL/USDC")),
]


def nulllinie(k: float) -> float:
    return ((1 + k / 100) / (1 - TRAIL / 100) - 1) * 100


if __name__ == "__main__":
    ob = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["ergebnis"]
    print(f"{'Plan':24s} {'Geb.':>5s} {'Schlupf/S':>9s} {'K':>6s} {'Puffer':>7s} {'Trail-Start':>11s}  Hinweis")
    zeilen = []
    for name, key, fk, fv, syms in PLAENE:
        b = ob.get(key, {})
        s = [b.get(x, {}).get("schlupf_161_pct") for x in syms]
        gueltig = [x for x in s if x is not None]
        fehlt = [x for x, v in zip(syms, s) if v is None]
        schlupf = sum(gueltig) / len(gueltig) if gueltig else None
        k = fk + fv + 2 * (schlupf or 0)
        z = {"plan": name, "gebuehr_runde": fk + fv, "schlupf_je_seite": None if schlupf is None else round(schlupf, 4),
             "K": round(k, 3), "puffer": round(k + 0.045, 3), "trail_start": round(nulllinie(k) + 0.05, 2),
             "fehlende_maerkte": fehlt}
        zeilen.append(z)
        hinweis = ("Schlupf nicht gemessen" if schlupf is None else "") + (f" fehlt: {fehlt}" if fehlt else "")
        print(f"{name:24s} {fk + fv:5.2f} {'-' if schlupf is None else f'{schlupf:.4f}':>9s} {k:6.3f} "
              f"{k + 0.045:7.3f} {nulllinie(k) + 0.05:11.2f}  {hinweis}")
    Path(sys.argv[1]).with_name(Path(sys.argv[1]).name.replace("orderbuch", "kostenlatte")).write_text(
        json.dumps(zeilen, indent=1, ensure_ascii=False), encoding="utf-8")
