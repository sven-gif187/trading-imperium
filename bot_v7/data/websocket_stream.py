"""
Trading Imperium V5 – WebSocket Preis-Stream
Ersetzt Polling durch echte Binance WebSocket-Verbindung fuer Echtzeit-Preise.
Schneller, weniger API-Calls, sub-sekunde Updates.
"""
import json
import time
import threading
from typing import Dict, Callable, Optional
from core.logger import log

try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False


class BinanceWebSocket:
    """Echtzeit-Preis-Stream ueber Binance WebSocket."""

    WS_URL = "wss://stream.binance.com:9443/ws"
    MULTI_URL = "wss://stream.binance.com:9443/stream?streams="

    def __init__(self):
        self.prices = {}       # symbol -> price
        self.volumes = {}      # symbol -> 24h volume
        self.changes = {}      # symbol -> 24h change %
        self.callbacks = []    # Funktionen die bei Preis-Update aufgerufen werden
        self._ws = None
        self._thread = None
        self._running = False
        self._reconnect_count = 0
        self._last_update = 0
        self._message_count = 0

    def start(self, symbols=None):
        """Startet den WebSocket Stream."""
        if not HAS_WS:
            log.warn("WS", "websocket-client nicht installiert: pip install websocket-client")
            return False

        if symbols is None:
            symbols = ["btcusdc", "ethusdc", "solusdc", "xrpusdc", "adausdc",
                       "avaxusdc", "linkusdc", "dotusdc", "dogeusdc", "nearusdc"]

        # Streams zusammenbauen
        streams = [f"{s.lower()}@ticker" for s in symbols]
        url = self.MULTI_URL + "/".join(streams)

        self._running = True
        self._thread = threading.Thread(target=self._connect, args=(url,), daemon=True)
        self._thread.start()
        log.info("WS", f"WebSocket gestartet fuer {len(symbols)} Coins")
        return True

    def stop(self):
        """Stoppt den WebSocket Stream."""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        log.info("WS", "WebSocket gestoppt")

    def _connect(self, url):
        """Verbindet mit WebSocket (mit Auto-Reconnect)."""
        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                log.warn("WS", f"Verbindung verloren: {str(e)[:40]}")

            if self._running:
                self._reconnect_count += 1
                wait = min(5 * self._reconnect_count, 60)
                log.info("WS", f"Reconnect #{self._reconnect_count} in {wait}s...")
                time.sleep(wait)

    def _on_open(self, ws):
        self._reconnect_count = 0
        log.info("WS", "Verbunden!")

    def _on_message(self, ws, message):
        """Verarbeitet eingehende Preis-Updates."""
        try:
            data = json.loads(message)

            # Multi-Stream Format
            if "stream" in data:
                data = data.get("data", {})

            symbol_raw = data.get("s", "")  # z.B. "BTCUSDC"
            if not symbol_raw:
                return

            # In unser Format umwandeln
            # BTCUSDC -> BTC/USDC
            for quote in ["USDC", "USDT", "USD"]:
                if symbol_raw.endswith(quote):
                    base = symbol_raw[:-len(quote)]
                    symbol = f"{base}/{quote}"
                    break
            else:
                symbol = symbol_raw

            price = float(data.get("c", 0))  # Current price
            volume = float(data.get("v", 0))  # 24h volume
            change_pct = float(data.get("P", 0))  # 24h change %

            if price > 0:
                self.prices[symbol] = price
                self.volumes[symbol] = volume
                self.changes[symbol] = change_pct
                self._last_update = time.time()
                self._message_count += 1

                # Callbacks aufrufen
                for cb in self.callbacks:
                    try:
                        cb(symbol, price, change_pct, volume)
                    except Exception:
                        pass

        except Exception as e:
            if self._message_count == 0:
                log.warn("WS", f"Parse: {str(e)[:40]}")

    def _on_error(self, ws, error):
        log.warn("WS", f"Error: {str(error)[:60]}")

    def _on_close(self, ws, close_status, close_msg):
        log.info("WS", f"Geschlossen: {close_status}")

    def on_price_update(self, callback: Callable):
        """Registriert Callback fuer Preis-Updates: fn(symbol, price, change, volume)."""
        self.callbacks.append(callback)

    def get_price(self, symbol) -> float:
        """Aktueller Preis aus dem Stream."""
        return self.prices.get(symbol, 0)

    def get_all_prices(self) -> Dict[str, float]:
        """Alle aktuellen Preise."""
        return dict(self.prices)

    def get_ticker(self, symbol) -> Dict:
        """Ticker-Daten (wie ccxt format)."""
        return {
            "last": self.prices.get(symbol, 0),
            "percentage": self.changes.get(symbol, 0),
            "baseVolume": self.volumes.get(symbol, 0),
        }

    def is_connected(self) -> bool:
        """Ist der WebSocket verbunden?"""
        return self._running and (time.time() - self._last_update) < 30

    def get_status(self) -> Dict:
        return {
            "connected": self.is_connected(),
            "coins": len(self.prices),
            "messages": self._message_count,
            "reconnects": self._reconnect_count,
            "last_update_sec": int(time.time() - self._last_update) if self._last_update else -1,
            "available": HAS_WS,
        }
