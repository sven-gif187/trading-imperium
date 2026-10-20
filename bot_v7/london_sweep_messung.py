# -*- coding: utf-8 -*-
"""london_sweep_messung.py - misst die London-Liquidity-Sweep-Strategie.

WOZU
----
Sven brachte die Strategie am 08.09.2026 ein: "das hoert sich sehr
interessant an und waere evtl was fuer unseren bot". Statt sie zu glauben,
wurde sie gemessen - Regel 10 des Masterprompts: nichts anschliessen ohne
Messung, und die Trivial-Latte immer mit ausweisen.

DIE REGEL
---------
Die Asien-Sitzung (00:00-07:00 UTC) bildet eine Spanne. Im London-Fenster
(07:00-11:00 UTC) faellt der Kurs unter das Asien-Tief - die Stopps darunter
werden abgeholt ("Sweep") - und schliesst danach wieder darueber. Das gilt
als Kaufsignal. Stopp unter das Sweep-Tief, Ziel ans Asien-Hoch.

KEIN BLICK IN DIE ZUKUNFT: Eingestiegen wird zum SCHLUSS der Kerze, die die
Rueckkehr bestaetigt - erst wenn sie geschlossen ist.

ERGEBNIS (6 Monate, 15-Minuten-Kerzen, Befund 96): NO-GO. Der Bruttovorteil
ist echt, aber mit +0,01 bis +0,12 % je Handel vier- bis fuenfzigmal zu
klein fuer die 0,505 % Kosten.

Braucht die Kerzendateien aus dem Schwesterskript (Binance-Klines, nur
lesend). AENDERT NICHTS AM BOT.
"""
import json, os, datetime, statistics, collections
ORD = os.path.dirname(os.path.abspath(__file__)); KOSTEN = 0.505

def lade(sym):
    k = json.load(open(os.path.join(ORD, "kerzen_%s.json" % sym)))
    return [(datetime.datetime.fromtimestamp(x[0]/1000, datetime.timezone.utc),
             float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in k]

for sym in ("BTCUSDT","ETHUSDT","SOLUSDT"):
    T = {}
    for x in lade(sym): T.setdefault(x[0].date(), []).append(x)
    arten = collections.Counter(); erg = collections.defaultdict(list); crvs = []
    for tag in sorted(T):
        kk = T[tag]
        asien = [x for x in kk if 0 <= x[0].hour < 7]
        fen   = [x for x in kk if 7 <= x[0].hour < 11]
        rest  = [x for x in kk if x[0].hour >= 11]
        if len(asien) < 20 or len(fen) < 8 or not rest: continue
        a_t, a_h = min(x[3] for x in asien), max(x[2] for x in asien)
        gesw, sw = False, None
        for i, x in enumerate(fen):
            if not gesw:
                if x[3] < a_t: gesw, sw = True, x[3]
                continue
            sw = min(sw, x[3])
            if x[4] > a_t:
                ein, stop, ziel, spaeter = x[4], sw, a_h, fen[i+1:]+rest
                break
        else: continue
        if not spaeter or ein <= stop: continue
        crvs.append((ziel-ein)/(ein-stop))
        art, r = "Zeitablauf", 100.0*(spaeter[-1][4]-ein)/ein
        for y in spaeter:
            if y[3] <= stop: art, r = "STOPP", 100.0*(stop-ein)/ein; break
            if y[2] >= ziel: art, r = "ZIEL",  100.0*(ziel-ein)/ein; break
        arten[art] += 1; erg[art].append(r)
    n = sum(arten.values())
    print("\n=== %s  (n=%d, mittleres geplantes CRV %.2f) ===" % (sym, n, statistics.mean(crvs)))
    for a in ("ZIEL","STOPP","Zeitablauf"):
        if erg[a]:
            print("   %-11s %3d Faelle (%4.1f %%)   mittleres Ergebnis brutto %+7.3f %%"
                  % (a, arten[a], 100.0*arten[a]/n, statistics.mean(erg[a])))
    alle = [x for a in erg for x in erg[a]]
    gew = [x for x in alle if x > 0]; ver = [x for x in alle if x <= 0]
    print("   ---")
    print("   mittlerer GEWINN  %+7.3f %%   (%d Faelle)" % (statistics.mean(gew) if gew else 0, len(gew)))
    print("   mittlerer VERLUST %+7.3f %%   (%d Faelle)" % (statistics.mean(ver) if ver else 0, len(ver)))
    print("   TATSAECHLICHES Gewinn/Verlust-Verhaeltnis: %.2f"
          % (abs(statistics.mean(gew)/statistics.mean(ver)) if gew and ver else 0))
    print("   Erwartungswert brutto %+7.3f %%   netto %+7.3f %%"
          % (statistics.mean(alle), statistics.mean(alle)-KOSTEN))
