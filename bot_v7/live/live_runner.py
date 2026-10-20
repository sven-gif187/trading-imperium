"""
Trading Imperium V5 – Live Runner
Verbindet V5 mit echtem Binance-Trading.
"""
import time, ccxt
from typing import Dict
from core.logger import log
from core.exceptions import *

class LiveRunner:
    def __init__(self, config):
        self.config = config
        self.exchange = None
        self.connected = False
        self._balance_cache = None
        self._cache_time = 0

    def connect(self, api_key, api_secret, exchange_id="binance"):
        try:
            # ==========================================================
            # [15.09.2026] BEFUND 69 WAR NUR HALB REPARIERT.
            #
            # Hier stand dieselbe Verwechslung, die am 14.09. im
            # Haupt-Handelspfad behoben wurde - an einer zweiten Stelle,
            # die niemand mehr angesehen hatte.
            #
            # Die Folge stand bei JEDEM Start im Log:
            #   [ERROR] [LIVE] Verbindung fehlgeschlagen: binance
            #           {"code":-2008,"msg":"Invalid Api-Key ID."}
            #   [ERROR] [APP] Live-Verbindung fehlgeschlagen -> Paper
            #
            # Kein Wunder: Der Aufrufer (app.py) uebergibt
            # `config.exchange.ccxt_id` - und das ist die KURSQUELLE
            # (binance), nicht die Handelsboerse (bybit.eu). Der Bot
            # meldete sich also mit dem Bybit-Schluessel bei Binance an.
            #
            # Der Handel selbst war nie betroffen, der laeuft ueber
            # execution/engine.py. Betroffen war, was an diesem Runner
            # haengt: die Statusanzeige `runner_mode` (meldete "paper",
            # waehrend echtes Geld lief) und StateRecovery, das dadurch
            # bei jedem Start uebersprungen wurde.
            #
            # Dieselben drei Fallen wie im Haupt-Pfad, alle drei hier:
            #   1. handel_ccxt_id statt ccxt_id
            #   2. hostname bybit.eu - ccxt zeigt sonst auf bybit.com
            #   3. defaultType "unified" - Bybit EU kennt nur dieses
            #      Konto und antwortet auf "spot" mit
            #      "accountType only support UNIFIED"
            # ==========================================================
            _ziel = (getattr(self.config.exchange, "handel_ccxt_id", "")
                     or exchange_id)
            _host = getattr(self.config.exchange, "handel_hostname", "") or ""
            _kontoart = "unified" if "bybit" in str(_ziel).lower() else "spot"

            Ex = getattr(ccxt, _ziel, None) or ccxt.binance
            _einst = {
                'apiKey': api_key, 'secret': api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': _kontoart,
                            'adjustForTimeDifference': True,
                            'recvWindow': 60000},
            }
            if _host:
                _einst['hostname'] = _host
            log.info("LIVE", f"Verbinde mit {_ziel}"
                             f"{' / ' + _host if _host else ''}"
                             f" (Konto: {_kontoart})")
            self.exchange = Ex(_einst)
            self.exchange.load_markets()
            bal = self.exchange.fetch_balance()
            usdc = bal['total'].get('USDC', 0) + bal['total'].get('USDT', 0)
            btc = bal['total'].get('BTC', 0)
            self.connected = True
            log.info("LIVE", f"Verbunden! USDC: {usdc:.2f} | BTC: {btc:.8f}")
            for asset, amt in bal['total'].items():
                if amt > 0 and asset not in ('USDC', 'USDT', 'BTC'):
                    log.info("LIVE", f"  {asset}: {amt:.6f}")
            return True
        except Exception as e:
            self.connected = False
            log.error("LIVE", f"Verbindung fehlgeschlagen: {str(e)[:120]}")
            return False

    def disconnect(self):
        self.exchange = None; self.connected = False

    def fetch_balance(self):
        if not self.connected: return {'total': {}, 'free': {}}
        now = time.time()
        if self._balance_cache and (now - self._cache_time) < 3:
            return self._balance_cache
        try:
            b = self.exchange.fetch_balance()
            self._balance_cache = b; self._cache_time = now; return b
        except Exception as e:
            log.warn("LIVE", f"Balance: {str(e)[:60]}")
            return self._balance_cache or {'total': {}, 'free': {}}

    def buy(self, symbol, amount_usd):
        if not self.connected: raise ExchangeConnectionError("Nicht verbunden!")
        price = self.exchange.fetch_ticker(symbol)['last']
        qty = round(amount_usd / price, 6)
        order = self.exchange.create_market_buy_order(symbol, qty)
        self._balance_cache = None
        return {'symbol': symbol, 'side': 'buy', 'price': order.get('average', price),
                'qty': order.get('filled', qty), 'cost': order.get('cost', amount_usd),
                'fee': order.get('fee', {}).get('cost', 0), 'order_id': order.get('id', '')}

    def sell(self, symbol, qty):
        if not self.connected: raise ExchangeConnectionError("Nicht verbunden!")
        order = self.exchange.create_market_sell_order(symbol, qty)
        self._balance_cache = None
        fp = order.get('average', order.get('price', 0))
        return {'symbol': symbol, 'side': 'sell', 'price': fp,
                'qty': qty, 'cost': order.get('cost', qty * fp),
                'fee': order.get('fee', {}).get('cost', 0), 'order_id': order.get('id', '')}

    def get_price(self, symbol):
        try: return self.exchange.fetch_ticker(symbol)['last']
        except Exception as _e:  # P1-HARDEN
            log.warn("LIVE", f"{symbol}: Preis-Abruf fehlgeschlagen -> 0 ({str(_e)[:50]})")
            return 0

    def get_status(self):
        return {"connected": self.connected, "exchange": self.config.exchange.name}
