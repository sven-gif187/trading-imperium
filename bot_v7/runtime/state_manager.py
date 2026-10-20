# -*- coding: utf-8 -*-
"""
runtime/state_manager.py - Monolith-Split Schritt 2 (SPLIT-2)

Das Gedaechtnis des Bots: auto_save (zyklisches Sichern des Zustands)
und restore_positions (Wiederherstellen beim Start, inkl. RESTORE-HARDEN
Fallback-Preiskette gegen Geisterpositionen).

Code WORTWOERTLICH aus app.py umgezogen (Stand 09.07.2026, nach
Restore-Haertung + E6-B). self.X -> self.app.X, sonst NULL Aenderung.
Verbesserungen hier NUR als eigene Tickets, nie beim Umzug.
"""
from core.logger import log
import json
import os
import time


class StateManager:
    """Delegat: haelt eine Referenz auf die App und arbeitet auf deren Zustand."""

    def __init__(self, app):
        self.app = app

    def auto_save(self):
        """Speichert den KOMPLETTEN Zustand periodisch."""
        try:
            self.app.state.save()
            self.app.journal.save()
            # === COUNTER-SYNC: tote State-Zaehler aus Journal spiegeln ===
            try:
                _js = self.app.journal.get_stats()
                self.app.state.set("realized_pnl", round(float(_js.get("total_pnl", 0)), 2))
                self.app.state.set("trade_count", int(_js.get("total_trades", 0)))
            except Exception:
                pass
            # Equity-History tracken
            bal = self.app.execution.get_balance()
            usdc = bal["total"].get("USDC", 0) + bal["total"].get("USDT", 0)
            btc_val = self.app.btc_accumulator.total_btc * self.app.data_agent.price_cache.get("BTC/USDC", 0)
            # Coin-Positionen bewerten
            pos_val = 0
            for sym, pos in self.app.risk_engine.open_positions.items():
                if pos.get("active"):
                    price = self.app.data_agent.price_cache.get(sym, 0)
                    pos_val += pos.get("qty", 0) * price
            total_equity = usdc + btc_val + pos_val
            equity_history = self.app.state.get("equity_history", [])
            equity_history.append({"time": time.strftime("%H:%M"), "equity": round(total_equity, 2),
                                   "usdc": round(usdc, 2), "btc_val": round(btc_val, 2)})
            if len(equity_history) > 500:
                equity_history = equity_history[-500:]
            self.app.state.set("equity_history", equity_history)
            # Equity Tracker (fuer Chart)
            trade_pnl = sum(t.get("pnl", 0) for t in self.app.journal.get_all()
                           if t.get("type") in ("SELL", "sell") and isinstance(t.get("pnl"), (int, float)))
            self.app.equity_tracker.record(usdc + pos_val, btc_val, trade_pnl)
            self.app.equity_tracker.save()
            # Open Positions backup
            positions_data = {}
            for sym, pos in self.app.risk_engine.open_positions.items():
                if pos.get("active"):
                    positions_data[sym] = {
                        "entry_price": pos.get("entry_price", 0),
                        "highest_price": pos.get("highest_price", 0),
                        "qty": pos.get("qty", 0),
                        "active": True, "mode": pos.get("mode", "SL"),
                        # [E9 29.07.] Ohne diese vier Felder waeren nach jedem
                        # Neustart die Kostenbasis (-> P&L rechnet wieder ohne
                        # Kaufgebuehr), die Nachkauf-Stufe (-> Leiter faengt bei
                        # 1 an) und die Breakeven-Sperre weg.
                        "cost_basis": pos.get("cost_basis", 0),
                        "dca_levels": pos.get("dca_levels", 1),
                        "lowest_price": pos.get("lowest_price", pos.get("entry_price", 0)),
                        "hoechst_pnl_pct": pos.get("hoechst_pnl_pct", 0.0),
                        # [TOEPFE SCHRITT 1 - 07.08.2026] Kennungsfelder MUESSEN
                        # hier mit rein. Diese Liste ist eine Whitelist: was nicht
                        # aufgezaehlt ist, ueberlebt keinen Neustart. Genau darum
                        # geht es im E9-Kommentar direkt darueber - dort fehlten
                        # vier Felder und Kostenbasis wie Nachkaufstufe waren nach
                        # jedem Start wieder auf Anfang. Ohne diese drei Zeilen
                        # bekaeme dieselbe Position bei jedem Neustart eine neue
                        # Kennung, und keine Auswertung ueber Zeit waere moeglich.
                        "position_id": pos.get("position_id", ""),
                        "topf": pos.get("topf", "haupt"),
                        "strategie_id": pos.get("strategie_id", ""),
                        "eroeffnet_ts": pos.get("eroeffnet_ts", pos.get("time", 0)),
                        # [BEFUND 88, GLIED 3 - 11.09.2026] Diese zwei Felder
                        # fehlten hier, und nur hier. app.py:1904 schreibt sie
                        # beim Kauf an die Position, runtime/exit_monitor.py:443
                        # liest sie beim Verkauf wieder aus - aber dazwischen
                        # liegt ein Neustart, und die Whitelist warf sie weg.
                        # Ergebnis: jede Position, die einen Neustart erlebte,
                        # wurde mit entry_score=None verkauft. Am 11.09. am
                        # lebenden Objekt belegt: die offene BTC-Position trug
                        # 13 Felder, keines davon der Score.
                        # Ohne diese zwei Zeilen ist Befund 103 ("traegt der
                        # Einstiegs-Score?") nicht vorwaerts pruefbar - die
                        # Stichprobe waechst nur um Positionen, die innerhalb
                        # EINER Bot-Laufzeit auf- und wieder zugehen.
                        "entry_score": pos.get("entry_score"),
                        "entry_strategie": pos.get("entry_strategie", ""),
                        # [15.09.2026] Die Kaufwelle und die bereits
                        # bedienten Fibonacci-Ziele. Ohne diese vier
                        # Felder waere nach jedem Neustart nicht mehr
                        # bekannt, aus welcher Welle die Position stammt -
                        # der Fibonacci-Ausstieg fiele still auf die alten
                        # Prozentmarken zurueck, und `ziele_erreicht`
                        # faenge bei null an: schon verkaufte Ziele wuerden
                        # ein zweites Mal bedient.
                        #
                        # Das ist dieselbe Falle wie Befund 88. Diese Liste
                        # ist eine Whitelist - was hier nicht steht,
                        # ueberlebt keinen Neustart, egal wie sorgfaeltig
                        # es beim Kauf geschrieben wurde.
                        "welle_hoch": pos.get("welle_hoch"),
                        "welle_tief": pos.get("welle_tief"),
                        "welle_zeitrahmen": pos.get("welle_zeitrahmen", ""),
                        "ziele_erreicht": pos.get("ziele_erreicht", []),
                    }
            # WURZEL-FIX: open_positions_backup NICHT mit {} ueberschreiben,
            # wenn noch Coin-Bestaende existieren (sonst Buchhaltungs-Desync).
            if positions_data:
                self.app.state.set("open_positions_backup", positions_data)
            else:
                try:
                    _pb = getattr(self.app.execution, "_paper_balances", {}) or {}
                    _has_coins = any(k not in ("USDC","USDT","EUR","USD") and float(v) > 0
                                     for k, v in _pb.items())
                except Exception:
                    _has_coins = False
                if not _has_coins:
                    self.app.state.set("open_positions_backup", positions_data)
                # sonst: altes Backup behalten, NICHT leeren
            # [PATCH 54] Verlustzaehler mitsichern. Ohne das beginnt er bei
            # jedem Neustart bei null - und die Cooldown-Sperre kann nie
            # greifen (0 Ausloesungen in 12 Tagen, obwohl es Serien von
            # 4/3/3 gab). Der Kill-Switch sichert seinen Tagesverlust
            # laengst; hier fehlte dieselbe Behandlung. Befund 54.
            try:
                self.app.state.set(
                    "coin_consecutive_losses",
                    dict(getattr(self.app.risk_engine,
                                 "coin_consecutive_losses", {}) or {}))
                self.app.state.set(
                    "consecutive_losses",
                    int(getattr(self.app.risk_engine,
                                "consecutive_losses", 0) or 0))
            except Exception as _cl_e:
                from core.logger import log as _log
                _log.warn("STATE", f"Verlustzaehler nicht gesichert: "
                                   f"{str(_cl_e)[:60]}")

            # === BALANCE PERSIST FIX ===
            # Auch Paper-Balances speichern (USDC + Coin-Mengen).
            # Damit USDC beim Restart nicht auf 300 zurueckspringt.
            if self.app.config.trading.mode == "paper":
                try:
                    pbal = getattr(self.app.execution, "_paper_balances", None)
                    if pbal:
                        self.app.state.set("paper_balances_backup", dict(pbal))
                except Exception:
                    pass
        except Exception:
            pass


    def restore_positions(self):
        """Stellt offene Positionen nach Neustart wieder her.

        FIX 6: Ueberspringt inaktive/leere Positionen damit nicht alte
        deaktivierte Positionen den Counter aufblaehen ('Max Positionen 33').

        BALANCE PERSIST FIX: Stellt jetzt auch die Paper-Balance wieder
        her (USDC + Coin-Mengen), sodass die freie Balance nicht auf
        initial_paper_balance zurueckspringt.
        """
        # === RESTORE-ONCE FIX (12.06.2026) ===
        # Restore lief beim Start zweimal (1. Trading-Tick + verzoegerte
        # Init). Der zweite Lauf ueberschrieb frische Kaeufe aus dem
        # Zeitfenster dazwischen (70$-SOL-Vorfall). Daher: nur 1x pro Lauf.
        if getattr(self.app, "_restore_done_once", False):  # [GUARD-FIX 10.07.]
            log.info("APP", "Restore uebersprungen (bereits beim Start erledigt)")
            return
        self.app._restore_done_once = True


        # === COUNTER SELF-HEALING (gegen Absturz-Schaden) ===
        try:
            import json as _json
            _tp = os.path.join("data_store", "trades_v5.json")
            if os.path.exists(_tp):
                with open(_tp, encoding="utf-8") as _f:
                    _td = _json.load(_f)
                _trades = _td if isinstance(_td, list) else _td.get("trades", [])
                if len(_trades) >= 5:
                    _real = round(sum(float(t.get("pnl") or 0) for t in _trades), 2)
                    _cnt = len(_trades)
                    _real_s = float(self.app.state.get("realized_pnl", 0) or 0)
                    _cnt_s = int(self.app.state.get("trade_count", 0) or 0)
                    if _cnt_s == 0 or abs(_real_s - _real) > 1.0:
                        self.app.state.set("realized_pnl", _real)
                        self.app.state.set("trade_count", _cnt)
                        log.warn("APP", f"SELF-HEAL: Zaehler korrigiert "
                                 f"({_cnt_s}->{_cnt} Trades, {_real_s:+.2f}$->{_real:+.2f}$) "
                                 f"- vermutlich Absturz-Schaden")
        except Exception as _he:
            log.warn("APP", "Counter-Self-Heal fehlgeschlagen: " + str(_he)[:80])

        # === BALANCE PERSIST FIX ===
        # 0. Paper-Balance VOR den Positionen wiederherstellen
        if self.app.config.trading.mode == "paper":
            # === BUGFIX RESET-MARKER ===
            # Pruefe ob ein Reset stattgefunden hat
            reset_marker = os.path.join("data_store", ".reset_marker")
            if os.path.exists(reset_marker):
                try:
                    initial = float(self.app.config.trading.initial_paper_balance)
                except Exception:
                    initial = 1000.0
                self.app.execution._paper_balances = {"USDC": initial}
                # State-Backup leeren damit weiter unten KEINE alten Positionen geladen werden
                try:
                    self.app.state.set("paper_balances_backup", {"USDC": initial})
                    self.app.state.set("open_positions_backup", {})
                    self.app.state.set("open_orders_backup", {})
                    self.app.state.set("realized_pnl", 0.0)
                    self.app.state.set("trade_count", 0)
                except Exception:
                    pass
                # Marker loeschen
                try:
                    os.remove(reset_marker)
                except Exception:
                    pass
                log.info("APP", f"RESET-MARKER erkannt - frischer Start mit {initial:.2f} USDC")
            else:
                try:
                    saved_bal = self.app.state.get("paper_balances_backup", None)
                    if saved_bal and isinstance(saved_bal, dict):
                        # === DISPLAY-BUG FIX v2 ===
                        # Wenn _paper_balances schon Coins enthaelt (aktive Trades
                        # seit Bot-Start), Restore UEBERSPRINGEN - sonst werden die
                        # gekauften Coins ueberschrieben und Cash faelschlich erhoeht.
                        current_bal = getattr(self.app.execution, "_paper_balances", {}) or {}
                        current_assets = [k for k in current_bal if k not in ("USDC", "USDT")]
                        if current_assets:
                            log.info("APP", f"Balance-Restore uebersprungen "
                                            f"(aktive Trades: {len(current_assets)} Assets)")
                        else:
                            self.app.execution._paper_balances = dict(saved_bal)
                            usdc = saved_bal.get("USDC", 0) + saved_bal.get("USDT", 0)
                            log.info("APP", f"Paper-Balance wiederhergestellt: USDC={usdc:.2f}$ "
                                            f"({len(saved_bal)} Assets)")
                        # === ENDE DISPLAY-BUG FIX v2 ===
                except Exception as e:
                    log.warn("APP", f"Balance-Restore Fehler: {e}")

        restored = 0
        skipped = 0
        # 1. Aus State-Backup
        # [PATCH 54] Verlustzaehler zurueckholen, bevor Positionen geladen
        # werden. Reihenfolge ist egal fuers Ergebnis, aber so steht der
        # Zaehler auch dann richtig, wenn kein Positions-Backup existiert.
        try:
            _cl = self.app.state.get("coin_consecutive_losses", {}) or {}
            if isinstance(_cl, dict) and _cl:
                self.app.risk_engine.coin_consecutive_losses = {
                    str(k): int(v) for k, v in _cl.items()}
                from core.logger import log as _log
                _log.info("STATE", f"Verlustzaehler wiederhergestellt: "
                                   f"{self.app.risk_engine.coin_consecutive_losses}")
            _g = self.app.state.get("consecutive_losses", 0)
            if _g:
                self.app.risk_engine.consecutive_losses = int(_g)
        except Exception as _cl_e:
            from core.logger import log as _log
            _log.warn("STATE", f"Verlustzaehler nicht geladen: {str(_cl_e)[:60]}")

        positions = self.app.state.get("open_positions_backup", {})
        if positions:
            for sym, pos in positions.items():
                # FIX 6: Strenge Filterung - nur AKTIVE Positionen mit Menge!
                if not pos.get("active"):
                    skipped += 1
                    continue
                if pos.get("qty", 0) <= 0:
                    skipped += 1
                    continue
                if pos.get("entry_price", 0) <= 0:
                    skipped += 1
                    continue
                self.app.risk_engine.open_positions[sym] = pos
                restored += 1
        # WURZEL-FIX: NICHT abbrechen wenn Backup leer - aus Balances
        # rekonstruieren (sonst bleiben Coins als Geisterbestand liegen).
        elif self.app.config.trading.mode != "paper":
            # ==========================================================
            # [14.09.2026] Hier stand ein nacktes `return`.
            #
            # Damit galt der WURZEL-FIX im Kommentar darueber nur fuer
            # den Papierhandel. Im Live-Modus stieg die Funktion an
            # dieser Stelle aus und liess vorhandene Coins liegen -
            # genau der Geisterbestand, gegen den der Fix gebaut wurde.
            #
            # Folge am ersten Live-Abend: 0,00041 BTC (~32 $, also 90 %
            # des Kontos) lagen ausserhalb jeder Ueberwachung. Der
            # Waechter meldete es korrekt als ALARM
            # (features/waechter.py:96), aber der Waechter liest nur -
            # er greift bewusst nicht ein. Es gab also eine Meldung und
            # niemanden, der sie ausfuehrt.
            #
            # Zugleich rechnete das Sizing mit 3,69 $ statt 36 $, weil
            # der Bestand nicht mitzaehlte.
            #
            # UNTERSCHIED ZUR PAPIER-REKONSTRUKTION WEITER UNTEN:
            # Dort wird der aktuelle Marktpreis als Einstand gesetzt,
            # und der Code warnt selbst, dass damit ein aufgelaufener
            # Buchverlust unsichtbar wird. Bei echtem Geld ist das nicht
            # hinnehmbar, deshalb wird hier der ECHTE Einstand aus den
            # Ausfuehrungen der Boerse geholt
            # (execution/engine.py: bestand_einstand).
            # ==========================================================
            self._uebernehme_live_bestand()
            return

        # 2. Aus Paper-Balances rekonstruieren (NUR wenn Backup-Positionen da waren)
        if self.app.config.trading.mode == "paper":
            bal = self.app.execution.get_balance()
            for coin in self.app.config.trading.coins:
                asset = coin.split("/")[0]
                qty = bal.get("total", {}).get(asset, 0)
                if qty > 0 and coin not in self.app.risk_engine.open_positions:
                    # === RESTORE-HARDEN: Preis-Fallback, Position nie wegen 0-Preis verlieren ===
                    price = self.app.data_agent.price_cache.get(coin, 0)
                    if price <= 0:
                        try:
                            price = self.app.data_agent.client.fetch_ticker(coin).get("last", 0)
                        except Exception as _pe:
                            log.warn("RESTORE", f"{coin}: Ticker-Preis fehlgeschlagen ({str(_pe)[:50]})")
                    if price <= 0:
                        # Fallback 1: Einstand aus dem Register-Backup
                        _bk = (self.app.state.get("open_positions_backup", {}) or {}).get(coin, {})
                        price = float(_bk.get("entry_price", 0) or 0)
                    if price <= 0:
                        # Fallback 2: letzter Marker-/Kassenwert (verhindert Geisterbestand)
                        price = float(self.app.data_agent.price_cache.get(coin, 0) or 0)
                    if price > 0:
                        self.app.risk_engine.open_positions[coin] = {
                            "active": True, "entry_price": price,
                            "highest_price": price, "lowest_price": price, "qty": qty,
                            # [E9] Rekonstruktion: Kostenbasis grob aus Preis*Menge
                            # plus 0.1 % Gebuehr. Genauer geht es hier nicht - der
                            # echte Einstand ist nur im Journal, und der Weg hierher
                            # bedeutet ja gerade, dass das Register fehlt.
                            "cost_basis": qty * price * 1.001,
                            "dca_levels": 1, "hoechst_pnl_pct": 0.0,
                            "time": time.time(), "_reconstructed": True,
                        }
                        restored += 1
                        log.warn("RESTORE", f"{coin}: {qty:.6f} @ {price:,.2f}$ (aus Balance REKONSTRUIERT) "
                                            f"- ACHTUNG: Einstand = aktueller Preis, ein bereits "
                                            f"aufgelaufener Buchverlust ist damit unsichtbar und der "
                                            f"Stop-Loss haengt am falschen Bezugspunkt!")
                    else:
                        # LETZTE Sicherung: Position mit Preis 0 anlegen waere gefaehrlich
                        # (Stop-Loss-Division). Stattdessen laut WARNEN, damit der
                        # Waechter-Alarm eine Ursache im Log hat statt stiller Luecke.
                        log.error("RESTORE", f"{coin}: {qty:.6f} Coins OHNE Preis - Position bleibt unueberwacht bis Preis da ist! (kein stiller Verlust)")

        if restored > 0:
            log.info("APP", f"Positionen wiederhergestellt: {restored} aktiv")
        if skipped > 0:
            log.info("APP", f"  ({skipped} inaktive/leere Positionen verworfen)")

    # ==================================================================
    # Live-Bestandsuebernahme  (14.09.2026)
    # ==================================================================
    def _uebernehme_live_bestand(self):
        """Nimmt vorhandene Coins auf dem Live-Konto ins Positionsregister.

        Der Anlass steht ausfuehrlich an der Aufrufstelle in
        restore_positions(). Kurz: Ohne diese Uebernahme liegen echte
        Coins ausserhalb jeder Ueberwachung - kein Stop-Loss, kein
        Trailing, und das Sizing rechnet mit einem zu kleinen Kapital.

        DREI DINGE, DIE HIER ANDERS SIND ALS IM PAPIERHANDEL:

        1. Der Einstand kommt aus den ECHTEN Ausfuehrungen der Boerse,
           nicht aus dem aktuellen Kurs. Sonst waere ein bereits
           aufgelaufener Buchverlust unsichtbar und der Stop-Loss
           haengt am falschen Bezugspunkt.

        2. Staub wird NICHT uebernommen. Liegt die Menge unter dem
           Mindesthandelsbetrag der Boerse, koennte ein Stop-Loss sie
           gar nicht verkaufen - die Position waere eine Dauerbaustelle,
           die bei jedem Ausloesen scheitert. Solche Reste werden
           gemeldet, aber nicht gefuehrt.

        3. Ohne belegbaren Einstand wird KEINE Position angelegt. Lieber
           ein lauter Alarm als ein Stop-Loss auf einer geratenen Zahl.
        """
        try:
            bal = self.app.execution.get_balance() or {}
        except Exception as e:
            log.error("RESTORE", f"Live-Kontostand nicht abrufbar: {str(e)[:90]}"
                                 f" - vorhandene Bestaende bleiben UNUEBERWACHT!")
            return

        total = bal.get("total", {}) or {}
        uebernommen = 0
        liegengelassen = []

        for coin in self.app.config.trading.coins:
            asset = coin.split("/")[0]
            try:
                qty = float(total.get(asset, 0) or 0)
            except Exception:
                continue
            if qty <= 0:
                continue
            if coin in self.app.risk_engine.open_positions:
                continue

            # --- Staubgrenze: kann die Boerse das ueberhaupt verkaufen? ---
            min_menge = 0.0
            try:
                markt = self.app.execution.exchange.market(coin)
                min_menge = float(
                    ((markt.get("limits") or {}).get("amount") or {}).get("min")
                    or 0)
            except Exception:
                min_menge = 0.0

            if min_menge > 0 and qty < min_menge:
                liegengelassen.append(
                    f"{coin}: {qty:.8f} unter Mindestmenge {min_menge:.8f} "
                    f"- nicht verkaufbar, daher keine Position")
                continue

            # --- Der echte Einstand ---
            e = None
            try:
                e = self.app.execution.bestand_einstand(coin, qty)
            except Exception as _ee:
                log.warn("RESTORE", f"{coin}: Einstand-Abruf scheiterte "
                                    f"({str(_ee)[:70]})")

            if not e or e.get("preis_schnitt", 0) <= 0:
                # KEIN Rueckfall auf den Marktpreis. Ein Stop-Loss auf
                # einer geratenen Zahl ist schlimmer als ein sichtbarer
                # Alarm: Er sieht aus wie Schutz und ist keiner.
                log.error("RESTORE", f"{coin}: {qty:.8f} {asset} im Bestand, "
                                     f"aber KEIN Einstand aus den Ausfuehrungen "
                                     f"belegbar - Position wird NICHT angelegt. "
                                     f"Diese Coins bleiben unueberwacht, der "
                                     f"Waechter wird sie melden.")
                continue

            einstand = e["preis_schnitt"]
            self.app.risk_engine.open_positions[coin] = {
                "active": True,
                "entry_price": einstand,
                "highest_price": einstand,
                "lowest_price": einstand,
                "qty": qty,
                "cost_basis": e["kostenbasis"],
                "dca_levels": 1,
                "hoechst_pnl_pct": 0.0,
                "time": time.time(),
                # Kennzeichen, damit spaetere Auswertungen diese
                # Positionen von normal eroeffneten trennen koennen.
                "_uebernommen_live": True,
            }
            uebernommen += 1

            hinweis = ""
            if e.get("ungedeckt", 0) > 1e-10:
                hinweis += (f" ACHTUNG: {e['ungedeckt']:.8f} {asset} ohne "
                            f"passenden Kauf - Einstand nur teilweise belegt!")
            if e.get("verkaeufe_gesehen"):
                hinweis += (f" ACHTUNG: {e['verkaeufe_gesehen']} Verkauf/Verkaeufe"
                            f" in der Historie - Einstand ist eine Naeherung!")

            log.warn("RESTORE", f"{coin}: {qty:.8f} {asset} UEBERNOMMEN. "
                                f"Echter Einstand {einstand:,.2f}$ aus "
                                f"{e['ausfuehrungen']} Ausfuehrungen, "
                                f"Kostenbasis {e['kostenbasis']:.4f}$. "
                                f"Stop-Loss und Trailing greifen ab jetzt.{hinweis}")

        for z in liegengelassen:
            log.warn("RESTORE", z)

        if uebernommen:
            log.info("APP", f"Live-Bestaende uebernommen: {uebernommen} Position(en) "
                            f"- ab jetzt ueberwacht")
        elif not liegengelassen:
            log.info("RESTORE", "Keine uebernahmefaehigen Live-Bestaende gefunden")
