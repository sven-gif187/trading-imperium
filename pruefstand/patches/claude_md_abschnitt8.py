# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
CLAUDE.md Abschnitt 8 (Zahlen, die man kennen muss) auf Bitvavo umstellen - Freigabe Sven 14.10.2026 (Z1).
Alte Latte bleibt ausdruecklich fuer alte Epochen gueltig. Aufruf: python claude_md_abschnitt8.py v6|v7 --pruefen|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "ZIELBOERSE BITVAVO 14.10.2026"
ALT = ("| Zielbörse | Bybit EU (MiCA), Taker **0,25 %** je Seite |\n"
       "| Kosten je Runde (K-BASIS) | **0,505 %** — nie aus `ccxt` holen, immer diese Konstante |\n")
ALT_Q = "| Datenquelle | Binance (nur Kurse), gehandelt wird bei Bybit EU |\n"


def neu(epoche: str) -> tuple[str, str]:
    a = (f"| Zielbörse | **Bitvavo, USDC-Märkte** (MiCA, AFM), **0,05 %** je Seite — seit {epoche} (14.10.2026, Entscheidung Sven). Vorher Bybit EU 0,25 % |\n"
         f"| Kosten je Runde (K-BASIS) | **0,150 %** ab {epoche} (0,10 Gebühr + 0,05 Schlupf, Bitvavo-Stichprobe) — **für ältere Epochen gilt weiter 0,505 %**. Nie aus `ccxt` holen |\n"
         f"| Herleitung | `pruefstand/berichte/2026-10-14_zielboerse.md`, `pruefstand/gebuehren.json` [{MARKE}] |\n")
    q = "| Datenquelle | Binance (nur Kurse), Zielbörse Bitvavo USDC (Kursabstand < 0,01 %, gemessen 14.10.) |\n"
    return a, q


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    inst = json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]
    a, q = neu("E10" if name == "v6" else "L9")
    main(Path(inst["pfad"]), [Ersetzung("CLAUDE.md", ALT, a), Ersetzung("CLAUDE.md", ALT_Q, q)], MARKE,
         f"CLAUDE.md Abschnitt 8 {name}")
