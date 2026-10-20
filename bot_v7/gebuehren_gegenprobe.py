"""Gegenprobe: wird die Kaufgebuehr doppelt abgezogen?

NUR LESEND. Aendert nichts, handelt nicht, schreibt keine Datenbank.

WARUM ES DIESES SKRIPT GIBT
---------------------------
Am 18.08.2026 fiel beim Nachrechnen EINES Handels auf, dass das
gebuchte Ergebnis nicht zum Kursverlauf passt:

    BTC gekauft 13.08. fuer 103.34 $, verkauft 18.08. fuer 103.88 $
    Gebuehren 0.2584 $ (Kauf) + 0.2597 $ (Verkauf)
    von Hand:  +0.277 $      gebucht: +0.019 $
    Differenz: 0.2583 $  ==  exakt die Kaufgebuehr

Die Ursache steht im Code und ist nachlesbar:

    execution/engine.py:354   amount = intent.amount_usd     # Mittelabfluss
                              fee    = amount * fee_rate     # AUS diesem Betrag
                              qty    = (amount - fee) / price
                       :401   result.filled_cost = amount    # <- Gebuehr ist DRIN

    app.py:1861               cost_basis = filled_cost + fee # <- und nochmal DRAUF
    app.py:2933               _kosten    = filled_cost + fee # dasselbe beim DCA

Der Kommentar an beiden Stellen ([E9-KOSTENBASIS]) sagt "echter
Mittelabfluss inkl. Kaufgebuehr" - der war schon drin. Der Fix vom
29.07. hat einen echten Fehler behoben (die Kaufgebuehr fehlte damals
tatsaechlich) und ist dabei um genau eine Gebuehr zu weit gegangen.

WAS DAS BEDEUTET
----------------
Jeder abgeschlossene Handel wird um eine Kaufgebuehr zu SCHLECHT
gebucht - vor dem 13.08. um 0,10 % des Kaufbetrags, seither um 0,25 %.
Kein Geld ist verloren gegangen, es ist falsch aufgeschrieben. Alle
Auswertungen, die auf dem gebuchten Ergebnis beruhen, fallen dadurch
zu pessimistisch aus.

WIE HIER GERECHNET WIRD - und was zuerst schiefging
---------------------------------------------------
Zwei Anlaeufe waren falsch und stehen hier als Warnung:

1. First-in-first-out ueber alle Kauflose (wie core/state_store.py:180
   es fuers Journal tut). Unbrauchbar: 449 Verkaeufen stehen 546 Kaeufe
   gegenueber. Die nie geschlossenen Lose - Sparplan und Altbestand -
   bleiben vorn in der Schlange liegen, und jeder neue Verkauf wird
   gegen ein uraltes Los gerechnet.
2. "Je Muenze eine offene Position". Scheitert am selben Rest: der
   staut sich in der Position auf und verfaelscht den Einstand.

Beide lieferten Fantasiewerte (Breakeven-Ausstiege mit +4,90 $ Schnitt
bei 150-$-Positionen) - und beide sahen auf den ersten Blick plausibel
aus. Deshalb der dritte, tragfaehige Weg: KEIN Nachbau von Positionen,
sondern der doppelt gezogene Betrag direkt aus dem Verkaufssatz:

    Gebuehrensatz  = Verkaufsgebuehr / (Preis * Menge)      exakt
    Einstiegspreis = Verkaufspreis / (1 + Ergebnis% / 100)  exakt
    Kaufbetrag     = Menge * Einstiegspreis / (1 - Satz)
    Kaufgebuehr    = Kaufbetrag * Satz        <- der doppelt gezogene Betrag

Jeder Wert stammt aus demselben Satz, nichts wird zugeordnet. Probe am
BTC-Handel oben: 0.2584 $, und 0.019 + 0.258 = 0.277 - genau der von
Hand nachgerechnete Wert.

GRENZE DER AUSSAGE, ausdruecklich
---------------------------------
Bei Positionen mit Nachkauf (DCA) wurde die Gebuehr JE TRANCHE doppelt
gezogen. Dieses Skript sieht nur die letzte und rechnet damit zu
vorsichtig. Die genannten Betraege sind also eine UNTERGRENZE.

Aufruf:  python gebuehren_gegenprobe.py
"""
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
TRADES = os.path.join(HIER, "data_store", "trades_v5.json")

E6_START = "2026-08-13T13:21"     # Beginn des Messfensters (0,25 % Gebuehr)


def doppelbetrag(t):
    """Wie viel wurde bei diesem Verkauf zu viel abgezogen? None = unklar."""
    preis = float(t.get("price") or 0)
    menge = float(t.get("qty") or 0)
    gebuehr = float(t.get("fee") or 0)
    pnl_pct = t.get("pnl_pct")
    if preis <= 0 or menge <= 0 or gebuehr <= 0 or pnl_pct is None:
        return None
    umsatz = preis * menge
    satz = gebuehr / umsatz
    if not 0.0005 < satz < 0.01:          # unplausibel -> lieber nichts sagen
        return None
    einstieg = preis / (1 + float(pnl_pct) / 100)
    if einstieg <= 0:
        return None
    kaufbetrag = menge * einstieg / (1 - satz)
    return kaufbetrag * satz


def main():
    if not os.path.exists(TRADES):
        print(f"Nicht gefunden: {TRADES}")
        return 1
    with open(TRADES, encoding="utf-8") as f:
        trades = json.load(f)

    verkaeufe = [t for t in trades if (t.get("type") or "").upper() == "SELL"]
    zeilen, unklar = [], 0
    for t in verkaeufe:
        d = doppelbetrag(t)
        if d is None:
            unklar += 1
            continue
        zeilen.append({
            "zeit": t.get("time", ""), "muenze": t.get("coin", ""),
            "gebucht": float(t.get("pnl") or 0), "zuviel": d,
            "grund": t.get("reason", "") or ""})

    if not zeilen:
        print("Keine auswertbaren Verkaeufe gefunden.")
        return 1

    gebucht = sum(z["gebucht"] for z in zeilen)
    zuviel = sum(z["zuviel"] for z in zeilen)

    print("=" * 66)
    print("GEBUEHREN-GEGENPROBE - wird die Kaufgebuehr doppelt gezogen?")
    print("=" * 66)
    print(f"Verkaeufe insgesamt        : {len(verkaeufe)}")
    print(f"davon auswertbar           : {len(zeilen)}"
          + (f"   (unklar: {unklar})" if unklar else ""))
    print()
    print("Nur die auswertbaren Verkaeufe - NICHT das Gesamtergebnis:")
    print(f"{'  so gebucht':32} {gebucht:>10.2f}$")
    print(f"{'  doppelt abgezogene Gebuehren':32} {zuviel:>10.2f}$")
    print(f"{'  so waere es richtig':32} {gebucht + zuviel:>10.2f}$"
          f"   <- Untergrenze")
    print()

    plus_alt = sum(1 for z in zeilen if z["gebucht"] > 0)
    plus_neu = sum(1 for z in zeilen if z["gebucht"] + z["zuviel"] > 0)
    print(f"{'Handel im Plus (gebucht)':32} {plus_alt:>10}")
    print(f"{'Handel im Plus (richtig)':32} {plus_neu:>10}")
    print(f"{'dreht das Vorzeichen bei':32} {plus_neu - plus_alt:>10} Handeln")
    print()

    fenster = [z for z in zeilen if z["zeit"] >= E6_START]
    if fenster:
        fg = sum(z["gebucht"] for z in fenster)
        fz = sum(z["zuviel"] for z in fenster)
        print(f"Messfenster ab {E6_START} ({len(fenster)} Verkaeufe):")
        print(f"{'  gebucht':32} {fg:>10.2f}$")
        print(f"{'  richtig':32} {fg + fz:>10.2f}$")
        for z in fenster:
            print(f"  {z['zeit'][:16]} {z['muenze']:10} "
                  f"gebucht {z['gebucht']:>7.3f}$  ->  "
                  f"richtig {z['gebucht'] + z['zuviel']:>7.3f}$   "
                  f"{z['grund'][:30]}")
        print()

    be = [z for z in zeilen if "BREAKEVEN" in z["grund"].upper()]
    if be:
        print(f"Breakeven-Sperre ({len(be)} Ausloesungen):")
        print(f"{'  Schnitt gebucht':32} "
              f"{sum(z['gebucht'] for z in be)/len(be):>10.3f}$")
        print(f"{'  Schnitt richtig':32} "
              f"{sum(z['gebucht']+z['zuviel'] for z in be)/len(be):>10.3f}$")
        print(f"{'  Summe gebucht':32} "
              f"{sum(z['gebucht'] for z in be):>10.2f}$")
        print(f"{'  Summe richtig':32} "
              f"{sum(z['gebucht']+z['zuviel'] for z in be):>10.2f}$")
        print()

    print("Lesehilfe: 'richtig' ist eine Untergrenze - bei Positionen mit")
    print("Nachkauf wurde je Tranche eine Gebuehr zu viel gezogen, hier")
    print("zaehlt nur die letzte. Der Fehler liegt in der Buchhaltung,")
    print("nicht im Handel: es ist nie Geld verloren gegangen, es stand")
    print("nur falsch in den Buechern.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
