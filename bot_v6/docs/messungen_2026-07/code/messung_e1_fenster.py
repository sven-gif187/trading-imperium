# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Messskript zum Audit E1/E2/E5 vom 29./30.07.2026.
# Nicht archivieren - Beleg fuer die Live-Freigabe. Siehe ../README.md
"""Fenster-Sensitivitaet: V0 (Harness-Regeln) und V5n (Live-nahe Frequenz)
nur auf dem Zeitraum der Live-Messung (ca. Mai-Juli 2026)."""
import os
import sys
from datetime import datetime, timezone

def _finde_projekt():
    """Projektwurzel relativ zum Skriptort suchen (Marker: app.py).

    Ersetzt den frueher fest verdrahteten absoluten Pfad. Damit laeuft das
    Skript unabhaengig davon, wohin der Projektordner verschoben wird.
    """
    p = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isfile(os.path.join(p, "app.py")):
            return p
        p = os.path.dirname(p)
    raise RuntimeError("Projektwurzel nicht gefunden - app.py in keiner "
                       "uebergeordneten Ebene")


PROJEKT = _finde_projekt()
if PROJEKT not in sys.path:
    sys.path.insert(0, PROJEKT)
from backtest.ausstieg_backtest import NEUE_LEITER, Lauf, lade_kerzen, lade_fear_greed
from messung_e1_nachkaufrate import LaufInstr, COINS, rate

def ms(s):
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)

for von_s in ("2026-05-01", "2026-04-01"):
    von = ms(von_s)
    d = {}
    for c in COINS:
        k = [x for x in lade_kerzen(c) if x[0] >= von]
        if k:
            d[c] = k
    fg = lade_fear_greed()

    v0 = LaufInstr(NEUE_LEITER, "v0", breakeven=True, max_stufen=3)
    v0.laufe(d, fg)
    n, nk, r = rate(v0)
    print(f"Fenster ab {von_s}:  V0  Harness-Regeln:      Trades={n:4d}  NK={nk:3d}  Rate={r:5.1f}%")

    v5n = LaufInstr(NEUE_LEITER, "v5n", breakeven=True, max_stufen=3,
                    nk_frei=True, neue_je_kerze=2, nk_intrabar=True)
    v5n.laufe(d, fg)
    n, nk, r = rate(v5n)
    print(f"Fenster ab {von_s}:  V5n Live-nahe Frequenz:  Trades={n:4d}  NK={nk:3d}  Rate={r:5.1f}%")
