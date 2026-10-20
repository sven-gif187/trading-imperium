"""
Trading Imperium V6 – Multi-Exchange Support
Verbindet mit mehreren Boersen gleichzeitig. Findet besten Preis.
Unterstuetzt: Binance, Bybit, Kraken, OKX, Coinbase.
"""
import time
import threading
from typing import Dict, List, Optional
from core.logger import log

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False


EXCHANGE_CONFIGS = {
    "binance": {"class": "binance", "name": "Binance", "fees": 0.1},
    "bybit": {"class": "bybit", "name": "Bybit", "fees": 0.1},
    "kraken": {"class": "kraken", "name": "Kraken", "fees": 0.26},
    "okx": {"class": "okx", "name": "OKX", "fees": 0.1},
    "coinbase": {"class": "coinbasepro", "name": "Coinbase", "fees": 0.6},
}


class MultiExchangeManager:
    """Verwaltet mehrere Exchange-Verbindungen."""

    def __init__(self):
        self.exchanges = {}  # name -> ccxt instance
        self.price_cache = {}  # exchange -> symbol -> price
        self.active_exchange = "binance"
        self._lock = threading.Lock()

    def add_exchange(self, name, api_key="", api_secret="", testnet=False):
        """Fuegt eine Exchange hinzu."""
        if not HAS_CCXT:
            log.warn("MULTI-EX", "ccxt nicht installiert")
            return False

        cfg = EXCHANGE_CONFIGS.get(name)
        if not cfg:
            log.warn("MULTI-EX", f"Exchange '{name}' nicht unterstuetzt")
            return False

        try:
            Ex = getattr(ccxt, cfg["class"])
            params = {"enableRateLimit": True, "timeout": 15000}
            if api_key and api_secret:
                params["apiKey"] = api_key
                params["secret"] = api_secret
                if name == "binance":
                    params["options"] = {"defaultType": "spot", "adjustForTimeDifference": True,
                                         "recvWindow": 60000}
            if testnet:
                params["sandbox"] = True

            ex = Ex(params)
            # Test-Call
            t = ex.fetch_ticker("BTC/USDT")
            self.exchanges[name] = ex
            log.info("MULTI-EX", f"{cfg['name']} verbunden (BTC: {t.get('last', 0):,.2f}$)")
            return True
        except Exception as e:
            log.warn("MULTI-EX", f"{name}: {str(e)[:50]}")
            return False

    def add_public(self, name):
        """Fuegt eine Exchange OHNE API-Key hinzu (nur Preise lesen)."""
        return self.add_exchange(name)

    def get_best_price(self, symbol, side="buy") -> Dict:
        """Findet den besten Preis ueber alle Exchanges."""
        prices = {}
        for name, ex in self.exchanges.items():
            try:
                # Versuche USDC, dann USDT
                try:
                    t = ex.fetch_ticker(symbol)
                except Exception:
                    alt = symbol.replace("USDC", "USDT") if "USDC" in symbol else symbol.replace("USDT", "USDC")
                    t = ex.fetch_ticker(alt)
                prices[name] = {
                    "bid": t.get("bid", 0),
                    "ask": t.get("ask", 0),
                    "last": t.get("last", 0),
                    "spread": t.get("ask", 0) - t.get("bid", 0) if t.get("ask") and t.get("bid") else 0,
                }
            except Exception:
                pass
            time.sleep(0.2)

        if not prices:
            return {"best_exchange": self.active_exchange, "price": 0}

        if side == "buy":
            # Kaufen: niedrigster Ask-Preis
            best = min(prices.items(), key=lambda x: x[1]["ask"] if x[1]["ask"] > 0 else 999999)
        else:
            # Verkaufen: hoechster Bid-Preis
            best = max(prices.items(), key=lambda x: x[1]["bid"])

        return {
            "best_exchange": best[0],
            "price": best[1]["ask"] if side == "buy" else best[1]["bid"],
            "all_prices": prices,
            "spread": best[1]["spread"],
        }

    def fetch_ohlcv(self, symbol, timeframe="1h", limit=500, exchange=None):
        """Holt OHLCV von einer bestimmten oder der aktiven Exchange."""
        ex_name = exchange or self.active_exchange
        ex = self.exchanges.get(ex_name)
        if not ex:
            return None
        try:
            try:
                return ex.fetch_ohlcv(symbol, timeframe, limit=limit)
            except Exception:
                alt = symbol.replace("USDC", "USDT") if "USDC" in symbol else symbol.replace("USDT", "USDC")
                return ex.fetch_ohlcv(alt, timeframe, limit=limit)
        except Exception as e:
            log.warn("MULTI-EX", f"OHLCV {symbol} {ex_name}: {str(e)[:40]}")
            return None

    def fetch_balance(self, exchange=None):
        """Holt Balance von einer Exchange."""
        ex_name = exchange or self.active_exchange
        ex = self.exchanges.get(ex_name)
        if not ex:
            return {"total": {}, "free": {}}
        try:
            return ex.fetch_balance()
        except Exception as e:
            log.warn("MULTI-EX", f"Balance {ex_name}: {str(e)[:40]}")
            return {"total": {}, "free": {}}

    def execute_order(self, symbol, side, amount_or_qty, exchange=None):
        """Fuehrt Order auf einer Exchange aus."""
        ex_name = exchange or self.active_exchange
        ex = self.exchanges.get(ex_name)
        if not ex:
            return {"error": f"Exchange '{ex_name}' nicht verbunden"}
        try:
            if side == "buy":
                return ex.create_market_buy_order(symbol, amount_or_qty)
            else:
                return ex.create_market_sell_order(symbol, amount_or_qty)
        except Exception as e:
            return {"error": str(e)}

    def get_exchanges(self) -> List[str]:
        return list(self.exchanges.keys())

    def set_active(self, name):
        if name in self.exchanges:
            self.active_exchange = name
            log.info("MULTI-EX", f"Aktive Exchange: {name}")

    def get_status(self):
        return {
            "connected": list(self.exchanges.keys()),
            "active": self.active_exchange,
            "count": len(self.exchanges),
        }
