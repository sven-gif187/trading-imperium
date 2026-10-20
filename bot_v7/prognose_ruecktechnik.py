# -*- coding: utf-8 -*-
"""Prognose-Ruecktechnik - mit welcher Methode kam jemand auf seine Zahl?

WAS DAS IST
-----------
Ein Suchwerkzeug. Es bekommt eine fertige Prognose (Zielkurs, Datum der
Aussage, Muenze) und probiert alle gaengigen Chart-Verfahren durch, die
mit den Kursen VON DAMALS moeglich waren. Es meldet, welche Kombination
aus Verfahren und Parametern genau diese Zahl ergibt.

Anlass: Tilo, ein Boersenprofi mit 27 Jahren Erfahrung, nannte am
07.05.2025 fuer BTC eine Triggerzone 97-104K und ein Ziel von 123.000 $.
Beides traf. Seine Chartbilder haben wir nicht - nur die Zahlen. Die
Frage ist also nicht "was hat er gezeichnet", sondern "welche Rechnung
ergibt genau diese Zahlen".

DIE WICHTIGSTE EIGENSCHAFT DIESES WERKZEUGS
-------------------------------------------
Es misst sich selbst.

Wer genug Verfahren mit genug Parametern durchprobiert, trifft JEDE
Zahl. Bei 8 Verhaeltnissen x 200 Swing-Paaren x 3 Richtungen sind das
ueber viertausend Kandidaten - da liegt fast immer einer nah dran. Ein
Treffer allein beweist deshalb gar nichts.

Deshalb rechnet dieses Werkzeug IMMER eine Trivial-Latte mit: Es sucht
dieselbe Anzahl ZUFAELLIGER Ziele im selben Kursbereich und zaehlt, wie
oft die auch getroffen werden. Erst der Abstand zwischen "echtes Ziel"
und "Zufallsziel" sagt etwas aus.

    Trifft die Suche das echte Ziel genauso gut wie ein gewuerfeltes,
    hat sie nichts gefunden - nur bewiesen, dass ihr Netz zu grob ist.

KAUSALITAET
-----------
Es werden ausschliesslich Kerzen bis zum Stichtag benutzt. Ein
Swing-Hoch gilt zudem erst als bekannt, wenn danach genug Kerzen
gelaufen sind (dieselbe Regel wie features/chartanalyse.py). Wer das
weglaesst, findet Methoden, die damals niemand kennen konnte.

AENDERT NICHTS AM BOT. Reines Lesen und Rechnen.

    python prognose_ruecktechnik.py --ziel 123000 --stichtag 2025-05-07
    python prognose_ruecktechnik.py --ziel 123000 --stichtag 2025-05-07 --symbol BTC/USDT
    python prognose_ruecktechnik.py --selbsttest
"""
import argparse
import random
import sys
import time

HIER = __file__

# Die gaengigen Fibonacci-Verhaeltnisse. Mehr aufzunehmen macht das Netz
# feiner und die Trivial-Latte gleich mit - es gewinnt also nichts.
FIB = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0,
       1.272, 1.414, 1.618, 2.0, 2.618, 3.618, 4.236]

# Runde Zahlen, an denen Menschen Ziele festmachen
RUNDE = [1000, 5000, 10000, 25000]


def kerzen_holen(symbol="BTC/USDT", timeframe="1d", ab="2023-01-01"):
    """Historische Kerzen ueber ccxt. Gibt einen DataFrame zurueck."""
    import ccxt
    import pandas as pd
    b = ccxt.binance({"enableRateLimit": True})
    seit = b.parse8601(ab + "T00:00:00Z")
    alle = []
    while True:
        teil = b.fetch_ohlcv(symbol, timeframe, since=seit, limit=1000)
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


def swings(df, weite=3):
    """Bestaetigte Swing-Hochs und -Tiefs.

    Rueckgabe je Punkt: (index, preis, bekannt_ab).
    bekannt_ab = index + weite, weil erst dann die bestaetigenden Kerzen
    gelaufen sind. Vorher wusste niemand, dass es ein Hoch war.
    """
    h, t = df["High"].values, df["Low"].values
    hochs, tiefs = [], []
    for i in range(weite, len(df) - weite):
        fh = h[i - weite:i + weite + 1]
        ft = t[i - weite:i + weite + 1]
        if h[i] == fh.max() and (fh == h[i]).sum() == 1:
            hochs.append((i, float(h[i]), i + weite))
        if t[i] == ft.min() and (ft == t[i]).sum() == 1:
            tiefs.append((i, float(t[i]), i + weite))
    return hochs, tiefs


def kandidaten(df, bis_index):
    """Alle Kurswerte, die sich am Stichtag berechnen liessen.

    Rueckgabe: Liste von (wert, beschreibung).
    """
    out = []
    kurs = float(df["Close"].iloc[bis_index])

    for weite in (2, 3, 5, 8):
        hochs, tiefs = swings(df.iloc[:bis_index + 1], weite)
        hochs = [p for p in hochs if p[2] <= bis_index]
        tiefs = [p for p in tiefs if p[2] <= bis_index]
        if not hochs or not tiefs:
            continue
        # nur die juengsten 12 je Seite - alles andere waere Rauschen
        for hi, hp, _ in hochs[-12:]:
            for ti, tp, _ in tiefs[-12:]:
                if hp <= tp:
                    continue
                spanne = hp - tp
                for r in FIB:
                    out.append((hp + spanne * r,
                                "Fib-Verlaengerung %.3f ueber Hoch %.0f (Tief %.0f, Weite %d)"
                                % (r, hp, tp, weite)))
                    out.append((hp - spanne * r,
                                "Fib-Rueckgang %.3f vom Hoch %.0f (Tief %.0f, Weite %d)"
                                % (r, hp, tp, weite)))
                    out.append((tp + spanne * r,
                                "Fib %.3f ueber Tief %.0f (Hoch %.0f, Weite %d)"
                                % (r, tp, hp, weite)))

    # Runde Zahlen ueber dem Kurs
    for schritt in RUNDE:
        for k in range(1, 6):
            wert = (int(kurs / schritt) + k) * schritt
            out.append((float(wert), "runde Zahl (%d-Schritt)" % schritt))

    # Prozentaufschlaege auf den Kurs
    for p in (10, 15, 20, 25, 30, 40, 50, 75, 100):
        out.append((kurs * (1 + p / 100.0), "%+d %% auf den Kurs" % p))

    # Vielfache des bisherigen Hochs
    hoch_alle = float(df["High"].iloc[:bis_index + 1].max())
    for f in (1.05, 1.1, 1.125, 1.15, 1.2, 1.25, 1.333, 1.5, 1.618, 2.0):
        out.append((hoch_alle * f, "%.3f x bisheriges Hoch %.0f" % (f, hoch_alle)))

    return out


def suche(kand, ziel, toleranz_pct):
    """Alle Kandidaten, die das Ziel innerhalb der Toleranz treffen."""
    tol = abs(ziel) * toleranz_pct / 100.0
    treffer = [(w, b, abs(w - ziel)) for w, b in kand if abs(w - ziel) <= tol]
    treffer.sort(key=lambda x: x[2])
    return treffer


def trivial_latte(kand, ziel, toleranz_pct, spanne_lo, spanne_hi, versuche=400):
    """Wie oft trifft dieselbe Suche ein GEWUERFELTES Ziel?

    Das ist die eigentliche Messung. Findet die Suche bei Zufallszielen
    genauso viele Treffer, hat der echte Treffer nichts zu bedeuten.
    """
    rnd = random.Random(20260826)
    zaehl = []
    for _ in range(versuche):
        z = rnd.uniform(spanne_lo, spanne_hi)
        zaehl.append(len(suche(kand, z, toleranz_pct)))
    zaehl.sort()
    return {
        "mittel": sum(zaehl) / len(zaehl),
        "median": zaehl[len(zaehl) // 2],
        "leer": sum(1 for x in zaehl if x == 0) / len(zaehl) * 100.0,
    }


def bericht(symbol, stichtag, ziel, toleranz, treffer, latte, kurs, n_kand):
    print("=" * 78)
    print(" PROGNOSE-RUECKTECHNIK")
    print("=" * 78)
    print("  Muenze     : %s" % symbol)
    print("  Stichtag   : %s   (nur Kerzen BIS dahin)" % stichtag)
    print("  Kurs damals: %.2f $" % kurs)
    print("  gesuchtes Ziel: %.2f $   (Toleranz %.1f %%)" % (ziel, toleranz))
    print("  durchprobierte Rechnungen: %d" % n_kand)
    print()
    if not treffer:
        print("  KEIN TREFFER. Mit diesen Verfahren ist die Zahl nicht erklaerbar.")
    else:
        print("  Treffer (die zehn naechsten):")
        print("  %-9s %-9s %s" % ("Wert", "Abstand", "Rechnung"))
        print("  " + "-" * 74)
        for w, b, d in treffer[:10]:
            print("  %9.0f %9.0f  %s" % (w, d, b[:56]))
        if len(treffer) > 10:
            print("  ... und %d weitere" % (len(treffer) - 10))
    print()
    print("=" * 78)
    print(" DIE EHRLICHKEITSPRUEFUNG - trifft die Suche auch Zufallsziele?")
    print("=" * 78)
    print("  Bei 400 gewuerfelten Zielen im selben Kursbereich fand dieselbe Suche:")
    print("    im Mittel   : %6.1f Treffer" % latte["mittel"])
    print("    im Median   : %6d Treffer" % latte["median"])
    print("    ohne Treffer: %6.1f %% der Zufallsziele" % latte["leer"])
    print()
    echt = len(treffer)
    if latte["mittel"] <= 0.01:
        urteil = "AUSSAGEKRAEFTIG - Zufallsziele werden praktisch nie getroffen"
    elif echt > latte["mittel"] * 3:
        urteil = "auffaellig - deutlich mehr Treffer als bei Zufall"
    elif echt >= 1 and latte["median"] >= 1:
        urteil = "WERTLOS - ein Zufallsziel wird genauso gut getroffen"
    else:
        urteil = "nicht entscheidbar"
    print("  Echtes Ziel: %d Treffer  |  Zufallsziel: %.1f im Mittel" % (echt, latte["mittel"]))
    print("  URTEIL: %s" % urteil)
    print()
    print("  Lesehilfe: Je feiner das Netz (mehr Verhaeltnisse, mehr Swing-Paare,")
    print("  groessere Toleranz), desto mehr Treffer - auch bei Zufall. Nur der")
    print("  ABSTAND zwischen beiden Zahlen sagt etwas aus.")
    print("=" * 78)


def selbsttest():
    """Gegentest in beide Richtungen."""
    print("SELBSTTEST")
    print("-" * 60)
    fehler = 0

    # 1) Findet die Suche einen Wert, den sie finden MUSS?
    kand = [(100.0, "test-a"), (200.0, "test-b")]
    t = suche(kand, 100.0, 1.0)
    ok = len(t) == 1 and t[0][0] == 100.0
    print("  %s exakter Wert wird gefunden" % ("OK  " if ok else "FEHL"))
    fehler += 0 if ok else 1

    # 2) Meldet sie NICHTS, wenn nichts passt?
    t = suche(kand, 500.0, 1.0)
    ok = len(t) == 0
    print("  %s weit entfernter Wert wird NICHT gemeldet" % ("OK  " if ok else "FEHL"))
    fehler += 0 if ok else 1

    # 3) Waechst die Trefferzahl mit der Toleranz?
    kand2 = [(float(x), "x") for x in range(90, 111)]
    a = len(suche(kand2, 100.0, 1.0))
    b = len(suche(kand2, 100.0, 10.0))
    ok = b > a
    print("  %s groessere Toleranz -> mehr Treffer (%d -> %d)" % ("OK  " if ok else "FEHL", a, b))
    fehler += 0 if ok else 1

    # 4) Erkennt die Trivial-Latte ein zu grobes Netz?
    dicht = [(float(x), "x") for x in range(1000, 2000)]
    lat = trivial_latte(dicht, 1500.0, 5.0, 1000, 2000, versuche=50)
    ok = lat["mittel"] > 10
    print("  %s dichtes Netz wird als wertlos erkannt (%.0f Zufallstreffer)"
          % ("OK  " if ok else "FEHL", lat["mittel"]))
    fehler += 0 if ok else 1

    # 5) Kausalitaet: kennt swings() nur bestaetigte Punkte?
    try:
        import pandas as pd
        d = pd.DataFrame({"High": [1, 2, 9, 2, 1, 1, 1],
                          "Low":  [1, 1, 1, 1, 1, 1, 1]})
        h, _ = swings(d, weite=2)
        ok = len(h) == 1 and h[0][0] == 2 and h[0][2] == 4
        print("  %s Swing-Hoch bei Index 2 ist erst ab Index 4 bekannt" % ("OK  " if ok else "FEHL"))
        fehler += 0 if ok else 1
    except Exception as e:
        print("  FEHL Kausalitaetstest: %s" % e); fehler += 1

    print("-" * 60)
    print("ALLE TESTS BESTANDEN" if fehler == 0 else "%d TEST(S) FEHLGESCHLAGEN" % fehler)
    return 0 if fehler == 0 else 1


def main():
    p = argparse.ArgumentParser(description="Mit welcher Methode kam jemand auf seine Zahl?")
    p.add_argument("--ziel", type=float, help="der vorhergesagte Kurs")
    p.add_argument("--stichtag", help="Datum der Aussage, z.B. 2025-05-07")
    p.add_argument("--symbol", default="BTC/USDT")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--toleranz", type=float, default=0.5,
                   help="Trefferbreite in Prozent (Vorgabe 0,5)")
    p.add_argument("--ab", default="2023-01-01", help="ab wann Kerzen geladen werden")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()

    if a.selbsttest:
        return selbsttest()
    if not a.ziel or not a.stichtag:
        p.error("--ziel und --stichtag werden gebraucht (oder --selbsttest)")

    df = kerzen_holen(a.symbol, a.timeframe, a.ab)
    if df is None or df.empty:
        print("Keine Kerzen erhalten.")
        return 1
    bis = df[df["zeit"] <= a.stichtag + "T23:59:59Z"]
    if len(bis) < 60:
        print("Zu wenige Kerzen bis zum Stichtag (%d)." % len(bis))
        return 1
    i = len(bis) - 1
    kurs = float(bis["Close"].iloc[-1])

    kand = kandidaten(bis, i)
    treffer = suche(kand, a.ziel, a.toleranz)
    lo = float(bis["Low"].min())
    hi = float(bis["High"].max()) * 2.0
    latte = trivial_latte(kand, a.ziel, a.toleranz, lo, hi)

    bericht(a.symbol, a.stichtag, a.ziel, a.toleranz, treffer, latte, kurs, len(kand))
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ==========================================================================
#  MEHRERE ZAHLEN AUF EINMAL - hier wird es erst aussagekraeftig
# ==========================================================================
#
# Eine einzelne Zahl laesst sich immer erklaeren. Gemessen am 27.08.2026:
# Bei 17.238 Kandidaten und 0,01 % Toleranz traf ein GEWUERFELTES Ziel im
# Mittel 1,5-mal - eine echte Prognose 5-mal. Das reicht nicht.
#
# Anders wird es, wenn jemand MEHRERE Linien aus DEMSELBEN Chart nennt.
# Dann sucht man nicht mehr eine Rechnung fuer eine Zahl, sondern EIN
# Raster, das moeglichst viele Zahlen gleichzeitig erklaert. Die
# Wahrscheinlichkeit, dass ein zufaelliges Hoch-Tief-Paar fuenf von neun
# Marken trifft, ist winzig - und genau das wird hier mitgemessen.

def raster_treffer(hoch, tief, ziele, toleranz_pct):
    """Wie viele der `ziele` erklaert EIN Fibonacci-Raster (hoch, tief)?

    Rueckgabe: (anzahl, [(ziel, verhaeltnis, wert, abstand), ...])
    """
    if hoch <= tief:
        return 0, []
    spanne = hoch - tief
    marken = []
    for r in FIB:
        marken.append((r, hoch - spanne * r, "Rueckgang %.3f"))
        marken.append((r, tief + spanne * r, "ab Tief %.3f"))
        marken.append((r, hoch + spanne * r, "Verlaengerung %.3f"))
    marken.append((0.0, hoch, "Hoch %.0f"))
    marken.append((1.0, tief, "Tief %.0f"))
    getroffen = []
    for z in ziele:
        tol = abs(z) * toleranz_pct / 100.0
        beste = None
        for r, w, art in marken:
            d = abs(w - z)
            if d <= tol and (beste is None or d < beste[3]):
                beste = (z, art % r, w, d)
        if beste:
            getroffen.append(beste)
    return len(getroffen), getroffen


def raster_suchen(df, bis_index, ziele, toleranz_pct=0.5, weiten=(2, 3, 5, 8, 13)):
    """Sucht das Hoch-Tief-Paar, das die meisten Ziele erklaert."""
    hochs_alle, tiefs_alle = [], []
    for w in weiten:
        h, t = swings(df.iloc[:bis_index + 1], w)
        hochs_alle += [p for p in h if p[2] <= bis_index]
        tiefs_alle += [p for p in t if p[2] <= bis_index]
    # auch die offensichtlichen Extremwerte des ganzen Fensters
    hochs_alle.append((bis_index, float(df["High"].iloc[:bis_index + 1].max()), 0))
    tiefs_alle.append((bis_index, float(df["Low"].iloc[:bis_index + 1].min()), 0))
    hp = sorted({round(p[1], 2) for p in hochs_alle})
    tp = sorted({round(p[1], 2) for p in tiefs_alle})

    ergebnisse = []
    for h in hp:
        for t in tp:
            n, det = raster_treffer(h, t, ziele, toleranz_pct)
            if n >= 2:
                ergebnisse.append((n, h, t, det))
    ergebnisse.sort(key=lambda x: (-x[0], sum(d[3] for d in x[3])))
    return ergebnisse, len(hp), len(tp)


def raster_latte(df, bis_index, anzahl_ziele, spanne_lo, spanne_hi,
                 toleranz_pct=0.5, versuche=60, weiten=(2, 3, 5, 8, 13)):
    """Trivial-Latte: wie viele ZUFAELLIGE Marken erklaert das beste Raster?"""
    rnd = random.Random(20260827)
    beste = []
    for _ in range(versuche):
        ziele = [rnd.uniform(spanne_lo, spanne_hi) for _ in range(anzahl_ziele)]
        erg, _, _ = raster_suchen(df, bis_index, ziele, toleranz_pct, weiten)
        beste.append(erg[0][0] if erg else 0)
    beste.sort()
    return {"mittel": sum(beste) / len(beste), "median": beste[len(beste) // 2],
            "max": beste[-1]}
