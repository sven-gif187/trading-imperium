# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
PATCH L14 (Nummer vorlaeufig) - Befund 88, Rest in v7: Der bediente Warte-Auftrag verliert die Kauf-Felder.
NUR v7 (v6 hat keine Warte-Auftraege). VORBEREITET, NOCH NICHT EINGESPIELT.
Vorab-Registrierung: pruefstand/epochen/L14_warte_kauf_felder.md

URSACHE (17.10.2026): Seit warteauftraege.aktiv = true (12.09.) kauft v7 im Papierbetrieb NUR noch ueber
Warte-Auftraege (warteauftraege.json: 22 ausgefuehrt = alle 22 Kaeufe im Journal). Beim Anlegen merkt sich
execution/engine.py (_execute_paper :430 und _warteauftrag_live_anlegen :1097) nur strategy_id, score,
confidence und entry_reason. Beim Bedienen (warteauftraege_pruefen :1271, _warteauftraege_live_takt :1201)
wird daraus ein NEUER DecisionIntent gebaut - ohne stop_loss, take_profit, trailing_stop_pct, agent_id,
risk_reason und ohne _evaluation_id. app.py _buche_ergebnis schreibt deshalb am KAUF stop_initial = None und
trailing_stop_pct = None (alle 22 v7-Kaeufe), und der L11-Block in _journal_add kann am Verkauf nichts erben.
v6 kauft immer sofort mit dem Original-Intent, deshalb ist dort alles da.

AENDERUNG (nur Aufzeichnung) execution/engine.py, CRLF:
  1 zwei Helfer vor class ExecutionEngine: _warte_merkangaben(intent) / _warte_merkangaben_zurueck(intent, ang)
  2 Anlegen Papier und Live: angaben bekommen stop_loss, take_profit, trailing_stop_pct, agent_id,
    model_version, risk_reason und evaluation_id (nur einfache Typen, die Datei ist JSON; wirft nie)
  3 Bedienen Papier und Live: der neue Intent bekommt diese Werte zurueck, dazu _evaluation_id
    (damit _buche_ergebnis die Entscheidung mit der Position verknuepft, Telemetrie position_id).
  Diese Felder liest weder die Ausfuehrung noch der Ausstieg (geprueft: engine.py, risk/, runtime/,
  Telegram on_buy). Preis, Menge, Gebuehr, Bestand und Order-Kennungen bleiben gleich (Funktionstest).
  NICHT im Patch: decision_id am Kauf bleibt die Kennung des neu gebauten Intents (sie steckt in der
  client_order_id der Order-Historie; sie umzustellen beruehrt die Order-Buchung).

Aufruf: python patch_l14_warte_kauf_felder.py v7 --pruefen|--selbsttest|--anwenden
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from _patchwerkzeug import Ersetzung, main  # noqa: E402

MARKE = "BEFUND 88 WARTEKAUF 17.10.2026"

HELFER = f'''\
# [{MARKE}] Ein bedienter Warte-Auftrag baut den Kauf als NEUEN DecisionIntent
# auf (warteauftraege_pruefen, _warteauftraege_live_takt). Bisher kamen dabei nur
# strategy_id, score, confidence und entry_reason mit. stop_loss,
# trailing_stop_pct, take_profit, agent_id, risk_reason und die
# Telemetrie-Kennung der Entscheidung gingen verloren. Folge: Seit dem 12.09.
# stand stop_initial/trailing_stop_pct an JEDEM v7-Kauf leer, und der Verkauf
# konnte sie nicht erben (W4 pflichtfelder GELB, Befund 88). Nur Aufzeichnung:
# Ausfuehrung und Ausstieg lesen diese Felder nicht.
_WARTE_ZAHLEN = ("stop_loss", "take_profit", "trailing_stop_pct")
_WARTE_TEXTE = ("agent_id", "model_version", "risk_reason")


def _warte_merkangaben(intent):
    """Entscheidungs-Angaben fuer die Warteschlange. Nur einfache Typen (die
    Datei ist JSON). Wirft nie - lieber ein Feld leer als kein Auftrag."""
    aus = {{}}
    for _f in _WARTE_ZAHLEN + _WARTE_TEXTE:
        try:
            _v = getattr(intent, _f, None)
            if _v is None:
                continue
            aus[_f] = float(_v) if _f in _WARTE_ZAHLEN else str(_v)
        except Exception:
            pass
    try:
        _eid = getattr(intent, "_evaluation_id", "") or ""
        if _eid:
            aus["evaluation_id"] = str(_eid)
    except Exception:
        pass
    return aus


def _warte_merkangaben_zurueck(intent, ang):
    """Setzt die gemerkten Angaben am neu gebauten Kauf. Ein Auftrag von vor
    diesem Fix hat die Schluessel nicht und bleibt wie bisher. Wirft nie."""
    for _f in _WARTE_ZAHLEN + _WARTE_TEXTE:
        try:
            if ang.get(_f) is not None:
                setattr(intent, _f, ang.get(_f))
        except Exception:
            pass
    try:
        if ang.get("evaluation_id"):
            intent._evaluation_id = str(ang.get("evaluation_id"))
    except Exception:
        pass
    return intent

'''

ERS = [
    Ersetzung("execution/engine.py",
              "from execution.fill_reconciler import FillReconciler\n\nclass ExecutionEngine:\n",
              "from execution.fill_reconciler import FillReconciler\n\n" + HELFER + "\nclass ExecutionEngine:\n"),
    # Anlegen, Papier (_execute_paper)
    Ersetzung("execution/engine.py",
              "                intent.symbol, price, intent.amount_usd,\n"
              "                angaben={\"strategy_id\": getattr(intent, \"strategy_id\", \"\") or \"\",\n"
              "                         \"score\": getattr(intent, \"score\", None),\n"
              "                         \"confidence\": getattr(intent, \"confidence\", None),\n"
              "                         \"entry_reason\": getattr(intent, \"entry_reason\", \"\") or \"\"})\n",
              "                intent.symbol, price, intent.amount_usd,\n"
              "                angaben={\"strategy_id\": getattr(intent, \"strategy_id\", \"\") or \"\",\n"
              "                         \"score\": getattr(intent, \"score\", None),\n"
              "                         \"confidence\": getattr(intent, \"confidence\", None),\n"
              "                         \"entry_reason\": getattr(intent, \"entry_reason\", \"\") or \"\",\n"
              f"                         # [{MARKE}] Stop, Nachzieh-Abstand usw. mitnehmen\n"
              "                         **_warte_merkangaben(intent)})\n"),
    # Anlegen, Live (_warteauftrag_live_anlegen)
    Ersetzung("execution/engine.py",
              "                     \"live_order_id\": oid,\n"
              "                     \"live_menge\": menge})\n",
              "                     \"live_order_id\": oid,\n"
              "                     \"live_menge\": menge,\n"
              f"                     # [{MARKE}] Stop, Nachzieh-Abstand usw. mitnehmen\n"
              "                     **_warte_merkangaben(intent)})\n"),
    # Bedienen, Live (_warteauftraege_live_takt)
    Ersetzung("execution/engine.py",
              "                confidence=float(ang.get(\"confidence\") or 0.0),\n"
              "            )\n"
              "            result = ExecutionResult(intent_id=intent.id, symbol=symbol,\n",
              "                confidence=float(ang.get(\"confidence\") or 0.0),\n"
              "            )\n"
              f"            _warte_merkangaben_zurueck(intent, ang)   # [{MARKE}]\n"
              "            result = ExecutionResult(intent_id=intent.id, symbol=symbol,\n"),
    # Bedienen, Papier (warteauftraege_pruefen)
    Ersetzung("execution/engine.py",
              "                confidence=float(ang.get(\"confidence\") or 0.0),\n"
              "            )\n"
              "            result = ExecutionResult(intent_id=intent.id, symbol=intent.symbol,\n",
              "                confidence=float(ang.get(\"confidence\") or 0.0),\n"
              "            )\n"
              f"            _warte_merkangaben_zurueck(intent, ang)   # [{MARKE}]\n"
              "            result = ExecutionResult(intent_id=intent.id, symbol=intent.symbol,\n"),
]

# Pakete, die execution/engine.py beim Laden und im Papierpfad braucht. Die Kopie liegt im Temp-Ordner,
# config/settings.py leitet DATA_DIR aus seinem eigenen Ort ab - Order-Historie, Idempotenz-Datei und
# system.log landen also in der Kopie, nie im Bot-Ordner (der Treiber prueft das vor dem ersten Schritt).
PAKETE = ("config", "core", "execution", "backtest", "features")

TREIBER = r'''
import json, os, sys, types
bot = sys.argv[1]
sys.path.insert(0, bot)
os.chdir(bot)
import config.settings as cs
if not os.path.abspath(cs.DATA_DIR).lower().startswith(os.path.abspath(bot).lower()):
    print(json.dumps({"abbruch": "DATA_DIR zeigt nicht in die Kopie: " + cs.DATA_DIR})); sys.exit(3)
from config.settings import AppConfig
from core.events import DecisionIntent, Side
import execution.engine as em
from execution.engine import ExecutionEngine
from execution.warteauftraege import Warteschlange
import execution.warteauftraege_live as wl

T0 = 1789000000.0
gepatcht = hasattr(em, "_warte_merkangaben")
aus = {"gepatcht": gepatcht}

def maschine(name, paper=True):
    cfg = AppConfig(); cfg.trading.mode = "paper"
    eng = ExecutionEngine(cfg)
    eng._paper_balances = {"USDC": 10000.0}; eng._paper_entries = {}
    eng.warteschlange = Warteschlange(pfad=os.path.join(bot, "ws_%s.json" % name),
                                      einstellungen={"aktiv": True, "abstand_pct": 0.10, "gueltig_kerzen": 4,
                                                     "kerze_minuten": 15, "nur_paper": False}, jetzt=T0)
    return eng

def kauf(**extra):
    i = DecisionIntent(symbol="TEST/USDC", side=Side.BUY, amount_usd=200.0, entry_price=100.0,
                       strategy_id="PRUEFUNG", score=8, confidence=0.8, **extra)
    return i

def felder(i):
    return {"stop_loss": i.stop_loss, "take_profit": i.take_profit, "trailing_stop_pct": i.trailing_stop_pct,
            "agent_id": i.agent_id, "model_version": i.model_version, "risk_reason": i.risk_reason,
            "evaluation_id": getattr(i, "_evaluation_id", None), "strategy_id": i.strategy_id, "score": i.score,
            "confidence": i.confidence, "entry_reason": i.entry_reason}

def handel(eng, r_anlage, fertige):
    i, r = fertige[0]
    return {"anlage_status": r_anlage.status, "limit": r_anlage.avg_fill_price, "status": r.status,
            "preis": r.avg_fill_price, "menge": r.filled_qty, "kosten": r.filled_cost, "gebuehr": r.fee,
            "schlupf": r.slippage_pct, "usdc": round(eng._paper_balances.get("USDC", 0), 8),
            "test": round(eng._paper_balances.get("TEST", 0), 10), "betrag": i.amount_usd,
            "einstieg": i.entry_price, "offen": len(eng.warteschlange.offene())}

# P1: Papier, voller Kauf (wie signal_agent.py:247 plus risk_reason und Telemetrie-Kennung)
eng = maschine("p1")
k = kauf(stop_loss=97.85, take_profit=None, trailing_stop_pct=1.21, agent_id="signal_agent")
k.risk_reason = "genehmigt"; k._evaluation_id = "ev_p1"
r = eng.execute(k)
datei = json.load(open(os.path.join(bot, "ws_p1.json"), encoding="utf-8"))
aus["p1_angaben"] = (datei["auftraege"].get("TEST/USDC") or {}).get("angaben")
f = eng.warteauftraege_pruefen({"TEST/USDC": 99.85})
aus["p1_handel"] = handel(eng, r, f) if f else None
aus["p1_felder"] = felder(f[0][0]) if f else None

# P2: Auftrag aus der Datei von VOR dem Fix (alte Schluessel) wird nach dem Einspielen bedient
eng = maschine("p2")
eng.warteschlange.anlegen("TEST/USDC", 100.0, 200.0, angaben={"strategy_id": "ALT", "score": 7,
                          "confidence": 0.7, "entry_reason": "alt"})
f = eng.warteauftraege_pruefen({"TEST/USDC": 99.85})
aus["p2_felder"] = felder(f[0][0]) if f else None
aus["p2_status"] = f[0][1].status if f else None

# P3: Kauf ohne Stop (z. B. Handkauf): nichts erfunden
eng = maschine("p3")
r = eng.execute(kauf())
aus["p3_angaben"] = (eng.warteschlange.offene().get("TEST/USDC") or {}).get("angaben")
f = eng.warteauftraege_pruefen({"TEST/USDC": 99.85})
aus["p3_felder"] = felder(f[0][0]) if f else None

# P4: Unbrauchbare Werte (kein Zahlwert, Objekt): Auftrag wird trotzdem angelegt, Datei bleibt JSON
eng = maschine("p4")
k = kauf(); k.stop_loss = "kaputt"; k.trailing_stop_pct = object(); k.agent_id = "signal_agent"
r = eng.execute(k)
try:
    datei = json.load(open(os.path.join(bot, "ws_p4.json"), encoding="utf-8")); lesbar = True
except Exception:
    datei = {}; lesbar = False
aus["p4"] = {"status": r.status, "datei_lesbar": lesbar,
             "angaben": (datei.get("auftraege", {}).get("TEST/USDC") or {}).get("angaben")}

# L1: Live-Pfad, Boersenaufrufe durch Attrappen ersetzt (kein Netz)
wl.stellen = lambda ex, sym, menge, limit, kennung="": ("OID1", None)
wl.status = lambda ex, oid, sym: {"zustand": "gefuellt", "menge": 1.5, "preis": 99.9, "gebuehr": 0.0,
                                   "waehrung": "USDC"}
wl.zuruecknehmen = lambda ex, oid, sym: {"zustand": "weg"}
eng = maschine("l1")
k = kauf(stop_loss=97.85, trailing_stop_pct=1.21, agent_id="signal_agent"); k._evaluation_id = "ev_l1"
from core.events import ExecutionResult
res = ExecutionResult(intent_id=k.id, symbol=k.symbol, side=k.side)
res = eng._warteauftrag_live_anlegen(k, res, None, 1.5, "K1")
aus["l1_anlage"] = {"status": res.status, "angaben": (eng.warteschlange.offene().get("TEST/USDC") or {}).get("angaben")}
f = eng._warteauftraege_live_takt()
aus["l1_felder"] = felder(f[0][0]) if f else None
aus["l1_handel"] = ({"status": f[0][1].status, "preis": f[0][1].avg_fill_price, "menge": f[0][1].filled_qty,
                     "order_id": f[0][1].order_id, "betrag": f[0][0].amount_usd} if f else None)
print(json.dumps(aus, default=str))
'''


def _kopie(ordner: Path, ziel: Path, patchen: bool) -> None:
    import shutil
    from _patchwerkzeug import anwenden
    weg = shutil.ignore_patterns("__pycache__", "*.bak*", "*.sicherung*", "*.pyc")
    for p in PAKETE:
        shutil.copytree(ordner / p, ziel / p, ignore=weg)
    (ziel / "data_store").mkdir()
    if patchen:
        if anwenden(ziel, ERS, MARKE, trocken_kopie=True) != 0:
            raise RuntimeError("Kopie liess sich nicht patchen")


def _lauf(bot: Path, treiber: Path) -> dict:
    import os
    env = dict(os.environ, TI_LOG_FILE=str(bot / "data_store" / "system.log"))   # core/logger.py liest das zuerst
    r = subprocess.run([sys.executable, "-I", str(treiber), str(bot)], cwd=str(bot), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    zeilen = [z for z in r.stdout.splitlines() if z.startswith("{")]
    if r.returncode != 0 or not zeilen:
        raise RuntimeError(f"Treiber Code {r.returncode}: {(r.stderr or r.stdout)[-600:]}")
    return json.loads(zeilen[-1])


def funktionstest(ordner: Path) -> int:
    """Echte ExecutionEngine auf zwei Kopien (alt / gepatcht) im Temp-Ordner, Papier- und Live-Pfad."""
    import tempfile
    fehler = 0
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        treiber = t / "treiber_l14.py"
        treiber.write_text(textwrap.dedent(TREIBER), encoding="utf-8")
        (t / "alt").mkdir(); (t / "neu").mkdir()
        _kopie(ordner, t / "alt", patchen=False)
        _kopie(ordner, t / "neu", patchen=True)
        alt, neu = _lauf(t / "alt", treiber), _lauf(t / "neu", treiber)

    def sage(text, ok, zusatz=""):
        nonlocal fehler
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} {text}" + (f"  ({zusatz})" if zusatz else ""))

    sage("Kopien richtig: alt ungepatcht, neu gepatcht", alt["gepatcht"] is False and neu["gepatcht"] is True)
    a1, n1 = alt["p1_felder"] or {}, neu["p1_felder"] or {}
    sage("Reproduktion: ohne Fix verliert der bediente Kauf Stop und Nachzieh-Abstand",
         a1.get("stop_loss") is None and a1.get("trailing_stop_pct") is None and a1.get("evaluation_id") is None,
         f"alt: stop_loss={a1.get('stop_loss')}, trailing={a1.get('trailing_stop_pct')}")
    sage("Papier: bedienter Kauf traegt stop_loss, trailing_stop_pct, agent_id, risk_reason, Kennung",
         n1.get("stop_loss") == 97.85 and n1.get("trailing_stop_pct") == 1.21 and n1.get("agent_id") == "signal_agent"
         and n1.get("risk_reason") == "genehmigt" and n1.get("evaluation_id") == "ev_p1" and n1.get("take_profit") is None,
         f"neu: {n1.get('stop_loss')}, {n1.get('trailing_stop_pct')}, {n1.get('agent_id')}, {n1.get('evaluation_id')}")
    ang = neu["p1_angaben"] or {}
    sage("Warteschlangen-Datei: neue Angaben als einfache JSON-Werte",
         ang.get("stop_loss") == 97.85 and ang.get("trailing_stop_pct") == 1.21 and ang.get("evaluation_id") == "ev_p1"
         and "take_profit" not in ang, f"{sorted(ang)}")
    sage("bisherige Angaben (Strategie, Score, Konfidenz, Begruendung) unveraendert",
         all(a1.get(k) == n1.get(k) for k in ("strategy_id", "score", "confidence", "entry_reason")))
    sage("Handel gleich: Limit, Preis, Menge, Gebuehr, Schlupf, Kasse, Bestand identisch",
         alt["p1_handel"] is not None and alt["p1_handel"] == neu["p1_handel"],
         f"Preis {neu['p1_handel'] and neu['p1_handel']['preis']}, Gebuehr {neu['p1_handel'] and neu['p1_handel']['gebuehr']}")
    p2 = neu["p2_felder"] or {}
    sage("Alt-Auftrag ohne neue Schluessel: wird bedient, Felder leer wie bisher",
         neu["p2_status"] == "filled" and p2.get("stop_loss") is None and p2.get("evaluation_id") is None
         and p2 == (alt["p2_felder"] or {}), f"Status {neu['p2_status']}")
    p3 = neu["p3_felder"] or {}
    sage("Kauf ohne Stop: nichts erfunden",
         p3.get("stop_loss") is None and p3.get("trailing_stop_pct") is None
         and not any(k in (neu["p3_angaben"] or {}) for k in ("stop_loss", "trailing_stop_pct", "evaluation_id")))
    p4 = neu["p4"]
    sage("Unbrauchbare Werte: Auftrag trotzdem angelegt, Datei lesbar, Feld weggelassen",
         p4["status"] == "wartet" and p4["datei_lesbar"] and "stop_loss" not in (p4["angaben"] or {})
         and "trailing_stop_pct" not in (p4["angaben"] or {}) and (p4["angaben"] or {}).get("agent_id") == "signal_agent",
         f"Status {p4['status']}, Angaben {sorted(p4['angaben'] or {})}")
    l1 = neu["l1_felder"] or {}
    sage("Live-Pfad: Anlegen merkt Stop und Kennung neben live_order_id",
         (neu["l1_anlage"]["angaben"] or {}).get("live_order_id") == "OID1"
         and (neu["l1_anlage"]["angaben"] or {}).get("stop_loss") == 97.85)
    sage("Live-Pfad: bedienter Kauf traegt Stop, Nachzieh-Abstand und Kennung",
         l1.get("stop_loss") == 97.85 and l1.get("trailing_stop_pct") == 1.21 and l1.get("evaluation_id") == "ev_l1")
    sage("Live-Pfad: Handel gleich (Preis, Menge, Order-Kennung, Betrag)",
         alt["l1_handel"] is not None and alt["l1_handel"] == neu["l1_handel"])
    return 1 if fehler else 0


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("v6", "v7"):
        print(__doc__); sys.exit(2)
    name = sys.argv.pop(1)
    if name != "v7":
        print("Nur v7: v6 hat keine Warte-Auftraege und kauft mit dem Original-Intent (Pflichtfelder vollstaendig).")
        sys.exit(2)
    pfad = Path(json.loads((HIER.parent / "instanzen.json").read_text(encoding="utf-8"))["instanzen"][name]["pfad"])
    main(pfad, ERS, MARKE, f"PATCH L14 (vorlaeufig) Befund 88 Warte-Kauf-Felder {name}",
         zusatztest=lambda: funktionstest(pfad))
