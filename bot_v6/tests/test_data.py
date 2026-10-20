"""Tests fuer Data Cache, DataQuality, Sentiment."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_cache():
    from data.cache import DataCache
    c = DataCache(default_ttl=1)
    c.set("test_key", "hello")
    assert c.get("test_key") == "hello"
    assert c.get("nonexistent") is None
    time.sleep(1.2)
    assert c.get("test_key") is None  # Abgelaufen
    # Status
    s = c.get_status()
    assert s["hits"] >= 1
    assert s["misses"] >= 1
    print("✅ DataCache OK")

def test_data_quality():
    import pandas as pd
    import numpy as np
    from data.data_quality import DataQualityChecker
    dq = DataQualityChecker()
    # Gute Daten
    df = pd.DataFrame({
        "Open": np.random.uniform(100, 110, 60),
        "High": np.random.uniform(110, 120, 60),
        "Low": np.random.uniform(90, 100, 60),
        "Close": np.random.uniform(100, 110, 60),
        "Volume": np.random.uniform(1000, 5000, 60),
    })
    r = dq.check_ohlcv(df, "TEST")
    assert r["score"] > 50
    # Schlechte Daten
    bad = df.copy()
    bad.loc[0:5, "Close"] = np.nan
    bad.loc[10, "High"] = 50  # High < Low
    r2 = dq.check_ohlcv(bad, "BAD")
    assert r2["score"] < r["score"]
    assert len(r2["issues"]) > 0
    # Auto-Fix
    fixed, fixes = dq.auto_fix(bad)
    assert len(fixes) > 0
    assert fixed["Close"].isna().sum() == 0
    print("✅ DataQualityChecker OK")

def test_sentiment():
    from data.sentiment_data import SentimentProvider
    sp = SentimentProvider(cache_minutes=0)
    # Ohne Netzwerk: sollte Default zurueckgeben
    fng = sp.get_fear_greed()
    assert "value" in fng
    assert "label" in fng
    # Sentiment mit fake News
    articles = [
        {"title": "Bitcoin surge to new ATH bullish rally", "body": ""},
        {"title": "Crash dump bearish fear selling", "body": ""},
    ]
    sent = sp.get_market_sentiment(articles)
    assert "score" in sent
    assert "label" in sent
    assert sent["bull_keywords"] > 0
    assert sent["bear_keywords"] > 0
    print("✅ SentimentProvider OK")

if __name__ == "__main__":
    test_cache()
    test_data_quality()
    test_sentiment()
    print("\n🎯 Alle Data-Tests bestanden!")
