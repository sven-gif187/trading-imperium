# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH Kostenlatte Bitvavo USDC (v6 Epoche E10, v7 Epoche L9) - Entscheidung Sven 14.10.2026 (Z1).

EINE Ursache: die Zielboerse wechselt von Bybit EU (0,25 % je Seite) zu Bitvavo
USDC-Maerkten (0,05 % je Seite, bitvavo.com/en/fees Kategorie B, geprueft 14.10.).
Alles, was daraus folgt, wird in einem Schritt umgestellt:
  - Gebuehrentabelle: neuer Eintrag "bitvavo_usdc"
  - Papier-Gebuehr: PAPER_GEBUEHR_BOERSE = "bitvavo_usdc"
  - Papier-Schlupf: SPREAD_BP fuer BTC/ETH/SOL aus der Bitvavo-Stichprobe
    (berichte/2026-10-14_spanne_bitvavo.json) statt Bybit-Messung 31.07.
  - Kostenlatte K = 0,10 Gebuehr + Schlupf (2 x halbe Spanne, Mittel BTC/ETH/SOL),
    gerundet auf 0,15 -> Nullsicherung-Puffer 0,195 (K + 0,045, Formel bleibt),
    Nachzieh-Start 1,21 ((1+K)/(1-1 %) - 1 + 0,05)
  - v6: Regime-Lerner und Schatten-Ausstiege von 0,32 auf K (v7 zieht ueber core/kosten.py mit)
  - config_zielgroessen.json kosten_je_runde_pct
Vorab-Registrierung: pruefstand/epochen/E10_L9_kostenlatte_bitvavo.md
Aufruf: python patch_kostenlatte_bitvavo.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "KOSTENLATTE BITVAVO 14.10.2026"
STICHPROBE = HIER.parent / "berichte" / "2026-10-14_spanne_bitvavo.json"
K = 0.15            # Gebuehr 0,10 + Schlupf (aus der Stichprobe, siehe schlupf_runde unten)
TRAIL = 1.0
TRAIL_AB = round(((1 + K / 100) / (1 - TRAIL / 100) - 1) * 100 + 0.05, 2)   # 1,21

sp = json.loads(STICHPROBE.read_text(encoding="utf-8"))
ERG = sp["ergebnis"]
MED = {s.split("/")[0]: ERG[s]["median_bp"] for s in ERG}
P90 = {s.split("/")[0]: ERG[s]["p90_bp"] for s in ERG}
schlupf_runde = sum(MED.values()) / len(MED) / 100      # 2 x halbe Spanne in %, Mittel
QUELLE = f"Bitvavo-Stichprobe {sp['start_utc'][:16]} UTC, {ERG['BTC/USDC']['proben']} Proben je Muenze"


def ersetzungen(name: str) -> list:
    e = []
    # 1 Gebuehrentabelle
    okx = '    "okx":        {"maker": 0.08, "taker": 0.10},\n'
    e.append(Ersetzung("backtest/fees.py", okx,
        f"    # [{MARKE}] Bitvavo USDC-Maerkte, Kategorie B: 0,05 % Maker und Taker\n"
        "    # (bitvavo.com/en/fees, geprueft 14.10.2026). Zielboerse seit Entscheidung Sven 14.10.\n"
        '    "bitvavo_usdc": {"maker": 0.05, "taker": 0.05},\n' + okx))
    # 2 Papier-Gebuehr
    e.append(Ersetzung("execution/engine.py", '    PAPER_GEBUEHR_BOERSE = "bybit"\n',
        f"    # [{MARKE}] Zielboerse Bitvavo USDC (0,05 % je Seite). Vorher \"bybit\" (0,25 %).\n"
        '    PAPER_GEBUEHR_BOERSE = "bitvavo_usdc"\n'))
    # 3 Papier-Schlupf
    alt_spread = ('        "ETH":  (0.054,  5.007),\n'
                  '        "BTC":  (0.118,  4.319),\n'
                  '        "SOL":  (1.366,  2.742),\n')
    e.append(Ersetzung("execution/engine.py", alt_spread,
        f"        # [{MARKE}] BTC/ETH/SOL aus der {QUELLE}\n"
        "        # (pruefstand/berichte/2026-10-14_spanne_bitvavo.json). Vorher Bybit EU 31.07.:\n"
        "        # ETH (0.054, 5.007), BTC (0.118, 4.319), SOL (1.366, 2.742). Uebrige Muenzen\n"
        "        # handelt der Bot nicht; sie behalten die Bybit-Werte.\n"
        f'        "ETH":  ({MED["ETH"]:.3f}, {P90["ETH"]:.3f}),\n'
        f'        "BTC":  ({MED["BTC"]:.3f}, {P90["BTC"]:.3f}),\n'
        f'        "SOL":  ({MED["SOL"]:.3f}, {P90["SOL"]:.3f}),\n'))
    # 4 Kostenlatte und Nachzieh-Start in exit_rules
    e.append(Ersetzung("risk/exit_rules.py",
        "K_BASIS_PCT = 0.505           # Bybit EU Taker 0,25 % je Seite, CLAUDE.md 8\n",
        f"# [{MARKE}] Bitvavo USDC: 2 x 0,05 % Gebuehr + {schlupf_runde:.3f} % Schlupf (Stichprobe)\n"
        f"# = {0.10 + schlupf_runde:.3f} %, gerundet {K:.2f}. Vorher 0.505 (Bybit EU). CLAUDE.md 8.\n"
        f"K_BASIS_PCT = {K:.3f}           # Bitvavo USDC, CLAUDE.md 8\n"))
    e.append(Ersetzung("risk/exit_rules.py",
        "TRAIL_AB_PCT = 1.57            # darunter kein Trailing\n",
        f"# [{MARKE}] Nulllinie (1+K)/(1-Trail)-1 bei K={K} und Trail={TRAIL} plus 0,05 Marge.\n"
        f"TRAIL_AB_PCT = {TRAIL_AB}            # darunter kein Trailing (vorher 1.57)\n"))
    # 5 Zielgroessen
    e.append(Ersetzung("config_zielgroessen.json",
        '  "kosten_je_runde_pct": 0.505,\n'
        '  "_kosten_warum": "K-BASIS, Bybit EU Taker 0,25 % je Seite plus Spread. Nie aus ccxt holen.",\n',
        f'  "kosten_je_runde_pct": {K},\n'
        f'  "_kosten_warum": "[{MARKE}] K-BASIS ab {"E10" if name == "v6" else "L9"}: Bitvavo USDC 2 x 0,05 % plus Spread '
        f'(Stichprobe), gerundet {K}. Vorher 0.505 (Bybit EU) - gilt weiter fuer aeltere Epochen. Nie aus ccxt holen.",\n'))
    if name == "v6":
        for datei in ("features/regime_adaptiv.py", "risk/exit_rules_schatten.py"):
            e.append(Ersetzung(datei, "KOSTEN_PCT = 0.32\n",
                f"# [{MARKE}] Vorher 0.32 (Gebuehrenwelt Juli, Handbuch 4.6). Jetzt die Kostenlatte K.\n"
                f"KOSTEN_PCT = {K:.3f}\n"))
    else:
        e.append(Ersetzung("core/kosten.py",
            "TAKER_PCT = 0.25            # je Seite, Bybit EU Spot\n",
            f"# [{MARKE}] Zielboerse Bitvavo USDC-Maerkte (Kategorie B), vorher Bybit EU 0,25.\n"
            "TAKER_PCT = 0.05            # je Seite, Bitvavo USDC\n"))
        e.append(Ersetzung("core/kosten.py",
            "MAKER_PCT = 0.25            # je Seite, Warte-Auftrag (Limit-Order)\n",
            "MAKER_PCT = 0.05            # je Seite, Warte-Auftrag (Limit-Order), Bitvavo: Maker = Taker\n"))
        e.append(Ersetzung("core/kosten.py",
            "SCHLUPF_PCT = 0.005         # je Runde, gemessen am Orderbuch\n",
            f"SCHLUPF_PCT = 0.050         # je Runde, Bitvavo-Stichprobe 14.10. ({schlupf_runde:.3f}, gerundet)\n"))
        e.append(Ersetzung("core/kosten.py",
            "K_BASIS_PCT = 0.505         # zwei Taker-Seiten plus Schlupf\n",
            f"K_BASIS_PCT = {K:.3f}         # zwei Taker-Seiten plus Schlupf (Bitvavo USDC, vorher 0.505)\n"))
    return e


def werteprobe() -> int:
    print(f"  Stichprobe: {QUELLE}")
    for m in ("BTC", "ETH", "SOL"):
        print(f"    {m}: Median {MED[m]} bp, p90 {P90[m]} bp -> Schlupf je Seite Median {MED[m] / 2 / 100:.4f} %")
    print(f"  Schlupf je Runde (Mittel) {schlupf_runde:.4f} % -> K = {0.10 + schlupf_runde:.4f} %, eingesetzt {K}")
    print(f"  Puffer = K + 0.045 = {K + 0.045:.3f} | Nachzieh-Start = {TRAIL_AB}")
    ok = abs((0.10 + schlupf_runde) - K) <= 0.03 and TRAIL_AB == 1.21
    print(f"  {'OK  ' if ok else 'FEHL'} gerundetes K liegt nahe an der Messung (Abstand <= 0,03)")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    inst = json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]
    main(Path(inst["pfad"]), ersetzungen(name), MARKE, f"PATCH Kostenlatte Bitvavo {name}",
         zusatztest=werteprobe)
