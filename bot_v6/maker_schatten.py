# -*- coding: utf-8 -*-
"""Lohnt sich der Wechsel von Sofort- auf Warte-Auftraegen?

DIE FRAGE
---------
Der Bot kauft ausschliesslich mit Sofort-Auftraegen (Market Order, Fach-
begriff "Taker"): er nimmt den Preis, der gerade da ist, und zahlt dafuer
0,25 % je Seite. Ein Warte-Auftrag (Limit Order, "Maker") legt ein Angebot
hin und wartet, bis jemand zugreift - dafuer nur 0,10 % je Seite.

Eine volle Runde kostet damit 0,505 % statt rund 0,20 %. Der mittlere
Trailing-Ausstieg bringt brutto +0,44 % - er liegt also UNTER der einen
und UEBER der anderen Kostenschwelle. Genau daran haengt, ob das System
ueberhaupt gewinnen kann.

SVENS EINWAND, der genau richtig ist
------------------------------------
"Was, wenn er nicht kaufen kann? Verlieren wir dann nicht Zeit und damit
gute Einstiege?"

Ein Warte-Auftrag kann liegenbleiben. Laeuft der Kurs weg, ist der
Einstieg verpasst, den ein Sofort-Auftrag sicher gehabt haette. Die
Ersparnis ist also nur die halbe Rechnung - die andere Haelfte ist der
entgangene Gewinn. Dieses Programm misst BEIDE.

DIE METHODE
-----------
Der Forschungs-Sammler schreibt seit dem 31.07. alle ~60 Sekunden Bid und
Ask je Muenze mit. Damit laesst sich jeder Zeitpunkt nachspielen:

    Sofort-Auftrag : kauft JETZT zum Ask.
    Warte-Auftrag  : legt sich auf den Bid und wartet.
                     Er wird gefuellt, sobald der Ask auf diesen Preis
                     faellt - also erst, wenn der Markt zu ihm herunter
                     kommt.

Fuer jeden Zeitpunkt wird geprueft, ob das innerhalb von 1, 5, 15, 30 und
60 Minuten passiert waere. Daraus ergeben sich zwei Zahlen:

    Ausfuehrungsquote  wie oft der Warte-Auftrag ueberhaupt zum Zug kaeme
    Ersparnis          Spanne + 0,15 Prozentpunkte Gebuehrenvorteil

Und die entscheidende Gegenrechnung:

    entgangener Gewinn  wie weit der Kurs in den Faellen davonlief, in
                        denen NICHT gefuellt wurde

Erst beide zusammen beantworten die Frage.

EHRLICHKEIT
-----------
- Gemessen wird nur, was in den Sammeldaten steht. Es wird nichts
  hochgerechnet und keine Ausfuehrung unterstellt, die nicht durch einen
  echten Kurs gedeckt ist.
- Die Daten kommen alle ~60 bis 120 Sekunden. Kurze Ausschlaege zwischen
  zwei Messpunkten sind unsichtbar - die Ausfuehrungsquote ist deshalb
  eher zu NIEDRIG geschaetzt, also zu Ungunsten des Warte-Auftrags.
- Ein echter Warte-Auftrag stuende in der Warteschlange hinter anderen.
  Auch das ist hier nicht abgebildet und wirkt in dieselbe Richtung.
- Gerechnet wird je Muenze getrennt, weil die Spanne sich um mehr als das
  Tausendfache unterscheidet (BTC 0,03 bp, NEAR 33 bp).

Reine Leseoperation. Aendert nichts am Bot und nichts am Handelspfad.

Aufruf:  python maker_schatten.py
         python maker_schatten.py --muenze BTC/USDC
"""
import csv
import os
import statistics as st
import sys
from collections import defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))
CAPTURE = os.path.join(HIER, "docs", "forschungsprogramm_2026-07", "capture")

# [E13 KLEINIGKEITEN 15.10.2026] Zielboerse seit 14.10.2026: Bitvavo USDC (Z1, pruefstand/gebuehren.json),
# Maker = Taker = 0,05 % je Seite. Der Gebuehrenvorteil des Warte-Auftrags ist damit NULL;
# messbar bleibt nur die halbe Spanne (BTC ~1,4 bp, SOL ~2,9 bp) gegen verpasste Einstiege.
# Vorher Bybit EU: TAKER_PCT = 0.25, MAKER_PCT = 0.10.
TAKER_PCT = 0.05
MAKER_PCT = 0.05
# Wartezeiten, die geprueft werden (Minuten).
FENSTER_MIN = (1, 5, 15, 30, 60)
# Muenzen, die der Bot wirklich handelt - fuer die zaehlt das Ergebnis.
ECHTE = ("BTC/USDC", "ETH/USDC", "SOL/USDC")


def ticker_lesen(nur_muenze=None):
    """Alle Bid/Ask-Messpunkte je Muenze, zeitlich sortiert."""
    daten = defaultdict(list)
    if not os.path.isdir(CAPTURE):
        print(f"  Sammelordner fehlt: {CAPTURE}")
        return daten

    for tag in sorted(os.listdir(CAPTURE)):
        pfad = os.path.join(CAPTURE, tag)
        if not os.path.isdir(pfad):
            continue
        for datei in sorted(os.listdir(pfad)):
            if not datei.startswith("ticker_") or not datei.endswith(".csv"):
                continue
            roh = datei[len("ticker_"):-len(".csv")]        # z.B. BTCUSDC
            if roh.endswith("USDC"):
                muenze = roh[:-4] + "/USDC"
            elif roh.endswith("USDT"):
                muenze = roh[:-4] + "/USDT"
            else:
                continue
            if nur_muenze and muenze != nur_muenze:
                continue
            try:
                with open(os.path.join(pfad, datei), encoding="utf-8") as f:
                    for z in csv.DictReader(f):
                        try:
                            ts = int(z["ts"]) / 1000.0
                            bid = float(z["bid"])
                            ask = float(z["ask"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        if bid > 0 and ask > 0 and ask >= bid:
                            daten[muenze].append((ts, bid, ask))
            except Exception:
                continue

    for m in daten:
        daten[m].sort(key=lambda x: x[0])
    return daten


def messen(punkte, fenster_sek):
    """Simuliert je Zeitpunkt einen Warte-Auftrag auf dem Bid.

    Rueckgabe:
        gefuellt   Liste der Ersparnisse in Prozentpunkten
        verpasst   Liste der Kursbewegungen, wo NICHT gefuellt wurde
    """
    gefuellt, verpasst = [], []
    n = len(punkte)

    for i in range(n):
        ts, bid, ask = punkte[i]
        if bid <= 0:
            continue
        treffer = False
        letzter_ask = ask
        j = i + 1
        while j < n and punkte[j][0] - ts <= fenster_sek:
            if punkte[j][2] <= bid:        # Ask faellt auf unser Gebot
                treffer = True
                break
            letzter_ask = punkte[j][2]
            j += 1
        if j == i + 1 and j >= n:
            continue                        # kein Folgepunkt vorhanden

        if treffer:
            # Ersparnis: die Spanne, die wir nicht bezahlen, plus der
            # Gebuehrenvorteil auf beiden Seiten der Runde.
            spanne_pct = (ask - bid) / ask * 100
            gefuellt.append(spanne_pct + 2 * (TAKER_PCT - MAKER_PCT))
        else:
            # Nicht gefuellt: wie weit ist der Markt davongelaufen?
            # Positiv = teurer geworden = echter entgangener Einstieg.
            verpasst.append((letzter_ask - ask) / ask * 100)
    return gefuellt, verpasst


def main():
    nur = None
    if "--muenze" in sys.argv:
        try:
            nur = sys.argv[sys.argv.index("--muenze") + 1]
        except IndexError:
            pass

    print("=" * 94)
    print(" WARTE-AUFTRAG STATT SOFORT-AUFTRAG - lohnt sich der Wechsel?")
    print("=" * 94)
    print(f"\n  Sofort (Taker) {TAKER_PCT} % je Seite  gegen  "
          f"Warte (Maker) {MAKER_PCT} % je Seite")
    print(f"  Gebuehrenvorteil je Runde: "
          f"{2 * (TAKER_PCT - MAKER_PCT):.2f} Prozentpunkte, dazu die Spanne.")

    daten = ticker_lesen(nur)
    if not daten:
        print("\n  Keine Ticker-Daten gefunden.")
        return 1

    print(f"\n  Datengrundlage:")
    for m in sorted(daten):
        p = daten[m]
        tage = (p[-1][0] - p[0][0]) / 86400 if len(p) > 1 else 0
        print(f"    {m:<11} {len(p):>6} Messpunkte ueber {tage:>5.1f} Tage")

    for fenster in FENSTER_MIN:
        print("\n" + "=" * 94)
        print(f" WARTEZEIT {fenster} MINUTEN")
        print("=" * 94)
        print(f"\n  {'Muenze':<11} {'Faelle':>7} {'gefuellt':>9} "
              f"{'Ersparnis':>11} {'entgangen':>11}  Netto-Urteil")
        print("  " + "-" * 88)

        for m in sorted(daten):
            g, v = messen(daten[m], fenster * 60)
            ges = len(g) + len(v)
            if ges < 50:
                print(f"  {m:<11} {ges:>7}  zu wenige Faelle")
                continue
            quote = 100.0 * len(g) / ges
            ersparnis = st.mean(g) if g else 0.0
            entgangen = st.mean(v) if v else 0.0
            # Erwartungswert: mit der Quote gewichtete Ersparnis, minus
            # der Kursbewegung in den Faellen, wo nicht gefuellt wurde.
            netto = (quote / 100.0) * ersparnis - (1 - quote / 100.0) * entgangen
            marke = " *" if m in ECHTE else ""
            urteil = ("lohnt sich" if netto > 0.05
                      else "lohnt nicht" if netto < -0.05
                      else "unentschieden")
            print(f"  {m:<11}{marke:<1} {ges:>6} {quote:>8.1f}% "
                  f"{ersparnis:>+10.3f}% {entgangen:>+10.3f}%  "
                  f"{netto:>+7.3f} {urteil}")

    print("\n" + "=" * 94)
    print(" WIE DAS ZU LESEN IST")
    print("=" * 94)
    print("""
  gefuellt   Anteil der Zeitpunkte, an denen der Warte-Auftrag innerhalb
             der Wartezeit zum Zug gekommen waere.
  Ersparnis  Was er in DIESEN Faellen gespart haette: die nicht bezahlte
             Spanne plus 0,30 Prozentpunkte Gebuehrenvorteil je Runde.
  entgangen  Wie weit der Kurs in den ANDEREN Faellen davonlief - Svens
             Einwand, in Zahlen. Ein positiver Wert heisst: es wurde
             teurer, der Einstieg war also wirklich verpasst.
  Netto      Beides gegeneinander verrechnet. Nur diese Spalte zaehlt.

  * = Muenze, die der Bot wirklich handelt.

  VORSICHT: Die Messpunkte liegen 60 bis 120 Sekunden auseinander. Kurze
  Ausschlaege dazwischen sind unsichtbar, und die Warteschlange an der
  Boerse ist nicht abgebildet. Beides macht die Ausfuehrungsquote eher zu
  NIEDRIG - das Ergebnis ist also zu Ungunsten des Warte-Auftrags verzerrt.
  Ein positives Netto ist damit belastbarer als ein negatives.

  Diese Messung ersetzt KEINEN Echtbetrieb. Sie sagt, ob sich ein
  Schattenlauf mit echten Limit-Auftraegen lohnt - nicht mehr.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
