# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Strategie-Labor Stufe 2-4: Selbsttests, dann Rueckrechnung M1-M3, K1-K3 (+ K4 Bot) je Kostenniveau.
Ergebnis: labor/ergebnisse/stufe4.json und stufe4.md
Aufruf: python stufe4.py [--nur-selbsttest]
"""
from __future__ import annotations

import copy
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "skripte"))
import backtest as bt  # noqa: E402

KOSTEN = (0.15, 0.20, 0.50, 1.00)
FENSTER = ("2026-08-13", "2026-10-13")
ERG = HIER / "ergebnisse"


def strategien():
    return [bt.M1BTCHalten(), bt.M2Korb(), bt.M3BTC200(), bt.K1Trend(),
            bt.K1Trend(filter_btc200=True, name="K2 Trend + BTC-200-Filter"), bt.K3Rotation()]


def selbsttest(m: bt.Markt, start: str) -> int:
    fehler = 0
    # 1 M1 gegen Formel
    for k in (0.15, 1.0):
        e = bt.simuliere(bt.M1BTCHalten(), m, k, start)
        i0 = m.idx(start)
        # Kaufgebuehr kommt OBENDRAUF: fuer 500 $ wird 500 / (1 + Gebuehr) investiert
        soll = bt.START_KAPITAL / (1 + k / 200) * m.c["BTC"][len(m.datum) - 1] / m.o["BTC"][i0 + 1]
        ok = abs(e.equity[-1] - soll) < 1e-6 * soll
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} M1 bei K={k}: Simulator {e.equity[-1]:.4f} $ = Formel {soll:.4f} $")
    # 2 Zwei-Wege-Kontrolle fuer alle Strategien
    for s in strategien():
        e = bt.simuliere(s, m, 0.5, start)
        ok = abs(e.kontrolle) < 1e-6
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Konto = Summe der Runden: {s.name:32s} Abweichung {e.kontrolle:.2e} $ "
              f"| Endwert {e.equity[-1]:,.2f} $ | Runden {len(e.runden)}")
        if max(e.exposure) > 1.0 + 1e-9:
            fehler += 1
            print(f"  FEHL Hebel: hoechste Investitionsquote {max(e.exposure):.4f}")
    # 3 Kein Blick in die Zukunft: Daten nach Tag t abschneiden darf Ziele bis t nicht aendern
    i0 = m.idx(start)
    for s_proto in (bt.K1Trend(), bt.K3Rotation(), bt.M2Korb()):
        voll = bt.ziele_berechnen(copy.deepcopy(s_proto), m, start)
        for schnitt in (i0 + 400, i0 + 1500, len(m.datum) - 30):
            kurz = bt.Markt(m.datum[:schnitt + 1], {k: v[:schnitt + 1] for k, v in m.o.items()},
                            {k: v[:schnitt + 1] for k, v in m.c.items()})
            teil = bt.ziele_berechnen(copy.deepcopy(s_proto), kurz, start)
            gleich = all(teil.get(i) == voll.get(i) for i in range(i0, schnitt))
            fehler += not gleich
            print(f"  {'OK  ' if gleich else 'FEHL'} kein Blick in die Zukunft: {s_proto.name:32s} Schnitt {m.datum[schnitt]}")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return fehler


def bot_referenz(k: float) -> dict:
    """K4: v6-Runden E7 (13.08.-13.10.) als Tageskurve, nur realisiert, Start 500 $."""
    from runden_lib import lade, runden
    rd = runden(lade(Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")),
                "2026-08-13T13:21:19", "2026-10-14T00:00:00")
    je_tag = defaultdict(float)
    for r in rd:
        je_tag[r["tag"]] += r["brutto"] - k / 200 * (r["kauf_nominal"] + r["verkauf_nominal"])
    tage, eq, e = [], [], bt.START_KAPITAL
    from datetime import date, timedelta
    d = date.fromisoformat(FENSTER[0])
    while d.isoformat() <= FENSTER[1]:
        e += je_tag.get(d.isoformat(), 0.0)
        tage.append(d.isoformat())
        eq.append(e)
        d += timedelta(days=1)
    x = bt.Ergebnis("K4 heutiger Bot (v6 E7)", k, tage, eq, [0.0] * len(eq))
    out = bt.kennzahlen(x)
    out["runden_je_monat"] = round(len(rd) / (len(tage) / 30.44), 1)
    out["hinweis"] = "nur realisierte Runden, Kosten neu gerechnet (brutto - K/2 je Seite)"
    return out


def main():
    m = bt.Markt.laden()
    start = m.datum[200]                      # erster Tag mit BTC-200-Tage-Linie
    print(f"Daten {m.datum[0]} .. {m.datum[-1]}, Rueckrechnung ab {start}\n")
    if selbsttest(m, start):
        sys.exit(1)
    if "--nur-selbsttest" in sys.argv:
        return
    lage = bt.marktlage(m)
    jahre = sorted({d[:4] for d in m.datum if d >= start})
    out = {"start": start, "ende": m.datum[-1], "kosten_niveaus": list(KOSTEN), "ergebnisse": {}, "bot": {}}
    sr_tag = defaultdict(dict)
    r_tag = {}
    for s in strategien():
        ziele = bt.ziele_berechnen(s, m, start)
        out["ergebnisse"][s.name] = {}
        for k in KOSTEN:
            e = bt.simuliere(s, m, k, start, ziele=ziele)
            r = bt.renditen(e.equity)
            r_tag[(s.name, k)] = r
            sr_tag[k][s.name] = (sum(r) / len(r)) / (math.sqrt(sum((x - sum(r) / len(r)) ** 2 for x in r) / (len(r) - 1)))
            res = {"gesamt": bt.kennzahlen(e),
                   "jahre": {j: bt.kennzahlen(e, f"{j}-01-01", f"{j}-12-31").get("rendite_gesamt_pct") for j in jahre},
                   "marktlage": {L: bt.kennzahlen(e, tage_filter=lambda d, L=L: lage.get(d) == L) for L in ("Bulle", "Seitwaerts", "Baer")},
                   "fenster_bot": bt.kennzahlen(e, *FENSTER), "kontrolle_usd": e.kontrolle}
            out["ergebnisse"][s.name][str(k)] = res
            g = res["gesamt"]
            print(f"{s.name:34s} K={k:4.2f}  Jahr {g['rendite_jahr_pct']:7.1f} %  MaxDD {g['max_rueckgang_pct']:6.1f} %  "
                  f"Sharpe {g['sharpe']:5.2f}  Calmar {g['calmar']}  Runden/Mon {g['runden_je_monat']:5.1f}  "
                  f"Kostenanteil {g['kostenanteil_brutto_pct']} %  | 13.08.-13.10.: {res['fenster_bot'].get('rendite_gesamt_pct')} %",
                  flush=True)
    # Deflated Sharpe: Versuche = die drei Kandidaten (Stufe 5 erhoeht die Zahl)
    for k in KOSTEN:
        kand = {n: v for n, v in sr_tag[k].items() if n.startswith("K")}
        for n in kand:
            dsr = bt.deflated_sharpe(r_tag[(n, k)], list(kand.values()))
            out["ergebnisse"][n][str(k)]["deflated_sharpe"] = round(dsr, 3)
    for k in KOSTEN:
        out["bot"][str(k)] = bot_referenz(k)
        b = out["bot"][str(k)]
        print(f"{'K4 heutiger Bot (v6 E7)':34s} K={k:4.2f}  13.08.-13.10.: {b['rendite_gesamt_pct']} %  MaxDD {b['max_rueckgang_pct']} %")
    ERG.mkdir(exist_ok=True)
    (ERG / "stufe4.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("gespeichert:", ERG / "stufe4.json")


if __name__ == "__main__":
    main()
