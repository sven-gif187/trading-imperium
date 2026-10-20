# -*- coding: utf-8 -*-
"""warteauftrag_gegenauslese.py - misst die fehlende Zahl zu OFFEN.md C1.

DIE FRAGE
---------
`OFFEN.md` Punkt C1 nennt Warte-Auftraege (Limit-Orders) den groessten
gemessenen Hebel: +0,23 Prozentpunkte je Runde, das Vorzeichen dreht von
-0,065 % auf +0,17 %. Daneben steht aber ein Einwand, der nie geprueft wurde:

    "Offener Einwand: Gegenauslese ist nicht gemessen."

GEGENAUSLESE (adverse selection) heisst: Ein Warte-Auftrag unter dem Markt
wird nur bedient, wenn der Kurs zu dir FAELLT. Steigt er, gehst du leer aus.
Du bekommst also ueberproportional die Faelle, in denen es weiter abwaerts
geht - und verpasst die, in denen es sofort hochgeht.

Eine Rechnung, die unterstellt, jeder Auftrag werde ausgefuehrt, misst nur
die gesparte Gebuehr und uebersieht den Preis dafuer.

WIE GEMESSEN WIRD
-----------------
An echten 15-Minuten-Kerzen (sechs Monate, drei Muenzen). Zu jedem
Kaufzeitpunkt:

  SOFORTKAUF    zum Schlusskurs, Taker-Gebuehr
  WARTE-AUFTRAG X % darunter, gueltig N Kerzen. Ausgefuehrt nur, wenn das
                Tief einer Folgekerze den Preis erreicht - dann Maker-Gebuehr.
                Sonst: kein Handel.

Verglichen wird ueber ALLE Gelegenheiten, nicht nur ueber die ausgefuehrten.
Ein nicht ausgefuehrter Auftrag zaehlt als 0 % - genau das ist der Punkt.

QUELLEN - was belegt ist und was nicht
--------------------------------------
  Kerzen        api.binance.com/api/v3/klines, 15 Minuten, 17.568 je Muenze,
                09.03. bis 08.09.2026. Echte gehandelte Preise.        BELEGT
  Taker 0,25 %  Bybit Help-Center "Bybit Spot Fees Explained", Stand
  Maker 0,10 %  08.03.2026, vom Eigentuemer selbst geprueft. Siehe
                backtest/fees.py:9-14 und
                docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v1.1.md
                                                                        BELEGT
  Fuellregel    NICHT belegt. Siehe unten.

DIE FUELLREGEL IST DIE SCHWACHSTELLE
------------------------------------
docs/messungen_2026-07/BEFUNDE.md:406 sagt ueber die Vorgaenger-Messung F1e:

    "Die Fuellquote in F1e ist eine BERUEHRUNGSQUOTE. Warteschlangen-
     position, Teilfuellung, Ordergroesse gegen Orderbuchtiefe und das
     Verhalten unter Stress sind nicht abgebildet - nur die Obergrenze."

Dasselbe gilt hier. Deshalb werden ZWEI Regeln nebeneinander gerechnet:

  BERUEHRT      Tief <= Limitpreis. Optimistisch - in Wirklichkeit steht man
                in einer Warteschlange und wird nicht zwingend bedient.
  DURCHBROCHEN  Tief <= Limitpreis minus PUFFER. Der Kurs muss unter den
                eigenen Preis GELAUFEN sein, es hat dort also wirklich
                gehandelt. Vorsichtig, aber immer noch keine Garantie.

Die Wahrheit liegt dazwischen. Traegt der Vorteil auch unter der strengen
Regel, ist er belastbar.

AENDERT NICHTS AM BOT. Reines Rechnen auf gespeicherten Kerzen.
"""
import json
import io
import os
import statistics
import sys

ORD = (r"C:\Users\<BENUTZER>\AppData\Local\Temp\claude"
       r"\C--Users-sven7-Desktop-trading-imperium-v6-21-"
       r"\efb0dd76-0fbc-46d7-b8ff-7c7f12f375a5\scratchpad")

TAKER = 0.25          # Prozent je Seite, Bybit EU
MAKER = 0.10          # Prozent je Seite, Warte-Auftrag
HALTEN = 16           # Kerzen bis zum Ausstieg (16 x 15 min = 4 h)
PUFFER = 0.02         # Prozent, die der Kurs unter den Limitpreis
                      # laufen muss, damit die strenge Regel fuellt


def lade(sym):
    p = os.path.join(ORD, "kerzen_%s.json" % sym)
    if not os.path.exists(p):
        return None
    k = json.load(io.open(p, encoding="utf-8"))
    return [(float(x[1]), float(x[2]), float(x[3]), float(x[4])) for x in k]


def messe(kerzen, abstand_pct, gueltig, schritt=8, streng=False):
    """Ein Durchlauf. Gibt (sofort, warte, quote, n) zurueck.

    streng=False  BERUEHRT      Tief <= Limitpreis
    streng=True   DURCHBROCHEN  Tief <= Limitpreis * (1 - PUFFER/100)
    """
    sofort, warte = [], []
    treffer = 0
    gelegenheiten = 0
    i = 0
    grenze = len(kerzen) - gueltig - HALTEN - 1
    while i < grenze:
        ein_sofort = kerzen[i][3]                      # Schlusskurs jetzt
        ziel = ein_sofort * (1 - abstand_pct / 100.0)  # Warte-Auftrag darunter
        fuellt_bei = ziel * (1 - PUFFER / 100.0) if streng else ziel
        gelegenheiten += 1

        # Sofortkauf: raus nach HALTEN Kerzen
        aus = kerzen[i + HALTEN][3]
        sofort.append(100.0 * (aus - ein_sofort) / ein_sofort - 2 * TAKER)

        # Warte-Auftrag: wird er innerhalb von 'gueltig' Kerzen bedient?
        gefuellt = None
        for j in range(i + 1, i + 1 + gueltig):
            if kerzen[j][2] <= fuellt_bei:             # Tief erreicht den Preis
                gefuellt = j
                break
        if gefuellt is None:
            warte.append(0.0)                          # kein Handel, kein Ergebnis
        else:
            treffer += 1
            aus2 = kerzen[min(gefuellt + HALTEN, len(kerzen) - 1)][3]
            warte.append(100.0 * (aus2 - ziel) / ziel - MAKER - TAKER)
        i += schritt
    quote = 100.0 * treffer / gelegenheiten if gelegenheiten else 0
    return sofort, warte, quote, gelegenheiten


def main():
    print("=" * 96)
    print("  WARTE-AUFTRAEGE: was kostet die Gegenauslese?")
    print("  Taker %.2f %% je Seite, Maker %.2f %%, Haltedauer %d Kerzen (%d h)"
          % (TAKER, MAKER, HALTEN, HALTEN // 4))
    print("=" * 96)

    fehlt = [s for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT") if lade(s) is None]
    if fehlt:
        print("\n  Kerzendateien fehlen: %s" % ", ".join(fehlt))
        print("  (Sie werden vom Schwesterskript geholt - nur lesend von Binance.)")
        return 2

    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        k = lade(sym)
        print("\n%s   (%d Kerzen)" % (sym, len(k)))
        print("  Abstand  gueltig   Ausfuehrungs-   SOFORT      WARTE      Unterschied")
        print("           (Kerzen)  quote           netto %%     netto %%    Prozentpunkte")
        print("  " + "-" * 88)
        for abstand in (0.1, 0.25, 0.5):
            for gueltig in (4, 12):
                so, wa, quote, n = messe(k, abstand, gueltig)
                ms, mw = statistics.mean(so), statistics.mean(wa)
                marke = "  <== besser" if mw > ms else ""
                print("  %5.2f %%   %2d       %5.1f %%         %+7.3f    %+7.3f    %+7.3f%s"
                      % (abstand, gueltig, quote, ms, mw, mw - ms, marke))
        print("  (n = %d Gelegenheiten je Zeile)" % n)

    print("\n" + "=" * 96)
    print("  WIE DIE ZAHLEN ZU LESEN SIND")
    print("=" * 96)
    print("  Die Spalte WARTE rechnet ueber ALLE Gelegenheiten, auch die ohne")
    print("  Ausfuehrung - die zaehlen als 0 %. Genau das ist die Gegenauslese:")
    print("  die gesparte Gebuehr nuetzt nichts, wenn der Auftrag bei steigenden")
    print("  Kursen gar nicht erst bedient wird.")
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
