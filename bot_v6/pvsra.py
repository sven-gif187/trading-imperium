# -*- coding: utf-8 -*-
"""PVSRA - Price Volume Setup Range Analysis, nachgebaut und gemessen.

WAS DAS IST
-----------
PVSRA faerbt Kerzen danach ein, ob hinter ihnen ungewoehnlich viel
Handelsvolumen steckt. Die Idee: Grosse Marktteilnehmer hinterlassen
Spuren im Volumen, und eine Kerze mit viel Volumen UND grosser Spanne
zeigt, wo sie zugegriffen haben.

Der Indikator stammt aus Marks Werkzeugliste (Trademania - PVSRA
Indikator von BitbullTrading, 12.700 Boosts auf TradingView) und war
dort im Bild AUSGEWAEHLT. Er ist der einzige seiner acht Indikatoren,
den wir noch nicht hatten.

DIE REGEL - Standarddefinition
------------------------------
Fuer jede Kerze wird verglichen, wie sie zu den letzten zehn steht:

  KLIMAX      Volumen x Spanne  >=  2,0 x Mittel der letzten 10
              -> gruen, wenn Schluss ueber Oeffnung (Kaufdruck)
              -> rot,   wenn Schluss unter Oeffnung (Verkaufsdruck)

  STEIGEND    Volumen           >=  1,5 x Mittel der letzten 10
              -> blau bei steigender, pink bei fallender Kerze

  NORMAL      alles Uebrige

WAS HIER GEMESSEN WIRD - und warum das der Punkt ist
-----------------------------------------------------
Einen Indikator nachzubauen ist die halbe Arbeit. Die andere Haelfte
ist die Frage, ob er etwas taugt. Deshalb rechnet dieses Programm
sofort mit:

  Was passierte NACH einer gruenen Klimax-Kerze - gegen das, was nach
  einer BELIEBIGEN Kerze passierte?

Ohne diesen Vergleich sagt eine Trefferquote nichts. Dieselbe Regel
gilt hier wie ueberall im Projekt.

KAUSALITAET
-----------
Der Vergleich laeuft ueber die zehn Kerzen DAVOR, die aktuelle
eingeschlossen - so, wie der Indikator im Chart rechnet. Eingestiegen
wird am OEFFNEN der naechsten Kerze, nicht am Schluss der aktuellen.

AENDERT NICHTS AM BOT. Reines Lesen und Rechnen.

    python pvsra.py
    python pvsra.py --symbol ETH/USDT --timeframe 4h
    python pvsra.py --selbsttest
"""
import argparse
import sys
import time

K_BASIS = 0.505          # Kosten je Runde in Prozent, CLAUDE.md Abschnitt 8
FENSTER = 10             # Vergleichsfenster in Kerzen
KLIMAX = 2.0             # Faktor fuer Volumen x Spanne
STEIGEND = 1.5           # Faktor fuer Volumen allein


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


def einfaerben(df, fenster=FENSTER, klimax=KLIMAX, steigend=STEIGEND):
    """Ordnet jeder Kerze ihre PVSRA-Art zu.

    Rueckgabe: Liste gleicher Laenge wie df mit Werten
    'klimax_auf', 'klimax_ab', 'steigend_auf', 'steigend_ab', 'normal'.
    Die ersten `fenster` Kerzen sind 'normal' - vorher gibt es keinen
    Vergleichswert, und Raten waere hier ein Blick in die Zukunft.
    """
    v = df["Volume"].values
    spanne = (df["High"] - df["Low"]).values
    schluss = df["Close"].values
    offen = df["Open"].values
    vs = v * spanne
    art = ["normal"] * len(df)
    for i in range(fenster, len(df)):
        m_vs = vs[i - fenster:i].mean()
        m_v = v[i - fenster:i].mean()
        auf = schluss[i] > offen[i]
        if m_vs > 0 and vs[i] >= klimax * m_vs:
            art[i] = "klimax_auf" if auf else "klimax_ab"
        elif m_v > 0 and v[i] >= steigend * m_v:
            art[i] = "steigend_auf" if auf else "steigend_ab"
    return art


def ergebnis(df, i, horizont):
    """Rendite nach `horizont` Kerzen, NACH Kosten.

    Einstieg am OEFFNEN der naechsten Kerze - der Schluss der aktuellen
    ist zum Entscheidungszeitpunkt der letzte bekannte Kurs, aber
    handeln kann man erst danach.
    """
    ein, aus = i + 1, i + 1 + horizont
    if aus >= len(df):
        return None
    p_ein = float(df["Open"].iloc[ein])
    if p_ein <= 0:
        return None
    return (float(df["Close"].iloc[aus]) / p_ein - 1) * 100.0 - K_BASIS


def messen(symbol="BTC/USDT", tf="1h", ab="2021-01-01", horizont=24):
    import statistics as st
    import math
    df = kerzen(symbol, tf, ab)
    if df is None or len(df) < 200:
        print("Zu wenige Kerzen.")
        return []
    art = einfaerben(df)
    print("=" * 82)
    print(" PVSRA NACHGEBAUT UND GEMESSEN  -  %s, %s" % (symbol, tf))
    print("=" * 82)
    print("  Kerzen: %d   (%s bis %s)" % (len(df), df["zeit"].iloc[0].date(),
                                          df["zeit"].iloc[-1].date()))
    print("  Horizont: %d Kerzen   Kosten: %.3f %%\n" % (horizont, K_BASIS))
    gruppen = {}
    for i, a in enumerate(art):
        r = ergebnis(df, i, horizont)
        if r is not None:
            gruppen.setdefault(a, []).append(r)
    alle = [x for w in gruppen.values() for x in w]
    ev_alle = sum(alle) / len(alle) if alle else 0.0
    print("  Kerzenart        Anzahl  Anteil    EV netto   gegen ALLE   Urteil")
    print("  " + "-" * 74)
    zeilen = []
    for a in ("klimax_auf", "klimax_ab", "steigend_auf", "steigend_ab", "normal"):
        w = gruppen.get(a, [])
        if len(w) < 30:
            print("  %-16s %6d   zu wenig" % (a, len(w)))
            continue
        ev = sum(w) / len(w)
        vor = ev - ev_alle
        se = st.pstdev(w) / math.sqrt(len(w))
        if abs(vor) < 2 * se:
            u = "kein Unterschied"
        elif vor > 0:
            u = "BESSER"
        else:
            u = "schlechter"
        print("  %-16s %6d  %5.1f %%  %+8.3f %%  %+8.3f PP   %s"
              % (a, len(w), 100.0 * len(w) / len(alle), ev, vor, u))
        zeilen.append((a, len(w), ev, vor, u))
    print("  " + "-" * 74)
    print("  %-16s %6d  100.0 %%  %+8.3f %%       Latte" % ("ALLE (Latte)", len(alle), ev_alle))
    print()
    print("  Achtung Fallzahl: Aufeinanderfolgende Kerzen ueberlappen im Horizont.")
    print("  Von %d Kerzen sind hoechstens %d unabhaengig (Abstand >= Horizont)."
          % (len(alle), len(alle) // max(horizont, 1)))
    print("=" * 82)
    return zeilen


def selbsttest():
    import pandas as pd
    print("SELBSTTEST")
    print("-" * 60)
    f = 0

    # 1) Eine ruhige Reihe hat keine Klimax-Kerze
    n = 40
    df = pd.DataFrame({"Open": [100.0] * n, "Close": [100.5] * n,
                       "High": [101.0] * n, "Low": [99.0] * n,
                       "Volume": [1000.0] * n})
    art = einfaerben(df)
    ok = all(a == "normal" for a in art)
    print("  %s gleichfoermige Reihe -> alles 'normal'" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    # 2) Ein Volumen- und Spannenausschlag wird als Klimax erkannt
    df.loc[30, "Volume"] = 5000.0
    df.loc[30, "High"] = 110.0
    df.loc[30, "Low"] = 90.0
    art = einfaerben(df)
    ok = art[30] == "klimax_auf"
    print("  %s Ausschlag bei steigender Kerze -> 'klimax_auf' (ist: %s)"
          % ("OK  " if ok else "FEHL", art[30]))
    f += 0 if ok else 1

    # 3) Dieselbe Kerze fallend -> klimax_ab
    df.loc[30, "Close"] = 99.0
    art = einfaerben(df)
    ok = art[30] == "klimax_ab"
    print("  %s dieselbe Kerze fallend -> 'klimax_ab' (ist: %s)"
          % ("OK  " if ok else "FEHL", art[30]))
    f += 0 if ok else 1

    # 4) Die ersten Kerzen bleiben 'normal' - kein Blick zurueck moeglich
    ok = all(a == "normal" for a in art[:FENSTER])
    print("  %s erste %d Kerzen bleiben 'normal'" % ("OK  " if ok else "FEHL", FENSTER))
    f += 0 if ok else 1

    # 5) Kosten werden abgezogen
    d2 = pd.DataFrame({"Open": [100.0] * 10, "Close": [100.0] * 10,
                       "High": [100.0] * 10, "Low": [100.0] * 10,
                       "Volume": [1.0] * 10})
    r = ergebnis(d2, 0, 3)
    ok = r is not None and abs(r + K_BASIS) < 1e-9
    print("  %s unveraenderter Kurs -> genau -K_BASIS (%.3f)" % ("OK  " if ok else "FEHL", r or 0))
    f += 0 if ok else 1

    # 6) Nur Volumen hoch, Spanne normal -> 'steigend', nicht 'klimax'
    df2 = pd.DataFrame({"Open": [100.0] * n, "Close": [100.5] * n,
                        "High": [101.0] * n, "Low": [99.0] * n,
                        "Volume": [1000.0] * n})
    df2.loc[30, "Volume"] = 1600.0
    art2 = einfaerben(df2)
    ok = art2[30] == "steigend_auf"
    print("  %s nur Volumen erhoeht -> 'steigend_auf' (ist: %s)"
          % ("OK  " if ok else "FEHL", art2[30]))
    f += 0 if ok else 1

    print("-" * 60)
    print("ALLE TESTS BESTANDEN" if f == 0 else "%d TEST(S) FEHLGESCHLAGEN" % f)
    return 0 if f == 0 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTC/USDT")
    p.add_argument("--timeframe", default="1h")
    p.add_argument("--ab", default="2021-01-01")
    p.add_argument("--horizont", type=int, default=24)
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    if a.selbsttest:
        return selbsttest()
    messen(a.symbol, a.timeframe, a.ab, a.horizont)
    return 0


if __name__ == "__main__":
    sys.exit(main())
