"""Bottom Detection - Multi-Indikator Markt-Boden-Erkennung."""
import time
from typing import Dict, Optional
from core.logger import log


class BottomDetector:
    """Erkennt Markt-Boeden ueber mehrere Indikatoren."""

    def __init__(self, config=None):
        self.config = config
        self.last_check_time = 0
        self.last_result: Optional[Dict] = None
        self.is_bottom = False
        self.bottom_since: Optional[float] = None

        self.fg_extreme_threshold = 20
        self.rsi_oversold_threshold = 30
        self.bottom_cycle_phases = {"DEEP_BEAR", "CAPITULATION"}
        self.min_indicators_for_bottom = 2

    def evaluate(self, fear_greed=50, cycle_phase="UNKNOWN",
                 btc_rsi_daily=None, mvrv=None, sopr=None):
        score = 0
        indicators = {}
        reasons = []

        if fear_greed < self.fg_extreme_threshold:
            score += 1
            indicators["fear_greed"] = True
            reasons.append(f"F&G extreme Fear ({fear_greed})")
        else:
            indicators["fear_greed"] = False

        phase_str = str(cycle_phase).upper()
        if phase_str in self.bottom_cycle_phases:
            score += 1
            indicators["cycle_phase"] = True
            reasons.append(f"Cycle {phase_str}")
        else:
            indicators["cycle_phase"] = False

        if btc_rsi_daily is not None and btc_rsi_daily < self.rsi_oversold_threshold:
            score += 1
            indicators["btc_rsi"] = True
            reasons.append(f"BTC RSI {btc_rsi_daily:.0f} oversold")
        else:
            indicators["btc_rsi"] = False

        if mvrv is not None and mvrv < 1.0:
            score += 1
            indicators["mvrv"] = True
            reasons.append(f"MVRV {mvrv:.2f} unterbewertet")
        if sopr is not None and sopr < 1.0:
            score += 1
            indicators["sopr"] = True
            reasons.append(f"SOPR {sopr:.2f} (Verluste)")

        is_bottom = score >= self.min_indicators_for_bottom

        if is_bottom and not self.is_bottom:
            self.bottom_since = time.time()
            log.info("BOTTOM", f"Bottom-Signal AKTIV: {score} Indikatoren - "
                               f"{', '.join(reasons)}")
        elif not is_bottom and self.is_bottom:
            duration_min = (time.time() - (self.bottom_since or time.time())) / 60
            log.info("BOTTOM", f"Bottom-Signal beendet nach {duration_min:.0f} Minuten")
            self.bottom_since = None

        self.is_bottom = is_bottom
        result = {
            "is_bottom": is_bottom,
            "score": score,
            "indicators": indicators,
            "reason": " + ".join(reasons) if reasons else "Keine Bottom-Indikatoren",
        }
        self.last_check_time = time.time()
        self.last_result = result
        return result

    def get_status(self):
        return {
            "is_bottom": self.is_bottom,
            "last_check": self.last_check_time,
            "last_result": self.last_result,
            "bottom_since": self.bottom_since,
        }
