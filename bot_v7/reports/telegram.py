"""
Trading Imperium V5 – Telegram Reporter
Sendet Trade-Alerts, Tages- und Wochenberichte per Telegram.
"""
import time
import threading
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone
from core.logger import log


class TelegramReporter:
    """Telegram-Benachrichtigungen und Reports."""

    def __init__(self, config):
        self.token = config.telegram.token
        self.chat_id = config.telegram.chat_id
        self.enabled = config.telegram.enabled and bool(self.token) and bool(self.chat_id)
        self.daily_trades = []
        self.weekly_trades = []
        self.last_daily = 0
        self.last_weekly = 0

        # === ABSENDER-KENNUNG (14.09.2026) ===
        # Seit dem 14.09. laufen zwei Bots: Papierhandel im alten Ordner
        # (Epoche E9) und Echtgeld hier. Beide benutzen denselben
        # Telegram-Bot - nachgemessen ueber die Pruefsummen der beiden
        # .env-Dateien, Token und Chat-ID sind identisch.
        #
        # Folge: Im Telegram-Verlauf stehen die Meldungen beider Bots
        # untereinander und sind nicht auseinanderzuhalten. Eine
        # Verkaufsmeldung koennte aus dem Papierhandel kommen oder
        # echtes Geld betreffen.
        #
        # Die Kennung stellt sich vor jede Nachricht. Sie loest das
        # darunterliegende Problem NICHT (siehe start_command_listener),
        # aber sie macht sichtbar, wer spricht.
        _modus = str(getattr(config.trading, "mode", "?")).lower()
        self.kennung = "\U0001F534 LIVE" if _modus == "live" else "\U0001F4C4 PAPIER"

        # Schalter fuer den Befehls-Empfaenger, Begruendung dort.
        # Hier gelesen und nicht erst beim Start abgefragt, damit der
        # Wert an genau einer Stelle steht.
        self.befehle_aktiv = bool(getattr(config.telegram,
                                          "befehle_aktiv", True))

        if self.enabled:
            log.info("TELEGRAM", f"Reporter aktiv (Kennung: {self.kennung})")
        else:
            log.info("TELEGRAM", "Reporter deaktiviert (kein Token/ChatID)")

    def send(self, message: str):
        """Sendet eine Nachricht an Telegram."""
        if not self.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            text = f"<b>[{self.kennung}]</b> {message}"
            requests.post(url, json={"chat_id": self.chat_id, "text": text,
                                     "parse_mode": "HTML"}, timeout=5)
        except Exception as e:
            log.warn("TELEGRAM", f"Senden fehlgeschlagen: {str(e)[:50]}")

    def on_buy(self, trade: Dict):
        """Benachrichtigung bei Kauf."""
        coin = trade.get("coin", "?").split("/")[0]
        qty = trade.get("qty", 0)
        price = trade.get("price", 0)
        amount = trade.get("amount", 0)
        strat = trade.get("strategy", "?")
        reason = trade.get("reason", "")

        msg = (f"🛒 <b>KAUF {coin}</b>\n"
               f"Menge: {qty:.6f}\n"
               f"Preis: {price:,.2f}$\n"
               f"Betrag: {amount:.2f} USDC\n"
               f"Strategie: {strat}\n"
               f"{reason}")
        self.send(msg)
        self.daily_trades.append(trade)
        self.weekly_trades.append(trade)

    def on_sell(self, trade: Dict):
        """Benachrichtigung bei Verkauf."""
        coin = trade.get("coin", "?").split("/")[0]
        qty = trade.get("qty", 0)
        price = trade.get("price", 0)
        amount = trade.get("amount", 0)
        pnl = trade.get("pnl", 0)
        pnl_pct = trade.get("pnl_pct", 0)

        # [DOPPELMELDUNG 18.08.2026] Der Grund stand bisher NUR in einer
        # zweiten Nachricht, die runtime/exit_monitor.py:625 selbst
        # verschickte - jeder Verkauf meldete sich dadurch zweimal
        # (GEFUNDENE-PROBLEME 38, von Sven am Telefon entdeckt). Der alte
        # Absender ist entfernt; damit dabei nichts verlorengeht, steht
        # der Grund jetzt hier. Er wird seit jeher mitgeliefert, wurde nur
        # nie angezeigt.
        grund = str(trade.get("reason") or "").strip()

        emoji = "✅" if pnl > 0 else "❌"
        msg = (f"{emoji} <b>SELL {coin}</b>\n"
               f"Menge: {qty:.6f}\n"
               f"Preis: {price:,.2f}$\n"
               f"Wert: {amount:.2f} USDC\n"
               f"P&L: {pnl:+.2f}$ ({pnl_pct:+.1f}%)")
        if grund:
            msg += f"\nGrund: {grund[:120]}"
        self.send(msg)
        self.daily_trades.append(trade)
        self.weekly_trades.append(trade)

    def on_error(self, error: str):
        """Benachrichtigung bei Fehler."""
        self.send(f"⚠️ <b>FEHLER</b>\n{error[:200]}")

    def on_kill_switch(self, reason: str):
        """Benachrichtigung bei Kill-Switch."""
        self.send(f"🛑 <b>KILL-SWITCH AKTIVIERT!</b>\n{reason}")

    def _journal_stats(self, since_hours=None):
        """Rechnet echte Zahlen aus trades_v5.json (statt In-Memory-Listen).
        since_hours=None -> alles; 24 -> letzte 24h; 168 -> letzte 7 Tage."""
        import os, json
        from datetime import datetime, timezone, timedelta
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "data_store", "trades_v5.json")
        if not os.path.exists(path):
            path = os.path.join(root, "trades_v5.json")
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            trades = d if isinstance(d, list) else d.get("trades", [])
        except Exception:
            trades = []
        cutoff = None
        if since_hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        sells, buys, pnl, wins = [], 0, 0.0, 0
        for t in trades:
            typ = str(t.get("type", t.get("side", ""))).upper()
            if cutoff is not None:
                ts = t.get("time", t.get("timestamp", t.get("_saved_at", "")))
                try:
                    when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                    if when < cutoff:
                        continue
                except Exception:
                    pass
            if "SELL" in typ:
                p = t.get("pnl")
                p = float(p) if isinstance(p, (int, float)) else 0.0
                sells.append(p)
                pnl += p
                if p > 0:
                    wins += 1
            elif "BUY" in typ:
                buys += 1
        n = len(sells)
        return {
            "sells": n, "buys": buys, "pnl": round(pnl, 2),
            "win_rate": round(wins / n * 100, 1) if n else 0.0,
            "wins": wins,
        }

    def _vermoegenszeilen(self, usdc, vermoegen):
        """Die Geldzeilen einer Nachricht.

        [14.09.2026] Vorher stand hier nur eine Zeile: "Balance: X USDC" -
        das reine Bargeld. Am 14.09. waren das 268,13 $, waehrend das
        Gesamtvermoegen bei 601,57 $ lag; der Rest steckte in Positionen
        und im Sparplan.

        Eine Nachricht, die genau dafuer da ist, aus der Ferne den Stand
        zu sehen, darf nicht ein Drittel des Vermoegens verschweigen.

        `vermoegen` ist optional: Wer diese Funktion ohne aufruft (alter
        Code, Tests), bekommt die alte Zeile. Ein neuer Pflichtparameter
        haette jeden bestehenden Aufruf gebrochen.
        """
        if not vermoegen or vermoegen.get("gesamt") is None:
            return f"💰 Bargeld: {usdc:.2f} USDC\n"
        g = vermoegen["gesamt"]
        p = vermoegen.get("positionen")
        zeilen = f"💰 Gesamt: {g:.2f}$\n   davon Bargeld: {usdc:.2f}$\n"
        if p is not None and p > 0.01:
            zeilen += f"   davon in Positionen: {p:.2f}$\n"
        return zeilen

    def send_daily_report(self, stats: Dict, balance: Dict, vermoegen: Dict = None):
        """Täglicher Bericht."""
        now = time.time()
        if now - self.last_daily < 82800:  # 23 Stunden
            return
        self.last_daily = now

        usdc = balance.get("total", {}).get("USDC", 0)
        btc = balance.get("total", {}).get("BTC", 0)
        _d = self._journal_stats(since_hours=24)
        _all = self._journal_stats()
        buys = [None] * _d["buys"]
        sells = [None] * _d["sells"]
        pnl = _d["pnl"]
        wins = _d["wins"]
        wr = (wins / len(sells) * 100) if sells else 0

        msg = (f"📊 <b>TAGESBERICHT</b>\n"
               f"{'─' * 25}\n"
               f"{self._vermoegenszeilen(usdc, vermoegen)}"
               f"₿ BTC: {btc:.8f}\n"
               f"📈 Trades: {len(buys)} Käufe, {len(sells)} Verkäufe\n"
               f"💵 P&L: {pnl:+.2f}$\n"
               f"🎯 Win-Rate: {wr:.0f}%\n"
               f"{'─' * 25}\n"
               f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        self.send(msg)
        self.daily_trades = []

    def send_weekly_report(self, stats: Dict, balance: Dict, vermoegen: Dict = None):
        """Wöchentlicher Bericht."""
        now = time.time()
        if now - self.last_weekly < 604000:  # ~7 Tage
            return
        self.last_weekly = now

        usdc = balance.get("total", {}).get("USDC", 0)
        btc = balance.get("total", {}).get("BTC", 0)
        _w = self._journal_stats(since_hours=168)
        total_trades = _w["sells"] + _w["buys"]
        sells = [None] * _w["sells"]
        pnl = _w["pnl"]
        wins = _w["wins"]
        wr = _w["win_rate"]

        msg = (f"📊 <b>WOCHENBERICHT</b>\n"
               f"{'═' * 25}\n"
               f"{self._vermoegenszeilen(usdc, vermoegen)}"
               f"₿ BTC: {btc:.8f}\n"
               f"📈 Trades: {total_trades}\n"
               f"💵 Wochen-P&L: {pnl:+.2f}$\n"
               f"🎯 Win-Rate: {wr:.0f}%\n"
               f"{'═' * 25}\n"
               f"⏰ KW {datetime.now().strftime('%V')} | {datetime.now().strftime('%d.%m.%Y')}")
        self.send(msg)
        self.weekly_trades = []

    def send_status(self, status: Dict):
        """Status auf Anfrage (/status Befehl)."""
        _all = self._journal_stats()
        _day = self._journal_stats(since_hours=24)
        msg = (f"⚡ <b>STATUS</b>\n"
               f"Version: {status.get('version', '?')}\n"
               f"Modus: {status.get('mode', '?')}\n"
               f"Uptime: {status.get('uptime', '?')}\n"
               f"Trades gesamt: {_all['sells'] + _all['buys']}\n"
               f"Realisiert gesamt: {_all['pnl']:+.2f}$\n"
               f"P&L (24h): {_day['pnl']:+.2f}$\n"
               f"Win-Rate: {_all['win_rate']:.0f}%")
        self.send(msg)

    # ========================================================
    # TELEGRAM-V2: BEFEHLS-EMPFAENGER (Steuerung per Telegram)
    # ========================================================
    def start_command_listener(self, engine):
        """Startet den Empfangs-Thread fuer Telegram-Befehle.

        Sicherheit: Es werden NUR Nachrichten von der konfigurierten
        chat_id akzeptiert - alle anderen Absender werden ignoriert.
        """
        if not self.enabled:
            return

        # === ZWEI BOTS, EIN TOKEN (14.09.2026) ===
        #
        # DAS PROBLEM, und es ist kein kosmetisches:
        # Telegram liefert eine Nachricht ueber getUpdates genau EINMAL
        # aus. Fragen zwei Prozesse mit demselben Token, bekommt sie der,
        # der zufaellig zuerst fragt - der andere sieht sie nie. Am
        # 14.09. lief genau das: Papier-Bot und Live-Bot pollten beide,
        # nachweisbar in beiden Logs ("Befehls-Empfaenger gestartet").
        #
        # Ein /notaus landet damit mit etwa gleicher Wahrscheinlichkeit
        # beim Papierhandel statt beim Echtgeld-Bot - und im Verlauf
        # sieht es aus, als waere der Befehl angekommen. Telegram meldet
        # zusaetzlich Fehler 409 (Conflict); im Papier-Log stehen
        # entsprechende Poll-Fehler.
        #
        # SAUBER LOESEN laesst sich das NUR mit einem zweiten Bot-Token
        # (BotFather, /newbot, zwei Minuten). Alles andere ist Flickwerk:
        # Solange zwei Prozesse an einem Token haengen, ist nicht
        # bestimmbar, wer eine Nachricht bekommt.
        #
        # Bis dahin dieser Schalter. Vorgabe AN, damit sich nichts
        # unbemerkt aendert - wer die Steuerung dem jeweils anderen Bot
        # ueberlassen will, stellt ihn hier ab.
        if not self.befehle_aktiv:
            log.warn("TELEGRAM", "Befehls-Empfaenger AUS "
                                 "(config.telegram.befehle_aktiv=false) - "
                                 "dieser Bot sendet nur, er hoert nicht")
            return

        self._engine = engine
        self._pending = None          # offene Bestaetigung: ("verkauf", "BTC/USDC") / ("notaus", None)
        self._pending_ts = 0
        self._offset = 0
        # === ALARME: pro Coin einstellbare Preis-Alarme ===
        import os
        self._alerts_path = os.path.join("data_store", "telegram_alerts.json")
        self._alerts = self._load_alerts()
        t = threading.Thread(target=self._poll_loop, daemon=True,
                             name="telegram-commander")
        t.start()
        ta = threading.Thread(target=self._alert_loop, daemon=True,
                              name="telegram-alerts")
        ta.start()
        log.info("TELEGRAM", "Befehls-Empfaenger gestartet (/hilfe fuer Kommandos)")
        self.send("\U0001F916 <b>Bot-Steuerung aktiv.</b> Tippe /hilfe fuer alle Befehle.")

    def _poll_loop(self):
        while True:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                r = requests.get(url, params={"offset": self._offset + 1,
                                              "timeout": 25}, timeout=35)
                data = r.json()
                for upd in data.get("result", []):
                    self._offset = max(self._offset, upd.get("update_id", 0))
                    msg = upd.get("message") or {}
                    text = (msg.get("text") or "").strip()
                    sender = str((msg.get("chat") or {}).get("id", ""))
                    if not text:
                        continue
                    if sender != str(self.chat_id):
                        log.warn("TELEGRAM", "Fremder Absender ignoriert: " + sender)
                        continue
                    self._handle_command(text)
            except Exception as e:
                log.warn("TELEGRAM", "Poll-Fehler: " + str(e)[:60])
                time.sleep(10)

    # ---------------- Befehls-Verarbeitung ----------------
    def _handle_command(self, text: str):
        try:
            cmd = text.lower().split()[0]
            arg = text.split()[1].upper() if len(text.split()) > 1 else ""

            if cmd in ("/start", "/hilfe", "/help"):
                self._cmd_hilfe()
            elif cmd == "/status":
                self._cmd_status()
            elif cmd in ("/positionen", "/pos"):
                self._cmd_positionen()
            elif cmd == "/bericht":
                self._cmd_bericht()
            elif cmd == "/sensei":
                self._cmd_sensei()
            elif cmd == "/verkauf":
                self._cmd_verkauf(arg)
            elif cmd == "/alarm":
                parts = text.split()
                self._cmd_alarm(parts[1].upper() if len(parts) > 1 else "",
                                parts[2] if len(parts) > 2 else "")
            elif cmd == "/alarme":
                self._cmd_alarme()
            elif cmd == "/alarmweg":
                self._cmd_alarmweg(arg)
            elif cmd == "/notaus":
                self._pending = ("notaus", None)
                self._pending_ts = time.time()
                self.send("\U0001F6D1 <b>NOTAUS angefordert!</b>\n"
                          "Verkauft ALLE Positionen und stoppt den Bot.\n"
                          "Zum Bestaetigen innerhalb 60s: /ja")
            elif cmd == "/ja":
                self._cmd_ja()
            elif cmd in ("/botstop", "/botstopp", "/pause"):
                self._cmd_botstop()
            elif cmd in ("/botstart", "/weiter"):
                self._cmd_botstart()
            elif cmd == "/botstatus":
                self._cmd_botstatus()
            elif cmd == "/nein":
                self._pending = None
                self.send("Abgebrochen.")
            else:
                self.send("Unbekannter Befehl. /hilfe zeigt alle Kommandos.")
        except Exception as e:
            self.send("Befehlsfehler: " + str(e)[:150])

    def _cmd_hilfe(self):
        self.send(
            "\U0001F4D6 <b>BEFEHLE</b>\n"
            "/status - Balance, P&amp;L, Ueberblick\n"
            "/positionen - offene Positionen mit PnL\n"
            "/bericht - Tagesbericht des Doc-Agents\n"
            "/sensei - Tages-Lektion vom Sensei\n"
            "/verkauf SYMBOL - Position verkaufen (z.B. /verkauf BTC)\n"
            "/alarm BTC 65000 - Preis-Alarm setzen\n"
            "/alarme - alle Alarme anzeigen\n"
            "/alarmweg BTC - Alarme fuer Coin loeschen\n"
            "/botstop - Trading pausieren\n"
            "/botstart - Trading fortsetzen\n"
            "/botstatus - laeuft/pausiert?\n"
            "/notaus - ALLES verkaufen + Bot stoppen\n"
            "/ja /nein - Bestaetigung fuer verkauf/notaus")

    def _cmd_status(self):
        e = self._engine
        bal = e.execution.get_balance()
        usdc = bal.get("total", {}).get("USDC", 0)
        positions = {s: p for s, p in e.risk_engine.open_positions.items()
                     if p.get("active")}
        pos_val = 0.0
        for sym, p in positions.items():
            price = e.data_agent.price_cache.get(sym, 0)
            pos_val += p.get("qty", 0) * price
        # Echte Zahlen aus dem Journal (nicht aus toten State-Feldern)
        _all = self._journal_stats()
        _day = self._journal_stats(since_hours=24)
        realized = _all["pnl"]
        self.send(f"\u26A1 <b>STATUS</b>\n"
                  f"USDC: {usdc:.2f}$\n"
                  f"Positionen: {len(positions)} ({pos_val:.2f}$)\n"
                  f"Gesamt: {usdc + pos_val:.2f}$\n"
                  f"Realisiert gesamt: {realized:+.2f}$\n"
                  f"P&amp;L (24h): {_day['pnl']:+.2f}$\n"
                  f"Win-Rate: {_all['win_rate']:.0f}% ({_all['sells']} Verkaeufe)")

    def _cmd_botstop(self):
        e = self._engine
        if getattr(e, "_trading_paused", False):
            self.send("\u23F8\uFE0F Bot ist bereits pausiert.")
            return
        e._trading_paused = True
        self.send("\U0001F534 <b>Bot pausiert!</b>\n"
                  "Trading gestoppt - keine neuen Trades.\n"
                  "Offene Positionen laufen weiter (Stop-Loss aktiv).\n"
                  "Mit /botstart wieder starten.")

    def _cmd_botstart(self):
        e = self._engine
        if not getattr(e, "_trading_paused", False):
            self.send("\u2139\uFE0F Bot laeuft bereits.")
            return
        e._trading_paused = False
        self.send("\U0001F7E2 <b>Bot gestartet!</b>\nTrading laeuft wieder.")

    def _cmd_botstatus(self):
        e = self._engine
        paused = getattr(e, "_trading_paused", False)
        if paused:
            self.send("\u23F8\uFE0F Trading: PAUSIERT (mit /botstart starten)")
        else:
            self.send("\U0001F7E2 Trading: AKTIV (mit /botstop pausieren)")

    def _cmd_positionen(self):
        e = self._engine
        positions = {s: p for s, p in e.risk_engine.open_positions.items()
                     if p.get("active")}
        if not positions:
            self.send("Keine offenen Positionen.")
            return
        lines = ["\U0001F4CA <b>POSITIONEN</b>"]
        for sym, p in positions.items():
            entry = p.get("entry_price", 0)
            qty = p.get("qty", 0)
            price = e.data_agent.price_cache.get(sym, 0)
            pnl_pct = ((price / entry) - 1) * 100 if entry else 0
            pnl_usd = (price - entry) * qty
            emoji = "\U0001F7E2" if pnl_usd >= 0 else "\U0001F534"
            lines.append(f"{emoji} {sym.split('/')[0]}: {qty:.4f} | "
                         f"Entry {entry:,.2f}$ | {pnl_pct:+.2f}% ({pnl_usd:+.2f}$)")
        self.send("\n".join(lines))

    def _cmd_bericht(self):
        e = self._engine
        doc = getattr(e, "doc_agent", None) or getattr(e, "doc", None)
        if doc is None:
            self.send("Doc-Agent nicht gefunden.")
            return
        # Echte Tageszahlen aus dem Journal (daily_buffer ist nach Neustart leer)
        _d = self._journal_stats(since_hours=24)
        ctx = getattr(doc, "market_context", {})
        _errs = 0
        try:
            _errs = len(doc.daily_buffer.get("errors", []))
        except Exception:
            pass
        self.send(f"\U0001F4CB <b>TAGESBERICHT (24h)</b>\n"
                  f"Trades: {_d['sells'] + _d['buys']} | Verkaeufe: {_d['sells']}\n"
                  f"Win-Rate: {_d['win_rate']:.0f}% | P&amp;L: {_d['pnl']:+.2f}$\n"
                  f"Zyklus: {ctx.get('cycle') or 'n/a'} | F&amp;G: {ctx.get('fg', 'n/a')}\n"
                  f"Fehler: {_errs}")

    def _cmd_sensei(self):
        try:
            from features.sensei import Sensei
            text = Sensei().daily_lesson()
            # HTML-Sonderzeichen entschaerfen
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.send("\U0001F94B <b>SENSEI</b>\n" + text[:3500])
        except Exception as e:
            self.send("Sensei-Fehler: " + str(e)[:150])

    def _cmd_verkauf(self, arg: str):
        if not arg:
            self.send("Nutzung: /verkauf BTC (oder /verkauf BTC/USDC)")
            return
        sym = arg if "/" in arg else arg + "/USDC"
        e = self._engine
        pos = e.risk_engine.open_positions.get(sym, {})
        if not pos.get("active"):
            self.send(f"Keine offene Position fuer {sym}.")
            return
        self._pending = ("verkauf", sym)
        self._pending_ts = time.time()
        qty = pos.get("qty", 0)
        self.send(f"\u26A0\uFE0F Verkauf {sym} ({qty:.6f}) wirklich?\n"
                  f"Bestaetigen mit /ja (60s gueltig), abbrechen mit /nein")

    def _cmd_ja(self):
        if not self._pending or time.time() - self._pending_ts > 60:
            self._pending = None
            self.send("Nichts zu bestaetigen (oder abgelaufen).")
            return
        action, sym = self._pending
        self._pending = None
        if action == "verkauf":
            ok = self._do_sell(sym)
            self.send(("\u2705 Verkauf ausgeloest: " + sym) if ok
                      else ("Verkauf fehlgeschlagen: " + sym))
        elif action == "notaus":
            e = self._engine
            sold = []
            for s, p in list(e.risk_engine.open_positions.items()):
                if p.get("active") and self._do_sell(s):
                    sold.append(s.split("/")[0])
            self.send("\U0001F6D1 NOTAUS: verkauft: " + (", ".join(sold) or "nichts")
                      + "\nBot wird gestoppt.")
            try:
                e.stop()
            except Exception as ex:
                self.send("Stop-Fehler: " + str(ex)[:120])

    # ---------------- Preis-Alarme ----------------
    def _load_alerts(self):
        import json, os
        try:
            if os.path.exists(self._alerts_path):
                with open(self._alerts_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_alerts(self):
        import json, os
        try:
            os.makedirs(os.path.dirname(self._alerts_path), exist_ok=True)
            with open(self._alerts_path, "w", encoding="utf-8") as f:
                json.dump(self._alerts, f)
        except Exception as e:
            log.warn("TELEGRAM", "Alarm-Speichern fehlgeschlagen: " + str(e)[:60])

    def _cmd_alarm(self, coin: str, preis: str):
        if not coin or not preis:
            self.send("Nutzung: /alarm BTC 65000")
            return
        sym = coin if "/" in coin else coin + "/USDC"
        try:
            target = float(preis.replace(",", "."))
        except ValueError:
            self.send("Preis nicht lesbar: " + preis)
            return
        cur = self._engine.data_agent.price_cache.get(sym, 0)
        if cur <= 0:
            self.send(f"Kein Kurs fuer {sym} verfuegbar - Coin richtig geschrieben?")
            return
        richtung = "ueber" if target > cur else "unter"
        self._alerts.append({"symbol": sym, "target": target, "richtung": richtung})
        self._save_alerts()
        self.send(f"\U0001F514 Alarm gesetzt: {sym} {richtung} {target:,.4f}$ "
                  f"(aktuell {cur:,.4f}$)")

    def _cmd_alarme(self):
        if not self._alerts:
            self.send("Keine Alarme gesetzt. /alarm BTC 65000 zum Anlegen.")
            return
        lines = ["\U0001F514 <b>ALARME</b>"]
        for i, a in enumerate(self._alerts, 1):
            cur = self._engine.data_agent.price_cache.get(a["symbol"], 0)
            lines.append(f"{i}. {a['symbol']} {a['richtung']} {a['target']:,.4f}$ "
                         f"(aktuell {cur:,.4f}$)")
        self.send("\n".join(lines))

    def _cmd_alarmweg(self, coin: str):
        if not coin:
            self.send("Nutzung: /alarmweg BTC")
            return
        sym = coin if "/" in coin else coin + "/USDC"
        before = len(self._alerts)
        self._alerts = [a for a in self._alerts if a["symbol"] != sym]
        self._save_alerts()
        self.send(f"{before - len(self._alerts)} Alarm(e) fuer {sym} geloescht.")

    def _alert_loop(self):
        """Prueft alle 30s die Preis-Alarme gegen den Live-Kurs."""
        while True:
            try:
                time.sleep(30)
                if not self._alerts:
                    continue
                fired = []
                for a in self._alerts:
                    cur = self._engine.data_agent.price_cache.get(a["symbol"], 0)
                    if cur <= 0:
                        continue
                    if ((a["richtung"] == "ueber" and cur >= a["target"]) or
                            (a["richtung"] == "unter" and cur <= a["target"])):
                        self.send(f"\U0001F6A8 <b>PREIS-ALARM {a['symbol'].split('/')[0]}</b>\n"
                                  f"Kurs {a['richtung']} {a['target']:,.4f}$!\n"
                                  f"Aktuell: {cur:,.4f}$")
                        fired.append(a)
                if fired:
                    self._alerts = [a for a in self._alerts if a not in fired]
                    self._save_alerts()
            except Exception as e:
                log.warn("TELEGRAM", "Alarm-Loop-Fehler: " + str(e)[:60])
                time.sleep(30)

    def _do_sell(self, sym: str) -> bool:
        """Verkauft ueber denselben Weg wie der MANUELL-Tab im GUI."""
        try:
            from core.events import DecisionIntent, Side, EVENT_SIGNAL
            e = self._engine
            pos = e.risk_engine.open_positions.get(sym, {})
            qty = pos.get("qty", 0)
            price = e.data_agent.price_cache.get(sym, 0)
            if qty <= 0 or price <= 0:
                return False
            intent = DecisionIntent(
                symbol=sym, side=Side.SELL, confidence=1.0,
                entry_price=price, quantity=qty,
                strategy_id="TELEGRAM_SELL", entry_reason="Per Telegram verkauft",
                score=10, agent_id="telegram")
            e.bus.publish(EVENT_SIGNAL, intent, source="telegram")
            return True
        except Exception as ex:
            log.warn("TELEGRAM", "Sell-Fehler: " + str(ex)[:80])
            return False

    def get_status(self) -> Dict:
        return {"enabled": self.enabled, "daily_trades": len(self.daily_trades),
                "weekly_trades": len(self.weekly_trades)}
