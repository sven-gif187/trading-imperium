# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH E12 / L11 - Puffer Nullsicherung K + 0,10 und Kauf-Felder am Verkauf (Befund 88). v6 E12, v7 L11.
Entscheidung Sven 15.10.2026: E5 ("Puffer 0,25 mit der naechsten Bot-Aenderung"), F8 (Kleinkram selbststaendig).

AENDERUNG 1 (verhaltensaendernd) risk/exit_rules.py:
  BREAKEVEN_MARGE_PCT 0,045 -> 0,10, also Puffer = K + Marge = 0,150 + 0,10 = 0,25 %.
  Grund (A5-V2, A10: traegt): Ausloeseverzug der Nullsicherung im Mittel 0,072 %, p90 0,17 %. Mit 0,045 endete
  jede Nullsicherung im Mittel bei -0,027 %, mit 0,10 bei +0,028 %. Wirkung klein (rund +1 $ in zwei Monaten).

AENDERUNG 2 (nur Aufzeichnung) app.py _journal_add():
  Befund 88: stop_initial, trailing_stop_pct, decision_id, signal_score, signal_reasons und active_strategy
  stehen am KAUF, aber nicht am VERKAUF. Dazu fehlten oft entry_score/entry_strategie, weil Positionen nach
  einem Neustart ohne diese Felder wiederhergestellt werden. Jetzt fuellt _journal_add, durch das ALLE
  Schreibwege laufen, fehlende Felder eines Verkaufs aus dem ersten Kauf der laufenden Runde (Kaeufe derselben
  Muenze seit dem letzten Verkauf, wie pruefstand/skripte/runden_lib.py). Vorhandene Werte bleiben, Herkunft
  steht in "felder_aus_kauf". Darf nie werfen. Teilverkaeufe: der zweite Teil findet keinen Kauf mehr und
  bleibt wie bisher (seit E7 gab es 0 Teilverkaeufe, A10).
Aufruf: python patch_e12_puffer_pflichtfelder.py v6|v7 --pruefen|--selbsttest|--anwenden
"""
import json
import sys
import textwrap
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "E12 PUFFER PFLICHTFELDER 15.10.2026"

ALT_MARGE = "BREAKEVEN_MARGE_PCT = 0.045   # damit die Null nicht knapp verfehlt wird\n"
NEU_MARGE = (f"# [{MARKE}] Marge 0,045 -> 0,10 (A5-V2, Entscheidung Sven E5): Ausloeseverzug der Nullsicherung\n"
             "# im Mittel 0,072 %, p90 0,17 %. Mit 0,045 endete sie im Mittel bei -0,027 %, mit 0,10 bei +0,028 %.\n"
             "BREAKEVEN_MARGE_PCT = 0.10    # damit die Null nicht knapp verfehlt wird\n")

BLOCK = '''\
# [MARKE] Befund 88: Kauf-Felder an den Verkauf weiterreichen.
# stop_initial, trailing_stop_pct, decision_id, signal_score, signal_reasons und active_strategy stehen
# am KAUF, aber nicht am VERKAUF - die Frage "welches Signal endet wie?" war nur ueber Umwege
# beantwortbar. Positionen, die nach einem Neustart wiederhergestellt werden, verlieren zudem
# entry_score/entry_strategie. Hier, wo ALLE Schreibwege durchlaufen, werden fehlende Felder eines
# Verkaufs aus dem ersten Kauf der laufenden Runde ergaenzt (Kaeufe derselben Muenze seit dem letzten
# Verkauf, wie pruefstand/skripte/runden_lib.py). Vorhandene Werte bleiben unangetastet.
try:
    if str(entry.get("type", "")).upper().startswith("SELL"):
        _kf_felder = ("stop_initial", "trailing_stop_pct", "decision_id",
                      "signal_score", "signal_reasons", "active_strategy")
        _kf_leer = (None, "", [])
        if (any(entry.get(_f) in _kf_leer for _f in _kf_felder)
                or entry.get("entry_score") is None or not entry.get("entry_strategie")):
            _kf_coin = entry.get("coin") or entry.get("symbol")
            _kf_kaeufe = []
            for _t in reversed(self.journal.get_last(400)):
                if (_t.get("coin") or _t.get("symbol")) != _kf_coin:
                    continue
                _kf_typ = str(_t.get("type", "")).upper()
                if _kf_typ.startswith("SELL"):
                    break
                if _kf_typ == "BUY":
                    _kf_kaeufe.append(_t)
            if _kf_kaeufe:
                _kf_k = _kf_kaeufe[-1]          # erster Kauf der Runde
                for _f in _kf_felder:
                    if entry.get(_f) in _kf_leer and _kf_k.get(_f) not in _kf_leer:
                        entry[_f] = _kf_k.get(_f)
                if entry.get("entry_score") is None:
                    entry["entry_score"] = _kf_k.get("signal_score", _kf_k.get("score"))
                if not entry.get("entry_strategie"):
                    entry["entry_strategie"] = (_kf_k.get("active_strategy")
                                                or _kf_k.get("strategy") or "")
                entry["felder_aus_kauf"] = {"kauf_id": _kf_k.get("_id"),
                                            "kauf_zeit": _kf_k.get("time"),
                                            "kaeufe": len(_kf_kaeufe)}
except Exception as _kf_e:
    try:
        log.warn("JOURNAL", f"Kauf-Felder nicht uebernommen: {str(_kf_e)[:80]}")
    except Exception:
        pass
'''.replace("MARKE", MARKE)

ALT_ADD = "\n        _ergebnis = self.journal.add(entry)\n"
NEU_ADD = "\n" + textwrap.indent(BLOCK, " " * 8) + "\n        _ergebnis = self.journal.add(entry)\n"
ERS = [Ersetzung("risk/exit_rules.py", ALT_MARGE, NEU_MARGE), Ersetzung("app.py", ALT_ADD, NEU_ADD)]


def funktionstest(ordner: Path) -> int:
    """Puffer im gepatchten exit_rules.py = 0,25; Block auf einem Schein-Journal in sechs Faellen."""
    import importlib.util
    import shutil
    import tempfile
    from _patchwerkzeug import anwenden
    fehler = 0
    with tempfile.TemporaryDirectory() as t:
        k = Path(t)
        (k / "risk").mkdir()
        shutil.copy2(ordner / "risk" / "exit_rules.py", k / "risk" / "exit_rules.py")
        shutil.copy2(ordner / "app.py", k / "app.py")
        anwenden(k, ERS, MARKE, trocken_kopie=True)
        spec = importlib.util.spec_from_file_location("er", k / "risk" / "exit_rules.py")
        er = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(er)
        ok = abs(er.BREAKEVEN_PUFFER_PCT - 0.25) < 1e-9 and er.K_BASIS_PCT == 0.150
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Puffer {er.BREAKEVEN_PUFFER_PCT} = K {er.K_BASIS_PCT} + Marge {er.BREAKEVEN_MARGE_PCT}")
        text = (k / "app.py").read_text(encoding="utf-8")
        ok = text.count(MARKE) == 1 and text.index(MARKE) < text.index("_ergebnis = self.journal.add(entry)")
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} Block steht genau einmal vor journal.add")

    class Log:
        meldungen = []

        def warn(self, *a):
            self.meldungen.append(a)

    class J:
        def __init__(self, z):
            self.z = z

        def get_last(self, n):
            return self.z[-n:]

    ns = {}
    exec("def f(self, entry, log):\n" + textwrap.indent(BLOCK, "    "), ns)
    kauf = {"type": "BUY", "coin": "BTC/USDC", "_id": 7, "time": "t1", "stop_initial": 100.0, "trailing_stop_pct": 1.0,
            "decision_id": "d1", "signal_score": 6, "signal_reasons": ["a"], "active_strategy": "EMA_TREND", "strategy": "EMA_TREND"}

    class S:
        def __init__(self, z):
            self.journal = J(z)
    faelle = []
    e = {"type": "SELL", "coin": "BTC/USDC", "entry_score": None, "entry_strategie": ""}
    ns["f"](S([{"type": "SELL", "coin": "BTC/USDC"}, kauf]), e, Log())
    faelle.append(("Verkauf erbt alle Felder", e.get("stop_initial") == 100.0 and e.get("decision_id") == "d1"
                   and e.get("entry_score") == 6 and e.get("entry_strategie") == "EMA_TREND"
                   and e["felder_aus_kauf"]["kauf_id"] == 7))
    e = {"type": "SELL", "coin": "BTC/USDC", "decision_id": "eigen", "entry_score": 9, "entry_strategie": "X"}
    ns["f"](S([kauf]), e, Log())
    faelle.append(("vorhandene Werte bleiben", e["decision_id"] == "eigen" and e["entry_score"] == 9 and e["entry_strategie"] == "X"))
    e = {"type": "SELL", "coin": "BTC/USDC"}
    ns["f"](S([kauf, {"type": "SELL", "coin": "BTC/USDC"}]), e, Log())
    faelle.append(("nach einem Verkauf kein Kauf mehr -> nichts erfunden", "stop_initial" not in e and "felder_aus_kauf" not in e))
    e = {"type": "SELL", "coin": "ETH/USDC"}
    ns["f"](S([kauf]), e, Log())
    faelle.append(("andere Muenze -> nichts", "stop_initial" not in e))
    k2 = dict(kauf, _id=8, decision_id="d2")
    e = {"type": "SELL", "coin": "BTC/USDC"}
    ns["f"](S([kauf, k2]), e, Log())
    faelle.append(("zwei Kaeufe -> erster Kauf der Runde", e.get("decision_id") == "d1" and e["felder_aus_kauf"]["kaeufe"] == 2))
    lg = Log()
    e = {"type": "SELL", "coin": "BTC/USDC"}

    class Kaputt:
        def get_last(self, n):
            raise RuntimeError("kaputt")

    class S2:
        journal = Kaputt()
    try:
        ns["f"](S2(), e, lg)
        geworfen = False
    except Exception:
        geworfen = True
    faelle.append(("Fehler im Journal wirft nicht, nur Warnung", not geworfen and len(lg.meldungen) == 1))
    e = {"type": "BUY", "coin": "BTC/USDC"}
    ns["f"](S([kauf]), e, Log())
    faelle.append(("Kauf bleibt unberuehrt", "stop_initial" not in e))
    for text, ok in faelle:
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} {text}")
    return 1 if fehler else 0


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    pfad = Path(json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]["pfad"])
    main(pfad, ERS, MARKE, f"PATCH E12/L11 Puffer + Pflichtfelder {name}", zusatztest=lambda: funktionstest(pfad))
