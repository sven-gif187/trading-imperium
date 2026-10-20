# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH V1 (A5) - Nachzieh-Start aus dem WIRKSAMEN Abstand (v6 E11, v7 L10). Entscheidung Sven 14.10.2026 (Z4).

BEFUND A5 (berichte/2026-10-14_ausstieg.md): Der Nachzieh-Abstand im Bot ist nicht 1,0 %, sondern
Config x Regime (EARLY_BEAR 0,85) x Leiter-Stufe x Trend-Bonus (1,3 bei TRENDING_UP). In E7 loesten
40 von 61 Nachzieh-Stopps bei 0,85 % aus, 9 bei 1,274 %. Der Start TRAIL_AB_PCT (heute 1,21) war aber
fest fuer 1,0 % gerechnet - im Aufwaertstrend endet ein Ausstieg zwischen 1,21 und ~1,5 % nach Kosten im Minus.

AENDERUNG (eine, in risk/exit_rules.py effektiver_trail()):
  Start = (1 + K/100) / (1 - Abstand/100) - 1  + 0,05   mit Abstand = trail_pct x Leiter x Trend-Bonus
  (K = K_BASIS_PCT der Datei, heute 0,150). Beispiele: EARLY_BEAR 0,85 -> 1,06 | normal 1,0 -> 1,21 |
  TRENDING_UP 1,3 -> 1,52. TRAIL_AB_PCT bleibt als Richtwert (1,0 %) stehen; wird trail_ab_pct
  ausdruecklich uebergeben, gilt er wie bisher.
Aufruf: python patch_v1_trailstart_wirksam.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "V1 TRAILSTART WIRKSAM 14.10.2026"
ALT_SIG = ('def effektiver_trail(hoechst_pnl_pct, trail_pct, regime="",\n'
           '                     trail_ab_pct=TRAIL_AB_PCT, trend_bonus=TREND_BONUS):\n')
NEU_SIG = (
    f"# [{MARKE}] Marge ueber der Nulllinie, wie Patch 45.\n"
    "TRAIL_MARGE_PCT = 0.05\n"
    "\n"
    "\n"
    "def trail_start_pct(abstand_pct, k_pct=None, marge_pct=TRAIL_MARGE_PCT):\n"
    f"    \"\"\"[{MARKE}] Ab welchem Hoch verdient ein Nachzieh-Stopp mit diesem Abstand?\n"
    "\n"
    "    Nulllinie = (1 + K) / (1 - Abstand) - 1, dazu die Marge. K = Kosten je Runde\n"
    "    (K_BASIS_PCT). Abstand = der WIRKSAME Abstand nach Regime, Leiter und Trend-Bonus.\n"
    "    \"\"\"\n"
    "    k = K_BASIS_PCT if k_pct is None else k_pct\n"
    "    return round(((1 + k / 100.0) / (1 - abstand_pct / 100.0) - 1) * 100.0 + marge_pct, 3)\n"
    "\n"
    "\n"
    'def effektiver_trail(hoechst_pnl_pct, trail_pct, regime="",\n'
    "                     trail_ab_pct=None, trend_bonus=TREND_BONUS):\n")
ALT_KOERPER = (
    "    if hoch < trail_ab_pct or trail_pct <= 0:\n"
    "        return 0.0\n"
    "    faktor = LEITER[0][1]\n"
    "    for schwelle, f in LEITER:\n"
    "        if hoch >= schwelle:\n"
    "            faktor = f\n"
    '    if "TRENDING_UP" in str(regime).upper():\n'
    "        faktor *= trend_bonus\n"
    "    return round(trail_pct * faktor, 3)\n")
NEU_KOERPER = (
    "    if trail_pct <= 0:\n"
    "        return 0.0\n"
    "    faktor = LEITER[0][1]\n"
    "    for schwelle, f in LEITER:\n"
    "        if hoch >= schwelle:\n"
    "            faktor = f\n"
    '    if "TRENDING_UP" in str(regime).upper():\n'
    "        faktor *= trend_bonus\n"
    "    abstand = trail_pct * faktor\n"
    f"    # [{MARKE}] Start aus dem wirksamen Abstand statt fest TRAIL_AB_PCT\n"
    "    # (Entscheidung Sven, A5-Vorschlag V1). Vorher: if hoch < TRAIL_AB_PCT.\n"
    "    start = trail_ab_pct if trail_ab_pct is not None else trail_start_pct(abstand)\n"
    "    if hoch < start:\n"
    "        return 0.0\n"
    "    return round(abstand, 3)\n")
ERS = [Ersetzung("risk/exit_rules.py", ALT_SIG, NEU_SIG), Ersetzung("risk/exit_rules.py", ALT_KOERPER, NEU_KOERPER)]


def funktionstest(ordner: Path) -> int:
    import importlib.util
    import shutil
    import tempfile
    from _patchwerkzeug import anwenden
    with tempfile.TemporaryDirectory() as t:
        k = Path(t)
        (k / "risk").mkdir()
        shutil.copy2(ordner / "risk" / "exit_rules.py", k / "risk" / "exit_rules.py")
        anwenden(k, ERS, MARKE, trocken_kopie=True)
        spec = importlib.util.spec_from_file_location("er", k / "risk" / "exit_rules.py")
        er = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(er)
        f = er.effektiver_trail
        faelle = [  # (hoch, trail_pct, regime, erwartet, text)
            (1.10, 0.85, "", 0.85, "EARLY_BEAR 0,85: aktiv ab 1,06 -> bei Hoch 1,10 aktiv"),
            (1.00, 0.85, "", 0.0, "EARLY_BEAR 0,85: Hoch 1,00 < 1,06 -> nicht aktiv"),
            (1.15, 1.00, "", 0.0, "normal 1,0: Hoch 1,15 < 1,21 -> nicht aktiv"),
            (1.25, 1.00, "", 1.0, "normal 1,0: Hoch 1,25 -> aktiv mit 1,0"),
            (1.40, 1.00, "TRENDING_UP", 0.0, "Trend 1,3: Hoch 1,40 < 1,52 -> NICHT aktiv (vorher aktiv)"),
            (1.60, 1.00, "TRENDING_UP", 1.3, "Trend 1,3: Hoch 1,60 -> aktiv mit 1,3"),
            (3.50, 1.00, "", 1.3, "Leiter 3 %: Faktor 1,3"),
        ]
        fehler = 0
        print(f"  K_BASIS_PCT in der Datei: {er.K_BASIS_PCT} | Start bei 0,85/1,0/1,3: "
              f"{er.trail_start_pct(0.85)} / {er.trail_start_pct(1.0)} / {er.trail_start_pct(1.3)}")
        for hoch, tp, reg, soll, text in faelle:
            ist = f(hoch, tp, reg)
            ok = abs(ist - soll) < 1e-9
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} {text}: {ist}")
        ok = f(1.30, 1.0, "", trail_ab_pct=1.57) == 0.0
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} ausdruecklich uebergebenes trail_ab_pct=1.57 gilt weiter")
        # Nachrechnung: Ausstieg am Start-Hoch minus Abstand muss netto >= 0 sein
        for d in (0.85, 1.0, 1.3, 1.105):
            s = er.trail_start_pct(d)
            netto = ((1 + s / 100) * (1 - d / 100) - 1) * 100 - er.K_BASIS_PCT
            ok = netto >= 0
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} Abstand {d}: Start {s} -> Ausstieg netto {netto:+.3f} % (>= 0)")
    return 1 if fehler else 0


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    pfad = Path(json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]["pfad"])
    main(pfad, ERS, MARKE, f"PATCH V1 Nachzieh-Start wirksam {name}", zusatztest=lambda: funktionstest(pfad))
