"""
Trading Imperium V5 – State Store
Persistenter Zustandsspeicher. Überlebt Abstürze und Neustarts.
Atomic Writes verhindern korrupte Dateien.
"""
import os
import json
import time
import shutil          # [FIX 29.07.] fehlte auf Modulebene -> TradeJournal._save()
                       # warf stumm NameError, das .bak wurde NIE geschrieben.
import threading
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from config.settings import DATA_DIR


class StateStore:
    """Thread-sicherer, persistenter Key-Value Store."""

    def __init__(self, name: str = "state"):
        self._name = name
        self._file = os.path.join(DATA_DIR, f"{name}.json")
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._dirty = False
        self._load()

    def _load(self):
        """Laedt den Zustand. [CRASH-SAFE PATCH] Probiert Haupt-, .bak- und .tmp-Datei der Reihe nach."""
        candidates = [self._file, self._file + ".bak", self._file + ".tmp"]
        for cand in candidates:
            if not os.path.exists(cand):
                continue
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._data = data
                    if cand != self._file:
                        print(f"[STATE] '{self._name}' aus {os.path.basename(cand)} wiederhergestellt")
                    return
            except Exception as e:
                print(f"[STATE] '{self._name}' {os.path.basename(cand)} unlesbar: {e}")
                continue
        self._data = {}

    def save(self):
        """Speichert atomar. [CRASH-SAFE PATCH] Erst tmp+fsync, dann .bak kopieren, dann ersetzen."""
        with self._lock:
            try:
                self._data["_saved_at"] = datetime.now(timezone.utc).isoformat()
                tmp = self._file + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2, default=str, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                # Erst jetzt die noch gueltige Hauptdatei sichern (kopieren, nicht verschieben)
                if os.path.exists(self._file):
                    try:
                        shutil.copy2(self._file, self._file + ".bak")
                    except Exception:
                        pass
                # Atomar ersetzen - es existiert zu jedem Zeitpunkt eine gueltige Datei
                os.replace(tmp, self._file)
                self._dirty = False
            except Exception as e:
                print(f"[STATE] save fehlgeschlagen: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Liest einen Wert."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Setzt einen Wert."""
        with self._lock:
            self._data[key] = value
            self._dirty = True

    def delete(self, key: str):
        """Löscht einen Wert."""
        with self._lock:
            self._data.pop(key, None)
            self._dirty = True

    def get_all(self) -> Dict:
        """Gibt alle Daten zurück."""
        with self._lock:
            return dict(self._data)

    def update(self, data: Dict):
        """Aktualisiert mehrere Werte gleichzeitig."""
        with self._lock:
            self._data.update(data)
            self._dirty = True

    def is_dirty(self) -> bool:
        """Prüft ob ungespeicherte Änderungen existieren."""
        return self._dirty

    def clear(self):
        """Löscht alle Daten."""
        with self._lock:
            self._data = {}
            self._dirty = True


class TradeJournal:
    """Spezieller Store für Trade-History – append-only, nie überschreiben."""

    def __init__(self, name: str = "trades"):
        self._file = os.path.join(DATA_DIR, f"{name}.json")
        self._lock = threading.Lock()
        self._trades = self._load()

    def _load(self) -> list:
        # [E10-JOURNAL 29.07.] "leer" ist NICHT "kaputt".
        # Vorher galt eine gueltige leere Liste als unlesbar und loeste die
        # Wiederherstellung aus .bak aus. Solange das .bak wegen des
        # shutil-NameErrors (E9-5) nie geschrieben wurde, fiel das nicht auf.
        # Mit repariertem Backup wuerde jedes bewusst geleerte Journal beim
        # naechsten Start wieder auferstehen - ein Reset waere unmoeglich.
        # Jetzt: None = fehlt/unlesbar, [] = gueltig und absichtlich leer.
        data = self._try_load_file(self._file)
        if data is not None:
            return data
        # 2) .bak
        alt = self._try_load_file(self._file + ".bak")
        if alt:
            print(f"[JOURNAL] Hauptdatei leer/kaputt - aus .bak wiederhergestellt: {len(alt)} Trades")
            self._trades = alt
            try: self._save()
            except Exception: pass
            return alt
        # 3) aus order_history.json rekonstruieren (letzter Rettungsanker)
        rec = self._recover_from_orders()
        if rec:
            print(f"[JOURNAL] Aus order_history.json rekonstruiert: {len(rec)} Trades")
            self._trades = rec
            try: self._save()
            except Exception: pass
            return rec
        return []

    def _try_load_file(self, path) -> list:
        """Laedt eine Journal-Datei.

        Rueckgabe:
          None  -> Datei fehlt, ist unlesbar oder enthaelt keine Liste
                   (echter Schaden -> Aufrufer soll das .bak probieren)
          []    -> Datei ist in Ordnung und absichtlich leer (nach clear())
          [...] -> Trades
        """
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except Exception:
            return None

    def _recover_from_orders(self):
        oh = os.path.join(os.path.dirname(self._file), "order_history.json")
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
        lots, journal = {}, []
        for o in orders:
            sym = o.get("symbol", o.get("coin", "?"))
            side = str(o.get("side", o.get("type", ""))).upper()
            price = float(o.get("fill_price", o.get("price", 0)) or 0)
            qty = float(o.get("fill_qty", o.get("qty", 0)) or 0)
            fee = float(o.get("fee", 0) or 0)
            t = o.get("created_at", o.get("time", ""))
            try:
                tiso = datetime.fromtimestamp(float(t), timezone.utc).isoformat() if not isinstance(t, str) else t
            except Exception:
                tiso = str(t)
            if qty <= 0 or price <= 0:
                continue
            e = {"symbol": sym, "coin": sym, "type": side,
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

    def add(self, trade: Dict):
        """Fügt einen Trade hinzu und speichert sofort."""
        with self._lock:
            trade["_id"] = len(self._trades) + 1
            trade["_saved_at"] = datetime.now(timezone.utc).isoformat()
            self._trades.append(trade)
            self._save()

    def save(self):
        """Oeffentliche Save-Methode."""
        with self._lock:
            self._save()

    @property
    def _speicher(self):
        """[AUDIT 06.08.2026] Zustand des Buchhaltungs-Schreibpfads.

        Bewusst je Instanz (nicht als Klassen-Attribut), damit sich die
        Zaehler zweier Journale nie vermischen. Lazy angelegt, weil auch
        Recovery-Pfade ohne __init__ auf _save() laufen koennen.
        """
        s = self.__dict__.get("_speicher_zustand")
        if s is None:
            s = {"fehler_serie": 0, "seit": 0.0, "letzter": "",
                 "gesamt": 0, "ok_um": 0.0}
            self.__dict__["_speicher_zustand"] = s
        return s

    @staticmethod
    def _log():
        """Logger erst bei Bedarf holen (vermeidet Import-Zyklus)."""
        from core.logger import log
        return log

    def speicher_status(self) -> Dict:
        """[AUDIT 06.08.2026] Ehrlicher Zustand des Journal-Schreibpfads.

        gesund=False heisst: die Trades stehen im Speicher, aber NICHT auf
        der Platte. Ein Absturz in diesem Zustand kostet die Buchhaltung.
        """
        s = dict(self._speicher)
        s["gesund"] = (s["fehler_serie"] == 0)
        s["alter_sec"] = int(time.time() - s["ok_um"]) if s["ok_um"] else -1
        return s

    def _melde_erfolg(self):
        """Nach einer Fehlerserie genau EINMAL Entwarnung geben."""
        s = self._speicher
        if s["fehler_serie"]:
            dauer = int(time.time() - (s["seit"] or time.time()))
            try:
                self._log().warn("JOURNAL",
                    f"Speichern wieder OK nach {s['fehler_serie']} Fehlversuchen "
                    f"({dauer}s blind). Kein Datenverlust - die Trades lagen die "
                    f"ganze Zeit im Speicher und sind jetzt auf der Platte.")
            except Exception:
                pass
        s["fehler_serie"] = 0
        s["seit"] = 0.0
        s["ok_um"] = time.time()

    def _melde_fehler(self, e):
        """Ein Speicherfehler darf NIE wieder still bleiben.

        Vorher stand hier nur print() - das landet im cmd-Fenster und
        sonst nirgends: nicht im system.log, nicht beim HealthMonitor,
        nicht beim Scheduler (der zaehlt nur Fehler, die AUS dem Task
        herausfliegen - diese hier wurde vorher geschluckt). Am 06.08.2026
        hat der Bot deshalb ueber eine Stunde lang nicht persistiert,
        ohne dass ein einziger Waechter angeschlagen hat.
        """
        s = self._speicher
        s["fehler_serie"] += 1
        s["gesamt"] += 1
        s["letzter"] = f"{type(e).__name__}: {str(e)[:150]}"
        if not s["seit"]:
            s["seit"] = time.time()
        try:
            self._log().error("JOURNAL",
                f"Trade-Journal NICHT gespeichert ({s['fehler_serie']}x in Folge, "
                f"{len(self._trades)} Trades nur im RAM): {s['letzter']}")
        except Exception:
            print(f"[JOURNAL] Speichern fehlgeschlagen "
                  f"({s['fehler_serie']}x): {s['letzter']}")

    def _save(self):
        try:
            tmp = self._file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._trades, f, indent=1, default=str, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())          # erzwingt Schreiben auf Platte (Absturzschutz)
            # [AUDIT 06.08.2026] Retry statt Einmalversuch. os.replace scheitert
            # auf Windows mit WinError 5, sobald ein anderer Thread die Zieldatei
            # gerade zum Lesen offen haelt (Pythons open() setzt kein
            # FILE_SHARE_DELETE). Genau diese Kollision entsteht hier: der
            # Scheduler faehrt jeden Task in einem eigenen Thread, auto_save
            # schreibt alle 30 s, daily_loss.pruefe() liest trades_v5.json bei
            # jedem Trading-Tick (alle 12 s). Ein kurzer Retry loest praktisch
            # jede dieser Ueberlappungen; was ihn ueberlebt, wird laut gemeldet.
            _fehler = None
            for _pause in (0.05, 0.15, 0.40, 0.0):
                try:
                    os.replace(tmp, self._file)   # atomar
                    _fehler = None
                    break
                except OSError as _e:
                    _fehler = _e
                    if _pause:
                        time.sleep(_pause)
            if _fehler is not None:
                raise _fehler
            # [E10-JOURNAL 29.07.] .bak ERST NACH dem Ersetzen ziehen.
            # Vorher wurde die noch alte Hauptdatei gesichert, das .bak hinkte
            # also immer einen Trade hinterher - bei einer beschaedigten
            # Hauptdatei war der letzte Trade unwiederbringlich weg (im Test:
            # 3 von 4 gerettet). Jetzt entspricht das .bak exakt dem letzten
            # erfolgreich geschriebenen Stand. Stirbt der Prozess waehrend des
            # Kopierens, ist zwar das .bak unvollstaendig - die Hauptdatei ist
            # zu diesem Zeitpunkt aber bereits atomar korrekt.
            if os.path.exists(self._file) and os.path.getsize(self._file) > 2:
                try:
                    shutil.copy2(self._file, self._file + ".bak")
                except Exception:
                    pass
            self._melde_erfolg()              # [AUDIT 06.08.2026]
        except Exception as e:
            self._melde_fehler(e)             # [AUDIT 06.08.2026] statt stillem print()

    def clear(self, backup: bool = True) -> int:
        """Leert das Journal. Gibt die Anzahl der geloeschten Trades zurueck.

        [E10-JOURNAL 29.07.2026] Diese Methode fehlte. app.py hat sie beim
        Selbsttest zur Laufzeit angeflanscht ("clear() Methode dynamisch
        hinzugefuegt (Auto-Repair)") - und der Ersatz griff auf `trades` statt
        auf `_trades` zu. Er legte also ein NEUES, leeres Attribut an, waehrend
        _save() unveraendert die alten _trades schrieb. Folge: der Reset-Knopf
        im UI (ui/main_window.py:2454) hat das Journal nie geleert, sondern nur
        so getan. Jetzt eine echte Methode - der Auto-Repair feuert nie wieder.

        Vor dem Leeren wird eine datierte Sicherung abgelegt; ein Journal ist
        die Buchfuehrung, das loescht man nicht ersatzlos.
        """
        with self._lock:
            anzahl = len(self._trades)
            if backup and anzahl > 0:
                try:
                    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ziel = f"{self._file}.vor_clear_{stempel}"
                    if os.path.exists(self._file):
                        shutil.copy2(self._file, ziel)
                        print(f"[JOURNAL] Sicherung vor clear(): {os.path.basename(ziel)}")
                except Exception as e:
                    print(f"[JOURNAL] Sicherung vor clear() fehlgeschlagen: {e}")
            self._trades = []
            self._save()
        return anzahl

    def get_all(self) -> list:
        with self._lock:
            return list(self._trades)

    def get_last(self, n: int = 20) -> list:
        with self._lock:
            return self._trades[-n:]

    def get_by_type(self, trade_type: str) -> list:
        with self._lock:
            return [t for t in self._trades if t.get("type") == trade_type]

    def get_stats(self) -> Dict:
        """Berechnet Trade-Statistiken."""
        with self._lock:
            sells = [t for t in self._trades if t.get("type") == "SELL" and isinstance(t.get("pnl"), (int, float))]
            wins = [t for t in sells if t["pnl"] > 0]
            losses = [t for t in sells if t["pnl"] <= 0]
            total_pnl = sum(t["pnl"] for t in sells)
            buys = [t for t in self._trades if "BUY" in t.get("type", "")]
            total_invested = sum(t.get("amount", 0) for t in buys)

            return {
                "total_trades": len(self._trades),
                "buys": len(buys),
                "sells": len(sells),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": (len(wins) / len(sells) * 100) if sells else 0,
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": round(total_pnl / len(sells), 2) if sells else 0,
                "total_invested": round(total_invested, 2),
            }

    def count(self) -> int:
        return len(self._trades)
