# -*- coding: utf-8 -*-
"""mark_gegenprobe.py - rechnet unser Fibonacci gegen Marks eigene Zahlen.

WOZU
----
`features/chartanalyse.py:232` fuehrt neun Stufen, darunter die zwei
Wurzelverhaeltnisse 0,707 = Wurzel(0,5) und 0,866 = Wurzel(0,75), die kein
Standard-Werkzeug anzeigt. Der Bau stuetzt sich auf Marks eigene, mit
Zahlen beschriftete Charts (prognosen/MARK.md).

Diese Pruefung stellt sicher, dass unsere Formel seine Werte WIRKLICH
trifft - nicht ungefaehr, sondern auf den Cent. Sie prueft in BEIDE
Richtungen: sie muss schweigen, wenn alles stimmt, und anschlagen, wenn
jemand eine Stufe verstellt.

Zwei belegte Faelle, beide aus MARK.md, beide von ihm selbst beschriftet:

  BTCUSD 30 min, 19.08.2026   0 am HOCH  (Aufwaertsbewegung)
  SILBER 4 h,    28.08.2026   0 am HOCH  (Aufwaertsbewegung)

Der Silberfall ist der staerkere Beleg: ein anderer Markt schliesst aus,
dass wir eine BTC-Eigenheit nachgebaut haben.

AENDERT NICHTS. Rechnet nur.

    python mark_gegenprobe.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from features.chartanalyse import FIB_RUECK          # noqa: E402

# ---------------------------------------------------------------- Faelle
# Quelle: prognosen/MARK.md, Abschnitte vom 27.08. und 28.08.2026.
# Marks abgelesene Werte, so wie sie in seinen Charts beschriftet sind.
FAELLE = [
    {
        "name": "BTCUSD 30 min, 19.08.2026",
        "hoch": 64545.0,
        "tief": 62671.0,
        "abgelesen": {
            0.0:   64545.0,
            0.236: 64103.0,
            0.382: 63829.0,
            0.5:   63608.0,
            0.618: 63387.0,
            0.707: 63220.0,
            0.786: 63072.0,
            0.866: 62922.0,
            1.0:   62671.0,
        },
        # Er liest ganze Dollar ab - mehr Genauigkeit gibt das Bild nicht her.
        "toleranz": 1.0,
        "einheit": "$",
    },
    {
        "name": "SILBER 4 h, 28.08.2026",
        "hoch": 71.3602,
        "tief": 54.6917,
        "abgelesen": {
            0.236: 67.4264,
            0.382: 64.9928,
            0.5:   63.0259,
            0.618: 61.0591,
            0.707: 59.5756,
            0.786: 58.2588,
            0.866: 56.9253,
        },
        "toleranz": 0.001,
        "einheit": "",
    },
]


def stufe(hoch, tief, verhaeltnis):
    """Die eine Formel, die im Reiter steht: Hoch minus Spanne mal Verhaeltnis."""
    return hoch - (hoch - tief) * verhaeltnis


def main():
    print("=" * 74)
    print("  MARKS ZAHLEN gegen unsere Formel")
    print("=" * 74)

    fehler = []
    geprueft = 0

    for fall in FAELLE:
        print()
        print("  %s" % fall["name"])
        print("    Anker: Hoch %s  Tief %s  Spanne %s"
              % (fall["hoch"], fall["tief"],
                 round(fall["hoch"] - fall["tief"], 4)))
        print()
        print("    %-10s %14s %14s %12s" % ("Verhaeltnis", "Mark liest ab",
                                            "wir rechnen", "Abweichung"))
        print("    " + "-" * 54)
        for r in sorted(fall["abgelesen"]):
            soll = fall["abgelesen"][r]
            ist = stufe(fall["hoch"], fall["tief"], r)
            ab = abs(ist - soll)
            geprueft += 1
            marke = "" if ab <= fall["toleranz"] else "   DANEBEN"
            if ab > fall["toleranz"]:
                fehler.append((fall["name"], r, soll, ist, ab))
            print("    %-10s %14.4f %14.4f %12.4f%s"
                  % (r, soll, ist, ab, marke))

        # Fuehrt unsere Stufenliste ueberhaupt alle Verhaeltnisse, die er nutzt?
        fehlend = [r for r in fall["abgelesen"] if r not in FIB_RUECK]
        if fehlend:
            print()
            print("    Unsere Stufenliste kennt diese nicht: %s" % fehlend)
            fehler.append((fall["name"], "Stufenliste", fehlend, None, None))

    # ---------------------------------------------------------- Gegentest
    print()
    print("  Gegentest - wuerde diese Pruefung eine verstellte Stufe finden?")
    fall = FAELLE[0]
    # 0,707 durch die naheliegende Verwechslung 0,70 ersetzen
    falsch = stufe(fall["hoch"], fall["tief"], 0.70)
    echt = fall["abgelesen"][0.707]
    ab = abs(falsch - echt)
    print("    0,707 (Wurzel 0,5) statt dessen als 0,70 gerechnet:")
    print("      Mark  %10.2f $" % echt)
    print("      falsch%10.2f $   Abweichung %.2f $" % (falsch, ab))
    if ab > fall["toleranz"]:
        print("      -> wuerde als DANEBEN gemeldet. Die Pruefung greift.")
    else:
        print("      -> wuerde NICHT auffallen. Dann ist sie wertlos.")
        fehler.append(("Gegentest", 0.707, echt, falsch, ab))

    # Und der Fall, um den es eigentlich geht: fehlt eine Stufe ganz?
    print()
    print("  Gegentest 2 - was, wenn 0,707 und 0,866 ganz fehlten?")
    print("    Genau das war der Zustand vor dem 27.08. (Befund 83): das")
    print("    Suchnetz kannte die zwei Wurzelverhaeltnisse nicht, deshalb")
    print("    fand die Ruecktechnik nichts. Heute stehen sie in FIB_RUECK:")
    for r in (0.707, 0.866):
        print("      %s  %s" % (r, "vorhanden" if r in FIB_RUECK else "FEHLT"))
    if 0.707 not in FIB_RUECK or 0.866 not in FIB_RUECK:
        fehler.append(("Stufenliste", "Wurzelwerte", None, None, None))

    print()
    print("-" * 74)
    if fehler:
        print("  DURCHGEFALLEN: %d von %d Stufen daneben." % (len(fehler), geprueft))
        for f in fehler:
            print("    %s" % (f,))
        return 1
    print("  BESTANDEN: alle %d Stufen aus zwei Maerkten getroffen." % geprueft)
    print()
    print("  Damit ist das WERKZEUG bestaetigt - nicht der Nutzen. Ob die")
    print("  Stufen einen handelbaren Vorteil bringen, ist eine andere")
    print("  Frage; die beantwortet mark_messung.py.")
    print("-" * 74)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
