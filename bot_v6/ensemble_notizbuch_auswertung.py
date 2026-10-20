"""
Auswertung des Ensemble-Notizbuchs (GEFUNDENE-PROBLEME #17, 11.08.2026).

Beantwortet die Frage, die ueber das Reparieren entscheidet:
Wuerde ein ECHTER technical-Wert die Kaufentscheidungen ueberhaupt aendern -
und wenn ja, wie oft und in welche Richtung?

Hintergrund
-----------
raw_scores["technical"] steht fest auf 0,5, obwohl der Kommentar daneben
"Wird pro Coin ueberschrieben" behauptet. Da technical mit 30 von 73
vergebenen Gewichtsprozenten das groesste Einzelgewicht hat, sind rund 41 %
des Ensemble-Werts eine Konstante.

Der Ensemble-Wert geht ab 0,65 als Bonus in den Kauf-Score ein
(agents/signal_agent.py:135): ueber 0,65 gibt es +1 Punkt, ueber 0,75 sogar
+2 - bei einer Kaufschwelle von 3 Punkten ist das viel.

Warum nicht einfach reparieren
------------------------------
Weil "repariert" nicht automatisch "besser" heisst. Ein echter technical-Wert
weckt diesen Bonus zum Leben, Kaeufe wuerden also LEICHTER ausgeloest. Dazu
kommt: signal_agent bewertet RSI, MACD und Bollinger bereits direkt mit
eigenen Punkten - dieselben Indikatoren zaehlten dann doppelt.

Deshalb laeuft die Sache erst im Notizbuch-Modus, und diese Auswertung sagt,
wie gross der Unterschied ueberhaupt waere.

Aufruf:  python ensemble_notizbuch_auswertung.py
"""
import os
import re
import sqlite3
import sys
from datetime import datetime

from core.telemetrie import DB_DATEI

MUSTER = re.compile(
    r"technical ([0-9.]+) -> Ensemble ([0-9.]+) \(Bonus (\d)\), "
    r"heute ([0-9.]+) \(Bonus (\d)\)")


def lade(db):
    if not os.path.exists(db):
        print(f"Keine Telemetrie-Datenbank gefunden: {db}")
        return []
    con = sqlite3.connect(db)
    try:
        zeilen = con.execute(
            "SELECT ts_utc, symbol, haette, zusatz FROM schatten_regeln "
            "WHERE regel='ensemble_technical' ORDER BY ts_utc").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()

    notizen = []
    for ts, symbol, haette, zusatz in zeilen:
        t = MUSTER.search(haette or "")
        if not t:
            continue
        notizen.append({
            "zeit": datetime.fromisoformat(ts),
            "symbol": symbol,
            "technical": float(t.group(1)),
            "ensemble_echt": float(t.group(2)),
            "bonus_echt": int(t.group(3)),
            "ensemble_heute": float(t.group(4)),
            "bonus_heute": int(t.group(5)),
            "teile": zusatz or "",
        })
    return notizen


def mittel(werte):
    return sum(werte) / len(werte) if werte else 0.0


def main():
    print("=" * 66)
    print("ENSEMBLE-NOTIZBUCH - Auswertung (Punkt 17: technical haengt auf 0,5)")
    print("=" * 66)
    print(f"Datenbank: {DB_DATEI}")
    print("-" * 66)

    n = lade(DB_DATEI)
    if not n:
        print("Noch keine Ensemble-Notizen vorhanden.")
        print()
        print("Das ist normal, solange der Bot seit dem Einbau nicht neu "
              "gestartet wurde. Danach entsteht je Coin eine Notiz pro Stunde.")
        return 0

    print(f"Notizen  : {len(n)}")
    print(f"Zeitraum : {n[0]['zeit']:%d.%m. %H:%M} bis "
          f"{n[-1]['zeit']:%d.%m. %H:%M} (UTC)")
    print(f"Coins    : {', '.join(sorted({x['symbol'] for x in n}))}")
    print("-" * 66)

    tech = [x["technical"] for x in n]
    print("Der technische Wert, den es heute nicht gibt:")
    print(f"  Spanne     : {min(tech):.3f} bis {max(tech):.3f}")
    print(f"  Mittelwert : {mittel(tech):.3f}   (heute fest: 0.500)")
    print()

    print("Ensemble-Wert:")
    print(f"  heute (technical fest) : Mittel {mittel([x['ensemble_heute'] for x in n]):.3f}")
    print(f"  mit echtem technical   : Mittel {mittel([x['ensemble_echt'] for x in n]):.3f}")
    print()

    anders = [x for x in n if x["bonus_echt"] != x["bonus_heute"]]
    hoeher = [x for x in anders if x["bonus_echt"] > x["bonus_heute"]]
    tiefer = [x for x in anders if x["bonus_echt"] < x["bonus_heute"]]

    print(f"Bonus im Kauf-Score waere ANDERS ausgefallen: "
          f"{len(anders)} von {len(n)} ({len(anders)/len(n):.1%})")
    print(f"  davon Kauf LEICHTER (mehr Punkte) : {len(hoeher)}")
    print(f"  davon Kauf SCHWERER (weniger)     : {len(tiefer)}")
    print()

    heute_nie = all(x["bonus_heute"] == 0 for x in n)
    if heute_nie:
        print("Beobachtung: Der Bonus hat heute in KEINEM einzigen Fall "
              "ausgeloest.")
        print("             Das Ensemble ist als Eingang in die "
              "Kaufentscheidung praktisch tot.")
        print()

    if len(n) < 100:
        print(f"URTEIL: Noch zu duenn ({len(n)} Notizen). Mindestens 100 "
              f"abwarten.")
    elif not anders:
        print("URTEIL: Kein Unterschied. Das Reparieren wuerde an den "
              "Entscheidungen nichts aendern - dann ist es reine "
              "Code-Kosmetik und kann gefahrlos gemacht werden.")
    else:
        print(f"URTEIL: Das Reparieren wuerde {len(anders)/len(n):.1%} der "
              f"Entscheidungen veraendern, ueberwiegend Richtung "
              f"{'LEICHTER kaufen' if len(hoeher) >= len(tiefer) else 'SCHWERER kaufen'}.")
        print("        Das ist eine echte Verhaltensaenderung, keine Kosmetik.")
        print("        Vor dem Scharfschalten mit Sven besprechen - besonders")
        print("        die Doppelzaehlung: signal_agent bewertet RSI/MACD/")
        print("        Bollinger bereits direkt mit eigenen Punkten.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
