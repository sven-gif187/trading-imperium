# -*- coding: utf-8 -*-
"""Trading Imperium V6 - Sauberer V6-Lernzaehler (Variante C, 11.08.2026).

WARUM ES DIESE DATEI GIBT
-------------------------
data_store/brain_performance.json ist mit V4-Altdaten vorbefuellt
(`source: v4_bootstrap`). Am 27.07.2026 wurde deshalb beschlossen, sie im
Cockpit NICHT anzuzeigen - "V4-verseucht" (ENTWICKLERHANDBUCH.md:1419). Der
schon am 25.06.2026 notierte Folgeauftrag "Brain-Scrub (v4_baseline
rausrechnen)" (ENTWICKLERHANDBUCH.md:444) wurde nie erledigt.

Beispiel fuer das Problem: DCA_FEAR_GREED steht dort mit 320 Trades und
91,25 % Trefferquote. Darin steckt eine V4-Grundlast, die als nicht
verwendbar eingestuft wurde. Wer neue V6-Ergebnisse einfach dazuaddiert,
bekommt eine Zahl, die weder V4 noch V6 ist - und die ueber den
Strategie-Score echte Kaufentscheidungen beeinflusst.

WAS DIESE DATEI TUT
-------------------
Sie zaehlt ab dem 11.08.2026 NEU und AUSSCHLIESSLICH mit, was V6 selbst
erlebt hat - Gewinne UND Verluste. Die alte Datei bleibt unberuehrt und
dient weiter als Beweisstueck.

WAS SIE AUSDRUECKLICH NICHT TUT
-------------------------------
Sie beeinflusst KEINE Handelsentscheidung. Niemand liest sie im
Entscheidungspfad. Sie sammelt, bis genug Faelle da sind; ueber eine
spaetere Umstellung des Strategie-Scores entscheidet der Eigentuemer
gesondert. Das Format ist deshalb absichtlich identisch zur alten Datei -
eine spaetere Umstellung ist ein Pfadwechsel, kein Umbau.

SICHERHEITSREGELN
-----------------
- Wirft niemals nach aussen. Ein Zaehlfehler darf einen bereits
  ausgefuehrten Verkauf nie gefaehrden.
- Schreibt atomar (Temp-Datei + os.replace). Ein Absturz mitten im
  Schreiben kann die Datei nicht halb beschrieben zuruecklassen - genau
  dieser Schaden hat am 04.08.2026 die ersten 68 KB des
  ENTWICKLERHANDBUCHs vernichtet.
- Abschalter: config.json -> "lern_journal_v6_enabled": false schaltet
  still ab, ohne Codeaenderung.
- Mindestdatenmenge: ist_belastbar() sagt Nein, solange zu wenige Faelle
  vorliegen. Keine Auswertung auf duenner Datenlage.
"""
import json
import os
import threading
from datetime import datetime, timezone

try:
    from config.settings import DATA_DIR
except Exception:                                    # Notfall-Pfad
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data_store")

DATEI = os.path.join(DATA_DIR, "brain_performance_v6.json")

# Ab so vielen Verkaeufen je Strategie gilt eine Zahl als belastbar.
# Bewusst konservativ: bei n=10 schwankt eine Trefferquote noch um
# zweistellige Prozentpunkte. Vorbild ist das n>=20-Gate des
# Forschungsprogramms.
MIN_FAELLE = 20


_JOURNAL = None
_JOURNAL_LOCK = threading.Lock()


def hole_journal():
    """Liefert das eine gemeinsame Journal. Wirft nie, liefert notfalls None.

    Bewusst als Singleton: sonst haetten app.py-Pfad und exit_monitor-Pfad
    je einen eigenen Zaehler mit eigenem Dateizugriff - und zwei Prozesse
    auf derselben Datei waren am 07.08.2026 die Ursache von WinError 5.
    """
    global _JOURNAL
    if _JOURNAL is None:
        with _JOURNAL_LOCK:
            if _JOURNAL is None:
                try:
                    tel = None
                    try:
                        from core.telemetrie import Telemetrie
                        tel = Telemetrie()
                    except Exception:
                        tel = None          # JSON-Zaehler laeuft auch ohne DB
                    _JOURNAL = LernJournalV6(telemetrie=tel)
                except Exception:
                    return None
    return _JOURNAL


class LernJournalV6:
    """Zaehlt V6-Verkaufsergebnisse sauber und getrennt mit."""

    def __init__(self, datei=None, telemetrie=None, aktiv=None):
        self.datei = datei or DATEI
        self.telemetrie = telemetrie
        self._lock = threading.Lock()
        self.gebucht = 0
        self.fehler = 0
        self.aktiv = self._schalter_lesen() if aktiv is None else bool(aktiv)
        self.performance = self._laden()

    # ------------------------------------------------------------------
    # Schalter
    # ------------------------------------------------------------------
    @staticmethod
    def _schalter_lesen():
        """Abschalter aus config.json. Fehlt der Schluessel, ist es AN.

        [KORREKTUR 11.08.2026] Die erste Fassung suchte config.json im
        Hauptordner. Sie liegt aber in data_store/. Der Abschalter waere
        also wirkungslos gewesen - still, ohne Fehlermeldung. Genau die
        Sorte Fehler, die man erst bemerkt, wenn man ihn braucht.
        Deshalb jetzt beide Orte, data_store zuerst.
        """
        for pfad in (os.path.join(DATA_DIR, "config.json"),
                     os.path.join(os.path.dirname(DATA_DIR), "config.json")):
            try:
                if os.path.exists(pfad):
                    with open(pfad, "r", encoding="utf-8") as f:
                        return bool(json.load(f).get("lern_journal_v6_enabled", True))
            except Exception:
                continue
        return True

    # ------------------------------------------------------------------
    # Lesen / Schreiben
    # ------------------------------------------------------------------
    def _laden(self):
        try:
            if os.path.exists(self.datei):
                with open(self.datei, "r", encoding="utf-8") as f:
                    return json.load(f).get("performance", {}) or {}
        except Exception:
            self.fehler += 1
        return {}

    def _speichern(self):
        """Atomar schreiben: erst daneben, dann umbenennen."""
        tmp = self.datei + ".tmp"
        payload = {
            "hinweis": ("Reiner V6-Zaehler ab 11.08.2026. Enthaelt KEINE "
                        "V4-Altdaten. Beeinflusst keine Handelsentscheidung."),
            "saved_at": datetime.now().astimezone().isoformat(),
            "zaehlt_seit": self._zaehlt_seit(),
            "performance": self.performance,
            "total_strategies": len(self.performance),
            "total_trades": sum(p.get("trades", 0) for p in self.performance.values()),
        }
        os.makedirs(os.path.dirname(self.datei), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.datei)

    def _zaehlt_seit(self):
        werte = [p.get("erster_ts") for p in self.performance.values()
                 if p.get("erster_ts")]
        return min(werte) if werte else None

    # ------------------------------------------------------------------
    # Hauptzugang
    # ------------------------------------------------------------------
    def buchen(self, strategie, pnl, quelle="", symbol="", position_id=""):
        """Verbucht EIN Verkaufsergebnis. Gibt True/False zurueck, wirft nie.

        Gezaehlt wird bei JEDEM Ausgang - auch bei Verlust und bei exakt
        null. Genau das war der Fehler B1 (app.py): dort standen die
        Lern-Aufrufe in einem "if pnl > 0"-Block, weshalb ein Zaehler
        entstand, der Verluste nie hochzaehlen KONNTE.
        """
        if not self.aktiv:
            return False
        try:
            sid = str(strategie or "UNBEKANNT")[:80]
            wert = float(pnl)
        except Exception:
            self.fehler += 1
            return False

        try:
            jetzt = datetime.now(timezone.utc).isoformat()
            with self._lock:
                p = self.performance.setdefault(sid, {
                    "trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0,
                    "win_rate": 0.0, "erster_ts": jetzt, "letzter_ts": jetzt,
                    "quellen": {},
                })
                p["trades"] += 1
                if wert > 0:
                    p["wins"] += 1
                else:
                    p["losses"] = p.get("losses", 0) + 1
                p["total_pnl"] = round(p.get("total_pnl", 0.0) + wert, 6)
                p["win_rate"] = round(p["wins"] / p["trades"] * 100, 2)
                p["letzter_ts"] = jetzt
                p.setdefault("erster_ts", jetzt)
                q = p.setdefault("quellen", {})
                schluessel = str(quelle or "unbekannt")[:40]
                q[schluessel] = q.get(schluessel, 0) + 1
                self._speichern()
            self.gebucht += 1
        except Exception:
            self.fehler += 1
            return False

        # Rohspur in die Telemetrie-DB. Bewusst NACH der JSON-Buchung und
        # eigenstaendig gekapselt: faellt die DB aus, bleibt der Zaehler
        # trotzdem korrekt.
        try:
            if self.telemetrie is not None:
                self.telemetrie.lern_ereignis(
                    strategie=sid, pnl_usd=wert, quelle=quelle,
                    symbol=symbol, position_id=position_id)
        except Exception:
            pass
        return True

    # ------------------------------------------------------------------
    # Auswertung
    # ------------------------------------------------------------------
    def ist_belastbar(self, strategie, min_faelle=MIN_FAELLE):
        """Sagt Nein, solange zu wenige Faelle vorliegen."""
        try:
            return self.performance.get(str(strategie), {}).get("trades", 0) >= min_faelle
        except Exception:
            return False

    def status(self):
        """Diagnose - taucht im Systemstatus auf."""
        gesamt = sum(p.get("trades", 0) for p in self.performance.values())
        return {
            "aktiv": self.aktiv,
            "datei": self.datei,
            "strategien": len(self.performance),
            "faelle_gesamt": gesamt,
            "gewinne": sum(p.get("wins", 0) for p in self.performance.values()),
            "verluste": sum(p.get("losses", 0) for p in self.performance.values()),
            "gebucht_diese_sitzung": self.gebucht,
            "fehler": self.fehler,
            "zaehlt_seit": self._zaehlt_seit(),
            "belastbare_strategien": [s for s in self.performance
                                      if self.ist_belastbar(s)],
        }
