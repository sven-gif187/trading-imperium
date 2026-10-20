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

# [BEFUND 88 WARTEKAUF 17.10.2026] Ein bedienter Warte-Auftrag baut den Kauf als NEUEN DecisionIntent
# auf (warteauftraege_pruefen, _warteauftraege_live_takt). Bisher kamen dabei nur
# strategy_id, score, confidence und entry_reason mit. stop_loss,
# trailing_stop_pct, take_profit, agent_id, risk_reason und die
# Telemetrie-Kennung der Entscheidung gingen verloren. Folge: Seit dem 12.09.
# stand stop_initial/trailing_stop_pct an JEDEM v7-Kauf leer, und der Verkauf
# konnte sie nicht erben (W4 pflichtfelder GELB, Befund 88). Nur Aufzeichnung:
# Ausfuehrung und Ausstieg lesen diese Felder nicht.
_WARTE_ZAHLEN = ("stop_loss", "take_profit", "trailing_stop_pct")
_WARTE_TEXTE = ("agent_id", "model_version", "risk_reason")


def _warte_merkangaben(intent):
    """Entscheidungs-Angaben fuer die Warteschlange. Nur einfache Typen (die
    Datei ist JSON). Wirft nie - lieber ein Feld leer als kein Auftrag."""
    aus = {}
    for _f in _WARTE_ZAHLEN + _WARTE_TEXTE:
        try:
            _v = getattr(intent, _f, None)
            if _v is None:
                continue
            aus[_f] = float(_v) if _f in _WARTE_ZAHLEN else str(_v)
        except Exception:
            pass
    try:
        _eid = getattr(intent, "_evaluation_id", "") or ""
        if _eid:
            aus["evaluation_id"] = str(_eid)
    except Exception:
        pass
    return aus


def _warte_merkangaben_zurueck(intent, ang):
    """Setzt die gemerkten Angaben am neu gebauten Kauf. Ein Auftrag von vor
    diesem Fix hat die Schluessel nicht und bleibt wie bisher. Wirft nie."""
    for _f in _WARTE_ZAHLEN + _WARTE_TEXTE:
        try:
            if ang.get(_f) is not None:
                setattr(intent, _f, ang.get(_f))
        except Exception:
            pass
    try:
        if ang.get("evaluation_id"):
            intent._evaluation_id = str(ang.get("evaluation_id"))
    except Exception:
        pass
    return intent


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
        # [WARTE-AUFTRAEGE 11.09.2026] Warteschlange fuer Limit-Kaeufe.
        # Wird IMMER geladen (damit ein beim Absturz offener Auftrag beim
        # Start aufgeraeumt wird), aber nur gefragt, wenn der Schalter in
        # data_store/config.json -> warteauftraege.aktiv auf true steht.
        # Herleitung und Messung: execution/warteauftraege.py.
        try:
            from execution.warteauftraege import Warteschlange, einstellungen_lesen
            self.warteschlange = Warteschlange(
                einstellungen=einstellungen_lesen())
            if self.warteschlange.aktiv:
                log.info("EXEC", "Warte-Auftraege AKTIV: %.2f %% Abstand, "
                                 "%d Kerzen gueltig"
                         % (self.warteschlange.einst["abstand_pct"],
                            self.warteschlange.einst["gueltig_kerzen"]))
        except Exception as _we:
            # Kein stilles Scheitern: ohne Warteschlange handelt der Bot
            # weiter wie bisher (Sofortkauf), aber es steht im Log.
            log.error("EXEC", f"Warteschlange nicht geladen: {_we}")
            self.warteschlange = None
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
            log.info("EXEC", "  -> .env anlegen mit BYBIT_API_KEY und BYBIT_API_SECRET")
            log.info("EXEC", "     (EXCHANGE_* und BINANCE_* werden auch gelesen)")
            log.info("EXEC", "  -> Fallback: Paper-Modus")
            self._paper_mode = True
            return
        try:
            # ========================================================
            # [BEFUND 69, 14.09.2026] DIE HANDELSBOERSE, NICHT DIE
            # DATENQUELLE
            # --------------------------------------------------------
            # Hier stand `self.config.exchange.ccxt_id` - dasselbe Feld,
            # aus dem auch data/market_data.py:17 die KURSE holt. Ein
            # Feld fuer zwei verschiedene Dinge. Wer es auf bybit
            # stellte, um dort zu handeln, verlegte damit zugleich die
            # Kursquelle und aenderte den laufenden Papierhandel.
            #
            # Jetzt eigene Felder: `handel_ccxt_id` und
            # `handel_hostname`. Die Kurse bleiben, wo sie waren.
            #
            # DER HOSTNAME IST DER ENTSCHEIDENDE TEIL. ccxt kennt nur
            # EINE Bybit-Anbindung und die zeigt fest auf bybit.com -
            # am 14.09. nachgemessen. Bybit EU ist eine andere
            # Plattform (MiCA-lizenziert, eigene EUR-Paare). Ohne diese
            # Zeile landet jede Live-Order auf bybit.com, also auf der
            # Boerse, auf der ausdruecklich NICHT gehandelt werden soll.
            # ========================================================
            _ziel = (getattr(self.config.exchange, "handel_ccxt_id", "")
                     or self.config.exchange.ccxt_id)
            _host = getattr(self.config.exchange, "handel_hostname", "") or ""
            Ex = getattr(ccxt, _ziel, None) or ccxt.bybit
            # [14.09.2026] "unified" statt "spot" bei Bybit EU.
            #
            # Bybit EU kennt nur EIN Konto: UNIFIED. Eine Abfrage mit
            # defaultType "spot" antwortet dort woertlich mit
            #     "accountType only support UNIFIED"
            # und liefert einen leeren Kontostand - obwohl Geld da ist.
            #
            # Am 14.09. genau so passiert: Sven hatte 36,25 USDC
            # eingezahlt, der Bot meldete 0,00. Der Fehler sah aus wie
            # eine fehlende Einzahlung und war einer im Abruf.
            #
            # Fuer andere Boersen bleibt "spot" richtig, deshalb die
            # Fallunterscheidung statt eines pauschalen Wechsels.
            _kontoart = "unified" if "bybit" in str(_ziel).lower() else "spot"
            _einst = {"apiKey": key, "secret": secret, "enableRateLimit": True,
                "timeout": self.config.exchange.timeout_read * 1000,
                "options": {"defaultType": _kontoart,
                            "adjustForTimeDifference": True, "recvWindow": 60000}}
            if _host:
                _einst["hostname"] = _host
            self.exchange = Ex(_einst)
            log.info("EXEC", "Handelsboerse: %s%s (Kurse kommen weiter von %s)"
                     % (_ziel, " / " + _host if _host else "",
                        self.config.exchange.ccxt_id))
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
            elif result.status == "wartet":
                # [WARTE-AUFTRAEGE 11.09.2026] Ein hingelegter Auftrag ist
                # weder gefuellt noch abgelehnt - er wartet. Ohne diesen
                # Zweig liefe er in update_rejected() und stuende in der
                # Order-Historie als Ablehnung, obwohl er noch lebt. Die
                # Buchung uebernimmt spaeter warteauftraege_pruefen(),
                # sobald er bedient wird oder verfaellt.
                pass
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
        return self._paper_gebuehr_satz("taker")

    def _paper_gebuehr_satz(self, art="taker"):
        """Gebuehrensatz als Anteil. art ist "taker" oder "maker".

        [WARTE-AUFTRAEGE 11.09.2026] Bis hierher stellte der Bot nur
        Market-Orders und war immer Taker. Ein Warte-Auftrag (Limit) ist
        Maker: 0,10 % statt 0,25 % je Seite bei Bybit EU, belegt in
        backtest/fees.py:24. Der Unterschied von 0,15 Prozentpunkten je
        Seite ist ein Teil des gemessenen Vorteils - der groessere Teil
        kommt aus dem guenstigeren Einstiegspreis.
        """
        # [EINHEITSGEBUEHR 05.10.2026] Maker = Taker seit Bybit-EU-Einheitsgebuehr.
        rueckfall = {"taker": 0.0025, "maker": 0.0025}
        try:
            from backtest.fees import EXCHANGE_FEES
            boerse = getattr(self.config.trading, "paper_gebuehr_boerse",
                             self.PAPER_GEBUEHR_BOERSE)
            return float(EXCHANGE_FEES[boerse][art]) / 100.0
        except Exception:
            return rueckfall.get(art, 0.0025)   # Bybit EU, geprueft 08.03.2026

    def _execute_paper(self, intent, result, warte_fuellung=None):
        price = intent.entry_price
        if price <= 0:
            result.status = "rejected"; result.rejected_reason = "Kein Preis"; return result

        # ============================================================
        # [WARTE-AUFTRAEGE 11.09.2026] Zwei Abzweige, beide nur beim KAUF.
        #
        # Verkaeufe bleiben IMMER Sofort-Auftraege. Ein Stop-Loss, ein
        # Notaus oder ein Trailing-Ausstieg, der als Warte-Auftrag liegen
        # bleibt und nie bedient wird, waere genau die Art von stillem
        # Scheitern, die am 03.08. schon einmal einen NOTAUS-NETZ-Stop
        # gefressen hat (siehe Kommentar in execute()). Dasselbe steht in
        # TODO-NACH-DEM-MESSFENSTER.md: "Nie pauschal umstellen -
        # Stop-Loss, Kill-Switch und Notfall-Ausstiege muessen Market
        # bleiben."
        # ============================================================
        if (warte_fuellung is None and intent.side == Side.BUY
                and self.warteschlange is not None
                and self.warteschlange.aktiv):
            auftrag = self.warteschlange.anlegen(
                intent.symbol, price, intent.amount_usd,
                angaben={"strategy_id": getattr(intent, "strategy_id", "") or "",
                         "score": getattr(intent, "score", None),
                         "confidence": getattr(intent, "confidence", None),
                         "entry_reason": getattr(intent, "entry_reason", "") or "",
                         # [BEFUND 88 WARTEKAUF 17.10.2026] Stop, Nachzieh-Abstand usw. mitnehmen
                         **_warte_merkangaben(intent)})
            if auftrag is None:
                result.status = "rejected"
                result.rejected_reason = "Warte-Auftrag laeuft bereits"
                return result
            # NICHT "pending" - das ist der Standardwert von ExecutionResult
            # (core/events.py:134) und waere von "noch nichts passiert" nicht
            # zu unterscheiden. Ein eigener Name macht den Zustand sichtbar.
            result.status = "wartet"
            result.rejected_reason = ""
            result.avg_fill_price = auftrag["limitpreis"]
            log.info("PAPER", "Warte-Auftrag %s: Limit %.8f $ (%.2f %% unter "
                              "%.8f $), gueltig %d Minuten"
                     % (intent.symbol, auftrag["limitpreis"],
                        auftrag["abstand_pct"], auftrag["marktpreis_bei_anlage"],
                        int(self.warteschlange.gueltig_sekunden() // 60)))
            return result

        # === REALISTISCHE SIMULATION ===
        # 1. Slippage je Muenze aus der Messung, nicht geraten.
        #    [GEFUNDENE-PROBLEME #23] Siehe _paper_slippage().
        import random
        if warte_fuellung is not None:
            # Ein Warte-Auftrag wird bedient. Er bekommt GENAU seinen Preis -
            # kein Schlupf, denn Schlupf entsteht dadurch, dass eine
            # Market-Order sich durch das Orderbuch frisst. Ein Limit-Auftrag
            # liegt IM Orderbuch; wer ihn bedient, zahlt den halben Spread.
            price = float(warte_fuellung["limitpreis"])
            slippage_pct = 0.0
        else:
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
        # [WARTE-AUFTRAEGE] Ein bedienter Limit-Auftrag ist Maker (0,10 %),
        # ein Sofortkauf Taker (0,25 %). Beides aus backtest/fees.py, nie
        # aus ccxt - siehe _paper_gebuehr_satz().
        fee_rate = (self._paper_gebuehr_satz("maker") if warte_fuellung is not None
                    else self._paper_gebuehr())

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
            # [BEFUND 42, behoben 11.09.2026 - Epoche E8] filled_cost OHNE Gebuehr.
            #
            # Vorher stand hier "result.filled_cost = amount". In amount steckt
            # die Kaufgebuehr aber schon drin (oben: fee = amount * fee_rate,
            # qty = (amount - fee) / price). app.py:1862 und :2958 rechnen
            # danach cost_basis = filled_cost + fee - also ein ZWEITES Mal.
            # Zusammen mit der Verkaufsgebuehr in app.py:1712 wurden dadurch
            # DREI Gebuehren abgezogen statt zwei. Am 01.09. ueber 14 Verkaeufe
            # gemessen: Faktor 3,00 (kleinster 2,99, groesster 3,33), also
            # 0,75 % je Runde statt der K-BASIS von 0,505 %.
            #
            # amount - fee ist genau qty * price - und damit dasselbe, was
            # ccxt im Livepfad als "cost" liefert (:546). Beide Wege bedeuten
            # ab jetzt dasselbe, und filled_cost + fee ergibt in beiden den
            # echten Mittelabfluss. Der Livepfad bleibt unberuehrt.
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

                # ==========================================================
                # [15.09.2026] PHANTOM-VERKAUF-SCHUTZ, jetzt auch LIVE.
                #
                # Diese Kappung gab es bisher NUR im Papierhandel
                # (weiter unten, "Menge auf echten Bestand gekappt").
                # Ausgerechnet dort, wo kein Geld auf dem Spiel steht.
                #
                # WAS AM 15.09. UM 13:39 PASSIERTE:
                #   [MONITOR] ETH: STOP_LOSS TRIGGERED! (-2.15%)
                #   [ORDERS]  Error: bybit {"retCode":170131,
                #             "retMsg":"Insufficient balance."}
                #
                # Der Stop-Loss loeste aus - und der Verkauf scheiterte.
                # Die Position lief danach UNGESCHUETZT weiter, waehrend
                # sie fiel. Das ist der gefaehrlichste Zustand ueberhaupt.
                #
                # DIE URSACHE, auf zwoelf Stellen nachgerechnet:
                #   Register: 0,0042      ETH
                #   Boerse:   0,0041895   ETH
                #   0,0042 x 0,25 % = 0,0000105  ->  genau die Differenz
                #
                # Bybit zieht die KAUFGEBUEHR IN DER GEKAUFTEN MUENZE ab.
                # Der Bot schrieb aber die volle Ausfuehrungsmenge an die
                # Position - also immer 0,25 % mehr, als er besitzt.
                # Jeder Verkauf der vollen Position muss daran scheitern.
                #
                # Dieselbe Waehrungsfalle wie in bestand_einstand(), nur
                # an der anderen Stelle: dort bei den Kosten, hier bei
                # der Menge.
                #
                # Die Ursache ist in app.py behoben (Gebuehr wird von der
                # Menge abgezogen). Diese Kappung bleibt trotzdem: Sie
                # faengt AUCH Rundungsreste, Teilverkaeufe und von Hand
                # abgebuchte Betraege ab. Ein Stop-Loss, der an 0,25 %
                # scheitert, ist kein Stop-Loss.
                # ==========================================================
                try:
                    _asset = intent.symbol.split("/")[0]
                    _bal = self.get_balance() or {}
                    _frei = float((_bal.get("free") or {}).get(_asset)
                                  or (_bal.get("total") or {}).get(_asset) or 0)
                    if _frei > 0 and roh > _frei:
                        log.warn("LIVE-SAFETY",
                                 f"{intent.symbol}: Verkaufsmenge auf echten "
                                 f"Bestand gekappt {roh:.8f} -> {_frei:.8f} "
                                 f"(Differenz {roh - _frei:.8f}, meist die "
                                 f"in Coins abgezogene Kaufgebuehr)")
                        roh = _frei
                    elif _frei <= 0:
                        # Kein stilles Scheitern: Wer hier nichts findet,
                        # verkauft gleich ins Leere - das muss im Log stehen.
                        log.error("LIVE-SAFETY",
                                  f"{intent.symbol}: KEIN {_asset} auf dem "
                                  f"Konto, aber Verkauf von {roh:.8f} "
                                  f"angefordert - Geister-Position?")
                except Exception as _be:
                    log.warn("LIVE-SAFETY", f"{intent.symbol}: Bestand fuer "
                                            f"die Kappung nicht abrufbar "
                                            f"({str(_be)[:60]}) - Verkauf "
                                            f"laeuft mit der Registermenge")
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

        # ================================================================
        # [BEFUND 68, Punkt 2 - 14.09.2026] MINDESTBETRAG PRUEFEN
        # ----------------------------------------------------------------
        # Jede Boerse hat einen Mindestbetrag je Order. Bybit Spot verlangt
        # 5,00 USDT (am 14.09. gegen die echten Marktregeln gemessen,
        # testnetz_probe.py --ohne-schluessel). Eine kleinere Order wird
        # abgelehnt - im Papiermodus faellt das NIE auf, weil dort nichts
        # gesendet wird.
        #
        # Bei 135 $ Positionsgroesse ist das unkritisch. Es trifft den
        # Teilverkauf und den Fall, dass das Kapital zusammengeschmolzen
        # ist - also genau dann, wenn ohnehin etwas schiefgeht.
        #
        # Abgelehnt wird HIER, vor dem Senden. Eine Order, von der man
        # vorher weiss, dass die Boerse sie zurueckweist, soll gar nicht
        # erst hinausgehen - jeder abgelehnte Versuch zaehlt auf den
        # Rejection-Counter und kann den Bot in den Schlafmodus schicken.
        # ================================================================
        try:
            _m = (best_exchange.markets or {}).get(intent.symbol) or {}
            _min_betrag = ((_m.get("limits") or {}).get("cost") or {}).get("min")
            if _min_betrag:
                _wert = (intent.amount_usd if intent.side == Side.BUY
                         else menge * float(intent.entry_price))
                if _wert < float(_min_betrag):
                    result.status = "rejected"
                    result.rejected_reason = (
                        f"unter dem Mindestbetrag der Boerse "
                        f"({_wert:.2f} < {float(_min_betrag):.2f})")
                    log.warn("LIVE-SAFETY",
                             f"{intent.symbol}: Order {_wert:.2f} unter dem "
                             f"Mindestbetrag {float(_min_betrag):.2f} - nicht "
                             f"gesendet (Befund 68)")
                    return result
        except Exception as _mb_e:
            # Kein stiller Schlucker, aber auch kein Abbruch: sind die
            # Marktregeln nicht geladen, entscheidet die Boerse selbst.
            log.warn("LIVE-SAFETY", f"{intent.symbol}: Mindestbetrag nicht "
                                    f"pruefbar ({str(_mb_e)[:60]})")

        # ================================================================
        # [BEFUND 68, Punkt 1 - 14.09.2026] DIE KENNUNG MITSENDEN
        # ----------------------------------------------------------------
        # Hier stand bisher create_market_buy_order(symbol, menge) - ohne
        # Kennung. Darueber liegt self.retry.execute(), also eine
        # Wiederholung. Geht die Antwort der Boerse verloren (Zeit-
        # ueberschreitung, Verbindungsabbruch), sendet der Versuch die
        # Order ein zweites Mal - und die Boerse sieht zwei voellig
        # unabhaengige Auftraege. ES WIRD ZWEIMAL GEKAUFT.
        #
        # Der IdempotencyGuard schuetzt davor NICHT: er prueft, ob
        # execute() zweimal aufgerufen wird. Die Wiederholung passiert
        # INNERHALB eines Aufrufs, unterhalb seiner Pruefung.
        #
        #   "Der Bot weiss immer, was er gewollt hat. Die Boerse weiss
        #    nicht, dass sie es schon einmal gehoert hat."
        #
        # DER PARAMETERNAME IST BOERSENABHAENGIG, und das ist die Falle:
        # Die in GEFUNDENE-PROBLEME.md notierte Reparatur nennt
        # `newClientOrderId` - das ist BINANCE. Bybit heisst das Feld
        # `orderLinkId`. In ccxt nachgesehen (14.09.2026): bybit.create_order
        # liest `clientOrderId` NICHT, Binance schon. Wer die Reparatur
        # eins zu eins uebernimmt, sendet bei Bybit einen Parameter, den
        # die Boerse ignoriert - der Schutz waere wirkungslos, ohne dass
        # es auffaellt.
        # ================================================================
        _kennung = (result.client_order_id or "")[:36]   # Bybit: max 36
        _params = {}
        if _kennung:
            _boerse = str(getattr(best_exchange, "id", "")).lower()
            if "bybit" in _boerse:
                _params["orderLinkId"] = _kennung
            elif "binance" in _boerse:
                _params["newClientOrderId"] = _kennung
            else:
                # ccxt vereinheitlicht das Feld fuer die meisten Boersen.
                _params["clientOrderId"] = _kennung

        # ================================================================
        # [WARTE-AUFTRAEGE LIVE 17.09.2026] Der Abzweig fuer echte
        # Limit-Orders - das Spiegelbild zu _execute_paper():419.
        # ----------------------------------------------------------------
        # Warum hier und nicht frueher: An dieser Stelle ist `menge` schon
        # boersenkonform gerundet (:708) und der Mindestbetrag geprueft
        # (:735-747). Ein Warte-Auftrag unter dem Boersenminimum waere
        # sonst dasselbe stille Scheitern wie Befund 68.
        #
        # NUR KAEUFE. Verkaeufe bleiben Sofort-Auftraege, aus demselben
        # Grund wie im Papierpfad (:410-417): Ein Stop-Loss, der als
        # Limit-Order im Buch liegt, wird bei einem schnellen Rutsch NICHT
        # bedient - der Kurs springt darueber hinweg. Die Notbremse muss
        # ein Sofort-Auftrag bleiben.
        #
        # Der Schalter `nur_paper` steht bis zur ausdruecklichen Freigabe
        # auf true; bis dahin ist dieser Zweig tot und das Verhalten
        # unveraendert.
        # ================================================================
        if (intent.side == Side.BUY
                and self.warteschlange is not None
                and self.warteschlange.aktiv
                and not self.warteschlange.einst.get("nur_paper", True)):
            return self._warteauftrag_live_anlegen(
                intent, result, best_exchange, menge, _kennung)

        def _do():
            seite = "buy" if intent.side == Side.BUY else "sell"
            return best_exchange.create_order(intent.symbol, "market", seite,
                                              menge, None, _params)

        order = self.retry.execute(lambda: self.circuit.call(_do)) or {}

        result.order_id = order.get("id", "") or ""

        # ================================================================
        # [BEFUND 68, Punkt 3 - 14.09.2026] NACHFRAGEN STATT RATEN
        # ----------------------------------------------------------------
        # `fetch_order` kam im ganzen Bot nicht vor. Nach einer Zeit-
        # ueberschreitung wusste er deshalb nicht, ob die Order durchging -
        # er konnte nicht nachsehen, nur raten.
        #
        # Gefragt wird NUR, wenn die Antwort unvollstaendig ist. Eine
        # Boerse, die sauber geantwortet hat, wird nicht noch einmal
        # behelligt - jede zusaetzliche Abfrage kostet Rate-Limit.
        # ================================================================
        # [BERICHTIGT 14.09.2026, nach dem ersten Echtgeld-Lauf]
        #
        # WAS SCHIEFGING: Die erste Fassung rief nur `fetch_order` auf.
        # Bybit beantwortet das fuer eine bereits AUSGEFUEHRTE Spot-Order
        # nicht - woertlich: "fetchOrder() can only access an order if it
        # is in last ...". Der Aufruf scheiterte, `order` blieb das leere
        # Dict von oben, und der Bot buchte die Order als NICHT GEFUELLT.
        #
        # Am 14.09. um 21:24 dreimal passiert: drei Kaeufe zu je 10,87 $
        # gingen durch (Boerse: Status "Filled"), der Bot fuehrte KEINE
        # Position. Damit greift kein Stop-Loss, kein Trailing - und er
        # haette weitergekauft, bis das Guthaben leer ist.
        #
        # Verloren war nichts (36,25 $ vorher, 36,16 $ nachher, der Rest
        # Gebuehren), aber der Zustand war der gefaehrlichste denkbare:
        # Der Bot besitzt etwas, von dem er nichts weiss.
        #
        # JETZT DREI WEGE, in dieser Reihenfolge. Der erste, der
        # antwortet, gewinnt:
        #   1. fetch_order          - klappt bei offenen Orders
        #   2. fetch_closed_order   - fuer bereits ausgefuehrte
        #   3. fetch_my_trades      - die Ausfuehrungen selbst, das ist
        #                             die Quelle, die eine Boerse IMMER hat
        if result.order_id and not order.get("filled"):
            _nach = None
            _fehler = []
            for _name, _wie in (
                    ("fetch_order",
                     lambda: best_exchange.fetch_order(result.order_id, intent.symbol)),
                    ("fetch_closed_order",
                     lambda: best_exchange.fetch_closed_order(result.order_id, intent.symbol)),
            ):
                try:
                    _nach = _wie()
                    if _nach and (_nach.get("filled") or _nach.get("status")):
                        log.info("EXEC", f"{intent.symbol}: nachgefragt via "
                                         f"{_name} - Status {_nach.get('status')}, "
                                         f"gefuellt {_nach.get('filled')}")
                        order = _nach
                        break
                except Exception as _e:
                    _fehler.append(f"{_name}: {str(_e)[:50]}")
                    _nach = None

            # Letzter Weg: die Ausfuehrungen. Wenn die Boerse gehandelt
            # hat, steht es hier - unabhaengig davon, ob sie die Order
            # noch zum Abruf bereithaelt.
            # ============================================================
            # [15.09.2026] NICHT IN DERSELBEN SEKUNDE AUFGEBEN.
            #
            # Der dritte Weg war richtig gebaut - er wurde nur zu frueh
            # gefragt. Am 15.09. um 14:23 verkaufte der Bot 0,0041 ETH
            # fuer 9,99 $, die Boerse fuehrte aus, und eine Sekunde
            # spaeter stand im Log:
            #
            #   [ERROR] Order ueber KEINEN Weg abfragbar - UNBEKANNT
            #   [ERROR] Order NICHT gefuellt
            #
            # Folge: Die Position blieb im Register, obwohl sie verkauft
            # war. Der Bot loeste danach zwei Stunden lang alle 30
            # Sekunden denselben Stop-Loss aus, und seine Buchhaltung
            # wies 27 % Gewinn aus, den es nicht gab.
            #
            # Die Ursache ist eine Frage von Sekundenbruchteilen:
            # Zwischen Ausfuehrung und Sichtbarkeit in der
            # Handelshistorie vergeht bei Bybit ein Moment. In diesem
            # Fenster ist die Order weder offen (schon gefuellt) noch
            # auffindbar - sie existiert fuer den Abruf schlicht nicht.
            #
            # Deshalb: mehrmals fragen, mit wachsender Pause. Und nach
            # BEIDEN Kennungen suchen - der Boersen-ID UND unserer
            # eigenen orderLinkId. Letztere ist die verlaesslichere:
            # Wir haben sie selbst gesetzt, sie kann nicht verlorengehen.
            #
            # Die Wartezeit ist bewusst kurz gehalten (zusammen unter
            # vier Sekunden). Ein Bot, der nach einer Order minutenlang
            # steht, verpasst den naechsten Stop-Loss.
            # ============================================================
            if not (order.get("filled")):
                _kennung = (result.client_order_id or "")
                for _versuch, _pause in ((1, 0.0), (2, 1.0), (3, 2.5)):
                    if _pause:
                        time.sleep(_pause)
                    try:
                        _trades = best_exchange.fetch_my_trades(
                            intent.symbol, limit=20)
                    except Exception as _e:
                        _fehler.append(f"fetch_my_trades#{_versuch}: "
                                       f"{str(_e)[:40]}")
                        continue

                    _meine = []
                    for t in (_trades or []):
                        _oid = str(t.get("order") or "")
                        _lid = str(((t.get("info") or {}).get("orderLinkId")
                                    or ""))
                        if (_oid and _oid == str(result.order_id)) or \
                           (_kennung and _lid and _lid.startswith(_kennung[:36])):
                            _meine.append(t)

                    if _meine:
                        _menge = sum(float(t.get("amount") or 0) for t in _meine)
                        _wert = sum(float(t.get("cost") or 0) for t in _meine)
                        _geb = sum(float((t.get("fee") or {}).get("cost") or 0)
                                   for t in _meine)
                        _gw = ""
                        for t in _meine:
                            _gw = str((t.get("fee") or {}).get("currency")
                                      or "").upper()
                            if _gw:
                                break
                        order = {"id": result.order_id, "filled": _menge,
                                 "cost": _wert, "status": "closed",
                                 "average": (_wert / _menge) if _menge else 0,
                                 "fee": {"cost": _geb, "currency": _gw}}
                        log.info("EXEC", f"{intent.symbol}: ueber die "
                                         f"Ausfuehrungen gefunden (Versuch "
                                         f"{_versuch}) - {_menge:.8f} fuer "
                                         f"{_wert:.2f} $")
                        break

            if not order.get("filled") and _fehler:
                # Jetzt ist der Zustand wirklich unbekannt. Das ist der
                # gefaehrlichste Fall, deshalb als Fehler und nicht als
                # Warnung - und mit allen drei Fehlermeldungen, damit man
                # sieht, welcher Weg woran scheiterte.
                log.error("EXEC", f"{intent.symbol}: Order {result.order_id} "
                                  f"ueber KEINEN Weg abfragbar - Zustand an "
                                  f"der Boerse UNBEKANNT. {' | '.join(_fehler)}")

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
        #
        # [15.09.2026] Die WAEHRUNG wird jetzt mitgenommen. Ohne sie ist
        # `gebuehr` eine Zahl ohne Einheit, und die Einheit entscheidet:
        # Bybit zieht die Spot-Kaufgebuehr in der GEKAUFTEN Muenze ab.
        # Wer sie als Dollar liest, verrechnet zwei Waehrungen; wer sie
        # ignoriert, fuehrt eine Position, die 0,25 % groesser ist als
        # der echte Bestand - und genau daran scheiterte am 15.09. um
        # 13:39 ein Stop-Loss mit "Insufficient balance".
        gebuehr = 0.0
        gebuehr_waehrung = ""
        try:
            f = order.get("fee")
            if isinstance(f, dict):
                gebuehr = float(f.get("cost") or 0)
                gebuehr_waehrung = str(f.get("currency") or "").upper()
            if gebuehr <= 0:
                for f2 in (order.get("fees") or []):
                    if isinstance(f2, dict):
                        gebuehr += float(f2.get("cost") or 0)
                        if not gebuehr_waehrung:
                            gebuehr_waehrung = str(
                                f2.get("currency") or "").upper()
        except Exception:
            gebuehr = 0.0
            gebuehr_waehrung = ""

        result.avg_fill_price = preis
        result.filled_qty = filled
        result.filled_cost = kosten if kosten > 0 else filled * preis
        result.fee = gebuehr
        result.fee_currency = gebuehr_waehrung

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

    # ==================================================================
    # [WARTE-AUFTRAEGE 11.09.2026] Der Takt-Aufruf.
    # ------------------------------------------------------------------
    # app.py ruft das bei jedem Durchlauf auf. Gibt eine Liste von
    # (intent, result) zurueck - genau die zwei Dinge, die app.py nach
    # einem Sofortkauf auch hat. Damit laeuft ein bedienter Warte-Auftrag
    # durch denselben Pfad wie jeder andere Kauf: Journal, Position,
    # Telemetrie, Impact-Journal. Kein zweiter Schreibweg.
    #
    # Genau das war der Fehler bei Befund 88: zwei Wege, die Verkaeufe
    # schreiben, und nur einer schrieb alle Felder mit. Ein dritter
    # Kaufweg mit eigener Journal-Logik waere derselbe Fehler noch
    # einmal - deshalb baut diese Methode nur Intent und Result und
    # ueberlaesst das Buchen dem Aufrufer.
    # ==================================================================
    def _warteauftrag_live_anlegen(self, intent, result, exchange, menge,
                                   kennung):
        """Stellt einen ECHTEN Warte-Auftrag ins Orderbuch der Boerse.

        [17.09.2026] Gegenstueck zu _execute_paper():419, aber mit einem
        entscheidenden Unterschied: dort spielt der Bot den Auftrag nach
        und prueft alle 12 Sekunden selbst, ob der Kurs sein Limit
        erreicht hat. Hier haelt die BOERSE den Auftrag und sieht jeden
        einzelnen Handel. Der Grund fuer die in warteauftraege.py
        genannte Obergrenze von 73,3 % entfaellt damit.

        Die Reihenfolge ist Absicht: erst an die Boerse, dann in die
        eigene Liste. Andersherum stuende ein Auftrag in der Liste, den
        es an der Boerse nie gab - und der Takt wuerde ewig auf seine
        Ausfuehrung warten.
        """
        from execution import warteauftraege_live as _wl

        limitpreis = self.warteschlange.limitpreis(float(intent.entry_price))
        oid, fehler = _wl.stellen(exchange, intent.symbol, menge, limitpreis,
                                  kennung)
        if fehler:
            # KEIN Rueckfall auf einen Sofortkauf. Wer bei einem
            # gescheiterten Warte-Auftrag still zum teureren Weg wechselt,
            # misst hinterher etwas anderes, als er glaubt - und der
            # Grund fuer das Scheitern bliebe unsichtbar.
            result.status = "rejected"
            result.rejected_reason = f"Warte-Auftrag nicht gestellt: {fehler}"
            log.error("WARTE-LIVE",
                      f"{intent.symbol}: Auftrag nicht gestellt ({fehler}) - "
                      f"es wird NICHT ersatzweise sofort gekauft")
            return result

        auftrag = self.warteschlange.anlegen(
            intent.symbol, float(intent.entry_price), intent.amount_usd,
            angaben={"strategy_id": getattr(intent, "strategy_id", "") or "",
                     "score": getattr(intent, "score", None),
                     "confidence": getattr(intent, "confidence", None),
                     "entry_reason": getattr(intent, "entry_reason", "") or "",
                     # Diese beiden machen den Auftrag an der Boerse
                     # wiederfindbar. Ohne sie waere er nach einem
                     # Neustart des Bots verwaist: er laege im Orderbuch,
                     # bindet Geld, und niemand nimmt ihn je zurueck.
                     "live_order_id": oid,
                     "live_menge": menge,
                     # [BEFUND 88 WARTEKAUF 17.10.2026] Stop, Nachzieh-Abstand usw. mitnehmen
                     **_warte_merkangaben(intent)})
        if auftrag is None:
            # Die Liste nimmt ihn nicht - dann darf er auch an der Boerse
            # nicht liegen bleiben.
            log.warn("WARTE-LIVE",
                     f"{intent.symbol}: laeuft bereits, gerade gestellter "
                     f"Auftrag {oid} wird zurueckgenommen")
            _wl.zuruecknehmen(exchange, oid, intent.symbol)
            result.status = "rejected"
            result.rejected_reason = "Warte-Auftrag laeuft bereits"
            return result

        result.status = "wartet"
        result.rejected_reason = ""
        result.order_id = oid
        result.avg_fill_price = auftrag["limitpreis"]
        log.info("WARTE-LIVE",
                 "%s: ECHTER Warte-Auftrag %s bei %.8f $ (%.2f %% unter "
                 "%.8f $), gueltig %d Minuten"
                 % (intent.symbol, oid, auftrag["limitpreis"],
                    auftrag["abstand_pct"], auftrag["marktpreis_bei_anlage"],
                    int(self.warteschlange.gueltig_sekunden() // 60)))
        return result

    def _warteauftraege_live_takt(self):
        """Ein Takt im Echtbetrieb: die Boerse fragen, nicht den Kurs raten.

        [17.09.2026] Im Papierpfad entscheidet der Bot anhand des Kurses,
        ob sein Limit erreicht wurde. Hier liegt der Auftrag an der
        Boerse - also wird dort nachgefragt. Das ist nicht nur genauer,
        es ist die einzige Wahrheit: eine Teilausfuehrung oder ein
        zwischenzeitlich bedienter Auftrag stehen nirgends im Kurs.

        Drei Zustaende, drei Behandlungen:
          gefuellt/teilweise -> buchen, mit der Menge, die WIRKLICH kam
          abgelaufen         -> zuruecknehmen (und dabei nachsehen, ob er
                                im letzten Moment doch bedient wurde)
          unklar             -> NICHTS tun. Beim naechsten Takt nochmal.
                                Wer hier aufraeumt, verliert Positionen.
        """
        from execution import warteauftraege_live as _wl

        ergebnisse = []
        jetzt = time.time()
        gueltig = self.warteschlange.gueltig_sekunden()

        # [FIX 17.09.2026] .values() - offene() gibt ein DICT
        # {symbol: auftrag} zurueck. Ohne .values() laeuft die Schleife
        # ueber die SCHLUESSEL, also ueber Zeichenketten, und das erste
        # a.get("angaben") wirft "'str' object has no attribute 'get'".
        # Genau das stand seit dem Scharfschalten alle 12 Sekunden im
        # Log. Kein Schaden - der Takt brach ab, bevor er etwas tat -
        # aber die Warte-Auftraege waren damit wirkungslos.
        for a in list(self.warteschlange.offene().values()):
            ang = a.get("angaben") or {}
            oid = ang.get("live_order_id") or ""
            symbol = a["symbol"]
            if not oid:
                # Ein Auftrag ohne Boersen-Kennung kann nur aus dem
                # Papierpfad stammen. Nicht anfassen, aber melden -
                # stillschweigend ueberspringen waere genau das Muster,
                # das dieses Projekt schon zweimal Geld gekostet hat.
                log.warn("WARTE-LIVE",
                         f"{symbol}: Auftrag ohne live_order_id in der "
                         f"Warteschlange - wird uebersprungen")
                continue

            abgelaufen = (jetzt - float(a.get("angelegt_ts") or 0)) >= gueltig
            if abgelaufen:
                st = _wl.zuruecknehmen(self.exchange, oid, symbol)
            else:
                st = _wl.status(self.exchange, oid, symbol)

            if st["zustand"] == "unklar":
                continue                       # nicht raten, nicht aufraeumen
            if st["zustand"] == "offen":
                continue                       # laeuft noch
            if st["zustand"] == "weg":
                self.warteschlange.erledigen(symbol, "verfallen")
                log.info("WARTE-LIVE",
                         f"{symbol}: Warte-Auftrag {oid} verfallen, Limit "
                         f"{a['limitpreis']:.8f} wurde in "
                         f"{int(gueltig // 60)} Minuten nicht erreicht")
                continue

            # Ab hier: gefuellt oder teilweise gefuellt.
            self.warteschlange.erledigen(symbol, "ausgefuehrt")
            menge = float(st["menge"] or 0.0)
            preis = float(st["preis"] or a["limitpreis"])
            if menge <= 0:
                log.error("WARTE-LIVE",
                          f"{symbol}: Boerse meldet '{st['zustand']}', aber "
                          f"Menge 0 - nicht gebucht")
                continue

            intent = DecisionIntent(
                symbol=symbol, side=Side.BUY,
                entry_price=preis,
                # Der WIRKLICH bezahlte Betrag, nicht der geplante. Bei
                # einer Teilausfuehrung sind das zwei verschiedene Zahlen,
                # und die geplante waere gelogen.
                amount_usd=menge * preis,
                strategy_id=ang.get("strategy_id", "") or "",
                entry_reason=ang.get("entry_reason", "") or "",
                score=int(ang.get("score") or 0),
                confidence=float(ang.get("confidence") or 0.0),
            )
            _warte_merkangaben_zurueck(intent, ang)   # [BEFUND 88 WARTEKAUF 17.10.2026]
            result = ExecutionResult(intent_id=intent.id, symbol=symbol,
                                     side=Side.BUY)
            client_id = self.idempotency.create_id(intent.id, symbol)
            result.client_order_id = client_id
            result.order_id = oid
            result.status = "filled"
            result.avg_fill_price = preis
            result.filled_qty = menge
            result.fee = float(st.get("gebuehr") or 0.0)
            result.fee_currency = str(st.get("waehrung") or "")

            self.order_manager.place(client_id, symbol, "BUY",
                                     intent.amount_usd, intent.strategy_id,
                                     intent.entry_reason)
            self.order_manager.update_fill(client_id, oid, preis, menge,
                                           result.fee or 0)
            self.idempotency.confirm(client_id, oid)

            teil = ""
            if st["zustand"] == "teilweise":
                geplant = float(a.get("betrag_usd") or 0.0)
                teil = (f"  TEILWEISE: {intent.amount_usd:.2f} von "
                        f"{geplant:.2f} $ geplant")
            log.trade("WARTE-LIVE",
                      "%s BEDIENT (Maker): %.8f @ %.8f $, lag %.0f Minuten%s"
                      % (symbol, menge, preis,
                         (jetzt - float(a.get("angelegt_ts") or jetzt)) / 60.0,
                         teil))
            ergebnisse.append((intent, result))

        return ergebnisse

    def warteauftraege_pruefen(self, kurse):
        """Ein Takt der Warteschlange. Gibt [(intent, result), ...] zurueck.

        `kurse` ist ein Dict symbol -> aktueller Preis. Ein Symbol, das
        darin fehlt, bleibt unberuehrt (Befund 95: eingefrorene Kurse).
        """
        if self.warteschlange is None or not self.warteschlange.aktiv:
            return []
        # [17.09.2026] Im Echtbetrieb entscheidet nicht mehr der Kursblick
        # des Bots, sondern die Boerse. Deshalb ein eigener Takt.
        if not self._paper_mode:
            if self.warteschlange.einst.get("nur_paper", True):
                return []
            return self._warteauftraege_live_takt()

        gefuellt, verfallen = self.warteschlange.pruefen(kurse)

        for a in verfallen:
            log.info("PAPER", "Warte-Auftrag %s verfallen: Limit %.8f $ wurde "
                              "in %d Minuten nicht erreicht"
                     % (a["symbol"], a["limitpreis"],
                        int(self.warteschlange.gueltig_sekunden() // 60)))

        ergebnisse = []
        for a in gefuellt:
            ang = a.get("angaben") or {}
            intent = DecisionIntent(
                symbol=a["symbol"], side=Side.BUY,
                entry_price=a["limitpreis"],
                amount_usd=a["betrag_usd"],
                strategy_id=ang.get("strategy_id", "") or "",
                entry_reason=ang.get("entry_reason", "") or "",
                score=int(ang.get("score") or 0),
                confidence=float(ang.get("confidence") or 0.0),
            )
            _warte_merkangaben_zurueck(intent, ang)   # [BEFUND 88 WARTEKAUF 17.10.2026]
            result = ExecutionResult(intent_id=intent.id, symbol=intent.symbol,
                                     side=intent.side)
            client_id = self.idempotency.create_id(intent.id, intent.symbol)
            result.client_order_id = client_id
            self.order_manager.place(client_id, intent.symbol, intent.side.value,
                                     intent.amount_usd, intent.strategy_id,
                                     intent.entry_reason)
            try:
                result = self._execute_paper(intent, result, warte_fuellung=a)
            except Exception as e:
                # Kein stilles Scheitern. Der Auftrag ist aus der
                # Warteschlange schon heraus - er darf nicht einfach
                # verschwinden, ohne dass jemand es sieht.
                result.status = "error"
                result.error = str(e)[:200]
                self.order_manager.update_error(client_id, str(e))
                log.error("PAPER", f"Warte-Auftrag {a['symbol']} nicht "
                                   f"ausfuehrbar: {e}")
            if result.status == "filled":
                self.order_manager.update_fill(client_id, result.order_id or "",
                                               result.avg_fill_price,
                                               result.filled_qty, result.fee or 0)
                log.trade("PAPER", "Warte-Auftrag %s BEDIENT: %.6f @ %.8f $ "
                                   "(Maker, lag %.0f Minuten)"
                          % (a["symbol"], result.filled_qty,
                             result.avg_fill_price,
                             (a.get("gefuellt_ts", 0) - a.get("angelegt_ts", 0)) / 60.0))
            elif result.status == "rejected":
                self.order_manager.update_rejected(client_id,
                                                   result.rejected_reason or "?")
                log.warn("PAPER", "Warte-Auftrag %s abgelehnt: %s"
                         % (a["symbol"], result.rejected_reason))
            self.idempotency.release(client_id)
            ergebnisse.append((intent, result))
        return ergebnisse

    def warteauftraege_stand(self):
        """Was wartet gerade, und wie ist die Bilanz? Fuer Anzeige und Test."""
        if self.warteschlange is None:
            return {"aktiv": False, "offen": {}, "verlauf": {}}
        return {"aktiv": self.warteschlange.aktiv,
                "offen": self.warteschlange.offene(),
                "verlauf": dict(self.warteschlange.verlauf),
                "einstellungen": dict(self.warteschlange.einst)}

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

    def bestand_einstand(self, symbol, menge_vorhanden, limit=100):
        """Der ECHTE Einstandspreis eines vorhandenen Bestands.

        WOZU (14.09.2026)
        -----------------
        Nach dem ersten Live-Lauf lagen 0,00041 BTC auf dem Konto, die in
        keinem Positionsregister standen - der Bot hielt seine eigenen
        vier Kaeufe fuer gescheitert. Damit ein Stop-Loss diese Coins
        bewachen kann, braucht er einen Bezugspunkt.

        Der naheliegende Weg waere gewesen, den AKTUELLEN Kurs als
        Einstand zu nehmen. Genau das tut die Paper-Rekonstruktion in
        runtime/state_manager.py, und sie warnt dort selbst davor:
        ein bereits aufgelaufener Buchverlust wird dadurch unsichtbar,
        und der Stop-Loss haengt am falschen Punkt. Bei -2,5 % Stop und
        einem schon 2 % gefallenen Bestand ist das der Unterschied
        zwischen "sofort verkaufen" und "erst bei -4,5 %".

        Der echte Einstand steht an genau einer Stelle: in den
        Ausfuehrungen der Boerse. Dieselbe Quelle, ueber die am
        14.09. abends auch die Fuell-Erkennung repariert wurde
        (execution/engine.py:800) - sie ist die einzige, die eine
        Boerse immer hat.

        VERFAHREN UND SEINE GRENZE
        --------------------------
        Die Ausfuehrungen werden von neu nach alt durchgegangen und die
        KAEUFE aufgesammelt, bis ihre Summe die vorhandene Menge deckt.
        Das ist eine "zuletzt gekauft"-Annahme.

        Sie ist EXAKT richtig, solange zwischendurch nicht verkauft
        wurde. Wurde verkauft, ist sie eine Naeherung - deshalb meldet
        die Funktion `verkaeufe_gesehen` mit, damit der Aufrufer die
        Zahl einordnen kann statt ihr blind zu glauben.

        Rueckgabe: dict oder None (None = kein Einstand ermittelbar;
        der Aufrufer darf dann NICHT einfach den Marktpreis nehmen).
        """
        if self._paper_mode or not self.exchange:
            return None
        try:
            menge_soll = float(menge_vorhanden)
        except Exception:
            return None
        if menge_soll <= 0:
            return None

        try:
            trades = self.retry.execute(
                lambda: self.circuit.call(
                    lambda: self.exchange.fetch_my_trades(symbol, limit=limit)))
        except Exception as e:
            log.warn("EXEC", f"{symbol}: Ausfuehrungen nicht abrufbar "
                             f"({str(e)[:80]}) - Einstand unbekannt")
            return None

        if not trades:
            return None

        trades = sorted(trades, key=lambda t: t.get("timestamp") or 0,
                        reverse=True)
        verkaeufe = sum(1 for t in trades
                        if str(t.get("side", "")).lower() == "sell")

        basis_coin = symbol.split("/")[0]
        rest = menge_soll
        menge_ges = 0.0
        kosten_ges = 0.0
        gebuehr_quote = 0.0     # Gebuehr in USDC
        gebuehr_basis = 0.0     # Gebuehr in BTC/ETH/SOL
        benutzt = 0

        for t in trades:
            if rest <= 1e-12:
                break
            if str(t.get("side", "")).lower() != "buy":
                continue
            try:
                menge = float(t.get("amount") or 0)
                preis = float(t.get("price") or 0)
            except Exception:
                continue
            if menge <= 0 or preis <= 0:
                continue
            nimm = min(menge, rest)
            anteil = nimm / menge

            # === GEBUEHRENWAEHRUNG (14.09.2026, an echten Daten gefunden) ===
            #
            # Erster Entwurf nahm fee["cost"] und addierte es zur
            # Kostenbasis in Dollar. An den echten Ausfuehrungen vom
            # 14.09. zeigte sich: Bybit zieht die Spot-Kaufgebuehr in
            # der GEKAUFTEN MUENZE ab, nicht in USDC.
            #
            #   fee = {'currency': 'BTC', 'cost': 3.425e-07, 'rate': 0.0025}
            #
            # Die 0,0000003425 sind BTC. Sie zu einem Dollarbetrag zu
            # addieren, mischt zwei Waehrungen in einer Summe - der
            # Fehler faellt nur deshalb nicht auf, weil die Zahl winzig
            # ist. Bei groesseren Positionen verfaelscht er die
            # Kostenbasis.
            #
            # Richtig ist: Wer in der Basiswaehrung zahlt, bekommt
            # WENIGER Coins - der Dollarbetrag (cost) ist bereits der
            # volle Einsatz. Nachgerechnet an den vier Ausfuehrungen:
            #   Summe amount   0,00041100 BTC
            #   Summe Gebuehr  0,00000103 BTC
            #   Rest           0,00040997 BTC  = genau der Kontostand
            _f = t.get("fee") or {}
            try:
                _fc = float(_f.get("cost") or 0) * anteil
            except Exception:
                _fc = 0.0
            _fw = str(_f.get("currency") or "").upper()
            if _fw == basis_coin:
                gebuehr_basis += _fc
            else:
                gebuehr_quote += _fc

            menge_ges += nimm
            kosten_ges += nimm * preis
            rest -= nimm
            benutzt += 1

        if menge_ges <= 0:
            return None

        return {
            "menge": menge_ges,
            # Der Ausfuehrungspreis, ohne Gebuehr. Daran haengt der
            # Stop-Loss - und der soll die Kursbewegung messen, nicht
            # die Gebuehren.
            "preis_schnitt": kosten_ges / menge_ges,
            "kosten": kosten_ges,
            "gebuehr": gebuehr_quote,
            "gebuehr_in_coins": gebuehr_basis,
            # Was tatsaechlich an Dollar geflossen ist. Gebuehren in der
            # Basiswaehrung stecken bereits darin, weil man dafuer
            # weniger Coins bekommen hat - sie duerfen NICHT noch einmal
            # addiert werden.
            "kostenbasis": kosten_ges + gebuehr_quote,
            # Wieviel der vorhandenen Menge KEIN Kauf zugeordnet werden
            # konnte. Groesser 0 heisst: der Einstand ist nur teilweise
            # belegt (z. B. Coins von ausserhalb des Bots).
            "ungedeckt": rest,
            "verkaeufe_gesehen": verkaeufe,
            "ausfuehrungen": benutzt,
        }

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
