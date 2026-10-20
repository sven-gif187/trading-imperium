# -*- coding: utf-8 -*-
"""Hold/Recovery im SCHATTENMODUS - sie haelt nichts und verkauft nichts.

WAS DIESE REGEL WAERE, WENN SIE SCHARF WAERE
--------------------------------------------
Svens Handelsweg vom 14.09.2026 sieht vor: Geht eine Position ins Minus,
wird sie nicht verkauft, sondern **ausgesessen** - solange die Struktur
haelt, die den Einstieg begruendet hat. Erst wenn der Kurs unter das
Swing-Tief faellt, aus dem die Kaufzone gebildet wurde, ist die These
widerlegt und die Position wird geschlossen.

DER PUNKT, DEN MAN KENNEN MUSS
------------------------------
Ein Verfahren, das Verlierer aussitzt, erzeugt **zwangslaeufig** eine hohe
Trefferquote. Fast jede Position wird irgendwann gruen - bis eine es nicht
wird. Der Verlust kommt selten und dann gross.

> **Das ist die haeufigste Erklaerung fuer "80 % Trefferquote".** Nicht,
> weil die Methode schlecht waere - sondern weil die Trefferquote allein
> bei dieser Bauart nichts aussagt. Was zaehlt, ist der Erwartungswert
> ueber ALLE Faelle, der groesste Rueckgang und die laengste Verlustserie.

Deshalb misst diese Datei von Anfang an mit, was die Trefferquote
verschweigt: wie tief es zwischendurch ging, wie lange, und wie oft die
Notbremse gezogen haette.

DIE NOTBREMSE
-------------
Sven hat am 14.09.2026 entschieden: **Notbremse bei -15 %**, abweichend
vom urspruenglichen Prompt, der gar keinen Stop vorsah.

Der Wert ist nicht gegriffen. Kriterium E der Freigabe (`go_live_check.py`)
verlangt einen groessten Rueckgang von hoechstens 15 %. Eine Regel, die
eine einzelne Position tiefer fallen laesst, koennte dieses Kriterium mit
einem einzigen Handel reissen - und dann waere die ganze Messung wertlos.

    NORMAL      Position im Plus oder noch nie im Minus gewesen
    RECOVERY    im Minus, Struktur haelt - wird ausgesessen
    ERHOLT      aus RECOVERY zurueck ueber null
    INVALIDIERT Struktur gebrochen: Kurs unter dem Swing-Tief
    NOTBREMSE   -15 % erreicht, unabhaengig von der Struktur

KEIN SCALE-IN
-------------
Svens Prompt sieht Nachkaeufe an tieferen Zonen vor, aber ausdruecklich
"standardmaessig deaktiviert". Diese Datei kennt sie deshalb gar nicht.
Nachkaufen im Verlust verschiebt den Einstand nach unten UND erhoeht den
Einsatz genau dann, wenn die These gerade nicht aufgeht - das ist eine
eigene Entscheidung mit eigener Messung, nicht ein Schalter nebenbei.

SIE HANDELT NICHT
-----------------
Wie `risk/exit_rules_schatten.py` rechnet diese Datei bei jedem Kurs-Update
mit, was sie GETAN HAETTE, und schreibt es nach `telemetrie.db`. Sie kennt
weder Orders noch Positionen. Der echte Stop-Loss, die Breakeven-Sperre und
die Trailing-Leiter laufen voellig unberuehrt weiter.

Erst wenn die Messung zeigt, dass sie traegt, wird ueber das Scharfstellen
geredet - und das braucht dann eine eigene Epochengrenze.
"""
from core.kosten import K_BASIS_PCT

REGEL_NAME = "HOLD_RECOVERY_15"

# Sven, 14.09.2026. Abweichend vom Prompt, der keinen Stop vorsah.
# Begruendung: Kriterium E der Freigabe erlaubt hoechstens 15 % Rueckgang.
NOTBREMSE_PCT = -15.0

# Wie weit unter das Swing-Tief der Kurs muss, damit die Struktur als
# gebrochen gilt. Ohne Puffer wuerde ein einzelner Docht die These
# widerlegen - und Dochte gibt es in jedem Kursverlauf.
INVALIDIERUNG_PUFFER_PCT = 0.3

# Ab hier gilt eine Position als "im Minus". Nicht exakt null, sonst
# schaltet die Regel bei jedem Kursrauschen hin und her.
RECOVERY_AB_PCT = -0.2

ZUSTAENDE = ("NORMAL", "RECOVERY", "ERHOLT", "INVALIDIERT", "NOTBREMSE")


def struktur_gebrochen(preis, swing_tief, puffer_pct=INVALIDIERUNG_PUFFER_PCT):
    """Ist die These widerlegt?

    Die These lautet: "Der Kurs dreht an dieser Zone." Sie ist widerlegt,
    wenn er unter das Tief faellt, aus dem die Zone gebildet wurde - mit
    Puffer, damit ein einzelner Docht nicht reicht.
    """
    if swing_tief is None or swing_tief <= 0 or preis is None:
        return False
    return float(preis) < float(swing_tief) * (1.0 - puffer_pct / 100.0)


def bewerte(pnl_pct, preis=None, swing_tief=None, tiefster_pnl_pct=None,
            notbremse_pct=NOTBREMSE_PCT,
            puffer_pct=INVALIDIERUNG_PUFFER_PCT,
            recovery_ab_pct=RECOVERY_AB_PCT):
    """Was wuerde Hold/Recovery in diesem Moment tun?

    pnl_pct          aktueller Buchgewinn in Prozent
    preis            aktueller Kurs (fuer die Struktur-Pruefung)
    swing_tief       das Tief, das die Kaufzone begruendet hat
    tiefster_pnl_pct schlechtester Stand bisher - fuer die Notbremse

    Rueckgabe: dict mit zustand, verkauft (bool), grund.

    Die Reihenfolge der Pruefungen ist nicht beliebig: Die Notbremse kommt
    VOR der Struktur. Waere es andersherum, koennte eine Position bei -20 %
    weiterlaufen, solange die Struktur formal noch haelt - und genau das
    soll die Notbremse verhindern.
    """
    try:
        pnl = float(pnl_pct)
    except (TypeError, ValueError):
        return {"zustand": "NORMAL", "verkauft": False,
                "grund": "kein Gewinnwert"}

    tiefst = pnl if tiefster_pnl_pct is None else min(float(tiefster_pnl_pct), pnl)

    # 1. Notbremse - immer zuerst
    if tiefst <= notbremse_pct:
        return {"zustand": "NOTBREMSE", "verkauft": True,
                "grund": "Notbremse: %.2f %% erreicht (Grenze %.1f %%)"
                         % (tiefst, notbremse_pct),
                "tiefster_pnl_pct": tiefst}

    # 2. Struktur gebrochen
    if struktur_gebrochen(preis, swing_tief, puffer_pct):
        return {"zustand": "INVALIDIERT", "verkauft": True,
                "grund": "Struktur gebrochen: %.8g unter Swing-Tief %.8g "
                         "(Puffer %.2f %%)" % (preis, swing_tief, puffer_pct),
                "tiefster_pnl_pct": tiefst}

    # 3. Im Minus, Struktur haelt -> aussitzen
    if pnl <= recovery_ab_pct:
        return {"zustand": "RECOVERY", "verkauft": False,
                "grund": "im Minus (%.2f %%), Struktur haelt - wird "
                         "ausgesessen" % pnl,
                "tiefster_pnl_pct": tiefst}

    # 4. Wieder ueber null, nachdem es im Minus war
    if tiefst <= recovery_ab_pct and pnl > 0:
        return {"zustand": "ERHOLT", "verkauft": False,
                "grund": "zurueck im Plus (%.2f %%), tiefster Stand war "
                         "%.2f %%" % (pnl, tiefst),
                "tiefster_pnl_pct": tiefst}

    return {"zustand": "NORMAL", "verkauft": False,
            "grund": "%.2f %%" % pnl, "tiefster_pnl_pct": tiefst}


def haette_gehalten(pnl_pct, preis=None, swing_tief=None,
                    tiefster_pnl_pct=None, **kw):
    """True, wenn diese Regel die Position JETZT noch halten wuerde.

    Das ist die Frage, die im Schattenbetrieb zaehlt: Der echte Bot
    verkauft gerade - haette Hold/Recovery weitergehalten?
    """
    e = bewerte(pnl_pct, preis, swing_tief, tiefster_pnl_pct, **kw)
    return not e["verkauft"]


def grund_text(pnl_pct, preis=None, swing_tief=None, tiefster_pnl_pct=None,
               **kw):
    """Menschenlesbarer Grund, fuer die Telemetrie."""
    e = bewerte(pnl_pct, preis, swing_tief, tiefster_pnl_pct, **kw)
    return "%s | %s" % (e["zustand"], e["grund"])


def netto(brutto_pct, kosten_pct=None):
    """Bruttobewegung minus Kosten einer Runde.

    Steht hier, damit im Schattenprotokoll nie eine Bruttozahl landet:
    eine Position, die sich von -1,0 auf +0,3 % erholt, hat nach 0,505 %
    Kosten immer noch verloren.
    """
    k = K_BASIS_PCT if kosten_pct is None else kosten_pct
    try:
        return float(brutto_pct) - k
    except (TypeError, ValueError):
        return None
