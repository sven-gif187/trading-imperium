# -*- coding: utf-8 -*-
"""
risk/reentry_guard.py - Wiedereinstiegs-Sperre  [E9-CHURN 29.07.2026]
=====================================================================
WARUM ES DIESE DATEI GIBT (Messung, nicht Meinung):

  Auswertung von data_store/trades_v5.json, 944 Eintraege, Stand 29.07.:
    * 338 Wiederkaeufe desselben Coins innerhalb von 15 Minuten nach
      einem Verkauf.
    * Davon 319 (94 %) zu einem HOEHEREN Preis als der Verkauf.
    * Median-Aufschlag beim Wiederkauf: +0.102 %.
  Jede dieser Runden kostet ~0.20 % Gebuehr + ~0.10 % Slippage +
  ~0.10 % schlechteren Einstieg = ~0.4 % vom Umsatz. Auf ~18.600 $
  gedrehtes Volumen sind das rund 70 $ - bei einem Gesamtergebnis
  von -27.57 $ ist das ALLEIN der Unterschied zwischen Plus und Minus.

  Ursache: der DCA-Pfad in app.py kennt nur einen Cooldown seit dem
  letzten KAUF (AdvancedDCA.record_dca). Nach einem Trailing-Exit ist
  die Position geloescht, der Kauf-Cooldown laengst abgelaufen -> der
  naechste Tick kauft sofort wieder ein, oft Sekunden spaeter.

REGELN (beide muessen erfuellt sein, sonst kein Wiedereinstieg):
  1. ZEIT:  mindestens `sperr_minuten` seit dem Exit.
  2. PREIS: innerhalb `preisfenster_stunden` nach dem Exit nur, wenn
            der Preis mindestens `mindest_abschlag_pct` UNTER dem
            Exit-Preis liegt. Wer bei 64.019 verkauft, kauft nicht bei
            64.132 zurueck.

Neustart-fest: Zustand liegt in data_store/reentry_guard.json.
Greift NUR bei Kaeufen. Verkaeufe werden nie blockiert.
"""
import os
import json
import time

try:
    from core.logger import log
except Exception:                                   # Testbarkeit ohne Bot
    class _L:
        def info(self, m, s): print(f"[{m}] {s}")
        def warn(self, m, s): print(f"[{m}] {s}")
        def error(self, m, s): print(f"[{m}] {s}")
    log = _L()


def _store(name):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data_store", name)


class ReentryGuard:
    """Sperrt den Wiedereinstieg in einen gerade verlassenen Coin."""

    def __init__(self, sperr_minuten=90, preisfenster_stunden=6,
                 mindest_abschlag_pct=1.0, pfad=None):
        self.sperr_minuten = float(sperr_minuten)
        self.preisfenster_stunden = float(preisfenster_stunden)
        self.mindest_abschlag_pct = float(mindest_abschlag_pct)
        self.pfad = pfad or _store("reentry_guard.json")
        self._exits = {}            # symbol -> {"zeit": epoch, "preis": float, "grund": str}
        self._laden()

    # ---------- Persistenz ----------
    def _laden(self):
        try:
            with open(self.pfad, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                self._exits = {k: v for k, v in d.items() if isinstance(v, dict)}
        except Exception:
            self._exits = {}

    def _speichern(self):
        try:
            os.makedirs(os.path.dirname(self.pfad), exist_ok=True)
            tmp = self.pfad + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._exits, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.pfad)
        except Exception:
            pass

    # ---------- Schreiben ----------
    def notiere_exit(self, symbol, exit_preis, grund=""):
        """Nach JEDEM Verkauf aufrufen - egal ueber welchen Pfad."""
        try:
            p = float(exit_preis or 0)
        except Exception:
            p = 0.0
        if p <= 0:
            return
        self._exits[symbol] = {"zeit": time.time(), "preis": p, "grund": str(grund)[:80]}
        self._speichern()

    # ---------- Lesen ----------
    def darf_kaufen(self, symbol, aktueller_preis):
        """(bool, grund) - False = Kauf blockieren."""
        e = self._exits.get(symbol)
        if not e:
            return True, ""
        try:
            alter_min = (time.time() - float(e.get("zeit", 0))) / 60.0
            exit_preis = float(e.get("preis", 0))
            preis = float(aktueller_preis or 0)
        except Exception:
            return True, ""

        if alter_min >= self.preisfenster_stunden * 60:
            # Fenster abgelaufen - Sperre verfaellt komplett
            self._exits.pop(symbol, None)
            self._speichern()
            return True, ""

        if alter_min < self.sperr_minuten:
            return False, (f"Wiedereinstiegs-Sperre: Exit vor {alter_min:.0f} min "
                           f"(Sperre {self.sperr_minuten:.0f} min)")

        if exit_preis > 0 and preis > 0:
            abschlag_pct = (exit_preis - preis) / exit_preis * 100.0
            if abschlag_pct < self.mindest_abschlag_pct:
                return False, (f"Wiedereinstieg nur unter {exit_preis:.6f} "
                               f"-{self.mindest_abschlag_pct:.1f}% "
                               f"(jetzt {preis:.6f} = {abschlag_pct:+.2f}%)")
        return True, ""

    def status(self):
        """Fuer Terminal-Tab / Diagnose."""
        jetzt = time.time()
        out = {}
        for sym, e in self._exits.items():
            alter_min = (jetzt - float(e.get("zeit", 0))) / 60.0
            if alter_min >= self.preisfenster_stunden * 60:
                continue
            out[sym] = {
                "exit_vor_min": round(alter_min, 1),
                "exit_preis": e.get("preis", 0),
                "zeitsperre_aktiv": alter_min < self.sperr_minuten,
                "grund": e.get("grund", ""),
            }
        return out

    def aufraeumen(self):
        """Abgelaufene Eintraege entfernen (optional, spart Datei-Groesse)."""
        jetzt = time.time()
        vorher = len(self._exits)
        self._exits = {
            k: v for k, v in self._exits.items()
            if (jetzt - float(v.get("zeit", 0))) / 3600.0 < self.preisfenster_stunden
        }
        if len(self._exits) != vorher:
            self._speichern()
        return vorher - len(self._exits)
