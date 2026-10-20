"""
Waechter-Agent - Buchhaltungs-Pruefer von Trading Imperium V6

Prueft zyklisch (alle 5 Min) Invarianten, die IMMER stimmen muessen:
  1. Keine Position groesser als der tatsaechliche Coin-Bestand
     (haette den 70$-SOL-Vorfall vom 12.06. sofort gemeldet)
  2. Kein nennenswerter Coin-Bestand OHNE zugehoerige Position
     ("Geisterbestand" - Coins, die niemand ueberwacht)
  3. USDC niemals negativ
Bei Verstoss: Log-Alarm + Telegram-Nachricht (max. 1x pro Stunde
pro Problem, damit das Handy nicht explodiert).

Liest NUR - greift nie in Trading, Positionen oder Balance ein.
"""
import time
import threading

try:
    from core.logger import log
except Exception:
    class _Log:
        def info(self, *a): pass
        def warn(self, *a): pass
        def error(self, *a): pass
    log = _Log()

CHECK_INTERVAL = 300      # alle 5 Minuten
FIRST_DELAY = 120         # erste Pruefung 2 Min nach Start (Bot soll erst hochfahren)
QTY_TOLERANZ = 1.02       # 2% Toleranz (Rundungen, Gebuehren-Reste)
GEIST_MIN_USD = 30.0      # Geisterbestaende unter 30$ ignorieren (z.B. BTC-Tresor)
ALARM_COOLDOWN = 3600     # gleicher Alarm max. 1x pro Stunde


class Waechter:
    def __init__(self, engine):
        self.engine = engine
        self._last_alarm = {}   # problem_key -> timestamp

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True, name="waechter")
        t.start()
        log.info("WAECHTER", "Buchhaltungs-Pruefer gestartet (alle 5 Min)")

    # ------------------------------------------------------------------
    def _loop(self):
        time.sleep(FIRST_DELAY)
        while True:
            try:
                probleme = self.pruefe()
                if probleme:
                    for p in probleme:
                        self._alarm(p)
                else:
                    log.info("WAECHTER", "Buecher-Check OK")
            except Exception as e:
                log.warn("WAECHTER", "Pruef-Fehler: " + str(e)[:100])
            time.sleep(CHECK_INTERVAL)

    # ------------------------------------------------------------------
    def pruefe(self) -> list:
        """Fuehrt alle Invarianten-Checks aus, gibt Problemliste zurueck."""
        e = self.engine
        probleme = []

        balances = (e.execution.get_balance() or {}).get("total", {})
        positions = {s: p for s, p in e.risk_engine.open_positions.items()
                     if p.get("active")}
        prices = getattr(e.data_agent, "price_cache", {}) or {}

        # Check 1+2: Position vs. Bestand je Coin
        pos_coins = {}
        for sym, p in positions.items():
            coin = sym.split("/")[0]
            pos_coins[coin] = pos_coins.get(coin, 0.0) + float(p.get("qty", 0))

        for coin, pos_qty in pos_coins.items():
            bal_qty = float(balances.get(coin, 0))
            if pos_qty > bal_qty * QTY_TOLERANZ + 1e-9:
                probleme.append(
                    f"POSITION GROESSER ALS BESTAND: {coin} Position "
                    f"{pos_qty:.6f}, Bestand nur {bal_qty:.6f} - "
                    f"Buecher widersprechen sich!")

        for coin, bal_qty in balances.items():
            if coin in ("USDC", "USDT", "EUR", "USD"):
                continue
            bal_qty = float(bal_qty)
            pos_qty = pos_coins.get(coin, 0.0)
            diff = bal_qty - pos_qty
            if diff <= 0:
                continue
            price = float(prices.get(f"{coin}/USDC", 0))
            wert = diff * price
            if wert > GEIST_MIN_USD:
                probleme.append(
                    f"GEISTERBESTAND: {diff:.6f} {coin} (~{wert:.2f}$) im "
                    f"Bestand, aber keine Position dazu - wird von keinem "
                    f"Stop-Loss ueberwacht!")

        # Check 3: USDC nie negativ
        usdc = float(balances.get("USDC", 0))
        if usdc < -0.01:
            probleme.append(f"USDC NEGATIV: {usdc:.2f}$ - Buchungsfehler!")

        # (Frueherer Check 4 entfernt: verglich das tote State-Feld
        #  realized_pnl gegen das Journal und loeste Dauer-Fehlalarm aus.
        #  Counter-Sync haelt die Felder jetzt ohnehin synchron.)

        return probleme

    # ------------------------------------------------------------------
    def _alarm(self, problem: str):
        key = problem[:40]
        now = time.time()
        if now - self._last_alarm.get(key, 0) < ALARM_COOLDOWN:
            return
        self._last_alarm[key] = now
        log.error("WAECHTER", "ALARM: " + problem)
        try:
            tg = getattr(self.engine, "telegram", None)
            if tg and getattr(tg, "enabled", False):
                tg.send("\U0001F6A8 <b>WAECHTER-ALARM</b>\n" + problem)
        except Exception:
            pass
