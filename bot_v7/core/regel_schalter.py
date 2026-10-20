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

try:
    from config.settings import DATA_DIR
except Exception:                                    # Notfall-Pfad
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data_store")

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
)


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
        """Liest die Zustaende. Jeder Fehler endet bei ACTIVE."""
        modi = {r: ACTIVE for r in BEKANNTE_REGELN}
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
            pass          # kaputte Datei -> ueberall ACTIVE, also heutiges Verhalten
        return modi

    def neu_laden(self):
        """Zustaende erneut von der Platte lesen (ohne Neustart)."""
        with self._lock:
            self.unbekannt = set()
            self.modi = self._laden()
        return dict(self.modi)

    # ------------------------------------------------------------------
    def modus(self, regel):
        """Zustand einer Regel. Unbekannte Regel -> ACTIVE."""
        return self.modi.get(str(regel), ACTIVE)

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
