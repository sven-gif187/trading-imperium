# -*- coding: utf-8 -*-
"""
Zentrale Per-Coin-Stop-Tabelle - EINE Wahrheit fuer ALLE Exit-Pfade.
Eingefuehrt mit E6-B (ADA 3.0%), vervollstaendigt am 14.07.2026.
Regel: Override kann den Stop nur LOCKERN (nie enger als Basis).
"""

COIN_SL_MIN = {
    "ADA/USDC": 3.0,   # E6-B: ADA braucht weiteren Stop (Basis-Volatilitaet)
}


def effective_stop(symbol, base_stop_pct):
    """Effektiver Stop fuer ein Symbol: max(Basis, Per-Coin-Override)."""
    try:
        o = COIN_SL_MIN.get(symbol)
        if o is not None and float(o) > float(base_stop_pct):
            return float(o)
    except Exception:
        pass
    return base_stop_pct
