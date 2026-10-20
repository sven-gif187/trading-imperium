# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""
harness_ext.py - Messinstrumentierung fuer E2 (Stop-Abstand) und E5 (Universum).

GRUNDSATZ
---------
Die Hauptschleife von backtest/ausstieg_backtest.py::Lauf.laufe wird NICHT
dupliziert und NICHT veraendert. Diese Subklasse haengt sich ausschliesslich
an drei Stellen ein:

  _kaufe          -> merkt Eintrittszeit + den fuer DIESE Position gueltigen
                     Stop-Abstand (fix in % oder ATR-basiert)
  _verkaufe       -> ergaenzt den Trade-Datensatz um Haltedauer, Gebuehren,
                     Bruttobewegung und den verwendeten Stop
  _pruefe_ausstieg-> wortgleich zum Original (Z.243-256), einzige Aenderung:
                     der Stop kommt aus self.stop_pos[symbol] statt aus
                     self.stop_loss_pct. Bei stop_mode="pct" ist das
                     rechnerisch identisch zum Original.
  eigenkapital    -> passiver Mitschnitt der Kapitalbindung an genau den
                     Zeitpunkten, an denen das Original ohnehin sampelt.

Damit ist bei stop_mode="pct" jede Variante bitgleich zum Original-Harness,
und der einzige Unterschied zwischen den E2-Varianten ist der Stop-Abstand.

ATR - AUSDRUECKLICH OHNE LOOK-AHEAD
-----------------------------------
ATR(14) auf 1h-Kerzen (default_timeframe des Bots, config.json:50), aus den
15m-Kerzen aggregiert. Fuer einen 15m-Zeitpunkt t in Stunde H wird
ausschliesslich der ATR der Stunde H-1 verwendet, also nur abgeschlossene
Kerzen. Fehlt der Wert (erste 14 Stunden je Coin), wird der Kauf mit dem
Fallback-Stop ausgefuehrt und gezaehlt (self.atr_fallback).
"""
import os
import sys

def _finde_projekt():
    """Projektwurzel relativ zum Skriptort suchen (Marker: app.py).

    Ersetzt den frueher fest verdrahteten absoluten Pfad. Damit laeuft das
    Skript unabhaengig davon, wohin der Projektordner verschoben wird.
    """
    p = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isfile(os.path.join(p, "app.py")):
            return p
        p = os.path.dirname(p)
    raise RuntimeError("Projektwurzel nicht gefunden - app.py in keiner "
                       "uebergeordneten Ebene")


PROJEKT = _finde_projekt()
if PROJEKT not in sys.path:
    sys.path.insert(0, PROJEKT)

from backtest.ausstieg_backtest import (Lauf, NEUE_LEITER, ALTE_LEITER,
                                        lade_kerzen, lade_fear_greed,
                                        GEBUEHR, SLIPPAGE)
from risk import exit_rules

STUNDE_MS = 3_600_000
TAG_MS = 86_400_000

COINS = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "ADA/USDC", "AVAX/USDC",
         "LINK/USDC", "DOT/USDC", "DOGE/USDC", "NEAR/USDC", "UNI/USDC",
         "ATOM/USDC"]


# ===========================================================================
# Daten
# ===========================================================================
_CACHE = {}


def lade_jahr(marke="", coins=None):
    """marke='' -> 2025-07-29..2026-07-29, marke='_v1' -> 2024-07-29..2025-07-29"""
    key = (marke, tuple(coins or COINS))
    if key in _CACHE:
        return _CACHE[key]
    d = {}
    for c in (coins or COINS):
        k = lade_kerzen(c, marke=marke)
        if k:
            d[c] = k
    res = (d, lade_fear_greed())
    _CACHE[key] = res
    return res


def atr_1h_ohne_lookahead(kerzen15, periode=14):
    """{15m-zeit: ATR-Wert der letzten ABGESCHLOSSENEN Stunde}."""
    stunden = {}
    for t, o, hi, lo, cl in kerzen15:
        H = (t // STUNDE_MS) * STUNDE_MS
        s = stunden.get(H)
        if s is None:
            stunden[H] = [o, hi, lo, cl]
        else:
            s[1] = max(s[1], hi)
            s[2] = min(s[2], lo)
            s[3] = cl
    reihe = sorted(stunden.items())
    atr_je_stunde, trs, prev_close = {}, [], None
    for H, (o, hi, lo, cl) in reihe:
        if prev_close is None:
            tr = hi - lo
        else:
            tr = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close))
        trs.append(tr)
        if len(trs) > periode:
            trs.pop(0)
        if len(trs) == periode:
            atr_je_stunde[H] = sum(trs) / periode
        prev_close = cl
    out = {}
    for t, _o, _hi, _lo, _cl in kerzen15:
        H = (t // STUNDE_MS) * STUNDE_MS
        a = atr_je_stunde.get(H - STUNDE_MS)
        if a is not None:
            out[t] = a
    return out


# ===========================================================================
# Instrumentierter Lauf
# ===========================================================================
class LaufMess(Lauf):
    def __init__(self, *a, stop_mode="pct", atr_mult=1.5, atr_tab=None, **kw):
        super().__init__(*a, **kw)
        self.stop_mode = stop_mode
        self.atr_mult = atr_mult
        self.atr_tab = atr_tab or {}
        self.eintritt = {}       # symbol -> eintrittszeit_ms
        self.stop_pos = {}       # symbol -> stop_pct dieser Position
        self.bindung = []        # (cash, equity, offene_positionen)
        self.atr_fallback = 0
        self.stop_pcts = []      # alle tatsaechlich vergebenen Stop-Abstaende
        self.kauf_events = []    # (symbol, zeit, ROHpreis) - fuer Einstiegsqualitaet

    # ---- Stop-Abstand je Position festlegen ----
    def _kaufe(self, symbol, preis, zeit):
        neu = symbol not in self.positionen
        ok = super()._kaufe(symbol, preis, zeit)
        if not ok:
            return False
        if neu:
            self.eintritt[symbol] = zeit
        if self.stop_mode == "atr":
            a = self.atr_tab.get(symbol, {}).get(zeit)
            if a and preis > 0:
                self.stop_pos[symbol] = a / preis * 100.0 * self.atr_mult
            else:
                self.atr_fallback += 1
                self.stop_pos[symbol] = self.stop_loss_pct
        else:
            self.stop_pos[symbol] = self.stop_loss_pct
        self.stop_pcts.append(self.stop_pos[symbol])
        self.kauf_events.append((symbol, zeit, preis))
        return True

    # ---- Trade-Datensatz anreichern ----
    def _verkaufe(self, p, preis, zeit, grund):
        sym = p.symbol
        ein = self.eintritt.get(sym, zeit)
        stop = self.stop_pos.get(sym, self.stop_loss_pct)
        super()._verkaufe(p, preis, zeit, grund)
        t = self.trades[-1]
        t["eintritt"] = ein
        t["haltedauer_h"] = (zeit - ein) / STUNDE_MS
        t["stop_pct"] = stop
        t["geb"] = t["kosten"] * GEBUEHR + t["menge"] * t["ausstieg"] * GEBUEHR
        roh_ein = t["einstand"] / (1 + SLIPPAGE)
        roh_aus = t["ausstieg"] / (1 - SLIPPAGE)
        t["brutto_pct"] = (roh_aus / roh_ein - 1) * 100 if roh_ein > 0 else 0.0
        self.eintritt.pop(sym, None)
        self.stop_pos.pop(sym, None)

    # ---- wortgleich zu ausstieg_backtest.py:243-256, nur Stop-Quelle anders ----
    def _pruefe_ausstieg(self, p, preis, regime):
        pnl_pct = (preis / p.einstand - 1) * 100
        if pnl_pct > p.hoechst_pnl:
            p.hoechst_pnl = pnl_pct
        sl = self.stop_pos.get(p.symbol, self.stop_loss_pct)
        if pnl_pct <= -sl:
            return "STOP_LOSS"
        if self.breakeven and exit_rules.breakeven_verletzt(pnl_pct, p.hoechst_pnl):
            return "BREAKEVEN"
        trail = self.leiter_fn(pnl_pct, p.hoechst_pnl, self.trail_pct, regime)
        if trail > 0 and p.hoch > 0:
            fall = (p.hoch - preis) / p.hoch * 100
            if fall >= trail:
                return "TRAILING"
        return None

    # ---- Kapitalbindung passiv mitschneiden ----
    def eigenkapital(self, preis_map):
        w = super().eigenkapital(preis_map)
        if preis_map is not None:
            self.bindung.append((self.bar, w, len(self.positionen)))
        return w


# ===========================================================================
# Kennzahlen
# ===========================================================================
def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def kennzahlen(trades):
    """Kennzahlen aus einer Trade-Liste. R/R = avg_gewinn / |avg_verlust|."""
    n = len(trades)
    if n == 0:
        return dict(n=0, wr=0.0, rr=0.0, be_rr=0.0, ev=0.0, ev_r=0.0,
                    summe=0.0, geb=0.0, halte=0.0, avg_w=0.0, avg_v=0.0)
    pnl = [t["pnl"] for t in trades]
    gew = [x for x in pnl if x > 0]
    ver = [x for x in pnl if x <= 0]
    avg_w = sum(gew) / len(gew) if gew else 0.0
    avg_v = sum(ver) / len(ver) if ver else 0.0
    wr = len(gew) / n
    rr = abs(avg_w / avg_v) if avg_v else 0.0
    be_rr = (1 - wr) / wr if wr > 0 else float("inf")
    return dict(
        n=n, wr=wr * 100, rr=rr, be_rr=be_rr,
        ev=sum(pnl) / n,                       # $ je Trade (NICHT live-uebertragbar)
        ev_r=wr * rr - (1 - wr),               # in R (dimensionslos, vergleichbar)
        summe=sum(pnl),
        geb=sum(t["geb"] for t in trades),
        halte=sum(t["haltedauer_h"] for t in trades) / n,
        avg_w=avg_w, avg_v=avg_v)


def stop_anteil_am_verlust(trades):
    """(Anteil Stop-Trades an allen Trades, Anteil Stop-Verlust am Gesamtverlust)."""
    verlust_ges = sum(t["pnl"] for t in trades if t["pnl"] <= 0)
    stop_tr = [t for t in trades if t["grund"] == "STOP_LOSS"]
    stop_verlust = sum(t["pnl"] for t in stop_tr if t["pnl"] <= 0)
    n = len(trades)
    return (len(stop_tr) / n * 100 if n else 0.0,
            stop_verlust / verlust_ges * 100 if verlust_ges else 0.0,
            verlust_ges, stop_verlust)


def rueckkehr_nach_stop(trades, kerzen_je_coin, stunden=24):
    """E2c: Wie oft stand der Kurs nach einem Stop-Ausstieg innerhalb von
    <stunden> wieder UEBER dem (gemittelten) Einstand der Position?
    Gemessen am Kerzen-HOCH nach dem Ausstiegszeitpunkt."""
    idx = {s: sorted(ks) for s, ks in kerzen_je_coin.items()}
    stop_tr = [t for t in trades if t["grund"] == "STOP_LOSS"]
    zurueck = 0
    for t in stop_tr:
        ks = idx.get(t["symbol"])
        if not ks:
            continue
        t0, t1 = t["zeit"], t["zeit"] + stunden * STUNDE_MS
        for k in ks:
            if k[0] <= t0:
                continue
            if k[0] > t1:
                break
            if k[2] >= t["einstand"]:
                zurueck += 1
                break
    return len(stop_tr), zurueck, (zurueck / len(stop_tr) * 100 if stop_tr else 0.0)


def kapitalbindung(lauf):
    """(mittlere investierte Quote in %, mittlere Zahl offener Positionen)."""
    b = [(c, w, o) for c, w, o in lauf.bindung if w > 0]
    if not b:
        return 0.0, 0.0
    return (sum(1 - c / w for c, w, _ in b) / len(b) * 100,
            sum(o for _, _, o in b) / len(b))
