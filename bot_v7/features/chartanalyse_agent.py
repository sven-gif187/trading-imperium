# -*- coding: utf-8 -*-
"""Chartanalyse-Agent - haelt die Messung selbsttaetig auf aktuellem Stand.

[CHARTANALYSE-AGENT 07.08.2026]

WAS ER TUT
----------
Einmal taeglich laeuft der Backtest ueber die aktuellen Kurse neu. Die
Ergebnisse landen in data_store/telemetrie.db, und der Agent vergleicht sie
mit dem letzten Lauf: Ist die Trefferquote gefallen? Ist der Erwartungswert
gekippt? Feuert die Regel ploetzlich doppelt so oft?

WAS ER AUSDRUECKLICH NICHT TUT - der wichtigste Absatz hier
-----------------------------------------------------------
Er veraendert KEINEN Parameter. Nicht die Swing-Weite, nicht die
Zonen-Toleranz, nicht die Mindestguete, nicht die Kostenannahme. Die
Einstellungen sind in PARAMETER eingefroren und werden nur von Hand geaendert,
mit Datum und Begruendung.

Der Grund ist wichtig: Ein Agent, der seine Schwellen so lange nachzieht, bis
die Zahlen wieder gut aussehen, produziert keine Erkenntnis, sondern eine
Illusion. Er wuerde die Regel immer genauer an die Vergangenheit anpassen
(Overfitting) und im Echtbetrieb verlieren. Genau davor schuetzt das
Forschungsprogramm dieses Projekts mit Regel 14 - und dieselbe Disziplin gilt
hier.

Der Agent bringt also nur die MESSUNG auf Stand, nicht das Ergebnis in Form.

Er handelt nicht und wird von keinem Kaufpfad importiert.
"""
import json
import os
import sqlite3
import traceback
from datetime import datetime, timezone

# Eingefrorene Messparameter. Aenderungen NUR von Hand, mit Datum und Grund.
# Stand 07.08.2026 - erster Satz, noch nie angepasst.
PARAMETER = {
    "maerkte": [("BTC/USDC", "1h"), ("BTC/USDC", "4h"),
                ("ETH/USDC", "4h"), ("SOL/USDC", "4h")],
    "kerzen": 800,
    "min_guete": 0.35,
    "stand": "2026-08-07",
}

# Ab welcher Veraenderung gegenueber dem Vorlauf gemeldet wird.
SCHWELLE_QUOTE_PP = 8.0        # Prozentpunkte Trefferquote
SCHWELLE_EV_PP = 0.15          # Prozentpunkte Erwartungswert
SCHWELLE_ANZAHL = 0.5          # 50 % mehr oder weniger Signale


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _db():
    return os.path.join(_root(), "data_store", "telemetrie.db")


def _log(stufe, text):
    """Loggt ueber den Bot-Logger, faellt auf print zurueck."""
    try:
        from core.logger import log
        getattr(log, stufe, log.info)("CHART-AGENT", text)
    except Exception:
        print(f"[CHART-AGENT] {text}")


def _vorlauf(con, symbol, timeframe, ausser_id):
    z = con.execute(
        "SELECT quote_pct, ev_netto_pct, signale FROM chart_laeufe "
        "WHERE symbol=? AND timeframe=? AND lauf_id<>? "
        "ORDER BY ts_utc DESC LIMIT 1", (symbol, timeframe, ausser_id)).fetchone()
    return z


def _aktueller(con, lauf_id):
    return con.execute(
        "SELECT quote_pct, ev_netto_pct, signale FROM chart_laeufe "
        "WHERE lauf_id=?", (lauf_id,)).fetchone()


def taeglicher_lauf(telegram=None):
    """Einmal ueber alle konfigurierten Maerkte messen und vergleichen.

    Rueckgabe: dict mit Ergebnis je Markt. Wirft nie nach aussen - ein Fehler
    hier darf den Bot nicht beruehren.
    """
    ergebnis = {"zeit": datetime.now(timezone.utc).isoformat()[:19],
                "maerkte": [], "meldungen": [], "fehler": []}
    try:
        import sys
        if _root() not in sys.path:
            sys.path.insert(0, _root())
        from chartanalyse_backtest import lauf
    except Exception as e:
        _log("error", f"Backtest-Modul nicht ladbar: {e}")
        ergebnis["fehler"].append(str(e))
        return ergebnis

    for symbol, tf in PARAMETER["maerkte"]:
        try:
            lauf_id = lauf(symbol, tf, PARAMETER["kerzen"],
                           PARAMETER["min_guete"])
            if not lauf_id:
                ergebnis["fehler"].append(f"{symbol} {tf}: kein Ergebnis")
                continue

            con = sqlite3.connect(_db(), timeout=10.0)
            jetzt = _aktueller(con, lauf_id)
            vorher = _vorlauf(con, symbol, tf, lauf_id)
            con.close()
            if not jetzt:
                continue

            eintrag = {"symbol": symbol, "timeframe": tf,
                       "quote": jetzt[0], "ev": jetzt[1], "signale": jetzt[2],
                       "veraenderung": None}

            if vorher:
                d_quote = jetzt[0] - vorher[0]
                d_ev = jetzt[1] - vorher[1]
                d_anz = ((jetzt[2] - vorher[2]) / vorher[2]) if vorher[2] else 0
                eintrag["veraenderung"] = {
                    "quote_pp": round(d_quote, 2),
                    "ev_pp": round(d_ev, 4),
                    "signale_pct": round(d_anz * 100, 1)}

                auffaellig = []
                if abs(d_quote) >= SCHWELLE_QUOTE_PP:
                    auffaellig.append(f"Trefferquote {d_quote:+.1f} Prozentpunkte")
                if abs(d_ev) >= SCHWELLE_EV_PP:
                    auffaellig.append(f"Erwartungswert {d_ev:+.3f} Prozentpunkte")
                if abs(d_anz) >= SCHWELLE_ANZAHL:
                    auffaellig.append(f"Signalzahl {d_anz*100:+.0f} Prozent")
                # Vorzeichenwechsel ist immer eine Meldung wert
                if (vorher[1] < 0) != (jetzt[1] < 0):
                    auffaellig.append(
                        f"Erwartungswert hat das Vorzeichen gewechselt "
                        f"({vorher[1]:+.3f} -> {jetzt[1]:+.3f})")
                if auffaellig:
                    text = f"{symbol} {tf}: " + ", ".join(auffaellig)
                    ergebnis["meldungen"].append(text)
                    _log("warn", text)

            ergebnis["maerkte"].append(eintrag)
            _log("info", f"{symbol} {tf}: {jetzt[2]} Signale, "
                         f"Quote {jetzt[0]:.1f}%, EV netto {jetzt[1]:+.3f}%")
        except Exception as e:
            ergebnis["fehler"].append(f"{symbol} {tf}: {type(e).__name__}: {e}")
            _log("warn", f"{symbol} {tf} fehlgeschlagen: {str(e)[:100]}")
            try:
                with open(os.path.join(_root(), "data_store",
                                       "chartagent_fehler.log"), "a",
                          encoding="utf-8") as f:
                    f.write(f"\n[{ergebnis['zeit']}] {symbol} {tf}\n"
                            f"{traceback.format_exc()}")
            except Exception:
                pass

    _bericht_schreiben(ergebnis)

    if ergebnis["meldungen"] and telegram is not None:
        try:
            telegram.send("📐 Chartanalyse - Veraenderung erkannt\n\n"
                          + "\n".join(f"• {m}" for m in ergebnis["meldungen"])
                          + "\n\nParameter unveraendert. Nur die Messung ist neu.")
        except Exception as e:
            _log("warn", f"Telegram fehlgeschlagen: {str(e)[:60]}")

    return ergebnis


def _bericht_schreiben(ergebnis):
    """Letzten Stand als JSON ablegen - der Tab kann ihn anzeigen."""
    try:
        p = os.path.join(_root(), "data_store", "chartagent_stand.json")
        ergebnis["parameter"] = PARAMETER
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ergebnis, f, ensure_ascii=False, indent=1, default=str)
        os.replace(tmp, p)
    except Exception as e:
        _log("warn", f"Stand nicht gespeichert: {str(e)[:60]}")


def letzter_stand():
    """Liest den zuletzt geschriebenen Stand (fuer den Tab)."""
    try:
        p = os.path.join(_root(), "data_store", "chartagent_stand.json")
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


if __name__ == "__main__":
    import sys
    erg = taeglicher_lauf()
    print("\n" + "=" * 78)
    print(" CHARTANALYSE-AGENT - Ergebnis")
    print("=" * 78)
    for m in erg["maerkte"]:
        v = m.get("veraenderung")
        zusatz = ""
        if v:
            zusatz = (f"   (Quote {v['quote_pp']:+.1f}pp, "
                      f"EV {v['ev_pp']:+.3f}pp, Signale {v['signale_pct']:+.0f}%)")
        print(f"  {m['symbol']:<10s} {m['timeframe']:<4s} "
              f"{m['signale']:5d} Signale  Quote {m['quote']:5.1f}%  "
              f"EV {m['ev']:+.3f}%{zusatz}")
    if erg["meldungen"]:
        print("\n  MELDUNGEN:")
        for x in erg["meldungen"]:
            print(f"    - {x}")
    if erg["fehler"]:
        print("\n  FEHLER:")
        for x in erg["fehler"]:
            print(f"    - {x}")
    print("=" * 78)
    sys.exit(0)
