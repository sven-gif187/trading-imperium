# -*- coding: utf-8 -*-
"""
risk/exit_rules.py - Ausstiegs-Leiter  [E9-RR 29.07.2026]
==========================================================
EINE Wahrheit fuer Trailing-Stufen und Breakeven-Sperre.
Getrennt vom exit_monitor, damit die Regel OHNE Bot testbar ist.

------------------------------------------------------------------
GEMESSENE AUSGANGSLAGE (data_store/trades_v5.json, 423 Verkaeufe)
------------------------------------------------------------------
    Trefferquote          71.9 %
    Mittlerer Gewinn      +1.23 %  vom Positionsvolumen
    Mittlerer Verlust     -2.33 %
    Chance/Risiko in %     0.53      -> in Dollar nur 0.35
    Median MFE (Bestand)  +2.36 %
    Median realisiert     +0.43 %
    Groesster Gewinn      +4.64 %   <- KEIN Trade lief je weiter
    Exit-Verteilung: 161x Trailing (+142 $), 67x Stop-Loss (-183 $)

------------------------------------------------------------------
DER ECHTE DEFEKT DER ALTEN LEITER (nicht "zu eng", sondern SELBSTBEZUEGLICH)
------------------------------------------------------------------
Alt wurde der Trail-Faktor aus dem AKTUELLEN Gewinn bestimmt:
    >= 5.0 % -> 0.5x  |  >= 3.0 % -> 0.7x  |  >= 1.0 % -> 1.0x  |  > 0.3 % -> 1.6x

Daraus folgen zwei Fehler:

 1. INVERSION. Bei +2.99 % durfte der Kurs 1.0 % zuruecklaufen, bei
    +3.01 % nur noch 0.7 %, ab +5 % nur noch 0.5 %. Der stuendliche
    Rauschpegel dieser Coins liegt bei ~0.5-1.0 %. Ein Trade, der ueber
    +3 % steigt, wird also von der naechstbesten normalen Schwankung
    hinausgeworfen. Genau deshalb steht in 423 Verkaeufen als
    Maximum +4.64 % - die Leiter ist die Decke, nicht der Markt.

 2. SELBSTLOCKERUNG AUF DEM RUECKWEG. Faellt der Kurs, sinkt der
    aktuelle Gewinn, und damit WEITET sich der Trail rueckwirkend.
    Aus einem 0.7-%-Stop bei +3 % wird auf dem Weg nach unten ein
    1.0-%-Stop bei +2.1 %. Der Ausstieg ist damit kein Ratschen-
    mechanismus mehr, sondern eine bewegliche Zielscheibe.

------------------------------------------------------------------
NEUE LEITER
------------------------------------------------------------------
Der Faktor haengt am HOECHSTSTAND des Gewinns, nicht am aktuellen.
Das ist eine echte Ratsche: einmal erreicht, wird sie nie wieder
lockerer (Turtle-/Chandelier-Prinzip; Freqtrade macht es genauso
ueber trailing_stop_positive_offset).

  < 1.2 %      kein Trailing. Der Stop-Loss regiert.
  1.2 - 3.0 %  1.0x  - bewusst IDENTISCH zur alten Leiter. Hier liegt
                       der Median-MFE (2.36 %), also die Masse aller
                       Trades. Was dort funktioniert hat, wird nicht
                       ohne Beweis angefasst.
  3.0 - 5.0 %  1.3x  - hier wuergte die alte Leiter mit 0.7x
  5.0 - 8.0 %  1.7x  - alt 0.5x
  > 8.0 %      2.2x

Dazu eine BREAKEVEN-SPERRE: war die Position einmal ueber +1.0 %,
wird bei Rueckfall auf +0.35 % glattgestellt. Ein Gewinner wird nie
wieder zum Verlierer.

  [KORREKTUR 10.08.2026] Der Puffer stand bis dahin auf 0.25 % und war
  damit ZU NIEDRIG - er deckte nur die Gebuehren (2x0.1 %), nicht die
  Slippage (2x0.06 %). Echte Kosten 0.32 %. Die Sperre stellte also
  unterhalb des Breakeven glatt und erzeugte systematisch kleine
  Verluste: alle sechs BREAKEVEN_LOCK-Verkaeufe im Journal endeten im
  Minus. Details bei BREAKEVEN_PUFFER_PCT unten.

------------------------------------------------------------------
EHRLICHKEIT ZUR WIRKUNG
------------------------------------------------------------------
Dass die Aenderung Geld bringt, ist NICHT bewiesen. MFE/MAE wird erst
seit dem 25.07. protokolliert - es gibt genau 15 Trades mit Hoechst-
stand-Daten. Was bewiesen ist: die alte Regel war logisch defekt
(Inversion + Selbstlockerung) und ihre Obergrenze (+4.64 % in 423
Trades) passt exakt zu dieser Mechanik. Der Umbau unter +3 % ist
verhaltensgleich; das Risiko der Aenderung liegt allein im Bereich
darueber, wo bisher ohnehin fast nichts ankam.
Gegenprobe nach ~50 Verkaeufen: Median MFE gegen Median realisiert.
"""

# Vorgaben (Faktoren beziehen sich auf config.risk.trailing_stop_pct)
BREAKEVEN_AB_PCT = 1.0        # ab hier darf der Trade nicht mehr ins Minus
# [BREAKEVEN-FIX 10.08.2026] 0.25 -> 0.35.
#
# Der alte Wert deckte laut Kommentar "2x0.1 % Gebuehr" = 0.20 % und hatte
# 0.05 % Marge. Die SLIPPAGE fehlte in dieser Rechnung. Sie steht in jedem
# Journal-Eintrag als slippage_pct und liegt bei ~0.06 % JE SEITE:
#
#     Gebuehren   2 x 0.10 %  =  0.20 %
#     Slippage    2 x 0.06 %  =  0.12 %
#     ------------------------------------
#     echte Kosten            =  0.32 %   <- ueber dem alten Puffer 0.25 %
#
# Folge: Die Sperre stellte 0.07 Prozentpunkte UNTERHALB des echten
# Breakeven glatt. Sie sicherte also nicht die Null, sondern garantierte
# einen kleinen Verlust. Belegt in trades_v5.json - alle sechs
# BREAKEVEN_LOCK-Verkaeufe endeten im Minus (0 % Trefferquote, -0.83 $):
#     08.09. BTC -0.25 $  (war +1.02 %, jetzt +0.22 %)
#     08.07. SOL -0.16 $  (war +1.28 %, jetzt +0.19 %)
#     08.07. ETH -0.20 $  (war +1.22 %, jetzt +0.19 %)
#
# 0.35 % = 0.32 % Kosten + 0.03 % Marge. Die Trailing-Leiter bleibt
# unveraendert; geaendert wird ausschliesslich der Notausgang.
# Gegenprobe nach ~10 weiteren BREAKEVEN_LOCK-Verkaeufen: der Durchschnitt
# muss bei oder ueber 0 $ liegen, sonst ist auch 0.35 % noch zu niedrig.
# [PATCH 00a, ab 28.08.2026] Der Puffer wird gerechnet, nicht gesetzt.
#
# Vorher: 0.35 %, hergeleitet aus 2x0.10 % Gebuehr + 2x0.06 % Slippage.
# Diese Herleitung war am 10.08. richtig. Seit der Gebuehrenkorrektur
# (Bybit EU, 0,25 % je Seite) liegen die echten Kosten bei 0,505 % je
# Runde - der Puffer blieb stehen und garantierte damit einen kleinen
# VERLUST statt die Null zu sichern:
#
#     0.350 % - 0.505 % = -0.155 %
#
# Die im alten Kommentar verlangte Gegenprobe ist faellig und faellt
# durch: die vier BREAKEVEN_LOCK-Verkaeufe nach dem Fix liegen bei
# -0,594 $ im Schnitt, schlechter als die sechs davor.
#
# Jetzt aus der Konstante gerechnet, damit er beim naechsten
# Gebuehrenwechsel nicht wieder haengenbleibt.
# [KOSTENLATTE BITVAVO 14.10.2026] Bitvavo USDC: 2 x 0,05 % Gebuehr + 0.043 % Schlupf (Stichprobe)
# = 0.143 %, gerundet 0.15. Vorher 0.505 (Bybit EU). CLAUDE.md 8.
K_BASIS_PCT = 0.150           # Bitvavo USDC, CLAUDE.md 8
# [E12 PUFFER PFLICHTFELDER 15.10.2026] Marge 0,045 -> 0,10 (A5-V2, Entscheidung Sven E5): Ausloeseverzug der Nullsicherung
# im Mittel 0,072 %, p90 0,17 %. Mit 0,045 endete sie im Mittel bei -0,027 %, mit 0,10 bei +0,028 %.
BREAKEVEN_MARGE_PCT = 0.10    # damit die Null nicht knapp verfehlt wird
BREAKEVEN_PUFFER_PCT = round(K_BASIS_PCT + BREAKEVEN_MARGE_PCT, 3)   # 0.55
# [PATCH 45, 14.10.2026] Aus den Kosten gerechnet statt
# gesetzt. Nulllinie = (1+K)/(1-Trail)-1 = 1.520 % bei
# K=0.505 % und Trail=1.0 %, plus 0.05 % Marge.
# Der alte Wert 1.2 stammte aus einer Zeit mit 0,10 % Gebuehr je Seite
# (Nulllinie damals 1,33 %). Seit dem 13.08.2026 sind es 0,25 %.
# Wer Gebuehren oder Trail aendert, muss diesen Wert neu rechnen:
#     python patches_nach_27_08/patch_45_trailing_schwelle.py --pruefen
# [KOSTENLATTE BITVAVO 14.10.2026] Nulllinie (1+K)/(1-Trail)-1 bei K=0.15 und Trail=1.0 plus 0,05 Marge.
TRAIL_AB_PCT = 1.21            # darunter kein Trailing (vorher 1.57)
TREND_BONUS = 1.3             # Faktor obendrauf bei Regime TRENDING_UP

# (Hoechststand des Gewinns in %, Faktor) - aufsteigend, monoton WEITER.
# Letzter passender Eintrag gewinnt.
LEITER = (
    (1.2, 1.0),   # alt 1.0x  -> unveraendert (hier liegt die Masse)
    (3.0, 1.3),   # alt 0.7x  -> der Wuerger
    (5.0, 1.7),   # alt 0.5x
    (8.0, 2.2),   # alt 0.5x
)


# [V1 TRAILSTART WIRKSAM 14.10.2026] Marge ueber der Nulllinie, wie Patch 45.
# [E13 KLEINIGKEITEN 15.10.2026] 0,05 -> 0,10 (Entscheidung Sven E5b): gleiche Sicherheit wie der Puffer (E12),
# Ausloeseverzug im Mittel 0,072 %, p90 0,17 %. Start 0,85 -> 1,11 | 1,0 -> 1,26 | 1,3 -> 1,57.
TRAIL_MARGE_PCT = 0.10


def trail_start_pct(abstand_pct, k_pct=None, marge_pct=TRAIL_MARGE_PCT):
    """[V1 TRAILSTART WIRKSAM 14.10.2026] Ab welchem Hoch verdient ein Nachzieh-Stopp mit diesem Abstand?

    Nulllinie = (1 + K) / (1 - Abstand) - 1, dazu die Marge. K = Kosten je Runde
    (K_BASIS_PCT). Abstand = der WIRKSAME Abstand nach Regime, Leiter und Trend-Bonus.
    """
    k = K_BASIS_PCT if k_pct is None else k_pct
    return round(((1 + k / 100.0) / (1 - abstand_pct / 100.0) - 1) * 100.0 + marge_pct, 3)


def effektiver_trail(hoechst_pnl_pct, trail_pct, regime="",
                     trail_ab_pct=None, trend_bonus=TREND_BONUS):
    """Trail-Abstand in % vom Hoechstkurs. 0.0 = kein Trailing aktiv.

    WICHTIG: erstes Argument ist der HOECHSTSTAND des Gewinns, nicht der
    aktuelle. Nur so ist die Leiter eine Ratsche und lockert sich nicht
    auf dem Rueckweg.

    hoechst_pnl_pct : bester Gewinnstand der Position in %
    trail_pct       : Basiswert aus der Config (z.B. 1.0)
    regime          : enthaelt er TRENDING_UP, wird gelockert
    """
    try:
        hoch = float(hoechst_pnl_pct)
        trail_pct = float(trail_pct)
    except Exception:
        return 0.0
    if trail_pct <= 0:
        return 0.0
    faktor = LEITER[0][1]
    for schwelle, f in LEITER:
        if hoch >= schwelle:
            faktor = f
    if "TRENDING_UP" in str(regime).upper():
        faktor *= trend_bonus
    abstand = trail_pct * faktor
    # [V1 TRAILSTART WIRKSAM 14.10.2026] Start aus dem wirksamen Abstand statt fest TRAIL_AB_PCT
    # (Entscheidung Sven, A5-Vorschlag V1). Vorher: if hoch < TRAIL_AB_PCT.
    start = trail_ab_pct if trail_ab_pct is not None else trail_start_pct(abstand)
    if hoch < start:
        return 0.0
    return round(abstand, 3)


def breakeven_verletzt(pnl_pct, hoechst_pnl_pct,
                       breakeven_ab_pct=BREAKEVEN_AB_PCT,
                       puffer_pct=BREAKEVEN_PUFFER_PCT):
    """True, wenn die Breakeven-Sperre greift.

    Scharf erst, wenn die Position einmal ueber `breakeven_ab_pct` stand.
    Danach Ausstieg, sobald der Gewinn unter `puffer_pct` faellt.
    """
    try:
        pnl_pct = float(pnl_pct)
        hoechst_pnl_pct = float(hoechst_pnl_pct)
    except Exception:
        return False
    if hoechst_pnl_pct < breakeven_ab_pct:
        return False
    return pnl_pct <= puffer_pct


def beschreibung():
    """Klartext fuer Log / Terminal-Tab."""
    stufen = ", ".join(f"ab +{s:.1f}%: x{f}" for s, f in LEITER)
    return (f"Ratsche am Hoechststand | Breakeven ab +{BREAKEVEN_AB_PCT}% "
            f"(Puffer +{BREAKEVEN_PUFFER_PCT}%) | Trail: {stufen} | "
            f"TRENDING_UP x{TREND_BONUS}")
