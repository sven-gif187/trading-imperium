# -*- coding: utf-8 -*-
"""Trading Imperium V6 - Chartanalyse (NUR LESEN UND MESSEN).

WAS DAS IST
-----------
Klassische Chartanalyse, mechanisch ausgerechnet: Unterstuetzungs- und
Widerstandszonen, Ausbrueche, Retests, Trendkanaele, gleitende Durchschnitte
als dynamische Zonen, Fibonacci-Ziele und die gaengigen Formationen
(Doppel-Tief/-Hoch, Schulter-Kopf-Schulter, Dreieck).

WAS DAS NICHT IST - nicht verhandelbar
--------------------------------------
Dieses Modul loest KEINEN Handel aus. Es wird von keinem Kaufpfad importiert.
Es rechnet, zeigt an und schreibt in die Datenbank, damit ueber Wochen messbar
wird, ob die Analyse ueberhaupt trifft. Erst wenn die Trefferquote das belegt,
wird ueber einen Einbau als Zusatzfilter gesprochen - und dann als eigene,
bewusste Entscheidung.

KAUSALITAET - der wichtigste Punkt an dieser Datei
--------------------------------------------------
Ein Swing-Hoch ist erst dann als Swing-Hoch erkennbar, wenn danach genug
Kerzen gelaufen sind. Wer eine Zone aus einem Hoch bildet und dann so tut,
als haette man sie schon beim Hoch selbst gekannt, misst die Zukunft mit -
der Backtest sieht dann grossartig aus und die Regel verliert im Echtbetrieb.

Genau dieser Fehler ist in diesem Projekt bereits dokumentiert:
02_EXPERIMENT-REGISTER_v2.0.md, Nachtrag N1 vom 04.08.2026 - 45 Minuten
Look-ahead in messung_f2_ic.py, groesster Verzerrungsbetrag 4,77 Prozentpunkte.
Deshalb traegt hier JEDE Zone und JEDE Formation einen bestaetigt_ab-Index.
Vor diesem Index existiert sie fuer jede Auswertung schlicht nicht.

Reine Standardbibliothek plus pandas/numpy (beides ist bereits Abhaengigkeit).
"""
import math
from dataclasses import dataclass, field, asdict
from typing import List, Optional

try:
    import numpy as np
    import pandas as pd
except Exception:                                # pragma: no cover
    np = None
    pd = None


# ============================================================
# Datenmodell
# ============================================================
@dataclass
class Zone:
    """Eine horizontale Preiszone (Unterstuetzung oder Widerstand)."""
    art: str                    # SUPPORT | RESISTANCE
    preis: float                # Mittelpunkt der Zone
    von: float                  # untere Kante
    bis: float                  # obere Kante
    treffer: int                # wie oft der Kurs hier reagiert hat
    staerke: float              # 0..1, aus Treffern und Alter
    bestaetigt_ab: int          # Kerzen-Index, ab dem die Zone bekannt war
    quelle: str = "SWING"       # SWING | EMA | FIBO

    def enthaelt(self, preis: float) -> bool:
        return self.von <= preis <= self.bis


@dataclass
class Formation:
    """Eine erkannte Chartformation."""
    name: str                   # DOPPEL_TIEF | DOPPEL_HOCH | SKS | DREIECK
    richtung: str               # BULLISH | BEARISH
    kursziel: Optional[float]
    bestaetigt_ab: int
    guete: float                # 0..1
    detail: str = ""


@dataclass
class Analyse:
    """Gesamtbild zu einem Zeitpunkt."""
    symbol: str
    timeframe: str
    preis: float
    kerzen_index: int
    zonen: List[Zone] = field(default_factory=list)
    formationen: List[Formation] = field(default_factory=list)
    trend: str = "NEUTRAL"              # AUFWAERTS | ABWAERTS | SEITWAERTS
    trend_staerke: float = 0.0
    naechster_support: Optional[float] = None
    naechster_widerstand: Optional[float] = None
    einstieg_signal: str = "KEIN"       # KEIN | SUPPORT_BOUNCE | BREAKOUT | RETEST
    einstieg_guete: float = 0.0
    vorschlag_stop: Optional[float] = None
    vorschlag_ziel: Optional[float] = None
    rr_verhaeltnis: Optional[float] = None
    begruendung: str = ""
    atr: float = 0.0
    # [27.08.2026] Fibonacci nach Marks Verfahren. Leeres dict, wenn keine
    # bestaetigte Bewegung vorliegt - siehe fibonacci_ziele().
    fibonacci: dict = field(default_factory=dict)

    def als_dict(self):
        d = asdict(self)
        d["zonen"] = [asdict(z) for z in self.zonen]
        d["formationen"] = [asdict(f) for f in self.formationen]
        return d


# ============================================================
# Grundbausteine
# ============================================================
def atr(df, periode: int = 14) -> float:
    """Average True Range - die typische Schwankungsbreite je Kerze.

    Wird als Massstab fuer Zonenbreite und Stop-Abstand verwendet. Feste
    Prozentwerte waeren falsch: 1 % ist bei BTC etwas voellig anderes als
    bei einem ruhigen Seitwaertsmarkt.
    """
    if df is None or len(df) < periode + 1:
        return 0.0
    hoch, tief, schluss = df["High"], df["Low"], df["Close"]
    vorher = schluss.shift(1)
    tr = pd.concat([hoch - tief, (hoch - vorher).abs(), (tief - vorher).abs()],
                   axis=1).max(axis=1)
    wert = tr.rolling(periode).mean().iloc[-1]
    return float(wert) if not math.isnan(wert) else 0.0


def swing_punkte(df, weite: int = 3):
    """Findet bestaetigte Swing-Hochs und -Tiefs (Fraktale).

    Ein Swing-Hoch bei Index i liegt vor, wenn das Hoch dort hoeher ist als
    in den `weite` Kerzen davor UND danach.

    KAUSALITAET: Der Punkt ist erst bei Index i+weite bekannt, weil erst dann
    die bestaetigenden Kerzen gelaufen sind. Genau das gibt bestaetigt_ab an.
    Wer i verwendet, blickt in die Zukunft.

    Rueckgabe: (hochs, tiefs), je Liste von (index, preis, bestaetigt_ab)
    """
    hochs, tiefs = [], []
    if df is None or len(df) < 2 * weite + 1:
        return hochs, tiefs
    h = df["High"].values
    t = df["Low"].values
    for i in range(weite, len(df) - weite):
        fenster_h = h[i - weite:i + weite + 1]
        fenster_t = t[i - weite:i + weite + 1]
        if h[i] == fenster_h.max() and (fenster_h == h[i]).sum() == 1:
            hochs.append((i, float(h[i]), i + weite))
        if t[i] == fenster_t.min() and (fenster_t == t[i]).sum() == 1:
            tiefs.append((i, float(t[i]), i + weite))
    return hochs, tiefs


def zonen_bilden(punkte, art: str, toleranz: float, jetzt_index: int,
                 min_treffer: int = 2) -> List[Zone]:
    """Fasst nah beieinanderliegende Swing-Punkte zu einer Zone zusammen.

    Ein einzelnes Hoch ist noch kein Widerstand. Erst wenn der Kurs mehrfach
    im selben Bereich gedreht hat, ist es eine Zone - deshalb min_treffer.

    `toleranz` kommt aus dem ATR, nicht aus einem festen Prozentwert.
    """
    zonen: List[Zone] = []
    if not punkte or toleranz <= 0:
        return zonen

    # Nur Punkte, die zum Betrachtungszeitpunkt bereits bestaetigt waren.
    sichtbar = [p for p in punkte if p[2] <= jetzt_index]
    if not sichtbar:
        return zonen

    for _, preis, best_ab in sorted(sichtbar, key=lambda p: p[1]):
        for z in zonen:
            if abs(z.preis - preis) <= toleranz:
                # Zone erweitern; sie gilt ab dem SPAETESTEN Treffer, weil
                # sie vorher noch nicht die volle Staerke hatte.
                gesamt = z.treffer + 1
                z.preis = (z.preis * z.treffer + preis) / gesamt
                z.treffer = gesamt
                z.von = min(z.von, preis - toleranz / 2)
                z.bis = max(z.bis, preis + toleranz / 2)
                z.bestaetigt_ab = max(z.bestaetigt_ab, best_ab)
                break
        else:
            zonen.append(Zone(art=art, preis=preis,
                              von=preis - toleranz / 2, bis=preis + toleranz / 2,
                              treffer=1, staerke=0.0, bestaetigt_ab=best_ab))

    fertig = [z for z in zonen if z.treffer >= min_treffer]
    for z in fertig:
        # Staerke: mehr Treffer = staerker, gedeckelt bei 5 Beruehrungen.
        z.staerke = round(min(z.treffer / 5.0, 1.0), 3)
    return fertig


def ema_zonen(df, jetzt_index: int, perioden=(50, 200)) -> List[Zone]:
    """Gleitende Durchschnitte als dynamische Unterstuetzung/Widerstand."""
    zonen = []
    if df is None or len(df) < 20:
        return zonen
    preis = float(df["Close"].iloc[-1])
    spanne = atr(df) * 0.5 or preis * 0.002
    for p in perioden:
        if len(df) < p:
            continue
        wert = float(df["Close"].ewm(span=p, adjust=False).mean().iloc[-1])
        if math.isnan(wert):
            continue
        zonen.append(Zone(
            art="SUPPORT" if preis > wert else "RESISTANCE",
            preis=wert, von=wert - spanne, bis=wert + spanne,
            treffer=1, staerke=0.6 if p == 200 else 0.4,
            bestaetigt_ab=jetzt_index, quelle=f"EMA{p}"))
    return zonen


# Marks Stufensatz, aus zwei seiner Charts abgelesen und nachgerechnet
# (prognosen/MARK.md, 27.08.2026):
#
#   30-Minuten-Chart 19.08.  0 / 0,236 / 0,382 / 0,5 / 0,618 / 0,707 /
#                            0,786 / 0,866 / 1     - alle acht auf 0,3 $ genau
#   Chart vom Mai            0 / 0,236 / 0,382 / 0,5 / 0,618 / 0,786 /
#                            1 / 1,618             - alle acht auf 0,5 $ genau
#
# 0,707 und 0,866 sind KEINE Fibonacci-Zahlen, sondern Wurzelverhaeltnisse
# (Wurzel aus 0,5 und aus 0,75). Genau die zwei fehlten im Suchnetz vom
# 27.08. - deshalb fand die Ruecktechnik nichts (Befund 83).
#
# Seine Konvention in BEIDEN Charts: 0 liegt am HOCH, 1 am TIEF, jede Stufe
# ist Hoch minus Spanne mal Verhaeltnis. Das gilt unabhaengig davon, ob das
# Hoch oder das Tief zuerst kam - deshalb reicht EINE Formel.
FIB_RUECK = [0.0, 0.236, 0.382, 0.5, 0.618, 0.707, 0.786, 0.866, 1.0]
FIB_VOR = [1.272, 1.618, 2.0, 2.618]


def fibonacci_ziele(df, hochs, tiefs, jetzt_index: int, mit_vor: bool = True,
                    rueckblick: int = 0):
    """Fibonacci-Stufen der letzten klaren Bewegung, nach Marks Verfahren.

    KAUSALITAET: Es werden nur Wendepunkte benutzt, die zum Zeitpunkt
    `jetzt_index` bereits BESTAETIGT waren (siehe swing_punkte). Ein Hoch,
    das erst drei Kerzen spaeter erkennbar wurde, darf hier nicht auftauchen -
    sonst zeigt der Chart eine Linie, die es damals nicht gab.

    Rueckgabe: dict mit hoch, tief, spanne, richtung, bestaetigt_ab und
    stufen = Liste von (verhaeltnis, preis, art). art ist "anker" fuer 0
    und 1, "rueck" fuer die Stufen dazwischen, "vor" fuer die
    Verlaengerungen darunter. Leeres dict, wenn keine Bewegung vorliegt.

    rueckblick: Nur Wendepunkte aus den letzten so vielen Kerzen kommen
    als Anker in Frage. 0 heisst: alle. Der Aufrufer setzt hier die
    Zahl der Kerzen ein, die er ANZEIGT - sonst zeigt der Chart Stufen
    einer Bewegung, die gar nicht im Bild ist (siehe Ankerwahl unten).
    """
    ab = (jetzt_index - rueckblick + 1) if rueckblick and rueckblick > 0 else -1
    sicht_h = [p for p in hochs if ab <= p[2] <= jetzt_index]
    sicht_t = [p for p in tiefs if ab <= p[2] <= jetzt_index]
    if not sicht_h or not sicht_t:
        return {}

    # ANKERWAHL - hier steckt die eigentliche Entscheidung.
    #
    # Erster Versuch nahm das JUENGSTE Hoch und das JUENGSTE Tief. An
    # echten Daten getestet ergab das am 27.08. eine Spanne von 682 $ auf
    # 80.500 - also 0,85 %. Alle dreizehn Stufen lagen dann innerhalb
    # eines knappen Prozents untereinander und waren im Chart eine einzige
    # Linie. Unbrauchbar.
    #
    # Mark macht es anders. In seinem 30-Minuten-Chart vom 19.08. lagen
    # die Anker bei 64.545 (19.08. 11:00) und 62.671 (17.08. 00:30) - das
    # sind das HOECHSTE und das TIEFSTE des sichtbaren Fensters, rund
    # 59 Kerzen auseinander. Nicht die juengsten Wendepunkte, sondern die
    # aeussersten.
    #
    # Deshalb: die Extreme unter den bestaetigten Wendepunkten. Das ist
    # das, was ein Mensch beim Aufziehen des Werkzeugs auch tut.
    #
    # [Nachtrag 27.08.2026] Und zwar die Extreme des SICHTBAREN Fensters.
    # Ohne `rueckblick` wurden sie ueber alle 300 geladenen Kerzen
    # gesucht, waehrend der Chart nur 150 zeigt. Gemessen am 27.08. auf
    # Stundenkerzen: Ankertief 62.716, sichtbarer Bereich aber erst ab
    # 75.190 - elf der dreizehn Stufen lagen unterhalb des Bildrands,
    # gezeichnet wurden zwei. Marks 59 Kerzen zwischen seinen Ankern
    # zeigen, dass er ebenfalls im Sichtbaren bleibt.
    hoechstes = max(sicht_h, key=lambda p: p[1])
    tiefstes = min(sicht_t, key=lambda p: p[1])
    hoch, tief = hoechstes[1], tiefstes[1]
    if hoch <= tief:
        return {}
    spanne = hoch - tief
    letztes_hoch, letztes_tief = hoechstes, tiefstes

    # RICHTUNG - die zweite Entscheidung, und bis zum 28.08. eine falsche.
    #
    # Die Null liegt IMMER am Ende der Bewegung, die Eins an ihrem Anfang.
    # Welcher der beiden Anker das Ende ist, entscheidet die ZEIT:
    #
    #   Hoch zuletzt  (Aufwaertsbewegung)  ->  0 am Hoch,  Stufen nach unten
    #   Tief zuletzt  (Abwaertsbewegung)   ->  0 am Tief,  Stufen nach oben
    #
    # Vorher stand hier fest `hoch - spanne * r`, also immer die erste
    # Variante. Das stimmte fuer Marks August-Charts und war fuer seine
    # Charts vom 30.04. genau verkehrt herum. Nachgerechnet gegen vier
    # seiner Fibonacci-Raster von diesem Tag - dort liegt die 0 am Tief:
    #
    #   Tief 74.904,22  Hoch 77.925,02   0,236 = 75.617,13   Abweichung 0,00 $
    #   Tief 75.324,64  Hoch 76.430,19   1,618 = 77.113,42   Abweichung 0,00 $
    #   Tief 74.841,93  Hoch 77.909,45   0,618 = 76.737,66   Abweichung 0,00 $
    #   Tief 75.835,87  Hoch 76.314,59   0,786 = 76.212,14   Abweichung 0,00 $
    #
    # Groesste Abweichung ueber alle vier Raster: 0,01 $. Damit ist nicht
    # nur die Formel bestaetigt, sondern auch, dass die Richtung mitlaeuft.
    auf = letztes_tief[0] < letztes_hoch[0]      # Hoch kam spaeter -> Aufwaerts

    def _preis(r):
        return (hoch - spanne * r) if auf else (tief + spanne * r)

    stufen = []
    for r in FIB_RUECK:
        stufen.append((r, _preis(r), "anker" if r in (0.0, 1.0) else "rueck"))
    if mit_vor:
        for r in FIB_VOR:
            # Verlaengerung ueber den AELTEREN Anker hinaus: bei einer
            # Aufwaertsbewegung nach unten (Marks 1,618 = 62.259 im
            # Mai-Chart), bei einer Abwaertsbewegung nach oben
            # (Marks 1,618 = 77.113,42 am 30.04.).
            stufen.append((r, _preis(r), "vor"))

    return {
        "hoch": hoch,
        "tief": tief,
        "spanne": spanne,
        "richtung": "AUF" if auf else "AB",
        "bestaetigt_ab": max(letztes_hoch[2], letztes_tief[2]),
        "stufen": stufen,
    }


def formationen_finden(df, hochs, tiefs, jetzt_index: int,
                       toleranz: float) -> List[Formation]:
    """Erkennt Doppel-Tief/-Hoch, Schulter-Kopf-Schulter und Dreieck."""
    gefunden: List[Formation] = []
    sicht_h = [p for p in hochs if p[2] <= jetzt_index]
    sicht_t = [p for p in tiefs if p[2] <= jetzt_index]
    if toleranz <= 0:
        return gefunden

    # --- Doppel-Tief: zwei Tiefs auf gleicher Hoehe, dazwischen ein Hoch ---
    if len(sicht_t) >= 2:
        a, b = sicht_t[-2], sicht_t[-1]
        if abs(a[1] - b[1]) <= toleranz and b[0] - a[0] >= 4:
            zwischen = [h for h in sicht_h if a[0] < h[0] < b[0]]
            if zwischen:
                nacken = max(zwischen, key=lambda p: p[1])[1]
                hoehe = nacken - (a[1] + b[1]) / 2
                gefunden.append(Formation(
                    name="DOPPEL_TIEF", richtung="BULLISH",
                    kursziel=round(nacken + hoehe, 4),
                    bestaetigt_ab=max(a[2], b[2]),
                    guete=round(max(0.0, 1.0 - abs(a[1] - b[1]) / toleranz), 3),
                    detail=f"Tiefs {a[1]:.2f}/{b[1]:.2f}, Nackenlinie {nacken:.2f}"))

    # --- Doppel-Hoch ---
    if len(sicht_h) >= 2:
        a, b = sicht_h[-2], sicht_h[-1]
        if abs(a[1] - b[1]) <= toleranz and b[0] - a[0] >= 4:
            zwischen = [t for t in sicht_t if a[0] < t[0] < b[0]]
            if zwischen:
                nacken = min(zwischen, key=lambda p: p[1])[1]
                hoehe = (a[1] + b[1]) / 2 - nacken
                gefunden.append(Formation(
                    name="DOPPEL_HOCH", richtung="BEARISH",
                    kursziel=round(nacken - hoehe, 4),
                    bestaetigt_ab=max(a[2], b[2]),
                    guete=round(max(0.0, 1.0 - abs(a[1] - b[1]) / toleranz), 3),
                    detail=f"Hochs {a[1]:.2f}/{b[1]:.2f}, Nackenlinie {nacken:.2f}"))

    # --- Schulter-Kopf-Schulter: Kopf hoeher, Schultern aehnlich ---
    if len(sicht_h) >= 3:
        s1, kopf, s2 = sicht_h[-3], sicht_h[-2], sicht_h[-1]
        if (kopf[1] > s1[1] and kopf[1] > s2[1]
                and abs(s1[1] - s2[1]) <= toleranz * 1.5):
            taeler = [t for t in sicht_t if s1[0] < t[0] < s2[0]]
            if len(taeler) >= 2:
                nacken = sum(t[1] for t in taeler) / len(taeler)
                gefunden.append(Formation(
                    name="SKS", richtung="BEARISH",
                    kursziel=round(nacken - (kopf[1] - nacken), 4),
                    bestaetigt_ab=max(s1[2], kopf[2], s2[2]),
                    guete=round(max(0.0, 1.0 - abs(s1[1] - s2[1]) / (toleranz * 1.5)), 3),
                    detail=f"Kopf {kopf[1]:.2f}, Schultern {s1[1]:.2f}/{s2[1]:.2f}"))

    # --- Dreieck: Hochs fallen, Tiefs steigen (Kontraktion) ---
    if len(sicht_h) >= 2 and len(sicht_t) >= 2:
        h1, h2 = sicht_h[-2], sicht_h[-1]
        t1, t2 = sicht_t[-2], sicht_t[-1]
        if h2[1] < h1[1] and t2[1] > t1[1]:
            enge = (h2[1] - t2[1]) / (h1[1] - t1[1]) if h1[1] > t1[1] else 1.0
            if enge < 0.8:
                gefunden.append(Formation(
                    name="DREIECK", richtung="NEUTRAL",
                    kursziel=None,
                    bestaetigt_ab=max(h2[2], t2[2]),
                    guete=round(min(1.0, 1.0 - enge), 3),
                    detail=f"Spanne auf {enge*100:.0f}% zusammengelaufen - "
                           f"Ausbruch steht an"))
    return gefunden


def trend_bestimmen(df, hochs, tiefs, jetzt_index: int):
    """Trend aus der Struktur: hoehere Hochs und hoehere Tiefs = Aufwaerts."""
    sicht_h = [p for p in hochs if p[2] <= jetzt_index][-3:]
    sicht_t = [p for p in tiefs if p[2] <= jetzt_index][-3:]
    if len(sicht_h) < 2 or len(sicht_t) < 2:
        return "NEUTRAL", 0.0
    hh = sicht_h[-1][1] > sicht_h[-2][1]
    ht = sicht_t[-1][1] > sicht_t[-2][1]
    if hh and ht:
        return "AUFWAERTS", 1.0
    if not hh and not ht:
        return "ABWAERTS", 1.0
    return "SEITWAERTS", 0.5


# ============================================================
# Gesamtanalyse
# ============================================================
def analysiere(df, symbol: str, timeframe: str, swing_weite: int = 3,
               zonen_toleranz_atr: float = 0.6,
               fib_rueckblick: int = 0) -> Optional[Analyse]:
    """Rechnet das vollstaendige Chartbild zum LETZTEN Balken von df.

    Fuer einen Backtest wird df einfach gekuerzt uebergeben - dann kennt die
    Funktion nichts, was danach passiert ist. Das ist die einzige ehrliche
    Art, so etwas rueckwirkend zu pruefen.
    """
    if pd is None or df is None or len(df) < 30:
        return None

    jetzt = len(df) - 1
    preis = float(df["Close"].iloc[-1])
    a = atr(df)
    if a <= 0:
        a = preis * 0.005
    toleranz = a * zonen_toleranz_atr

    hochs, tiefs = swing_punkte(df, swing_weite)
    zonen = (zonen_bilden(tiefs, "SUPPORT", toleranz, jetzt)
             + zonen_bilden(hochs, "RESISTANCE", toleranz, jetzt)
             + ema_zonen(df, jetzt))
    formationen = formationen_finden(df, hochs, tiefs, jetzt, toleranz)
    trend, staerke = trend_bestimmen(df, hochs, tiefs, jetzt)

    unter = [z for z in zonen if z.preis < preis]
    ueber = [z for z in zonen if z.preis > preis]
    naechster_sup = max((z.preis for z in unter), default=None)
    naechster_res = min((z.preis for z in ueber), default=None)

    erg = Analyse(symbol=symbol, timeframe=timeframe, preis=preis,
                  kerzen_index=jetzt, zonen=zonen, formationen=formationen,
                  trend=trend, trend_staerke=staerke,
                  naechster_support=naechster_sup,
                  naechster_widerstand=naechster_res, atr=round(a, 6),
                  fibonacci=fibonacci_ziele(df, hochs, tiefs, jetzt,
                                            rueckblick=fib_rueckblick))

    _einstieg_bewerten(erg, df, toleranz, a)
    return erg


def _einstieg_bewerten(erg: Analyse, df, toleranz: float, a: float):
    """Leitet aus dem Chartbild ein Einstiegssignal mit Stop und Ziel ab."""
    preis = erg.preis
    gruende = []

    sup_zonen = [z for z in erg.zonen if z.art == "SUPPORT" and z.quelle == "SWING"]
    res_zonen = [z for z in erg.zonen if z.art == "RESISTANCE" and z.quelle == "SWING"]

    # 1) Abpraller an einer Unterstuetzung
    beruehrt = [z for z in sup_zonen if z.enthaelt(preis)]
    if beruehrt:
        z = max(beruehrt, key=lambda x: x.staerke)
        erg.einstieg_signal = "SUPPORT_BOUNCE"
        erg.einstieg_guete = round(0.4 + 0.6 * z.staerke, 3)
        erg.vorschlag_stop = round(z.von - a * 0.5, 6)
        gruende.append(f"Kurs in Unterstuetzung {z.preis:.2f} "
                       f"({z.treffer} Beruehrungen)")

    # 2) Ausbruch ueber einen Widerstand
    if len(df) >= 3 and not beruehrt:
        vorher = float(df["Close"].iloc[-2])
        gebrochen = [z for z in res_zonen if vorher <= z.bis < preis]
        if gebrochen:
            z = max(gebrochen, key=lambda x: x.staerke)
            erg.einstieg_signal = "BREAKOUT"
            erg.einstieg_guete = round(0.35 + 0.55 * z.staerke, 3)
            erg.vorschlag_stop = round(z.von - a * 0.5, 6)
            gruende.append(f"Ausbruch ueber Widerstand {z.preis:.2f}")

    # 3) Retest: gebrochener Widerstand wird von oben getestet
    if erg.einstieg_signal == "KEIN" and len(df) >= 6:
        hoch_zuletzt = float(df["High"].iloc[-6:-1].max())
        fuer_retest = [z for z in res_zonen
                       if z.preis < hoch_zuletzt and z.enthaelt(preis)]
        if fuer_retest:
            z = max(fuer_retest, key=lambda x: x.staerke)
            erg.einstieg_signal = "RETEST"
            erg.einstieg_guete = round(0.5 + 0.5 * z.staerke, 3)
            erg.vorschlag_stop = round(z.von - a * 0.5, 6)
            gruende.append(f"Retest der gebrochenen Linie {z.preis:.2f}")

    # Trend als Verstaerker oder Daempfer
    if erg.einstieg_signal != "KEIN":
        if erg.trend == "AUFWAERTS":
            erg.einstieg_guete = round(min(1.0, erg.einstieg_guete * 1.2), 3)
            gruende.append("Trendstruktur aufwaerts")
        elif erg.trend == "ABWAERTS":
            erg.einstieg_guete = round(erg.einstieg_guete * 0.6, 3)
            gruende.append("Gegen den Abwaertstrend - abgewertet")

        bullisch = [f for f in erg.formationen if f.richtung == "BULLISH"]
        if bullisch:
            erg.einstieg_guete = round(min(1.0, erg.einstieg_guete * 1.15), 3)
            gruende.append(f"Formation {bullisch[0].name}")

        # Ziel: naechster Widerstand, sonst Formationsziel
        ziel = erg.naechster_widerstand
        if ziel is None and bullisch and bullisch[0].kursziel:
            ziel = bullisch[0].kursziel
        erg.vorschlag_ziel = round(ziel, 6) if ziel else None

        if erg.vorschlag_stop and erg.vorschlag_ziel:
            risiko = preis - erg.vorschlag_stop
            chance = erg.vorschlag_ziel - preis
            if risiko > 0 and chance > 0:
                erg.rr_verhaeltnis = round(chance / risiko, 3)

    erg.begruendung = " + ".join(gruende) if gruende else "kein Setup erkennbar"
