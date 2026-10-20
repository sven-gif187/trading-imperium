# -*- coding: utf-8 -*-
"""vollstaendigkeit.py - haben wir am Stichtag wirklich ALLE Daten?

[CLEANUP-KEEP]

Angelegt 21.08.2026. Sven: "helfe mir doch bitte einfach das so
aufzustellen damit wir dann alles haben!"

WOZU:
  Sieben Monate lang endete jede Auswertung mit "es fehlt noch was".
  Immer erst am Stichtag, immer zu spaet. Dieses Werkzeug beantwortet
  die Frage HEUTE statt am 18.09.

  Es sagt vier Dinge:
    1. Welche Felder werden bei jedem Verkauf geschrieben - und welche nicht?
    2. Sind die Luecken aus anderen Quellen fuellbar, oder endgueltig weg?
    3. Laesst sich jeder Verkauf eindeutig einer Position zuordnen?
    4. Reicht das Tempo bis zum Stichtag?

FASST NICHTS AN. Liest nur. Kein Schreibzugriff, keine Bot-Beruehrung.
Freeze-sicher.

Aufruf:  python vollstaendigkeit.py
Oder:    VOLLSTAENDIGKEIT.bat  (doppelklicken)
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HIER, "data_store")

# Toleranz fuer die Zuordnung Verkauf <-> Position ueber den Zeitstempel.
# Gemessen am 21.08.: die Verzoegerung lag zwischen 49 und 325 Sekunden,
# weil positionsverlauf.py in Intervallen prueft. 600 s deckt das ab.
# Gegengeprueft: bei 27 geschlossenen Positionen gab es NULL Faelle, in
# denen zwei Positionen derselben Muenze binnen 600 s schlossen - die
# Zuordnung ist damit eindeutig, nicht geraten.
TOLERANZ_SEK = 600

# Die Felder, die fuer die FREIGABE gebraucht werden (go_live_check.py).
# Fehlt hier etwas, ist der Stichtag geplatzt.
KERN = ["pnl", "pnl_pct", "fee", "market_regime", "cycle_phase",
        "fear_greed_at_entry", "time", "coin", "price", "qty"]

# Die Felder fuer die ANALYSE-Fragen: welche Ausstiegsregel taugt,
# wie viel Risiko lag an, warum wurde gekauft. Fehlen sie, bleibt die
# Freigabe moeglich - aber die Frage nach der naechsten Verbesserung
# unbeantwortbar.
ANALYSE = ["position_id", "haltedauer_min", "entry_strategie", "entry_score",
           "stop_initial", "trailing_stop_pct", "decision_id", "mfe_pct",
           "mae_pct", "r_multiple", "slippage_pct", "spread_pct_entry"]

# Welche Luecke laesst sich woher nachtragen?
QUELLEN = {
    "position_id":       "positionsverlauf.db -> positionen.pos_id",
    "haltedauer_min":    "positionsverlauf.db -> geschlossen minus eroeffnet",
    "entry_strategie":   "positionsverlauf.db -> positionen.strategie",
    "entry_score":       "positionsverlauf.db -> positionen.score",
    # [29.08.2026 richtiggestellt] Hier stand "wird nirgends geschrieben".
    # Das ist falsch, nachgemessen an trades_v5.json: Auf der KAUF-Seite
    # stehen alle drei Felder in 64 von 68 Kaeufen seit dem 06.08. (94,1 %).
    # Geschrieben werden sie also sehr wohl - sie werden nur nicht auf den
    # Verkauf mitgenommen.
    #
    # Nachtragbar sind sie trotzdem nicht, aber aus einem ANDEREN Grund:
    # Es gibt keine belastbare Verbindung Verkauf -> Kauf. Positionen
    # werden per Nachkauf aufgebaut und teilweise verkauft, die Mengen
    # passen also nicht (geprueft: Verkauf SOL 1,357 gegen Kauf 0,714).
    # Und positionsverlauf.db fuehrt in `positionen` nur pos_id, muenze,
    # eroeffnet, einstieg, menge, strategie, score, geschlossen und
    # schluss_grund - keines der drei Felder.
    #
    # Der Unterschied ist nicht akademisch: "wird nirgends geschrieben"
    # heisst, man muesste das Schreiben erst bauen. "wird geschrieben,
    # aber nicht weitergereicht" heisst, es fehlt nur die Uebergabe -
    # deutlich weniger Arbeit, und die Daten der Vergangenheit sind fuer
    # die betroffenen Kaeufe bereits vorhanden.
    "stop_initial":      "steht am KAUF (94,1 % seit 06.08.), wird nicht "
                         "zum Verkauf mitgenommen - keine belastbare Zuordnung",
    "trailing_stop_pct": "steht am KAUF (94,1 % seit 06.08.), wird nicht "
                         "zum Verkauf mitgenommen - keine belastbare Zuordnung",
    "decision_id":       "steht am KAUF (94,1 % seit 06.08.) und beim Weg "
                         "execute_approved_trade - sonst nicht weitergereicht",
}

# Welche davon lassen sich WIRKLICH nachtragen?
#
# [29.08.2026] Vorher wurde das an der Zeichenkette "NICHT" im Quellentext
# abgelesen. Sobald jemand die Formulierung aendert - und genau das war
# noetig, weil sie falsch war - zaehlt das Programm falsch, ohne zu
# murren. Es meldete "Nachtragbar: 7, Endgueltig fehlend: 0", obwohl sich
# drei davon nicht nachtragen lassen. Jetzt steht es ausdruecklich da.
NACHTRAGBAR = {"position_id", "haltedauer_min", "entry_strategie", "entry_score"}


def _dt(s):
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _epoche_start():
    """Beginn der laufenden Epoche aus config_epochs.json."""
    try:
        with open(os.path.join(HIER, "config_epochs.json"), encoding="utf-8") as f:
            ep = json.load(f)
        liste = ep if isinstance(ep, list) else ep.get("epochs", [])
        gueltig = [e for e in liste if e.get("ab") or e.get("start")]
        if not gueltig:
            return None, None
        letzte = sorted(gueltig, key=lambda e: e.get("ab") or e.get("start"))[-1]
        return (letzte.get("ab") or letzte.get("start")), letzte.get("name", "?")
    except Exception:
        return None, None


def _stichtag():
    try:
        with open(os.path.join(HIER, "config_zielgroessen.json"),
                  encoding="utf-8") as f:
            return json.load(f).get("messfenster_ende")
    except Exception:
        return None


def lade_verkaeufe(ab):
    """Alle Verkaeufe der laufenden Epoche.

    Das massgebliche Feld ist 'type'. 'side' existiert nur in
    Altbestaenden und deckt nur einen Bruchteil ab - am 21.08. fuehrte
    das beinahe zu einer Falschmeldung ("0 Verkaeufe in E7").
    """
    p = os.path.join(STORE, "trades_v5.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    sells = [t for t in d if str(t.get("type", "")).upper() == "SELL"]
    return [t for t in sells if not ab or str(t.get("time", "")) >= ab]


def lade_positionen():
    p = os.path.join(STORE, "positionsverlauf.db")
    if not os.path.isfile(p):
        return []
    c = sqlite3.connect(p)
    try:
        rows = c.execute(
            "SELECT pos_id,muenze,eroeffnet,einstieg,menge,strategie,score,"
            "geschlossen FROM positionen WHERE geschlossen IS NOT NULL").fetchall()
    except Exception:
        return []
    finally:
        c.close()
    return [dict(zip(["pos_id", "muenze", "eroeffnet", "einstieg", "menge",
                      "strategie", "score", "geschlossen"], r)) for r in rows]


def zuordnen(verkauf, positionen):
    """Die Position zu einem Verkauf finden - oder None.

    Gibt zusaetzlich zurueck, ob die Zuordnung EINDEUTIG war: gaebe es
    zwei Kandidaten im Fenster, waere das Ergebnis geraten. Dann lieber
    nichts melden als etwas Falsches.
    """
    tv = _dt(verkauf.get("time"))
    if not tv:
        return None, False
    treffer = []
    for p in positionen:
        if p["muenze"] != verkauf.get("coin"):
            continue
        tp = _dt(p["geschlossen"])
        if not tp:
            continue
        if abs((tv - tp).total_seconds()) <= TOLERANZ_SEK:
            treffer.append(p)
    if not treffer:
        return None, False
    return treffer[0], len(treffer) == 1


def main():
    ab, epname = _epoche_start()
    stichtag = _stichtag()
    verk = lade_verkaeufe(ab)
    pos = lade_positionen()

    print("=" * 74)
    print("  VOLLSTAENDIGKEIT - haben wir am Stichtag wirklich alle Daten?")
    print("  Epoche %s ab %s" % (epname, str(ab)[:16]))
    print("  Stichtag %s" % stichtag)
    print("=" * 74)

    if not verk:
        print()
        print("  Noch keine Verkaeufe in dieser Epoche.")
        return 0

    print()
    print("  Verkaeufe in dieser Epoche: %d" % len(verk))
    print("  Geschlossene Positionen in positionsverlauf.db: %d" % len(pos))

    # ---------------------------------------------------- 1. Freigabe-Felder
    print()
    print("-" * 74)
    print("  1) FELDER FUER DIE FREIGABE  -  hier darf nichts fehlen")
    print("-" * 74)
    kern_ok = True
    for f in KERN:
        n = sum(1 for t in verk if t.get(f) is not None)
        pct = 100.0 * n / len(verk)
        if pct < 100:
            kern_ok = False
        print("    %-22s %3d/%-3d  %5.1f%%   %s"
              % (f, n, len(verk), pct, "OK" if pct == 100 else "!! LUECKE"))
    print()
    print("    %s" % ("Alle Freigabe-Felder vollstaendig."
                      if kern_ok else
                      "!! ACHTUNG: Ein Freigabe-Feld hat Luecken."))

    # ---------------------------------------------------- 2. Analyse-Felder
    print()
    print("-" * 74)
    print("  2) FELDER FUER DIE ANALYSE  -  Luecken hier blockieren die")
    print("     Freigabe nicht, aber die naechste Verbesserung bleibt")
    print("     unbeantwortbar")
    print("-" * 74)
    luecken = []
    for f in ANALYSE:
        n = sum(1 for t in verk if t.get(f) is not None)
        pct = 100.0 * n / len(verk)
        if pct < 100:
            luecken.append((f, n, pct))
        print("    %-22s %3d/%-3d  %5.1f%%   %s"
              % (f, n, len(verk), pct, "OK" if pct == 100 else "!!"))

    # ---------------------------------------------------- 3. Fuellbarkeit
    print()
    print("-" * 74)
    print("  3) SIND DIE LUECKEN FUELLBAR?")
    print("-" * 74)
    if not luecken:
        print("    Keine Luecken.")
    else:
        fuellbar = nicht = 0
        for f, n, pct in luecken:
            q = QUELLEN.get(f, "keine bekannte Quelle")
            geht = f in NACHTRAGBAR
            if geht:
                fuellbar += 1
            else:
                nicht += 1
            print("    %-22s %5.1f%%  ->  %s" % (f, pct, q))
        print()
        print("    Nachtragbar: %d   Endgueltig fehlend: %d" % (fuellbar, nicht))

    # ------------------------------------ 4. Zuordnung Verkauf <-> Position
    print()
    print("-" * 74)
    print("  4) ZUORDNUNG VERKAUF -> POSITION  (Toleranz %d s)" % TOLERANZ_SEK)
    print("-" * 74)
    ohne = [t for t in verk if t.get("position_id") is None]
    if not ohne:
        print("    Alle Verkaeufe tragen bereits eine Positions-Kennung.")
    else:
        eind = mehr = keine = 0
        for t in ohne:
            p, ok = zuordnen(t, pos)
            if p is None:
                keine += 1
            elif ok:
                eind += 1
            else:
                mehr += 1
        print("    Verkaeufe ohne Kennung      : %d" % len(ohne))
        print("    davon eindeutig zuordenbar  : %d" % eind)
        print("    mehrdeutig (nicht nutzbar)  : %d" % mehr)
        print("    gar nicht zuordenbar        : %d" % keine)
        if mehr:
            print()
            print("    !! Mehrdeutige Faelle werden NICHT nachgetragen.")
            print("       Eine geratene Zuordnung ist schlimmer als keine.")

    # ---------------------------------------------------- 5. Reicht das Tempo?
    print()
    print("-" * 74)
    print("  5) REICHT DAS TEMPO BIS ZUM STICHTAG?")
    print("-" * 74)
    t0 = _dt(ab)
    tend = _dt(str(stichtag) + "T00:00:00+00:00") if stichtag else None
    jetzt = datetime.now(timezone.utc)
    if t0 and tend:
        gelaufen = (jetzt - t0).total_seconds() / 86400.0
        rest = (tend - jetzt).total_seconds() / 86400.0
        rate = len(verk) / gelaufen if gelaufen > 0 else 0
        erwartet = len(verk) + rate * rest
        print("    Epoche laeuft seit      : %.2f Tagen" % gelaufen)
        print("    Rate                    : %.2f Verkaeufe/Tag" % rate)
        print("    Rest bis zum Stichtag   : %.2f Tage" % rest)
        print("    Erwartung am Stichtag   : %.0f Verkaeufe" % erwartet)
        print()
        for ziel, was in ((30, "Messfenster (Handbuch 4.44)"),
                          (100, "Kriterium A der Freigabe")):
            if len(verk) >= ziel:
                print("    n=%-4d %-28s ERREICHT" % (ziel, was))
            elif erwartet >= ziel:
                tage = (ziel - len(verk)) / rate if rate > 0 else 999
                print("    n=%-4d %-28s in %.1f Tagen erreichbar"
                      % (ziel, was, tage))
            else:
                print("    n=%-4d %-28s WIRD NICHT ERREICHT (erwartet %.0f)"
                      % (ziel, was, erwartet))
    else:
        print("    Nicht berechenbar - Epochenstart oder Stichtag fehlt.")

    print()
    print("=" * 74)
    if kern_ok:
        print("  ERGEBNIS: Die Freigabe-Daten sind vollstaendig.")
        if luecken:
            print("            %d Analyse-Feld(er) mit Luecken - siehe 2 und 3."
                  % len(luecken))
    else:
        print("  ERGEBNIS: !! Ein Freigabe-Feld hat Luecken. Sofort klaeren.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
