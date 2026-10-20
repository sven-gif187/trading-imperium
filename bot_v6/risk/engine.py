"""
Trading Imperium V5 – Risk Engine (Veto-Agent)
Prueft JEDEN Trade. Hat absolutes Veto-Recht.
Nutzt: ExposureManager, DrawdownGuard, KillSwitch, PositionSizer.

[TOEPFE SCHRITT 1 - 07.08.2026] Positions-Kennung eingefuehrt.

WARUM: open_positions ist ein Dict mit dem SYMBOL als Schluessel - es gibt also
genau einen Platz je Coin. Die geplanten drei Toepfe (je eine BTC-Position nach
eigener Strategie) sind darin nicht darstellbar.

WAS SICH IN DIESEM SCHRITT AENDERT: nur die Struktur, NICHT das Verhalten.
Jede Position bekommt zusaetzlich position_id, topf und strategie_id in ihr
Wert-Dict geschrieben. Der SCHLUESSEL bleibt das Symbol - dadurch funktionieren
alle rund 40 Zugriffsstellen in app.py, runtime/state_manager.py und
runtime/exit_monitor.py unveraendert weiter.

WAS ERST IN SCHRITT 3 KOMMT: der Schluesselwechsel auf position_id und damit
mehrere gleichzeitige Positionen je Coin. Bis dahin gilt weiter: ein Coin, eine
Position, "Bereits in Position" blockt wie bisher.
"""
import time
import uuid
from typing import Dict
from core.events import DecisionIntent, Side, IntentStatus
from core.logger import log
from risk.exposure import ExposureManager
from risk.drawdown_guard import DrawdownGuard
from risk.kill_switch import KillSwitch
from risk.position_sizing import PositionSizer
from core.regel_schalter import entscheidet

# [25.09.2026] Ab welchem Score eine Verlustserien-Sperre aufgehoben werden
# darf (Regel "verlustsperre_aufhebung"). Vorher stand hier fest 50 - bei
# einer Punkteskala von 0 bis 10 unerreichbar, die Aufhebung war tot
# (v7-Befund 119). 8 von 10 ist ein Startwert, KEIN gemessener Wert: die
# Regel laeuft im Schatten, erst die Notizen zeigen, ob 8 taugt.
VERLUSTSPERRE_AUFHEBUNG_AB_SCORE = 8


class RiskEngine:
    """Zentrale Risk-Engine. Vereint alle Risk-Module."""

    def __init__(self, config):
        self.config = config.risk
        self._portfolio_manager = None  # Wird spaeter via set_portfolio_manager gesetzt

        # Werte aus aktivem Modus oder Fallback (Kompatibilitaet)
        active_mode = config.get_active_mode() if hasattr(config, 'get_active_mode') else None

        # Position-Size aus aktivem Modus oder TradingConfig
        if active_mode:
            position_size_pct = active_mode.position_size_pct
            max_open_positions = active_mode.max_positions
            max_coin_pct = max(active_mode.max_coin_pct, position_size_pct + 5)
        else:
            position_size_pct = getattr(config.trading, 'position_size_pct', 12.5)
            max_open_positions = getattr(config.risk, 'max_open_positions', 8)
            max_coin_pct = max(
                getattr(config.risk, 'max_exposure_per_coin_pct', 35.0),
                position_size_pct + 5)

        # Wichtig: max_open_positions Attribute setzen (wird von check() gelesen)
        self.config.max_open_positions = max_open_positions

        self.exposure = ExposureManager(
            max_coin_pct=max_coin_pct,
            max_sector_pct=80.0)
        self.drawdown = DrawdownGuard(max_drawdown_pct=config.risk.max_drawdown_pct)

        # Daily-Loss: prozentual ODER USD (Kompatibilitaet)
        max_loss_usd = getattr(config.risk, 'max_daily_loss_usd', 0)
        if max_loss_usd <= 0:
            # Wenn nur prozentual gesetzt, Default 50$ fuer Kill-Switch
            max_loss_usd = 50.0
        self.kill_switch = KillSwitch(max_daily_loss=max_loss_usd)
        # [25.09.2026] risk.kill_switch_enabled wurde nie gelesen - ein
        # Scheinschalter (v7-Befund 118). Vorgabe und heutiger Wert: true.
        self.kill_switch_an = bool(getattr(config.risk, "kill_switch_enabled", True))
        self._notbremse_tag = None          # UTC-Datum fuer den Tagesreset
        self._notbremse_gemeldet = False    # Sammel-Notbremse je Ausloesung einmal
        self.notbremse_rueckruf = None      # setzt app.py (Sammel-Notbremse)

        self.sizer = PositionSizer(
            default_pct=position_size_pct,
            min_usd=5.0, max_pct=50.0)
        self.consecutive_losses = 0           # Globaler Counter (alt - bleibt fuer Stats)
        self.open_positions = {}
        self.daily_trades = 0

        # FIX 5: Coin-spezifischer Cooldown (statt global!)
        self.coin_consecutive_losses = {}     # {symbol: count}
        # Bei Score >= diesem Wert darf die Sperre aufgehoben werden - aber nur,
        # wenn der Schalter verlustsperre_aufhebung auf ACTIVE steht.
        self.coin_cooldown_override_score = VERLUSTSPERRE_AUFHEBUNG_AB_SCORE

        # === AUTO-DEFENSE STEP 1 ===
        self.consecutive_rejects = 0
        self.sleep_mode_until = 0
        self.sleep_threshold = 10
        self.sleep_duration_sec = 15 * 60
        self.defense_loss_threshold_pct = 2.0
        self.defense_max_sells_per_cycle = 2

    def set_portfolio_manager(self, portfolio_manager):
        """Verbindet die RiskEngine mit dem PortfolioManager fuer dynamische Limits."""
        self._portfolio_manager = portfolio_manager

    # ==================================================================
    # [TOEPFE SCHRITT 1 - 07.08.2026] Positions-Kennung
    # Reine Struktur-Vorbereitung. Aendert KEIN Handelsverhalten.
    # ==================================================================
    @staticmethod
    def neue_position_id(symbol: str = "") -> str:
        """Erzeugt eine eindeutige, dauerhafte Kennung fuer eine Position.

        Format: pos_<coin>_<8 Hex-Zeichen>, z. B. pos_BTC_9f3a1c07.
        Der Coin steht mit drin, damit die Kennung im Log und in der Datenbank
        ohne Nachschlagen lesbar ist. Die Zufallszeichen kommen aus uuid4 -
        eine laufende Nummer waere nach einem Neustart nicht mehr eindeutig.
        """
        asset = (symbol.split("/")[0] if "/" in symbol else symbol or "POS").upper()
        return f"pos_{asset}_{uuid.uuid4().hex[:8]}"

    def position_kennung_sicherstellen(self, symbol: str, pos: dict,
                                       strategie_id: str = "",
                                       topf: str = "haupt") -> dict:
        """Ergaenzt fehlende Kennungsfelder an EINER Position.

        Absichtlich nachruestend statt erzwingend: Positionen entstehen an
        mehreren Stellen (RiskEngine.record_result, app.py Signal- und
        DCA-Pfad, state_manager beim Wiederherstellen). Statt alle Stellen
        umzubauen - und dabei eine zu vergessen - wird die Kennung hier
        zentral nachgetragen. Vorhandene Werte werden nie ueberschrieben.
        """
        if not isinstance(pos, dict):
            return pos
        if not pos.get("position_id"):
            pos["position_id"] = self.neue_position_id(symbol)
        if not pos.get("topf"):
            pos["topf"] = topf or "haupt"
        if "strategie_id" not in pos:
            pos["strategie_id"] = strategie_id or ""
        if not pos.get("eroeffnet_ts"):
            pos["eroeffnet_ts"] = pos.get("time") or time.time()
        # [SCORE-FIX 10.08.2026] Der Einstiegs-Score muss an der Position
        # haengen. Vorher schrieb exit_monitor.py bei JEDEM Verkauf hart
        # score=10 - dadurch stand im Journal bei allen Verkaufszeilen
        # derselbe Wert und die Auswertung "welcher Score endet wie?" war
        # unmoeglich (Gesamtauswertung zeigte nur Score 0 und 10).
        if "entry_score" not in pos:
            pos["entry_score"] = None
        return pos

    def positions_kennungen_pruefen(self) -> int:
        """Rüstet fehlende Kennungen an ALLEN offenen Positionen nach.

        Faengt die Faelle ab, die aus einem alten bot_state.json geladen wurden
        oder an einer noch nicht angefassten Stelle entstanden sind. Wird vom
        Waechter periodisch aufgerufen.

        Rueckgabe: Anzahl der nachgetragenen Kennungen.
        """
        ergaenzt = 0
        try:
            for sym, pos in list(self.open_positions.items()):
                if isinstance(pos, dict) and not pos.get("position_id"):
                    self.position_kennung_sicherstellen(sym, pos)
                    ergaenzt += 1
        except Exception as e:
            log.warn("RISK", f"Kennungspruefung fehlgeschlagen: {str(e)[:60]}")
        return ergaenzt

    def position_nach_id(self, position_id: str):
        """Sucht eine Position ueber ihre Kennung. (symbol, pos) oder (None, None).

        Wird in Schritt 3 der Hauptzugriffsweg. Jetzt schon vorhanden, damit
        neuer Code bereits ueber die Kennung arbeiten kann.
        """
        for sym, pos in self.open_positions.items():
            if isinstance(pos, dict) and pos.get("position_id") == position_id:
                return sym, pos
        return None, None

    def positionen_fuer_symbol(self, symbol: str) -> list:
        """Alle Positionen eines Coins als LISTE.

        Heute immer 0 oder 1 Eintrag - der Schluessel ist noch das Symbol.
        Ab Schritt 3 koennen es mehrere sein. Wer diese Methode statt
        open_positions[symbol] benutzt, muss dann nicht angefasst werden.
        """
        pos = self.open_positions.get(symbol)
        return [pos] if isinstance(pos, dict) and pos.get("active") else []

    def positionen_je_topf(self) -> dict:
        """Zaehlt offene Positionen je Topf - Grundlage der spaeteren Buchfuehrung."""
        zaehler = {}
        for pos in self.open_positions.values():
            if isinstance(pos, dict) and pos.get("active"):
                topf = pos.get("topf") or "haupt"
                zaehler[topf] = zaehler.get(topf, 0) + 1
        return zaehler

    def check(self, intent, portfolio=None, cycle_phase=""):
        """Prueft einen Intent gegen ALLE Risk-Regeln."""
        portfolio = portfolio or {}

        # SELLS IMMER genehmigen! Nie Verkauf blockieren!
        if intent.side == Side.SELL:
            intent.status = IntentStatus.APPROVED
            intent.risk_approved = True
            intent.risk_reason = "SELL immer erlaubt"
            log.risk("RISK", f"APPROVED SELL {intent.symbol}")
            return intent

        if intent.side == Side.BUY and self.is_in_sleep_mode():
            remaining = int(self.sleep_mode_until - time.time())
            intent.status = IntentStatus.REJECTED
            intent.risk_reason = f"Schlafmodus aktiv (noch {remaining}s)"
            intent.risk_approved = False
            log.risk("RISK", f"REJECTED BUY {intent.symbol}: {intent.risk_reason}")
            return intent

        reasons = []
        # [SCHLAFFALLE-FIX 06.08.2026] Zweite Liste NUR fuer echte Stoerungen.
        #
        # PROBLEM: record_reject() (unten) zaehlte JEDE BUY-Ablehnung und schickte
        # den Bot nach 10 Stueck fuer 15 Minuten in den Schlafmodus - inklusive
        # DCA/Nachkauf ("[DCA] Runde uebersprungen - Schlafmodus").
        # Bei 3 Coins und max_open_positions=3 ist der Bot regelmaessig voll und
        # lehnt dann voellig KORREKT ab. Im Log vom 06.08.2026 22:41 fuehrte das
        # dazu, dass er von 14 Minuten Laufzeit 10 Minuten im Zwangsschlaf lag -
        # er bestrafte sich fuer Wohlverhalten.
        #
        # UNTERSCHEIDUNG:
        #   Kapazitaet/Absicht -> "bin voll", "hab ich schon", "Baerenmarkt",
        #                         "Cooldown", Exposure-/Sektorgrenze.
        #                         Das ist der Bot, der korrekt arbeitet. KEINE Pause.
        #   Stoerung           -> Kapitalbasis unbekannt, Drawdown-Limit gerissen.
        #                         Hier ist die Pause sinnvoll.
        stoerungen = []

        # 1. Kill-Switch
        # [25.09.2026] Nur noch, wenn risk.kill_switch_enabled true ist (war
        # ein Scheinschalter). Dazu der Tagesreset und die Sammel-Notbremse,
        # beide im Schatten - siehe _notbremse_tageswechsel/_notbremse_folgen.
        if self.kill_switch_an:
            self._notbremse_tageswechsel()
            self._notbremse_folgen()
            if self.kill_switch.active:
                intent.status = IntentStatus.REJECTED
                intent.risk_reason = f"Kill-Switch: {self.kill_switch.trigger_reason}"
                intent.risk_approved = False
                log.risk("RISK", f"REJECTED {intent.side.value} {intent.symbol}: {intent.risk_reason}")
                return intent

            if self.kill_switch.check():
                self._notbremse_folgen()
                intent.status = IntentStatus.REJECTED
                intent.risk_reason = f"Kill-Switch ausgeloest: {self.kill_switch.trigger_reason}"
                intent.risk_approved = False
                log.risk("RISK", f"REJECTED {intent.side.value} {intent.symbol}: {intent.risk_reason}")
                return intent

        # 2. Drawdown-Guard
        # [25.09.2026] update_equity() hatte keinen einzigen Aufrufer - der
        # Hoechststand blieb 0, die Regel konnte nie greifen (v7-Befund 119).
        # Jetzt wird der Kapitalstand bei jeder Kaufpruefung nachgefuehrt.
        # Eingreifen darf die Regel nur mit Schalter drawdown_stopp = ACTIVE;
        # Vorgabe ist SHADOW, dann wird nur notiert.
        _eq_dd = portfolio.get("total_equity", 0) or 0
        if intent.side == Side.BUY and _eq_dd > 0:
            self.drawdown.update(_eq_dd)
        if not self.drawdown.is_safe():
            _g = (f"Drawdown {self.drawdown.current_drawdown_pct:.1f}% >= "
                  f"{self.drawdown.max_drawdown_pct}%")
            if entscheidet("drawdown_stopp", haette="alle Kaeufe sperren",
                           grund=f"{_g} (Hoechststand "
                                 f"{self.drawdown.peak_equity:.2f}$, jetzt "
                                 f"{_eq_dd:.2f}$)"):
                reasons.append(_g)
                stoerungen.append(_g)      # echtes Warnsignal -> Pause gerechtfertigt

        # 3. Max Positionen (aus aktivem Trading-Modus, falls verfuegbar)
        open_count = sum(1 for p in self.open_positions.values() if p.get("active"))
        # Nutze portfolio_manager max_positions wenn moeglich (skaliert mit Modus)
        max_pos = self.config.max_open_positions
        if hasattr(self, '_portfolio_manager') and self._portfolio_manager:
            try:
                max_pos = self._portfolio_manager.get_max_positions()
            except Exception:
                pass
        if intent.side == Side.BUY and open_count >= max_pos:
            reasons.append(f"Max Positionen: {open_count}/{max_pos}")

        # 4. Exposure-Check
        # [E9 29.07.] Vorgabe war 10000 - auf einem 500-$-Konto haette ein
        # fehlendes portfolio-Dict damit JEDE Exposure-Grenze aufgehoben
        # (alles ist klein gegen 10.000). Fehlender Wert = kein Freibrief:
        # 0 -> der Block unten wird uebersprungen statt blind durchgewinkt.
        total_eq = portfolio.get("total_equity", 0) or 0
        # [FAIL-SAFE 05.08.2026] Der E9-Kommentar oben sagt "kein Freibrief",
        # aber das blosse UEBERSPRINGEN des Blocks bei total_eq <= 0 ist
        # genau einer: es wird nichts geprueft UND nichts abgelehnt, der
        # Kauf laeuft ohne Exposure-Kontrolle weiter. Jetzt wird abgelehnt.
        # Kein Handel ohne belastbare Kapitalbasis - lieber eine Chance
        # verpassen als blind kaufen.
        if intent.side == Side.BUY and total_eq <= 0:
            _g = ("Exposure nicht pruefbar: total_equity unbekannt "
                  "oder <= 0")
            reasons.append(_g)
            stoerungen.append(_g)      # Kapitalbasis kaputt -> echte Stoerung
        if intent.side == Side.BUY and total_eq > 0:
            exp_check = self.exposure.check_coin_exposure(
                intent.symbol, intent.amount_usd, total_eq, self.open_positions)
            if not exp_check["ok"]:
                if exp_check.get("adjusted_amount", 0) > 5:
                    intent.amount_usd = exp_check["adjusted_amount"]
                    log.info("RISK", f"Exposure angepasst: {intent.amount_usd:.2f}$")
                else:
                    reasons.append(exp_check["reason"])

            sec_check = self.exposure.check_sector_exposure(
                intent.symbol, intent.amount_usd, total_eq, self.open_positions)
            if not sec_check["ok"]:
                reasons.append(sec_check["reason"])

        # 5. Cooldown nach Verlusten (FIX 5: COIN-SPEZIFISCH, nicht global!)
        if intent.side == Side.BUY:
            coin_losses = self.coin_consecutive_losses.get(intent.symbol, 0)
            cooldown_threshold = self.config.cooldown_after_losses
            if coin_losses >= cooldown_threshold:
                # Score-Override: Hoher Score umgeht Cooldown
                # [25.09.2026] Schwelle 8 statt unerreichbarer 50, und nur mit
                # Schalter verlustsperre_aufhebung = ACTIVE (Vorgabe SHADOW).
                intent_score = getattr(intent, 'score', 0) or 0
                _ab = self.coin_cooldown_override_score
                _aufheben = False
                if intent_score >= _ab:
                    _aufheben = entscheidet(
                        "verlustsperre_aufhebung", symbol=intent.symbol,
                        haette=f"Sperre aufheben, Kauf pruefen (Score {intent_score})",
                        grund=f"{coin_losses} Verluste in Folge, Score "
                              f"{intent_score} >= {_ab}",
                        preis=getattr(intent, "entry_price", None))
                if _aufheben:
                    log.info("RISK", f"Cooldown OVERRIDE fuer {intent.symbol}: "
                                      f"Score {intent_score} >= {_ab}")
                elif intent_score < _ab:
                    reasons.append(f"Cooldown: {coin_losses}x {intent.symbol} Verlust "
                                   f"(Score {intent_score} < {_ab})")
                else:
                    reasons.append(f"Cooldown: {coin_losses}x {intent.symbol} Verlust "
                                   f"(Score {intent_score} >= {_ab}, Aufhebung "
                                   f"nicht scharf)")

        # 6. Zyklusphase
        if cycle_phase in ("MID_BEAR", "DEEP_BEAR", "CAPITULATION"):
            asset = intent.symbol.split("/")[0] if "/" in intent.symbol else ""
            if asset not in ("BTC", "ETH") and intent.side == Side.BUY:
                # [25.09.2026] Schalter baerenmarkt wird jetzt gelesen.
                if entscheidet("baerenmarkt", symbol=intent.symbol,
                               haette="BUY blockieren",
                               grund=f"Zyklus {cycle_phase}: nur BTC+ETH",
                               preis=getattr(intent, "entry_price", None)):
                    reasons.append("Baerenmarkt: nur BTC+ETH")

        # 7. Bereits in Position
        if intent.symbol in self.open_positions and self.open_positions[intent.symbol].get("active"):
            if intent.side == Side.BUY:
                reasons.append("Bereits in Position")

        # 8. Position Sizing anpassen (NICHT unter 50% des gewollten Betrags!)
        if intent.side == Side.BUY and not reasons:
            # Exposure-Limit aktualisieren falls Config geaendert wurde
            new_max = max(self.config.max_exposure_per_coin_pct,
                         intent.amount_usd / total_eq * 100 + 5 if total_eq > 0 else 25)
            self.exposure.max_coin_pct = max(self.exposure.max_coin_pct, new_max)

            optimal = self.sizer.calculate(
                total_eq, intent.confidence, cycle_phase,
                regime=intent.regime if hasattr(intent, 'regime') else "UNKNOWN")
            # Minimum: Nie unter 50% des gewollten Betrags
            min_amount = intent.amount_usd * 0.5
            if optimal < min_amount:
                optimal = min_amount
            if optimal < intent.amount_usd:
                intent.amount_usd = optimal
                log.info("RISK", f"Sizing: {optimal:.2f}$ (Confidence: {intent.confidence:.2f})")

        # Entscheidung
        if reasons:
            intent.status = IntentStatus.REJECTED
            intent.risk_reason = " | ".join(reasons)
            intent.risk_approved = False
            # [SCHLAFFALLE-FIX 06.08.2026] Art der Ablehnung sichtbar machen -
            # sonst sieht "REJECTED" fuer den Leser aus wie ein Problem, obwohl
            # der Bot in den allermeisten Faellen einfach nur voll ist.
            _art = "STOERUNG" if stoerungen else "Kapazitaet"
            log.risk("RISK", f"REJECTED [{_art}] {intent.symbol}: {intent.risk_reason}")
            if intent.side == Side.BUY:
                # NUR echte Stoerungen zaehlen auf den Schlafmodus ein.
                # Kapazitaets-Ablehnungen lassen den Zaehler unveraendert -
                # sie setzen ihn aber auch NICHT zurueck, sonst koennte eine
                # Mischung aus Stoerung und "bin voll" den Schutz aushebeln.
                if stoerungen:
                    self.record_reject()
        else:
            intent.status = IntentStatus.APPROVED
            intent.risk_approved = True
            intent.risk_reason = "OK"
            log.risk("RISK", f"APPROVED {intent.symbol} {intent.side.value} {intent.amount_usd:.2f}$")
            if intent.side == Side.BUY:
                self.record_approve()

        return intent

    def record_result(self, symbol, pnl, side):
        """Ergebnis eines Trades verarbeiten.

        FIX 5: Per-Coin Cooldown Tracking.
        FIX 6: Position wird ATOMAR aus open_positions entfernt (nicht nur "active=False").
        """
        if side == Side.SELL:
            # Per-Coin Cooldown
            if pnl < 0:
                self.kill_switch.add_loss(abs(pnl))
                if self.kill_switch_an:
                    self._notbremse_folgen()
                self.consecutive_losses += 1
                self.coin_consecutive_losses[symbol] = \
                    self.coin_consecutive_losses.get(symbol, 0) + 1
            else:
                self.consecutive_losses = 0
                self.coin_consecutive_losses[symbol] = 0

            # FIX 6: ATOMARES Loeschen aus open_positions
            # Vorher: nur active=False (Position bleibt im Dict -> "Max Positionen 33"!)
            # Jetzt: komplett raus
            if symbol in self.open_positions:
                del self.open_positions[symbol]
                log.info("RISK", f"Position {symbol} aus Register entfernt "
                                  f"({len(self.open_positions)} aktiv)")
        elif side == Side.BUY:
            # [TOEPFE SCHRITT 1 - 07.08.2026] Wie bisher wird das Wert-Dict
            # neu aufgebaut (entry_price, qty usw. setzt danach app.py). NEU
            # ist nur: eine bereits vergebene Kennung geht dabei nicht
            # verloren. app.py:1260 legt bei TWAP schon vorher eine Position
            # an - ohne diese Uebernahme bekaeme sie hier eine zweite ID und
            # dieselbe Position haette zwei Kennungen.
            _alt = self.open_positions.get(symbol) or {}
            _neu = {"active": True, "time": time.time()}
            # [SCORE-FIX 10.08.2026] entry_score mit uebernehmen - sonst geht
            # der Einstiegs-Score hier verloren und die Verkaufszeile im
            # Journal kann ihn nicht mehr ausweisen.
            for _k in ("position_id", "topf", "strategie_id", "eroeffnet_ts",
                       "entry_score"):
                if isinstance(_alt, dict) and _alt.get(_k):
                    _neu[_k] = _alt[_k]
            self.position_kennung_sicherstellen(symbol, _neu)
            self.open_positions[symbol] = _neu
        self.daily_trades += 1

    def reset_all_positions(self):
        """Schliesst ALLE offenen Positionen sicher (fuer Paper-Mode Reset).
        Returns: Anzahl der geschlossenen Positionen.
        """
        count = 0
        # Liste kopieren da wir waehrend Iteration loeschen
        symbols = list(self.open_positions.keys())
        for sym in symbols:
            try:
                self.open_positions[sym]["active"] = False
            except Exception:
                pass
            count += 1
        # Komplett leeren
        self.open_positions.clear()
        # Trade-Statistiken zuruecksetzen
        self.consecutive_losses = 0
        self.coin_consecutive_losses = {}     # FIX 5: Per-coin cooldowns auch reset
        self.daily_trades = 0
        try:
            self.kill_switch.reset_daily()
        except Exception:
            pass
        log.info("RISK", f"Alle Positionen geschlossen: {count}")
        return count

    def increase_max_positions(self, new_max: int):
        """Temporaer das Max-Positions Limit erhoehen."""
        old = self.config.max_open_positions
        self.config.max_open_positions = new_max
        log.info("RISK", f"Max Positionen: {old} -> {new_max}")

    def update_equity(self, equity):
        """Aktualisiert Drawdown mit aktuellem Equity."""
        self.drawdown.update(equity)

    def reset_daily(self):
        """Tages-Reset."""
        self.kill_switch.reset_daily()
        self.daily_trades = 0
        log.info("RISK", "Tages-Reset")

    # ------------------------------------------------------------------
    # [25.09.2026] Notbremse: Tagesreset und Sammel-Notbremse (v7-Befund 119)
    # ------------------------------------------------------------------
    def _notbremse_tageswechsel(self):
        """Tagesreset der Notbremse um 00:00 UTC - im Schatten.

        Die Notbremse heisst "Tages-Verlust", zaehlte aber seit Programm-
        start: einen automatischen Reset gab es nie, nur den Knopf im
        Cockpit. Ob der Reset gebraucht wird, zeigen erst die Notizen -
        deshalb Schalter notbremse_tagesreset, Vorgabe SHADOW.
        """
        heute = time.strftime("%Y-%m-%d", time.gmtime())
        if self._notbremse_tag is None:
            self._notbremse_tag = heute
            return
        if heute == self._notbremse_tag:
            return
        self._notbremse_tag = heute
        verlust = float(self.kill_switch.daily_loss or 0)
        if verlust <= 0 and not self.kill_switch.active:
            return                          # nichts zurueckzusetzen
        _was = f"Verlustzaehler {verlust:.2f}$ auf 0 setzen"
        if self.kill_switch.active:
            _was += " und die ausgeloeste Notbremse loesen"
        if entscheidet("notbremse_tagesreset", haette=_was,
                       grund=f"neuer Tag {heute} (UTC), Grenze "
                             f"{self.kill_switch.max_daily_loss:.2f}$",
                       sperre_s=0):
            self.kill_switch.reset_daily()

    def _notbremse_folgen(self):
        """Sammel-Notbremse, einmal je Ausloesung - im Schatten.

        Vorher tot: _close_all_positions_safety() in app.py hatte keinen
        Aufrufer, und EVENT_KILL_SWITCH wurde nirgends gesendet. Die
        Notbremse sperrte nur neue Kaeufe. Mit Schalter sammel_notbremse =
        ACTIVE ruft sie den Rueckruf, den app.py setzt (alles schliessen,
        Bot anhalten). Vorgabe SHADOW: nur notieren.
        """
        if not self.kill_switch.active:
            self._notbremse_gemeldet = False
            return
        if self._notbremse_gemeldet:
            return
        self._notbremse_gemeldet = True
        offen = [s for s, p in self.open_positions.items()
                 if isinstance(p, dict) and p.get("active")]
        if entscheidet("sammel_notbremse",
                       haette=f"alle {len(offen)} Positionen schliessen und "
                              f"den Bot anhalten",
                       grund=f"Notbremse: {self.kill_switch.trigger_reason}",
                       zusatz=",".join(offen), sperre_s=0):
            if callable(self.notbremse_rueckruf):
                self.notbremse_rueckruf(self.kill_switch.trigger_reason)
            else:
                log.error("RISK", "Sammel-Notbremse ist ACTIVE, aber kein "
                                  "Rueckruf angemeldet - es wurde NICHTS geschlossen")



    def is_in_sleep_mode(self) -> bool:
        """STEP 1: Prueft ob Bot gerade im Schlafmodus ist."""
        return time.time() < self.sleep_mode_until

    def record_reject(self):
        """STEP 1: Wird aufgerufen bei jedem REJECT."""
        self.consecutive_rejects += 1
        if self.consecutive_rejects >= self.sleep_threshold:
            self.sleep_mode_until = time.time() + self.sleep_duration_sec
            log.warn("AUTO-DEFENSE",
                     f"Schlafmodus aktiviert: {self.consecutive_rejects} Rejects in Folge - "
                     f"pausiere fuer {self.sleep_duration_sec//60} Min")
            self.consecutive_rejects = 0

    def record_approve(self):
        """STEP 1: Wird aufgerufen bei jedem APPROVE."""
        self.consecutive_rejects = 0

    def check_auto_defense_sells(self, positions_with_prices, market_regime, mtf_direction):
        """STEP 1: Prueft ob Positionen aktiv verkauft werden sollen.

        Triggers nur bei TRENDING_DOWN + MTF BEARISH.
        Verkauft NUR die 2 schlechtesten Positionen die ueber Loss-Schwelle sind.
        """
        regime_str = str(market_regime).upper()
        if regime_str not in ("TRENDING_DOWN", "TRENDINGDOWN"):
            return []
        if str(mtf_direction).upper() != "BEARISH":
            return []

        loss_candidates = []
        for pos in positions_with_prices:
            entry = pos.get("entry_price", 0)
            current = pos.get("current_price", 0)
            if entry <= 0 or current <= 0:
                continue
            pnl_pct = ((current / entry) - 1) * 100
            if pnl_pct < -self.defense_loss_threshold_pct:
                loss_candidates.append({
                    "symbol": pos["symbol"],
                    "pnl_pct": pnl_pct,
                    "current_price": current,
                    "qty": pos.get("qty", 0),
                })

        if not loss_candidates:
            return []

        loss_candidates.sort(key=lambda x: x["pnl_pct"])
        to_sell = loss_candidates[:self.defense_max_sells_per_cycle]

        # [25.09.2026] Hier stand "verkauft" - verkauft wird aber erst in
        # app.py, und nur mit Schalter auto_verteidigung = ACTIVE. Die Zeile
        # ist gedrosselt (einmal je Symbol in 10 Minuten): die Pruefung laeuft
        # im 12-s-Takt je Position, seit sie Daten bekommt.
        if not hasattr(self, "_defense_gemeldet"):
            self._defense_gemeldet = {}
        _jetzt = time.time()
        for s in to_sell:
            if _jetzt - self._defense_gemeldet.get(s["symbol"], 0) >= 600:
                self._defense_gemeldet[s["symbol"]] = _jetzt
                log.warn("AUTO-DEFENSE",
                         f"{s['symbol']} ist Verkaufskandidat @ PnL {s['pnl_pct']:+.2f}% "
                         f"(Bearish Market Protect)")

        return to_sell

    def get_status(self):
        return {
            "kill_switch": self.kill_switch.get_status(),
            "drawdown": self.drawdown.get_status(),
            "exposure": {"max_coin": self.exposure.max_coin_pct, "max_sector": self.exposure.max_sector_pct},
            "sizing": self.sizer.get_status(),
            "trades_today": self.daily_trades,
            "open_positions": sum(1 for p in self.open_positions.values() if p.get("active")),
            "max_positions": self.config.max_open_positions,
            "loss_streak": self.consecutive_losses,
        }
