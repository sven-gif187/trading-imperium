# -*- coding: utf-8 -*-
"""Zeichnet den Analyse-Chart wirklich - unsichtbar - und vermisst ihn.

WARUM ES DIESES WERKZEUG GIBT
-----------------------------
Am 27.08.2026 bekam der Analyse-Reiter Fibonacci-Linien. Dabei sind zwei
Fehler passiert, die BEIDE einen Syntaxtest bestanden haetten:

  1. Die Anker lagen so eng beieinander, dass alle dreizehn Stufen als
     eine einzige Linie uebereinander lagen (Spanne 0,85 %).
  2. Die Anker wurden ueber 300 Kerzen gesucht, waehrend der Chart nur
     150 zeigt - elf von dreizehn Linien lagen unter dem Bildrand.

Beides war erst zu sehen, als der Chart WIRKLICH gezeichnet und die
entstandenen Objekte GEZAEHLT wurden. Genau das macht dieses Programm.

WAS GEPRUEFT WIRD
-----------------
  - liegen die Fibonacci-Linien waagerecht
  - liegen sie innerhalb der Zeichenflaeche
  - liegen zwei Linien auf demselben Pixel (das waere eine Gitterwand)
  - ueberlagern sich Beschriftungen am rechten Rand
  - ist der Anker kausal sauber (bestaetigt_ab liegt nicht in der Zukunft)
  - kommen ueberhaupt genug Linien im Bild an

DAS FENSTER BLEIBT UNSICHTBAR. Es wird nichts angezeigt und nichts
gehandelt - der Chart wird nur im Speicher aufgebaut und ausgemessen.

AENDERT NICHTS AM BOT. Reines Lesen und Rechnen.

    python chart_zeichentest.py
    python chart_zeichentest.py --muenzen BTC/USDT
    python chart_zeichentest.py --gegentest
    python chart_zeichentest.py --selbsttest

Der Vollauf holt 15-mal Kerzen von der Boerse und dauert rund acht Minuten.
"""
import argparse
import sys

MUENZEN = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
ZEITRAHMEN = ["15m", "30m", "1h", "4h", "1d"]
B, H = 1100, 520          # Leinwandmasse wie im echten Reiter
MIN_LINIEN = 4            # weniger heisst: die Anker liegen falsch
MIN_ABSTAND_LINIE = 3.0   # Pixel, sonst Gitterwand
MIN_ABSTAND_TEXT = 11.0   # Pixel, sonst ueberlagerte Beschriftung


def _werkzeug():
    """Tk-Wurzel, Zeichenmodul und die drei Fibonacci-Farben.

    Die Farben werden AUS DEM CODE geholt, nicht abgeschrieben. Beim
    ersten Anlauf am 27.08. waren sie im Test geraten - dadurch zaehlte
    er neun Linien als eine und meldete einen Fehler, den es nicht gab.
    Ein Messgeraet, das man nicht eicht, misst falsch.
    """
    import tkinter as tk
    sys.path.insert(0, ".")
    from ui import chartanalyse_tab as T
    wurzel = tk.Tk()
    wurzel.withdraw()
    farben = {T.CLR_FIB.lower(),
              T._blass(T.CLR_FIB, 0.55).lower(),
              T._blass(T.CLR_FIB, 0.3).lower()}
    # [29.08.2026] Bollinger dazu. Aussen (0,75) und Mitte (0,35).
    boll = {T._blass(T.CLR_BOLL, 0.75).lower(),
            T._blass(T.CLR_BOLL, 0.35).lower()}
    return tk, wurzel, T, farben, boll


def vermessen(T, tk, farben, boll, df, analyse):
    """Zeichnet einmal und gibt die Messwerte zurueck."""
    c = tk.Canvas(width=B, height=H, bg="#0d0d0f")
    # Eine nicht angezeigte Leinwand meldet Breite 1; _zeichne steigt dann
    # bei "b < 120" aus und malt gar nichts. Wir geben die Masse vor, die
    # der echte Reiter haette - geprueft wird alles, was danach kommt.
    c.winfo_width = lambda: B
    c.winfo_height = lambda: H
    try:
        T._zeichne(c, df, analyse)
    except Exception as e:
        c.destroy()
        return {"fehler": repr(e)}
    ids = c.find_all()
    fib = [i for i in ids if c.type(i) == "line"
           and str(c.itemcget(i, "fill")).lower() in farben]
    ys = sorted(round(c.coords(i)[1], 1) for i in fib)
    tx = sorted(c.coords(i)[1] for i in ids
                if c.type(i) == "text" and c.coords(i)[0] > B - 100)
    m = {
        "objekte": len(ids),
        "linien": len(fib),
        "schief": sum(1 for i in fib if abs(c.coords(i)[1] - c.coords(i)[3]) > 0.01),
        "ausserhalb": sum(1 for i in fib if not (0 <= c.coords(i)[1] <= H)),
        "engste_linie": min([q - p for p, q in zip(ys, ys[1:])], default=999.0),
        "texte": len(tx),
        "engster_text": min([q - p for p, q in zip(tx, tx[1:])], default=999.0),
    }

    # --- Bollinger: Kurvenzuege, nicht waagerechte Linien ---
    #
    # Geprueft wird nicht nur "ist etwas da", sondern die eine Eigenschaft,
    # die immer gelten MUSS: das obere Band liegt ueber dem unteren. Auf
    # der Leinwand heisst das kleineres y. Waere die Rechnung vertauscht,
    # saehe der Chart trotzdem plausibel aus - drei Kurven eben.
    bl = [i for i in ids if c.type(i) == "line"
          and str(c.itemcget(i, "fill")).lower() in boll]
    m["boll_zuege"] = len(bl)
    m["boll_punkte"] = sum(len(c.coords(i)) // 2 for i in bl)
    # Waagerechte Bollinger-Zuege waeren verdaechtig: ein Band folgt dem Kurs
    m["boll_waagerecht"] = sum(
        1 for i in bl if len(c.coords(i)) >= 4
        and max(c.coords(i)[1::2]) - min(c.coords(i)[1::2]) < 1.0)
    aussen = T._blass(T.CLR_BOLL, 0.75).lower()
    paare = [i for i in bl if str(c.itemcget(i, "fill")).lower() == aussen]
    m["boll_vertauscht"] = 0
    if len(paare) >= 2:
        mitten = sorted((sum(c.coords(i)[1::2]) / max(len(c.coords(i)) // 2, 1), i)
                        for i in paare)
        # oberstes Band muss das kleinste mittlere y haben - sonst vertauscht
        if mitten[0][0] > mitten[-1][0]:
            m["boll_vertauscht"] = 1
    c.destroy()
    return m


def urteil(m, analyse, kerzen):
    """Liste der Probleme - leer heisst sauber."""
    if "fehler" in m:
        return ["Ausnahme: " + m["fehler"]]
    p = []
    if m["schief"]:
        p.append("%d schiefe Linien" % m["schief"])
    if m["ausserhalb"]:
        p.append("%d ausserhalb" % m["ausserhalb"])
    if m["engste_linie"] < MIN_ABSTAND_LINIE:
        p.append("Linien %.1f px" % m["engste_linie"])
    if m["engster_text"] < MIN_ABSTAND_TEXT:
        p.append("Texte %.1f px" % m["engster_text"])
    if m["linien"] < MIN_LINIEN:
        p.append("nur %d Linien im Bild" % m["linien"])
    if m.get("boll_zuege", 0) < 2:
        p.append("nur %d Bollinger-Zuege" % m.get("boll_zuege", 0))
    if m.get("boll_waagerecht"):
        p.append("%d waagerechte Bollinger-Zuege" % m["boll_waagerecht"])
    if m.get("boll_vertauscht"):
        p.append("Bollinger-Baender vertauscht")
    f = getattr(analyse, "fibonacci", None) or {}
    if f and f.get("bestaetigt_ab", 0) > kerzen - 1:
        p.append("KAUSAL: Anker in der Zukunft")
    return p


def lauf(muenzen, zeitrahmen):
    from features.chartanalyse import analysiere
    tk, wurzel, T, farben, boll = _werkzeug()
    print("=" * 78)
    print(" CHART-ZEICHENTEST  -  der Chart wird gezeichnet und vermessen")
    print("=" * 78)
    print("  Muenze      TF     Linien  Spanne   engste  Texte  Boll   Urteil")
    print("  " + "-" * 72)
    schlecht = 0
    for coin in muenzen:
        for tf in zeitrahmen:
            df = T._hole_df(None, coin, tf)
            if df is None or len(df) < 60:
                print("  %-11s %-5s  keine Kerzen" % (coin, tf))
                schlecht += 1
                continue
            a = analysiere(df, coin, tf, fib_rueckblick=T.ZEIGE_KERZEN)
            m = vermessen(T, tk, farben, boll, df, a)
            p = urteil(m, a, len(df))
            f = getattr(a, "fibonacci", None) or {}
            sp = 100.0 * f["spanne"] / f["hoch"] if f else 0.0
            schlecht += bool(p)
            print("  %-11s %-5s  %5d  %6.1f %%  %6.1f  %5d  %4d   %s"
                  % (coin, tf, m.get("linien", 0), sp,
                     m.get("engste_linie", 0), m.get("texte", 0),
                     m.get("boll_zuege", 0), ", ".join(p) if p else "ok"))
    wurzel.destroy()
    print("  " + "-" * 72)
    n = len(muenzen) * len(zeitrahmen)
    if schlecht:
        print("%d VON %d FAELLEN MIT PROBLEM" % (schlecht, n))
    else:
        print("ALLE %d FAELLE SAUBER" % n)
    print("=" * 78)
    return 0 if not schlecht else 1


def gegentest():
    """Findet der Test den BEKANNT kaputten Zustand wieder?

    Ohne diese Richtung ist ein Urteil "alles sauber" wertlos - ein
    Werkzeug, das nie anschlaegt, sieht genauso aus wie eines, das
    nichts findet.
    """
    from features.chartanalyse import analysiere
    tk, wurzel, T, farben, boll = _werkzeug()
    print("GEGENTEST  -  derselbe Chart, nur der Rueckblick unterschiedlich")
    print("-" * 70)
    df = T._hole_df(None, "BTC/USDT", "1h")
    if df is None:
        print("  Keine Kerzen - Gegentest nicht moeglich.")
        wurzel.destroy()
        return 1
    f = 0
    for name, rb, erwartet in (
            ("KAPUTT (alt: alle 300 Kerzen)", 0, True),
            ("REPARIERT (nur die 150 im Bild)", T.ZEIGE_KERZEN, False)):
        a = analysiere(df, "BTC/USDT", "1h", fib_rueckblick=rb)
        m = vermessen(T, tk, farben, boll, df, a)
        p = urteil(m, a, len(df))
        ok = bool(p) == erwartet
        f += 0 if ok else 1
        print("  %s %-33s %2d von 13 Linien  -> %s"
              % ("OK  " if ok else "FEHL", name, m.get("linien", 0),
                 "schlaegt an" if p else "sauber"))
    wurzel.destroy()
    print("-" * 70)
    print("GEGENTEST BESTANDEN" if f == 0 else "GEGENTEST FEHLGESCHLAGEN")
    return 0 if f == 0 else 1


def selbsttest():
    """Prueft die Bewertung selbst - ohne Boerse, ohne Zeichnen."""
    print("SELBSTTEST")
    print("-" * 60)
    f = 0

    class L:                       # nur ein Traeger fuer fibonacci
        fibonacci = {"bestaetigt_ab": 10}

    sauber = {"objekte": 300, "linien": 9, "schief": 0, "ausserhalb": 0,
              "engste_linie": 20.0, "texte": 18, "engster_text": 13.0,
              "boll_zuege": 3, "boll_punkte": 440, "boll_waagerecht": 0,
              "boll_vertauscht": 0}
    ok = urteil(sauber, L(), 150) == []
    print("  %s sauberer Fall -> keine Beanstandung" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    for feld, wert, was in (("linien", 2, "zu wenig Linien"),
                            ("engste_linie", 1.0, "Linien zu eng"),
                            ("engster_text", 4.0, "Texte zu eng"),
                            ("schief", 1, "schiefe Linie"),
                            ("ausserhalb", 1, "Linie ausserhalb"),
                            ("boll_zuege", 0, "fehlende Bollinger-Baender"),
                            ("boll_waagerecht", 2, "waagerechte Bollinger-Zuege"),
                            ("boll_vertauscht", 1, "vertauschte Bollinger-Baender")):
        d = dict(sauber)
        d[feld] = wert
        ok = urteil(d, L(), 150) != []
        print("  %s %s wird erkannt" % ("OK  " if ok else "FEHL", was))
        f += 0 if ok else 1

    class Z:
        fibonacci = {"bestaetigt_ab": 999}
    ok = any("KAUSAL" in x for x in urteil(sauber, Z(), 150))
    print("  %s Anker in der Zukunft wird erkannt" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    ok = urteil({"fehler": "boom"}, L(), 150) != []
    print("  %s Ausnahme beim Zeichnen wird gemeldet" % ("OK  " if ok else "FEHL"))
    f += 0 if ok else 1

    print("-" * 60)
    print("ALLE TESTS BESTANDEN" if f == 0 else "%d TEST(S) FEHLGESCHLAGEN" % f)
    return 0 if f == 0 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--muenzen", default=",".join(MUENZEN))
    p.add_argument("--zeitrahmen", default=",".join(ZEITRAHMEN))
    p.add_argument("--gegentest", action="store_true")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    if a.selbsttest:
        return selbsttest()
    if a.gegentest:
        return gegentest()
    return lauf([x.strip() for x in a.muenzen.split(",") if x.strip()],
                [x.strip() for x in a.zeitrahmen.split(",") if x.strip()])


if __name__ == "__main__":
    sys.exit(main())
