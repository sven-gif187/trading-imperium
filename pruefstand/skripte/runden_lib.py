# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Runden aus trades_v5.json als Kassenrechnung (Grundlage fuer W3/W4, A2/A3/A6).

Zuordnung: Verkauf gehoert zum offenen Kauf derselben Muenze (FIFO, Nachkaeufe
werden zusammengefasst). Bedeutung von Kauf-"amount" wird je Kauf erkannt:
  - v6 bis E8: amount = Mittelabfluss MIT Gebuehr
  - v7 seit 11.09., v6 ab E9: amount = qty * Kurs OHNE Gebuehr
Verkaufs-"amount" ist immer qty * Kurs (brutto), Gebuehr getrennt.

Geprueft 14.10.2026 (berichtigt nach A5): v6 Verkaeufe ab 13.08.2026 13:21:19 UTC bis 13.10. ->
136 Runden, brutto +75,51 $, Gebuehren 109,62 $, netto -34,11 $. Der Bericht v6 nannte -43,13 $ -
er hatte denselben Fehler (Verkaufsgebuehr bei 21 Signal-Verkaeufen doppelt). Gebucht -88,89 $
= Kasse minus alle 136 Kaufgebuehren (54,78 $): Befund 42 betraf ALLE Wege.
v7 15 Runden netto -13,70 $ = gebucht.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def _f(x) -> float:
    try:
        return float(x or 0.0)
    except (TypeError, ValueError):
        return 0.0


def lade(bot: Path) -> list[dict]:
    rows = json.loads((Path(bot) / "data_store" / "trades_v5.json").read_text(encoding="utf-8"))
    return sorted(rows, key=lambda r: r["time"])


def runden(rows: list[dict], von: str = "", bis: str = "9999") -> list[dict]:
    offen: dict[str, list] = defaultdict(list)
    aus = []
    for r in rows:
        typ = str(r.get("type", "")).upper()
        if typ == "BUY":
            offen[r["coin"]].append(r)
        elif typ == "SELL" and offen[r["coin"]]:
            kaeufe = offen.pop(r["coin"])
            if not (von <= r["time"] < bis):
                continue
            k_abfluss = k_fee = k_nominal = 0.0
            for k in kaeufe:
                a, fe = _f(k.get("amount")), _f(k.get("fee"))
                nominal = _f(k.get("qty")) * _f(k.get("price"))
                ohne = abs(a - nominal) <= max(0.01, fe * 0.2)
                k_abfluss += a + (fe if ohne else 0.0)
                k_fee += fe
                k_nominal += nominal
            v_amt, v_fee = _f(r.get("amount")), _f(r.get("fee"))
            # [14.10.2026, Befund A5] Verkaufs-"amount" hat zwei Bedeutungen:
            #   exit_monitor:            amount = qty * Kurs (brutto), Gebuehr getrennt
            #   execute_approved_trade:  amount = qty * Kurs - Gebuehr (netto, engine.py filled_cost)
            # Die erste Fassung zog bei den 21 Signal-Verkaeufen in E7 die Gebuehr doppelt ab (9,02 $).
            v_nominal = _f(r.get("qty")) * _f(r.get("price"))
            if v_nominal > 0 and abs(v_amt - (v_nominal - v_fee)) <= 0.01 and abs(v_amt - v_nominal) > 0.01:
                v_amt = v_nominal                     # auf brutto vereinheitlichen
            if k_abfluss <= 0 or v_amt <= 0:
                continue
            netto = (v_amt - v_fee) - k_abfluss
            aus.append({
                "t": r["time"], "tag": r["time"][:10], "kauf_t": kaeufe[0]["time"], "coin": r["coin"],
                "n_kaeufe": len(kaeufe), "kauf_nominal": k_nominal, "verkauf_nominal": v_amt,
                "kauf_fee": k_fee, "verkauf_fee": v_fee, "kauf_abfluss": k_abfluss,
                "brutto": v_amt - k_nominal, "netto": netto,
                "gebucht": None if r.get("pnl") is None else _f(r.get("pnl")),
                "ausstieg": r.get("strategy"), "kaufweg": kaeufe[0].get("strategy"),
            })
    return aus
