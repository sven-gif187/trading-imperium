# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Schattenbuch Kosten (W3 / A6): dieselben Runden unter jedem Gebuehrenplan.

Je Runde: netto_plan = brutto - f_kauf * Kauf-Nominal - f_verkauf * Verkauf-Nominal
(brutto enthaelt den Schlupf des Papier-Bots bereits; Zusatzschlupf je Boerse
siehe orderbuch_kosten.py). Zusaetzlich je Plan der 95 %-Bereich des mittleren
Netto je Runde per Block-Bootstrap nach Kalendertagen (Haltezeiten ueberlappen,
Skepsis-Regel 5) - damit sichtbar ist, ob eine Zahl belegt oder nur moeglich ist.

Gebuehren: Primaerquellen, abgerufen 14.10.2026 (Quelle je Plan im Ergebnis).
Aufruf: python kosten_schatten.py <bot-ordner> <von ISO> <bis ISO> [--json ziel.json]
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runden_lib import lade, runden  # noqa: E402

# (Name, Kauf %, Verkauf %, Quelle/Konfidenz)
PLAENE = [
    ("Bybit EU seit 05.10. (heute)", 0.25, 0.25, "bybit.eu Trading-Fee-Structure, 05.10.2026, SICHER"),
    ("OKX EEA mit X-Perps, Taker/Taker", 0.10, 0.10, "okx.com/en-eu Hilfe, 03.09.2026, SICHER"),
    ("OKX EEA mit X-Perps, Maker-Kauf", 0.08, 0.10, "dto., Fuellquote offen"),
    ("OKX EEA ohne X-Perps, Taker/Taker", 0.35, 0.35, "dto., SICHER"),
    ("Bitvavo USDC-Maerkte, Taker/Taker", 0.05, 0.05, "bitvavo.com/en/fees Kategorie B, SICHER"),
    ("Bitvavo EUR-Maerkte, Taker/Taker", 0.25, 0.25, "bitvavo.com/en/fees Kategorie A, SICHER"),
    ("Gate EU VIP 0", 0.10, 0.10, "gate.com/en-eu/fee, SICHER"),
    ("Kraken Pro Stufe 3 (ab 10k $/30 T)", 0.38, 0.38, "kraken.com fee-schedule, SICHER"),
    ("Kraken Pro Stufe 1", 0.80, 0.80, "dto., SICHER"),
    ("Coinbase Advanced (ungeprueft)", 0.60, 0.60, "nur hinter Anmeldung, WAHRSCHEINLICH"),
]


def bootstrap(werte_je_tag: dict[str, list[float]], n: int = 10000, seed: int = 7) -> tuple[float, float]:
    tage = list(werte_je_tag)
    rnd = random.Random(seed)
    mittel = []
    for _ in range(n):
        stich = [w for t in (rnd.choice(tage) for _ in tage) for w in werte_je_tag[t]]
        mittel.append(sum(stich) / len(stich))
    mittel.sort()
    return mittel[int(0.025 * n)], mittel[int(0.975 * n)]


def auswerten(rd: list[dict]) -> dict:
    n = len(rd)
    kn = sum(r["kauf_nominal"] for r in rd)
    vn = sum(r["verkauf_nominal"] for r in rd)
    brutto = sum(r["brutto"] for r in rd)
    out = {"runden": n, "tage": len({r["tag"] for r in rd}), "brutto_usd": round(brutto, 2),
           "kauf_nominal": round(kn, 2), "verkauf_nominal": round(vn, 2),
           "breakeven_gebuehr_je_seite_pct": round(brutto / (kn + vn) * 100, 4), "plaene": []}
    # Gegenprobe: tatsaechlich gebuchte Gebuehren
    out["ist_gebuehren_usd"] = round(sum(r["kauf_fee"] + r["verkauf_fee"] for r in rd), 2)
    out["ist_netto_usd"] = round(sum(r["netto"] for r in rd), 2)
    plaene = [("BRUTTO (ohne Gebuehr)", 0.0, 0.0, "Kasse")] + PLAENE
    for name, fk, fv, quelle in plaene:
        je = [(r["brutto"] - fk / 100 * r["kauf_nominal"] - fv / 100 * r["verkauf_nominal"])
              / r["kauf_nominal"] * 100 for r in rd]
        usd = sum(r["brutto"] - fk / 100 * r["kauf_nominal"] - fv / 100 * r["verkauf_nominal"] for r in rd)
        tage = {}
        for r, w in zip(rd, je):
            tage.setdefault(r["tag"], []).append(w)
        lo, hi = bootstrap(tage)
        m, s = st.mean(je), st.stdev(je)
        out["plaene"].append({"plan": name, "kauf_pct": fk, "verkauf_pct": fv, "quelle": quelle,
                              "netto_usd": round(usd, 2), "je_runde_pct": round(m, 3),
                              "t_einfach": round(m / (s / n ** 0.5), 2),
                              "bereich95_tage_pct": [round(lo, 3), round(hi, 3)],
                              "belegt_ueber_null": lo > 0})
    return out


if __name__ == "__main__":
    bot, von, bis = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    rd = runden(lade(bot), von, bis)
    e = auswerten(rd)
    print(f"{bot.name}: {e['runden']} Runden an {e['tage']} Tagen | brutto {e['brutto_usd']:+.2f} $ | "
          f"ist: Gebuehren {e['ist_gebuehren_usd']} $, netto {e['ist_netto_usd']:+.2f} $ | "
          f"Break-even je Seite {e['breakeven_gebuehr_je_seite_pct']} %")
    print(f"{'Plan':38s} {'Kauf':>5s} {'Verk':>5s} {'netto $':>9s} {'je Runde':>9s} {'t':>6s}  95%-Bereich (Tage-Bootstrap)")
    for p in e["plaene"]:
        print(f"{p['plan']:38s} {p['kauf_pct']:5.2f} {p['verkauf_pct']:5.2f} {p['netto_usd']:+9.2f} "
              f"{p['je_runde_pct']:+8.3f}% {p['t_einfach']:6.2f}  [{p['bereich95_tage_pct'][0]:+.3f} ; "
              f"{p['bereich95_tage_pct'][1]:+.3f}] {'BELEGT' if p['belegt_ueber_null'] else ''}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(e, indent=1, ensure_ascii=False),
                                                                encoding="utf-8")
