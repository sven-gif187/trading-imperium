"""
Trading Imperium V5 – Reddit Sentiment
Analysiert r/CryptoCurrency und r/Bitcoin Stimmung.
Nutzt PRAW (Python Reddit API Wrapper) oder kostenlose JSON-API als Fallback.
"""
import time
import threading
import json
from typing import Dict, List
from core.logger import log

try:
    import requests
except ImportError:
    requests = None

try:
    import praw
    HAS_PRAW = True
except ImportError:
    HAS_PRAW = False


# Sentiment-Keywords
BULL_WORDS = [
    "moon", "bullish", "pump", "buy", "hodl", "hold", "long", "ath",
    "breakout", "rally", "surge", "accumulate", "dip", "cheap", "undervalued",
    "adoption", "institutional", "etf", "halving", "green", "gains",
    "lambo", "diamond hands", "wagmi", "lfg", "send it",
]
BEAR_WORDS = [
    "crash", "dump", "bearish", "sell", "short", "scam", "rug",
    "fear", "panic", "dead", "bubble", "overvalued", "hack", "ban",
    "regulation", "sec", "lawsuit", "ponzi", "fraud", "exit",
    "capitulation", "bloodbath", "rekt", "ngmi", "paper hands",
]


class RedditSentimentProvider:
    """Analysiert Reddit Crypto-Stimmung.

    ============================================================
    STILLGELEGT SEIT 29.07.2026 - BEWUSST, NICHT VERGESSEN
    ============================================================
    Entscheidung des Eigentuemers am 12.08.2026: stilllegen, Code behalten.

    WAS PASSIERT IST: Reddit liefert seit dem 29.07. auf jede Anfrage
    Status 403. Am 12.08. nachgeprueft - der Zugang laesst sich NICHT
    durch einen Kniff wiederherstellen: auch mit Browser-Kennung
    (Mozilla/5.0 statt TradingImperium/1.0) kommt 403. Reddit hat den
    unangemeldeten Zugriff auf die JSON-Schnittstelle dichtgemacht. Die
    Zeile "kein Account noetig" unten stimmt seither nicht mehr.

    WARUM NICHT REPARIERT: Zwei Gruende, beide gemessen statt vermutet.
      1. Es ist heute nichts kaputt. data/source_health.py erkennt die
         tote Quelle (posts == 0) und nimmt sie aus der Gewichtung. Ihre
         5 % verteilen sich automatisch auf die lebenden Quellen -
         nachgerechnet: technical 41,1 % -> 44,1 %, fear_greed 20,5 % ->
         22,1 % usw. Der Ensemble-Wert aendert sich um 0,005.
      2. Ob Reddit je etwas genuetzt hat, weiss niemand. Im Mess-Audit
         (docs/messungen_2026-07/BEFUNDE.md, Befund 28) steht Reddit
         unter den 13 Merkmalen, die als NICHT ENTSCHEIDBAR gelten - nicht
         "kein Effekt", sondern nie pruefbar, weil die Werte nur live
         vorlagen und nie archiviert wurden. Eine Quelle mit unbekanntem
         Nutzen zu reparieren waere Aufwand ins Blaue.

    WIE MAN SIE ZURUECKHOLT (falls je gewuenscht): Der praw-Pfad unten
    ist fertig gebaut und braucht nur Zugangsdaten.
      1. Auf reddit.com/prefs/apps eine App vom Typ "script" anlegen.
      2. client_id und client_secret in die .env eintragen.
      3. Beim Bauen des Providers uebergeben - dann laeuft _fetch_praw()
         statt der offenen JSON-Schnittstelle.
    Danach mindestens vier Wochen im Notizbuch messen, BEVOR die Quelle
    wieder Gewicht bekommt. Seit dem 11.08. archiviert die Zeitreihe
    (Tabelle markt_historie) alle Quellenwerte - damit waere Reddit
    erstmals ueberhaupt bewertbar.

    NICHT LOESCHEN: Die Klasse bleibt liegen, damit der Weg zurueck offen
    ist und niemand die Arbeit neu macht.
    """

    SUBREDDITS = ["CryptoCurrency", "Bitcoin", "ethereum", "solana"]
    # Kostenlose Reddit JSON API - liefert seit 29.07.2026 nur noch 403,
    # siehe Klassen-Kommentar. Ohne Anmeldung geht hier nichts mehr.
    REDDIT_JSON_URL = "https://www.reddit.com/r/{sub}/hot.json?limit=25"

    def __init__(self, client_id="", client_secret="", user_agent="TradingImperium/1.0",
                 cache_minutes=30):
        self.cache_minutes = cache_minutes
        self._cache = {}
        self._cache_time = 0
        self._lock = threading.Lock()
        self.praw_client = None

        # PRAW Setup (optional)
        if HAS_PRAW and client_id and client_secret:
            try:
                self.praw_client = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                )
                log.info("REDDIT", "PRAW Client verbunden")
            except Exception as e:
                log.warn("REDDIT", f"PRAW Setup fehlgeschlagen: {e}")
        else:
            log.info("REDDIT", "Nutze kostenlose JSON-API (kein PRAW)")

    def fetch_posts(self, subreddit="CryptoCurrency", limit=25) -> List[Dict]:
        """Holt Posts von einem Subreddit."""
        if self.praw_client:
            return self._fetch_praw(subreddit, limit)
        return self._fetch_json(subreddit, limit)

    def _fetch_praw(self, subreddit, limit) -> List[Dict]:
        """Holt Posts ueber PRAW (bessere Qualitaet, braucht API-Key)."""
        posts = []
        try:
            sub = self.praw_client.subreddit(subreddit)
            for post in sub.hot(limit=limit):
                posts.append({
                    "title": post.title,
                    "score": post.score,
                    "upvote_ratio": post.upvote_ratio,
                    "num_comments": post.num_comments,
                    "created": post.created_utc,
                    "flair": str(post.link_flair_text or ""),
                    "subreddit": subreddit,
                })
        except Exception as e:
            log.warn("REDDIT", f"PRAW {subreddit}: {str(e)[:40]}")
        return posts

    def _fetch_json(self, subreddit, limit) -> List[Dict]:
        """Holt Posts ueber kostenlose JSON-API (kein Account noetig)."""
        posts = []
        if not requests:
            return posts
        try:
            url = self.REDDIT_JSON_URL.format(sub=subreddit)
            headers = {"User-Agent": "TradingImperium/1.0"}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                children = data.get("data", {}).get("children", [])
                for child in children[:limit]:
                    p = child.get("data", {})
                    posts.append({
                        "title": p.get("title", ""),
                        "score": p.get("score", 0),
                        "upvote_ratio": p.get("upvote_ratio", 0.5),
                        "num_comments": p.get("num_comments", 0),
                        "created": p.get("created_utc", 0),
                        "flair": p.get("link_flair_text", ""),
                        "subreddit": subreddit,
                    })
            elif r.status_code == 429:
                log.warn("REDDIT", f"Rate-Limit auf r/{subreddit}")
            else:
                log.warn("REDDIT", f"r/{subreddit}: Status {r.status_code}")
        except Exception as e:
            log.warn("REDDIT", f"JSON {subreddit}: {str(e)[:40]}")
        return posts

    def analyze_sentiment(self) -> Dict:
        """
        Analysiert Gesamt-Sentiment aus allen Subreddits.
        Returns: {"score": 0-1, "label": str, "details": str}
        """
        with self._lock:
            if self._cache and (time.time() - self._cache_time) < self.cache_minutes * 60:
                return self._cache

        all_posts = []
        for sub in self.SUBREDDITS:
            posts = self.fetch_posts(sub, limit=25)
            all_posts.extend(posts)
            time.sleep(1)  # Rate-Limit respektieren

        if not all_posts:
            result = {"score": 0.5, "label": "NEUTRAL", "posts": 0,
                      "details": "Keine Reddit-Daten"}
            with self._lock:
                self._cache = result
                self._cache_time = time.time()
            return result

        # Sentiment berechnen
        bull_count = 0
        bear_count = 0
        total_weight = 0

        for post in all_posts:
            title = post.get("title", "").lower()
            score = max(post.get("score", 1), 1)
            weight = min(score / 100, 5)  # Gewichtung nach Upvotes, max 5x

            post_bull = sum(1 for w in BULL_WORDS if w in title)
            post_bear = sum(1 for w in BEAR_WORDS if w in title)

            bull_count += post_bull * weight
            bear_count += post_bear * weight
            total_weight += weight

        # Score berechnen
        total = bull_count + bear_count
        if total > 0:
            sentiment_score = bull_count / total
        else:
            sentiment_score = 0.5

        # Label
        if sentiment_score > 0.65:
            label = "BULLISH"
        elif sentiment_score > 0.55:
            label = "LEICHT_BULLISH"
        elif sentiment_score < 0.35:
            label = "BEARISH"
        elif sentiment_score < 0.45:
            label = "LEICHT_BEARISH"
        else:
            label = "NEUTRAL"

        result = {
            "score": round(sentiment_score, 2),
            "label": label,
            "posts": len(all_posts),
            "bull_signals": round(bull_count, 1),
            "bear_signals": round(bear_count, 1),
            "subreddits": len(self.SUBREDDITS),
            "details": f"{len(all_posts)} Posts analysiert: {bull_count:.0f} bull / {bear_count:.0f} bear → {label}",
        }

        log.info("REDDIT", result["details"])

        with self._lock:
            self._cache = result
            self._cache_time = time.time()

        return result

    def get_trending_coins(self) -> List[str]:
        """Welche Coins werden am meisten auf Reddit erwaehnt?"""
        coin_mentions = {}
        coin_names = {
            "bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH",
            "solana": "SOL", "sol": "SOL", "xrp": "XRP", "ripple": "XRP",
            "cardano": "ADA", "ada": "ADA", "avalanche": "AVAX", "avax": "AVAX",
            "dogecoin": "DOGE", "doge": "DOGE", "polkadot": "DOT", "dot": "DOT",
            "chainlink": "LINK", "link": "LINK", "near": "NEAR",
        }

        all_posts = []
        for sub in self.SUBREDDITS[:2]:  # Nur die 2 groessten
            all_posts.extend(self.fetch_posts(sub, 25))
            time.sleep(1)

        for post in all_posts:
            title = post.get("title", "").lower()
            for keyword, symbol in coin_names.items():
                if keyword in title:
                    coin_mentions[symbol] = coin_mentions.get(symbol, 0) + 1

        sorted_coins = sorted(coin_mentions.items(), key=lambda x: x[1], reverse=True)
        return [c[0] for c in sorted_coins[:10]]

    def get_status(self):
        return {
            "has_praw": self.praw_client is not None,
            "cached": bool(self._cache),
            "cache_age_sec": int(time.time() - self._cache_time) if self._cache_time else -1,
            "last_score": self._cache.get("score", "?"),
            "last_label": self._cache.get("label", "?"),
        }
