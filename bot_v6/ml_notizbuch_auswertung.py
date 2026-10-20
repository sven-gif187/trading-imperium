"""
Auswertung des ML-Notizbuch-Modus (GEFUNDENE-PROBLEME #4, 11.08.2026).

Beantwortet die EINE Frage, die ueber das Scharfschalten entscheidet:
Hat die XGBoost-Vorhersage Vorhersagekraft - oder ist sie Rauschen?

Wie gemessen wird
-----------------
app.py/_ml_notizbuch() schreibt je Coin und Stunde eine Zeile in die Tabelle
schatten_regeln (regel='ml_model') mit Zeit, Coin, Score und Preis. Das Modell
sagt voraus: "steigt der Preis in 5 Kerzen um mehr als 1,0 %?" - im
1h-Zeitrahmen also 5 Stunden voraus. (Die Schwelle lag bis zum 12.08. bei
0,5 % und damit UNTER den Handelskosten - siehe SCHWELLE_STIEG unten.)

Diese Auswertung paart jede Notiz mit der Notiz desselben Coins rund 5 Stunden
spaeter und vergleicht Vorhersage mit dem, was wirklich passiert ist. Es werden
KEINE Zusatzdaten gebraucht: die spaeteren Notizen liefern den Preis selbst.

Der ehrliche Massstab
---------------------
Trefferquote allein taeuscht, wenn die Klassen ungleich verteilt sind. Steigt
der Preis nur in 23 % der Faelle, ist "immer nein sagen" schon zu 77 % richtig.
Deshalb wird immer beides ausgewiesen - und zusaetzlich die mittlere Rendite in
der oberen gegen die untere Score-Haelfte. Letztere ist der eigentliche Test:
verdient man Geld, wenn man dem Modell folgt?

Aufruf:  python ml_notizbuch_auswertung.py
"""
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta

from core.telemetrie import DB_DATEI

# Das Modell sagt 5 Kerzen voraus; Zeitrahmen laut config: 1h.
HORIZONT_STUNDEN = 5
# Wieviel darf die Paarung vom Ziel abweichen (Notizen kommen stuendlich,
# koennen aber ausfallen, wenn der Bot stand).
TOLERANZ_STUNDEN = 1.5
# Dieselbe Schwelle, mit der das Modell trainiert wurde.
#
# [KORRIGIERT 12.08.2026] Stand auf 0,005. Das war die alte, wirtschaftlich
# sinnlose Schwelle: 0,5 % Ziel bei 0,60 % Kosten je Runde - ein perfekter
# Treffer haette Geld verloren. Beides muss denselben Wert benutzen, sonst
# misst diese Auswertung etwas anderes, als das Modell gelernt hat.
# Massgeblich ist jetzt XGBoostSignalModel.LABEL_SCHWELLE; hier steht der
# Wert nur nochmal, damit das Werkzeug ohne den Bot laeuft.
SCHWELLE_STIEG = 0.010
# Ab welchem Score gilt die Vorhersage als "Kauf".
SCHWELLE_SCORE = 0.5
# Die Latte, ab der ein Rendite-Unterschied ueberhaupt zaehlt.
#
# WARUM DIESE ZEILE EXISTIERT: Ohne sie meldete diese Auswertung auch bei
# reinem Zufall "es gibt ein Signal" - geprueft mit erfundenen Zufallsdaten,
# Unterschied +0,006 %. Jedes Rauschen ergibt zufaellig irgendeinen
# Unterschied ungleich null. Ein Vorsprung zaehlt erst, wenn er die
# Handelskosten uebersteigt - alles darunter fressen die Gebuehren auf.
#
# WOHER DIE ZAHL KOMMT [KORRIGIERT 11.08.2026]: Zuerst standen hier 0,2 %
# aus dem Binance-Modell (2x0,10 % Taker). Das war FALSCH, gleich doppelt:
#   1. Gehandelt wird kuenftig auf Bybit EU (MiCA-lizenziert) - die
#      Entscheidung ist alt und steht in docs/forschungsprogramm_2026-07/.
#   2. Bybit EU nimmt Maker 0,10 % / Taker 0,25 % je Seite - vom Eigentuemer
#      selbst auf der offiziellen Gebuehrenseite geprueft (Stand 08.03.2026,
#      02_EXPERIMENT-REGISTER_v1.1.md). Taker ist also 2,5-mal teurer als
#      angenommen.
# [NACHGEZOGEN 12.08.2026, GEFUNDENE-PROBLEME #23] Hier standen 0,60 % -
# das Szenario K-BASIS mit einer pauschalen Slippage-Annahme von 0,05 % je
# Seite. Am echten Bybit-EU-Orderbuch gemessen (145-148 Messpunkte je Muenze,
# 12_SPREAD-MESSUNG.md) ist das fuer die drei GEHANDELTEN Muenzen viel zu
# pessimistisch: der halbe Median-Spread betraegt 0,0003 % (ETH), 0,0006 %
# (BTC) und 0,0068 % (SOL). Die Runde kostet damit:
#
#     ETH 0,5005 %   BTC 0,5012 %   SOL 0,5137 %
#
# Massgeblich ist der teuerste der drei, aufgerundet: 0,52 %. Eine zu hohe
# Latte ist nicht "sicherheitshalber gut" - sie verwirft Signale, die sich
# in Wirklichkeit tragen wuerden.
#
# ACHTUNG bei Aenderung des Universums: Fuer DOT waeren es 0,6523 % je Seite,
# die Runde also 1,80 %. Kommen andere Muenzen dazu, muss diese Zahl neu
# bestimmt werden - execution/engine.py:SPREAD_BP hat die Tabelle.
#
# Sobald der Bot Limit-Orders kann, gilt K-MAKER (0,26 %) - dann darf diese
# Zahl sinken, vorher NICHT.
#
# WARNUNG aus derselben Quelle: ccxt.bybit().fees['trading'] liefert
# maker 0,01 % / taker 0,075 % - fuer EU-Spot schlicht falsch. Gebuehren
# duerfen NIE aus ccxt-Metadaten stammen.
SCHWELLE_NUTZEN = 0.0052


def lade_notizen(db):
    if not os.path.exists(db):
        print(f"Keine Telemetrie-Datenbank gefunden: {db}")
        return []
    con = sqlite3.connect(db)
    try:
        zeilen = con.execute(
            "SELECT ts_utc, symbol, haette, preis, zusatz FROM schatten_regeln "
            "WHERE regel='ml_model' AND preis IS NOT NULL ORDER BY ts_utc"
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()

    notizen = []
    for ts, symbol, haette, preis, zusatz in zeilen:
        treffer = re.search(r"Score\s+([0-9.]+)", haette or "")
        if not treffer or not preis:
            continue
        try:
            notizen.append({
                "zeit": datetime.fromisoformat(ts),
                "symbol": symbol,
                "score": float(treffer.group(1)),
                "preis": float(preis),
                "version": (zusatz or "").replace("version=", ""),
            })
        except (ValueError, TypeError):
            continue
    return notizen


def paare_bilden(notizen):
    """Jede Notiz mit der rund HORIZONT_STUNDEN spaeteren desselben Coins."""
    nach_coin = {}
    for n in notizen:
        nach_coin.setdefault(n["symbol"], []).append(n)

    paare = []
    ziel = timedelta(hours=HORIZONT_STUNDEN)
    toleranz = timedelta(hours=TOLERANZ_STUNDEN)

    for coin, liste in nach_coin.items():
        liste.sort(key=lambda x: x["zeit"])
        for i, jetzt in enumerate(liste):
            bester, bester_abstand = None, None
            for spaeter in liste[i + 1:]:
                abstand = abs((spaeter["zeit"] - jetzt["zeit"]) - ziel)
                if spaeter["zeit"] - jetzt["zeit"] > ziel + toleranz:
                    break
                if abstand <= toleranz and (bester_abstand is None
                                            or abstand < bester_abstand):
                    bester, bester_abstand = spaeter, abstand
            if bester and jetzt["preis"] > 0:
                paare.append({
                    "coin": coin,
                    "score": jetzt["score"],
                    "rendite": bester["preis"] / jetzt["preis"] - 1,
                    "version": jetzt["version"],
                })
    return paare


def mittel(werte):
    return sum(werte) / len(werte) if werte else 0.0


def auswerten(paare):
    n = len(paare)
    gestiegen = [p for p in paare if p["rendite"] > SCHWELLE_STIEG]
    basisrate = len(gestiegen) / n

    richtig = sum(
        1 for p in paare
        if (p["score"] > SCHWELLE_SCORE) == (p["rendite"] > SCHWELLE_STIEG))
    treffer = richtig / n
    # "Immer nein" - die Messlatte, die das Modell schlagen MUSS.
    trivial = max(basisrate, 1 - basisrate)

    sortiert = sorted(paare, key=lambda p: p["score"])
    haelfte = n // 2
    unten = [p["rendite"] for p in sortiert[:haelfte]]
    oben = [p["rendite"] for p in sortiert[n - haelfte:]]

    print(f"Ausgewertete Paare : {n}")
    print(f"Modelle            : {', '.join(sorted({p['version'] for p in paare}))}")
    print(f"Coins              : {', '.join(sorted({p['coin'] for p in paare}))}")
    print()
    print(f"Preis stieg > {SCHWELLE_STIEG:.1%} in {basisrate:6.1%} der Faelle")
    print(f"Trefferquote Modell        : {treffer:6.1%}")
    print(f"Trefferquote 'immer nein'  : {trivial:6.1%}  <- diese Latte zaehlt")
    print()
    nutzen = mittel(oben) - mittel(unten)
    print(f"Mittlere Rendite obere Score-Haelfte : {mittel(oben):+7.3%}")
    print(f"Mittlere Rendite untere Score-Haelfte: {mittel(unten):+7.3%}")
    print(f"Unterschied (der eigentliche Nutzen) : {nutzen:+7.3%}")
    print(f"Latte: Handelskosten Kauf+Verkauf    : {SCHWELLE_NUTZEN:7.3%}")
    print()

    if n < 100:
        print(f"URTEIL: Noch zu duenn ({n} Paare). Mindestens 100, besser 300 "
              f"abwarten, bevor irgendetwas entschieden wird.")
    elif nutzen <= SCHWELLE_NUTZEN:
        print("URTEIL: KEINE brauchbare Vorhersagekraft.")
        if nutzen > 0:
            print(f"        Der Vorsprung von {nutzen:+.3%} liegt unter den "
                  f"{SCHWELLE_NUTZEN:.1%} Handelskosten - er waere aufgefressen, "
                  f"bevor er ankommt.")
        else:
            print("        Die obere Score-Haelfte lief nicht besser als die "
                  "untere - das Modell trennt gute nicht von schlechten "
                  "Zeitpunkten.")
        print("        -> nicht scharf schalten. Erst Trainingsdaten "
              "reparieren (models/auto_retrain.py), dann neu messen.")
    elif treffer <= trivial:
        print(f"URTEIL: Gemischt. Die Rendite-Trennung ({nutzen:+.3%}) traegt "
              f"ueber die Kosten, aber die Trefferquote schlaegt 'immer nein' "
              f"nicht. Weiter sammeln, bevor entschieden wird.")
    else:
        print(f"URTEIL: Echtes Signal. Vorsprung {nutzen:+.3%} liegt ueber den "
              f"{SCHWELLE_NUTZEN:.1%} Handelskosten UND die Trefferquote "
              f"schlaegt die Trivial-Latte.")
        print("        -> Scharfschalten kann besprochen werden. Vorher pruefen, "
              "ob das Ergebnis ueber mehrere Wochen und Coins stabil ist.")


def main():
    print("=" * 64)
    print("ML-NOTIZBUCH - Auswertung")
    print("=" * 64)
    print(f"Datenbank: {DB_DATEI}")
    print(f"Horizont : {HORIZONT_STUNDEN} Stunden (5 Kerzen im 1h-Zeitrahmen)")
    print("-" * 64)

    notizen = lade_notizen(DB_DATEI)
    if not notizen:
        print("Noch keine ML-Notizen vorhanden.")
        print()
        print("Das ist normal, solange der Bot seit dem Einbau nicht neu "
              "gestartet wurde - der Notizbuch-Modus laeuft erst ab dem "
              "naechsten Start mit. Danach entsteht je Coin eine Notiz pro "
              "Stunde, also rund 120 am Tag bei 5 Coins.")
        return 0

    print(f"Notizen gesamt: {len(notizen)}")
    print(f"Zeitraum      : {notizen[0]['zeit']:%d.%m.%Y %H:%M} bis "
          f"{notizen[-1]['zeit']:%d.%m.%Y %H:%M} (UTC)")
    print("-" * 64)

    paare = paare_bilden(notizen)
    if not paare:
        print(f"Noch kein Paar mit {HORIZONT_STUNDEN} Stunden Abstand "
              f"gefunden - die aeltesten Notizen sind noch zu frisch.")
        return 0

    auswerten(paare)
    return 0


if __name__ == "__main__":
    sys.exit(main())
