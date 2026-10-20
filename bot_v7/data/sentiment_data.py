"""
Trading Imperium V5 – Sentiment Data
Fear & Greed Index, Social Sentiment, Markt-Stimmung.
"""
import time
import threading
from typing import Dict
from core.logger import log

try:
    import requests
except ImportError:
    requests = None


class SentimentProvider:
    """Holt Sentiment-Daten von kostenlosen APIs."""

    FNG_URL = "https://api.alternative.me/fng/?limit=7"

    def __init__(self, cache_minutes=30):
        self.cache_minutes = cache_minutes
        self._fng_cache = None
        self._fng_time = 0
        self._lock = threading.Lock()

    def get_fear_greed(self) -> Dict:
        """Holt den Fear & Greed Index (0-100). Cached."""
        with self._lock:
            if self._fng_cache and (time.time() - self._fng_time) < self.cache_minutes * 60:
                return self._fng_cache

        result = {"value": 50, "label": "Neutral", "history": []}

        try:
            if requests:
                r = requests.get(self.FNG_URL, timeout=10)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if data:
                        current = data[0]
                        result["value"] = int(current.get("value", 50))
                        result["label"] = current.get("value_classification", "Neutral")
                        result["timestamp"] = current.get("timestamp", "")
                        result["history"] = [
                            {"value": int(d.get("value", 50)), "label": d.get("value_classification", "")}
                            for d in data[:7]
                        ]
                    log.info("SENTIMENT", f"F&G: {result['value']} ({result['label']})")
        except Exception as e:
            log.warn("SENTIMENT", f"F&G Fehler: {str(e)[:40]}")

        with self._lock:
            self._fng_cache = result
            self._fng_time = time.time()

        return result

    def get_market_sentiment(self, news_articles=None) -> Dict:
        """Berechnet Gesamt-Sentiment aus News und F&G."""
        fng = self.get_fear_greed()
        fng_val = fng.get("value", 50)

        # F&G Score normalisieren auf 0.0-1.0
        fng_score = fng_val / 100

        # News-Sentiment (einfache Keyword-Analyse)
        news_score = 0.5
        if news_articles:
            bull_words = ["rally", "surge", "bullish", "ath", "high", "gain", "pump", "breakout", "adoption"]
            bear_words = ["crash", "dump", "bearish", "fear", "sell", "drop", "ban", "hack", "scam", "fraud"]
            bull_count = 0
            bear_count = 0
            for article in news_articles:
                text = (article.get("title", "") + " " + article.get("body", "")).lower()
                bull_count += sum(1 for w in bull_words if w in text)
                bear_count += sum(1 for w in bear_words if w in text)
            total = bull_count + bear_count
            if total > 0:
                news_score = bull_count / total

        # Gewichtetes Gesamt-Sentiment
        combined = fng_score * 0.6 + news_score * 0.4
        if combined > 0.65:
            label = "BULLISH"
        elif combined > 0.45:
            label = "NEUTRAL"
        else:
            label = "BEARISH"

        return {
            "score": round(combined, 2),
            "label": label,
            "fear_greed": fng,
            "news_score": round(news_score, 2),
            "bull_keywords": bull_count if news_articles else 0,
            "bear_keywords": bear_count if news_articles else 0,
        }

    def is_extreme_fear(self) -> bool:
        """Ist der Markt in extremer Angst? (F&G < 20)"""
        fng = self.get_fear_greed()
        return fng.get("value", 50) < 20

    def is_extreme_greed(self) -> bool:
        """Ist der Markt in extremer Gier? (F&G > 80)"""
        fng = self.get_fear_greed()
        return fng.get("value", 50) > 80

    def get_status(self):
        fng = self._fng_cache or {}
        return {"fear_greed": fng.get("value", "?"), "label": fng.get("label", "?"),
                "cache_age": int(time.time() - self._fng_time) if self._fng_time else -1}
