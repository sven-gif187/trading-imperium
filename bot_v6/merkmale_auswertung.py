"""Welche Indikatorwerte gingen steigenden Kursen voraus?

NUR LESEND. Aendert nichts, handelt nicht.

DIE FRAGE - und was sie NICHT ist
---------------------------------
In feature_snapshots liegen 38 Indikatorspalten. Gefragt war urspruenglich:
"Welche Werte fuehrten zu Gewinnen?" So gestellt ist sie NICHT
beantwortbar - es gibt 11 Verkaeufe mit Ergebnis, und KEINER von ihnen
traegt einen Verweis auf einen Schnappschuss. Der Verweis wird seit dem
Neustart am 17.08. mitgeschrieben; bis dahin haben zwei Kaeufe einen,
beide noch offen.

Beantwortbar ist die schwaechere, aber ehrliche Fassung:

    Welche Indikatorwerte gingen einem STEIGENDEN KURS voraus?

Das ist keine Aussage ueber Gewinn. Es fehlen Kosten (0,505 % je Runde),
Ausstiegsregel und Positionsgroesse. Es beantwortet "war der Zeitpunkt
guenstig", nicht "haette der Bot Geld verdient".

DIE KETTE
---------
    nachlauf.db (Kurs nach 1/4/24 h)
        -> evaluations (die Entscheidung, ueber evaluation_id)
        -> feature_snapshots (38 Indikatoren, ueber feature_snapshot_id)

Datengrundlage sind die Ablehnungen: Jedes Mal, wenn der Bot NICHT
gekauft hat, wurden Indikatoren und Folgekurs mitgeschrieben.

WARUM NUR DER 1-STUNDEN-HORIZONT ZAEHLT
---------------------------------------
Die Schnappschuesse entstehen STUENDLICH je Muenze. Der Bot prueft alle
12 Sekunden und verweist dabei immer auf denselben Schnappschuss -
955 Zeilen sind deshalb nur 316 Beobachtungen.

Und beim Horizont gilt dieselbe Rechnung wie im Handbuch 4.44: In T
Tagen passen bei Horizont H nur T*24/H nicht ueberlappende Fenster.

    Horizont 1 h : 316 verschiedene Schnappschuesse, stuendlich
                   -> nicht ueberlappend, alle 316 zaehlen
    Horizont 4 h : 307 Schnappschuesse, aber nur ~79 unabhaengig
    Horizont 24 h: 280 Schnappschuesse, aber nur ~13 unabhaengig

Deshalb ist 1 h die Hauptauswertung, 4 h ein Hinweis und 24 h NICHT
ENTSCHEIDBAR. Es waere ein Leichtes, aus 721 Zeilen eine schoene
24-Stunden-Aussage zu bauen - sie waere dieselbe Beobachtung 55-mal
gezaehlt.

DIE TRIVIAL-LATTE
-----------------
Jede Gruppe wird gegen die Latte gemessen: die mittlere Kursbewegung
ALLER Faelle im selben Zeitraum. Eine Gruppe, die 0,05 % bringt, waehrend
der Markt ohnehin 0,05 % gestiegen ist, hat nichts erklaert. Ohne diese
Latte sieht in einem steigenden Markt jeder Indikator gut aus.

Aufruf:  python merkmale_auswertung.py
         python merkmale_auswertung.py --horizont 4h
"""
import os
import sqlite3
import statistics
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
TELEMETRIE = os.path.join(HIER, "data_store", "telemetrie.db")
NACHLAUF = os.path.join(HIER, "data_store", "nachlauf.db")

# Welche Indikatoren untersucht werden, mit den Grenzen der Gruppen.
# Die Grenzen sind die ueblichen Lehrbuchwerte, damit niemand den
# Verdacht haben muss, sie seien auf ein Ergebnis hin gewaehlt worden.
# ACHTUNG, SKALEN - beim ersten Lauf am 18.08.2026 falsch angenommen:
# stoch_rsi laeuft 0 bis 100 (nicht 0 bis 1), volatility bewegt sich
# zwischen 0,0004 und 0,0046 (meine Grenzen lagen komplett darueber).
# Folge: 281 von 316 Faellen landeten in EINER Gruppe, und die Tabelle
# sah trotzdem ordentlich aus. Erst der Blick auf die Spannweite jeder
# Spalte hat es gezeigt.
#
# Wo die Skala feststeht (RSI, ADX, Vorzeichen, Bollinger-Lage,
# Stochastik-RSI), gelten Lehrbuchgrenzen - damit niemand vermuten muss,
# sie seien auf ein Ergebnis hin gewaehlt. Wo es keine natuerliche Skala
# gibt, werden die VIERTEL DER DATEN genommen (grenzen=None); das ergibt
# gleich grosse Gruppen und kommt ohne Annahme aus.
MERKMALE = [
    ("rsi",            "RSI",                    [30, 45, 55, 70]),
    ("adx",            "ADX (Trendstaerke)",     [20, 25, 40]),
    ("macd_hist",      "MACD-Histogramm",        [0]),
    ("bb_lage",        "Lage im Bollinger-Band", [0.2, 0.5, 0.8]),
    ("stoch_rsi",      "Stochastik-RSI (0-100)", [20, 50, 80]),
    ("close_to_ema20", "Abstand zur EMA20",      None),
    ("volatility",     "Schwankung",             None),
    ("volume_ratio",   "Volumen zum Schnitt",    None),
]


def viertel(werte):
    """Grenzen bei 25/50/75 Prozent - fuer Spalten ohne feste Skala."""
    w = sorted(v for v in werte if v is not None)
    if len(w) < 8:
        return [0]
    return [round(w[len(w) // 4], 6), round(w[len(w) // 2], 6),
            round(w[len(w) * 3 // 4], 6)]


def gruppe(wert, grenzen):
    if wert is None:
        return None
    if len(grenzen) == 1:
        return f"< {grenzen[0]}" if wert < grenzen[0] else f">= {grenzen[0]}"
    if wert < grenzen[0]:
        return f"< {grenzen[0]}"
    for a, b in zip(grenzen, grenzen[1:]):
        if a <= wert < b:
            return f"{a} bis {b}"
    return f">= {grenzen[-1]}"


def lade(horizont):
    """Ein Datensatz je Schnappschuss - NICHT je Auswertungszeile."""
    con = sqlite3.connect(TELEMETRIE)
    con.execute(f"attach database '{NACHLAUF}' as n")
    spalten = ", ".join(f"f.{m}" for m, _, _ in MERKMALE)
    # Je Schnappschuss die FRUEHESTE Zeile - eine Beobachtung, nicht 30.
    q = f"""
        select f.feature_snapshot_id, f.symbol, min(nl.ts_utc) as zeit,
               nl.preis, nl.{horizont}, {spalten}
        from n.nachlauf nl
        join evaluations e on e.evaluation_id = nl.kennung
        join feature_snapshots f on f.feature_snapshot_id = e.feature_snapshot_id
        where nl.{horizont} is not null and nl.preis > 0
        group by f.feature_snapshot_id
    """
    zeilen = []
    for r in con.execute(q):
        preis, danach = r[3], r[4]
        if not preis or not danach:
            continue
        satz = {"id": r[0], "symbol": r[1], "zeit": r[2],
                "rendite": (danach / preis - 1) * 100}
        for i, (feld, _, _) in enumerate(MERKMALE):
            satz[feld] = r[5 + i]
        zeilen.append(satz)
    return zeilen


def unabhaengige_fenster(zeilen, stunden):
    """T*24/H je Muenze - die Rechnung aus Handbuch 4.44."""
    if not zeilen:
        return 0
    zeiten = sorted(z["zeit"] for z in zeilen)
    from datetime import datetime
    t0 = datetime.fromisoformat(zeiten[0])
    t1 = datetime.fromisoformat(zeiten[-1])
    tage = max((t1 - t0).total_seconds() / 86400, 0.01)
    muenzen = len({z["symbol"] for z in zeilen})
    # Nie mehr unabhaengige Fenster als es ueberhaupt Beobachtungen gibt -
    # sonst behauptet die Rechnung mehr, als gemessen wurde.
    return min(len(zeilen), int(tage * 24 / stunden) * muenzen)


def main():
    horizont = "p1h"
    stunden = 1
    if "--horizont" in sys.argv:
        wahl = sys.argv[sys.argv.index("--horizont") + 1]
        horizont = "p" + wahl
        stunden = int(wahl.rstrip("h"))

    zeilen = lade(horizont)
    if len(zeilen) < 20:
        print(f"Nur {len(zeilen)} Beobachtungen - zu wenig fuer eine Aussage.")
        return 1

    renditen = [z["rendite"] for z in zeilen]
    latte = statistics.median(renditen)
    unabh = unabhaengige_fenster(zeilen, stunden)

    print("=" * 70)
    print(f"WELCHE INDIKATORWERTE GINGEN STEIGENDEN KURSEN VORAUS? ({stunden} h)")
    print("=" * 70)
    print(f"Beobachtungen (verschiedene Schnappschuesse) : {len(zeilen)}")
    print(f"davon unabhaengig (T*24/H je Muenze)         : {unabh}")
    print(f"Zeitraum                                     : "
          f"{min(z['zeit'] for z in zeilen)[:16]} bis "
          f"{max(z['zeit'] for z in zeilen)[:16]}")
    print()
    print(f"TRIVIAL-LATTE: der Median ALLER Faelle liegt bei {latte:+.3f} %.")
    print("Eine Gruppe zaehlt nur, wenn sie diese Latte deutlich schlaegt.")
    if unabh < 30:
        print()
        print("!! ACHTUNG: unter 30 unabhaengige Faelle. Alles Folgende ist")
        print("!! ein HINWEIS, keine Aussage. Nicht als Beleg verwenden.")
    print()

    for feld, name, grenzen in MERKMALE:
        if grenzen is None:
            grenzen = viertel([z.get(feld) for z in zeilen])
        gruppen = {}
        for z in zeilen:
            g = gruppe(z.get(feld), grenzen)
            if g is not None:
                gruppen.setdefault(g, []).append(z["rendite"])
        if not gruppen:
            continue
        print(f"{name}")
        print(f"  {'Gruppe':16} {'Faelle':>7} {'Median':>9} {'im Plus':>9} "
              f"{'gegen Latte':>12}")
        for g, werte in sorted(gruppen.items(),
                               key=lambda x: statistics.median(x[1]),
                               reverse=True):
            med = statistics.median(werte)
            plus = sum(1 for w in werte if w > 0) / len(werte) * 100
            marke = ""
            if len(werte) >= 20 and abs(med - latte) >= 0.05:
                marke = "  <--" if med > latte else "  (schlechter)"
            print(f"  {g:16} {len(werte):>7} {med:>+8.3f}% {plus:>8.0f}% "
                  f"{med-latte:>+11.3f}%{marke}")
        print()

    print("-" * 70)
    print("Lesehilfe: 'gegen Latte' ist der Unterschied zur mittleren")
    print("Bewegung aller Faelle. Nur Gruppen mit mindestens 20 Faellen und")
    print("mindestens 0,05 Prozentpunkten Abstand sind markiert - und auch")
    print("die sind nur so viel wert wie die Zahl der unabhaengigen Faelle")
    print("ganz oben. Kosten von 0,505 % je Runde sind hier NICHT enthalten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
