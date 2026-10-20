# -*- coding: utf-8 -*-
"""
Daily-Loss-Waechter — EINE Wahrheit. [DAILY-LOSS P5 20.07.2026]
================================================================
Ersetzt die drei alten Implementierungen (manager-Methoden,
daily_loss_guard.py, daily_loss_guardian.py).

GRUNDREGELN (nicht verhandelbar):
  * Reaktion ist AUSSCHLIESSLICH eine Kaufpause.
  * Es wird NIEMALS eine Position verkauft. Kein Zwangsverkauf,
    kein "alles schliessen". Genau das hat am 18.06. den groessten
    Verlusttag verursacht. Offene Positionen behalten ihren
    Einzel-Stop-Loss, der Exit-Monitor laeuft unabhaengig weiter.
  * Messgroesse ist der REALISIERTE Tagesverlust aus dem Journal
    (data_store/trades_v5.json). Wird bei jeder Pruefung neu
    gerechnet -> strukturell neustart-fest, kein RAM-Zustand.
  * Kalender ist die LOKALE Zeit (wie Journal + Terminal-Tab).

MODI (config.risk.daily_loss.mode, Vorgabe "schatten"):
  aus       - komplett inaktiv
  schatten  - rechnet + protokolliert, greift NICHT ein
              (keine Verhaltensaenderung, epochensicher)
  aktiv     - pausiert tatsaechlich neue Kaeufe bis Mitternacht
"""
import os, json
from datetime import datetime, date

try:
    from core.logger import log
except Exception:                                    # Testbarkeit ohne Bot
    class _L:
        def info(self, m, s): print(f"[{m}] {s}")
        def warn(self, m, s): print(f"[{m}] {s}")
        def error(self, m, s): print(f"[{m}] {s}")
    log = _L()

MODUS_AUS, MODUS_SCHATTEN, MODUS_AKTIV = "aus", "schatten", "aktiv"
VORGABE_LIMIT_PCT = 10.0


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _store(name):
    return os.path.join(_root(), "data_store", name)


class DailyLoss:
    """Tagesverlust-Waechter. Nur Kaufpause, nie Verkauf."""

    def __init__(self, config=None, equity_getter=None,
                 journal_path=None, state_path=None, protokoll_path=None):
        self.config = config
        self.equity_getter = equity_getter          # callable -> float
        self.journal_path = journal_path or _store("trades_v5.json")
        self.state_path = state_path or _store("daily_loss_state.json")
        self.protokoll_path = protokoll_path or _store("daily_loss_schatten.json")
        self._gemeldet_am = ""                      # Log-Drosselung: 1x pro Tag

    # ---------- Konfiguration ----------
    def _cfg(self):
        mode, limit = MODUS_SCHATTEN, VORGABE_LIMIT_PCT
        try:
            dl = getattr(getattr(self.config, "risk", None), "daily_loss", None)
            if isinstance(dl, dict):
                mode = str(dl.get("mode", mode)).lower()
                limit = float(dl.get("limit_pct", limit))
            elif dl is not None:
                mode = str(getattr(dl, "mode", mode)).lower()
                limit = float(getattr(dl, "limit_pct", limit))
        except Exception:
            pass
        if mode not in (MODUS_AUS, MODUS_SCHATTEN, MODUS_AKTIV):
            mode = MODUS_SCHATTEN
        return mode, limit

    # ---------- Bausteine ----------
    @staticmethod
    def _heute():
        return date.today().isoformat()

    @staticmethod
    def _lokales_datum(zeitstempel):
        """ISO-Zeitstempel -> lokales Kalenderdatum ('YYYY-MM-DD') oder ''.

        [ZEITZONEN-FIX 29.07.2026] Das Journal schreibt UTC
        (datetime.now(timezone.utc).isoformat() in app.py und
        exit_monitor.py), verglichen wurde aber gegen date.today(),
        also LOKALE Zeit. Bei MESZ (UTC+2) fielen dadurch alle Trades
        zwischen 00:00 und 02:00 Ortszeit aus der Tagesrechnung heraus -
        sie tragen noch das UTC-Datum von gestern. Der Tagesverlust-
        Waechter hat exakt in den Stunden nach Mitternacht falsch
        gerechnet. Jetzt wird sauber nach Ortszeit umgerechnet.
        """
        s = str(zeitstempel or "")
        if not s:
            return ""
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return s[:10]                       # Notnagel: alte Eintraege ohne Zone
        try:
            if dt.tzinfo is not None:
                dt = dt.astimezone()            # -> lokale Zeitzone
        except Exception:
            pass
        return dt.date().isoformat()

    def _realisiert_heute(self):
        """Summe der heute realisierten P&L aus dem Journal. (verlust, anzahl)"""
        try:
            with open(self.journal_path, "r", encoding="utf-8") as f:
                trades = json.load(f)
        except Exception:
            return 0.0, 0
        heute = self._heute()
        summe, n = 0.0, 0
        for t in trades:
            if t.get("type") != "SELL":
                continue
            if self._lokales_datum(t.get("time", "")) != heute:
                continue
            try:
                summe += float(t.get("pnl", 0) or 0)
                n += 1
            except Exception:
                continue
        return summe, n

    def _tagesstart_equity(self):
        """Persistierter Startwert des Tages (neustart-fest)."""
        heute = self._heute()
        zustand = {}
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                zustand = json.load(f)
        except Exception:
            zustand = {}
        if zustand.get("datum") == heute and zustand.get("start_equity"):
            return float(zustand["start_equity"]), False
        # neuer Tag -> Startwert setzen
        equity = 0.0
        try:
            if self.equity_getter:
                equity = float(self.equity_getter() or 0)
        except Exception:
            equity = 0.0
        if equity <= 0:
            # Kein verlaesslicher Wert -> alten behalten, nicht ueberschreiben
            return float(zustand.get("start_equity", 0) or 0), False
        self._schreibe_json(self.state_path,
                            {"datum": heute, "start_equity": round(equity, 2),
                             "gesetzt_um": datetime.now().isoformat()[:19]})
        log.info("DAILY-LOSS", f"Neuer Tag {heute} - Startkapital {equity:.2f}$")
        return equity, True

    @staticmethod
    def _schreibe_json(pfad, daten):
        try:
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            tmp = pfad + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(daten, f, indent=1, ensure_ascii=False)
            os.replace(tmp, pfad)
        except Exception:
            pass

    def _protokolliere(self, eintrag):
        """Schatten-Protokoll: ein Eintrag je Tag, fuer die spaetere Auswertung."""
        try:
            hist = {}
            if os.path.isfile(self.protokoll_path):
                with open(self.protokoll_path, "r", encoding="utf-8") as f:
                    hist = json.load(f)
            heute = eintrag["datum"]
            alt = hist.get(heute, {})
            # schlechtesten Stand des Tages festhalten
            if not alt or eintrag["verlust_pct"] > alt.get("verlust_pct", -999):
                hist[heute] = eintrag
                self._schreibe_json(self.protokoll_path, hist)
        except Exception:
            pass

    # ---------- Hauptpruefung ----------
    def pruefe(self):
        """Rechnet den Tagesstand. Greift NIE selbst ein."""
        mode, limit_pct = self._cfg()
        pnl, n = self._realisiert_heute()
        start_equity, _neu = self._tagesstart_equity()
        verlust_pct = 0.0
        if start_equity > 0 and pnl < 0:
            verlust_pct = abs(pnl) / start_equity * 100
        erreicht = bool(start_equity > 0 and verlust_pct >= limit_pct)
        ergebnis = {
            "modus": mode, "limit_pct": limit_pct,
            "datum": self._heute(), "pnl_heute": round(pnl, 2),
            "sells_heute": n, "start_equity": round(start_equity, 2),
            "verlust_pct": round(verlust_pct, 2), "limit_erreicht": erreicht,
        }
        if mode != MODUS_AUS:
            self._protokolliere(dict(ergebnis))
        if erreicht and self._gemeldet_am != ergebnis["datum"]:
            self._gemeldet_am = ergebnis["datum"]
            if mode == MODUS_SCHATTEN:
                log.warn("DAILY-LOSS", f"[SCHATTEN] WUERDE jetzt pausieren: "
                                       f"{pnl:+.2f}$ = -{verlust_pct:.2f}% "
                                       f"(Limit {limit_pct}%). Kein Eingriff.")
            elif mode == MODUS_AKTIV:
                log.error("DAILY-LOSS", f"LIMIT ERREICHT: {pnl:+.2f}$ = "
                                        f"-{verlust_pct:.2f}% (Limit {limit_pct}%). "
                                        f"KEINE neuen Kaeufe heute. "
                                        f"Offene Positionen behalten ihren Stop-Loss.")
        return ergebnis

    def kaeufe_pausiert(self):
        """EINZIGE Wirkung nach aussen: True = keine neuen Kaeufe.
        Verkauft niemals etwas."""
        e = self.pruefe()
        return bool(e["limit_erreicht"] and e["modus"] == MODUS_AKTIV)

    def status_text(self):
        """Kurzfassung fuer den Terminal-Tab."""
        e = self.pruefe()
        if e["modus"] == MODUS_AUS:
            return "aus"
        pausiert = " - KAEUFE PAUSIERT" if (e["limit_erreicht"] and
                                            e["modus"] == MODUS_AKTIV) else ""
        return (f"-{e['verlust_pct']:.1f}% von {e['limit_pct']:.0f}% "
                f"(Modus: {e['modus'].capitalize()}){pausiert}")

    def reset(self):
        """Manuelles Zuruecksetzen (UI): Tagesstart neu setzen."""
        try:
            os.remove(self.state_path)
        except Exception:
            pass
        self._gemeldet_am = ""
        return self._tagesstart_equity()[0]
