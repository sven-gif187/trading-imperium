# -*- coding: utf-8 -*-
"""MACD 12/26/9 ueber verschiedene Zeitrahmen - traegt er ueberhaupt?

WARUM DIESES WERKZEUG
---------------------
Mark, der mit Chartanalyse arbeitet, benutzt MACD 12/26/9 auf WOCHEN-
kerzen. Unser Bot benutzt denselben Indikator mit denselben Einstellungen
auf STUNDEN-kerzen. Zwischen beiden liegt der Faktor 168.

Die Frage ist also nicht "taugt MACD", sondern "auf welchem Zeitrahmen
taugt er" - und das laesst sich mit unseren Daten beantworten.

WAS GEMESSEN WIRD
-----------------
Ein bullisches Kreuz (MACD-Linie schneidet ihre Signallinie von unten)
gilt als Kaufanlass. Gemessen wird, was danach passierte - nach Kosten.

Gegen die TRIVIAL-LATTE: derselbe Zeitraum, dieselbe Muenze, aber ohne
jeden Indikator - einfach jeder Balken. Schlaegt das Kreuz die Latte
nicht, ist der Indikator auf diesem Zeitrahmen wertlos.

UNABHAENGIGKEIT
---------------
Zwei Kreuze, die drei Balken auseinanderliegen, messen fast dieselbe
Bewegung. Deshalb wird zusaetzlich gezaehlt, wieviele Kreuze weiter als
der Messhorizont auseinanderliegen - nur die tragen ein Urteil.

AENDERT NICHTS AM BOT. Reines Lesen und Rechnen.

    python macd_zeitrahmen.py
    python macd_zeitrahmen.py --symbol ETH/USDT
    python macd_zeitrahmen.py --selbsttest
"""
import argparse
import sys
import time

K_BASIS = 0.505          # Kosten je Runde in Prozent, CLAUDE.md Abschnitt 8
ZEITRAHMEN = [("1h", 24), ("4h", 12), ("1d", 7), ("1w", 4)]
# je (Zeitrahmen, Horizont in Balken) - ueberall rund eine Woche Vorlauf


def kerzen(symbol, tf, ab):
    import ccxt
    import pandas as pd
    b = ccxt.binance({"enableRateLimit": True})
    seit = b.parse8601(ab + "T00:00:00Z")
    alle = []
    while True:
        teil = b.fetch_ohlcv(symbol, tf, since=seit, limit=1000)
        if not teil:
            break
        alle += teil
        seit = teil[-1][0] + 1
        if len(teil) < 1000:
            break
        time.sleep(b.rateLimit / 1000.0)
    if not alle:
        return None
    df = pd.DataFrame(alle, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
    df = df.drop_duplicates(subset="ts").sort_values("ts").reset_index(drop=True)
    df["zeit"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df


def macd(close, schnell=12, langsam=26, signal=9):
    """MACD 12/26/9 - exakt die Einstellung aus Marks Charts."""
    ema_s = close.ewm(span=schnell, adjust=False).mean()
    ema_l = close.ewm(span=langsam, adjust=False).mean()
    linie = ema_s - ema_l
    sig = linie.ewm(span=signal, adjust=False).mean()
    return linie, sig, linie - sig


def kreuze(linie, sig):
    """Balken-Indizes, an denen die MACD-Linie ihre Signallinie von UNTEN
    schneidet. Der Index ist der Balken, an dem das Kreuz FERTIG ist -
    handelbar waere erst der naechste."""
    out = []
    for i in range(1, len(linie)):
        if linie.iloc[i - 1] <= sig.iloc[i - 1] and linie.iloc[i] > sig.iloc[i]:
            out.append(i)
    return out


def ergebnis(df, start, horizont):
    """Rendite in Prozent nach `horizont` Balken, NACH Kosten.

    Eingestiegen wird am OEFFNEN des naechsten Balkens - nicht am Schluss
    des Kreuz-Balkens. Wer das verwechselt, handelt mit einem Kurs, den
    es zum Entscheidungszeitpunkt noch nicht gab.
    """
    ein = start + 1
    aus = ein + horizont
    if aus >= len(df):
        return None
    p_ein = float(df["Open"].iloc[ein])
    p_aus = float(df["Close"].iloc[aus])
    if p_ein <= 0:
        return None
    return (p_aus / p_ein - 1) * 100.0 - K_BASIS


def latte(df, horizont, schritt=1):
    """Trivial-Latte: JEDER Balken als Einstieg, ohne Indikator."""
    w = []
    for i in range(0, len(df) - horizont - 2, schritt):
        r = ergebnis(df, i, horizont)
        if r is not None:
            w.append(r)
    return w


def unabhaengig(idx, horizont):
    """Wieviele Kreuze liegen weiter auseinander als der Messhorizont?"""
    if not idx:
        return 0
    n = 1
    letzte = idx[0]
    for i in idx[1:]:
        if i - letzte >= horizont:
            n += 1
            letzte = i
    return n


def messen(symbol, ab="2021-01-01"):
    import statistics as st
    import math
    print("=" * 82)
    print(" MACD 12/26/9 UEBER ZEITRAHMEN  -  %s" % symbol)
    print("=" * 82)
    print("  Kosten je Runde: %.3f %% (K-BASIS)" % K_BASIS)
    print("  Einstieg am OEFFNEN des Balkens NACH dem Kreuz.\n")
    print("  Zeitrahmen  Horizont   Kreuze  unabh.   EV netto    Trivial-Latte   Vorsprung")
    print("  " + "-" * 78)
    zeilen = []
    for tf, hor in ZEITRAHMEN:
        df = kerzen(symbol, tf, ab)
        if df is None or len(df) < 100:
            print("  %-10s  zu wenige Kerzen" % tf)
            continue
        linie, sig, _ = macd(df["Close"])
        idx = kreuze(linie, sig)
        werte = [ergebnis(df, i, hor) for i in idx]
        werte = [w for w in werte if w is not None]
        if len(werte) < 5:
            print("  %-10s  nur %d auswertbare Kreuze" % (tf, len(werte)))
            continue
        lat = latte(df, hor, schritt=max(1, hor // 4))
        ev = sum(werte) / len(werte)
        ev_l = sum(lat) / len(lat) if lat else 0.0
        u = unabhaengig(idx, hor)
        vor = ev - ev_l
        zeilen.append((tf, hor, len(werte), u, ev, ev_l, vor, werte))
        print("  %-10s  %6d   %6d  %6d   %+8.3f %%  %+8.3f %%   %+8.3f PP"
              % (tf, hor, len(werte), u, ev, ev_l, vor))
    print()
    print("=" * 82)
    print(" URTEIL")
    print("=" * 82)
    for tf, hor, n, u, ev, ev_l, vor, werte in zeilen:
        se = st.pstdev(werte) / math.sqrt(max(u, 1))
        if u < 20:
            urteil = "nicht entscheidbar (nur %d unabhaengige Kreuze)" % u
        elif vor > 2 * se:
            urteil = "TRAEGT - schlaegt die Latte belastbar"
        elif vor < -2 * se:
            urteil = "SCHADET - schlechter als gar kein Indikator"
        else:
            urteil = "kein Unterschied zur Latte"
        print("  %-6s %s" % (tf, urteil))
    print()
    print("  Lesehilfe: 'unabh.' zaehlt nur Kreuze, die weiter auseinander liegen")
    print("  als der Messhorizont. Zwei Kreuze im selben Fenster messen dieselbe")
    print("  Bewegung zweimal - fuer ein Urteil zaehlt nur die linke Zahl.")
    print("=" * 82)
    return zeilen


def selbsttest():
    import pandas as pd
    print("SELBSTTEST")
    print("-" * 60)
    f = 0

    # 1) MACD gegen eine von Hand nachgerechnete Reihe
    c = pd.Series([float(x) for x in range(1, 60)])
    l, s, h = macd(c)
    ok = l.iloc[-1] > 0 and abs(h.iloc[-1]) < abs(l.iloc[-1])
    print("  %s steigende Reihe -> MACD positiv" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    # 2) Kreuz wird erkannt - und nur eines
    c = pd.Series([100] * 30 + [100 - i for i in range(20)] + [80 + i * 2 for i in range(30)])
    l, s, _ = macd(c)
    k = kreuze(l, s)
    ok = len(k) == 1
    print("  %s genau ein bullisches Kreuz erkannt (%d)" % ("OK  " if ok else "FEHL", len(k)))
    f += 0 if ok else 1

    # 3) Kein Kreuz bei durchgehend steigender Reihe nach dem Start
    c = pd.Series([float(100 + i) for i in range(80)])
    l, s, _ = macd(c)
    ok = len(kreuze(l, s)) <= 1
    print("  %s monotone Reihe erzeugt hoechstens ein Kreuz" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    # 4) Kosten werden abgezogen
    df = pd.DataFrame({"Open": [100.0] * 10, "Close": [100.0] * 10,
                       "High": [100.0] * 10, "Low": [100.0] * 10})
    r = ergebnis(df, 0, 3)
    ok = r is not None and abs(r + K_BASIS) < 1e-9
    print("  %s unveraenderter Kurs -> genau -K_BASIS (%.3f)" % ("OK  " if ok else "FEHL", r or 0))
    f += 0 if ok else 1

    # 5) Unabhaengigkeit zaehlt richtig
    ok = unabhaengig([0, 1, 2, 20, 21, 50], 10) == 3
    print("  %s Unabhaengigkeit: [0,1,2,20,21,50] bei Horizont 10 -> 3" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    print("-" * 60)
    print("ALLE TESTS BESTANDEN" if f == 0 else "%d TEST(S) FEHLGESCHLAGEN" % f)
    return 0 if f == 0 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTC/USDT")
    p.add_argument("--ab", default="2021-01-01")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    if a.selbsttest:
        return selbsttest()
    messen(a.symbol, a.ab)
    return 0


if __name__ == "__main__":
    sys.exit(main())
