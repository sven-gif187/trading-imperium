"""
CHART-DATEN-LADER  -  Baustein 1 des Chart-Tabs
================================================
Holt historische Kerzendaten (OHLCV) von Binance fuer jeden Coin und
speichert sie lokal in data_store/charts/. So hast du den kompletten
Chartverlauf offline - fuer Anzeige, Indikatoren, Stop-Loss-Backtest
und zum Lernen.

- Binance /api/v3/klines ist oeffentlich, kein API-Key noetig.
- Max 1000 Kerzen pro Anfrage -> wird automatisch paginiert.
- Cache: laedt nur neue Kerzen nach, nicht jedes Mal alles.
- Reine Datensammlung, KEIN Trading-Eingriff.

Standalone testen (laedt echte Daten von Binance):
  python "C:\\...\\features\\chart_data.py"
"""
import os
import csv
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

BINANCE = "https://api.binance.com/api/v3/klines"
# Fallback-Host (oeffentliche Datendomain), falls der Haupt-Host zickt
BINANCE_ALT = "https://data-api.binance.vision/api/v3/klines"

# Millisekunden pro Intervall (fuer Pagination)
INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
    "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000,
    "1d": 86_400_000, "3d": 259_200_000, "1w": 604_800_000,
}


class ChartData:
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root = project_root
        self.dir = os.path.join(self.root, "data_store", "charts")
        os.makedirs(self.dir, exist_ok=True)

    # ---------- HTTP ----------
    def _fetch_chunk(self, symbol, interval, start_ms=None, end_ms=None, limit=1000):
        params = f"?symbol={symbol}&interval={interval}&limit={limit}"
        if start_ms is not None:
            params += f"&startTime={int(start_ms)}"
        if end_ms is not None:
            params += f"&endTime={int(end_ms)}"
        last_err = None
        for base in (BINANCE, BINANCE_ALT):
            try:
                req = urllib.request.Request(base + params,
                                             headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    return json.load(r)
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"Binance nicht erreichbar: {str(last_err)[:80]}")

    # ---------- Dateipfad ----------
    def _path(self, symbol, interval):
        safe = symbol.replace("/", "")
        return os.path.join(self.dir, f"{safe}_{interval}.csv")

    # ---------- Laden mit Cache ----------
    def load(self, symbol, interval="1h", days=90, progress=None):
        """Laedt Kerzen fuer symbol/interval, days Tage zurueck.
        Nutzt lokalen Cache und holt nur fehlende neue Kerzen nach.
        symbol: 'BTCUSDT' oder 'BTC/USDC' (wird normalisiert).
        Gibt Liste von Kerzen-Dicts zurueck."""
        sym = symbol.replace("/", "")
        if sym.endswith("USDC"):
            sym = sym[:-4] + "USDT"   # Binance hat fuer die meisten Coins USDT-Paare
        if interval not in INTERVAL_MS:
            raise ValueError("Ungueltiges Intervall: " + interval)

        path = self._path(sym, interval)
        existing = self._read_csv(path)
        now_ms = int(time.time() * 1000)
        want_start = now_ms - days * 86_400_000

        # Startpunkt bestimmen: ab letzter gecachter Kerze, sonst ab want_start
        if existing:
            start_ms = int(existing[-1]["open_time"]) + INTERVAL_MS[interval]
        else:
            start_ms = want_start

        new_rows = []
        cur = start_ms
        calls = 0
        fetch_failed = False
        while cur < now_ms:
            try:
                chunk = self._fetch_chunk(sym, interval, start_ms=cur, limit=1000)
            except Exception as e:
                # Binance nicht erreichbar: mit Cache weiterarbeiten statt crashen
                fetch_failed = True
                if progress:
                    progress(f"{sym}: Binance offline, nutze Cache ({str(e)[:40]})")
                break
            calls += 1
            if not chunk:
                break
            for k in chunk:
                new_rows.append({
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": int(k[6]),
                })
            cur = int(chunk[-1][0]) + INTERVAL_MS[interval]
            if progress:
                progress(f"{sym} {interval}: {len(existing)+len(new_rows)} Kerzen geladen...")
            if len(chunk) < 1000:
                break
            time.sleep(0.25)  # hoeflich zu Binance
            if calls > 60:     # Sicherheitslimit (~60k Kerzen)
                break

        all_rows = existing + new_rows
        # Auf gewuenschten Zeitraum kuerzen
        all_rows = [r for r in all_rows if r["open_time"] >= want_start]
        if new_rows:
            self._write_csv(path, all_rows)
        if not all_rows and fetch_failed:
            raise RuntimeError("Binance nicht erreichbar und kein Cache vorhanden")
        return all_rows

    # ---------- CSV I/O ----------
    def _read_csv(self, path):
        if not os.path.exists(path):
            return []
        rows = []
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rows.append({
                        "open_time": int(r["open_time"]),
                        "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"]),
                        "volume": float(r["volume"]), "close_time": int(r["close_time"]),
                    })
        except Exception:
            return []
        return rows

    def _write_csv(self, path, rows):
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["open_time", "open", "high", "low",
                                              "close", "volume", "close_time"])
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)

    # ---------- Mehrere Coins auf einmal ----------
    def load_all(self, symbols, interval="1h", days=90, progress=None):
        out = {}
        for s in symbols:
            try:
                out[s] = self.load(s, interval, days, progress)
            except Exception as e:
                if progress:
                    progress(f"{s}: FEHLER {str(e)[:60]}")
                out[s] = []
        return out

    def info(self):
        """Was liegt schon im Cache?"""
        files = [f for f in os.listdir(self.dir) if f.endswith(".csv")]
        result = []
        for f in sorted(files):
            p = os.path.join(self.dir, f)
            rows = self._read_csv(p)
            if rows:
                first = datetime.fromtimestamp(rows[0]["open_time"] / 1000, timezone.utc)
                last = datetime.fromtimestamp(rows[-1]["open_time"] / 1000, timezone.utc)
                result.append(f"{f}: {len(rows)} Kerzen, {first:%Y-%m-%d} bis {last:%Y-%m-%d}")
        return result


if __name__ == "__main__":
    cd = ChartData()
    # [20.08.2026] Die Liste wird nicht mehr hier wiederholt, sondern aus
    # dem Chart-Sammler geholt. Eine zweite Liste derselben Muenzen ist
    # eine zweite Gelegenheit, sie auseinanderlaufen zu lassen - genau das
    # war passiert: hier standen zwoelf, beobachtet werden achtzehn.
    try:
        from features.chart_refresher import COINS as coins
    except Exception:
        from chart_refresher import COINS as coins
    print(f"Lade Kerzendaten von Binance (1h, 90 Tage) fuer {len(coins)} Coins...\n")
    cd.load_all(coins, interval="1h", days=90, progress=lambda m: print("  " + m))
    print("\n=== Cache-Inhalt ===")
    for line in cd.info():
        print("  " + line)
    print("\nFertig. Daten liegen in data_store/charts/")
