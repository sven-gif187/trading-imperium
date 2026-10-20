"""
Trading Imperium V5 – News Data
Holt Krypto-News von kostenlosen Quellen (kein API-Key noetig).
"""
import time
import json
import threading
from typing import Dict, List
from core.logger import log

try:
    import requests
except ImportError:
    requests = None


class NewsDataProvider:
    """Holt und cached Krypto-News von kostenlosen APIs."""

    SOURCES = {
        "cryptocompare": "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&sortOrder=latest",
        "coingecko_trending": "https://api.coingecko.com/api/v3/search/trending",
    }

    def __init__(self, cache_minutes=10):
        self.cache_minutes = cache_minutes
        self._cache = {}
        self._cache_time = 0
        self._lock = threading.Lock()

    def fetch(self) -> List[Dict]:
        """Holt aktuelle News. Cached fuer cache_minutes."""
        with self._lock:
            if self._cache and (time.time() - self._cache_time) < self.cache_minutes * 60:
                return self._cache.get("articles", [])

        articles = []

        # CryptoCompare News (kostenlos, kein Key)
        try:
            if requests:
                r = requests.get(self.SOURCES["cryptocompare"], timeout=10)
                if r.status_code == 200:
                    data = r.json().get("Data", [])
                    for item in data[:15]:
                        articles.append({
                            "title": item.get("title", ""),
                            "source": item.get("source", ""),
                            "url": item.get("url", ""),
                            "body": item.get("body", "")[:200],
                            "categories": item.get("categories", ""),
                            "time": item.get("published_on", 0),
                        })
                    log.info("NEWS", f"CryptoCompare: {len(articles)} Artikel")
        except Exception as e:
            log.warn("NEWS", f"CryptoCompare Fehler: {str(e)[:40]}")

        # CoinGecko Trending (kostenlos)
        try:
            if requests:
                r = requests.get(self.SOURCES["coingecko_trending"], timeout=10)
                if r.status_code == 200:
                    coins = r.json().get("coins", [])
                    trending = [c.get("item", {}).get("name", "") for c in coins[:5]]
                    if trending:
                        articles.append({
                            "title": f"Trending: {', '.join(trending)}",
                            "source": "CoinGecko",
                            "categories": "trending",
                            "time": int(time.time()),
                        })
        except Exception as e:
            log.warn("NEWS", f"CoinGecko Fehler: {str(e)[:40]}")

        with self._lock:
            self._cache = {"articles": articles, "count": len(articles)}
            self._cache_time = time.time()

        return articles

    def get_headlines(self, max_n=5) -> List[str]:
        """Gibt nur die Schlagzeilen zurueck."""
        articles = self.fetch()
        return [a["title"] for a in articles[:max_n] if a.get("title")]

    def search(self, keyword) -> List[Dict]:
        """Durchsucht gecachte News nach Keyword."""
        articles = self.fetch()
        keyword = keyword.lower()
        return [a for a in articles if keyword in a.get("title", "").lower()
                or keyword in a.get("body", "").lower()
                or keyword in a.get("categories", "").lower()]

    def get_status(self):
        return {"cached_articles": len(self._cache.get("articles", [])),
                "cache_age_sec": int(time.time() - self._cache_time) if self._cache_time else -1,
                "sources": list(self.SOURCES.keys())}
