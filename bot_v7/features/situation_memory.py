"""
Trading Imperium V6 - Situation Memory (Shadow v1)
===================================================

+---------------------------------------------------------------+
|  NICHT VERDRAHTET - Stand 11.08.2026                          |
|                                                               |
|  Dieses Modul laeuft NICHT im Bot. Es wird von app.py nirgends |
|  aufgerufen; seine Datei data_store/situation_memory.json      |
|  existiert nicht, es ist also noch kein einziges Mal gelaufen. |
|  Einziger Nutzer ist situation_replay.py - ein Werkzeug zum    |
|  Nachspielen von Hand, kein Teil des Handelspfads.             |
|                                                               |
|  Bewusst so gelassen (Entscheidung des Eigentuemers vom        |
|  11.08.2026): Entfernen kostet Arbeit und wuerde               |
|  situation_replay.py brechen; liegen lassen kostet nichts,     |
|  weil null Laufzeit-Referenzen auch null Risiko bedeuten.      |
|                                                               |
|  Wer hier etwas misst: die Zahlen stammen NICHT aus dem        |
|  Betrieb. Vor jeder Verwendung erst verdrahten und messen.     |
+---------------------------------------------------------------+
kNN-Aehnlichkeitsgedaechtnis fuer Marktsituationen.
Frage bei jedem Signal: "Wann sah der Markt zuletzt SO aus -
und was ist danach passiert?"

SHADOW-MODUS: Dieses Modul trifft KEINE Trading-Entscheidungen.
Es beobachtet, vergleicht und loggt. Aktive Nutzung erst nach
nachgewiesener Vorhersagekraft in eigener Epoche (E7-Kandidat).

Datenquelle: impact_journal.json (Kontext beim Entry + Outcome beim Exit).
Fehlende Features (rsi=0, adx=0, nupl=0) werden per Masking ignoriert,
statt die Distanz zu verzerren.

Ziel-Pfad: features/situation_memory.py
Keine externen Abhaengigkeiten (pure Python).
"""
import os
import json
import math
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# --- Logger: echter Bot-Logger, Fallback fuer Standalone-Nutzung ---
try:
    from core.logger import log
except Exception:
    class _StubLog:
        def info(self, tag, msg): print(f"[{tag}] {msg}")
        def warn(self, tag, msg): print(f"[{tag}] WARN {msg}")
    log = _StubLog()

try:
    from config.settings import DATA_DIR
except Exception:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

MEMORY_FILE = os.path.join(DATA_DIR, "situation_memory.json")

# Kategorische Dimensionen (one-hot). Unbekannte Werte -> eigene "OTHER"-Dim.
REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "TRENDING", "RANGING", "VOLATILE"]
CYCLES = ["EARLY_BULL", "MID_BULL", "EUPHORIA", "DISTRIBUTION",
          "EARLY_BEAR", "MID_BEAR", "DEEP_BEAR", "CAPITULATION", "ACCUMULATION"]

# Numerische Features: (context-key, normalisierung, gewicht, missing-wert)
# Wert == missing-Wert => Dimension wird maskiert (zaehlt nicht in Distanz).
NUMERIC_FEATURES = [
    ("fear_greed", 100.0, 1.5, None),   # 0 ist bei F&G ein gueltiger Wert
    ("rsi",        100.0, 1.0, 0),      # 0 = nicht befuellt (bekannte Luecke)
    ("adx",        100.0, 0.75, 0),
    ("nupl",         1.0, 0.5, 0),
    ("mtf_confluence", 5.0, 0.5, 0),
]
W_REGIME = 1.5   # Gewicht pro kategorischer Gruppe
W_CYCLE = 1.5


class SituationMemory:
    """Speichert Marktsituationen (Kontext beim Entry) samt Outcome und
    findet per gewichteter, maskierter Distanz die aehnlichsten Faelle."""

    def __init__(self, path: Optional[str] = None, autoload: bool = True):
        self.path = path or MEMORY_FILE
        self.situations: List[Dict] = []
        if autoload:
            self._load()

    # ------------------------------------------------------------------
    # Persistenz
    # ------------------------------------------------------------------
    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.situations = data.get("situations", [])
                elif isinstance(data, list):
                    self.situations = data
                log.info("SIT-MEM", f"{len(self.situations)} Situationen geladen")
        except Exception as e:
            log.warn("SIT-MEM", f"Load-Fehler: {str(e)[:120]}")
            self.situations = []

    def save(self):
        try:
            tmp = self.path + ".tmp"
            payload = {
                "saved_at": datetime.now().isoformat(),
                "count": len(self.situations),
                "situations": self.situations,
            }
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=1)
            os.replace(tmp, self.path)
        except Exception as e:
            log.warn("SIT-MEM", f"Save-Fehler: {str(e)[:120]}")

    # ------------------------------------------------------------------
    # Aufnahme von Situationen
    # ------------------------------------------------------------------
    def add_situation(self, context: Dict, ts: float, symbol: str = "",
                      strategy: str = "", pnl_pct: Optional[float] = None,
                      sell_reason: str = "", status: str = "OPEN",
                      sit_id: str = "") -> Dict:
        """Fuegt eine Situation hinzu. Outcome darf spaeter via
        update_outcome() nachgetragen werden (Shadow-Live-Betrieb)."""
        sit = {
            "id": sit_id or f"sit_{int(ts)}_{symbol.replace('/', '')}",
            "ts": float(ts),
            "symbol": symbol,
            "strategy": strategy,
            "context": dict(context or {}),
            "pnl_pct": pnl_pct,
            "sell_reason": sell_reason,
            "status": status,
        }
        self.situations.append(sit)
        return sit

    def update_outcome(self, sit_id: str, pnl_pct: float,
                       sell_reason: str = "", status: str = "") -> bool:
        for s in reversed(self.situations):
            if s.get("id") == sit_id:
                s["pnl_pct"] = round(float(pnl_pct), 3)
                s["sell_reason"] = sell_reason or s.get("sell_reason", "")
                s["status"] = status or ("WIN" if pnl_pct > 0 else "LOSS")
                return True
        return False

    def load_impact_journal(self, path: str, closed_only: bool = True) -> int:
        """Importiert Situationen aus impact_journal.json (Format V6)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", data if isinstance(data, list) else [])
        except Exception as e:
            log.warn("SIT-MEM", f"Impact-Journal nicht lesbar: {str(e)[:120]}")
            return 0

        added = 0
        for e in entries:
            if e.get("side") != "BUY":
                continue
            status = e.get("status", "OPEN")
            if closed_only and status not in ("WIN", "LOSS"):
                continue
            ts = _parse_ts(e.get("timestamp"))
            if ts is None:
                continue
            self.add_situation(
                context=e.get("context") or {},
                ts=ts,
                symbol=e.get("symbol", ""),
                strategy=e.get("strategy", ""),
                pnl_pct=e.get("pnl_pct"),
                sell_reason=e.get("sell_reason") or "",
                status=status,
                sit_id=e.get("id", ""),
            )
            added += 1
        log.info("SIT-MEM", f"{added} Situationen aus Impact-Journal importiert")
        return added

    # ------------------------------------------------------------------
    # Aehnlichkeitssuche
    # ------------------------------------------------------------------
    def query(self, context: Dict, k: int = 5, before_ts: Optional[float] = None,
              same_symbol: str = "", min_neighbors: int = 3) -> Dict:
        """Findet die k aehnlichsten ABGESCHLOSSENEN Situationen.

        before_ts: nur Situationen VOR diesem Zeitpunkt beruecksichtigen
                   (Pflicht fuer Replay -> kein Lookahead!).
        same_symbol: optionaler Filter auf denselben Coin.
        """
        candidates = []
        for s in self.situations:
            if s.get("pnl_pct") is None:
                continue
            if before_ts is not None and s.get("ts", 0) >= before_ts:
                continue
            if same_symbol and s.get("symbol") != same_symbol:
                continue
            d = self._distance(context, s.get("context") or {})
            if d is not None:
                candidates.append((d, s))

        candidates.sort(key=lambda x: x[0])
        neighbors = candidates[:max(1, k)]

        result = {
            "n": len(neighbors),
            "pool": len(candidates),
            "reliable": len(neighbors) >= min_neighbors,
            "wins": 0, "losses": 0, "win_rate": None,
            "avg_pnl_pct": None, "worst_pnl_pct": None, "best_pnl_pct": None,
            "avg_distance": None,
            "neighbors": [],
        }
        if not neighbors:
            return result

        pnls = []
        for d, s in neighbors:
            p = float(s["pnl_pct"])
            pnls.append(p)
            if p > 0:
                result["wins"] += 1
            else:
                result["losses"] += 1
            result["neighbors"].append({
                "id": s.get("id"), "symbol": s.get("symbol"),
                "strategy": s.get("strategy"), "pnl_pct": p,
                "sell_reason": s.get("sell_reason", ""),
                "distance": round(d, 4),
            })
        n = len(pnls)
        result["win_rate"] = round(result["wins"] / n, 3)
        result["avg_pnl_pct"] = round(sum(pnls) / n, 3)
        result["worst_pnl_pct"] = round(min(pnls), 3)
        result["best_pnl_pct"] = round(max(pnls), 3)
        result["avg_distance"] = round(sum(d for d, _ in neighbors) / n, 4)
        return result

    def shadow_line(self, context: Dict, symbol: str = "", k: int = 5) -> str:
        """Eine Log-Zeile fuer den Shadow-Betrieb neben einem Signal."""
        r = self.query(context, k=k)
        if not r["reliable"]:
            return (f"SIT-MEM [{symbol}]: zu wenig Vergleichsdaten "
                    f"({r['n']}/{k}, Pool {r['pool']})")
        return (f"SIT-MEM [{symbol}]: {r['n']} aehnliche Situationen -> "
                f"{r['wins']}W/{r['losses']}L, Oe {r['avg_pnl_pct']:+.2f}%, "
                f"worst {r['worst_pnl_pct']:+.2f}% "
                f"(Distanz {r['avg_distance']:.2f})")

    # ------------------------------------------------------------------
    # Distanz: gewichtete Dimensionen + Masking fuer fehlende Werte
    # ------------------------------------------------------------------
    @staticmethod
    def _distance(c1: Dict, c2: Dict) -> Optional[float]:
        total = 0.0
        weight_sum = 0.0

        # Kategorisch: Regime
        r1 = str(c1.get("regime", "") or "")
        r2 = str(c2.get("regime", "") or "")
        if r1 and r2:
            total += W_REGIME * (0.0 if r1 == r2 else 1.0)
            weight_sum += W_REGIME

        # Kategorisch: Cycle
        y1 = str(c1.get("cycle", "") or "")
        y2 = str(c2.get("cycle", "") or "")
        if y1 and y2:
            total += W_CYCLE * (0.0 if y1 == y2 else 1.0)
            weight_sum += W_CYCLE

        # Numerisch mit Masking
        for key, norm, w, missing in NUMERIC_FEATURES:
            v1 = c1.get(key, missing)
            v2 = c2.get(key, missing)
            if v1 is None or v2 is None:
                continue
            if missing is not None and (v1 == missing or v2 == missing):
                continue  # Dimension nicht befuellt -> ignorieren
            try:
                diff = (float(v1) - float(v2)) / norm
            except (TypeError, ValueError):
                continue
            total += w * (diff * diff)
            weight_sum += w

        if weight_sum <= 0:
            return None  # keine vergleichbare Dimension vorhanden
        return math.sqrt(total / weight_sum)

    # ------------------------------------------------------------------
    def stats(self) -> Dict:
        closed = [s for s in self.situations if s.get("pnl_pct") is not None]
        wins = sum(1 for s in closed if s["pnl_pct"] > 0)
        return {
            "total": len(self.situations),
            "closed": len(closed),
            "open": len(self.situations) - len(closed),
            "wins": wins,
            "losses": len(closed) - wins,
        }


def _parse_ts(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except Exception:
        return None


if __name__ == "__main__":
    # Mini-Selbsttest mit synthetischen Daten
    mem = SituationMemory(path="_selftest_memory.json", autoload=False)
    base = time.time() - 86400 * 30
    for i in range(40):
        ctx = {"regime": "RANGING" if i % 2 else "TRENDING_DOWN",
               "cycle": "MID_BEAR", "fear_greed": 10 + i % 30,
               "rsi": 0, "adx": 0, "nupl": 0, "mtf_confluence": 0}
        pnl = 0.5 if i % 2 else -2.5  # RANGING gewinnt, TRENDING_DOWN verliert
        mem.add_situation(ctx, ts=base + i * 3600, symbol="BTC/USDC",
                          strategy="DCA_FEAR_GREED", pnl_pct=pnl,
                          status="WIN" if pnl > 0 else "LOSS")
    q = {"regime": "TRENDING_DOWN", "cycle": "MID_BEAR", "fear_greed": 15,
         "rsi": 0, "adx": 0, "nupl": 0, "mtf_confluence": 0}
    print(mem.shadow_line(q, "BTC/USDC"))
    r = mem.query(q, k=5)
    assert r["win_rate"] == 0.0, "Selbsttest: Nachbarn muessten alle LOSS sein"
    q2 = dict(q, regime="RANGING")
    r2 = mem.query(q2, k=5)
    assert r2["win_rate"] == 1.0, "Selbsttest: Nachbarn muessten alle WIN sein"
    print(mem.shadow_line(q2, "BTC/USDC"))
    print("Selbsttest OK:", mem.stats())
