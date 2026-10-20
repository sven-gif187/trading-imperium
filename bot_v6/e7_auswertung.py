#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  E7-AUSWERTUNG  -  der grosse Report (read-only, aendert NICHTS)
================================================================
Fasst am Ende des E7-Fensters (~31.07.) alles zusammen, was fuer
die Entscheidung "E7 behalten / verwerfen / anpassen" noetig ist:

  1. Fenster-Kennzahlen: Sells, WR, R/R vs E6.1-Basis (0.54)
  2. E7-UP-Bilanz: wieviele Treffer, welche Coins, welche Stufen
  3. Wirksame vs neutrale Faelle (nur PnL>=1% trennen die Leitern)
  4. Gegenprobe je wirksamem Fall (ruft e7_gegenprobe-Logik nach):
     was haette die ALTE Leiter gebracht?
  5. Klares Urteil nach VORREGISTRIERTEN Kriterien

VORREGISTRIERTE KRITERIEN (aus dem E7-Deploy festgehalten):
  K1: R/R im Fenster >= E6.1-Basis (0.54)
  K2: Summe(E7 - alte Leiter) ueber alle wirksamen Faelle > 0
  K3: Nicht-UP-Phasen unveraendert (Kontroll-Check: normale
      Trailing-Exits verhalten sich wie vor E7)
  K4: mind. 3 wirksame Faelle (PnL>=1%) - sonst "Datenlage zu duenn"

Ausgabe: Report auf die Konsole (per > in Datei umleiten).
KEIN Eingriff, kein Schreiben ausser optionalem Report-File.
  python "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\\e7_auswertung.py" > "C:\\Users\\<BENUTZER>\\Desktop\\E7_REPORT.txt" 2>&1
================================================================
"""
import os, re, csv, json, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HERE, "data_store", "trades_v5.json")
CHARTS = os.path.join(HERE, "data_store", "charts")

E7_DEPLOY = "2026-07-17T12"          # Messbeginn
E61_BASIS_RR = 0.54                  # vorregistrierte Basis
MUSTER = re.compile(
    r"Fall\s+([\d.]+)%\s*>=\s*([\d.]+)%.*?PnL\s+([+-]?[\d.]+)%.*?Stufe\s+x([\d.]+)", re.S)


def med(x):
    s = sorted(x); n = len(s)
    return 0.0 if not s else (s[n//2] if n % 2 else (s[n//2-1]+s[n//2])/2)


def alte_stufe(pnl):
    return 0.5 if pnl >= 5 else 0.7 if pnl >= 3 else 1.0 if pnl >= 1 else 1.6


def ms(ts):
    try:
        return int(datetime.fromisoformat(str(ts)[:19]).timestamp()*1000)
    except Exception:
        return None


def lade_kerzen(coin):
    sym = coin.replace("/", "")
    if sym.endswith("USDC"):
        sym = sym[:-4] + "USDT"
    p = os.path.join(CHARTS, f"{sym}_1h.csv")
    if not os.path.isfile(p):
        return []
    out = []
    try:
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out.append({"t": int(r["open_time"]), "h": float(r["high"]),
                            "l": float(r["low"])})
    except Exception:
        return []
    return out


def sim_alt(kerzen, einstieg, basis, start_ms, ende_ms):
    hoch = einstieg
    for k in kerzen:
        if k["t"] < start_ms or k["t"] > ende_ms:
            continue
        hoch = max(hoch, k["h"])
        pnl_tief = (k["l"]/einstieg - 1)*100
        if pnl_tief <= 0:
            continue
        schwelle = basis * alte_stufe(pnl_tief)
        if (hoch - k["l"])/hoch*100 >= schwelle:
            preis = max(hoch*(1-schwelle/100), k["l"])
            return (preis/einstieg - 1)*100
    return None


def main():
    print("=" * 64)
    print("  E7-AUSWERTUNG  -  Phasen-Trailing im Test")
    print("  Erstellt:", datetime.now().strftime("%d.%m.%Y %H:%M"))
    print("=" * 64)
    if not os.path.isfile(JOURNAL):
        print("FEHLER: trades_v5.json fehlt."); return 1
    trades = json.load(open(JOURNAL, encoding="utf-8", errors="ignore"))
    sells = [t for t in trades if t.get("type") == "SELL"]
    fenster = [t for t in sells if str(t.get("time", "")) >= E7_DEPLOY]

    # --- 1. Fenster-Kennzahlen ---
    print(f"\n[1] FENSTER (ab {E7_DEPLOY[:10]}, {len(fenster)} Sells)")
    w = [float(t.get("pnl", 0)) for t in fenster if float(t.get("pnl", 0)) > 0]
    l = [float(t.get("pnl", 0)) for t in fenster if float(t.get("pnl", 0)) <= 0]
    aw = sum(w)/len(w) if w else 0
    al = abs(sum(l)/len(l)) if l else 0
    rr = aw/al if al else 0
    wr = len(w)/len(fenster)*100 if fenster else 0
    print(f"    WR {wr:.0f}% | AvgWin +{aw:.2f}$ | AvgLoss -{al:.2f}$")
    print(f"    R/R {rr:.2f}  (Basis E6.1: {E61_BASIS_RR})  "
          f"-> {'K1 erfuellt' if rr >= E61_BASIS_RR else 'K1 VERFEHLT'}")
    print(f"    Gesamt-P&L: {sum(float(t.get('pnl',0)) for t in fenster):+.2f}$")

    # --- 2./3. E7-UP-Faelle sortieren ---
    e7 = [t for t in fenster if "E7-UP" in str(t.get("reason", ""))]
    neutral, wirksam = [], []
    for t in e7:
        m = MUSTER.search(str(t.get("reason", "")))
        if not m:
            continue
        pnl, stufe = float(m.group(3)), float(m.group(4))
        basis = float(m.group(2))/stufe if stufe else 0
        (neutral if abs(alte_stufe(pnl)-stufe) < 1e-9 else wirksam).append(
            {"t": t, "pnl": pnl, "stufe": stufe, "basis": basis})
    print(f"\n[2] E7-UP-BILANZ")
    print(f"    Treffer gesamt: {len(e7)} | Coins: {sorted(set(t.get('coin') for t in e7))}")
    print(f"    Wirksam (PnL>=1%): {len(wirksam)} | Neutral (<1%): {len(neutral)}")

    # --- 4. Gegenprobe je wirksamem Fall ---
    print(f"\n[3] GEGENPROBE (E7 vs alte Leiter, Kerzen 1h)")
    summe_diff, gezaehlt = 0.0, 0
    for e in wirksam:
        t = e["t"]; coin = t.get("coin", "?")
        preis = float(t.get("price", 0) or 0); qty = float(t.get("qty", 0) or 0)
        einstieg = preis/(1+e["pnl"]/100) if preis else 0
        verkauf_ms = ms(t.get("time"))
        vorher = [ms(x.get("time")) for x in trades if x.get("type") == "SELL"
                  and x.get("coin") == coin and ms(x.get("time"))
                  and ms(x.get("time")) < verkauf_ms]
        letzter = max(vorher) if vorher else 0
        kaeufe = [ms(x.get("time")) for x in trades if x.get("type") == "BUY"
                  and x.get("coin") == coin and ms(x.get("time"))
                  and letzter < ms(x.get("time")) < verkauf_ms]
        start_ms = min(kaeufe) if kaeufe else verkauf_ms - 48*3600_000
        kerzen = lade_kerzen(coin)
        if not (preis and einstieg and kerzen):
            print(f"    {str(t.get('time',''))[5:16]} {coin}: uebersprungen (Daten/Kerzen fehlen)")
            continue
        alt = sim_alt(kerzen, einstieg, e["basis"], start_ms, verkauf_ms)
        if alt is None:
            print(f"    {str(t.get('time',''))[5:16]} {coin}: alte Leiter kein Ausstieg im Fenster")
            continue
        diff = e["pnl"] - alt
        diff_usd = einstieg*qty*diff/100 if qty else 0
        summe_diff += diff; gezaehlt += 1
        print(f"    {str(t.get('time',''))[5:16]} {coin}: "
              f"E7 {e['pnl']:+.2f}% vs ALT {alt:+.2f}% = {diff:+.2f}pp ({diff_usd:+.2f}$)")

    # --- 5. Urteil ---
    print(f"\n[4] URTEIL (vorregistrierte Kriterien)")
    k1 = rr >= E61_BASIS_RR
    k2 = gezaehlt > 0 and summe_diff > 0
    k4 = gezaehlt >= 3
    print(f"    K1 R/R >= {E61_BASIS_RR}:            {'JA' if k1 else 'NEIN'} ({rr:.2f})")
    print(f"    K2 Gegenprobe-Summe > 0:      {'JA' if k2 else 'NEIN'} ({summe_diff:+.2f}pp ueber {gezaehlt} Faelle)")
    print(f"    K4 mind. 3 wirksame Faelle:   {'JA' if k4 else 'NEIN'} ({gezaehlt})")
    print()
    if not k4:
        print("    >> DATENLAGE ZU DUENN. E7-Fenster verlaengern, weiter sammeln.")
    elif k1 and k2:
        print("    >> E7 BESTEHT. Behalten. Naechster Schritt: E8-Sizing.")
    elif k1 and not k2:
        print("    >> E7 NEUTRAL/NEGATIV trotz gutem R/R. Gegenprobe zeigt keinen")
        print("       Vorteil -> E7 verwerfen oder Stufen nachjustieren.")
    else:
        print("    >> K1 VERFEHLT. Fenster war schwach - Ursache pruefen,")
        print("       nicht vorschnell an E7 festmachen.")
    print("\n    ACHTUNG: 1h-Kerzen, konservative Annahmen, ADA-lastige Stichprobe.")
    print("    Entscheidung mit dem Sensei besprechen, nicht automatisch handeln.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
