#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  E7-GEGENPROBE  -  reines Analyse-Werkzeug (aendert NICHTS)
================================================================
FRAGE: Haben die E7-UP-Exits mehr gebracht als die alte Leiter?

METHODE (kontrafaktisch):
  Der E7-Ausstieg ist Tatsache (steht im Journal). Die ALTE Leiter
  haette frueher verkauft - wann genau, spielen wir mit den
  gecachten Kerzen nach:
    1. E7-UP-Verkaeufe aus data_store/trades_v5.json lesen
    2. Aus dem Grund-Text Fall/Schwelle/PnL/Stufe zerlegen
       -> Trail-Basis = Schwelle / Stufe (selbstkalibrierend)
    3. Alte Stufe aus dem PnL bestimmen (0.5/0.7/1.0/1.6)
       Ist sie gleich der E7-Stufe -> neutraler Fall, kein Vergleich
    4. Einstiegspreis = Verkaufspreis / (1 + PnL/100)
    5. Kerzen (data_store/charts/<COIN>USDT_1h.csv) vom Einstieg bis
       zum Verkauf durchgehen, alte Leiter simulieren, ersten
       Ausstieg finden -> Vergleich mit dem echten E7-Ergebnis

GRENZEN (ehrlich):
  * 1h-Kerzen: der genaue Verlauf INNERHALB einer Stunde ist unbekannt.
    Wir rechnen konservativ mit High (Hoch) und Low (Rueckfall) -
    das benachteiligt tendenziell E7, das Ergebnis ist also eher
    eine Untergrenze.
  * Nur Trailing wird nachgespielt. Andere Ausstiege (Stop, Trend,
    RSI) bleiben unberuecksichtigt - sie waren an diesen Tagen nicht
    der Grund.
  * Stichprobe ist klein. Das hier ist ein Hinweis, kein Beweis.

Aufruf:
  python "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\\e7_gegenprobe.py" > "C:\\Users\\<BENUTZER>\\Desktop\\e7probe_log.txt" 2>&1
================================================================
"""
import os, re, csv, json, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, "data_store", "trades_v5.json")
CHARTS = os.path.join(HERE, "data_store", "charts")

MUSTER = re.compile(
    r"Fall\s+([\d.]+)%\s*>=\s*([\d.]+)%.*?PnL\s+([+-]?[\d.]+)%.*?Stufe\s+x([\d.]+)", re.S)


def alte_stufe(pnl_pct):
    if pnl_pct >= 5.0:
        return 0.5
    if pnl_pct >= 3.0:
        return 0.7
    if pnl_pct >= 1.0:
        return 1.0
    return 1.6


def lade_kerzen(coin):
    sym = coin.replace("/", "")
    if sym.endswith("USDC"):
        sym = sym[:-4] + "USDT"
    pfad = os.path.join(CHARTS, f"{sym}_1h.csv")
    if not os.path.isfile(pfad):
        return []
    kerzen = []
    try:
        with open(pfad, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                kerzen.append({"t": int(r["open_time"]), "h": float(r["high"]),
                               "l": float(r["low"]), "c": float(r["close"])})
    except Exception:
        return []
    return kerzen


def ms(zeitstring):
    try:
        return int(datetime.fromisoformat(str(zeitstring)[:19]).timestamp() * 1000)
    except Exception:
        return None


def simuliere_alte_leiter(kerzen, einstieg, trail_basis, start_ms, ende_ms):
    """Erster Ausstieg der ALTEN Leiter. -> (pnl_pct, zeit) oder None."""
    hoch = einstieg
    for k in kerzen:
        if k["t"] < start_ms or k["t"] > ende_ms:
            continue
        hoch = max(hoch, k["h"])
        pnl_tief = (k["l"] / einstieg - 1) * 100
        if pnl_tief <= 0:
            continue                                   # Trailing nur im Gewinn
        schwelle = trail_basis * alte_stufe(pnl_tief)
        fall = (hoch - k["l"]) / hoch * 100
        if fall >= schwelle:
            preis = hoch * (1 - schwelle / 100)
            preis = max(preis, k["l"])
            return (preis / einstieg - 1) * 100, k["t"]
    return None


def main():
    print("=" * 62)
    print("  E7-GEGENPROBE - alte Leiter gegen E7 (kontrafaktisch)")
    print("=" * 62)
    if not os.path.isfile(JOURNAL):
        print("FEHLER: trades_v5.json nicht gefunden."); return 1
    if not os.path.isdir(CHARTS):
        print("FEHLER: data_store/charts/ nicht gefunden (Kerzen-Cache fehlt)."); return 1
    trades = json.load(open(JOURNAL, encoding="utf-8", errors="ignore"))
    e7 = [t for t in trades if t.get("type") == "SELL"
          and "E7-UP" in str(t.get("reason", ""))]
    print(f"\nGefundene E7-UP-Verkaeufe: {len(e7)}\n")
    if not e7:
        print("Noch keine E7-UP-Exits im Journal."); return 0

    neutral, vergleichbar, fehlend = [], [], []
    for t in e7:
        m = MUSTER.search(str(t.get("reason", "")))
        if not m:
            fehlend.append((t, "Grund nicht lesbar")); continue
        fall, schwelle, pnl, stufe = (float(m.group(1)), float(m.group(2)),
                                      float(m.group(3)), float(m.group(4)))
        basis = schwelle / stufe if stufe else 0
        alt = alte_stufe(pnl)
        eintrag = {"t": t, "pnl": pnl, "stufe": stufe, "alt": alt,
                   "schwelle": schwelle, "basis": basis, "fall": fall}
        (neutral if abs(alt - stufe) < 1e-9 else vergleichbar).append(eintrag)

    print(f"  Neutrale Faelle (Stufe identisch, E7 ohne Wirkung): {len(neutral)}")
    for e in neutral:
        print(f"    {str(e['t'].get('time',''))[5:16]}  {e['t'].get('coin','?'):10} "
              f"PnL {e['pnl']:+.2f}%  Stufe x{e['stufe']}  -> haette genauso verkauft")
    print(f"\n  Wirksame Faelle (Stufe unterschiedlich): {len(vergleichbar)}")
    print("-" * 62)

    summe_diff_pct, summe_diff_usd, gezaehlt = 0.0, 0.0, 0
    for e in vergleichbar:
        t = e["t"]
        coin = t.get("coin", "?")
        preis = float(t.get("price", 0) or 0)
        qty = float(t.get("qty", 0) or 0)
        einstieg = preis / (1 + e["pnl"] / 100) if preis else 0
        verkauf_ms = ms(t.get("time"))
        if not (preis and einstieg and verkauf_ms):
            fehlend.append((t, "Preis/Zeit unvollstaendig")); continue
        # Einstiegszeit = letzter BUY dieses Coins vor dem Verkauf
        kaeufe = [x for x in trades if x.get("type") == "BUY"
                  and x.get("coin") == coin and ms(x.get("time"))
                  and ms(x.get("time")) < verkauf_ms]
        start_ms = ms(kaeufe[-1].get("time")) if kaeufe else verkauf_ms - 48 * 3600_000
        kerzen = lade_kerzen(coin)
        if not kerzen:
            fehlend.append((t, "keine Kerzen im Cache")); continue
        alt_ergebnis = simuliere_alte_leiter(kerzen, einstieg, e["basis"],
                                             start_ms, verkauf_ms)
        print(f"\n  {str(t.get('time',''))[5:16]}  {coin}")
        print(f"    E7:  PnL {e['pnl']:+.2f}%  (Stufe x{e['stufe']}, "
              f"Schwelle {e['schwelle']:.3f}%)  = {float(t.get('pnl',0)):+.2f}$")
        if alt_ergebnis is None:
            print(f"    ALT: haette im Fenster NICHT ausgeloest "
                  f"(Stufe x{e['alt']}) -> kein Vergleich moeglich")
            continue
        alt_pnl, alt_t = alt_ergebnis
        diff = e["pnl"] - alt_pnl
        diff_usd = einstieg * qty * diff / 100 if qty else 0
        zeit = datetime.fromtimestamp(alt_t / 1000).strftime("%d.%m %H:%M")
        print(f"    ALT: PnL {alt_pnl:+.2f}%  (Stufe x{e['alt']}, Ausstieg {zeit})")
        print(f"    -> Differenz {diff:+.2f} Prozentpunkte" +
              (f"  ({diff_usd:+.2f}$)" if qty else ""))
        summe_diff_pct += diff
        summe_diff_usd += diff_usd
        gezaehlt += 1

    print("\n" + "=" * 62)
    print("  ERGEBNIS")
    print("=" * 62)
    if gezaehlt:
        print(f"  Verglichene Faelle:      {gezaehlt}")
        print(f"  Summe Differenz:         {summe_diff_pct:+.2f} Prozentpunkte "
              f"({summe_diff_usd:+.2f}$)")
        print(f"  Durchschnitt je Trade:   {summe_diff_pct/gezaehlt:+.2f} Pp")
        print(f"\n  {'E7 war im Vorteil.' if summe_diff_pct > 0 else 'Die alte Leiter war besser.' if summe_diff_pct < 0 else 'Gleichstand.'}")
    else:
        print("  Kein Fall vergleichbar - mehr Daten abwarten.")
    if fehlend:
        print(f"\n  Uebersprungen: {len(fehlend)}")
        for t, grund in fehlend:
            print(f"    {str(t.get('time',''))[5:16]} {t.get('coin','?'):10} {grund}")
    print("\n  ACHTUNG: 1h-Kerzen, kleine Stichprobe, konservative Annahmen.")
    print("  Hinweis fuer die E7-Auswertung - kein abschliessender Beweis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
