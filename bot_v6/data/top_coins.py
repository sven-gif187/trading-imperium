"""
Trading Imperium V6 – Top Coins Auto-Update
Holt woechentlich die Top 15/20 Coins nach MarketCap von CoinGecko.
"""
import time
import json
import os
import threading
from typing import List
from config.settings import DATA_DIR
from core.logger import log

try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False

TOP_COINS_FILE = os.path.join(DATA_DIR, "top_coins.json")


class TopCoinsUpdater:
    """Aktualisiert die Coin-Liste basierend auf MarketCap."""

    COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

    def __init__(self, quote="USDC", max_coins=20):
        self.quote = quote
        self.max_coins = max_coins
        self.last_update = 0
        self.top_coins = []

    def fetch_top_coins(self) -> List[str]:
        """Holt Top Coins nach MarketCap."""
        if not HAS_REQ:
            return []

        try:
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 50,
                "page": 1,
                "sparkline": "false",
            }
            r = requests.get(self.COINGECKO_URL, params=params, timeout=15)
            if r.status_code != 200:
                log.warn("TOPCOIN", f"CoinGecko Status: {r.status_code}")
                return self._load_cached()

            data = r.json()
            # Stablecoins und Wrapped-Tokens rausfiltern
            skip = {"usdt", "usdc", "dai", "busd", "tusd", "wbtc", "weth", "steth", "lido"}
            symbols = []
            for coin in data:
                sym = coin.get("symbol", "").upper()
                if sym.lower() not in skip and len(symbols) < self.max_coins:
                    pair = f"{sym}/{self.quote}"
                    symbols.append(pair)

            self.top_coins = symbols
            self.last_update = time.time()
            self._save(symbols)
            log.info("TOPCOIN", f"Top {len(symbols)} Coins aktualisiert: {', '.join(s.split('/')[0] for s in symbols[:5])}...")
            return symbols

        except Exception as e:
            log.warn("TOPCOIN", f"Fehler: {str(e)[:40]}")
            return self._load_cached()

    def should_update(self, interval_hours=168) -> bool:
        """Soll aktualisiert werden? (Standard: woechentlich = 168h)"""
        return (time.time() - self.last_update) > interval_hours * 3600

    def get_or_fetch(self, interval_hours=168) -> List[str]:
        """Gibt gecachte Coins zurueck oder holt neue."""
        if self.should_update(interval_hours):
            return self.fetch_top_coins()
        if self.top_coins:
            return self.top_coins
        return self._load_cached()

    def _save(self, coins):
        try:
            os.makedirs(os.path.dirname(TOP_COINS_FILE), exist_ok=True)
            with open(TOP_COINS_FILE, "w") as f:
                json.dump({"coins": coins, "time": time.time()}, f)
        except Exception:
            pass

    def _load_cached(self) -> List[str]:
        try:
            if os.path.exists(TOP_COINS_FILE):
                with open(TOP_COINS_FILE, "r") as f:
                    data = json.load(f)
                self.top_coins = data.get("coins", [])
                self.last_update = data.get("time", 0)
                return self.top_coins
        except Exception:
            pass
        return []

    def get_status(self):
        return {"coins": len(self.top_coins), "last_update": self.last_update,
                "age_hours": int((time.time() - self.last_update) / 3600) if self.last_update else -1}
