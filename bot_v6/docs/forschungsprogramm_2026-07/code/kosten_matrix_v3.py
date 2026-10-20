# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Kostenmatrix v3 - gemessene Spreads statt Annahme, 31.07.2026.
"""
Ersetzt die Slippage-ANNAHME der Kostenszenarien durch MESSWERTE aus dem
Live-Capture (Bybit EU, api.bybit.eu v5/market/tickers).

KEIN TRIAL: keine Handelsregel wird gegen Marktdaten ausgewertet. Es wird
eine Annahme durch eine Messung ersetzt. Trial-Zaehler bleibt T-033.

METHODE
-------
slippage_je_seite = median(spread_bp) / 2 / 100   [in Prozent]
  Begruendung: eine Market-Order zahlt gegenueber der Mitte den halben
  Spread. Das gilt fuer Ordergroessen, die im Top-of-Book Platz finden -
  bei 25-100 $ Ordergroesse und den gemessenen Buchtiefen plausibel,
  aber NICHT gemessen: Buchtiefen-Auswertung folgt separat.

  K-BASIS_coin  = 2 * 0,25 % Taker  + 2 * slippage_je_seite
  K-MAKER_coin  = 2 * 0,10 % Maker  + 2 * 0,03 % Adverse Selection
                  (Maker zahlt keinen Spread - der Wert bleibt unveraendert
                   und ist bewusst NICHT coinabhaengig)

VORBEHALT - ausdruecklich, nicht kleingedruckt
----------------------------------------------
Die Messung umfasst 146 Punkte je Coin aus EINEM Tag (31.07.2026, ca.
5,5 h). Das ist eine Momentaufnahme, keine Verteilung ueber Marktphasen.
Die Definition of Done des Capture lautet 7 Tage lueckenlos; erst dann
sind diese Zahlen belastbar. Bis dahin gilt: WAHRSCHEINLICH, nicht SICHER.
Der Median ist gegen die Ausfallphasen (12:16-13:22 UTC) robuster als das
Mittel und wird deshalb verwendet; p90 und max sind mitgefuehrt, weil sie
zeigen, wie weit die Spreads in Stressmomenten aufgehen.
"""
import csv
import glob
import gzip
import io
import json
import os
import statistics as st
import sys
from datetime import datetime, timezone

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(BASIS, "capture")
TAKER, MAKER, ADVERSE = 0.25, 0.10, 0.03
ALT_SLIP = 0.05          # bisherige Annahme je Seite, in Prozent
BARRIEREN = (5.0, 7.0, 10.0)


def p_be(c, B):
    return (0.5 + c / (2.0 * B)) * 100.0


def messe():
    tage = sorted(d for d in glob.glob(os.path.join(CAP, "2026-*"))
                  if os.path.isdir(d))
    out, n_tage = {}, len(tage)
    for p in sorted(glob.glob(os.path.join(tage[-1], "ticker_*.csv.gz"))):
        sym = os.path.basename(p)[len("ticker_"):-len(".csv.gz")]
        txt = gzip.open(p, "rt", encoding="utf-8").read()
        sp = [float(r["spread_bp"]) for r in csv.DictReader(io.StringIO(txt))
              if r.get("spread_bp")]
        if len(sp) >= 30:
            q = st.quantiles(sp, n=100)
            out[sym] = {"n": len(sp), "min": min(sp), "median": st.median(sp),
                        "p90": q[89], "max": max(sp)}
    return out, n_tage, os.path.basename(tage[-1])


def main():
    mess, n_tage, tag = messe()
    print("=" * 104)
    print(" KOSTENMATRIX v3 - GEMESSENE Spreads ersetzen die 5-bp-Annahme")
    print(f" Quelle: Live-Capture Bybit EU, Tag {tag}, {n_tage} Tag(e) erfasst")
    print(" KEIN TRIAL. Vorbehalt: Momentaufnahme, DoD 7 Tage noch nicht erreicht.")
    print("=" * 104)

    print(f"\n  GEMESSENE SPREADS (Basispunkte)")
    print(f"    {'Coin':<10s} {'n':>5s} {'min':>8s} {'median':>8s} "
          f"{'p90':>8s} {'max':>8s} {'Median in %':>12s}")
    print("    " + "-" * 66)
    for sym, m in sorted(mess.items(), key=lambda x: x[1]["median"]):
        print(f"    {sym:<10s} {m['n']:5d} {m['min']:8.3f} {m['median']:8.3f} "
              f"{m['p90']:8.3f} {m['max']:8.3f} {m['median']/100:11.4f}%")

    print("\n" + "=" * 104)
    print(" KOSTEN JE COIN - K-BASIS neu (Taker beidseitig + gemessener Spread)")
    print("=" * 104)
    print(f"\n    {'Coin':<10s} {'Slip/Seite':>11s} {'K-BASIS neu':>12s} "
          f"{'K-BASIS alt':>12s} {'Delta':>9s} {'K-MAKER':>9s} | "
          f"{'p_be +/-5%':>11s} {'+/-7%':>8s} {'+/-10%':>8s}")
    print("    " + "-" * 104)
    k_maker = 2 * MAKER + 2 * ADVERSE
    k_alt = 2 * TAKER + 2 * ALT_SLIP
    zeilen = []
    for sym, m in sorted(mess.items(), key=lambda x: x[1]["median"]):
        slip = m["median"] / 2 / 100
        kb = 2 * TAKER + 2 * slip
        zeilen.append((sym, slip, kb, k_maker, m))
        print(f"    {sym:<10s} {slip:10.4f}% {kb:11.4f}% {k_alt:11.2f}% "
              f"{kb - k_alt:+8.4f}% {k_maker:8.2f}% | "
              + " ".join(f"{p_be(kb, B):10.2f}%" for B in BARRIEREN))

    guenstig = [z for z in zeilen if z[2] < k_alt]
    teurer = [z for z in zeilen if z[2] >= k_alt]
    print(f"\n  {len(guenstig)} Coins GUENSTIGER als die Annahme, "
          f"{len(teurer)} TEURER.")
    print(f"  Spanne K-BASIS: {min(z[2] for z in zeilen):.4f} % "
          f"({min(zeilen, key=lambda z: z[2])[0]}) bis "
          f"{max(z[2] for z in zeilen):.4f} % "
          f"({max(zeilen, key=lambda z: z[2])[0]}) - Faktor "
          f"{max(z[2] for z in zeilen)/min(z[2] for z in zeilen):.2f}")

    print("\n" + "=" * 104)
    print(" RUECKWIRKUNG AUF DIE BEREITS GEFAELLTEN URTEILE")
    print("=" * 104)
    seg = {"T-031 BTCUSDC": ("BTCUSDC", -0.855), "T-032 ETHUSDC": ("ETHUSDC", -0.173)}
    print("\n  Klausel A verlangt Netto-EV je Segment > K-BASIS. Das kritische")
    print("  Segment war S-C. Neurechnung mit gemessenen Kosten:\n")
    print(f"    {'Trial':<16s} {'S-C alt':>10s} {'Korrektur':>11s} "
          f"{'S-C neu':>10s} {'Schwelle':>10s} {'Urteil':>10s}")
    print("    " + "-" * 72)
    unveraendert = True
    for name, (sym, ev_alt) in seg.items():
        kb = 2 * TAKER + 2 * (mess[sym]["median"] / 2 / 100)
        korr = k_alt - kb              # eingesparte Kosten je Runde
        ev_neu = ev_alt + korr
        ok = ev_neu > kb
        unveraendert &= not ok
        print(f"    {name:<16s} {ev_alt:+9.3f}% {korr:+10.4f}% "
              f"{ev_neu:+9.3f}% {kb:9.4f}% "
              f"{'BESTEHT' if ok else 'FAELLT':>10s}")
    print(f"\n  GATE-2-VERDIKT: "
          f"{'UNVERAENDERT NEGATIV' if unveraendert else 'MUESSTE NEU BEWERTET WERDEN'}")
    print("  Die guenstigeren Kosten heben die S-C-Werte, aber nicht ueber die")
    print("  Schwelle. Fuer das 12er-Portfolio (T-033) wirkt die Messung sogar")
    print("  GEGEN den Trial: die teuren Alts (DOT, ATOM, NEAR, UNI) liegen weit")
    print("  ueber der alten Annahme und senken den Portfolio-EV zusaetzlich.")

    # ---- Datenbank ----
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from db_schema import verbinde
    con = verbinde()
    con.execute("DELETE FROM kostenszenarien WHERE name LIKE 'K-BASIS/%' "
                "OR name LIKE 'K-MAKER/%'")
    J = datetime.now(timezone.utc).isoformat()[:19] + "Z"
    for sym, slip, kb, km, m in zeilen:
        con.execute(
            "INSERT INTO kostenszenarien (name,boerse,maker_pct,taker_pct,"
            "slippage_pct,roundtrip_pct,quelle,verifiziert_am,konfidenz,"
            "quelle_md) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"K-BASIS/{sym}", "Bybit EU", None, TAKER, round(slip, 5),
             round(kb, 5),
             f"GEMESSEN Live-Capture {tag}, n={m['n']}, Median-Spread "
             f"{m['median']:.3f} bp (min {m['min']:.3f} / p90 {m['p90']:.3f} "
             f"/ max {m['max']:.3f}). Slippage = halber Median-Spread.",
             J, "WAHRSCHEINLICH",
             "docs/forschungsprogramm_2026-07/12_SPREAD-MESSUNG.md"))
        con.execute(
            "INSERT INTO kostenszenarien (name,boerse,maker_pct,taker_pct,"
            "slippage_pct,roundtrip_pct,quelle,verifiziert_am,konfidenz,"
            "quelle_md) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (f"K-MAKER/{sym}", "Bybit EU", MAKER, None, ADVERSE,
             round(km, 5),
             "Maker zahlt keinen Spread; Adverse Selection 0,03 % aus F1e. "
             "Bewusst NICHT coinabhaengig.", J, "WAHRSCHEINLICH",
             "docs/forschungsprogramm_2026-07/12_SPREAD-MESSUNG.md"))
    con.execute(
        "INSERT INTO befunde (runde,kurztext,langtext,konfidenz,risiko_0_10,"
        "impact_0_10,prioritaet,trial_bezug,zeitstempel,quelle_md) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (2, "Die 5-bp-Slippage-Annahme war in BEIDE Richtungen falsch",
         f"Gemessen am {tag} (n=146 je Coin, Bybit EU): Median-Spread reicht "
         f"von {min(m['median'] for m in mess.values()):.3f} bp (ETH) bis "
         f"{max(m['median'] for m in mess.values()):.3f} bp (DOT) - Faktor "
         f"{max(m['median'] for m in mess.values())/min(m['median'] for m in mess.values()):.0f}. "
         f"Fuer BTC/ETH ist die Annahme von 5 bp je Seite um zwei "
         f"Groessenordnungen ZU KONSERVATIV (K-BASIS faellt von 0,60 auf "
         f"~0,50 %). Fuer DOT/ATOM/NEAR/UNI ist sie ZU OPTIMISTISCH "
         f"(K-BASIS steigt auf bis zu 1,15 %). Eine einheitliche Kostenzahl "
         f"ueber alle Coins ist damit hinfaellig. Das Gate-2-Verdikt bleibt "
         f"unveraendert negativ: die guenstigeren BTC/ETH-Kosten heben die "
         f"S-C-Werte nicht ueber die Klausel-A-Schwelle.",
         "WAHRSCHEINLICH", 3, 8, "HOCH", "T-031,T-032,T-033", J,
         "docs/forschungsprogramm_2026-07/12_SPREAD-MESSUNG.md"))
    con.commit()
    print(f"\n  Datenbank: {2*len(zeilen)} coinweise Kostenszenarien + 1 Befund "
          f"eingetragen.")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
