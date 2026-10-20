# -*- coding: utf-8 -*-
"""Fibonacci-Ausstiegsziele - die zweite Haelfte von Svens Verfahren.

WARUM ES DAS BRAUCHT
--------------------
Seit dem 15.09.2026 steigt der Bot nach Svens Verfahren EIN: gekauft
wird nur in einer Fibonacci-Konfluenzzone (features/fraktal_tor.py).

Ausgestiegen wurde weiter nach dem alten Muster - Stop-Loss bei
-2,5 %, Trailing ab +1,57 %, Breakeven-Sperre. Feste Prozentmarken,
die nichts vom Chart wissen.

Genau so sah der erste echte Handel aus: Einstieg im Golden Pocket,
Ausstieg per Stop-Loss bei -2,26 %. Halb nach Verfahren, halb nach
Schema. Sven am 15.09.: *"das system vervollstaendigen damit er
komplett nach dem neuen muster handelt [...] im ein und ausstieg mit
fibonacci zonen"*.

DIE RECHNUNG
------------
Gekauft wird im Ruecksetzer einer AUFWAERTSWELLE (Tief -> Hoch). Die
Ziele sind Verlaengerungen genau dieser Welle, gemessen vom Tief:

    Ziel 1   1,000  =  das Wellenhoch selbst
    Ziel 2   1,272  =  Tief + Spanne * 1,272
    Ziel 3   1,618  =  Tief + Spanne * 1,618

Die Verhaeltnisse stammen aus FIB_VOR in features/chartanalyse.py:233
und sind dort an Marks eigenen Charts nachgerechnet (Abweichung 0,01 $
ueber vier Raster).

ZUR RICHTUNG - EIN PUNKT, DER LEICHT SCHIEFGEHT
-----------------------------------------------
`fibonacci_ziele()` in chartanalyse.py legt die Verlaengerungen nach
MARKS Konvention an: ueber den AELTEREN Anker hinaus. Bei einer
Aufwaertsbewegung zeigt Marks 1,618 deshalb nach UNTEN.

Das ist fuer SEINE Frage richtig (wohin laeuft die Korrektur) und fuer
UNSERE falsch (wohin laeuft der Gewinn). Deshalb wird hier eigens
gerechnet statt jene Funktion aufzurufen - und deshalb bleibt sie
unangetastet. Wer dort die Richtung drehte, um hier ein Ziel zu
bekommen, wuerde Marks Gegenprobe (mark_gegenprobe.py) still
zerstoeren.

WAS DIESES MODUL NICHT TUT
--------------------------
Es verkauft nicht und kennt keine Orders. Es rechnet Preise aus und
sagt, welches Ziel erreicht ist. Ob daraus ein Verkauf wird,
entscheidet runtime/exit_monitor.py.
"""

# Die Zielstufen. 1,0 ist das Wellenhoch - das erste natuerliche Ziel
# eines Kaufs im Ruecksetzer: dorthin zurueck, wo die Bewegung herkam.
ZIELE = (1.0, 1.272, 1.618)

# Welches Ziel den Verkauf ausloest.
#
# 1,0 ist das Wellenhoch - dorthin zurueck, wo die Bewegung herkam.
# Das ist das haeufigste und damit verlaesslichste Ziel.
#
# WARUM NICHT GESTAFFELT (Stand 15.09.2026):
# Der naheliegende Wunsch waere, an jedem Ziel einen Teil zu verkaufen
# (40/30/30). Dagegen sprechen zwei harte Gruende:
#
#   1. Der Verkaufspfad ist auf Ganz-oder-nichts gebaut. Nach einem
#      Verkauf raeumt runtime/exit_monitor.py:588 die Position ueber
#      record_result() atomar weg. Ein Teilverkauf braeuchte einen
#      Umbau dieser Kette - und ein halb umgebauter Verkaufspfad ist
#      ein Kapitalrisiko, kein Feature.
#   2. Bei der aktuellen Kontogroesse traegt es nicht. 30 % der
#      ETH-Position vom 15.09. waeren 0,00126 ETH, rund 3 $ - unter
#      dem, was die Boerse als Order annimmt. Der Teilverkauf wuerde
#      scheitern und die Position stehen lassen.
#
# Das gehoert gebaut, wenn das Konto groesser ist und der
# Verkaufspfad Teilmengen sauber fuehrt. Bis dahin: ein Ziel, ganze
# Position. Steht als offener Punkt in OFFEN.md.
ZIEL_VERKAUF = 1.0

# Die Staffel-Anteile, fuer den Tag, an dem Teilverkaeufe gebaut
# werden. Nicht gemessen - eine Setzung, und sie ist derzeit an KEINER
# Stelle angeschlossen. Absichtlich hier stehengelassen, damit die
# Absicht dokumentiert ist und nicht neu erfunden wird.
ANTEILE = {1.0: 0.40, 1.272: 0.30, 1.618: 0.30}

# Ein Ziel gilt als erreicht, wenn der Kurs es beruehrt. Kein Puffer
# nach oben - wer auf "sicher darueber" wartet, verkauft im Ruecklauf.
# Kleine Toleranz nach unten, damit ein Ziel nicht um zwei Cent
# verfehlt wird.
TOLERANZ_PCT = 0.05


def ziele_berechnen(welle):
    """Die Ausstiegsziele einer Kaufwelle.

    `welle` ist das dict aus dem Urteil des Tors:
        {"hoch": float, "tief": float, ...}

    Rueckgabe: Liste von dicts, aufsteigend nach Preis:
        [{"verhaeltnis": 1.0, "preis": ..., "anteil": 0.40}, ...]
    Leere Liste, wenn die Welle unbrauchbar ist.
    """
    if not welle:
        return []
    try:
        hoch = float(welle.get("hoch") or 0)
        tief = float(welle.get("tief") or 0)
    except (TypeError, ValueError):
        return []
    if hoch <= 0 or tief <= 0 or hoch <= tief:
        return []

    spanne = hoch - tief
    return [{"verhaeltnis": r,
             "preis": tief + spanne * r,
             "anteil": ANTEILE.get(r, 0.0)}
            for r in ZIELE]


def erreichtes_ziel(welle, preis, schon_verkauft=None):
    """Welches Ziel ist bei diesem Preis erreicht - und noch offen?

    `schon_verkauft` ist eine Liste der Verhaeltnisse, die bereits
    bedient wurden. Ohne sie wuerde dasselbe Ziel bei jedem Tick
    erneut ausloesen - der Bot prueft alle 12 Sekunden.

    Rueckgabe: das HOECHSTE erreichte, noch offene Ziel, oder None.

    Warum das hoechste und nicht das naechste: Springt der Kurs ueber
    mehrere Ziele auf einmal (Nachrichtenlage, duenne Orderbuecher),
    waere es falsch, nur das unterste zu bedienen und den Rest auf
    einen Ruecklauf warten zu lassen, der vielleicht nie kommt.
    """
    if not preis or preis <= 0:
        return None
    schon = set(schon_verkauft or [])
    treffer = None
    for z in ziele_berechnen(welle):
        if z["verhaeltnis"] in schon:
            continue
        grenze = z["preis"] * (1.0 - TOLERANZ_PCT / 100.0)
        if preis >= grenze:
            treffer = z          # weiterlaufen: hoeheres Ziel gewinnt
    return treffer


def restanteil(schon_verkauft):
    """Wieviel der urspruenglichen Position noch offen ist (0 bis 1).

    Wird gebraucht, um am letzten Ziel wirklich auf null zu kommen -
    Rundungsreste wuerden sonst eine Kleinstposition stehen lassen,
    die die Boerse gar nicht mehr verkaufen kann.
    """
    schon = set(schon_verkauft or [])
    return max(0.0, 1.0 - sum(ANTEILE.get(r, 0.0) for r in schon))


def ist_letztes_ziel(verhaeltnis):
    """Ist das das hoechste Ziel? Dann wird der ganze Rest verkauft."""
    return verhaeltnis == ZIELE[-1]


def beschreibung(welle, preis=None):
    """Eine Zeile fuers Log - die Ziele mit Abstand zum aktuellen Kurs."""
    z = ziele_berechnen(welle)
    if not z:
        return "keine Ziele (Welle unbrauchbar)"
    teile = []
    for x in z:
        if preis and preis > 0:
            weg = (x["preis"] - preis) / preis * 100.0
            teile.append(f"{x['verhaeltnis']:.3f}={x['preis']:,.2f}"
                         f" ({weg:+.2f}%)")
        else:
            teile.append(f"{x['verhaeltnis']:.3f}={x['preis']:,.2f}")
    return " | ".join(teile)
