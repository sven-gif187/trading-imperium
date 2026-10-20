# regime_filter.py
# Tor vor NEUEN Kaeufen bei bestaetigtem Abwaertstrend.
# Reine Logik - blockt nur neue BUYs, fasst KEINE offene Position an.
# Schwellen stehen in config_regime_filter.json (live editierbar, wird gecacht).
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(HERE, "config_regime_filter.json")

DEFAULT_CFG = {
    "enabled": True,
    "min_confirmations": 2,
    "signals": {"below_ema": True, "mtf_bearish": True, "regime_bear": True, "cycle_bear": True},
    "diag": False,
}
BEAR_REGIME = ("TRENDING_DOWN", "DOWNTREND", "TREND_DOWN")
BEAR_CYCLE = ("EARLY_BEAR", "MID_BEAR", "DEEP_BEAR")

_CACHE = {"cfg": None, "mtime": None}

def _load_cfg():
    try:
        m = os.path.getmtime(CFG_FILE)
        if _CACHE["cfg"] is None or m != _CACHE["mtime"]:
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                _CACHE["cfg"] = json.load(f)
            _CACHE["mtime"] = m
    except Exception:
        _CACHE["cfg"] = dict(DEFAULT_CFG)
    return _CACHE["cfg"]

def _f(x):
    try:
        return float(x)
    except Exception:
        return 0.0

def evaluate(regime, cycle, mtf_direction, indicators, price):
    # Liefert (block_bool, reason_text, confirmations_list).
    cfg = _load_cfg()
    if not cfg.get("enabled", True):
        return False, "Filter aus", []
    sig = cfg.get("signals", {})
    indicators = indicators or {}
    conf = []

    # 1) Struktur: Kurs unter den Trend-EMAs
    if sig.get("below_ema", True):
        ema20 = _f(indicators.get("ema20"))
        ema50 = _f(indicators.get("ema50"))
        p = _f(price)
        if ema20 > 0 and ema50 > 0 and p > 0 and p < ema50 and ema20 < ema50:
            conf.append("Kurs<EMA50")

    # 2) Multi-Timeframe bearish
    if sig.get("mtf_bearish", True):
        if str(mtf_direction).upper() == "BEARISH":
            conf.append("MTF-bearish")

    # 3) Regime: kurzfristiger Abwaertstrend (eigene Bestaetigung)
    # 4) Cycle:  langfristiger Baerenmarkt   (eigene Bestaetigung)
    r = str(regime).upper()
    c = str(cycle).upper()
    if sig.get("regime_bear", True) and any(k in r for k in BEAR_REGIME):
        conf.append("Regime-Abwaerts")
    if sig.get("cycle_bear", True) and any(k in c for k in BEAR_CYCLE):
        conf.append("Cycle-Baer")

    need = int(cfg.get("min_confirmations", 2))
    block = len(conf) >= need
    inside = ", ".join(conf) if conf else "keine"
    reason = "%d/%d Bestaetigungen [%s]" % (len(conf), need, inside)
    return block, reason, conf

def should_block_buy(regime, cycle, mtf_direction, indicators, price):
    # Bequemer Wrapper fuer app.py: (block, reason).
    block, reason, _ = evaluate(regime, cycle, mtf_direction, indicators, price)
    return block, reason


def diag_enabled():
    # True -> app.py loggt pro Kauf-Check die Filter-Eingaben (Diagnose).
    return bool(_load_cfg().get("diag", False))
