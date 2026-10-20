# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH KG1 - Kaufgroesse nur aus dem Handelsgeld (ohne Sparplan-BTC). v6 und v7.
Entscheidung Sven 15.10.2026: KG1 + KG1a (entscheidungen.md), "Umsetzung mit der naechsten
Bot-Aenderung als eigene Epoche". VORBEREITET, NOCH NICHT EINGESPIELT.
Vorab-Registrierung: pruefstand/epochen/E14_L13_kaufgroesse_handelsgeld.md

Eine Ursache, eine Aenderung je Bot (beide Dateien gehoeren zusammen):
  1 portfolio/manager.py (in v6 und v7 identisch): neue Funktion get_trading_capital()
    = get_total_capital() minus Sparplan-BTC. get_total_capital() bleibt UNVERAENDERT
    (Drawdown-Guard, Tagesverlust, Tagesstart-Kapital und Anzeige rechnen weiter mit Sparplan, E10-KAPITAL).
  2 app.py (v7 CRLF / v6 LF, Werkzeug haelt das je Datei): Im Block "MANUELLES SIZING"
    (use_dynamic_sizing = false, in beiden Bots aktiv) wird die Kaufgroesse aus
    get_trading_capital() statt aus get_total_capital() gerechnet.

Beleg fuer den Fehler (v7 system.log 15.10.2026, Z. 31757-31763): Das Signal rechnete 117,44 $
(50 % von 234,88 $ Handelsgeld), der Sizing-Block ueberschrieb mit 232,91 $ (50 % von 465,76 $ inkl.
Sparplan), erst die Bargeld-Grenze kappte auf 223,14 $ -> 95 % der Handelskasse in einer Muenze.

NICHT Teil dieses Patches (von Sven noch nicht entschieden, A10 trennt es als Fehler):
  "begrenzen statt ersetzen" - der Sizing-Block ueberschreibt den Betrag der Portfolio-Pruefung
  (Reserve, Muenz-Deckel). Eigener Patch, falls Sven zustimmt.

Aufruf: python patch_kg1_kaufgroesse_handelsgeld.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "KG1 KAUFGROESSE HANDELSGELD"

MANAGER = Ersetzung(
    "portfolio/manager.py",
    "    # ============================================================\n"
    "    # POSITION SIZING - 100% prozentual\n"
    "    # ============================================================\n"
    "    def get_position_size(self, capital: Optional[float] = None) -> float:\n",
    "    def get_trading_capital(self) -> float:\n"
    "        \"\"\"Kapital fuer die KAUFGROESSE: Handelsgeld (USDC + offene Positionen) OHNE Sparplan-BTC.\n"
    "\n"
    f"        [{MARKE}, 15.10.2026] Entscheidung Sven KG1/KG1a (pruefstand/entscheidungen.md).\n"
    "        get_total_capital() zaehlt den Sparplan seit E10-KAPITAL (29.07.) mit. Fuer Drawdown-Guard,\n"
    "        Tagesverlust und Anzeige bleibt das so. Die Kaufgroesse darf ihn aber nicht mitzaehlen:\n"
    "        v7 setzte am 15.10. dadurch 95 % der Handelskasse in eine einzige Muenze.\n"
    "        Im Papiermodus ist das exakt Handelsgeld; im Live-Modus wirkt der Kapital-Deckel\n"
    "        (_kapital_deckel) schon auf die Summe MIT Sparplan - dann ist der Wert eher zu klein, nie zu gross.\n"
    "        \"\"\"\n"
    "        gesamt = self.get_total_capital()\n"
    "        try:\n"
    "            sparplan = float(self.get_btc_accumulator_value() or 0.0)\n"
    "        except Exception:\n"
    "            sparplan = 0.0\n"
    "        return max(gesamt - max(sparplan, 0.0), 0.0)\n"
    "\n"
    "    # ============================================================\n"
    "    # POSITION SIZING - 100% prozentual\n"
    "    # ============================================================\n"
    "    def get_position_size(self, capital: Optional[float] = None) -> float:\n")

APP = Ersetzung(
    "app.py",
    "                try:\n"
    "                    capital = self.portfolio.get_total_capital()\n"
    "                    target_amount = self.portfolio.get_position_size(capital)\n",
    "                try:\n"
    f"                    # [{MARKE}, 15.10.2026] Basis ist das Handelsgeld OHNE Sparplan-BTC\n"
    "                    # (Entscheidung Sven KG1/KG1a). Vorher get_total_capital() mit Sparplan.\n"
    "                    capital = self.portfolio.get_trading_capital()\n"
    "                    target_amount = self.portfolio.get_position_size(capital)\n")

ERS = {"v6": [MANAGER, APP], "v7": [MANAGER, APP]}


def funktionstest(name: str, ordner: Path) -> int:
    """Rechnet get_trading_capital und die Kaufgroesse auf einer gepatchten Kopie nach."""
    import importlib.util
    import shutil
    import tempfile
    import types
    from _patchwerkzeug import anwenden
    fehler = 0
    with tempfile.TemporaryDirectory() as t:
        k = Path(t)
        for e in ERS[name]:
            (k / e.datei).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ordner / e.datei, k / e.datei)
        anwenden(k, ERS[name], MARKE, trocken_kopie=True)

        stub = types.ModuleType("core.logger")

        class L:
            def __getattr__(self, a):
                return lambda *x, **y: None
        stub.log = L()
        alt = {m: sys.modules.get(m) for m in ("core", "core.logger")}
        sys.modules["core"] = types.ModuleType("core")
        sys.modules["core.logger"] = stub
        try:
            spec = importlib.util.spec_from_file_location("pm_kg1", k / "portfolio" / "manager.py")
            pm_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pm_mod)
        finally:
            for m, v in alt.items():
                if v is None:
                    sys.modules.pop(m, None)
                else:
                    sys.modules[m] = v

        class Modus:
            def __init__(self, pct):
                self.position_size_pct = pct

        def pm(gesamt, sparplan, pct):
            o = object.__new__(pm_mod.PortfolioManager)
            o.config = types.SimpleNamespace(get_active_mode=lambda: Modus(pct))
            o.get_total_capital = lambda: gesamt
            if isinstance(sparplan, Exception):
                def _f():
                    raise sparplan
                o.get_btc_accumulator_value = _f
            else:
                o.get_btc_accumulator_value = lambda: sparplan
            return o

        faelle = [
            # (Beschreibung, gesamt, sparplan, modus-%, soll Handelsgeld, soll Kaufgroesse)
            ("v7 15.10. 08:29 (Log: Signal 117,44 $)", 465.76, 230.88, 50, 234.88, 117.44),
            ("v6 heute (Kasse 408,14 $, Sparplan 165,80 $)", 573.94, 165.80, 30, 408.14, 122.44),
            ("ohne Sparplan: unveraendert (Regression)", 300.00, 0.0, 30, 300.00, 90.00),
            ("Sparplan-Bewertung wirft Fehler: wie bisher", 300.00, RuntimeError("kein Preis"), 30, 300.00, 90.00),
            ("Sparplan groesser als Gesamt (Grenzfall): 0, Minimum 5 $", 100.00, 150.0, 30, 0.00, 5.00),
        ]
        for text, g, s, pct, soll_k, soll_b in faelle:
            o = pm(g, s, pct)
            k_ist = o.get_trading_capital()
            b_ist = o.get_position_size(k_ist)
            ok = abs(k_ist - soll_k) < 0.005 and abs(b_ist - soll_b) < 0.005
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} {text}: Handelsgeld {k_ist:.2f} $, Kauf {b_ist:.2f} $")

        o = pm(465.76, 230.88, 50)
        ok = o.get_total_capital() == 465.76
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} get_total_capital() unveraendert (Drawdown/Tagesverlust/Anzeige)")

        # nur Code-Zeilen zaehlen (der neue Kommentar nennt get_total_capital() beim Namen)
        def aufrufe(p: Path, wort: str) -> int:
            return sum(z.count(wort) for z in p.read_text(encoding="utf-8").splitlines()
                       if not z.strip().startswith("#"))
        vorher = aufrufe(ordner / "app.py", "self.portfolio.get_total_capital()")
        nachher = aufrufe(k / "app.py", "self.portfolio.get_total_capital()")
        neu = aufrufe(k / "app.py", "self.portfolio.get_trading_capital()")
        ok = nachher == vorher - 1 and neu == 1
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} app.py: genau 1 Aufruf umgestellt "
              f"(get_total_capital {vorher} -> {nachher}, get_trading_capital {neu})")
    return 1 if fehler else 0


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    pfad = Path(json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]["pfad"])
    main(pfad, ERS[name], MARKE, f"PATCH KG1 Kaufgroesse aus Handelsgeld {name}", zusatztest=lambda: funktionstest(name, pfad))
