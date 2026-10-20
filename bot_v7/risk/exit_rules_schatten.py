# -*- coding: utf-8 -*-
"""Alternative Ausstiegsregel im SCHATTENMODUS - sie verkauft NICHTS.

==================================================================
ZWECK
==================================================================
Diese Regel rechnet bei jedem Kurs-Update mit, wann SIE verkauft
haette, und schreibt das in telemetrie.db (Tabelle schatten_exits).
Die Position laeuft unveraendert weiter. Nach dem Messfenster steht
schwarz auf weiss, welche der beiden Regeln mehr uebrig gelassen
haette - gemessen, nicht geraten.

==================================================================
DIE FRAGE, DIE SIE BEANTWORTEN SOLL (Sven, 13.08.2026)
==================================================================
"Ich hoffe halt nur, dass wenn wir bei 20 % im Plus sind, nicht erst
5 Prozent fallen muessen, bevor wir den Gewinn mitnehmen."

Die heutige Leiter (risk/exit_rules.py) misst den Abstand am KURS:
1,0 % Basis mal einem Faktor, der mit dem Hoechststand WEITER wird
(bis 2,2x ueber +8 %). Diese hier misst am GEWINN: gib hoechstens
einen festen Anteil des Hoechstgewinns wieder her.

==================================================================
WO SIE BESSER IST - UND WO SCHLECHTER
==================================================================
Gerechnet am 13.08.2026 mit Basis 1,0 % und der Leiter aus
risk/exit_rules.py, Angaben in Prozentpunkten Gewinn:

    Hoechststand   heute raus bei   25 %-Regel   besser
        +1,5 %          +0,48 %       +1,00 %    25 %-Regel
        +2,0 %          +0,98 %       +1,50 %    25 %-Regel
        +3,0 %          +1,66 %       +2,25 %    25 %-Regel
        +5,0 %          +3,22 %       +3,75 %    25 %-Regel
        +8,0 %          +5,62 %       +6,00 %    25 %-Regel
       +15,0 %         +12,47 %      +11,25 %    heutige
       +23,0 %         +20,29 %      +17,25 %    heutige

Klartext: Die 25 %-Regel ist bei kleinen und mittleren Gewinnen
besser, ab etwa +12 % ist die heutige Leiter besser. Der Wendepunkt
liegt dort, wo 25 % des Gewinns groesser werden als der feste
Kursabstand.

Das ist KEIN Argument gegen sie, denn: Der Median-Hoechststand
liegt bei +1,54 % (37 Trades mit MFE-Daten), und nur 2 von 37
Trades kamen je ueber +5 %. Die Masse liegt genau dort, wo die
25 %-Regel gewinnt. Ob das reicht, um die seltenen grossen Trades
aufzuwiegen, entscheidet die Messung - nicht diese Datei.

==================================================================
WARUM ES EINE UNTERGRENZE GIBT
==================================================================
Ein reiner Prozentsatz waere bei kleinen Gewinnen zu eng. Beispiel:
Hoechststand +1,0 %, davon 25 % = 0,25 Prozentpunkte Spielraum. So
wenig schwankt ein Kurs im Minutentakt von allein - die Regel wuerde
praktisch sofort nach jedem Hoch ausloesen und nur noch Rauschen
handeln.

MINDEST_RUECKGABE_PCT setzt deshalb einen Boden: Der Spielraum ist
nie enger als 0,5 Prozentpunkte.

==================================================================
WARUM ERST AB +1 %
==================================================================
Bei 500 $ Kapital und 30 % Positionsgroesse sind das 150 $ je
Position. Die Kosten einer Runde betragen 0,32 % (2x0,10 %
Gebuehr + 2x0,06 % Schlupf) = 0,48 $. Ein Ausstieg unterhalb
davon ist Arbeit fuer nichts:

    Ausstieg bei    brutto     nach Kosten
        +0,35 %     0,53 $        0,04 $     <- heutige Breakeven-Sperre
        +0,50 %     0,75 $        0,27 $
        +1,00 %     1,50 $        1,02 $
        +1,50 %     2,25 $        1,77 $

Vier Cent bei der Breakeven-Sperre. Genau das meinte Sven mit
"deshalb fallen die Trades unter 1 Prozent so niedrig aus". Diese
Regel wird deshalb erst ab +1,0 % Hoechststand aktiv und steigt nie
unterhalb der Kostenschwelle plus Marge aus.

==================================================================
ABGRENZUNG
==================================================================
Diese Datei aendert NICHTS am Handel. Sie berechnet nur. Der
Aufrufer (runtime/exit_monitor.py) schreibt das Ergebnis in die
Telemetrie und verkauft ausdruecklich nicht. Solange das so bleibt,
darf sie auch waehrend eines laufenden Messfensters mitlaufen
(MASTERPROMPT.md, Abschnitt 0).
"""

# Anteil des Hoechstgewinns, der zurueckgegeben werden darf.
# 0.25 = "gib hoechstens ein Viertel des besten Standes wieder her".
GEWINN_ANTEIL = 0.25

# Untergrenze fuer den Spielraum in Prozentpunkten. Verhindert, dass
# die Regel bei kleinen Gewinnen im Kursrauschen ersaeuft (siehe oben).
MINDEST_RUECKGABE_PCT = 0.5

# Darunter bleibt die Regel stumm - der Stop-Loss regiert allein.
AKTIV_AB_PCT = 1.0

# Echte Kosten einer Runde: 2x0,10 % Gebuehr + 2x0,06 % Schlupf.
# Identisch zur Rechnung in risk/exit_rules.py (BREAKEVEN_PUFFER_PCT).
# [13.09.2026] Die Zahl steht jetzt an EINER Stelle: core/kosten.py.
# Hier stand 0.32 % - die alte Annahme aus der Zeit vor Bybit EU.
# Neun Dateien mit neun eigenen Kostenzahlen waren neun Gelegenheiten,
# eine davon zu vergessen; genau das war passiert. Diese Datei rechnet
# nur aus und handelt nicht - die Umstellung ist deshalb
# freeze-vertraeglich.
from core.kosten import K_BASIS_PCT
KOSTEN_PCT = K_BASIS_PCT
# exakt null landet.
KOSTEN_MARGE_PCT = 0.03

REGEL_NAME = "GEWINN_RATSCHE_25"


def schwelle(hoechst_pnl_pct,
             anteil=GEWINN_ANTEIL,
             mindest_rueckgabe_pct=MINDEST_RUECKGABE_PCT,
             aktiv_ab_pct=AKTIV_AB_PCT,
             kosten_pct=KOSTEN_PCT,
             kosten_marge_pct=KOSTEN_MARGE_PCT):
    """Ab welchem Gewinn wuerde diese Regel verkaufen?

    hoechst_pnl_pct : bester Gewinnstand der Position in Prozent

    Rueckgabe: (aktiv, ausstieg_bei_pct, rueckgabe_pct)
        aktiv           - False, solange der Hoechststand zu niedrig ist
        ausstieg_bei_pct- Gewinn in %, bei dessen Unterschreiten verkauft wuerde
        rueckgabe_pct   - wie viele Prozentpunkte Spielraum das sind

    Wie die Leiter in exit_rules.py ist das eine RATSCHE: Der Wert
    haengt am Hoechststand, nicht am aktuellen Gewinn, und wird auf
    dem Rueckweg nie wieder lockerer.
    """
    try:
        hoch = float(hoechst_pnl_pct)
    except (TypeError, ValueError):
        return (False, 0.0, 0.0)

    if hoch < aktiv_ab_pct:
        return (False, 0.0, 0.0)

    rueckgabe = max(hoch * anteil, mindest_rueckgabe_pct)
    ausstieg = hoch - rueckgabe

    # Nie unterhalb der Kostenschwelle aussteigen - sonst ist der
    # "gesicherte Gewinn" nach Gebuehren und Schlupf negativ.
    #
    # [13.08.2026] Bei den STANDARDWERTEN greift dieser Boden nie, und
    # das ist Absicht, kein toter Code: Der niedrigste moegliche
    # Ausstieg ist AKTIV_AB_PCT - MINDEST_RUECKGABE_PCT = 1,0 - 0,5 =
    # +0,5 %, und das liegt bereits ueber dem Boden von +0,35 %.
    # Beim Testen ist genau das aufgefallen.
    #
    # Der Boden ist eine Absicherung gegen spaetere Parameteraenderungen.
    # Wer AKTIV_AB_PCT auf 0,6 senkt, bekaeme sonst Ausstiege bei
    # +0,1 % - nach 0,32 % Kosten ein garantierter Verlust. Genau
    # dieser Fehler steckte bis zum 10.08. in der Breakeven-Sperre
    # (BREAKEVEN_PUFFER_PCT stand auf 0,25 %, alle sechs Ausstiege
    # endeten im Minus, siehe risk/exit_rules.py).
    boden = kosten_pct + kosten_marge_pct
    if ausstieg < boden:
        ausstieg = boden
        rueckgabe = hoch - ausstieg

    return (True, round(ausstieg, 3), round(rueckgabe, 3))


def loest_aus(pnl_pct, hoechst_pnl_pct, **kw):
    """True, wenn diese Regel jetzt verkaufen wuerde.

    pnl_pct         : aktueller Gewinn in %
    hoechst_pnl_pct : bester Stand in %
    """
    aktiv, ausstieg, _ = schwelle(hoechst_pnl_pct, **kw)
    if not aktiv:
        return False
    try:
        return float(pnl_pct) <= ausstieg
    except (TypeError, ValueError):
        return False


def grund_text(pnl_pct, hoechst_pnl_pct, **kw):
    """Klartext fuer die Telemetrie-Zeile."""
    _, ausstieg, rueckgabe = schwelle(hoechst_pnl_pct, **kw)
    return (f"GEWINN-RATSCHE {int(GEWINN_ANTEIL * 100)}% "
            f"(Hoch {float(hoechst_pnl_pct):+.2f}%, Schwelle "
            f"{ausstieg:+.2f}%, jetzt {float(pnl_pct):+.2f}%, "
            f"Spielraum {rueckgabe:.2f} Pp)")


def beschreibung():
    """Klartext fuer Log und Terminal-Reiter."""
    return (f"Gewinn-Ratsche (SCHATTEN, verkauft nicht): hoechstens "
            f"{int(GEWINN_ANTEIL * 100)} % des Hoechstgewinns zurueck, "
            f"mindestens {MINDEST_RUECKGABE_PCT} Pp Spielraum, aktiv ab "
            f"+{AKTIV_AB_PCT} %, Boden bei "
            f"+{KOSTEN_PCT + KOSTEN_MARGE_PCT:.2f} % (Kosten)")
