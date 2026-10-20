# -*- coding: utf-8 -*-
"""
runtime/exit_monitor.py - Monolith-Split Schritt 3 (SPLIT-3)

Das Exit-Organ des Bots: sl_tp_monitor (Stop-Loss / Take-Profit /
Stufen-Trailing, inkl. E6B-COINSTOP Per-Coin-Override und
phasen-angepasster Risiken via get_adjusted_risk) und
fetch_current_price (Preis-Fallback-Kette, P1-gehaertet).

Code WORTWOERTLICH aus app.py umgezogen (Stand 11.07.2026, nach
Split-2, Guard-Fix, Pricefeed-Fix). self.X -> self.app.X; die
Muster hasattr/getattr mit self-Komma wurden EXPLIZIT mit-
konvertiert (Lektion Guard-Bug 10.07.). Ein Streu-CR aus einem
alten Patch wurde zeilenende-normalisiert (keine Code-Aenderung).
WICHTIG (Bauplan-Falle): Laeuft im Scheduler-Thread - dieser Delegat
puffert KEINEN eigenen Zustand, alles haengt an self.app.
"""
from core.logger import log
from datetime import datetime

# [SCHATTENMODUS 10.08.2026, umgestellt 11.08.2026]
#
# Diese Konstante ist NICHT mehr der Schalter. Sie ist nur noch der
# Rueckfall, falls der gemeinsame Drei-Stufen-Schalter nicht geladen
# werden konnte (GEFUNDENE-PROBLEME #11).
#
# Eingestellt wird jetzt in data_store/config.json unter "regel_modi":
#     "trend_exit": "SHADOW"    <- heutiger Zustand
#     "trend_exit": "ACTIVE"    <- Regel verkauft wieder
#
# WARUM DER RUECKFALL AUF True STEHT: Der gemeinsame Schalter faellt bei
# jedem Fehler bewusst auf ACTIVE zurueck - ein Vertipper soll nie eine
# SCHUETZENDE Regel abschalten. Beim Trend-Ausstieg ist ACTIVE aber die
# gefaehrliche Richtung: er wurde stillgelegt, weil 46 Faelle zu 0 % im
# Plus lagen (Summe -36,08 $). Faellt der Schalter also ganz aus, bleibt
# es hier beim Schattenmodus - dem heutigen, gemessenen Zustand.
TREND_EXIT_SCHATTEN = True


class ExitMonitor:
    """Delegat: haelt nur die App-Referenz, kein eigener Zustand (Thread-Regel)."""

    def __init__(self, app):
        self.app = app

    def _schatten_notieren(self, sym, pos, regel, grund, preis, pnl_pct,
                           hoechst_pnl_pct):
        """[SCHATTENMODUS 10.08.2026] Haelt fest, was eine Regel getan HAETTE.

        Schreibt in die Telemetrie-Datenbank (Tabelle schatten_exits). Der
        spaetere Vergleich laeuft ueber position_id: wie ging die Position
        TATSAECHLICH aus, nachdem die Schattenregel ausgeloest haette?

        Pro Position und Regel wird nur der ERSTE Treffer notiert - sonst
        entstuende bei jedem 30-Sekunden-Takt eine neue Zeile, solange die
        Position unter der Schwelle liegt.

        Wirft nie nach aussen: ein Protokollfehler darf den Handel nie stoppen.
        """
        try:
            marker = f"_schatten_{regel}"
            if pos.get(marker):
                return                      # schon notiert
            pos[marker] = True

            from core.telemetrie import Telemetrie
            tel = getattr(self.app, "telemetrie", None)
            if tel is None:
                tel = self.app.telemetrie = Telemetrie()
            tel.schatten_exit(
                position_id=pos.get("position_id", ""),
                symbol=sym,
                regel=regel,
                grund=grund,
                preis=preis,
                pnl_pct=pnl_pct,
                hoechst_pnl_pct=hoechst_pnl_pct,
                entry_price=pos.get("entry_price", 0),
                entry_score=pos.get("entry_score"),
            )
            log.info("SCHATTEN", f"{sym}: {regel} haette ausgeloest "
                                 f"({grund}) - Position laeuft weiter")
        except Exception as e:
            log.warn("SCHATTEN", f"{sym}: Notiz fehlgeschlagen: {str(e)[:80]}")

    def sl_tp_monitor(self):
        """KRITISCH: Prueft alle offenen Positionen auf SL/TP/Trailing.

        Laeuft alle 30 Sekunden im Scheduler - UNABHAENGIG vom Trading-Loop.
        """
        try:
            self.app.health.heartbeat("sl_tp_monitor")
        except Exception:
            pass

        if not hasattr(self.app.risk_engine, 'open_positions'):
            return

        # Snapshot der offenen Positionen (vermeidet Race Conditions)
        positions_to_check = []
        for sym, pos in list(self.app.risk_engine.open_positions.items()):
            if not pos.get("active"):
                continue
            if pos.get("_selling"):
                continue
            qty = pos.get("qty", 0)
            entry = pos.get("entry_price", 0)
            if qty <= 0 or entry <= 0:
                continue
            # HOLD-Modus -> kein automatischer Verkauf
            coin_mode = self.app._coin_modes.get(sym, pos.get("mode", "SL"))
            if coin_mode == "HOLD":
                continue
            positions_to_check.append((sym, pos, coin_mode))

        # SICHTBARER Header damit User weiss: Monitor laeuft!
        if not positions_to_check:
            log.info("MONITOR", "Keine offenen Positionen zu pruefen")
            return

        # === REGIME-RISK: SL/Trail an Marktphase anpassen ===
        _rr_cycle = self.app.state.get("cycle_phase", "UNKNOWN")
        _rr_regime = "UNKNOWN"
        try:
            if hasattr(self.app, "regime_detector") and self.app.regime_detector:  # [DOPPELFIX 11.07.]
                _rr_regime = str(self.app.regime_detector.current_regime)
        except Exception:
            pass
        try:
            from risk.regime_profiles import get_adjusted_risk, get_profile_name
            sl_pct, trail_pct, _ = get_adjusted_risk(
                _rr_cycle, _rr_regime,
                self.app.config.risk.stop_loss_pct, self.app.config.risk.trailing_stop_pct)
            _rr_name = get_profile_name(_rr_cycle, _rr_regime)
        except Exception:
            sl_pct = self.app.config.risk.stop_loss_pct
            trail_pct = self.app.config.risk.trailing_stop_pct
            _rr_name = "config"
        tp_pct = self.app.config.risk.take_profit_pct

        log.info("MONITOR", f"Checking {len(positions_to_check)} Position(en) "
                            f"(SL:{sl_pct}% TP:{tp_pct}% Trail:{trail_pct}% | Phase: {_rr_name})")
        try:
            from risk.exit_rules import beschreibung as _er_beschreibung
            log.info("MONITOR", f"Ausstiegsregel: {_er_beschreibung()}")
        except Exception:
            pass

        for sym, pos, coin_mode in positions_to_check:
            try:
                # === E6B-COINSTOP: Per-Coin-Mindeststop (E6). ADA braucht weiteren Stop ===
                # Dict {Symbol: Mindest-Stop%}. Nur LOCKERN, nie enger als global.
                from risk.coin_stops import COIN_SL_MIN as _COIN_SL_MIN  # [E6B-FIX 14.07.] EINE Wahrheit
                _coin_sl = sl_pct
                if sym in _COIN_SL_MIN and _COIN_SL_MIN[sym] > _coin_sl:
                    _coin_sl = _COIN_SL_MIN[sym]
                entry = pos.get("entry_price", 0)
                qty = pos.get("qty", 0)
                highest = pos.get("highest_price", entry)

                # ====================================================
                # 1. AKTUELLEN PREIS HOLEN - mehrfacher Fallback
                # ====================================================
                current_price = self.fetch_current_price(sym)
                if current_price <= 0:
                    log.warn("SL_TP", f"{sym}: Kein Preis verfuegbar, ueberspringe")
                    continue

                # Hoechststand updaten (fuer Trailing-Stop)
                if current_price > highest:
                    pos["highest_price"] = current_price
                    highest = current_price

                # === MFE/MAE-LOGGING: Tiefststand mitfuehren (reines Logging) ===
                # lowest wird NIE in einer Verkaufsentscheidung gelesen -
                # nur aufgezeichnet, um spaeter MAE (max adverse excursion)
                # auszuwerten. Init = entry, falls Feld fehlt (z.B. nach Restore).
                lowest = pos.get("lowest_price", entry)
                if current_price < lowest:
                    pos["lowest_price"] = current_price
                    lowest = current_price

                # ====================================================
                # 2. P&L BERECHNEN
                # ====================================================
                pnl_pct = ((current_price / entry) - 1) * 100
                fall_from_high = ((highest - current_price) / highest) * 100 if highest > 0 else 0

                # [E9-RR 29.07.] Hoechststand des GEWINNS mitfuehren. Wird fuer
                # die Breakeven-Sperre gebraucht - `highest_price` allein reicht
                # nicht, weil sich der Einstand beim Nachkauf verschiebt.
                hoechst_pnl_pct = pos.get("hoechst_pnl_pct", 0.0)
                if pnl_pct > hoechst_pnl_pct:
                    hoechst_pnl_pct = pnl_pct
                    pos["hoechst_pnl_pct"] = pnl_pct

                # ====================================================
                # [SCHATTEN-LEITER 13.08.2026] Alternative Ausstiegsregel
                # rechnet mit - sie VERKAUFT NICHT.
                #
                # Frage dahinter (Sven, 13.08.): "wenn wir bei 20 % im Plus
                # sind, muessen dann erst 5 Prozent fallen, bevor wir den
                # Gewinn mitnehmen?" Die heutige Leiter misst den Abstand
                # am KURS und wird mit dem Gewinn WEITER (bis 2,2x). Die
                # Schatten-Regel misst am GEWINN: hoechstens 25 % des
                # Hoechststandes zurueckgeben.
                #
                # Gemessen an 37 Trades mit MFE-Daten ist die Schatten-Regel
                # bis etwa +12 % besser, darueber schlechter - und der
                # Median-Hoechststand liegt bei +1,54 %. Welche unterm
                # Strich mehr uebrig laesst, entscheidet die Messung.
                # Begruendung und Rechenweg: risk/exit_rules_schatten.py
                #
                # Bewusst VOR den Verkaufspruefungen: die Schatten-Regel
                # soll auch dann notiert werden, wenn die echte Leiter im
                # selben Takt zuschlaegt - nur so ist vergleichbar, wer
                # frueher dran gewesen waere. _schatten_notieren() schreibt
                # je Position und Regel nur den ERSTEN Treffer.
                # ====================================================
                try:
                    from risk.exit_rules_schatten import (
                        loest_aus as _sch_loest_aus, grund_text as _sch_grund,
                        REGEL_NAME as _SCH_NAME)
                    if _sch_loest_aus(pnl_pct, hoechst_pnl_pct):
                        self._schatten_notieren(
                            sym, pos, _SCH_NAME,
                            _sch_grund(pnl_pct, hoechst_pnl_pct),
                            current_price, pnl_pct, hoechst_pnl_pct)
                except Exception as _sch_e:
                    # Kein stiller Schlucker: faellt die Schatten-Regel aus,
                    # muss das sichtbar sein, sonst misst das Fenster ins
                    # Leere und niemand merkt es. Der Handel laeuft weiter -
                    # die Regel greift ja ohnehin nicht ein.
                    log.warn("SCHATTEN-LEITER",
                             f"{sym}: Berechnung fehlgeschlagen "
                             f"({type(_sch_e).__name__}: {str(_sch_e)[:70]}) - "
                             f"fuer diese Position fehlt der Vergleichswert")

                # SICHTBARES Status-Log pro Position (genau wie gewuenscht!)
                sl_price = entry * (1 - _coin_sl / 100)  # E6B-COINSTOP
                tp_price = entry * (1 + tp_pct / 100) if tp_pct > 0 else 0
                tp_str = f" | TP bei {tp_price:.4f}$" if tp_price > 0 else ""
                log.info("MONITOR", f"{sym.split('/')[0]}: Entry {entry:.4f}$ | "
                                     f"Aktuell {current_price:.4f}$ | "
                                     f"PnL {pnl_pct:+.2f}% | "
                                     f"SL bei {sl_price:.4f}${tp_str}")

                # ====================================================
                # 3. SL/TP/TRAILING CHECKEN
                # ====================================================
                sell_reason = None
                strategy = None

                # FIX 4: TREND-EXIT - bei MTF-Bearish UND PnL < -1% sofort raus!
                # (Verhindert dass Position bis -2% SL durchlaufen muss)
                #
                # [SCHATTENMODUS 10.08.2026] Diese Regel steht auf dem Pruefstand.
                # Messung ueber 46 Faelle: 0.0 % davon im Plus, Summe -36.08 $,
                # im Mittel -0.784 $ je Fall. Sie greift bei -1 %, der eigentliche
                # Stop-Loss aber erst bei -2 % - sie steigt also eine ganze
                # Prozentstufe frueher aus.
                #
                # ABER: Ob sie damit Schlimmeres verhindert hat, steht NICHT im
                # Journal - die Position wurde ja verkauft, der weitere Verlauf
                # ist unbekannt. Deshalb wird sie jetzt im Schatten gefahren:
                # sie rechnet weiter und protokolliert, was sie GETAN HAETTE,
                # verkauft aber nicht. Die Position laeuft normal weiter und
                # trifft spaeter auf Stop-Loss oder Trailing. Nach 20-30 Faellen
                # laesst sich vergleichen, ob der Ausstieg bei -1 % besser war
                # als das Aussitzen.
                #
                # Zum Scharfschalten: TREND_EXIT_SCHATTEN = False setzen.
                if pnl_pct < -1.0:
                    try:
                        mtf_data = self.app.multi_tf.last_signals.get(sym, {})
                        # [SICHTBARKEIT 11.08.2026] Der eigentliche stille
                        # Punkt sitzt HIER, nicht im except unten: fuer ETH
                        # und SOL ist last_signals dauerhaft leer, weil
                        # app.py:2082 die Mehrzeitrahmen-Analyse nur fuer
                        # coins[:1] (also BTC) aufruft. Ein leeres Dict wirft
                        # keinen Fehler - die Regel traf einfach nie zu, und
                        # niemand erfuhr davon.
                        #
                        # BELEG: von 47 TREND-EXIT-Verkaeufen in trades_v5.json
                        # entfallen 46 auf BTC und genau 1 auf ETH, bei neun
                        # gehandelten Coins und 441 Verkaeufen. Faktisch war
                        # das immer eine reine BTC-Regel.
                        #
                        # Nur Sichtbarkeit, KEINE Verhaltensaenderung: einmal
                        # je Symbol und Programmlauf, damit das Log nicht
                        # zulaeuft (die Pruefung liegt in einer Schleife).
                        if not mtf_data:
                            if not hasattr(self, "_mtf_luecke_gemeldet"):
                                self._mtf_luecke_gemeldet = set()
                            if sym not in self._mtf_luecke_gemeldet:
                                self._mtf_luecke_gemeldet.add(sym)
                                log.warn("TREND-EXIT",
                                         f"{sym}: keine Mehrzeitrahmen-Daten "
                                         f"(multi_tf laeuft nur fuer coins[:1], "
                                         f"app.py:2082) - Regel kann fuer "
                                         f"diesen Coin NIE ausloesen")
                        mtf_direction = mtf_data.get("direction", "NEUTRAL")
                        if mtf_direction == "BEARISH":
                            _te_grund = (f"TREND-EXIT (MTF BEARISH, "
                                         f"PnL {pnl_pct:+.2f}% < -1%)")
                            # [GEFUNDENE-PROBLEME #11] Gemeinsamer Schalter
                            # statt eigener Konstante. Fehlt er, gilt die
                            # Konstante oben - also weiterhin Schattenmodus.
                            _schalter = getattr(self.app, "regel_schalter", None)
                            if _schalter is not None:
                                _im_schatten = not _schalter.wirkt("trend_exit")
                            else:
                                _im_schatten = TREND_EXIT_SCHATTEN

                            if _im_schatten:
                                self._schatten_notieren(
                                    sym, pos, "TREND_EXIT", _te_grund,
                                    current_price, pnl_pct, hoechst_pnl_pct)
                            else:
                                sell_reason = _te_grund
                                strategy = "TREND_EXIT"
                    except Exception as _te_e:
                        # [SICHTBARKEIT 11.08.2026] Hier stand "pass" - ein
                        # stiller Schlucker. Faellt der Zugriff auf multi_tf
                        # aus, traf die Regel nie zu und niemand erfuhr davon.
                        # Genau dieses Muster war am 06.08. die Ursache des
                        # ganzen Projekts: nicht der Fehler war das Problem,
                        # sondern dass er unsichtbar blieb.
                        log.warn("TREND-EXIT",
                                 f"{sym}: Pruefung nicht moeglich "
                                 f"({type(_te_e).__name__}: {str(_te_e)[:60]})")

                # Stop-Loss (immer aktiv!)
                if not sell_reason and pnl_pct <= -_coin_sl:  # E6B-COINSTOP
                    sell_reason = f"STOP-LOSS ({pnl_pct:+.2f}% <= -{_coin_sl}%)"
                    strategy = "STOP_LOSS"
                # Take-Profit (wenn aktiviert)
                elif not sell_reason and tp_pct > 0 and pnl_pct >= tp_pct:
                    sell_reason = f"TAKE-PROFIT ({pnl_pct:+.2f}% >= +{tp_pct}%)"
                    strategy = "TAKE_PROFIT"
                # ====================================================
                # [E9-RR 29.07.] NEUE AUSSTIEGS-LEITER (risk/exit_rules.py)
                # Ersetzt das inverse Stufen-Trailing, das Gewinner bei
                # ~+0.9 % deckelte, waehrend Verlierer bis -2.5 % liefen
                # (gemessenes Chance/Risiko 0.35 ueber 423 Verkaeufe).
                #   < +1 %        : nur Stop-Loss, kein Trailing
                #   +1 % .. +2 %  : Breakeven-Sperre (nie wieder ins Minus)
                #   ab +2 %       : Trail, der MIT dem Gewinn WEITER wird
                # ====================================================
                elif not sell_reason and coin_mode == "SL":
                    from risk.exit_rules import effektiver_trail, breakeven_verletzt
                    # [25.09.2026] Die Schalter trailing_leiter und
                    # breakeven_sperre werden jetzt gelesen (vorher Attrappen,
                    # v7-Befund 118). Bei ACTIVE - dem heutigen Stand - laeuft
                    # alles wie zuvor: Trailing hat Vorrang, sonst Breakeven.
                    # Nur wenn das Trailing NICHT scharf ist, bekommt die
                    # Breakeven-Sperre im selben Durchlauf ihre Chance.
                    _schalter = getattr(self.app, "regel_schalter", None)

                    def _regel_wirkt(_r):
                        return _schalter is None or _schalter.wirkt(_r)

                    def _regel_schatten(_r):
                        return _schalter is not None and _schalter.schreibt_mit(_r)

                    # Faktor am HOECHSTSTAND, nicht am aktuellen Gewinn -> Ratsche.
                    eff_trail = effektiver_trail(hoechst_pnl_pct, trail_pct, _rr_regime)
                    _trail_trifft = eff_trail > 0 and fall_from_high >= eff_trail
                    if _trail_trifft:
                        _up_tag = ", TREND-UP" if _rr_regime == "TRENDING_UP" else ""
                        _tr_grund = (f"TRAILING-STOP (Fall {fall_from_high:.2f}% >= {eff_trail}%, "
                                     f"PnL {pnl_pct:+.2f}%, Hoch {hoechst_pnl_pct:+.2f}%{_up_tag})")
                        if _regel_wirkt("trailing_leiter"):
                            sell_reason = _tr_grund
                            strategy = "TRAILING_STOP"
                        elif _regel_schatten("trailing_leiter"):
                            self._schatten_notieren(
                                sym, pos, "TRAILING_STOP", _tr_grund,
                                current_price, pnl_pct, hoechst_pnl_pct)
                    if not sell_reason and breakeven_verletzt(pnl_pct, hoechst_pnl_pct):
                        _be_grund = (f"BREAKEVEN-SPERRE (war {hoechst_pnl_pct:+.2f}%, "
                                     f"jetzt {pnl_pct:+.2f}%)")
                        if _regel_wirkt("breakeven_sperre"):
                            sell_reason = _be_grund
                            strategy = "BREAKEVEN_LOCK"
                        elif _regel_schatten("breakeven_sperre"):
                            self._schatten_notieren(
                                sym, pos, "BREAKEVEN_LOCK", _be_grund,
                                current_price, pnl_pct, hoechst_pnl_pct)

                # ====================================================
                # 4. BEI TREFFER SOFORT SELL!
                # ====================================================
                if sell_reason:
                    log.warn("MONITOR", f"⚡ {sym.split('/')[0]}: {strategy} TRIGGERED! "
                                         f"({sell_reason})")

                    # Position als "im Verkauf" markieren (verhindert Doppel-Sell)
                    pos["_selling"] = True

                    # Sell-Intent erstellen
                    from core.events import DecisionIntent, Side, EVENT_SIGNAL
                    sell_intent = DecisionIntent(
                        symbol=sym, side=Side.SELL, confidence=0.95,
                        entry_price=current_price, quantity=qty,
                        strategy_id=strategy, strategy_name=strategy,
                        entry_reason=sell_reason, score=10,
                        agent_id="sl_tp_monitor")

                    # SOFORT ausfuehren (nicht ueber EventBus, das koennte verzoegern)
                    try:
                        result = self.app.execution.execute(sell_intent)
                        if result.status == "filled":
                            # ========================================
                            # [E9-FEE 29.07.] P&L gegen den ECHTEN Einstand.
                            # Alt: entry_cost = qty * entry. Beim Kauf gilt aber
                            #   qty = (Betrag - Kaufgebuehr) / Preis
                            # also ist qty*entry genau UM DIE KAUFGEBUEHR ZU KLEIN.
                            # Ergebnis: jeder gebuchte Gewinn war um 0.1 % des
                            # Volumens zu hoch. Ueber 19.276 $ Kaufvolumen sind
                            # das ~19 $ Phantomgewinn im Journal - bei einem
                            # ausgewiesenen Gesamtergebnis von -27.57 $.
                            # Neu: cost_basis = tatsaechlicher Mittelabfluss
                            # (wird beim Kauf mitgeschrieben), anteilig zur
                            # verkauften Menge.
                            # ========================================
                            revenue = result.filled_qty * result.avg_fill_price
                            _cost_basis = pos.get("cost_basis", 0) or 0
                            if _cost_basis > 0 and qty > 0:
                                entry_cost = _cost_basis * (result.filled_qty / qty)
                            else:
                                # Altbestand ohne cost_basis: Kaufgebuehr schaetzen
                                entry_cost = result.filled_qty * entry * 1.001
                            pnl_usd = revenue - entry_cost - (result.fee or 0)

                            # Journal-Eintrag
                            from datetime import datetime, timezone
                            self.app._journal_add({
                                "schreibpfad": "exit_monitor",
                                "type": "SELL", "coin": sym,
                                "price": result.avg_fill_price,
                                "qty": result.filled_qty,
                                "amount": revenue,
                                "pnl": pnl_usd,
                                "strategy": strategy,
                                "reason": sell_reason,
                                # === MFE/MAE-LOGGING (reines Logging, E7-konform) ===
                                # pnl_pct + fee: Regression-Fix (fehlten seit ~15.07.).
                                # mfe_pct: hoechster Stand ueber Einstand (max favorable).
                                # mae_pct: tiefster Stand unter Einstand (max adverse).
                                "pnl_pct": round(pnl_pct, 2),
                                "fee": round(result.fee or 0, 4),
                                # [GEFUNDENE-PROBLEME #24] Ist-Slippage. Dieser
                                # Pfad ist der WICHTIGSTE dafuer: ueber ihn
                                # laufen alle Verkaeufe (Teil 4.1). Auf dem
                                # Kaufpfad stand das Feld seit dem 05.08. schon
                                # drin, hier fehlte es - 13 Verkaeufe ohne den
                                # Wert. Beim Verkauf ist Slippage teurer als
                                # beim Kauf, weil unter Druck verkauft wird
                                # (Stop-Loss, Trend-Ausstieg).
                                "slippage_pct": getattr(result, "slippage_pct", None),
                                "mfe_pct": round(((highest / entry) - 1) * 100, 2) if entry > 0 else None,
                                "mae_pct": round(((lowest / entry) - 1) * 100, 2) if entry > 0 else None,
                                # [SCORE-FIX 10.08.2026] ECHTER Einstiegs-Score
                                # statt der frueher hart gesetzten 10. Erst damit
                                # laesst sich auswerten, ob schwache Signale
                                # schlechter enden als starke. Zusaetzlich die
                                # Kennung, um Kauf und Verkauf zu verbinden, und
                                # die Haltedauer.
                                "entry_score": pos.get("entry_score"),
                                "entry_strategie": pos.get("entry_strategie", ""),
                                "position_id": pos.get("position_id", ""),
                                "haltedauer_min": round(
                                    (datetime.now(timezone.utc).timestamp()
                                     - float(pos.get("eroeffnet_ts") or 0)) / 60, 1
                                ) if pos.get("eroeffnet_ts") else None,
                                "time": datetime.now(timezone.utc).isoformat(),
                            })

                            # === [VERKAUFS-LUECKE 10.08.2026] TELEMETRIE ===
                            # Verkaeufe liefen bisher komplett an der
                            # Telemetrie vorbei: Sie werden hier bewusst
                            # SOFORT ausgefuehrt statt ueber den EventBus
                            # (siehe Kommentar oben, Geschwindigkeit), und
                            # nur der Bus-Pfad schrieb ins Protokoll.
                            # Ergebnis: 52.198 Kaufpruefungen, 0 Verkaeufe.
                            # Als am 07.08. SOL verkauft wurde, war der Grund
                            # spaeter nicht mehr feststellbar - system.log war
                            # rotiert. Steht bewusst NACH dem Journal-Eintrag:
                            # das Journal ist die Buchhaltung und hat Vorrang.
                            try:
                                _hd = None
                                _eroeffnet = pos.get("eroeffnet_ts") or pos.get("time")
                                if _eroeffnet:
                                    import time as _t
                                    _hd = round((_t.time() - float(_eroeffnet)) / 60.0, 1)
                                self.app._telemetrie_verkauf(
                                    symbol=sym,
                                    preis=result.avg_fill_price,
                                    qty=result.filled_qty,
                                    pnl_usd=round(pnl_usd, 4),
                                    pnl_pct=round(pnl_pct, 4),
                                    grund=sell_reason,
                                    strategie=strategy,
                                    fee=round(result.fee or 0, 4),
                                    mfe_pct=round(((highest / entry) - 1) * 100, 2) if entry > 0 else None,
                                    mae_pct=round(((lowest / entry) - 1) * 100, 2) if entry > 0 else None,
                                    haltedauer_min=_hd,
                                    position_id=pos.get("position_id", ""),
                                )
                            except Exception as _tel_e:
                                log.warn("MONITOR", f"Telemetrie SELL: {str(_tel_e)[:80]}")

                            # === [TELEGRAM-LUECKE 17.08.2026] ===
                            # Dieselbe Ursache wie die Verkaufs-Luecke oben,
                            # nur ein anderer Verbraucher - und deshalb beim
                            # Fix am 10.08. uebersehen. app.py:1956
                            # _on_order_filled() ruft telegram.on_sell(), haengt
                            # aber am EventBus. Dieser Pfad geht bewusst daran
                            # vorbei, also wurde on_sell() bei KEINEM einzigen
                            # Exit-Monitor-Verkauf je aufgerufen. Sven fiel es
                            # auf, weil in Telegram nur Kaeufe ankamen.
                            # Steht bewusst NACH Journal und Telemetrie: eine
                            # Benachrichtigung darf die Buchhaltung nie
                            # gefaehrden. Eigenes try/except - ein Netzfehler
                            # bei Telegram darf keinen Verkauf stoeren.
                            try:
                                _tg = getattr(self.app, "telegram", None)
                                if _tg is not None:
                                    _tg.on_sell({
                                        "coin": sym,
                                        "qty": result.filled_qty,
                                        "price": result.avg_fill_price,
                                        "amount": revenue,
                                        "pnl": pnl_usd,
                                        "pnl_pct": pnl_pct,
                                        "reason": sell_reason,
                                        "strategy": strategy,
                                    })
                            except Exception as _tg_e:
                                log.warn("MONITOR", f"Telegram SELL: {str(_tg_e)[:80]}")

                            # === [E9-CHURN 29.07.] WIEDEREINSTIEGS-SPERRE SETZEN ===
                            # 338 von 423 Verkaeufen wurden binnen 15 min im
                            # selben Coin zurueckgekauft, 319 davon TEURER.
                            # Ab jetzt wird der Exit vermerkt; der DCA-Pfad
                            # fragt vor jedem Kauf nach.
                            try:
                                if getattr(self.app, "reentry_guard", None) is not None:
                                    self.app.reentry_guard.notiere_exit(
                                        sym, result.avg_fill_price, strategy)
                            except Exception as _rg_e:
                                log.warn("MONITOR", f"Reentry-Guard: {str(_rg_e)[:80]}")

                            # FIX 6: Position aufraeumen via record_result (atomares delete!)
                            # Vorher: active=False (Position blieb -> "Max Positionen 33"!)
                            self.app.risk_engine.record_result(sym, pnl_usd, Side.SELL)

                            # ========================================
                            # [LERN-FIX B2 11.08.2026] DER BOT LERNTE SEIT
                            # DEM 27.07.2026 NICHTS MEHR.
                            #
                            # URSACHE: Diese Datei ruft oben bewusst
                            # execution.execute() DIREKT auf ("nicht ueber
                            # EventBus, das koennte verzoegern"). Damit wird
                            # EVENT_ORDER_FILLED nie veroeffentlicht - das
                            # passiert ausschliesslich in app.py:1583. Am
                            # Handler _on_order_filled (app.py:471) haengen
                            # aber ALLE Lern-Aufrufe.
                            #
                            # BELEG: exit_monitor.py enthaelt 0 Treffer fuer
                            # bus.publish. brain_performance.json und die
                            # Historie in rl_weights.json enden beide exakt
                            # am 27.07.2026 08:06, obwohl seither Dutzende
                            # Verkaeufe liefen. agent_votes.json ist seit
                            # dem 06.06.2026 genau 2 Byte gross ("{}") -
                            # Meta-Voting hat nie etwas gelernt.
                            #
                            # Da JEDER Verkauf ueber diesen Monitor laeuft
                            # (Trailing, Stop-Loss, Breakeven, Trend-Exit),
                            # erreichte kein einziger den Lernpfad.
                            #
                            # LOESUNG: die Lern-Funktionen hier DIREKT
                            # aufrufen, statt ein zweites ORDER_FILLED zu
                            # veroeffentlichen. Ein zusaetzliches Event
                            # wuerde doppelt buchen: diese Datei schreibt
                            # das Journal bereits selbst (Zeile 313) und
                            # verschickt die Telegram-Meldung selbst
                            # (weiter unten) - app.py:_on_order_filled
                            # wuerde beides ein zweites Mal tun.
                            #
                            # [KORREKTUR 11.08.2026] Eine fruehere Fassung
                            # dieses Kommentars berief sich hier auf
                            # fix_exit_doppel.py als Beleg. Das war falsch
                            # zitiert: jenes Skript hat self.app.app ->
                            # self.app repariert (Regime-Erkennung und
                            # Impact-Journal), nicht doppelte Buchungen.
                            # Die Entscheidung stimmt, die Quellenangabe
                            # stimmte nicht.
                            #
                            # Gelernt wird bei JEDEM Ausgang, auch bei
                            # Verlust (siehe Lern-Fix B1 in app.py).
                            # Vollstaendig gekapselt: ein Lernfehler darf
                            # einen abgeschlossenen Verkauf nie stoeren.
                            # ========================================
                            for _name, _fn in (
                                ("strategy_brain",
                                 lambda: self.app.strategy_brain.record_trade_result(
                                     strategy, pnl_usd, quelle="exit_monitor",
                                     symbol=sym,
                                     position_id=pos.get("position_id", ""))),
                                ("rl_feedback",
                                 lambda: self.app.rl_feedback.record_trade(
                                     strategy, pnl_usd)),
                                ("adaptive_sizer",
                                 lambda: self.app.adaptive_sizer.record_result(pnl_usd)),
                                ("meta_voting",
                                 lambda: self.app.meta_voting.evaluate_trade(
                                     sym, pnl_usd)),
                                ("shadow_mode",
                                 lambda: self.app.shadow_mode.record_active_pnl(pnl_usd)),
                            ):
                                try:
                                    _fn()
                                except Exception as _le:
                                    log.warn("LERNEN", f"{sym}: {_name} "
                                                       f"fehlgeschlagen: {str(_le)[:70]}")
                            log.info("LERNEN", f"{sym}: Ergebnis {pnl_usd:+.2f}$ "
                                               f"({strategy}) an 5 Lernmodule "
                                               f"gemeldet")
                            # === SIT-MEM SELL FIX: Monitor-Exits ins Impact-Journal ===
                            try:
                                if getattr(self.app, "impact_journal", None) is not None:  # [DOPPELFIX 11.07.]
                                    self.app.impact_journal.log_sell(
                                        symbol=sym,
                                        exit_price=result.avg_fill_price,
                                        pnl_usd=round(pnl_usd, 2),
                                        reason=sell_reason,
                                    )
                            except Exception as _ij_e:
                                log.warn("MONITOR", f"ImpactJournal SELL-Hook: {str(_ij_e)[:80]}")

                            # Logging mit Farb-Emoji
                            emoji = "✅" if pnl_usd >= 0 else "❌"
                            log.info("EXEC", f"{emoji} SELL {sym}: {result.filled_qty:.6f} @ "
                                              f"{result.avg_fill_price:.4f}$ | "
                                              f"PnL: {pnl_usd:+.2f}$ ({pnl_pct:+.2f}%)")

                            # [ENTFERNT 18.08.2026 - GEFUNDENE-PROBLEME 38]
                            # Hier stand eine zweite Telegram-Nachricht zum
                            # SELBEN Verkauf. Zusammen mit dem on_sell()-Aufruf
                            # 120 Zeilen weiter oben meldete sich damit jeder
                            # Verkauf ZWEIMAL. Sven sah es am 18.08. auf seinem
                            # Telefon: zwei Nachrichten um 05:33 zum selben
                            # BTC-Verkauf.
                            #
                            # Die Vorgeschichte gehoert dazu: on_sell() wurde
                            # am 17.08. ergaenzt, weil "in Telegram nur Kaeufe
                            # ankamen". Das war richtig beobachtet - dieser
                            # Absender hier verschluckte naemlich jeden Fehler
                            # mit einem nackten "except Exception: pass" und
                            # schwieg dadurch unsichtbar. Repariert wurde
                            # daraufhin der falsche Ort: ein zweiter Absender
                            # kam dazu, statt den stummen zu heilen.
                            #
                            # Der Grund des Verkaufs geht nicht verloren - er
                            # steht jetzt in reports/telegram.py:on_sell().
                            #
                            # MERKE: Ein nacktes "except: pass" verschluckt
                            # nicht nur einen Fehler, sondern eine Tatsache.
                            # Es hat hier eine falsche Diagnose erst moeglich
                            # gemacht.
                        else:
                            # Sell fehlgeschlagen -> Marker entfernen
                            pos["_selling"] = False
                            log.warn("SL_TP", f"{sym}: Sell rejected: {result.rejected_reason}")
                    except Exception as e:
                        pos["_selling"] = False
                        log.error("SL_TP", f"{sym}: Sell-Fehler: {e}")

            except Exception as e:
                log.warn("SL_TP", f"{sym}: Monitor-Fehler: {e}")

    def fetch_current_price(self, symbol: str) -> float:
        """Holt aktuellen Preis fuer ein Symbol mit MEHRFACH-FALLBACK.

        Reihenfolge:
        1. data_agent.price_cache (lokal, schnell)
        2. exchange.fetch_ticker() (Binance Live - frisch!)
        3. multi_exchange.get_ticker() (alternative Boerse)
        4. position.entry_price (letzter Fallback)

        Funktioniert in PAPER und LIVE Modus identisch!
        """
        # 1. Lokaler Cache
        try:
            cache = getattr(self.app.data_agent, 'price_cache', {}) or {}
            price = cache.get(symbol, 0)
            if price > 0:
                return float(price)
        except Exception:
            pass

        # 2. Direkt von Binance Exchange (auch im Paper-Modus!)
        try:
            client = getattr(self.app.data_agent, 'client', None)
            if client is not None:
                ticker = client.fetch_ticker(symbol)
                if ticker and ticker.get("last", 0) > 0:
                    price = float(ticker["last"])
                    # Cache aktualisieren fuer naechstes Mal
                    try:
                        self.app.data_agent.price_cache[symbol] = price
                    except Exception:
                        pass
                    return price
        except Exception as e:
            # Stille Fallback - Exchange API kann zwischendurch failen
            pass

        # 3. Multi-Exchange als Fallback
        try:
            if hasattr(self.app.execution, 'multi_exchange') and self.app.execution.multi_exchange:
                ticker = self.app.execution.multi_exchange.get_ticker(symbol)
                if ticker and ticker.get("last", 0) > 0:
                    return float(ticker["last"])
        except Exception:
            pass

        return 0.0
