# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Strategie-Labor Stufen 2-4: Messlatten M1-M3, Kandidaten K1-K3, Rueckrechnung (Simulator).

GRUNDREGELN (labor/STRATEGIE_LABOR.md 3):
  - Signal am Tagesschluss t, Ausfuehrung zum Eroeffnungskurs t+1 (kein Blick in die Zukunft).
  - Kosten je Runde K -> je Seite K/2 auf jeden gehandelten Betrag. Niveaus 0,15/0,20/0,50/1,00 %.
  - Kein Hebel: Summe der Zielgewichte <= 1; Kaeufe werden gekuerzt, wenn das Geld nicht reicht.
  - Startkapital 500 $ (wie der Bot), damit die Mindestorder 10 $ eine Bedeutung hat.
  - Feste Parameter aus der Forschung bzw. Svens Vorgabe, keine Optimierung.

KOSTENBREMSE K1-K3 (Svens Vorgabe, Lesart offen benannt): Eroeffnen und Schliessen immer;
dazwischen nur umschichten, wenn sich die Zielgroesse um mehr als 25 % aendert UND die Order
mindestens 10 $ gross ist. Woertlich steht "oder" - dann bremst die Regel bei 500 $ Kapital fast
nie (fast jede Order ist >= 10 $). Die Variante "oder" laeuft in Stufe 5 als Robustheitstest.

KONTROLLE auf zwei Wegen: Endvermoegen aus dem Konto == Startkapital + Summe aller Runden-
ergebnisse (geschlossen) + Wert offener Runden. Jede Runde fuehrt ihren Geldfluss inkl. Kosten.
"""
from __future__ import annotations

import csv
import math
import statistics as st
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
DATEN = HIER / "daten"
COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE", "NEAR", "UNI", "ATOM"]
START_KAPITAL = 500.0
MIN_ORDER = 10.0


# ------------------------------------------------------------------ Daten
@dataclass
class Markt:
    datum: list[str]
    o: dict[str, list]       # je Coin Liste ueber alle Tage, None = noch nicht gelistet
    c: dict[str, list]

    @classmethod
    def laden(cls) -> "Markt":
        roh = {}
        for coin in COINS:
            with (DATEN / f"{coin}_1d.csv").open(encoding="utf-8") as f:
                roh[coin] = {r["datum"]: (float(r["open"]), float(r["close"])) for r in csv.DictReader(f)}
        tage = sorted(roh["BTC"])
        o = {k: [roh[k].get(d, (None, None))[0] for d in tage] for k in COINS}
        c = {k: [roh[k].get(d, (None, None))[1] for d in tage] for k in COINS}
        return cls(tage, o, c)

    def idx(self, datum: str) -> int:
        return next(i for i, d in enumerate(self.datum) if d >= datum)

    def verfuegbar(self, coin: str, i: int, mindest: int = 1) -> bool:
        """Coin hat an Tag i und den mindest-1 Tagen davor einen Schlusskurs."""
        return i - mindest + 1 >= 0 and all(self.c[coin][j] is not None for j in range(i - mindest + 1, i + 1))

    def sma(self, coin: str, i: int, n: int) -> float | None:
        if not self.verfuegbar(coin, i, n):
            return None
        return sum(self.c[coin][i - n + 1:i + 1]) / n


# ------------------------------------------------------------------ Strategien
class Strategie:
    name = "?"
    bremse = False

    def ziel(self, m: Markt, i: int) -> dict | None:
        """Zielgewichte nach Schluss von Tag i, oder None = nichts tun."""
        raise NotImplementedError


class M1BTCHalten(Strategie):
    name = "M1 BTC halten"

    def __init__(self):
        self.fertig = False

    def ziel(self, m, i):
        if self.fertig:
            return None
        self.fertig = True
        return {"BTC": 1.0}


class M2Korb(Strategie):
    name = "M2 Korb 12 gleich, monatlich"

    def ziel(self, m, i):
        if i + 1 < len(m.datum) and m.datum[i + 1][:7] == m.datum[i][:7] and getattr(self, "_start", False):
            return None                          # nur am Monatsende (Ausfuehrung am 1. des Folgemonats)
        self._start = True
        da = [k for k in COINS if m.verfuegbar(k, i)]
        return {k: 1.0 / len(da) for k in da}


class M3BTC200(Strategie):
    name = "M3 BTC ueber 200-Tage-Linie"

    def ziel(self, m, i):
        s = m.sma("BTC", i, 200)
        return {"BTC": 1.0 if (s and m.c["BTC"][i] > s) else 0.0}


def btc_ueber_200(m: Markt, i: int) -> bool:
    s = m.sma("BTC", i, 200)
    return bool(s and m.c["BTC"][i] > s)


class K1Trend(Strategie):
    """Trend-Ensemble nach Zarattini/Pagani/Barbon (2025), Regeln laut Sven (STRATEGIE_LABOR.md K1)."""
    name = "K1 Trend-Ensemble"
    bremse = True
    LOOKBACKS = (5, 10, 20, 30, 60, 90, 150, 250, 360)

    def __init__(self, ziel_vol=0.25, filter_btc200=False, name=None, lookbacks=None):
        self.ziel_vol = ziel_vol
        self.filter = filter_btc200
        self.lb = lookbacks or self.LOOKBACKS
        self.stopp = {(k, L): None for k in COINS for L in self.lb}   # None = nicht investiert
        if name:
            self.name = name

    def _vol(self, m, k, i, n=90):
        if not m.verfuegbar(k, i, n + 1):
            return None
        r = [math.log(m.c[k][j] / m.c[k][j - 1]) for j in range(i - n + 1, i + 1)]
        return st.stdev(r) * math.sqrt(365)

    def ziel(self, m, i):
        neu_erlaubt = (not self.filter) or btc_ueber_200(m, i)
        gew = {}
        da = [k for k in COINS if m.verfuegbar(k, i, 91)]
        for k in COINS:
            aktiv = 0
            for L in self.lb:
                key = (k, L)
                if not m.verfuegbar(k, i, L + 1):
                    self.stopp[key] = None
                    continue
                fenster = m.c[k][i - L + 1:i + 1]                 # letzte L Schluesse inkl. heute
                vorher = m.c[k][i - L:i]                          # die L Schluesse vor heute
                mitte = (max(fenster) + min(fenster)) / 2
                s = self.stopp[key]
                if s is None:
                    if neu_erlaubt and m.c[k][i] > max(vorher):
                        self.stopp[key] = mitte
                        aktiv += 1
                else:
                    if m.c[k][i] < s:                              # Schluss unter dem Vortages-Stopp
                        self.stopp[key] = None
                    else:
                        self.stopp[key] = max(s, mitte)
                        aktiv += 1
            if aktiv and k in da:
                v = self._vol(m, k, i)
                if v:
                    # [14.10.] Svens Vorgabe woertlich: Position auf 25 % Jahresschwankung
                    # (Anteil = Ziel / Schwankung), gleich ueber die L verteilt, GEDECKELT auf das
                    # Coin-Budget. Erste Fassung multiplizierte mit 1/N statt zu deckeln (doppelt geschrumpft).
                    gew[k] = min(1.0 / len(da), (aktiv / len(self.lb)) * self.ziel_vol / v)
        return gew


class K3Rotation(Strategie):
    """Querschnitts-Momentum: woechentlich, beste 3 halten, raus erst ausserhalb der besten 6, nur ueber BTC-200."""
    name = "K3 Rotation Top 3 / Halteband 6"
    bremse = True

    def __init__(self, top=3, band=6, name=None, filter_btc200=True):
        self.top, self.band, self.filter = top, band, filter_btc200
        self.halte: list[str] = []
        if name:
            self.name = name

    def ziel(self, m, i):
        if date.fromisoformat(m.datum[i]).weekday() != 6:
            return None                                              # Sonntagsschluss -> Montag ausfuehren
        if self.filter and not btc_ueber_200(m, i):
            self.halte = []
            return {}
        punkte = {}
        for k in COINS:
            if m.verfuegbar(k, i, 57):
                c = m.c[k]
                punkte[k] = sum(c[i] / c[i - n] - 1 for n in (7, 14, 28, 56)) / 4
        rang = sorted(punkte, key=punkte.get, reverse=True)
        self.halte = [h for h in self.halte if h in rang[:self.band]]
        for k in rang:
            if len(self.halte) >= self.top:
                break
            if k not in self.halte and k in rang[:self.top]:
                self.halte.append(k)
        return {k: 1.0 / self.top for k in self.halte}


# ------------------------------------------------------------------ Simulator
@dataclass
class Runde:
    coin: str
    start: str
    ende: str | None = None
    fluss: float = 0.0          # Geldfluss inkl. Kosten (- Kauf, + Verkauf)
    kosten: float = 0.0
    tage: int = 0


@dataclass
class Ergebnis:
    name: str
    k_runde: float
    datum: list[str] = field(default_factory=list)
    equity: list[float] = field(default_factory=list)
    exposure: list[float] = field(default_factory=list)
    runden: list[Runde] = field(default_factory=list)
    kosten: float = 0.0
    kontrolle: float = 0.0       # Abweichung der Zwei-Wege-Kontrolle in $


def ziele_berechnen(strat: Strategie, m: Markt, start: str, ende: str | None = None) -> dict[int, dict]:
    """Signale einmal rechnen (sie haengen nicht von Kosten oder Ausfuehrung ab)."""
    i0 = m.idx(start)
    i1 = len(m.datum) - 1 if ende is None else m.idx(ende)
    out = {}
    for i in range(i0, i1):
        z = strat.ziel(m, i)
        if z is not None:
            out[i] = z
    return out


def simuliere(strat: Strategie, m: Markt, k_runde_pct: float, start: str, ende: str | None = None,
              verzoegerung: int = 0, bremse_oder: bool = False, ohne: tuple = (),
              ziele: dict[int, dict] | None = None, kosten_je_coin: dict | None = None,
              journal: list | None = None) -> Ergebnis:
    """kosten_je_coin: {coin: Kosten je Seite als Anteil} statt k_runde_pct/2 (Papier-Wettkampf, Bitvavo).
    journal: Liste, in die jede Order als dict geschrieben wird (datum, coin, seite, betrag, preis, kosten)."""
    cs_flach = k_runde_pct / 100 / 2

    def cs_von(k):
        return kosten_je_coin.get(k, cs_flach) if kosten_je_coin else cs_flach
    i0 = m.idx(start)
    i1 = len(m.datum) - 1 if ende is None else m.idx(ende)
    cash, qty = START_KAPITAL, {k: 0.0 for k in COINS}
    offen: dict[str, Runde] = {}
    erg = Ergebnis(strat.name, k_runde_pct)
    warte: list[tuple[int, dict]] = []
    for i in range(i0, i1):
        z = ziele.get(i) if ziele is not None else strat.ziel(m, i)
        if z is not None:
            z = {k: w for k, w in z.items() if k not in ohne}
            warte.append((i + 1 + verzoegerung, z))
        auszufuehren = [w for t, w in warte if t == i + 1]
        warte = [(t, w) for t, w in warte if t > i + 1]
        j = i + 1
        if auszufuehren:
            ziel = auszufuehren[-1]
            preis = {k: m.o[k][j] for k in COINS if m.o[k][j] is not None}
            eq_open = cash + sum(qty[k] * preis[k] for k in qty if qty[k] and k in preis)
            orders = {}
            for k in set(ziel) | {k for k in qty if qty[k] > 0}:
                if k not in preis:
                    continue
                v_ist = qty[k] * preis[k]
                v_soll = max(0.0, ziel.get(k, 0.0)) * eq_open
                d = v_soll - v_ist
                if v_ist <= 1e-9 and v_soll < MIN_ORDER:
                    continue
                if v_soll <= 1e-9 and v_ist > 0:
                    orders[k] = (-v_ist, True)             # komplett schliessen
                    continue
                if v_ist <= 1e-9:
                    orders[k] = (d, False)
                    continue
                if strat.bremse:
                    gross = abs(d) > 0.25 * v_ist
                    min_ok = abs(d) >= MIN_ORDER
                    if not ((gross or min_ok) if bremse_oder else (gross and min_ok)):
                        continue
                elif abs(d) < 0.5:
                    continue
                orders[k] = (d, False)
            for k, (d, voll) in sorted(orders.items(), key=lambda x: x[1][0]):      # erst Verkaeufe
                p = preis[k]
                if d < 0:
                    menge = qty[k] if voll else min(qty[k], -d / p)
                    if qty[k] - menge < 1e-12:
                        menge = qty[k]
                    erloes = menge * p
                    kost = erloes * cs_von(k)
                    cash += erloes - kost
                    qty[k] -= menge
                    if journal is not None:
                        journal.append({"datum": m.datum[j], "coin": k, "seite": "VERKAUF", "betrag": round(erloes, 4),
                                        "preis": p, "menge": menge, "kosten": round(kost, 4), "voll": voll})
                    r = offen[k]
                    r.fluss += erloes - kost
                    r.kosten += kost
                    erg.kosten += kost
                    if qty[k] <= 1e-12:
                        qty[k] = 0.0
                        r.ende = m.datum[j]
                        erg.runden.append(r)
                        del offen[k]
                else:
                    brutto = min(d, cash / (1 + cs_von(k)))
                    if brutto < 1e-9:
                        continue
                    kost = brutto * cs_von(k)
                    cash -= brutto + kost
                    qty[k] += brutto / p
                    if journal is not None:
                        journal.append({"datum": m.datum[j], "coin": k, "seite": "KAUF", "betrag": round(brutto, 4),
                                        "preis": p, "menge": brutto / p, "kosten": round(kost, 4), "voll": False})
                    r = offen.setdefault(k, Runde(k, m.datum[j]))
                    r.fluss -= brutto + kost
                    r.kosten += kost
                    erg.kosten += kost
        # Laufender Tag (Papier-Wettkampf): noch kein Schluss -> zum Eroeffnungskurs bewerten
        wert = sum(qty[k] * (m.c[k][j] if m.c[k][j] is not None else m.o[k][j]) for k in qty if qty[k])
        eq = cash + wert
        for r in offen.values():
            r.tage += 1
        erg.datum.append(m.datum[j])
        erg.equity.append(eq)
        erg.exposure.append(wert / eq if eq > 0 else 0.0)
    # Zwei-Wege-Kontrolle
    j = i1

    def kurs(k):
        return m.c[k][j] if m.c[k][j] is not None else m.o[k][j]
    offen_wert = sum(qty[k] * kurs(k) for k in offen)
    weg2 = START_KAPITAL + sum(r.fluss for r in erg.runden) + sum(r.fluss for r in offen.values()) + offen_wert
    erg.kontrolle = (erg.equity[-1] if erg.equity else START_KAPITAL) - weg2
    erg.bestand = {k: v for k, v in qty.items() if v > 0}
    erg.cash = cash
    for k, r in offen.items():           # offene Runden zum Schlusskurs bewerten (fuer Statistik)
        r2 = Runde(r.coin, r.start, None, r.fluss + qty[k] * kurs(k), r.kosten, r.tage)
        erg.runden.append(r2)
    return erg


# ------------------------------------------------------------------ Kennzahlen
def renditen(eq: list[float], start: float = START_KAPITAL) -> list[float]:
    vorher = [start] + eq[:-1]
    return [e / v - 1 for e, v in zip(eq, vorher)]


def kennzahlen(erg: Ergebnis, von: str | None = None, bis: str | None = None, tage_filter=None) -> dict:
    idx = [n for n, d in enumerate(erg.datum) if (von is None or d >= von) and (bis is None or d <= bis)]
    if len(idx) < 2:
        return {}
    alle_r = renditen(erg.equity)
    r = [alle_r[n] for n in idx if (tage_filter is None or tage_filter(erg.datum[n]))]
    if len(r) < 2:
        return {}
    wachstum = math.prod(1 + x for x in r)
    jahre = len(r) / 365
    cagr = wachstum ** (1 / jahre) - 1 if wachstum > 0 else -1.0
    sd = st.stdev(r)
    neg = [min(0.0, x) for x in r]
    dd_sd = math.sqrt(sum(x * x for x in neg) / len(r))
    # groesster Rueckgang auf der verketteten Kurve dieses Ausschnitts
    stand, hoch, mdd = 1.0, 1.0, 0.0
    for x in r:
        stand *= 1 + x
        hoch = max(hoch, stand)
        mdd = min(mdd, stand / hoch - 1)
    sharpe = (st.mean(r) / sd * math.sqrt(365)) if sd > 0 else 0.0
    runden = [x for x in erg.runden if (von is None or x.start >= von) and (bis is None or x.start <= bis)]
    gew = [x.fluss for x in runden if x.fluss > 0]
    ver = [x.fluss for x in runden if x.fluss <= 0]
    expo = [erg.exposure[n] for n in idx]
    kosten = sum(x.kosten for x in runden)
    netto = sum(x.fluss for x in runden)
    monate = max(1e-9, len(idx) / 30.44)
    return {
        "tage": len(r), "rendite_gesamt_pct": round((wachstum - 1) * 100, 2), "rendite_jahr_pct": round(cagr * 100, 2),
        "max_rueckgang_pct": round(mdd * 100, 2), "sharpe": round(sharpe, 2),
        "sortino": round(st.mean(r) / dd_sd * math.sqrt(365), 2) if dd_sd > 0 else None,
        "calmar": round(cagr / abs(mdd), 2) if mdd < 0 else None,
        "runden_je_monat": round(len(runden) / monate, 2),
        "haltedauer_tage": round(st.mean([x.tage for x in runden]), 1) if runden else None,
        "zeit_im_markt_pct": round(100 * sum(1 for e in expo if e > 0.01) / len(expo), 1),
        "investiert_mittel_pct": round(100 * st.mean(expo), 1),
        "trefferquote_pct": round(100 * len(gew) / len(runden), 1) if runden else None,
        "gewinn_mittel_usd": round(st.mean(gew), 2) if gew else None,
        "verlust_mittel_usd": round(st.mean(ver), 2) if ver else None,
        "kostenanteil_brutto_pct": round(100 * kosten / (netto + kosten), 1) if (netto + kosten) > 0 else None,
        "kosten_usd": round(kosten, 2),
    }


def deflated_sharpe(r: list[float], sr_versuche: list[float]) -> float:
    """Bailey/Lopez de Prado (2014). r = Tagesrenditen der gewaehlten Strategie,
    sr_versuche = Sharpe (je Tag, nicht annualisiert) aller getesteten Varianten."""
    from scipy.stats import kurtosis, norm, skew
    n = len(r)
    sd = st.stdev(r)
    sr = st.mean(r) / sd
    N = max(2, len(sr_versuche))
    var_sr = st.variance(sr_versuche) if len(sr_versuche) > 1 else 0.0
    gamma = 0.5772156649
    sr0 = math.sqrt(var_sr) * ((1 - gamma) * norm.ppf(1 - 1 / N) + gamma * norm.ppf(1 - 1 / (N * math.e)))
    g3, g4 = skew(r), kurtosis(r, fisher=False)
    nenner = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr * sr))
    return float(norm.cdf((sr - sr0) * math.sqrt(n - 1) / nenner))


def marktlage(m: Markt):
    """Bulle / Baer / Seitwaerts je Tag aus BTC: Schluss vs 200-Tage-Linie und deren Steigung (20 Tage).
    Label fuer Tag t aus Daten bis t-1 (ex ante)."""
    lage = {}
    for i in range(1, len(m.datum)):
        s, s20 = m.sma("BTC", i - 1, 200), m.sma("BTC", i - 21, 200) if i > 21 else None
        if s is None or s20 is None:
            continue
        ueber, steigt = m.c["BTC"][i - 1] > s, s > s20
        lage[m.datum[i]] = "Bulle" if (ueber and steigt) else ("Baer" if (not ueber and not steigt) else "Seitwaerts")
    return lage
