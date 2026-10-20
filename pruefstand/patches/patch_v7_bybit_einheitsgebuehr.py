# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH Einheitsgebuehr fuer v7 - Warte-Auftraege kosten bei Bybit EU 0,25 %, nicht 0,10 %.

PRIMAERQUELLE (abgerufen 14.10.2026, HTTP 200):
  https://www.bybit.eu/en-EU/help-center/article/Trading-Fee-Structure
  "Last updated on 2026-10-05 13:01:39"
  "From 05/10/2026 at 11:00 UTC, we're moving to a single unified fee structure"
  VIP 0: Trading Fee Rate 0.2500 % - eine Spalte, kein Maker-Rabatt mehr.

BEFUND (pruefstand/inventur.md P0-1): v7 bucht Kaeufe ueber Warte-Auftraege
weiter mit 0,10 % (engine.py:486 -> _paper_gebuehr_satz("maker") ->
backtest/fees.py:24). 8 Kaeufe seit 05.10. 11:00 UTC, 2,88 $ zu wenig Gebuehr.

EINE Aenderung (der Maker-Satz), an den drei Stellen, an denen er steht:
  backtest/fees.py:24        bybit maker 0.10 -> 0.25   (Quelle der Engine)
  execution/engine.py:393    Rueckfall maker 0.0010 -> 0.0025
  core/kosten.py:61          MAKER_PCT 0.10 -> 0.25     (K_WARTE_PCT wird 0,505)
Kein Handelsverhalten: der Satz wird nur beim Buchen benutzt (geprueft 14.10.,
einzige Nutzung engine.py:486). Er aendert aber pnl und damit Lernen und
Verlustzaehler - deshalb mit Epochengrenze.

NICHT angefasst: maker_schatten.py:79 (Rueckblick-Messung aus der alten
Gebuehrenwelt) - meldet einen Vorteil, den es seit 05.10. nicht mehr gibt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

V7 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v7")
MARKE = "EINHEITSGEBUEHR 05.10.2026"

ERSETZUNGEN = [
    Ersetzung(
        "backtest/fees.py",
        '    "bybit":      {"maker": 0.10, "taker": 0.25},   # EU-Spot, geprueft\n',
        '    # [' + MARKE + '] Bybit EU seit 05.10.2026 11:00 UTC Einheitsgebuehr\n'
        '    # 0,25 % fuer VIP 0, kein Maker-Rabatt (Trading-Fee-Structure, geprueft 14.10.2026).\n'
        '    "bybit":      {"maker": 0.25, "taker": 0.25},   # EU-Spot, geprueft\n'),
    Ersetzung(
        "execution/engine.py",
        '        rueckfall = {"taker": 0.0025, "maker": 0.0010}\n',
        '        # [' + MARKE + '] Maker = Taker seit Bybit-EU-Einheitsgebuehr.\n'
        '        rueckfall = {"taker": 0.0025, "maker": 0.0025}\n'),
    Ersetzung(
        "core/kosten.py",
        "MAKER_PCT = 0.10            # je Seite, Warte-Auftrag (Limit-Order)\n",
        "# [" + MARKE + "] Bybit EU: Einheitsgebuehr, Maker = Taker (vorher 0,10).\n"
        "MAKER_PCT = 0.25            # je Seite, Warte-Auftrag (Limit-Order)\n"),
]


def wertprobe() -> int:
    """Liest die gepatchten Werte aus einer Kopie wie die Engine es tut."""
    import importlib.util
    import shutil
    import tempfile
    from _patchwerkzeug import anwenden
    with tempfile.TemporaryDirectory() as tmp:
        k = Path(tmp)
        for e in ERSETZUNGEN:
            (k / e.datei).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(V7 / e.datei, k / e.datei)
        anwenden(k, ERSETZUNGEN, MARKE, trocken_kopie=True)
        spec = importlib.util.spec_from_file_location("fees_kopie", k / "backtest" / "fees.py")
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        mk = m.EXCHANGE_FEES["bybit"]["maker"]
        sp = importlib.util.spec_from_file_location("kosten_kopie", k / "core" / "kosten.py")
        kk = importlib.util.module_from_spec(sp); sp.loader.exec_module(kk)
        ok = mk == 0.25 and kk.MAKER_PCT == 0.25 and abs(kk.K_WARTE_PCT - 0.505) < 1e-9
        print(f"  {'OK  ' if ok else 'FEHL'} Werte aus der Kopie: fees bybit maker {mk}, "
              f"MAKER_PCT {kk.MAKER_PCT}, K_WARTE_PCT {kk.K_WARTE_PCT}")
    return 0 if ok else 1


if __name__ == "__main__":
    main(V7, ERSETZUNGEN, MARKE, "PATCH v7 - Bybit-EU-Einheitsgebuehr 0,25 %", zusatztest=wertprobe)
