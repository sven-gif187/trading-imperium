# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
S7-Nachtrag 1 (14.10.2026, vor dem ersten Ergebnis): Zahlenband fuer Erfolgskriterium 3
"Verhalten passt zur Rueckrechnung" (A10-Befund 1, berichte/2026-10-14_advocatus.md).

Rueckrechnung auf den 6 Bitvavo-USDC-Coins, Papier-Kosten je Coin wie im Wettkampf.
Alle 91-Tage-Fenster (Schritt 7 Tage) ab 2018, getrennt nach Marktlage:
  "ueber"  = BTC an >= 50 % der Fenstertage ueber seiner 200-Tage-Linie
  "unter"  = sonst
Band = 10. bis 90. Perzentil von Investitionsquote (Mittel) und Runden je Monat; dazu Rendite und
groesster Rueckgang je Fenster und der Anteil der Fenster, in denen K2/K1 die Messlatte M3 schlagen.
Ausgabe: labor/papier/s7_band.json. Liest nur Labor-Daten.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
LABOR = HIER.parent
sys.path.insert(0, str(LABOR))
sys.path.insert(0, str(HIER))
import backtest as bt  # noqa: E402
from papier_tag import KOSTEN_SEITE, UNI6  # noqa: E402

FENSTER, SCHRITT = 91, 7


def perz(x: list[float], p: float) -> float:
    x = sorted(x)
    return x[min(len(x) - 1, max(0, round(p * (len(x) - 1))))]


def main() -> None:
    alle = list(bt.COINS)
    bt.COINS[:] = UNI6
    bt.DATEN = LABOR / "daten"
    try:
        m = bt.Markt.laden()
        start = m.datum[200]
        erg = {}
        for name, f in {"B K2": lambda: bt.K1Trend(filter_btc200=True), "C K1": bt.K1Trend, "M3": bt.M3BTC200}.items():
            s = f()
            erg[name] = bt.simuliere(s, m, 0.15, start, ziele=bt.ziele_berechnen(s, m, start), kosten_je_coin=KOSTEN_SEITE)
        tage = erg["B K2"].datum
        ueber = {d: bt.btc_ueber_200(m, m.idx(d)) for d in tage}
        out = {"erstellt": "2026-10-14", "fenster_tage": FENSTER, "schritt_tage": SCHRITT,
               "daten_bis": tage[-1], "gruppen": {}}
        sammel: dict[str, dict[str, list]] = {}
        for a in range(0, len(tage) - FENSTER, SCHRITT):
            von, bis = tage[a], tage[a + FENSTER - 1]
            g = "ueber" if sum(ueber[d] for d in tage[a:a + FENSTER]) >= FENSTER / 2 else "unter"
            k3 = bt.kennzahlen(erg["M3"], von, bis)
            for name in ("B K2", "C K1"):
                k = bt.kennzahlen(erg[name], von, bis)
                s = sammel.setdefault(f"{name} | {g}", {"investiert": [], "runden_mon": [], "rendite": [], "mdd": [], "schlaegt_m3": []})
                s["investiert"].append(k["investiert_mittel_pct"])
                s["runden_mon"].append(k["runden_je_monat"])
                s["rendite"].append(k["rendite_gesamt_pct"])
                s["mdd"].append(k["max_rueckgang_pct"])
                s["schlaegt_m3"].append(k["rendite_gesamt_pct"] > k3["rendite_gesamt_pct"])
        for key, s in sammel.items():
            out["gruppen"][key] = {
                "fenster": len(s["investiert"]),
                "investiert_pct_band_10_90": [perz(s["investiert"], .1), perz(s["investiert"], .9)],
                "investiert_pct_median": st.median(s["investiert"]),
                "runden_je_monat_band_10_90": [perz(s["runden_mon"], .1), perz(s["runden_mon"], .9)],
                "runden_je_monat_median": st.median(s["runden_mon"]),
                "rendite_91t_pct_band_10_90": [perz(s["rendite"], .1), perz(s["rendite"], .9)],
                "rendite_91t_pct_median": st.median(s["rendite"]),
                "max_rueckgang_91t_pct_p10": perz(s["mdd"], .1),
                "anteil_fenster_besser_als_m3_pct": round(100 * sum(s["schlaegt_m3"]) / len(s["schlaegt_m3"]), 1),
            }
        (HIER / "s7_band.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        for k, v in out["gruppen"].items():
            print(f"{k:16s} n {v['fenster']:3d} | investiert {v['investiert_pct_band_10_90']} (Median {v['investiert_pct_median']}) | "
                  f"Runden/Mon {v['runden_je_monat_band_10_90']} (Median {v['runden_je_monat_median']}) | "
                  f"Rendite 91 T {v['rendite_91t_pct_band_10_90']} | MaxDD p10 {v['max_rueckgang_91t_pct_p10']} | besser als M3 {v['anteil_fenster_besser_als_m3_pct']} %")
    finally:
        bt.COINS[:] = alle


if __name__ == "__main__":
    main()
