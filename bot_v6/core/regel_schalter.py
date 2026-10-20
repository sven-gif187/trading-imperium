# -*- coding: utf-8 -*-
"""Trading Imperium V6 - Dreifach-Schalter fuer Regeln (Aufgabe 3, 11.08.2026).

DAS PROBLEM
-----------
Jede Regel im Bot ist einfach AN. Die Baerenmarkt-Regel blockiert Kaeufe,
die Breakeven-Sperre zieht den Stop nach, die Wiedereinstiegs-Sperre
verhindert schnelle Rueckkaeufe. Ob sie nuetzen, weiss niemand - um das
herauszufinden, muesste man sie abschalten und zusehen.

DIE DREI ZUSTAENDE
------------------
  ACTIVE   Die Regel entscheidet mit. Genau wie heute.
  SHADOW   Die Regel rechnet, schreibt auf was sie TUN WUERDE, handelt aber
           nicht. Die Notiz landet in telemetrie.db (Tabelle schatten_regeln).
  OFF      Die Regel laeuft gar nicht und schreibt auch nichts.

Vorbild: TREND_EXIT_SCHATTEN in runtime/exit_monitor.py und
features/regime_adaptiv.py.

WICHTIG - SHADOW IST NICHT GRATIS
---------------------------------
Der Schalter EINZUBAUEN aendert nichts: Vorgabe ist ueberall ACTIVE, also
das heutige Verhalten. Aber eine Regel auf SHADOW zu stellen, aendert sehr
wohl etwas - sie hoert auf zu wirken:

  Regeln die BLOCKIEREN (Baerenmarkt, Smart-Entry, Wiedereinstiegs-Sperre):
      im Schatten wird NICHT mehr blockiert -> der Bot kauft Dinge, die er
      sonst abgelehnt haette.
  Regeln die HANDELN (Trailing-Leiter, Breakeven-Sperre, DCA-Stufen):
      im Schatten wird NICHT mehr gehandelt -> Positionen laufen weiter, wo
      sonst der Stop gezogen haette.

Wir sind im Papiermodus, es kostet also kein echtes Geld. Aber man bezahlt
die Erkenntnis mit einer Zeit lang schlechteren Entscheidungen. Das muss je
Regel einzeln gewollt sein, nicht pauschal.

EINSTELLEN
----------
In data_store/config.json:

    "regel_modi": {
        "trend_exit": "SHADOW",
        "baerenmarkt": "ACTIVE"
    }

Fehlt ein Eintrag oder steht Unsinn drin, gilt ACTIVE - im Zweifel das
heutige Verhalten. Ein Tippfehler darf nie versehentlich eine Regel
abschalten.

VERWENDUNG IM CODE
------------------
    from core.regel_schalter import RegelSchalter, ACTIVE, SHADOW

    schalter = RegelSchalter(telemetrie=self.telemetrie)

    if schalter.wirkt("baerenmarkt"):
        return "blockiert"                      # Regel greift
    schalter.notieren("baerenmarkt", symbol=sym, haette="BUY blockiert",
                      grund="nur BTC+ETH im Baerenmarkt", preis=kurs)
    # ... und der Kauf laeuft weiter

`wirkt()` ist die einzige Frage, die der Aufrufer stellen muss. Sie ist
True bei ACTIVE und False bei SHADOW und OFF. `notieren()` schreibt nur im
Zustand SHADOW - bei ACTIVE und OFF tut es nichts, der Aufrufer muss also
nicht selbst unterscheiden.
"""
import json
import os
import threading
import time

try:
    from config.settings import DATA_DIR
except Exception:                                    # Notfall-Pfad
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data_store")

try:
    from core.logger import log
except Exception:                                    # Notfall-Pfad (Tests)
    class _L:
        def info(self, m, s): print(f"[{m}] {s}")
        def warn(self, m, s): print(f"[{m}] {s}")
        def error(self, m, s): print(f"[{m}] {s}")
    log = _L()

ACTIVE = "ACTIVE"
SHADOW = "SHADOW"
OFF = "OFF"
ERLAUBT = (ACTIVE, SHADOW, OFF)

# Alle Regeln, die der Schalter kennt. Die Liste ist bewusst fest: so faellt
# ein Tippfehler im Schluessel sofort auf, statt still ins Leere zu laufen.
BEKANNTE_REGELN = (
    "trend_exit",             # Ausstieg bei MTF-Baerisch und PnL < -1 %
    "baerenmarkt",            # im Baerenmarkt nur BTC+ETH kaufen
    "breakeven_sperre",       # Stop auf Einstand ziehen ab +1 %
    "trailing_leiter",        # gestaffeltes Nachziehen des Stops
    "smart_entry",            # Einstieg verzoegern und auf besseren Kurs warten
    "wiedereinstieg_sperre",  # 90 min kein Rueckkauf nach Exit
    "dca_stufen",             # gestaffelter Nachkauf
    "meta_voting",            # Gewichtung der Agenten-Stimmen
    # [25.09.2026] Sechs Schutzregeln, die bisher NIE gewirkt haben
    # (v7-Befund 119, in v6 genauso nachgesehen). Sie werden zuerst im
    # SCHATTEN angeschlossen: sie rechnen und notieren, was sie getan
    # haetten, greifen aber nicht ein. Scharf erst nach Beleg und mit
    # eigener Epochengrenze. Sven am 25.09.: "es hat ja einen grund und
    # sinn das wir das drinnen haben, bzw teste und belege es".
    "drawdown_stopp",          # keine Kaeufe ab max_drawdown_pct Rueckgang
    "notbremse_tagesreset",    # Verlustzaehler der Notbremse um 00:00 UTC auf null
    "verlustsperre_aufhebung", # Verlustserien-Sperre bei hohem Score aufheben
    "auto_verteidigung",       # im Abwaertstrend die 2 schlechtesten verkaufen
    "nupl_bremse",             # NUPL aus echtem 200-Tage-Schnitt statt Ersatzwert
    "sammel_notbremse",        # bei ausgeloester Notbremse alles schliessen
)

# Was gilt, wenn ein Eintrag fehlt oder Unsinn enthaelt: immer das HEUTIGE
# Verhalten. Die acht alten Regeln wirken heute -> ACTIVE. Die sechs
# Schutzregeln wirkten bisher nie -> SHADOW. Mit ACTIVE als Vorgabe haette
# ein vergessener Eintrag sie still scharf geschaltet - z. B. einen
# ungemessenen Drawdown-Stopp, der ab 15 % Rueckgang seit dem Programmstart
# alle Kaeufe sperrt. (Nicht "sofort": der Hoechststand beginnt bei jedem
# Start bei 0, alte Rueckgaenge zaehlen nicht - risk/drawdown_guard.py:15.)
VORGABE = {r: ACTIVE for r in BEKANNTE_REGELN}
VORGABE.update({
    "drawdown_stopp": SHADOW,
    "notbremse_tagesreset": SHADOW,
    "verlustsperre_aufhebung": SHADOW,
    "auto_verteidigung": SHADOW,
    "nupl_bremse": SHADOW,
    "sammel_notbremse": SHADOW,
})


def vorgabe(regel):
    """Zustand einer Regel, wenn nichts eingestellt ist."""
    return VORGABE.get(str(regel), ACTIVE)


class RegelSchalter:
    """Liest die Zustaende und nimmt die Schatten-Notizen entgegen."""

    def __init__(self, telemetrie=None, config_datei=None):
        self.telemetrie = telemetrie
        self.config_datei = config_datei or os.path.join(DATA_DIR, "config.json")
        self._lock = threading.Lock()
        self.notiert = 0
        self.unbekannt = set()
        self.modi = self._laden()

    # ------------------------------------------------------------------
    def _laden(self):
        """Liest die Zustaende. Jeder Fehler endet bei der VORGABE."""
        modi = {r: vorgabe(r) for r in BEKANNTE_REGELN}
        try:
            if os.path.exists(self.config_datei):
                with open(self.config_datei, "r", encoding="utf-8") as f:
                    roh = json.load(f).get("regel_modi", {}) or {}
                for name, wert in roh.items():
                    if name not in BEKANNTE_REGELN:
                        self.unbekannt.add(name)
                        continue
                    wert = str(wert).strip().upper()
                    if wert in ERLAUBT:
                        modi[name] = wert
                    else:
                        self.unbekannt.add(f"{name}={wert}")
        except Exception:
            pass          # kaputte Datei -> ueberall VORGABE, also heutiges Verhalten
        return modi

    def neu_laden(self):
        """Zustaende erneut von der Platte lesen (ohne Neustart)."""
        with self._lock:
            self.unbekannt = set()
            self.modi = self._laden()
        return dict(self.modi)

    # ------------------------------------------------------------------
    def modus(self, regel):
        """Zustand einer Regel. Unbekannte Regel -> ihre VORGABE."""
        return self.modi.get(str(regel), vorgabe(regel))

    def wirkt(self, regel):
        """True = die Regel darf entscheiden. False = SHADOW oder OFF.

        Das ist die einzige Frage, die der Aufrufer stellen muss.
        """
        return self.modus(regel) == ACTIVE

    def schreibt_mit(self, regel):
        """True = im Schattenmodus, es wird nur notiert."""
        return self.modus(regel) == SHADOW

    # ------------------------------------------------------------------
    def notieren(self, regel, symbol="", haette="", grund="", preis=None,
                 pnl_pct=None, position_id="", zusatz=""):
        """Haelt fest, was die Regel getan haette. Nur im Zustand SHADOW.

        Bei ACTIVE und OFF passiert nichts - der Aufrufer muss also nicht
        selbst pruefen. Wirft nie nach aussen: ein Protokollfehler darf eine
        Handelsentscheidung nicht stoeren.
        """
        if self.modus(regel) != SHADOW:
            return False
        try:
            if self.telemetrie is not None:
                self.telemetrie.schatten_regel(
                    regel=regel, symbol=symbol, haette=haette, grund=grund,
                    preis=preis, pnl_pct=pnl_pct, position_id=position_id,
                    zusatz=zusatz)
            self.notiert += 1
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    def status(self):
        """Diagnose - gehoert in den Systemstatus und ins Startlog."""
        return {
            "modi": dict(self.modi),
            "nicht_aktiv": [r for r, m in self.modi.items() if m != ACTIVE],
            "notiert_diese_sitzung": self.notiert,
            "unbekannte_eintraege": sorted(self.unbekannt),
            "datei": self.config_datei,
        }

    def startmeldung(self):
        """Eine Zeile fuers Log. Schweigt, wenn alles auf ACTIVE steht.

        Absicht: Wer eine Regel nicht scharf hat, MUSS das im Log sehen.
        Sonst wundert sich in drei Wochen jemand ueber die Zahlen und
        niemand erinnert sich, dass da noch ein Schalter stand.
        """
        aus = [f"{r}={m}" for r, m in sorted(self.modi.items()) if m != ACTIVE]
        if not aus:
            return ""
        return "NICHT scharf: " + ", ".join(aus)


# ======================================================================
# [25.09.2026] Modulweiter Zugriff - damit der Schalter endlich GELESEN wird
# ======================================================================
# Bis heute fragte genau EINE Stelle im ganzen Bot den Schalter ab:
# runtime/exit_monitor.py fuer trend_exit. Die anderen sieben Eintraege in
# regel_modi waren Attrappen - wer "baerenmarkt" auf OFF stellte, aenderte
# nichts (v7-Befund 118, Ergaenzung zu Befund 11). Ein Grund dafuer: die
# Regeln sitzen teils in Modulen ohne Zugriff auf die App (risk/engine.py).
# app.py meldet deshalb den einen Schalter hier an, und jede Regelstelle
# stellt dieselbe Frage: entscheidet(regel, ...).

_AKTUELL = None
_ZULETZT = {}
_ZULETZT_LOCK = threading.Lock()


def anmelden(schalter):
    """app.py meldet den einen RegelSchalter an. Ein zweiter Aufruf ersetzt ihn."""
    global _AKTUELL
    _AKTUELL = schalter
    with _ZULETZT_LOCK:
        _ZULETZT.clear()


def aktueller():
    return _AKTUELL


def entscheidet(regel, symbol="", haette="", grund="", preis=None,
                pnl_pct=None, position_id="", zusatz="", sperre_s=3600):
    """Die eine Frage an jeder Regelstelle: darf die Regel jetzt eingreifen?

      ACTIVE  -> True. Die Regel greift, genau wie bisher.
      SHADOW  -> False. Es wird notiert, was sie getan HAETTE (Tabelle
                 schatten_regeln + eine Logzeile) - hoechstens einmal je
                 Regel und Symbol in `sperre_s` Sekunden. Ohne diese Drossel
                 schriebe der 12-s-Takt dieselbe Notiz tausendfach am Tag.
      OFF     -> False, keine Notiz.

    Ohne angemeldeten Schalter (Tests, Werkzeuge) gilt die VORGABE der
    Regel, also das heutige Verhalten.
    """
    s = _AKTUELL
    modus = s.modus(regel) if s is not None else vorgabe(regel)
    if modus == ACTIVE:
        return True
    if modus != SHADOW:
        return False
    schluessel = (str(regel), str(symbol))
    jetzt = time.time()
    with _ZULETZT_LOCK:
        if jetzt - _ZULETZT.get(schluessel, 0.0) < sperre_s:
            return False
        _ZULETZT[schluessel] = jetzt
    log.info("SCHATTEN", f"{regel}{' ' + symbol if symbol else ''}: haette "
                         f"{haette} ({grund})"[:300])
    if s is not None:
        s.notieren(regel, symbol=symbol, haette=haette, grund=grund,
                   preis=preis, pnl_pct=pnl_pct, position_id=position_id,
                   zusatz=zusatz)
    return False
