# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Forschungsdatenbank - Architektur-Scan, 30.07.2026.
"""
A3 - Bot-Architektur erfassen. NUR LESEND.

METHODE (mechanisch, keine Schaetzung)
--------------------------------------
* Jede .py unter der Projektwurzel, ausser __pycache__, _archive*, .venv,
  node_modules und docs/** (letzteres ist Forschungsprogramm, nicht Bot).
* zweck   = erste nichtleere Zeile des Modul-Docstrings, sonst erste
            Kommentarzeile. KEINE Interpretation.
* abhaengigkeiten = projektinterne Importe via ast, aufgeloest gegen die
            vorhandenen Modulpfade. importiert_von = Umkehrung.
* status  = mechanisch aus der Erreichbarkeit ab app.py:
      AKTIV       transitiv von app.py erreichbar
      TOT         von KEINEM Modul importiert und kein Einstiegspunkt
      UNGEPRUEFT  importiert, aber nicht von app.py aus erreichbar
      DEAKTIVIERT wird NICHT geraten - nur aus der Override-Liste
  Import != Aufruf. AKTIV heisst "erreichbar", nicht "wird benutzt".
  Diese Unterscheidung steht in status_belege.

OVERRIDES - jede Zeile mit Beleg, keine uebernommene Behauptung.
Die im Auftrag als "tot" genannten Module wurden einzeln nachgeprueft;
zwei Angaben waren so nicht haltbar und sind korrigiert.
"""
import ast
import json
import os
import sys
from datetime import datetime, timezone

from db_schema import verbinde

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
EINSTIEG = ["app.py"]
AUSSCHLUSS_TEILE = ("__pycache__", "_archive", ".venv", "venv",
                    "node_modules", "docs/")

UEBERSCHREIBUNGEN = {
    "risk/position_sizing.py": (
        "DEAKTIVIERT",
        "Modul lebt: risk/engine.py:13 importiert, :53 instanziiert, "
        ":179 self.sizer.calculate() aufgerufen. ABER config.json "
        "risk.use_dynamic_sizing=false und app.py:886 verzweigt darauf. "
        "KORREKTUR zur Auftragsannahme 'tot': nicht tot, sondern per "
        "Konfiguration abgeschaltet.",
        [], "Reaktivierung ist eine Config-Aenderung, kein Code-Fix."),
    "features/indicators.py": (
        "UNGEPRUEFT",
        "calc_all_indicators: in app.py:64 IMPORTIERT, aber 0 Aufrufe in "
        "app.py (verifiziert per grep 'calc_all_indicators('). Einziger "
        "echter Aufrufer: models/train_pipeline.py:31. KORREKTUR zur "
        "Auftragsannahme: die FUNKTION ist nicht global tot, der IMPORT "
        "in app.py ist toter Ballast.",
        ["toter Import app.py:64"],
        "G1 hat die Indikatoren numerisch verifiziert (17/21 exakt)."),
}

BUGS = {
    "features/vwap_agent.py": [
        "vwap_agent.py:64 rundet den zurueckgegebenen VWAP auf 2 Dezimalen; "
        "fuer Kleinpreis-Coins (DOGE) 24,6 % Vorzeichenfehler. Bias-Pfad "
        "rechnet vor der Rundung. (BEFUNDE.md 40)"],
    "data/market_data.py": [
        "_adx (market_data.py:117, SMA) und regime_detection.py:42 "
        "(ta.adx, Wilder) korrelieren mit Pearson -0,51 fuer +DI/-DI. "
        "(BEFUNDE.md 41)",
        "market_data.py:54 faellt bei fehlendem USDC-Paar auf USDT zurueck. "
        "Unter MiCA existieren keine USDT-Paare auf EU-Boersen - der "
        "Fallback laeuft stumm ins Leere. (01_IST-ZUSTAND.md)"],
    "features/regime_detection.py": [
        "Zweite, widerspruechliche ADX-Variante - siehe data/market_data.py."],
    "execution/engine.py": [
        "engine.py:253 fee_rate=0.001 hart verdrahtet; engine.py:242-247 "
        "Paper-Slippage ist random.uniform(0.02,0.08) %, kein Marktmodell.",
        "Nur Market-Orders (engine.py:384-385), kein Limit-Pfad. Nach "
        "07_GATE-1-BEFUND.md Par. 2 wirtschaftlich bedeutungslos fuer "
        "niederfrequente Regeln."],
    "config/settings.py": [
        "settings.py:236 dca_drop_pct ist toter Parameter: die -2-%-Schwelle "
        "ist in app.py:1798 hart codiert (entry*0.98). (BEFUNDE.md 4)"],
    "backtest/fees.py": [
        "fees.py:9 bnb_discount wird von FeeCalculator.calculate() nie "
        "gelesen. Tabelle gilt fuer Binance, nicht fuer Bybit EU.",
        "ccxt.bybit().fees meldet maker 0,01 / taker 0,075 % - fuer EU-Spot "
        "falsch (Ist 0,10/0,25). (06_MIGRATIONSSPEZIFIKATION.md)"],
    "app.py": [
        "app.py:1534 coins[:12] wirkungslos - config.json listet 11 Coins. "
        "(BEFUNDE.md 17)",
        "app.py:1789-1790 / 1754-1755 / 1834-1835: Cooldown dreifach "
        "fail-open; last_dca_time nur im RAM. (BEFUNDE.md 3)"],
}


def relevant(rel):
    r = rel.replace("\\", "/")
    return not any(a in r for a in AUSSCHLUSS_TEILE)


def modulname(rel):
    return rel.replace("\\", "/")[:-3].replace("/", ".")


def scan():
    dateien = []
    for wz, dirs, files in os.walk(WURZEL):
        dirs[:] = [d for d in dirs
                   if d not in ("__pycache__", ".venv", "venv",
                                "node_modules", "docs")
                   and not d.startswith("_archive")]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(wz, f),
                                      WURZEL).replace("\\", "/")
                if relevant(rel):
                    dateien.append(rel)
    namen = {}
    for rel in dateien:
        mn = modulname(rel)
        namen[mn] = rel
        namen.setdefault(mn.split(".")[-1], rel)
    info = {}
    for rel in dateien:
        p = os.path.join(WURZEL, rel)
        try:
            quelle = open(p, encoding="utf-8", errors="replace").read()
        except OSError as e:
            info[rel] = {"zeilen": 0, "zweck": f"NICHT LESBAR: {e}",
                         "deps": [], "fehler": True}
            continue
        zeilen = quelle.count("\n") + 1
        zweck, deps, fehler = "", set(), False
        try:
            baum = ast.parse(quelle)
            ds = ast.get_docstring(baum)
            if ds:
                for z in ds.strip().splitlines():
                    if z.strip():
                        zweck = z.strip()[:200]
                        break
            for k in ast.walk(baum):
                if isinstance(k, ast.Import):
                    for a in k.names:
                        deps.add(a.name)
                elif isinstance(k, ast.ImportFrom) and k.module and k.level == 0:
                    deps.add(k.module)
        except SyntaxError as e:
            fehler = True
            zweck = f"SYNTAXFEHLER: {e.msg} (Zeile {e.lineno})"
        if not zweck:
            for z in quelle.splitlines()[:6]:
                if z.strip().startswith("#") and "-*-" not in z:
                    zweck = z.strip("# ").strip()[:200]
                    break
        intern = sorted({namen[d] for d in deps
                         if d in namen and namen[d] != rel})
        info[rel] = {"zeilen": zeilen, "zweck": zweck, "deps": intern,
                     "fehler": fehler}
    von = {r: [] for r in info}
    for r, d in info.items():
        for x in d["deps"]:
            von.setdefault(x, []).append(r)
    erreichbar, stapel = set(), [e for e in EINSTIEG if e in info]
    while stapel:
        r = stapel.pop()
        if r in erreichbar:
            continue
        erreichbar.add(r)
        stapel.extend(info.get(r, {}).get("deps", []))
    return info, von, erreichbar


def main():
    info, von, erreichbar = scan()
    jetzt = datetime.now(timezone.utc).isoformat()[:19] + "Z"
    con = verbinde()
    con.execute("DELETE FROM bot_architektur")
    stat = {}
    fehlerhafte = []
    for rel, d in sorted(info.items()):
        if d.get("fehler"):
            fehlerhafte.append(rel)
        importeure = sorted(von.get(rel, []))
        if rel in erreichbar:
            status = "AKTIV"
            beleg = ("transitiv von app.py erreichbar. ACHTUNG: erreichbar "
                     "heisst importiert, nicht zwingend aufgerufen.")
        elif not importeure and rel not in EINSTIEG:
            status = "TOT"
            beleg = ("von keinem Projektmodul importiert und kein "
                     "Einstiegspunkt (mechanisch ermittelt).")
        else:
            status = "UNGEPRUEFT"
            beleg = (f"importiert von {len(importeure)} Modul(en), aber "
                     f"nicht von app.py aus erreichbar.")
        bugs = list(BUGS.get(rel, []))
        anm = ""
        if rel in UEBERSCHREIBUNGEN:
            status, beleg, ub, anm = UEBERSCHREIBUNGEN[rel]
            bugs += ub
        stat[status] = stat.get(status, 0) + 1
        con.execute(
            "INSERT INTO bot_architektur (pfad,zeilen,zweck,abhaengigkeiten,"
            "importiert_von,status,status_belege,bekannte_bugs,"
            "letzte_pruefung,anmerkung) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rel, d["zeilen"], d["zweck"], json.dumps(d["deps"]),
             json.dumps(importeure), status, beleg, json.dumps(bugs),
             jetzt, anm))
    con.commit()
    print(f"  Module erfasst: {sum(stat.values())}")
    for k in sorted(stat):
        print(f"    {k:<12s} {stat[k]:4d}")
    print(f"  Module mit dokumentierten Bugs: {len(BUGS)}")
    print(f"  AST-Parsefehler: {len(fehlerhafte)}"
          + (f" -> {', '.join(fehlerhafte[:5])}" if fehlerhafte else ""))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
