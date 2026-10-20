# -*- coding: utf-8 -*-
"""Fraktale + Multi-Timeframe-Fibonacci-Konfluenz. Stufe 1 des neuen Handelswegs.

WOZU
----
Sven hat am 14.09.2026 einen Handelsweg vorgelegt: Fraktale (Williams
Fractals) als Swing-Erkennung, daraus Fibonacci-Retracements auf MEHREREN
Zeitrahmen, und ein Einstieg dort, wo sich Stufen verschiedener Zeitrahmen
treffen - eine Konfluenzzone.

WAS HIER NEU IST - UND WAS SCHON DA WAR
---------------------------------------
Die Haelfte stand schon im Projekt, und zwar der schwierige Teil:

    Fraktale mit Kausalitaetsschutz   features/chartanalyse.py:127
                                      (swing_punkte, Feld `bestaetigt_ab`)
    Fibonacci mit neun Stufen         features/chartanalyse.py:232
    Zonenbildung aus Punkten          features/chartanalyse.py:154

Diese Datei baut das NICHT nach. Sie benutzt es und ergaenzt genau drei
Dinge, die gefehlt haben:

    1. Das Golden Pocket - das Band zwischen 0,618 und 0,65
    2. Konfluenz ueber MEHRERE Zeitrahmen statt nur einem
    3. Eine Bewertung (Score), die nicht dieselbe Information doppelt zaehlt

WARUM MARKS STUFENSATZ UNANGETASTET BLEIBT
------------------------------------------
`FIB_RUECK` in chartanalyse.py ist **Marks** Satz: die fuenf klassischen
Stufen plus 0,707 und 0,866 (Wurzelverhaeltnisse). Er ist an seinen eigenen
Charts belegt (`mark_gegenprobe.py`, 16 Stufen aus zwei Maerkten) und
Grundlage von Befund 102.

**Die 0,65 aus dem neuen Handelsweg steht NICHT in diesem Satz.** Wuerde man
sie dort hineinschreiben, misse `mark_messung.py` beim naechsten Lauf etwas
anderes als beim letzten - und der Vergleich waere still kaputt. Deshalb:

    FIB_RUECK        Marks Satz, unveraendert      -> Befund 102
    STUFEN_HANDEL    Marks Satz PLUS 0,65          -> dieser Handelsweg

Zwei Saetze nebeneinander, jeder mit seinem Zweck. Das ist keine Doppelung,
sondern die Trennung zweier Fragen.

DIE REGEL GEGEN DOPPELZAEHLUNG
------------------------------
Svens Prompt verlangt ausdruecklich: *"Pruefe explizit, dass nicht mehrfach
dieselbe Information kuenstlich als mehrere unabhaengige Bestaetigungen
gezaehlt wird."*

Das ist der wichtigste Punkt der ganzen Datei. Drei Stufen aus DERSELBEN
Welle, die zufaellig nah beieinanderliegen, sind **eine** Beobachtung, nicht
drei. Deshalb zaehlt der Score hier nach **Herkunft**: je Zeitrahmen und je
Swing zaehlt nur die staerkste Stufe. Ohne diese Regel bekaeme jede beliebige
Stelle im Chart einen hohen Score, sobald man nur genug Stufen einzeichnet.

KEIN HANDEL
-----------
Diese Datei rechnet. Sie kennt weder Orders noch Positionen und wird von
keinem Handelspfad importiert - genau wie `features/chartanalyse.py`, das
nur von Anzeige, Backtest und Export benutzt wird. Was daraus einmal ein
Handel wird, entscheidet Stufe 2 (Schattenbetrieb) und danach eine eigene
Epochengrenze.
"""
from collections import defaultdict

from features.chartanalyse import FIB_RUECK, swing_punkte

# ====================================================================
# Stufen
# ====================================================================
# Marks Satz plus die 0,65 - zusammen bilden 0,618 und 0,65 das Golden
# Pocket. Sortiert, damit die Reihenfolge nicht von der Schreibweise
# abhaengt.
STUFEN_HANDEL = sorted(set(FIB_RUECK) | {0.65})

# Das Golden Pocket ist ein BAND, keine Linie: das Preisband zwischen dem
# 0,618er und dem 0,65er Retracement. Welcher der beiden oben liegt, haengt
# von der Richtung der Bewegung ab - deshalb wird beim Bilden sortiert und
# nicht angenommen.
GOLDEN_POCKET = (0.618, 0.65)

# Wie nah zwei Stufen liegen muessen, um als eine Zone zu gelten. In
# Prozent des Preises, nicht in Dollar - sonst waere die Regel bei BTC eine
# andere als bei SOL.
TOLERANZ_PCT = 0.35


def golden_pocket(hoch, tief, aufwaerts=True):
    """Das Preisband zwischen 0,618 und 0,65.

    Gibt (unten, oben) zurueck, immer in dieser Reihenfolge - unabhaengig
    davon, ob die Bewegung auf- oder abwaerts lief. Genau das verlangt
    Svens Abschnitt 1B: "Unter-/Oberkante muessen unabhaengig von der
    Swing-Richtung korrekt sortiert werden."
    """
    if hoch is None or tief is None or hoch <= tief:
        return None
    spanne = hoch - tief
    a = (hoch - spanne * GOLDEN_POCKET[0]) if aufwaerts else (tief + spanne * GOLDEN_POCKET[0])
    b = (hoch - spanne * GOLDEN_POCKET[1]) if aufwaerts else (tief + spanne * GOLDEN_POCKET[1])
    return (min(a, b), max(a, b))


def im_golden_pocket(preis, hoch, tief, aufwaerts=True):
    """Liegt ein Preis im Golden Pocket? Raender zaehlen dazu."""
    band = golden_pocket(hoch, tief, aufwaerts)
    if band is None:
        return False
    return band[0] <= preis <= band[1]


def stufen_einer_welle(hoch, tief, aufwaerts=True, stufen=None,
                       zeitrahmen="", welle_id=""):
    """Alle Fibonacci-Stufen EINER Welle, als Liste von Beschreibungen.

    Jede Stufe traegt ihre Herkunft mit: Zeitrahmen und Welle. Das ist die
    Voraussetzung dafuer, dass der Score spaeter nicht dieselbe Information
    doppelt zaehlen kann.
    """
    if hoch is None or tief is None or hoch <= tief:
        return []
    stufen = STUFEN_HANDEL if stufen is None else stufen
    spanne = hoch - tief
    raus = []
    for r in stufen:
        preis = (hoch - spanne * r) if aufwaerts else (tief + spanne * r)
        raus.append({
            "verhaeltnis": r,
            "preis": preis,
            "zeitrahmen": zeitrahmen,
            "welle": welle_id,
            "richtung": "auf" if aufwaerts else "ab",
            "golden": r in GOLDEN_POCKET,
            "anker": r in (0.0, 1.0),
        })
    return raus


def wellen_aus_fraktalen(df, weite=2, jetzt_index=None, hoechstens=3):
    """Die juengsten bestaetigten Wellen aus den Fraktalen eines Zeitrahmens.

    Eine Welle ist ein Paar aus benachbartem Swing-Tief und Swing-Hoch.
    KAUSALITAET: `swing_punkte` gibt zu jedem Punkt `bestaetigt_ab` an -
    den Index, ab dem er ueberhaupt erkennbar war. Punkte, die zum
    Zeitpunkt `jetzt_index` noch nicht bestaetigt waren, fallen hier raus.
    Ohne diese Zeile haette man eine Welle, die es damals nicht gab.

    `weite` ist das n aus Svens Abschnitt 1A: ein Fraktal besteht aus
    2*n+1 Kerzen, bei n=2 also aus fuenf.
    """
    hochs, tiefs = swing_punkte(df, weite=weite)
    grenze = len(df) - 1 if jetzt_index is None else jetzt_index
    hochs = [p for p in hochs if p[2] <= grenze]
    tiefs = [p for p in tiefs if p[2] <= grenze]
    if not hochs or not tiefs:
        return []

    # Punkte nach Zeit mischen, dann benachbarte Gegensatzpaare bilden
    punkte = ([(i, preis, "hoch") for i, preis, _ in hochs]
              + [(i, preis, "tief") for i, preis, _ in tiefs])
    punkte.sort(key=lambda x: x[0])

    wellen = []
    for a, b in zip(punkte, punkte[1:]):
        if a[2] == b[2]:
            continue                       # zwei Hochs hintereinander: keine Welle
        tief_zuerst = a[2] == "tief"
        tief = a[1] if tief_zuerst else b[1]
        hoch = b[1] if tief_zuerst else a[1]
        if hoch <= tief:
            continue
        wellen.append({
            "tief": tief, "hoch": hoch,
            "aufwaerts": tief_zuerst,       # Tief zuerst -> Aufwaertsbewegung
            "von_index": a[0], "bis_index": b[0],
            "id": "%d-%d" % (a[0], b[0]),
        })
    return wellen[-hoechstens:] if hoechstens else wellen


def konfluenz(stufenlisten, toleranz_pct=TOLERANZ_PCT, nur_unter=None):
    """Fasst Stufen aus MEHREREN Zeitrahmen zu Zonen zusammen.

    `stufenlisten` ist eine Liste von Listen, wie sie stufen_einer_welle
    liefert. `nur_unter` beschraenkt auf Stufen unterhalb eines Preises
    (fuer Kaufzonen).

    Die Toleranz ist RELATIV: zwei Stufen gehoeren zusammen, wenn ihr
    Abstand unter `toleranz_pct` Prozent liegt. Absolut waere die Regel bei
    BTC eine voellig andere als bei SOL.
    """
    alle = []
    for liste in stufenlisten:
        for s in liste:
            if s["anker"]:
                continue                   # 0 und 1 sind die Anker, keine Stufen
            if nur_unter is not None and s["preis"] >= nur_unter:
                continue
            if s["preis"] > 0:
                alle.append(s)
    if not alle:
        return []

    alle.sort(key=lambda s: s["preis"])
    zonen, laufend = [], [alle[0]]
    for s in alle[1:]:
        mitte = sum(x["preis"] for x in laufend) / len(laufend)
        if abs(s["preis"] - mitte) / mitte * 100.0 <= toleranz_pct:
            laufend.append(s)
        else:
            zonen.append(_zone_bauen(laufend))
            laufend = [s]
    zonen.append(_zone_bauen(laufend))
    return zonen


def _zone_bauen(stufen):
    """Baut eine Konfluenzzone und bewertet sie.

    DIE BEWERTUNG IST DER HEIKLE TEIL. Svens Prompt verlangt, dass nicht
    dieselbe Information mehrfach als Bestaetigung zaehlt. Drei Stufen
    derselben Welle, die zufaellig nah beieinanderliegen, sind EINE
    Beobachtung.

    Deshalb wird nach Herkunft gezaehlt:
      - je (Zeitrahmen, Welle) zaehlt nur die staerkste Stufe
      - der Score ist die Zahl UNABHAENGIGER Quellen
      - Golden Pocket und 0,618 geben einen Zuschlag, aber nur einmal

    Ohne diese Regel bekaeme jede Stelle im Chart einen hohen Score, sobald
    man genug Stufen einzeichnet - und der Score waere eine Funktion der
    Zeichenwut, nicht des Marktes.
    """
    preise = [s["preis"] for s in stufen]
    unten, oben = min(preise), max(preise)
    mitte = sum(preise) / len(preise)

    # Gewicht je Stufe - welche gilt als staerker
    def gewicht(s):
        if s["verhaeltnis"] in GOLDEN_POCKET:
            return 3
        if s["verhaeltnis"] in (0.5, 0.786):
            return 2
        return 1

    # Je Quelle nur die staerkste Stufe
    je_quelle = {}
    for s in stufen:
        schluessel = (s["zeitrahmen"], s["welle"])
        if schluessel not in je_quelle or gewicht(s) > gewicht(je_quelle[schluessel]):
            je_quelle[schluessel] = s

    zeitrahmen = sorted({s["zeitrahmen"] for s in je_quelle.values() if s["zeitrahmen"]})
    hat_golden = any(s["verhaeltnis"] in GOLDEN_POCKET for s in je_quelle.values())

    # Score: Zahl unabhaengiger Quellen, plus je ein Punkt fuer
    # Golden Pocket und fuer mehr als einen Zeitrahmen. Beides nur EINMAL.
    score = len(je_quelle)
    if hat_golden:
        score += 1
    if len(zeitrahmen) > 1:
        score += 1

    return {
        "unten": unten, "oben": oben, "mitte": mitte,
        "breite_pct": (oben - unten) / mitte * 100.0 if mitte else 0.0,
        "score": score,
        "quellen": len(je_quelle),          # unabhaengige Beobachtungen
        "stufen_roh": len(stufen),          # wie viele Linien es wirklich sind
        "zeitrahmen": zeitrahmen,
        "golden_pocket": hat_golden,
        "stufen": sorted(je_quelle.values(), key=lambda s: -gewicht(s)),
        # Vollstaendige Herkunft, wie im Prompt verlangt: "muss alle
        # Quell-Level, Wellen und Timeframes vollstaendig und
        # nachvollziehbar speichern"
        "herkunft": [{"zeitrahmen": s["zeitrahmen"], "welle": s["welle"],
                      "verhaeltnis": s["verhaeltnis"], "preis": s["preis"]}
                     for s in stufen],
    }


def zonen_aus_zeitrahmen(daten, weite=2, hoechstens_wellen=3,
                         toleranz_pct=TOLERANZ_PCT, nur_unter=None,
                         jetzt=None):
    """Der ganze Weg in einem Aufruf.

    `daten` ist ein Dict Zeitrahmen -> DataFrame, z. B.
        {"1d": df_tag, "4h": df_4h, "1h": df_1h}
    `jetzt` ist ein Dict Zeitrahmen -> Index, bis zu dem gerechnet werden
    darf. Fehlt es, wird die letzte Kerze genommen.

    Gibt die Konfluenzzonen zurueck, die staerkste zuerst.
    """
    listen = []
    for tf, df in (daten or {}).items():
        if df is None or len(df) < 2 * weite + 2:
            continue
        idx = (jetzt or {}).get(tf)
        for w in wellen_aus_fraktalen(df, weite=weite, jetzt_index=idx,
                                      hoechstens=hoechstens_wellen):
            listen.append(stufen_einer_welle(
                w["hoch"], w["tief"], aufwaerts=w["aufwaerts"],
                zeitrahmen=tf, welle_id=w["id"]))
    zonen = konfluenz(listen, toleranz_pct=toleranz_pct, nur_unter=nur_unter)
    return sorted(zonen, key=lambda z: (-z["score"], -z["mitte"]))
