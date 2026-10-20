"""Trading Imperium V5 – Data Agent: Marktdaten holen + Indikatoren."""
import ccxt, pandas as pd, pandas_ta as ta, numpy as np
from typing import Dict, Optional, List
from core.events import MarketSnapshot, MarketRegime
from core.logger import log

class DataAgent:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.price_cache = {}
        self._last_snapshots = {}  # coin -> letzter Snapshot (fuer UI)
        # Client erstellen (MUSS funktionieren - Kern des Bots!)
        try:
            # [E13 KLEINIGKEITEN 15.10.2026] P0-11, wie v7 (15.09.2026): Die feste Tabelle wertete JEDEN Eintrag aus,
            # auch ccxt.coinbasepro, das es seit ccxt 4 nicht mehr gibt -> bei jedem Start
            # 'Client-Fehler (1. Versuch): module ccxt has no attribute coinbasepro', danach
            # Binance-Fallback. Ein roter Fehler bei jedem Start gewoehnt ans Ueberlesen.
            # Jetzt wird nur die eingestellte Boerse geholt (ccxt_id = binance -> derselbe Client).
            _id = str(getattr(config.exchange, "ccxt_id", "") or "binance")
            Ex = getattr(ccxt, _id, None)
            if Ex is None:
                log.warn("DATA", f"ccxt kennt keine Boerse '{_id}' - nehme binance fuer die Kurse")
                Ex = ccxt.binance
            self.client = Ex({"enableRateLimit": True, "timeout": 15000})
            log.info("DATA", f"Client erstellt: {config.exchange.name}")
        except Exception as e:
            log.error("DATA", f"Client-Fehler (1. Versuch): {e}")
            # Fallback: Direkt Binance ohne Config
            try:
                self.client = ccxt.binance({"enableRateLimit": True, "timeout": 15000})
                log.info("DATA", "Client erstellt: Binance (Fallback)")
            except Exception as e2:
                log.error("DATA", f"KRITISCH: Auch Fallback fehlgeschlagen: {e2}")

        if self.client:
            # Test-Aufruf um sicherzustellen dass es funktioniert
            try:
                t = self.client.fetch_ticker("BTC/USDC")
                self.price_cache["BTC/USDC"] = t.get("last", 0)
                log.info("DATA", f"Test OK: BTC/USDC = {t.get('last', 0):,.2f}$")
            except Exception as e:
                log.warn("DATA", f"Test BTC/USDC fehlgeschlagen: {str(e)[:50]}")
                # Versuche USDT als Test
                try:
                    t = self.client.fetch_ticker("BTC/USDT")
                    self.price_cache["BTC/USDT"] = t.get("last", 0)
                    log.info("DATA", f"Test OK: BTC/USDT = {t.get('last', 0):,.2f}$")
                except Exception as e2:
                    log.error("DATA", f"WARNUNG: Auch BTC/USDT fehlgeschlagen: {str(e2)[:50]}")
        else:
            log.error("DATA", "KEIN CLIENT! Bot kann keine Marktdaten holen!")

    def fetch_snapshot(self, symbol, tf="5m", limit=250):
        # [13.08.2026] limit 120 -> 250, Entscheidung Sven.
        #
        # WARUM: Mit 120 Kerzen ist EMA200 mathematisch nicht berechenbar -
        # er braucht 200. Im Merkmals-Schnappschuss (Schritt 3) blieb die
        # Spalte ema200 deshalb bei jedem Eintrag leer, waehrend alle
        # anderen 36 Merkmale ankamen. Ein Feld, das im Messfenster fehlt,
        # ist hinterher nicht nachrueckbar.
        #
        # WAS SICH DADURCH AENDERT: EMA ist rekursiv, mehr Historie ergibt
        # also andere Werte. Nachgemessen am 13.08. gegen eine volle
        # Historie von 400 Kerzen:
        #
        #     120 Kerzen: EMA20 weicht 0,000012 %, EMA50 weicht 0,0543 % ab
        #     250 Kerzen: EMA20 weicht 0,000000 %, EMA50 weicht 0,0002 % ab
        #
        # Die Umstellung macht EMA50 also nicht ungenauer, sondern rund
        # 280-mal GENAUER - mehr Historie liegt naeher am wahren Wert.
        # Es bleibt formal eine Verhaltensaenderung (andere Zahl = evtl.
        # andere Entscheidung an der Schwelle), aber sie geht in Richtung
        # korrekter, nicht in Richtung anders.
        #
        # WARUM TROTZDEM JETZT: Genau deshalb VOR dem Messfenster und
        # nicht mittendrin. Nach dem Einfrieren waere sie unzulaessig,
        # und dann fehlte EMA200 zwei Wochen lang.
        #
        # NICHT BETROFFEN: Aufrufer, die limit ausdruecklich setzen -
        # app.py:3006 (300), models/auto_retrain.py (500),
        # backtest/engine.py und train_pipeline.py (eigener Wert).
        # Der Handelspfad (app.py:2405 und :2497) nutzt den Standardwert.
        if not self.client: return None
        try:
            # Versuche USDC, Fallback auf USDT
            try:
                bars = self.client.fetch_ohlcv(symbol, tf, limit=limit)
            except Exception:
                alt = symbol.replace("USDC", "USDT")
                bars = self.client.fetch_ohlcv(alt, tf, limit=limit)

            if not bars or len(bars) < 30:
                return None

            df = pd.DataFrame(bars, columns=["Date","Open","High","Low","Close","Volume"])
            df["Date"] = pd.to_datetime(df["Date"], unit="ms"); df.set_index("Date", inplace=True)
            df["RSI"] = ta.rsi(df["Close"], length=14)
            df["EMA20"] = ta.ema(df["Close"], length=20)
            df["EMA50"] = ta.ema(df["Close"], length=50)
            m = ta.macd(df["Close"])
            if m is not None: df["MACD"]=m.iloc[:,0]; df["MACD_signal"]=m.iloc[:,2]; df["MACD_hist"]=m.iloc[:,1]
            bb = ta.bbands(df["Close"], length=20, std=2)
            if bb is not None:
                for c in bb.columns: df[c]=bb[c]
            df["ADX"] = self._adx(df); df["ATR"] = ta.atr(df["High"],df["Low"],df["Close"],length=14)
            last = df.iloc[-1]; self.price_cache[symbol] = last["Close"]
            adx = last.get("ADX", 20)
            reg = MarketRegime.TRENDING if adx>25 else MarketRegime.RANGING if adx<20 else MarketRegime.UNKNOWN
            snap = MarketSnapshot(symbol=symbol, timeframe=tf, open=last["Open"], high=last["High"],
                low=last["Low"], close=last["Close"], volume=last["Volume"], regime=reg,
                indicators={"rsi":round(last.get("RSI",50),1),"ema20":round(last.get("EMA20",0),2),
                    "ema50":round(last.get("EMA50",0),2),"macd":round(last.get("MACD",0),2),
                    "macd_signal":round(last.get("MACD_signal",0),2),
                    "adx":round(adx,1),"atr":round(last.get("ATR",0),2)})
            snap._df = df
            self._last_snapshots[symbol] = snap  # Fuer UI-Anzeige
            return snap
        except Exception as e:
            log.error("DATA", f"{symbol}: {str(e)[:80]}"); return None

    def fetch_prices(self, symbols):
        # [P4-FRISCHE 20.07.] Frische-Stempel + gedrosseltes Logging.
        # Verhalten unveraendert: alter Cache-Wert bleibt bei Fehler stehen.
        import time as _p4t
        if not hasattr(self, "price_ts"):
            self.price_ts = {}
        if not hasattr(self, "_p4_fails"):
            self._p4_fails = {}
        for s in symbols:
            try:
                if self.client:
                    self.price_cache[s] = self.client.fetch_ticker(s)["last"]
                    self.price_ts[s] = _p4t.time()
                    if self._p4_fails.pop(s, 0):
                        log.info("MARKET", f"{s}: Preis-Feed wieder OK")
            except Exception as _e:  # P1-HARDEN
                _n = self._p4_fails.get(s, 0) + 1
                self._p4_fails[s] = _n
                if _n == 1 or _n % 10 == 0:
                    _last = self.price_ts.get(s)
                    _alter = f"{_p4t.time() - _last:.0f}s alt" if _last else "nie erneuert"
                    log.warn("MARKET", f"{s}: Ticker-Preis fehlgeschlagen ({_n}x), "
                                       f"behalte alten Cache [{_alter}] ({str(_e)[:50]})")
        return dict(self.price_cache)

    def price_age(self, symbol):
        """[P4-FRISCHE] Alter des Cache-Preises in Sekunden (None = unbekannt)."""
        import time as _p4t
        _ts = getattr(self, "price_ts", {}).get(symbol)
        return (_p4t.time() - _ts) if _ts else None

    def _adx(self, df, p=14):
        try:
            h,l,c = df["High"],df["Low"],df["Close"]
            pdm=h.diff().clip(lower=0); mdm=(-l.diff()).clip(lower=0)
            tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
            atr=tr.rolling(p).mean(); pdi=100*(pdm.rolling(p).mean()/atr); mdi=100*(mdm.rolling(p).mean()/atr)
            dx=(pdi-mdi).abs()/(pdi+mdi+1e-10)*100; return dx.rolling(p).mean()
        except: return pd.Series([20]*len(df), index=df.index)

    def get_fear_greed(self):
        try:
            import requests; r=requests.get("https://api.alternative.me/fng/?limit=1",timeout=5)  # P1-HARDEN
            return int(r.json()["data"][0]["value"])
        except Exception as _e:
            log.warn("MARKET", f"F&G-Abruf fehlgeschlagen, nutze Default 50 ({str(_e)[:50]})")
            return 50
