# -*- coding: utf-8 -*-
"""
backtest/ausstieg_backtest.py - Ausstiegsregeln gegen echte Kerzen  [E11 29.07.2026]
====================================================================================
Beantwortet die eine offene Frage aus dem E9-Umbau:
**Ist die neue Ratsche wirklich besser als die alte Leiter?**

METHODE
-------
Beide Regeln laufen ueber IDENTISCHE Kerzen mit IDENTISCHEN Einstiegen.
Getauscht wird ausschliesslich die Ausstiegsregel. Damit ist jeder
Unterschied im Ergebnis dem Ausstieg zuzuschreiben und sonst nichts.

Die neue Regel wird NICHT nachgebaut, sondern es werden die echten
Funktionen aus risk/exit_rules.py aufgerufen - dieselben, die im
laufenden Bot arbeiten. Ein Nachbau wuerde genau das testen, was man
gerade nicht testen will: die eigene Vorstellung vom Code.

Die alte Regel ist woertlich aus runtime/exit_monitor.py uebernommen,
Stand vor dem 29.07. (siehe ALTE_LEITER unten).

PESSIMISTISCHE ANNAHMEN (bewusst gegen das Wunschergebnis gerichtet)
-------------------------------------------------------------------
 1. REIHENFOLGE INNERHALB DER KERZE. Bei einer 15-Minuten-Kerze ist der
    Weg zwischen Hoch und Tief unbekannt. Angenommen wird immer:
    erst das TIEF, dann das HOCH. Fuer eine Long-Position ist das der
    unguenstigste Fall - Stops loesen frueher aus, Hochs zaehlen spaeter.
 2. GEBUEHREN beidseitig 0.1 % (Binance-Standard ohne BNB-Rabatt).
 3. SLIPPAGE 0.05 % je Seite, fest statt zufaellig, damit zwei Laeufe
    vergleichbar bleiben.
 4. STOPS FUELLEN ZUM STOPPREIS, nicht besser. Reisst eine Kerze weit
    durch den Stop, wird der schlechtere Wert genommen (Kerzentief).

WAS DIESER BACKTEST NICHT KANN
------------------------------
 * Die Einstiege sind eine VEREINFACHUNG des echten DCA-Pfads (F&G je Tag
   statt live, ein Kauf je Stunde). Die absoluten Renditen sind daher
   nicht die Renditen des echten Bots. Fuer den VERGLEICH zweier
   Ausstiegsregeln ist das unerheblich, solange beide dieselben
   Einstiege bekommen - und das tun sie.
 * TREND_EXIT (Multi-Timeframe bearish) fehlt, weil die MTF-Kette hier
   nicht nachgebildet wird. Sie wirkt auf beide Regeln gleich.
 * 15-Minuten-Aufloesung statt der 30 Sekunden des echten Monitors.
   Sehr kurze Ausschlaege bleiben unsichtbar.
"""
import os
import sys
import csv
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk import exit_rules                       # DIE ECHTE REGEL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATEN = os.path.join(ROOT, "data_store", "backtest")

GEBUEHR = 0.001          # 0.1 % je Seite
SLIPPAGE = 0.0005        # 0.05 % je Seite


# ===========================================================================
# DIE ALTE LEITER - woertlich aus runtime/exit_monitor.py, Stand vor 29.07.
# ===========================================================================
def ALTE_LEITER(pnl_pct, hoechst_pnl_pct, trail_pct, regime):
    """Trail-Abstand nach der alten Regel.

    Zwei Eigenheiten, die hier absichtlich erhalten bleiben:
      * Der Faktor kommt aus dem AKTUELLEN Gewinn (pnl_pct), nicht aus
        dem Hoechststand -> lockert sich auf dem Rueckweg selbst.
      * Je hoeher der Gewinn, desto ENGER der Trail (Inversion).
    """
    if pnl_pct <= 0.3 or trail_pct <= 0:
        return 0.0
    up = "TRENDING_UP" in str(regime).upper()
    if pnl_pct >= 5.0:
        stufe = 1.0 if up else 0.5
    elif pnl_pct >= 3.0:
        stufe = 1.4 if up else 0.7
    elif pnl_pct >= 1.0:
        stufe = 2.0 if up else 1.0
    else:
        stufe = 1.6
    return round(trail_pct * stufe, 3)


def NEUE_LEITER(pnl_pct, hoechst_pnl_pct, trail_pct, regime):
    """Trail-Abstand nach der neuen Regel - echte Funktion, kein Nachbau."""
    return exit_rules.effektiver_trail(hoechst_pnl_pct, trail_pct, regime)


# ===========================================================================
# Daten
# ===========================================================================
def lade_kerzen(symbol, timeframe="15m", marke=""):
    p = os.path.join(DATEN, symbol.replace("/", "") + f"_{timeframe}{marke}.csv")
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                out.append((int(r["zeit"]), float(r["open"]), float(r["high"]),
                            float(r["low"]), float(r["close"])))
            except Exception:
                continue
    return out


def lade_fear_greed():
    p = os.path.join(DATEN, "fear_greed.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ===========================================================================
# Simulation
# ===========================================================================
class Position:
    __slots__ = ("symbol", "menge", "einstand", "kosten", "hoch", "tief",
                 "hoechst_pnl", "stufen", "auf")

    def __init__(self, symbol, menge, einstand, kosten):
        self.symbol, self.menge = symbol, menge
        self.einstand, self.kosten = einstand, kosten
        self.hoch = self.tief = einstand
        self.hoechst_pnl = 0.0
        self.stufen = 1
        self.auf = True


def gleitender_schnitt(kerzen, laenge):
    """{zeit: SMA des Schlusskurses}. laenge in Kerzen."""
    out, summe, fenster = {}, 0.0, []
    for k in kerzen:
        fenster.append(k[4])
        summe += k[4]
        if len(fenster) > laenge:
            summe -= fenster.pop(0)
        out[k[0]] = (summe / len(fenster)) if len(fenster) == laenge else None
    return out


class Lauf:
    """Ein kompletter Durchlauf mit einer bestimmten Ausstiegsregel.

    EINSTIEGSFILTER  [E11 29.07.2026]
    ---------------------------------
    trend_sma_bars : > 0 -> es wird nur gekauft, wenn der Coin UEBER seinem
                     gleitenden Schnitt dieser Laenge steht (in 15m-Kerzen;
                     96 = 1 Tag, 480 = 5 Tage, 2880 = 30 Tage).
    markt_sma_bars : > 0 -> es wird nur gekauft, wenn BTC ueber seinem
                     Schnitt steht. Marktfilter statt Coinfilter.

    Der Grund fuer diese Schalter: der Testzeitraum 2025-07 bis 2026-07 war
    ein Baerenmarkt (BTC -45 %, ADA -79 %), und der Fear-&-Greed-Index lag
    an 66 % aller Tage unter 30. Eine Regel "kaufe bei Angst und mittle
    nach" kauft dort ein Jahr lang in einen Absturz hinein. Ohne einen
    Trendfilter misst man nicht die Ausstiegsregel, sondern nur die
    Geschwindigkeit des Untergangs.
    """

    def __init__(self, leiter_fn, name, *, startkapital=500.0, stop_loss_pct=2.5,
                 trail_pct=1.0, groesse_pct=20.0, max_pos=5, max_stufen=3,
                 nachkauf_ab_pct=2.0, breakeven=True, sperre_min=90,
                 sperre_unter_pct=1.0, fg_grenze=30,
                 trend_sma_bars=0, markt_sma_bars=0):
        self.leiter_fn, self.name = leiter_fn, name
        self.startkapital = startkapital
        self.stop_loss_pct, self.trail_pct = stop_loss_pct, trail_pct
        self.groesse_pct, self.max_pos = groesse_pct, max_pos
        self.max_stufen, self.nachkauf_ab_pct = max_stufen, nachkauf_ab_pct
        self.breakeven = breakeven
        self.sperre_min, self.sperre_unter_pct = sperre_min, sperre_unter_pct
        self.fg_grenze = fg_grenze
        self.trend_sma_bars, self.markt_sma_bars = trend_sma_bars, markt_sma_bars
        self._sma = {}          # symbol -> {zeit: wert}
        self._markt = {}        # zeit -> True/False (BTC ueber Schnitt)

        self.bar = startkapital
        self.positionen = {}
        self.trades = []
        self.equity = []
        self.gesperrt = {}          # symbol -> (bis_ms, ausstiegspreis)

    # ---------- Buchhaltung ----------
    def _kaufe(self, symbol, preis, zeit):
        kurs = preis * (1 + SLIPPAGE)
        betrag = min(self.eigenkapital(preis_map=None) * self.groesse_pct / 100, self.bar)
        if betrag < 10:
            return False
        geb = betrag * GEBUEHR
        menge = (betrag - geb) / kurs
        self.bar -= betrag
        p = self.positionen.get(symbol)
        if p is None:
            self.positionen[symbol] = Position(symbol, menge, kurs, betrag)
        else:
            gesamt = p.menge + menge
            p.einstand = (p.einstand * p.menge + kurs * menge) / gesamt
            p.menge = gesamt
            p.kosten += betrag
            p.stufen += 1
            # E9-3: Hoechststaende beim Mitteln zuruecksetzen
            p.hoch = p.tief = p.einstand
            p.hoechst_pnl = 0.0
        return True

    def _verkaufe(self, p, preis, zeit, grund):
        kurs = preis * (1 - SLIPPAGE)
        erloes = p.menge * kurs
        geb = erloes * GEBUEHR
        netto = erloes - geb
        pnl = netto - p.kosten                      # E9-2: gegen echten Mittelabfluss
        self.bar += netto
        self.trades.append({
            "symbol": p.symbol, "zeit": zeit, "grund": grund,
            "einstand": p.einstand, "ausstieg": kurs, "menge": p.menge,
            "kosten": p.kosten, "pnl": pnl,
            "pnl_pct": (netto / p.kosten - 1) * 100 if p.kosten > 0 else 0,
            "mfe_pct": (p.hoch / p.einstand - 1) * 100,
            "mae_pct": (p.tief / p.einstand - 1) * 100,
            "stufen": p.stufen,
        })
        self.gesperrt[p.symbol] = (zeit + self.sperre_min * 60_000, kurs)
        del self.positionen[p.symbol]

    def eigenkapital(self, preis_map):
        w = self.bar
        if preis_map:
            for s, p in self.positionen.items():
                w += p.menge * preis_map.get(s, p.einstand)
        else:
            for p in self.positionen.values():
                w += p.menge * p.einstand
        return w

    # ---------- Ausstiegsentscheidung ----------
    def _pruefe_ausstieg(self, p, preis, regime):
        pnl_pct = (preis / p.einstand - 1) * 100
        if pnl_pct > p.hoechst_pnl:
            p.hoechst_pnl = pnl_pct
        if pnl_pct <= -self.stop_loss_pct:
            return "STOP_LOSS"
        if self.breakeven and exit_rules.breakeven_verletzt(pnl_pct, p.hoechst_pnl):
            return "BREAKEVEN"
        trail = self.leiter_fn(pnl_pct, p.hoechst_pnl, self.trail_pct, regime)
        if trail > 0 and p.hoch > 0:
            fall = (p.hoch - preis) / p.hoch * 100
            if fall >= trail:
                return "TRAILING"
        return None

    # ---------- Hauptschleife ----------
    def laufe(self, kerzen_je_coin, fg_tabelle, regime="RANGING"):
        zeitpunkte = sorted({k[0] for ks in kerzen_je_coin.values() for k in ks})
        index = {s: {k[0]: k for k in ks} for s, ks in kerzen_je_coin.items()}
        letzter_kauf_h = -1

        # Einstiegsfilter vorbereiten
        if self.trend_sma_bars > 0:
            for s, ks in kerzen_je_coin.items():
                self._sma[s] = gleitender_schnitt(ks, self.trend_sma_bars)
        if self.markt_sma_bars > 0:
            btc = kerzen_je_coin.get("BTC/USDC") or []
            sma = gleitender_schnitt(btc, self.markt_sma_bars)
            self._markt = {k[0]: (sma.get(k[0]) is not None and k[4] > sma[k[0]])
                           for k in btc}

        for t in zeitpunkte:
            tag = datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
            fg = fg_tabelle.get(tag, 50)
            preis_map = {}

            # --- 1. Ausstiege zuerst (pessimistisch: Tief vor Hoch) ---
            for s in list(self.positionen):
                k = index.get(s, {}).get(t)
                if not k:
                    continue
                _, o, hi, lo, cl = k
                preis_map[s] = cl
                p = self.positionen[s]
                if lo < p.tief:
                    p.tief = lo
                # Schritt 1: Tief - loest es einen Ausstieg aus?
                grund = self._pruefe_ausstieg(p, lo, regime)
                if grund:
                    self._verkaufe(p, lo, t, grund)
                    continue
                # Schritt 2: Hoch - neuer Hoechststand
                if hi > p.hoch:
                    p.hoch = hi
                pnl_hoch = (hi / p.einstand - 1) * 100
                if pnl_hoch > p.hoechst_pnl:
                    p.hoechst_pnl = pnl_hoch
                # Schritt 3: Schlusskurs
                grund = self._pruefe_ausstieg(p, cl, regime)
                if grund:
                    self._verkaufe(p, cl, t, grund)

            # --- 2. Einstiege: hoechstens einer je Stunde ---
            stunde = t // 3_600_000
            # Marktfilter: liegt BTC unter seinem Schnitt, wird gar nicht gekauft
            markt_ok = True if not self._markt else self._markt.get(t, False)
            if fg < self.fg_grenze and stunde != letzter_kauf_h and markt_ok:
                for s, ks in index.items():
                    k = ks.get(t)
                    if not k:
                        continue
                    preis = k[4]
                    preis_map.setdefault(s, preis)
                    # Trendfilter je Coin: nur kaufen was ueber seinem Schnitt steht
                    if self.trend_sma_bars > 0:
                        sma = self._sma.get(s, {}).get(t)
                        if sma is None or preis <= sma:
                            continue
                    p = self.positionen.get(s)
                    if p is not None:
                        # Nachkauf nur guenstiger und nur begrenzt oft
                        if p.stufen >= self.max_stufen:
                            continue
                        if preis >= p.einstand * (1 - self.nachkauf_ab_pct / 100):
                            continue
                    else:
                        if len(self.positionen) >= self.max_pos:
                            continue
                        # E9-1: Wiedereinstiegs-Sperre
                        bis, aus = self.gesperrt.get(s, (0, 0))
                        if t < bis:
                            continue
                        if aus > 0 and preis > aus * (1 - self.sperre_unter_pct / 100) \
                                and t < bis + 6 * 3_600_000:
                            continue
                    if self._kaufe(s, preis, t):
                        letzter_kauf_h = stunde
                        break

            if len(self.equity) == 0 or t - self.equity[-1][0] >= 3_600_000:
                self.equity.append((t, self.eigenkapital(preis_map)))

        # Am Ende offene Positionen zum letzten Kurs bewerten (nicht verkaufen)
        return self.auswertung()

    # ---------- Kennzahlen ----------
    def auswertung(self):
        pnl = [t["pnl"] for t in self.trades]
        n = len(pnl)
        gew = [p for p in pnl if p > 0]
        ver = [p for p in pnl if p <= 0]
        avg_w = sum(gew) / len(gew) if gew else 0.0
        avg_v = sum(ver) / len(ver) if ver else 0.0
        werte = [w for _, w in self.equity]
        dd, hoch = 0.0, None
        for w in werte:
            hoch = w if hoch is None or w > hoch else hoch
            if hoch > 0:
                dd = max(dd, (hoch - w) / hoch * 100)
        med_mfe = sorted(t["mfe_pct"] for t in self.trades)[n // 2] if n else 0.0
        med_real = sorted(t["pnl_pct"] for t in self.trades)[n // 2] if n else 0.0
        return {
            "name": self.name, "trades": n,
            "summe": sum(pnl),
            "mittel": sum(pnl) / n if n else 0.0,
            "wr": len(gew) / n * 100 if n else 0.0,
            "avg_w": avg_w, "avg_v": avg_v,
            "rr": abs(avg_w / avg_v) if avg_v else 0.0,
            "profitfaktor": (sum(gew) / abs(sum(ver))) if ver and sum(ver) else 0.0,
            "drawdown": dd,
            "endkapital": werte[-1] if werte else self.startkapital,
            "med_mfe": med_mfe, "med_real": med_real,
            "giveback": med_mfe - med_real,
            "groesster_gewinn": max(t["pnl_pct"] for t in self.trades) if n else 0.0,
            "gruende": _zaehle(t["grund"] for t in self.trades),
        }


def _zaehle(it):
    d = {}
    for x in it:
        d[x] = d.get(x, 0) + 1
    return d
