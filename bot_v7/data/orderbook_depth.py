"""
Trading Imperium V6 – Order Book Analysis
Analysiert Orderbuch-Tiefe fuer bessere Entry/Exit Punkte.
"""
import time
import threading
from typing import Dict, List
from core.logger import log


class OrderBookAnalyzer:
    """Analysiert Orderbuch fuer Support/Resistance und Imbalance."""

    def __init__(self, client=None, cache_sec=30):
        self.client = client
        self.cache_sec = cache_sec
        self._cache = {}
        self._cache_time = {}

    def set_client(self, client):
        self.client = client

    def analyze(self, symbol, depth=20) -> Dict:
        """Analysiert Orderbuch eines Coins."""
        if not self.client:
            return {"imbalance": 0, "bias": "NEUTRAL"}

        now = time.time()
        if symbol in self._cache and (now - self._cache_time.get(symbol, 0)) < self.cache_sec:
            return self._cache[symbol]

        try:
            ob = self.client.fetch_order_book(symbol, limit=depth)
            bids = ob.get("bids", [])
            asks = ob.get("asks", [])

            if not bids or not asks:
                return {"imbalance": 0, "bias": "NEUTRAL"}

            # Bid/Ask Volume
            bid_vol = sum(b[1] for b in bids[:depth])
            ask_vol = sum(a[1] for a in asks[:depth])
            total = bid_vol + ask_vol

            # Imbalance: positiv = mehr Kaufdruck
            imbalance = (bid_vol - ask_vol) / total if total > 0 else 0

            # Spread
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            spread_pct = ((best_ask - best_bid) / best_bid) * 100

            # Grosse Walls finden
            bid_wall = max(bids[:depth], key=lambda x: x[1]) if bids else [0, 0]
            ask_wall = max(asks[:depth], key=lambda x: x[1]) if asks else [0, 0]

            # Bias
            if imbalance > 0.15:
                bias = "BULLISH"
            elif imbalance < -0.15:
                bias = "BEARISH"
            else:
                bias = "NEUTRAL"

            result = {
                "imbalance": round(imbalance, 3),
                "bias": bias,
                "bid_volume": round(bid_vol, 2),
                "ask_volume": round(ask_vol, 2),
                "spread_pct": round(spread_pct, 4),
                "bid_wall": {"price": bid_wall[0], "size": bid_wall[1]},
                "ask_wall": {"price": ask_wall[0], "size": ask_wall[1]},
                "best_bid": best_bid,
                "best_ask": best_ask,
            }

            self._cache[symbol] = result
            self._cache_time[symbol] = now
            return result

        except Exception as e:
            return {"imbalance": 0, "bias": "NEUTRAL", "error": str(e)[:40]}

    def get_score(self, symbol) -> float:
        """Score fuer Signal: -0.3 bis +0.3."""
        data = self._cache.get(symbol, {})
        imb = data.get("imbalance", 0)
        return round(max(-0.3, min(0.3, imb)), 3)

    def get_status(self):
        return {"cached_symbols": len(self._cache)}
