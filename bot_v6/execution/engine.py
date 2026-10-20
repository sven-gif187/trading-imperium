"""Trading Imperium V5 – Execution Engine. Nutzt separate Module."""
import time, ccxt, os, sys, json
from typing import Dict
from core.events import DecisionIntent, ExecutionResult, Side
from core.logger import log
from core.exceptions import *
from execution.retry_policy import RetryPolicy
from execution.circuit_breaker import CircuitBreaker
from execution.idempotency import IdempotencyGuard
from execution.order_manager import OrderManager
from execution.fill_reconciler import FillReconciler

class ExecutionEngine:
    def __init__(self, config):
        self.config = config
        self.exchange = None
        self.multi_exchange = None
        self.circuit = CircuitBreaker(fail_threshold=config.exchange.max_retries+2, reset_timeout=60)
        self.retry = RetryPolicy(max_retries=config.exchange.max_retries)
        self.idempotency = IdempotencyGuard()
        self.order_manager = OrderManager()
        self.fill_reconciler = FillReconciler(self.order_manager)
        # === BUGFIX LIVE-SAFETY ===
        try:
            from features.safety import CashReservation, RateLimitTracker, RejectionCounter
            self.cash_reservation = CashReservation(timeout_sec=60)
            self.rate_limit = RateLimitTracker(limit_per_minute=1000)
            self.rejection_counter = RejectionCounter(max_in_row=10, sleep_duration_sec=900)
        except Exception as _e:
            log.warn("EXEC", f"Safety-Module Init-Fehler: {_e}")
            self.cash_reservation = None
            self.rate_limit = None
            self.rejection_counter = None
        # === ENDE LIVE-SAFETY ===
        self._paper_mode = config.trading.mode == "paper"
        self._paper_balances = {"USDC": config.trading.initial_paper_balance}
        self._paper_entries = {}
        self._init_exchange()

    def set_paper_balance(self, usdc_amount):
        """Setzt Paper-Balance auf einen bestimmten Betrag. Loescht alle Coins."""
        self._paper_balances = {"USDC": usdc_amount}
        self._paper_entries.clear()
        log.info("EXEC", f"Paper-Balance gesetzt: {usdc_amount:.2f} USDC")

    # ================================================================
    # [E10-LIVE 29.07.2026] SICHERUNGEN VOR DEM ECHTGELD-BETRIEB
    # ----------------------------------------------------------------
    # Der Wechsel auf Live ist die einzige Entscheidung im ganzen System,
    # die man nicht zurueckdrehen kann. Bis hierher genuegte dafuer ein
    # geaendertes Wort in config.json ("paper" -> "live"). Ab jetzt muss
    # der Bot vorher drei Fragen mit Ja beantworten:
    #   1. Traegt die Statistik das ueberhaupt?  (go_live_check.py)
    #   2. Kann der Schluessel Geld abheben?     (dann sofort Stopp)
    #   3. Sind Order- und Kapitaldeckel gesetzt?
    # Faellt eine Pruefung durch, faellt der Bot auf Papier zurueck und
    # sagt laut, warum. Er handelt NICHT einfach trotzdem.
    # ================================================================
    def _gate_bestanden(self) -> tuple:
        """Ruft go_live_check.py auf. (bestanden, begruendung)"""
        try:
            import subprocess
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            skript = os.path.join(root, "go_live_check.py")
            if not os.path.isfile(skript):
                return False, "go_live_check.py nicht gefunden"
            r = subprocess.run([sys.executable, skript, "--json"],
                               capture_output=True, text=True, timeout=120, cwd=root)
            daten = json.loads(r.stdout or "{}")
            if daten.get("freigabe"):
                return True, "alle Kriterien erfuellt"
            fehl = [p["kuerzel"] for p in daten.get("pruefungen", [])
                    if p.get("bestanden") is False]
            return False, "nicht erfuellt: " + ", ".join(fehl)
        except Exception as e:
            return False, f"Pruefung nicht durchfuehrbar ({str(e)[:60]})"

    def _pruefe_schluessel_rechte(self) -> bool:
        """True = Schluessel ist sicher. False = darf abheben -> Abbruch.

        Binance liefert unter GET /api/v3/account die Felder canTrade,
        canWithdraw, canDeposit. Ein Schluessel mit Auszahlungsrecht hat in
        einem Handelsbot nichts verloren - wird er gestohlen, ist das Konto
        leer, nicht nur falsch gehandelt.
        """
        try:
            info = (self.exchange.fetch_balance() or {}).get("info", {}) or {}
            darf_abheben = info.get("canWithdraw")
            darf_handeln = info.get("canTrade")
            if darf_abheben is True:
                log.error("LIVE-SAFETY", "❌ API-SCHLUESSEL DARF GELD ABHEBEN (canWithdraw=true).")
                log.error("LIVE-SAFETY", "   Bei Binance unter API-Management 'Enable Withdrawals'")
                log.error("LIVE-SAFETY", "   abschalten. Kein Live-Handel mit so einem Schluessel.")
                return False
            if darf_handeln is False:
                log.error("LIVE-SAFETY", "❌ Schluessel darf nicht handeln (canTrade=false).")
                return False
            log.info("LIVE-SAFETY", f"Schluessel-Rechte ok (handeln={darf_handeln}, "
                                    f"abheben={darf_abheben})")
            return True
        except Exception as e:
            log.warn("LIVE-SAFETY", f"Rechte nicht pruefbar ({str(e)[:60]}) - "
                                    f"von Hand bei Binance kontrollieren!")
            return True      # nicht pruefbar ist kein Beweis fuer unsicher

    def _init_exchange(self):
        if self._paper_mode:
            log.info("EXEC", "Paper-Modus aktiv"); return

        # --- Sicherung 1: traegt die Statistik den Live-Betrieb? ---
        if getattr(self.config.risk, "live_require_gate", True):
            ok, grund = self._gate_bestanden()
            if not ok:
                log.error("EXEC", "=" * 62)
                log.error("EXEC", "❌ LIVE-START ABGELEHNT - Freigabe-Pruefung nicht bestanden")
                log.error("EXEC", f"   {grund}")
                log.error("EXEC", "   Vollstaendiger Bericht:  python go_live_check.py")
                log.error("EXEC", "   -> Bot laeuft weiter im PAPIER-Modus.")
                log.error("EXEC", "=" * 62)
                self._paper_mode = True
                return
            log.info("EXEC", f"Freigabe-Pruefung bestanden ({grund})")

        # Live-Modus: API-Keys aus .env laden (sichere Methode!)
        try:
            self.config.exchange.load_api_keys()
        except Exception:
            pass

        key, secret = self.config.exchange.api_key, self.config.exchange.api_secret
        if not key or not secret:
            log.error("EXEC", "❌ LIVE-MODUS aber keine API-Keys in .env!")
            log.info("EXEC", "  -> Erstelle .env Datei mit BINANCE_API_KEY und BINANCE_API_SECRET")
            log.info("EXEC", "  -> Fallback: Paper-Modus")
            self._paper_mode = True
            return
        try:
            Ex = getattr(ccxt, self.config.exchange.ccxt_id, None) or ccxt.binance
            self.exchange = Ex({"apiKey": key, "secret": secret, "enableRateLimit": True,
                "timeout": self.config.exchange.timeout_read * 1000,
                "options": {"defaultType": "spot", "adjustForTimeDifference": True, "recvWindow": 60000}})
            self.exchange.load_markets()

            # --- Sicherung 2: darf der Schluessel Geld abheben? ---
            if not self._pruefe_schluessel_rechte():
                self._paper_mode = True
                self.exchange = None
                return

            # Sicherheits-Check: Balance abrufen um API-Key zu validieren
            try:
                bal = self.exchange.fetch_balance()
                usdc = bal.get("total", {}).get("USDC", 0) + bal.get("total", {}).get("USDT", 0)
                log.info("EXEC", f"🔴 LIVE: {self.config.exchange.name} verbunden | Balance: {usdc:.2f}$")
                # --- Sicherung 3: Deckel sichtbar machen ---
                deckel = float(getattr(self.config.risk, "live_max_order_usd", 0) or 0)
                kap = float(getattr(self.config.risk, "live_max_capital_usd", 0) or 0)
                log.warn("LIVE-SAFETY", f"Order-Deckel: {deckel:.2f}$ je Order | "
                                        f"Kapital-Deckel: {'unbegrenzt' if kap <= 0 else f'{kap:.2f}$'}")
            except Exception as e:
                log.warn("EXEC", f"Balance-Check fehlgeschlagen: {str(e)[:100]}")
        except Exception as e:
            log.error("EXEC", f"Exchange-Fehler: {e}"); self._paper_mode = True

    def execute(self, intent):
        start = time.time()
        result = ExecutionResult(intent_id=intent.id, symbol=intent.symbol, side=intent.side)
        client_id = self.idempotency.create_id(intent.id, intent.symbol)
        result.client_order_id = client_id
        if not self.idempotency.check_and_lock(client_id):
            result.status = "rejected"; result.rejected_reason = "Doppelte Order"; return result
        # === BUGFIX LIVE-SAFETY: Sleep-Mode Check ===
        # [FIX 04.08.] Der Schlafmodus darf NUR Kaeufe bremsen, niemals
        # Verkaeufe. Vorher blockierte er jede Order - am 03.08.2026 um
        # 12:32:56 und 12:32:57 traf es zweimal hintereinander einen
        # NOTAUS-NETZ-Stop auf ETH/USDC bei -3,5 % ("Order nicht gefuellt:
        # rejected | Sleep-Mode (676s remaining)"), obwohl risk/engine.py:81-86
        # den Verkauf ausdruecklich genehmigt hatte ("SELLS IMMER genehmigen!
        # Nie Verkauf blockieren!"). Ein zweites Gate hob die Zusage des
        # ersten auf. Gleiche Bedingung wie risk/engine.py:88.
        if (intent.side == Side.BUY
                and self.rejection_counter is not None
                and self.rejection_counter.is_sleeping()):
            remaining = self.rejection_counter.remaining_sleep_sec()
            result.status = "rejected"
            result.rejected_reason = f"Sleep-Mode ({remaining}s remaining)"
            self.idempotency.release(client_id)
            return result
        # === BUGFIX LIVE-SAFETY: Cash-Reservation ===
        _cash_reserved = False
        if (self.cash_reservation is not None and
                hasattr(intent.side, "value") and intent.side.value == "BUY"):
            try:
                bal = self._paper_balances if self._paper_mode else (self.get_balance().get("total", {}) or {})
                _current_cash = bal.get("USDC", 0) + bal.get("USDT", 0)
                _cash_reserved = self.cash_reservation.reserve(
                    client_id, intent.amount_usd, _current_cash)
                if not _cash_reserved:
                    result.status = "rejected"
                    result.rejected_reason = f"Cash-Reservation abgelehnt (parallele Orders)"
                    if self.rejection_counter is not None:
                        self.rejection_counter.increment("cash-reserve-fail")
                    self.idempotency.release(client_id)
                    return result
            except Exception as _e:
                # Bei Fehler: lass Cash-Reservation aus, fahre fort
                log.warn("EXEC", f"Cash-Reserve-Check Fehler: {_e}")
        # === ENDE LIVE-SAFETY ===
        self.order_manager.place(client_id, intent.symbol, intent.side.value, intent.amount_usd, intent.strategy_id, intent.entry_reason)
        try:
            if self._paper_mode:
                result = self._execute_paper(intent, result)
            else:
                result = self._execute_live(intent, result)
            result.latency_ms = int((time.time() - start) * 1000)
            if result.status == "filled":
                self.order_manager.update_fill(client_id, result.order_id or "", result.avg_fill_price, result.filled_qty, result.fee or 0)
                self.idempotency.confirm(client_id, result.order_id or "")
                log.trade("EXEC", f"{intent.side.value} {intent.symbol}: {result.filled_qty:.6f} @ {result.avg_fill_price:,.2f}$ ({result.latency_ms}ms)")
            else:
                self.order_manager.update_rejected(client_id, result.rejected_reason or "?")
        except Exception as e:
            result.status = "error"; result.error = str(e)[:200]
            self.order_manager.update_error(client_id, str(e))
            log.error("EXEC", f"Order fehlgeschlagen: {e}")
        finally:
            self.idempotency.release(client_id)
            # === BUGFIX LIVE-SAFETY: Cash-Reservation freigeben ===
            if _cash_reserved and self.cash_reservation is not None:
                try:
                    self.cash_reservation.release(client_id)
                except Exception:
                    pass
            # Rejection-Counter updaten
            if self.rejection_counter is not None:
                try:
                    if result.status == "filled":
                        self.rejection_counter.reset()
                    elif result.status in ("rejected", "error"):
                        self.rejection_counter.increment(result.rejected_reason or result.error or "?")
                except Exception:
                    pass
        return result

    # [GEFUNDENE-PROBLEME #21] Zielboerse fuer die Gebuehren-Simulation im
    # Papier-Modus. Bewusst getrennt von config.exchange.ccxt_id (= Datenquelle
    # fuer Kurse). Ueber config.trading.paper_gebuehr_boerse ueberschreibbar.
    # [KOSTENLATTE BITVAVO 14.10.2026] Zielboerse Bitvavo USDC (0,05 % je Seite). Vorher "bybit" (0,25 %).
    PAPER_GEBUEHR_BOERSE = "bitvavo_usdc"

    # [GEFUNDENE-PROBLEME #23, 12.08.2026] Gemessene Spreads je Muenze.
    #
    # Vorher stand im Papier-Pfad fuer JEDE Muenze dasselbe:
    #     slippage_pct = random.uniform(0.02, 0.08) / 100
    # Also 0,02-0,08 % Schlupf, egal ob BTC oder DOT. Am echten Bybit-EU-
    # Orderbuch gemessen (145-148 Messpunkte je Muenze, 31.07.2026,
    # docs/forschungsprogramm_2026-07/12_SPREAD-MESSUNG.md) liegt der
    # Median-Spread zwischen 0,054 bp (ETH) und 65,232 bp (DOT) -
    # Faktor 1208. Die alte Annahme war fuer BTC/ETH also rund 100-fach zu
    # PESSIMISTISCH und fuer DOT/ATOM etwa fuenffach zu OPTIMISTISCH.
    #
    # Eine Market-Order zahlt gegenueber der Mitte den halben Spread:
    #     slippage_je_seite = median_spread_bp / 2 / 10000
    #
    # Werte in Basispunkten (1 bp = 0,01 %), (median, p90):
    SPREAD_BP = {
        # [KOSTENLATTE BITVAVO 14.10.2026] BTC/ETH/SOL aus der Bitvavo-Stichprobe 2026-10-14T13:50 UTC, 120 Proben je Muenze
        # (pruefstand/berichte/2026-10-14_spanne_bitvavo.json). Vorher Bybit EU 31.07.:
        # ETH (0.054, 5.007), BTC (0.118, 4.319), SOL (1.366, 2.742). Uebrige Muenzen
        # handelt der Bot nicht; sie behalten die Bybit-Werte.
        "ETH":  (4.265, 5.149),
        "BTC":  (2.779, 4.351),
        "SOL":  (5.724, 8.118),
        "DOGE": (1.441,  4.317),
        "ADA":  (5.954, 17.610),
        "XRP":  (6.591, 11.182),
        "LINK": (12.105, 14.533),
        "AVAX": (12.372, 17.207),
        "UNI":  (16.519, 30.118),
        "NEAR": (18.276, 26.680),
        "ATOM": (56.887, 64.746),
        "DOT":  (65.232, 66.094),
    }
    # Unbekannte Muenze: der schlechteste gemessene Wert. Lieber zu teuer
    # rechnen als ein Papier-Ergebnis, das die Wirklichkeit schoenrechnet.
    SPREAD_UNBEKANNT = (65.232, 79.470)

    def _paper_slippage(self, symbol, random_modul):
        """Schlupf je Seite als Anteil (0.0001 = 0,01 %).

        In 10 % der Faelle wird der p90-Wert genommen statt des Medians -
        genau das bedeutet p90: jeder zehnte Spread ist so weit oder weiter.
        Ohne diesen Anteil waere die Simulation zu glatt; die Messung zeigt
        bei BTC einen Median von 0,118 bp, aber ein p90 von 4,319 bp - der
        Ausreisser ist das 37-Fache.
        """
        try:
            basis = str(symbol).split("/")[0].upper()
            median_bp, p90_bp = self.SPREAD_BP.get(basis, self.SPREAD_UNBEKANNT)
            bp = p90_bp if random_modul.random() < 0.10 else median_bp
            return (bp / 2.0) / 10000.0
        except Exception:
            # Im Zweifel der teuerste gemessene Wert
            return (self.SPREAD_UNBEKANNT[0] / 2.0) / 10000.0

    def _paper_gebuehr(self):
        """Taker-Gebuehr der Zielboerse als Anteil (0.0025 = 0,25 %).

        Der Bot stellt nur Market-Orders, ist also immer Taker. Faellt die
        Tabelle aus, wird der teurere Bybit-EU-Wert genommen - eine zu
        guenstige Annahme laesst jede Auswertung besser aussehen als die
        Wirklichkeit, und zwar still. Im Zweifel lieber zu teuer rechnen.
        """
        try:
            from backtest.fees import EXCHANGE_FEES
            boerse = getattr(self.config.trading, "paper_gebuehr_boerse",
                             self.PAPER_GEBUEHR_BOERSE)
            return float(EXCHANGE_FEES[boerse]["taker"]) / 100.0
        except Exception:
            return 0.0025          # Bybit EU Taker, geprueft 08.03.2026

    def _execute_paper(self, intent, result):
        price = intent.entry_price
        if price <= 0:
            result.status = "rejected"; result.rejected_reason = "Kein Preis"; return result

        # === REALISTISCHE SIMULATION ===
        # 1. Slippage je Muenze aus der Messung, nicht geraten.
        #    [GEFUNDENE-PROBLEME #23] Siehe _paper_slippage().
        import random
        slippage_pct = self._paper_slippage(intent.symbol, random)
        if intent.side == Side.BUY:
            price = price * (1 + slippage_pct)  # Kaufpreis etwas hoeher
        else:
            price = price * (1 - slippage_pct)  # Verkaufpreis etwas niedriger

        # 2. Gebuehren der ZIELBOERSE, nicht der Datenquelle.
        #
        # [GEFUNDENE-PROBLEME #21, 11.08.2026] Hier stand fest verdrahtet
        # fee_rate = 0.001 mit dem Kommentar "0.10% Standard Binance".
        # Gehandelt wird aber kuenftig auf Bybit EU (MiCA-lizenziert, alte
        # Entscheidung, siehe docs/forschungsprogramm_2026-07/). Dort kostet
        # eine TAKER-Order 0,25 % je Seite - vom Eigentuemer selbst auf der
        # offiziellen Gebuehrenseite geprueft. Der Bot stellt ausschliesslich
        # Market-Orders, ist also immer Taker.
        #
        # Das Papier-Trading rechnete damit 2,5-mal zu billig. Genau davor
        # warnt Migrationsrisiko 3 in 01_IST-ZUSTAND.md: eine harte fee_rate
        # entkoppelt Papier von der echten Kostenstruktur der Zielboerse -
        # und alles, was der Bot daraus lernt, faellt zu optimistisch aus.
        #
        # WICHTIG: Das ist bewusst NICHT an config.exchange.ccxt_id gekoppelt.
        # Die Kurse kommen weiterhin von Binance (Datenquelle), gehandelt wird
        # spaeter bei Bybit (Zielboerse). Zwei verschiedene Dinge.
        # NIE aus ccxt-Metadaten holen: ccxt.bybit().fees meldet 0,075 % Taker,
        # was fuer EU-Spot falsch ist.
        fee_rate = self._paper_gebuehr()

        if intent.side == Side.BUY:
            amount = intent.amount_usd
            fee = amount * fee_rate
            qty = (amount - fee) / price
            asset = intent.symbol.split("/")[0]
            avail = self._paper_balances.get("USDC", 0) + self._paper_balances.get("USDT", 0)
            if avail < amount:
                result.status = "rejected"; result.rejected_reason = f"Balance: {avail:.2f}$"; return result
            remaining = amount
            for q in ["USDC", "USDT"]:
                take = min(self._paper_balances.get(q, 0), remaining)
                self._paper_balances[q] = self._paper_balances.get(q, 0) - take; remaining -= take
                if remaining <= 0: break
            # [FIX 05.08.2026] GEKAUFTE MENGE EINBUCHEN.
            # Diese Zeile fehlte. USDC wurde oben abgezogen, der Einstand
            # unten gesetzt - aber _paper_balances[asset] wurde NIE erhoeht.
            # Im ganzen Modul gab es nur Stellen, die den Asset-Bestand
            # verringern (:318) oder loeschen (:320). Folgen, alle belegt:
            #   1. Jede gekaufte Position hatte Bestand 0 -> WAECHTER-ALARM
            #      "POSITION GROESSER ALS BESTAND ... Buecher widersprechen
            #      sich" (05.08. 03:21:50 BTC, 03:21:52 ETH).
            #   2. Jeder Verkauf scheiterte am Phantom-Schutz (:302-306),
            #      z. B. 05.08. 01:58:02 ADA bei +19,37 % Trailing-Stop:
            #      "SELL abgelehnt - Bestand 0, angefordert 320.779720".
            #   3. 10 Rejects in Folge -> "Bot pausiert 15 Min". Das ist die
            #      Quelle der 7.598 Sleep-Mode-Zeilen im 24-Stunden-Log.
            #   4. _alt_qty unten war dadurch immer negativ, die E9-Mittelung
            #      (29.07.) konnte nie greifen - der Einstand wurde bei jedem
            #      Nachkauf ueberschrieben statt gemittelt.
            # Die Erhoehung steht bewusst VOR _alt_qty: dort wird der ALTE
            # Bestand als "neuer Bestand minus qty" zurueckgerechnet.
            self._paper_balances[asset] = (
                self._paper_balances.get(asset, 0) + qty)

            # [E9-FIX 29.07.] Einstand beim Nachkauf MENGENGEWICHTET mitteln.
            # Vorher wurde er schlicht ueberschrieben - nach jedem DCA-Nachkauf
            # rechnete der Paper-Verkauf die GESAMTE Menge gegen den Preis der
            # LETZTEN Tranche. Bei einer gemittelten Position ist das reine
            # Fantasie (im Log stand ein Netto-Ergebnis, das es nie gab).
            _alt_qty = self._paper_balances.get(asset, 0) - qty
            _alt_entry = self._paper_entries.get(intent.symbol, 0)
            if _alt_qty > 1e-12 and _alt_entry > 0:
                self._paper_entries[intent.symbol] = (
                    (_alt_entry * _alt_qty + price * qty) / (_alt_qty + qty))
            else:
                self._paper_entries[intent.symbol] = price  # Entry-Preis MIT Slippage
            result.avg_fill_price = round(price, 8); result.filled_qty = qty
            # [BEFUND 42, behoben 14.10.2026 - Epoche E9, aus dem Pruefstand]
            # filled_cost OHNE Gebuehr, wortgleich mit v7 (engine.py:551, 11.09.2026).
            # Vorher stand hier "result.filled_cost = amount". In amount steckt
            # die Kaufgebuehr schon (oben: fee = amount * fee_rate,
            # qty = (amount - fee) / price). app.py:1896 und :3085 rechnen
            # danach cost_basis = filled_cost + fee - also ein ZWEITES Mal.
            # E7: 115 von 136 Runden betroffen, 45,91 $ zu schlecht gebucht.
            # amount - fee ist genau qty * price - dasselbe, was ccxt im
            # Livepfad als "cost" liefert (:546). filled_cost + fee ist jetzt
            # in beiden Wegen der echte Mittelabfluss. Livepfad unberuehrt.
            result.filled_cost = amount - fee; result.fee = round(fee, 4); result.status = "filled"
            result.slippage_pct = round(slippage_pct * 100, 4)

        elif intent.side == Side.SELL:
            asset = intent.symbol.split("/")[0]
            qty = intent.quantity or self._paper_balances.get(asset, 0)
            if qty <= 0:
                result.status = "rejected"; result.rejected_reason = f"Kein {asset}"; return result
            # === PHANTOM-VERKAUF-SCHUTZ ===
            # Nie mehr verkaufen als wirklich im Bestand ist (sonst bucht ein
            # Geister-Verkauf nach Neustart vollen Phantom-Gewinn -> Buecher kaputt).
            _held = self._paper_balances.get(asset, 0)
            if qty > _held:
                if _held <= 1e-10:
                    result.status = "rejected"
                    result.rejected_reason = f"Phantom-Verkauf verhindert: kein {asset} im Bestand"
                    log.warn("PAPER", f"SELL {intent.symbol} abgelehnt - Bestand 0, angefordert {qty:.6f} (Geister-Position?)")
                    return result
                log.warn("PAPER", f"SELL {intent.symbol}: Menge auf echten Bestand gekappt {qty:.6f} -> {_held:.6f}")
                qty = _held
            # === ENDE PHANTOM-VERKAUF-SCHUTZ ===
            revenue = qty * price  # Preis NACH Slippage (niedriger)
            fee = revenue * fee_rate
            net = revenue - fee
            # P&L berechnen (gegen Entry-Preis mit dessen Slippage)
            entry = self._paper_entries.get(intent.symbol, price)
            entry_cost = qty * entry
            pnl = net - entry_cost
            self._paper_balances[asset] = max(0, self._paper_balances.get(asset, 0) - qty)
            if self._paper_balances.get(asset, 0) < 1e-10 and asset in self._paper_balances:
                del self._paper_balances[asset]
            self._paper_balances["USDC"] = self._paper_balances.get("USDC", 0) + net
            if intent.symbol in self._paper_entries:
                del self._paper_entries[intent.symbol]
            result.avg_fill_price = round(price, 8); result.filled_qty = qty
            result.filled_cost = round(net, 4); result.fee = round(fee, 4)
            result.pnl = round(pnl, 4); result.status = "filled"
            result.slippage_pct = round(slippage_pct * 100, 4)
            log.info("PAPER", f"SELL {intent.symbol}: Netto {net:.2f}$ (Fee: {fee:.2f}$, Slip: {slippage_pct*100:.3f}%)")

        return result

    def _execute_live(self, intent, result):
        # Multi-Exchange: Besten Preis finden
        best_exchange = self.exchange
        if self.multi_exchange and len(self.multi_exchange.exchanges) > 1:
            try:
                best = self.multi_exchange.get_best_price(intent.symbol, "buy" if intent.side == Side.BUY else "sell")
                best_ex_name = best.get("best_exchange", "")
                if best_ex_name in self.multi_exchange.exchanges:
                    # Nur nutzen wenn API-Keys vorhanden
                    ex = self.multi_exchange.exchanges[best_ex_name]
                    if hasattr(ex, 'apiKey') and ex.apiKey:
                        best_exchange = ex
                        log.info("EXEC", f"Multi-Exchange: {best_ex_name} ({best.get('price', 0):,.2f}$)")
            except Exception:
                pass

        # ================================================================
        # [E9-LIVE 29.07.] AUSFUEHRUNGS-PRUEFUNG
        # Vorher stand hier bedingungslos result.status = "filled" - egal
        # was die Boerse zurueckgab. Eine abgelehnte Order, eine Teil-
        # ausfuehrung oder ein leeres Dict wurden als Vollausfuehrung ins
        # Journal und in open_positions gebucht. Im Paper-Modus wirkungslos,
        # im Live-Modus zerstoert das die Buchhaltung mit dem ersten Trade:
        # der Bot fuehrt eine Position, die es nicht (oder nicht in der
        # Groesse) gibt, und der Exit-Monitor verkauft spaeter ins Leere.
        # ================================================================
        if intent.entry_price is None or intent.entry_price <= 0:
            result.status = "rejected"
            result.rejected_reason = "Kein Referenzpreis fuer Live-Order"
            return result

        # [E10-LIVE] Harter Order-Deckel. Das Sizing rechnet prozentual und
        # laeuft ueber mehrere Module (Modus, Adaptive, NUPL, DXY, Exposure) -
        # ein Rechenfehler in einem davon darf im Echtgeld-Betrieb nicht das
        # halbe Konto in eine Order kippen. Fangnetz, keine Strategie.
        _deckel = float(getattr(self.config.risk, "live_max_order_usd", 0) or 0)
        if _deckel > 0 and intent.side == Side.BUY and intent.amount_usd > _deckel:
            log.warn("LIVE-SAFETY", f"{intent.symbol}: Order {intent.amount_usd:.2f}$ "
                                    f"auf Deckel {_deckel:.2f}$ gekuerzt")
            intent.amount_usd = _deckel

        def _menge():
            """Menge boersenkonform runden (Lot-Size/Precision)."""
            if intent.side == Side.BUY:
                roh = intent.amount_usd / intent.entry_price
            else:
                roh = intent.quantity or 0
            try:
                # ccxt kennt die Praezision des Marktes - manuelles round(x, 6)
                # verletzt bei vielen Paaren die Lot-Size und wird abgelehnt.
                return float(best_exchange.amount_to_precision(intent.symbol, roh))
            except Exception:
                return round(roh, 6)

        menge = _menge()
        if menge <= 0:
            result.status = "rejected"
            result.rejected_reason = f"Menge nach Rundung 0 ({intent.symbol})"
            return result

        def _do():
            if intent.side == Side.BUY:
                return best_exchange.create_market_buy_order(intent.symbol, menge)
            return best_exchange.create_market_sell_order(intent.symbol, menge)

        order = self.retry.execute(lambda: self.circuit.call(_do)) or {}

        result.order_id = order.get("id", "") or ""

        # --- Menge: was wurde WIRKLICH gefuellt? ---
        try:
            filled = float(order.get("filled") or 0)
        except Exception:
            filled = 0.0

        # --- Preis: average, sonst price, sonst cost/filled ---
        preis = order.get("average") or order.get("price") or 0
        try:
            preis = float(preis or 0)
        except Exception:
            preis = 0.0
        try:
            kosten = float(order.get("cost") or 0)
        except Exception:
            kosten = 0.0
        if preis <= 0 and filled > 0 and kosten > 0:
            preis = kosten / filled

        # --- Gebuehr: ccxt liefert fee=None, fee={} oder fees=[{...}] ---
        gebuehr = 0.0
        try:
            f = order.get("fee")
            if isinstance(f, dict):
                gebuehr = float(f.get("cost") or 0)
            if gebuehr <= 0:
                for f2 in (order.get("fees") or []):
                    if isinstance(f2, dict):
                        gebuehr += float(f2.get("cost") or 0)
        except Exception:
            gebuehr = 0.0

        result.avg_fill_price = preis
        result.filled_qty = filled
        result.filled_cost = kosten if kosten > 0 else filled * preis
        result.fee = gebuehr

        status_boerse = str(order.get("status") or "").lower()

        if filled <= 0 or preis <= 0:
            result.status = "rejected"
            result.rejected_reason = (f"Boerse meldet keine Ausfuehrung "
                                      f"(status={status_boerse or '?'}, filled={filled}, preis={preis})")
            log.error("EXEC", f"{intent.symbol}: Order NICHT gefuellt - {result.rejected_reason}")
            return result

        # Teilausfuehrung: als 'filled' buchen, ABER mit der echten Menge und
        # sichtbar im Log. Der Aufrufer schreibt result.filled_qty in die
        # Position - damit stimmt das Register mit der Boerse ueberein.
        if menge > 0 and filled < menge * 0.995:
            log.warn("EXEC", f"{intent.symbol}: TEILAUSFUEHRUNG {filled:.8f} von "
                             f"{menge:.8f} ({filled/menge*100:.1f}%) - "
                             f"Position wird mit der ECHTEN Menge gefuehrt")
            result.partial = True

        result.status = "filled"
        return result

    def set_multi_exchange(self, multi_ex):
        """Setzt den Multi-Exchange Manager."""
        self.multi_exchange = multi_ex

    def reconcile(self):
        if self._paper_mode or not self.exchange: return []
        try:
            return self.fill_reconciler.reconcile(self.exchange.fetch_open_orders(), self.exchange.fetch_my_trades(limit=20))
        except Exception as e: log.error("EXEC", f"Reconcile: {e}"); return []

    def get_balance(self):
        """Holt Balance. Paper: aus internem Speicher. Live: von Binance API.

        Live-Mode: Holt IMMER frisch von der Boerse (kein Caching)
        damit das Sizing immer auf der echten aktuellen Balance basiert!
        """
        if self._paper_mode:
            return {"total": dict(self._paper_balances), "free": dict(self._paper_balances)}

        # LIVE-MODE: Frisch von Binance holen
        try:
            balance = self.retry.execute(
                lambda: self.circuit.call(
                    lambda: self.exchange.fetch_balance()))
            # Validierung: Muss "total" Dict haben
            if not balance or "total" not in balance:
                log.warn("EXEC", "Live-Balance ungueltig - leeres Dict zurueck")
                return {"total": {}, "free": {}}
            return balance
        except Exception as e:
            log.error("EXEC", f"Live-Balance Fehler: {str(e)[:100]}")
            return {"total": {}, "free": {}}

    def get_price(self, symbol, data_client=None):
        # Multi-Exchange Preis
        if self.multi_exchange:
            try:
                best = self.multi_exchange.get_best_price(symbol, "buy")
                if best.get("price", 0) > 0:
                    return best["price"]
            except Exception:
                pass
        c = data_client or self.exchange
        if not c: return 0.0
        try: return c.fetch_ticker(symbol)["last"]
        except: return 0.0

    def get_status(self):
        me_status = self.multi_exchange.get_status() if self.multi_exchange else {}
        return {"mode": "paper" if self._paper_mode else "live", "circuit": self.circuit.get_status(),
                "retry": self.retry.get_status(), "idempotency": self.idempotency.get_status(),
                "orders": self.order_manager.get_stats(), "reconciler": self.fill_reconciler.get_status(),
                "multi_exchange": me_status}
