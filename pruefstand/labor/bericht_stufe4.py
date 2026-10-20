# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""Stufe 4: Tabellen aus ergebnisse/stufe4.json als Markdown (ergebnisse/stufe4.md)."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = Path(__file__).resolve().parent / "ergebnisse"
d = json.loads((E / "stufe4.json").read_text(encoding="utf-8"))
z = []
z.append(f"# Strategie-Labor · Stufe 4 · Rückrechnung {d['start']} bis {d['ende']}\n")
z.append("Signal am Tagesschluss, Ausführung zum nächsten Eröffnungskurs, Kosten je Runde K (je Seite K/2), kein Hebel, Start 500 $. "
         "12 heute existierende Coins (Überlebenden-Verzerrung!).\n")
for k in ("0.15", "0.5", "1.0"):
    z.append(f"\n## Kosten K = {k} % je Runde\n")
    z.append("| Strategie | Rendite/Jahr | größter Rückgang | Sharpe | Sortino | Calmar | Runden/Monat | Ø Haltedauer (T) | im Markt | Ø investiert | Treffer | Kostenanteil am Brutto | Deflated Sharpe |")
    z.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, je in d["ergebnisse"].items():
        g = je[k]["gesamt"]
        z.append(f"| {name} | {g['rendite_jahr_pct']} % | {g['max_rueckgang_pct']} % | {g['sharpe']} | {g['sortino']} | {g['calmar']} | "
                 f"{g['runden_je_monat']} | {g['haltedauer_tage']} | {g['zeit_im_markt_pct']} % | {g['investiert_mittel_pct']} % | "
                 f"{g['trefferquote_pct']} % | {g['kostenanteil_brutto_pct']} % | {je[k].get('deflated_sharpe', '–')} |")
z.append("\n## Rendite je Kalenderjahr (K = 0,15 %)\n")
jahre = list(next(iter(d["ergebnisse"].values()))["0.15"]["jahre"])
z.append("| Strategie | " + " | ".join(jahre) + " |")
z.append("|---|" + "---|" * len(jahre))
for name, je in d["ergebnisse"].items():
    z.append(f"| {name} | " + " | ".join(f"{je['0.15']['jahre'][j]} %" if je['0.15']['jahre'][j] is not None else "–" for j in jahre) + " |")
z.append("\n## Je Marktlage (BTC: Schluss vs 200-Tage-Linie und deren Steigung, ex ante), K = 0,15 %\n")
z.append("| Strategie | Bulle: Rendite/Jahr · Sharpe | Seitwärts | Bär |")
z.append("|---|---|---|---|")
for name, je in d["ergebnisse"].items():
    ml = je["0.15"]["marktlage"]
    z.append(f"| {name} | " + " | ".join(f"{ml[L].get('rendite_jahr_pct')} % · {ml[L].get('sharpe')} ({ml[L].get('tage')} T)" for L in ("Bulle", "Seitwaerts", "Baer")) + " |")
z.append("\n## Direkter Vergleich 13.08.–13.10.2026 (Zeitraum des Bot-Berichts)\n")
z.append("| Strategie | K 0,15 | K 0,50 | K 1,00 |")
z.append("|---|---|---|---|")
for name, je in d["ergebnisse"].items():
    z.append(f"| {name} | " + " | ".join(f"{je[k]['fenster_bot'].get('rendite_gesamt_pct')} %" for k in ("0.15", "0.5", "1.0")) + " |")
z.append("| K4 heutiger Bot (v6 E7, nur realisiert, 500 $) | " + " | ".join(f"{d['bot'][k]['rendite_gesamt_pct']} %" for k in ("0.15", "0.5", "1.0")) + " |")
(E / "stufe4.md").write_text("\n".join(z) + "\n", encoding="utf-8")
print("\n".join(z))
