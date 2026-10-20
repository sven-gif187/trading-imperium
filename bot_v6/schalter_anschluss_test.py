# -*- coding: utf-8 -*-
"""schalter_anschluss_test.py - belegt den Anschluss der Regel-Schalter (25.09.2026)

WOZU
----
Bis zum 25.09.2026 las der Bot von den acht Eintraegen in regel_modi genau
einen (trend_exit). Die anderen sieben waren Attrappen, und sechs
Schutzregeln waren tot (v7-Befund 118 und 119). Beides ist angeschlossen:
die sieben Schalter wirken, die sechs Schutzregeln laufen im SCHATTEN.

Dieser Test belegt zwei Dinge, und zwar mit dem ECHTEN Code, nicht mit
Suchmustern im Quelltext:

  1. GLEICHHEIT: Bei den heutigen Einstellungen entscheidet der neue Code
     genau wie der alte. Dafuer laeuft derselbe Fall durch die alte Fassung
     (die Sicherung *.vor_schalter_20260925) und durch die neue.
  2. WIRKUNG: SHADOW notiert und greift nicht ein, OFF tut gar nichts,
     ACTIVE greift ein.

NUR LESEND. Schreibt nicht ins echte system.log (Log wird umgebogen), nicht
in telemetrie.db (Notizen gehen an eine Attrappe), nicht in config.json
(Schalterstellungen kommen aus Einmal-Dateien im Temp-Ordner). Es wird
kein Auftrag ausgefuehrt: die Ausfuehrung ist eine Attrappe, die nur
mitschreibt, was verkauft werden sollte.

    python schalter_anschluss_test.py

Rueckgabewert 0 = alle Pruefungen bestanden, 1 = mindestens eine nicht.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
import types

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
os.chdir(HIER)
TMP = tempfile.mkdtemp(prefix="schalter_test_")

# Zuerst das Log umbiegen - alles danach schreibt in die Testdatei.
from core.logger import log                                     # noqa: E402
log._log_file = os.path.join(TMP, "test.log")

import core.regel_schalter as rs                                # noqa: E402
from core.events import DecisionIntent, Side, IntentStatus     # noqa: E402
from config.settings import AppConfig                           # noqa: E402

ERGEBNIS = []


def pruefe(name, ok, detail=""):
    ERGEBNIS.append((name, bool(ok), detail))
    print(f"  [{'OK  ' if ok else 'FEHL'}] {name}" + (f"  ({detail})" if detail else ""))


class FakeTel:
    def __init__(self):
        self.regeln, self.exits = [], []

    def schatten_regel(self, **kw):
        self.regeln.append(kw)

    def schatten_exit(self, **kw):
        self.exits.append(kw)


_zaehler = [0]


def schalter(modi):
    """Ein RegelSchalter mit eigener Einmal-Konfiguration, modulweit angemeldet."""
    _zaehler[0] += 1
    p = os.path.join(TMP, f"cfg_{_zaehler[0]}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"regel_modi": modi}, f)
    s = rs.RegelSchalter(telemetrie=FakeTel(), config_datei=p)
    rs.anmelden(s)
    return s


def lade_alt(name, pfad):
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader(name, os.path.join(HIER, pfad))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


# ======================================================================
print("\n1. Der Schalter selbst")
# ======================================================================
s = schalter({})
alte8 = rs.BEKANNTE_REGELN[:8]
neue6 = rs.BEKANNTE_REGELN[8:]
pruefe("leere regel_modi: die acht alten Regeln stehen auf ACTIVE",
       all(s.modus(r) == rs.ACTIVE for r in alte8))
pruefe("leere regel_modi: die sechs Schutzregeln stehen auf SHADOW",
       all(s.modus(r) == rs.SHADOW for r in neue6), ", ".join(neue6))
s = schalter({"baerenmarkt": "ACTIVE", "smart_entry": "SHADOW", "dca_stufen": "OFF"})
pruefe("ACTIVE -> entscheidet True", rs.entscheidet("baerenmarkt", symbol="X") is True)
pruefe("ACTIVE schreibt keine Notiz", len(s.telemetrie.regeln) == 0)
r1 = rs.entscheidet("smart_entry", symbol="SOL/USDC", haette="h", grund="g")
r2 = rs.entscheidet("smart_entry", symbol="SOL/USDC", haette="h", grund="g")
pruefe("SHADOW -> entscheidet False", r1 is False and r2 is False)
pruefe("SHADOW notiert, gedrosselt: zweimal gefragt, einmal notiert",
       len(s.telemetrie.regeln) == 1, f"{len(s.telemetrie.regeln)} Notiz(en)")
rs.entscheidet("smart_entry", symbol="ETH/USDC", haette="h", grund="g")
pruefe("SHADOW: anderes Symbol wird eigens notiert", len(s.telemetrie.regeln) == 2)
pruefe("OFF -> False und keine Notiz",
       rs.entscheidet("dca_stufen", symbol="X") is False and len(s.telemetrie.regeln) == 2)
s = schalter({"baerenmarkt": "AKTIV"})
pruefe("Tippfehler 'AKTIV' faellt auf die Vorgabe ACTIVE zurueck",
       s.modus("baerenmarkt") == rs.ACTIVE and "baerenmarkt=AKTIV" in s.unbekannt)
rs.anmelden(None)
pruefe("ohne angemeldeten Schalter: Vorgabe (alt ACTIVE, neu SHADOW)",
       rs.entscheidet("baerenmarkt") is True and rs.entscheidet("drawdown_stopp") is False)

# ======================================================================
print("\n2. Regel-Waechter: neue Regeln loesen keinen Alarm aus")
# ======================================================================
from core.regel_waechter import RegelWaechter                    # noqa: E402
import core.regel_waechter as rw_mod                              # noqa: E402
s = schalter({"trend_exit": "SHADOW"})
_soll = os.path.join(TMP, "soll.json")
with open(_soll, "w", encoding="utf-8") as f:     # Referenz im alten Format: 8 Eintraege
    json.dump({"modi": {r: ("SHADOW" if r == "trend_exit" else "ACTIVE") for r in alte8}}, f)
_alt_soll, _alt_cfg = rw_mod.SOLL_DATEI, rw_mod.CONFIG_DATEI
rw_mod.SOLL_DATEI, rw_mod.CONFIG_DATEI = _soll, s.config_datei
try:
    st = RegelWaechter(s, tickets_datei=os.path.join(TMP, "t.txt")).status()
finally:
    rw_mod.SOLL_DATEI, rw_mod.CONFIG_DATEI = _alt_soll, _alt_cfg
pruefe("alte Referenz (8 Regeln) gegen neuen Schalter (14): keine Abweichung",
       st["abweichungen"] == [], str(st["abweichungen"]))

# ======================================================================
print("\n3. Risikopruefung: alte Fassung gegen neue, heutige Einstellungen")
# ======================================================================
cfg = AppConfig.load()
ALT = lade_alt("risk_engine_alt", "risk/engine.py.vor_schalter_20260925")
import risk.engine as NEU                                         # noqa: E402


def absicht(sym, score=7, betrag=100.0, preis=100.0):
    return DecisionIntent(symbol=sym, side=Side.BUY, confidence=0.8,
                          entry_price=preis, amount_usd=betrag, score=score)


def fall(modul, vorbereiten, sym, phase, eq=500.0, score=7):
    eng = modul.RiskEngine(cfg)
    vorbereiten(eng)
    i = eng.check(absicht(sym, score=score), {"total_equity": eq}, phase)
    return i.status, round(i.amount_usd, 6), i.risk_reason


def nichts(e):
    pass


def in_position(e):
    e.open_positions["ETH/USDC"] = {"active": True, "time": time.time()}


def drei_verluste(e):
    e.coin_consecutive_losses["SOL/USDC"] = 3


def notbremse(e):
    e.kill_switch.add_loss(150.0)


FAELLE = [
    ("SOL im MID_BEAR (Baerenmarkt-Regel)", nichts, "SOL/USDC", "MID_BEAR", 7),
    ("BTC im EARLY_BEAR (normaler Kauf)", nichts, "BTC/USDC", "EARLY_BEAR", 7),
    ("ETH bereits in Position", in_position, "ETH/USDC", "EARLY_BEAR", 7),
    ("SOL nach 3 Verlusten, Score 8", drei_verluste, "SOL/USDC", "EARLY_BEAR", 8),
    ("SOL nach 3 Verlusten, Score 4", drei_verluste, "SOL/USDC", "EARLY_BEAR", 4),
    ("Notbremse ausgeloest (150 $ Verlust)", notbremse, "BTC/USDC", "EARLY_BEAR", 7),
]
s = schalter({"trend_exit": "SHADOW"})          # heutiger Stand: alles andere Vorgabe
for name, vorb, sym, phase, score in FAELLE:
    a = fall(ALT, vorb, sym, phase, score=score)
    n = fall(NEU, vorb, sym, phase, score=score)
    gleich = a[0] == n[0] and a[1] == n[1]
    pruefe(f"gleich: {name}", gleich, f"alt {a[0].name} {a[1]} | neu {n[0].name} {n[1]}")

# Drawdown: alt tot, neu im Schatten -> gleiche Entscheidung, aber eine Notiz
eng_a, eng_n = ALT.RiskEngine(cfg), NEU.RiskEngine(cfg)
eng_a.check(absicht("BTC/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
eng_n.check(absicht("BTC/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
n_vor = len(s.telemetrie.regeln)
ia = eng_a.check(absicht("BTC/USDC"), {"total_equity": 400.0}, "EARLY_BEAR")
in_ = eng_n.check(absicht("BTC/USDC"), {"total_equity": 400.0}, "EARLY_BEAR")
pruefe("gleich: 20 % Rueckgang - alt tot, neu im Schatten, beide lassen kaufen",
       ia.status == in_.status == IntentStatus.APPROVED,
       f"alt {ia.status.name} | neu {in_.status.name}")
dd = [x for x in s.telemetrie.regeln[n_vor:] if x["regel"] == "drawdown_stopp"]
pruefe("Schatten: der Drawdown-Stopp hat notiert, was er getan haette",
       len(dd) == 1, dd[0]["grund"] if dd else "keine Notiz")

# ======================================================================
print("\n4. Risikopruefung: SHADOW, OFF und ACTIVE wirken")
# ======================================================================
s = schalter({"baerenmarkt": "SHADOW"})
st_, _, _ = fall(NEU, nichts, "SOL/USDC", "MID_BEAR")
pruefe("baerenmarkt SHADOW: SOL im MID_BEAR wird NICHT mehr blockiert",
       st_ == IntentStatus.APPROVED)
pruefe("baerenmarkt SHADOW: und es gibt eine Notiz",
       any(x["regel"] == "baerenmarkt" for x in s.telemetrie.regeln))
s = schalter({"baerenmarkt": "OFF"})
st_, _, _ = fall(NEU, nichts, "SOL/USDC", "MID_BEAR")
pruefe("baerenmarkt OFF: nicht blockiert, keine Notiz",
       st_ == IntentStatus.APPROVED and not s.telemetrie.regeln)

s = schalter({"drawdown_stopp": "ACTIVE"})
e = NEU.RiskEngine(cfg)
e.check(absicht("BTC/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
i = e.check(absicht("BTC/USDC"), {"total_equity": 400.0}, "EARLY_BEAR")
pruefe("drawdown_stopp ACTIVE: nach 20 % Rueckgang wird gesperrt",
       i.status == IntentStatus.REJECTED and "Drawdown" in i.risk_reason, i.risk_reason)

s = schalter({"verlustsperre_aufhebung": "ACTIVE"})
st8, _, _ = fall(NEU, drei_verluste, "SOL/USDC", "EARLY_BEAR", score=8)
st7, _, r7 = fall(NEU, drei_verluste, "SOL/USDC", "EARLY_BEAR", score=7)
pruefe("verlustsperre_aufhebung ACTIVE: Score 8 hebt die Sperre auf",
       st8 == IntentStatus.APPROVED)
pruefe("verlustsperre_aufhebung ACTIVE: Score 7 bleibt gesperrt",
       st7 == IntentStatus.REJECTED and "Cooldown" in r7)

for modus, erwartet_reset in (("SHADOW", False), ("ACTIVE", True)):
    s = schalter({"notbremse_tagesreset": modus})
    e = NEU.RiskEngine(cfg)
    e.kill_switch.daily_loss = 30.0
    e._notbremse_tag = "2000-01-01"               # gestern
    e.check(absicht("BTC/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
    zurueck = e.kill_switch.daily_loss == 0.0
    pruefe(f"notbremse_tagesreset {modus}: Zaehler "
           f"{'auf 0' if erwartet_reset else 'bleibt 30'}",
           zurueck == erwartet_reset, f"Zaehler {e.kill_switch.daily_loss}")

for modus, erwartet in (("SHADOW", 0), ("ACTIVE", 1)):
    s = schalter({"sammel_notbremse": modus})
    e = NEU.RiskEngine(cfg)
    rufe = []
    e.notbremse_rueckruf = lambda grund: rufe.append(grund)
    e.kill_switch.add_loss(150.0)
    e.check(absicht("BTC/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
    e.check(absicht("ETH/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
    pruefe(f"sammel_notbremse {modus}: Rueckruf {erwartet}x (zwei Pruefungen)",
           len(rufe) == erwartet, f"{len(rufe)}x")

s = schalter({"kill_switch_enabled_test": "egal"})
cfg_aus = AppConfig.load()
cfg_aus.risk.kill_switch_enabled = False
e = NEU.RiskEngine(cfg_aus)
e.kill_switch.add_loss(150.0)
i = e.check(absicht("BTC/USDC"), {"total_equity": 500.0}, "EARLY_BEAR")
pruefe("kill_switch_enabled=false: die Notbremse sperrt nicht mehr (war Attrappe)",
       "Kill-Switch" not in (i.risk_reason or ""), i.risk_reason)


# ======================================================================
print("\n5. Ausstieg: alte Fassung gegen neue, und SHADOW/OFF")
# ======================================================================
EM_ALT = lade_alt("exit_monitor_alt", "runtime/exit_monitor.py.vor_schalter_20260925")
import runtime.exit_monitor as EM_NEU                             # noqa: E402


class FakeApp:
    def __init__(self, schalter_obj, pos, preis):
        self.health = types.SimpleNamespace(heartbeat=lambda *a, **k: None)
        self.risk_engine = types.SimpleNamespace(open_positions={"BTC/USDC": pos})
        self._coin_modes = {}
        self.state = types.SimpleNamespace(get=lambda k, d=None: {"cycle_phase": "EARLY_BEAR"}.get(k, d))
        self.regime_detector = types.SimpleNamespace(current_regime="RANGING")
        self.config = cfg
        self.data_agent = types.SimpleNamespace(price_cache={"BTC/USDC": preis})
        self.multi_tf = types.SimpleNamespace(last_signals={})
        self.telemetrie = FakeTel()
        self.regel_schalter = schalter_obj
        self.verkauft = []

        def _execute(intent):
            self.verkauft.append(intent.strategy_id)
            return types.SimpleNamespace(status="rejected", rejected_reason="Test")
        self.execution = types.SimpleNamespace(execute=_execute)


def position(hoechst_pct):
    return {"active": True, "qty": 1.0, "entry_price": 100.0, "mode": "SL",
            "highest_price": 100.0 * (1 + hoechst_pct / 100),
            "hoechst_pnl_pct": hoechst_pct, "position_id": "pos_TEST"}


def ausstieg(modul, schalter_obj, hoechst_pct, preis):
    app = FakeApp(schalter_obj, position(hoechst_pct), preis)
    modul.ExitMonitor(app).sl_tp_monitor()
    return (app.verkauft[0] if app.verkauft else None), app.telemetrie.exits


AUSSTIEGE = [
    ("Trailing: Hoch +5 %, jetzt 102", 5.0, 102.0),
    ("Breakeven: Hoch +1,1 %, jetzt 100,30", 1.1, 100.30),
    ("nichts: Hoch +0,6 %, jetzt 100,50", 0.6, 100.50),
    ("Stop-Loss: jetzt 97", 0.0, 97.0),
]
s_heute = schalter({"trend_exit": "SHADOW"})
for name, hoch, preis in AUSSTIEGE:
    a, _ = ausstieg(EM_ALT, s_heute, hoch, preis)
    n, _ = ausstieg(EM_NEU, s_heute, hoch, preis)
    pruefe(f"gleich: {name}", a == n, f"alt {a} | neu {n}")

s = schalter({"trailing_leiter": "SHADOW"})
n, ex = ausstieg(EM_NEU, s, 5.0, 102.0)
pruefe("trailing_leiter SHADOW: kein Trailing-Verkauf, aber eine Notiz",
       n != "TRAILING_STOP" and any(x.get("regel") == "TRAILING_STOP" for x in ex),
       f"Verkauf {n}, Notizen {[x.get('regel') for x in ex]}")
s = schalter({"trailing_leiter": "OFF"})
n, ex = ausstieg(EM_NEU, s, 5.0, 102.0)
pruefe("trailing_leiter OFF: kein Trailing-Verkauf, keine Trailing-Notiz",
       n != "TRAILING_STOP" and not any(x.get("regel") == "TRAILING_STOP" for x in ex))
s = schalter({"breakeven_sperre": "SHADOW"})
n, ex = ausstieg(EM_NEU, s, 1.1, 100.30)
pruefe("breakeven_sperre SHADOW: kein Breakeven-Verkauf, aber eine Notiz",
       n != "BREAKEVEN_LOCK" and any(x.get("regel") == "BREAKEVEN_LOCK" for x in ex),
       f"Verkauf {n}")
s = schalter({"trailing_leiter": "OFF"})
n, _ = ausstieg(EM_NEU, s, 1.25, 100.30)
pruefe("trailing OFF: die Breakeven-Sperre bekommt im selben Durchlauf ihre Chance",
       n == "BREAKEVEN_LOCK", f"Verkauf {n}")

# ======================================================================
print("\n6. app.py: die zwei neuen Helfer und die Schalterstellen")
# ======================================================================
import app as APP                                                 # noqa: E402
import threading                                                  # noqa: E402

# 6a Sammel-Notbremse: erst schliessen, dann EVENT_KILL_SWITCH senden
_ereignisse = []
_fertig = threading.Event()


def _schliessen():
    _ereignisse.append("geschlossen")
    return 2


def _senden(ev, daten, source=""):
    _ereignisse.append((ev, daten.get("reason")))
    _fertig.set()


fake = types.SimpleNamespace(_close_all_positions_safety=_schliessen,
                             bus=types.SimpleNamespace(publish=_senden))
APP.TradingImperiumV6._sammel_notbremse_ausfuehren(fake, "Test-Grund")
_fertig.wait(5)
pruefe("Sammel-Notbremse: erst alle Positionen schliessen, dann EVENT_KILL_SWITCH",
       _ereignisse == ["geschlossen", (APP.EVENT_KILL_SWITCH, "Test-Grund")],
       str(_ereignisse))

# 6b Echte Tageskurse (oeffentliche Binance-Daten, kein Schluessel)
import ccxt                                                       # noqa: E402
_abrufe = [0]
_client = ccxt.binance({"enableRateLimit": True})
_orig = _client.fetch_ohlcv


def _zaehlend(*a, **k):
    _abrufe[0] += 1
    return _orig(*a, **k)


_client.fetch_ohlcv = _zaehlend
fake = types.SimpleNamespace(data_agent=types.SimpleNamespace(client=_client))
k1 = APP.TradingImperiumV6._nupl_tageskurse(fake)
k2 = APP.TradingImperiumV6._nupl_tageskurse(fake)
pruefe("NUPL: 200 echte Tageskurse BTC/USDC geholt",
       bool(k1) and len(k1) == 200, f"{len(k1) if k1 else 0} Kurse")
pruefe("NUPL: zweiter Aufruf holt nicht neu (einmal je 24 h)", _abrufe[0] == 1,
       f"{_abrufe[0]} Abruf(e)")
if k1:
    sma = sum(k1) / len(k1)
    kurs = k1[-1]
    echt = (kurs - sma) / kurs
    ersatz = (kurs - 0.8 * kurs) / kurs
    print(f"      echter 200-Tage-Schnitt {sma:,.2f} | letzter Tageskurs {kurs:,.2f}"
          f" | NUPL echt {echt:+.3f} gegen Ersatz beim Start {ersatz:+.3f}")


class _Kaputt:
    def fetch_ohlcv(self, *a, **k):
        raise RuntimeError("Netz weg (Test)")


fake = types.SimpleNamespace(data_agent=types.SimpleNamespace(client=_Kaputt()))
pruefe("NUPL: Netzfehler -> None, bisheriger Ersatzwert bleibt",
       APP.TradingImperiumV6._nupl_tageskurse(fake) is None)

# 6c Jede der sieben Regeln wird an mindestens einer Stelle gefragt. Das ist
# eine Quelltext-Pruefung - sie belegt den ANSCHLUSS, nicht das Verhalten.
# Das Verhalten der Stellen in app.py zeigt erst der Lauf nach dem Neustart.
import ast                                                        # noqa: E402
_gefragt = set()
for _datei in ("app.py", "risk/engine.py", "runtime/exit_monitor.py"):
    for _n in ast.walk(ast.parse(open(_datei, encoding="utf-8").read())):
        if isinstance(_n, ast.Call) and _n.args and isinstance(_n.args[0], ast.Constant):
            _f = getattr(_n.func, "id", getattr(_n.func, "attr", ""))
            if _f in ("_entscheidet", "entscheidet", "wirkt", "schreibt_mit",
                      "_regel_wirkt", "_regel_schatten"):
                _gefragt.add(_n.args[0].value)
_fehlt = [r for r in rs.BEKANNTE_REGELN if r not in _gefragt]
pruefe("alle 14 Regeln werden im Code gefragt", not _fehlt,
       "fehlt: " + ", ".join(_fehlt) if _fehlt else "14 von 14")

# ======================================================================
fehl = [e for e in ERGEBNIS if not e[1]]
print(f"\n{len(ERGEBNIS) - len(fehl)} von {len(ERGEBNIS)} Pruefungen bestanden.")
print(f"(Testlog: {log._log_file})")
sys.exit(1 if fehl else 0)
