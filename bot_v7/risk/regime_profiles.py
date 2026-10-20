"""
Trading Imperium V6 - Regime Risk Profiles
============================================================
Passt Stop-Loss, Trailing-Stop und Positionsgroesse automatisch
an die aktuelle Marktphase (Cycle + Regime) an.

Deine Config-Werte sind die BASIS. Diese werden mit Faktoren
multipliziert je nach Marktlage. Werte leicht anpassbar:
einfach die Zahlen in CYCLE_RISK / REGIME_MOD aendern.
"""

# Multiplikatoren pro Cycle-Phase auf die Basis-Werte (SL, Trail, Size)
CYCLE_RISK = {
    "ACCUMULATION":  {"sl": 1.10, "trail": 1.20, "size": 1.10},  # Boden, guenstig: mutiger
    "EUPHORIA":      {"sl": 0.80, "trail": 1.30, "size": 0.70},  # Blase: eng sichern, Gewinn laufen lassen, klein
    "DISTRIBUTION":  {"sl": 0.90, "trail": 1.00, "size": 0.80},  # Uebergang zum Baer: vorsichtig
    "EARLY_BEAR":    {"sl": 0.85, "trail": 0.85, "size": 0.75},  # Baer beginnt
    "MID_BEAR":      {"sl": 0.80, "trail": 0.80, "size": 0.70},  # Baer: eng, klein
    "DEEP_BEAR":     {"sl": 0.75, "trail": 0.80, "size": 0.65},  # tiefer Baer
    "CAPITULATION":  {"sl": 1.00, "trail": 0.90, "size": 0.90},  # Crash-Boden: DCA-Chance
    "UNKNOWN":       {"sl": 1.00, "trail": 1.00, "size": 1.00},  # Default: wie Config
}

# Regime-Modifikator (zusaetzlich zum Cycle)
REGIME_MOD = {
    "VOLATILE": {"sl": 0.85, "trail": 0.90, "size": 0.80},  # Volatil: vorsichtiger
    "TRENDING": {"sl": 1.05, "trail": 1.15, "size": 1.05},  # Trend: mehr Raum
    "RANGING":  {"sl": 1.00, "trail": 1.00, "size": 1.00},  # Seitwaerts: neutral
    "UNKNOWN":  {"sl": 1.00, "trail": 1.00, "size": 1.00},
}

# Sicherheits-Grenzen (damit Werte nie extrem werden)
SL_MIN, SL_MAX = 1.5, 6.0
TRAIL_MIN, TRAIL_MAX = 0.5, 4.0
SIZE_MIN, SIZE_MAX = 0.5, 1.5


def _match_key(value, table):
    """Robustes Matching: findet Key auch bei 'MarketRegime.RANGING' etc."""
    v = str(value).upper()
    for key in table:
        if key == v:
            return key
    for key in table:
        if key != "UNKNOWN" and key in v:
            return key
    return "UNKNOWN"


def get_adjusted_risk(cycle, regime, base_sl, base_trail, base_size_mult=1.0):
    """Gibt (sl_pct, trail_pct, size_mult) angepasst an die Marktphase zurueck."""
    ck = _match_key(cycle, CYCLE_RISK)
    rk = _match_key(regime, REGIME_MOD)
    c = CYCLE_RISK[ck]
    r = REGIME_MOD[rk]

    sl = base_sl * c["sl"] * r["sl"]
    trail = base_trail * c["trail"] * r["trail"]
    size = base_size_mult * c["size"] * r["size"]

    sl = max(SL_MIN, min(SL_MAX, sl))
    trail = max(TRAIL_MIN, min(TRAIL_MAX, trail))
    size = max(SIZE_MIN, min(SIZE_MAX, size))

    return round(sl, 2), round(trail, 2), round(size, 3)


def get_profile_name(cycle, regime):
    """Kurzer Text fuer Logging, z.B. 'MID_BEAR/RANGING'."""
    ck = _match_key(cycle, CYCLE_RISK)
    rk = _match_key(regime, REGIME_MOD)
    return f"{ck}/{rk}"
