"""
Trading Imperium V5 – Trade Journal
Persistentes Trade-Tagebuch. Speichert JEDEN Trade mit allen Details.
Lernt aus Ergebnissen fuer zukuenftige Entscheidungen.
"""
import json
import os
import time
import threading
import shutil
from typing import Dict, List
from config.settings import DATA_DIR
from core.logger import log

JOURNAL_FILE = os.path.join(DATA_DIR, "trade_journal.json")


class TradeJournal:
    """Persistentes Trade-Tagebuch mit Analyse-Funktionen."""

    def __init__(self):
        self._lock = threading.Lock()
        self.trades = []
        self._load()

    def add(self, trade: Dict):
        """Fuegt einen Trade hinzu und speichert."""
        trade["journal_time"] = time.time()
        with self._lock:
            self.trades.append(trade)
            self._save()
        log.info("JOURNAL", f"{trade.get('type', '?')} {trade.get('coin', '?')}: "
                            f"{trade.get('qty', 0):.6f} @ {trade.get('price', 0):,.2f}$")

    def get_all(self, last_n=None) -> List[Dict]:
        with self._lock:
            if last_n:
                return list(self.trades[-last_n:])
            return list(self.trades)

    def get_last(self, n=10) -> List[Dict]:
        """Gibt die letzten n Trades zurueck."""
        with self._lock:
            return list(self.trades[-n:])

    def clear(self):
        """Loescht alle Trades und speichert den leeren Zustand persistent."""
        with self._lock:
            self.trades = []
            try:
                self._save()
            except Exception as e:
                log.warn("JOURNAL", f"Clear-Save fehlgeschlagen: {e}")
        log.info("JOURNAL", "Journal geleert (alle Trades geloescht)")

    def save(self):
        """Public Save-Methode (Wrapper fuer _save)."""
        with self._lock:
            self._save()

    def count(self) -> int:
        return len(self.trades)

    def get_stats(self) -> Dict:
        """Berechnet Gesamt-Statistiken."""
        sells = [t for t in self.trades if t.get("type") in ("SELL", "sell")]
        buys = [t for t in self.trades if t.get("type") in ("BUY", "buy")]
        pnls = [t.get("pnl", 0) for t in sells if isinstance(t.get("pnl"), (int, float))]
        total_pnl = sum(pnls)
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        wr = (wins / len(pnls) * 100) if pnls else 0

        # Beste/Schlechteste Trades
        best = max(pnls) if pnls else 0
        worst = min(pnls) if pnls else 0

        # Strategie-Performance
        strat_stats = {}
        for t in sells:
            s = t.get("strategy", "?")
            if s not in strat_stats:
                strat_stats[s] = {"trades": 0, "pnl": 0, "wins": 0}
            strat_stats[s]["trades"] += 1
            p = t.get("pnl", 0)
            if isinstance(p, (int, float)):
                strat_stats[s]["pnl"] += p
                if p > 0:
                    strat_stats[s]["wins"] += 1

        return {
            "total_trades": len(self.trades),
            "buys": len(buys), "sells": len(sells),
            "total_pnl": round(total_pnl, 2),
            "wins": wins, "losses": losses,
            "win_rate": round(wr, 1),
            "avg_pnl": round(total_pnl / len(pnls), 2) if pnls else 0,
            "best_trade": round(best, 2),
            "worst_trade": round(worst, 2),
            "strategies": strat_stats,
        }

    def get_by_coin(self, coin) -> List[Dict]:
        """Alle Trades fuer einen bestimmten Coin."""
        return [t for t in self.trades if coin in t.get("coin", t.get("symbol", ""))]

    def get_by_strategy(self, strategy) -> List[Dict]:
        """Alle Trades einer bestimmten Strategie."""
        return [t for t in self.trades if t.get("strategy") == strategy]

    def export_txt(self, filepath=None) -> str:
        """Exportiert als formatierter Text."""
        stats = self.get_stats()
        lines = [
            f"{'=' * 80}",
            f"  TRADING IMPERIUM V5 – TRADE JOURNAL",
            f"  Erstellt: {time.strftime('%d.%m.%Y %H:%M:%S')}",
            f"{'=' * 80}",
            f"",
            f"  Trades: {stats['total_trades']} | Sells: {stats['sells']} | "
            f"P&L: {stats['total_pnl']:+.2f}$ | Win-Rate: {stats['win_rate']:.0f}%",
            f"  Bester: {stats['best_trade']:+.2f}$ | Schlechtester: {stats['worst_trade']:+.2f}$",
            f"",
            f"{'─' * 80}",
            f"{'Zeit':<22}{'Typ':<8}{'Coin':<12}{'Menge':>12}{'Preis':>12}{'P&L':>10}{'Strategie':<14}",
            f"{'─' * 80}",
        ]
        for t in self.trades[-100:]:
            ts = str(t.get("time", ""))[:19]
            typ = str(t.get("type", "?"))[:6]
            coin = str(t.get("coin", "?")).split("/")[0][:10]
            qty = t.get("qty", 0)
            price = t.get("price", 0)
            pnl = t.get("pnl", "")
            pnl_s = f"{pnl:+.2f}" if isinstance(pnl, (int, float)) and pnl != 0 else ""
            strat = str(t.get("strategy", ""))[:13]
            lines.append(f"{ts:<22}{typ:<8}{coin:<12}{qty:>12.6f}{price:>11,.2f}${pnl_s:>10}{strat:<14}")

        text = "\n".join(lines)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)
            log.info("JOURNAL", f"Export: {filepath}")
        return text

    def _load(self):
        # 1) Hauptdatei versuchen
        loaded = self._try_load_file(JOURNAL_FILE)
        # 2) Wenn leer/kaputt: .bak versuchen
        if not loaded:
            bak = JOURNAL_FILE + ".bak"
            alt = self._try_load_file(bak)
            if alt:
                self.trades = alt
                log.warn("JOURNAL", f"Hauptdatei leer/kaputt - aus .bak wiederhergestellt: {len(alt)} Trades")
                try:
                    self._save()
                except Exception:
                    pass
                return
            # 3) Letzter Rettungsanker: aus order_history.json rekonstruieren
            recovered = self._recover_from_orders()
            if recovered:
                self.trades = recovered
                log.warn("JOURNAL", f"Aus order_history.json rekonstruiert: {len(recovered)} Trades")
                try:
                    self._save()
                except Exception:
                    pass
                return
            self.trades = []
            return
        self.trades = loaded
        log.info("JOURNAL", f"Geladen: {len(self.trades)} Trades")

    def _try_load_file(self, path):
        """Laedt eine Journal-Datei; gibt Liste zurueck oder None bei leer/kaputt."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return data
            return None
        except Exception as e:
            log.warn("JOURNAL", f"Laden fehlgeschlagen ({os.path.basename(path)}): {e}")
            return None

    def _recover_from_orders(self):
        """Baut das Journal aus order_history.json neu (FIFO-Netto-P&L mit Gebuehren)."""
        oh = os.path.join(os.path.dirname(JOURNAL_FILE), "order_history.json")
        if not os.path.exists(oh):
            return None
        try:
            with open(oh, "r", encoding="utf-8") as f:
                d = json.load(f)
            orders = d if isinstance(d, list) else d.get("orders", d.get("trades", []))
            orders = [o for o in orders if str(o.get("status", "filled")) == "filled"]
            orders.sort(key=lambda o: float(o.get("created_at", 0) or 0))
        except Exception:
            return None
        from datetime import datetime as _dt, timezone as _tz
        lots, journal = {}, []
        for o in orders:
            sym = o.get("symbol", o.get("coin", "?"))
            side = str(o.get("side", o.get("type", ""))).upper()
            price = float(o.get("fill_price", o.get("price", 0)) or 0)
            qty = float(o.get("fill_qty", o.get("qty", 0)) or 0)
            fee = float(o.get("fee", 0) or 0)
            t = o.get("created_at", o.get("time", ""))
            try:
                tiso = _dt.fromtimestamp(float(t), _tz.utc).isoformat() if not isinstance(t, str) else t
            except Exception:
                tiso = str(t)
            if qty <= 0 or price <= 0:
                continue
            e = {"symbol": sym, "coin": sym, "type": side, "side": side,
                 "price": price, "qty": qty, "fee": fee,
                 "strategy": o.get("strategy", ""), "reason": o.get("reason", ""), "time": tiso}
            if "BUY" in side:
                cost_per = (price * qty + fee) / qty if qty else price
                lots.setdefault(sym, []).append([qty, cost_per])
                journal.append(e)
            elif "SELL" in side:
                proceeds = price * qty - fee
                remaining, cost_basis = qty, 0.0
                cl = lots.get(sym, [])
                while remaining > 1e-12 and cl:
                    lq, lc = cl[0]
                    take = min(remaining, lq)
                    cost_basis += take * lc
                    lq -= take; remaining -= take
                    if lq <= 1e-12: cl.pop(0)
                    else: cl[0][0] = lq
                pnl = proceeds - cost_basis
                e["pnl"] = round(pnl, 4)
                e["pnl_pct"] = round((pnl / cost_basis * 100) if cost_basis else 0.0, 2)
                journal.append(e)
        return journal if journal else None

    def _save(self):
        try:
            os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
            data = self.trades[-2000:]
            # NICHT leer ueber volle Datei schreiben (Absturz-Schutz):
            # ein leeres Journal nur zulassen, wenn wirklich keine Trades da sind
            tmp = JOURNAL_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, default=str)
                f.flush()
                os.fsync(f.fileno())          # ERZWINGT Schreiben auf die Platte
            # Vorherige gute Datei als .bak sichern (copy, nicht move)
            if os.path.exists(JOURNAL_FILE) and os.path.getsize(JOURNAL_FILE) > 2:
                try:
                    shutil.copy2(JOURNAL_FILE, JOURNAL_FILE + ".bak")
                except Exception:
                    pass
            os.replace(tmp, JOURNAL_FILE)     # atomar
        except Exception as e:
            log.warn("JOURNAL", f"Speichern: {e}")
