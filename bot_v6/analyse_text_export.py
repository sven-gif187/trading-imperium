# -*- coding: utf-8 -*-
"""Schreibt den Textblock des Analyse-Reiters fuer ALLE Zeitrahmen in eine Datei.

WOZU
----
Sven laesst sich den Analyse-Reiter von einem zweiten Claude am lebenden
Bild erklaeren. Die Bilder kann er schicken - den Text darunter aus dem
Fenster zu kopieren ist umstaendlich. Dieses Programm erzeugt ihn
stattdessen zum Kopieren, fuer jeden Zeitrahmen einmal.

WICHTIG: Es ruft DIESELBEN Funktionen auf wie der Reiter
(`ui.chartanalyse_tab._hole_df`, `features.chartanalyse.analysiere`,
`ui.chartanalyse_tab._text`). Damit steht in der Datei Wort fuer Wort
das, was auch im Fenster steht - keine Nachbildung, die auseinanderlaufen
kann.

ZUSAETZLICH zum Fenstertext werden ausgegeben:
  - alle DREIZEHN Fibonacci-Stufen. Im Bild sind nur fuenf beschriftet
    (die zwei Anker und 0,382 / 0,5 / 0,618), damit keine Textwand
    entsteht. Wer das Bild liest, sieht die uebrigen acht Linien, kann
    sie aber nicht benennen.
  - die Bollinger-Werte am rechten Rand, also am aktuellen Kurs.

AENDERT NICHTS AM BOT. Reines Lesen und Rechnen.

    python analyse_text_export.py
    python analyse_text_export.py --coin ETH/USDC
    python analyse_text_export.py --zeitrahmen 1h,4h,1d
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ZEITRAHMEN = ["15m", "30m", "1h", "4h", "1d", "1w", "1M"]
NAMEN = {"15m": "15 Minuten", "30m": "30 Minuten", "1h": "1 Stunde",
         "4h": "4 Stunden", "1d": "1 Tag", "1w": "1 Woche", "1M": "1 Monat"}


def bollinger_am_rand(df, periode, abweichung):
    """Die drei Bollinger-Werte an der letzten Kerze - oder None."""
    try:
        mid = df["Close"].rolling(periode).mean()
        std = df["Close"].rolling(periode).std()
        o = float((mid + abweichung * std).iloc[-1])
        m = float(mid.iloc[-1])
        u = float((mid - abweichung * std).iloc[-1])
        if o != o or m != m or u != u:       # NaN
            return None
        return o, m, u
    except Exception:
        return None


def block(coin, tf, T, analysiere):
    """Ein Zeitrahmen als fertiger Textblock."""
    df = T._hole_df(None, coin, tf)
    if df is None or len(df) < 60:
        return "  (keine Kerzen fuer %s %s)" % (coin, tf)

    a = analysiere(df, coin, tf, fib_rueckblick=T.ZEIGE_KERZEN)
    if a is None:
        return "  (Analyse lieferte nichts fuer %s %s)" % (coin, tf)

    z = df.tail(T.ZEIGE_KERZEN)
    t = ["=" * 74,
         "  %s   Zeitrahmen %s (%s)" % (coin, tf, NAMEN.get(tf, tf)),
         "=" * 74,
         "  Im Bild: %d Kerzen von %d geladenen" % (len(z), len(df)),
         ""]

    # --- der Fenstertext, unveraendert ---
    t.append(T._text(a))

    # --- Fibonacci: alle dreizehn, nicht nur die fuenf beschrifteten ---
    f = getattr(a, "fibonacci", None) or {}
    if f.get("stufen"):
        spanne_pct = 100.0 * f["spanne"] / f["hoch"] if f["hoch"] else 0.0
        t += ["", "  FIBONACCI",
              "    Richtung %s   (bei AUF liegt die 0 am Hoch, bei AB am Tief)"
              % f.get("richtung", "?"),
              "    Anker Hoch {:>12,.2f}".format(f["hoch"]),
              "    Anker Tief {:>12,.2f}".format(f["tief"]),
              "    Spanne     {:>12,.2f}   = {:.2f} % des Hochs".format(
                  f["spanne"], spanne_pct),
              "",
              "    Verhaeltnis        Preis   Abstand zum Kurs   Art"]
        for r, preis, art in f["stufen"]:
            abst = 100.0 * (preis - a.preis) / a.preis if a.preis else 0.0
            marke = " *" if (art == "anker" or round(r, 3) in (0.382, 0.5, 0.618)) else "  "
            t.append("    {:<8s} {:>12,.2f}   {:+7.2f} %          {:<6s}{}".format(
                str(r).replace(".", ","), preis, abst, art, marke))
        t.append("    (* = im Bild beschriftet, die uebrigen sind nur gezeichnet)")

    # --- Bollinger am rechten Rand ---
    bb = bollinger_am_rand(df, T.BOLL_PERIODE, T.BOLL_ABWEICHUNG)
    if bb:
        o, m, u = bb
        breite = 100.0 * (o - u) / m if m else 0.0
        if a.preis >= o:      lage = "AM ODER UEBER dem oberen Band"
        elif a.preis <= u:    lage = "AM ODER UNTER dem unteren Band"
        elif a.preis > m:     lage = "zwischen Mitte und oberem Band"
        else:                 lage = "zwischen unterem Band und Mitte"
        t += ["", "  BOLLINGER (%d Perioden, %g Standardabweichungen)"
              % (T.BOLL_PERIODE, T.BOLL_ABWEICHUNG),
              "    oberes Band  {:>12,.2f}".format(o),
              "    Mitte        {:>12,.2f}".format(m),
              "    unteres Band {:>12,.2f}".format(u),
              "    Bandbreite  %11.2f %%   (Abstand der Baender, gemessen an der Mitte)" % breite,
              "    Der Kurs liegt %s." % lage]
    return "\n".join(t)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--coin", default="BTC/USDC")
    p.add_argument("--zeitrahmen", default=",".join(ZEITRAHMEN))
    p.add_argument("--datei", default="ANALYSE_TEXTE.txt")
    args = p.parse_args()

    from features.chartanalyse import analysiere
    from ui import chartanalyse_tab as T

    tfs = [x.strip() for x in args.zeitrahmen.split(",") if x.strip()]
    jetzt = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    kopf = [
        "ANALYSE-REITER - Textblock je Zeitrahmen",
        "Muenze: %s        Stand: %s" % (args.coin, jetzt),
        "",
        "Erzeugt mit analyse_text_export.py. Es sind DIESELBEN Funktionen,",
        "die auch das Fenster benutzt - der Text ist also Wort fuer Wort der,",
        "der unter dem Chart steht. Ergaenzt um alle dreizehn Fibonacci-Stufen",
        "(im Bild sind nur fuenf beschriftet) und die Bollinger-Werte am",
        "rechten Rand.",
        "",
        "ACHTUNG: Momentaufnahme. Die Zahlen aendern sich mit jeder Kerze -",
        "sie passen nur zu Bildern, die zur selben Zeit entstanden sind.",
        "",
    ]
    teile = [ "\n".join(kopf) ]
    for tf in tfs:
        print("  ... %s" % tf)
        teile.append(block(args.coin, tf, T, analysiere))
    text = "\n\n".join(teile) + "\n"

    with open(args.datei, "w", encoding="utf-8") as f:
        f.write(text)
    print("\nGeschrieben: %s  (%d Zeilen)" % (args.datei, text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
