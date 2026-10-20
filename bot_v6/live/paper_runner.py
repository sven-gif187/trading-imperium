"""
Trading Imperium V5 – Paper Runner
Simuliert Trading ohne echtes Geld. Nutzt echte Preise vom DataAgent.
"""
import time
from typing import Dict
from core.logger import log


class PaperRunner:
    def __init__(self, config):
        self.config = config
        self.price_cache = {}  # Wird von aussen gesetzt (DataAgent)
        self.connected = True
        self.balances = {"USDC": config.trading.initial_paper_balance}

    def connect(self, *args, **kwargs):
        self.connected = True
        bal = self.balances.get("USDC", 0) + self.balances.get("USDT", 0)
        log.info("PAPER", f"Paper-Modus: {bal:.2f}$ Start-Balance")
        return True

    def disconnect(self):
        self.connected = False

    def fetch_balance(self):
        return {'total': dict(self.balances), 'free': dict(self.balances)}

    def set_prices(self, prices):
        self.price_cache.update(prices)

    def _get_price(self, symbol):
        p = self.price_cache.get(symbol, 0)
        if p <= 0:
            alt = symbol.replace("USDT", "USDC") if "USDT" in symbol else symbol.replace("USDC", "USDT")
            p = self.price_cache.get(alt, 0)
        return p

    def buy(self, symbol, amount_usd):
        asset = symbol.split("/")[0]
        price = self._get_price(symbol)
        if price <= 0:
            return {'error': f'Kein Preis fuer {symbol}'}
        avail = self.balances.get("USDC", 0) + self.balances.get("USDT", 0)
        if avail < amount_usd:
            return {'error': f'Nicht genug: {avail:.2f}$ < {amount_usd:.2f}$'}
        fee_usd = amount_usd * 0.001
        qty = (amount_usd - fee_usd) / price
        remaining = amount_usd
        for q in ["USDC", "USDT"]:
            take = min(self.balances.get(q, 0), remaining)
            self.balances[q] = self.balances.get(q, 0) - take
            remaining -= take
            if remaining <= 0: break
        self.balances[asset] = self.balances.get(asset, 0) + qty
        log.trade("PAPER", f"BUY {asset}: {qty:.6f} @ {price:,.2f}$ = {amount_usd:.2f}$")
        return {'symbol': symbol, 'side': 'buy', 'price': price,
                'qty': qty, 'cost': amount_usd, 'fee': fee_usd,
                'order_id': f'paper_{int(time.time()*1000)}'}

    def sell(self, symbol, qty):
        asset = symbol.split("/")[0]
        available = self.balances.get(asset, 0)
        if available <= 0:
            return {'error': f'Kein {asset}'}
        if qty > available:
            qty = available
        price = self._get_price(symbol)
        if price <= 0:
            return {'error': f'Kein Preis fuer {symbol}'}
        revenue = qty * price
        fee_usd = revenue * 0.001
        self.balances[asset] = max(0, self.balances.get(asset, 0) - qty)
        if self.balances.get(asset, 0) < 1e-10 and asset in self.balances:
            del self.balances[asset]
        self.balances["USDC"] = self.balances.get("USDC", 0) + revenue - fee_usd
        log.trade("PAPER", f"SELL {asset}: {qty:.6f} @ {price:,.2f}$ = {revenue:.2f}$")
        return {'symbol': symbol, 'side': 'sell', 'price': price,
                'qty': qty, 'cost': revenue - fee_usd, 'fee': fee_usd,
                'order_id': f'paper_{int(time.time()*1000)}'}

    def reset(self):
        self.balances = {"USDC": self.config.trading.initial_paper_balance}
        log.info("PAPER", f"RESET: {self.config.trading.initial_paper_balance:.2f}$")

    def get_status(self):
        return {"connected": True, "mode": "paper", "balance": dict(self.balances)}
