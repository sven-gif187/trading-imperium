"""
Trading Imperium V5 – On-Chain Analytics Agent
Holt Glassnode-aehnliche Metriken kostenlos: SOPR, NVT, aktive Adressen.
Quellen: blockchain.info, blockchair.com (kostenlos)
"""
import time
import threading
from typing import Dict
from core.logger import log

try:
    import requests
except ImportError:
    requests = None


class OnChainAnalytics:
    """Holt On-Chain Metriken fuer BTC-Analyse."""

    BLOCKCHAIN_INFO = "https://blockchain.info"

    def __init__(self, cache_minutes=30):
        self.cache_minutes = cache_minutes
        self._cache = {}
        self._cache_time = 0
        self._lock = threading.Lock()

    def fetch_metrics(self) -> Dict:
        """Holt alle verfuegbaren On-Chain Metriken."""
        with self._lock:
            if self._cache and (time.time() - self._cache_time) < self.cache_minutes * 60:
                return self._cache

        metrics = {}
        if not requests:
            return metrics

        # 1. Hashrate
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/hashrate", timeout=10)
            if r.status_code == 200:
                metrics["hashrate"] = float(r.text)
        except Exception:
            pass

        # 2. Difficulty
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/getdifficulty", timeout=10)
            if r.status_code == 200:
                metrics["difficulty"] = float(r.text)
        except Exception:
            pass

        # 3. Unconfirmed TXs (Mempool-Groesse)
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/unconfirmedcount", timeout=10)
            if r.status_code == 200:
                metrics["mempool_txs"] = int(r.text)
        except Exception:
            pass

        # 4. Market Cap
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/marketcap", timeout=10)
            if r.status_code == 200:
                metrics["market_cap"] = float(r.text)
        except Exception:
            pass

        # 5. 24h Transaction Count
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/24hrtransactioncount", timeout=10)
            if r.status_code == 200:
                metrics["tx_count_24h"] = int(r.text)
        except Exception:
            pass

        # 6. Estimated BTC sent (24h)
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/24hrbtcsent", timeout=10)
            if r.status_code == 200:
                metrics["btc_sent_24h"] = float(r.text) / 1e8  # Satoshi -> BTC
        except Exception:
            pass

        # 7. Blocks mined today
        try:
            r = requests.get(f"{self.BLOCKCHAIN_INFO}/q/getblockcount", timeout=10)
            if r.status_code == 200:
                metrics["block_height"] = int(r.text)
        except Exception:
            pass

        # NVT berechnen (Network Value to Transactions)
        if metrics.get("market_cap") and metrics.get("btc_sent_24h"):
            daily_tx_value = metrics["btc_sent_24h"] * (metrics["market_cap"] / 21000000)
            if daily_tx_value > 0:
                metrics["nvt_ratio"] = round(metrics["market_cap"] / (daily_tx_value * 365), 2)

        if metrics:
            log.info("ONCHAIN", f"Metriken geladen: {len(metrics)} Datenpunkte")

        with self._lock:
            self._cache = metrics
            self._cache_time = time.time()
        return metrics

    def get_signal(self) -> Dict:
        """Berechnet ein On-Chain Signal (0-1)."""
        m = self.fetch_metrics()
        if not m:
            return {"score": 0.5, "label": "NEUTRAL", "details": "Keine Daten"}

        score = 0.5
        reasons = []

        # NVT: hoch = ueberbewertet, niedrig = unterbewertet
        nvt = m.get("nvt_ratio", 0)
        if nvt > 0:
            if nvt > 100:
                score -= 0.1; reasons.append(f"NVT hoch ({nvt:.0f}) = ueberbewertet")
            elif nvt < 30:
                score += 0.1; reasons.append(f"NVT niedrig ({nvt:.0f}) = unterbewertet")

        # Mempool: viel Aktivitaet = bullisch
        mempool = m.get("mempool_txs", 0)
        if mempool > 100000:
            score += 0.05; reasons.append(f"Mempool aktiv ({mempool:,})")
        elif mempool < 10000:
            score -= 0.05; reasons.append(f"Mempool ruhig ({mempool:,})")

        # TX Count: hohe Aktivitaet = bullisch
        txs = m.get("tx_count_24h", 0)
        if txs > 400000:
            score += 0.05; reasons.append(f"Hohe TX-Aktivitaet ({txs:,})")

        label = "BULLISH" if score > 0.6 else "BEARISH" if score < 0.4 else "NEUTRAL"
        return {"score": round(max(0, min(1, score)), 2), "label": label,
                "details": " | ".join(reasons) if reasons else "Normal",
                "metrics": m}

    def get_status(self):
        return {"cached": bool(self._cache), "metrics_count": len(self._cache),
                "cache_age_sec": int(time.time() - self._cache_time) if self._cache_time else -1}
