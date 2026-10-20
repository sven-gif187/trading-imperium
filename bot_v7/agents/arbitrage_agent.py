"""
Trading Imperium V6 – Cross-Exchange Arbitrage
Erkennt Preisunterschiede zwischen Binance und anderen Boersen.
"""
import time
import threading
from typing import Dict, List
from core.logger import log

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False


class ArbitrageAgent:
    """Erkennt Cross-Exchange Arbitrage-Moeglichkeiten."""

    def __init__(self, min_spread_pct=0.3):
        self.min_spread = min_spread_pct
        self.opportunities = []
        self.exchanges = {}
        self._init_exchanges()

    def _init_exchanges(self):
        if not HAS_CCXT:
            return
        try:
            self.exchanges["binance"] = ccxt.binance({"enableRateLimit": True, "timeout": 10000})
            self.exchanges["bybit"] = ccxt.bybit({"enableRateLimit": True, "timeout": 10000})
            log.info("ARB", f"Exchanges: {', '.join(self.exchanges.keys())}")
        except Exception as e:
            log.warn("ARB", f"Exchange-Setup: {str(e)[:40]}")

    def scan(self, symbols=None) -> List[Dict]:
        """Scannt Preisunterschiede zwischen Exchanges."""
        if len(self.exchanges) < 2:
            return []

        if symbols is None:
            symbols = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]

        opportunities = []
        for symbol in symbols:
            prices = {}
            for name, ex in self.exchanges.items():
                try:
                    # Versuche USDC, dann USDT
                    try:
                        t = ex.fetch_ticker(symbol)
                    except Exception:
                        alt = symbol.replace("USDC", "USDT")
                        t = ex.fetch_ticker(alt)
                    prices[name] = t.get("last", 0)
                except Exception:
                    pass
                time.sleep(0.2)

            if len(prices) >= 2:
                ex_list = list(prices.items())
                for i in range(len(ex_list)):
                    for j in range(i+1, len(ex_list)):
                        ex1, p1 = ex_list[i]
                        ex2, p2 = ex_list[j]
                        if p1 > 0 and p2 > 0:
                            spread_pct = abs(p1 - p2) / min(p1, p2) * 100
                            if spread_pct >= self.min_spread:
                                buy_at = ex1 if p1 < p2 else ex2
                                sell_at = ex2 if p1 < p2 else ex1
                                opp = {
                                    "symbol": symbol.split("/")[0],
                                    "buy_exchange": buy_at,
                                    "buy_price": min(p1, p2),
                                    "sell_exchange": sell_at,
                                    "sell_price": max(p1, p2),
                                    "spread_pct": round(spread_pct, 3),
                                    "time": time.strftime("%H:%M:%S"),
                                }
                                opportunities.append(opp)
                                log.info("ARB", f"{opp['symbol']}: {opp['spread_pct']:.2f}% "
                                               f"(Buy {buy_at} @ {min(p1,p2):,.2f} → "
                                               f"Sell {sell_at} @ {max(p1,p2):,.2f})")

        self.opportunities = opportunities[-20:]
        return opportunities

    def get_best_opportunity(self) -> Dict:
        if not self.opportunities:
            return {}
        return max(self.opportunities, key=lambda x: x["spread_pct"])

    def get_status(self):
        return {"exchanges": list(self.exchanges.keys()),
                "opportunities": len(self.opportunities),
                "min_spread": self.min_spread,
                "best": self.get_best_opportunity()}
