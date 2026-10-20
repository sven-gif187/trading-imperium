# -*- coding: utf-8 -*-
"""Lernender Waechter fuer den Regime-Filter.

WAS ER TUT
----------
Einmal taeglich misst er nach, was die geblockten Kaufgelegenheiten der
letzten Tage tatsaechlich gebracht haetten - und passt die Schwelle
min_confirmations an, wenn die Daten das eindeutig hergeben. Jede
Entscheidung wird mit Begruendung, Zahlen und Marktphase in der Datenbank
festgehalten.

Damit lernt der Bot nicht nur "jetzt lockern", sondern baut ein Gedaechtnis
auf: beim naechsten MID_BEAR kann er nachschlagen, wie sich der Filter
damals verhalten hat.

DIE MESSUNG
-----------
Fuer jede geblockte Gelegenheit (Zeitpunkt und Kurs stehen in
telemetrie.db) wird der Kurs 24 Stunden spaeter nachgeschlagen. Daraus
ergibt sich, ob der Block Geld gespart oder Gewinn verhindert hat -
gerechnet nach Kosten.

    Ergebnis deutlich POSITIV  -> Block war teuer  -> Filter lockern
    Ergebnis deutlich NEGATIV  -> Block hat gespart -> Filter verschaerfen
    dazwischen                 -> nichts tun

SICHERHEITSGRENZEN - nicht verhandelbar
---------------------------------------
1. min_confirmations bleibt immer zwischen 2 und 4.
2. Aenderung nur bei mindestens MIN_FAELLE unabhaengigen Zeitfenstern.
   Gezaehlt werden STUNDEN, nicht Einzelpruefungen - der Bot prueft alle
   12 Sekunden und wuerde sonst dieselbe Marktlage hundertfach zaehlen
   (Pseudo-Replikation). Das war die groesste Schwaeche der Erstmessung.
3. Hoechstens EINE Aenderung je Lauf, und nur um EINE Stufe.
4. Nach einer Aenderung mindestens SPERRE_TAGE Ruhe, damit die Wirkung
   messbar wird, bevor erneut gedreht wird.
5. Alles wird protokolliert - auch die Entscheidung, NICHTS zu tun.
6. AKTIV = False schaltet das Lernen komplett ab; dann wird nur gemessen
   und berichtet.

Aendert ausschliesslich min_confirmations im Regime-Filter. Ruehrt weder
Stop-Loss noch Positionsgroesse noch Kill-Switch an.
"""
import json
import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(HIER, "config_regime_filter.json")
DB = os.path.join(HIER, "data_store", "telemetrie.db")

# [MESSFENSTER-PAUSE 17.08.2026] True -> False bis zum 27.08.2026.
# Der Waechter misst und meldet weiter, aendert die Schwelle aber nicht.
#
# GRUND ist NICHT, dass seine Entscheidung vom 15.08. falsch war - sie war
# wahrscheinlich richtig. Der Grund ist die DATENLAGE: Bei 48 Stunden
# Horizont passen in zehn Tage nur fuenf nicht ueberlappende Zeitfenster.
# Jede weitere Umstellung teilt diesen ohnehin winzigen Vorrat noch einmal
# und macht die Frage "war das Strengerstellen richtig?" dauerhaft
# unbeantwortbar - gemessen mit schwelle_vergleich.py.
#
# Anders gesagt: Der Lerner braucht eine ruhige Strecke, um sich selbst
# ueberpruefen zu lassen. Nach dem 27.08. wieder auf True.
AKTIV = False             # False = nur messen und melden, nicht aendern
# [KORREKTUR 10.08.2026] 12 -> 24. Der erste Testlauf drehte sofort von 3 auf 4
# hoch, gestuetzt auf ganze 14 Stunden. Bei 4 muessen ALLE vier Signale feuern -
# der Filter waere praktisch aus. Ein einzelner Tag darf so eine Entscheidung
# nicht tragen. 24 unabhaengige Stunden bedeuten mindestens einen vollen
# Tageszyklus mit Nacht- und Handelsphasen.
MIN_FAELLE = 24           # unabhaengige STUNDEN, nicht Einzelpruefungen
SPERRE_TAGE = 3           # Ruhe nach einer Aenderung
SCHWELLE_PCT = 0.5        # ab dieser Rendite gilt ein Befund als eindeutig
HORIZONT_H = 24
# [13.09.2026] Die Zahl steht jetzt an EINER Stelle: core/kosten.py.
# Hier stand 0.32 % - die alte Annahme aus der Zeit vor Bybit EU.
# Neun Dateien mit neun eigenen Kostenzahlen waren neun Gelegenheiten,
# eine davon zu vergessen; genau das war passiert. Diese Datei rechnet
# nur aus und handelt nicht - die Umstellung ist deshalb
# freeze-vertraeglich.
from core.kosten import K_BASIS_PCT
KOSTEN_PCT = K_BASIS_PCT
GRENZE_MIN, GRENZE_MAX = 2, 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS regime_lernen (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT NOT NULL,
    marktphase    TEXT,
    regime        TEXT,
    faelle        INTEGER,      -- unabhaengige Stunden
    rendite_24h   REAL,         -- Mittel nach Kosten
    anteil_plus   REAL,
    wert_vorher   INTEGER,
    wert_nachher  INTEGER,
    entscheidung  TEXT,         -- LOCKERN | VERSCHAERFEN | UNVERAENDERT | GESPERRT
    begruendung   TEXT
);
CREATE INDEX IF NOT EXISTS ix_rl_ts ON regime_lernen(ts_utc);
"""


def _log(stufe, text):
    try:
        from core.logger import log
        getattr(log, stufe, log.info)("REGIME-LERN", text)
    except Exception:
        print(f"[REGIME-LERN] {text}")


def _db():
    con = sqlite3.connect(DB, timeout=10)
    con.executescript(SCHEMA)
    return con


def lade_cfg():
    with open(CFG, "r", encoding="utf-8") as f:
        return json.load(f)


def speichere_cfg(cfg):
    tmp = CFG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CFG)


def letzte_aenderung(con):
    """Wann wurde zuletzt wirklich gedreht? Fuer die Sperrfrist."""
    r = con.execute(
        "SELECT ts_utc FROM regime_lernen "
        "WHERE entscheidung IN ('LOCKERN','VERSCHAERFEN') "
        "ORDER BY ts_utc DESC LIMIT 1").fetchone()
    if not r:
        return None
    try:
        return datetime.fromisoformat(r[0].replace("Z", "+00:00"))
    except Exception:
        return None


def messe(con, tage=7):
    """Rendite der geblockten Gelegenheiten, gruppiert nach STUNDE.

    Rueckgabe: (anzahl_stunden, mittel_pct, anteil_plus_pct)
    """
    seit = (datetime.now(timezone.utc) - timedelta(days=tage)).isoformat()
    rows = con.execute(
        "SELECT e.ts_utc, e.symbol, e.entry_price FROM evaluations e "
        "JOIN rule_evaluations r ON r.evaluation_id = e.evaluation_id "
        "WHERE r.rule_name = 'REGIME_FILTER' AND e.entry_price > 0 "
        "  AND e.ts_utc >= ? ORDER BY e.ts_utc", (seit,)).fetchall()
    if not rows:
        return 0, 0.0, 0.0

    # Auf STUNDE eindampfen - eine Marktlage zaehlt einmal, nicht 300 Mal.
    je_stunde = {}
    for ts, sym, preis in rows:
        schluessel = (ts[:13], sym)          # YYYY-MM-DDTHH + Coin
        je_stunde.setdefault(schluessel, float(preis))
    if len(je_stunde) < 3:
        return len(je_stunde), 0.0, 0.0

    try:
        import ccxt
        boerse = ccxt.binance({"enableRateLimit": True})
    except Exception as e:
        _log("warn", f"Boerse nicht erreichbar: {str(e)[:60]}")
        return 0, 0.0, 0.0

    kerzen = {}
    for sym in {k[1] for k in je_stunde}:
        try:
            roh = boerse.fetch_ohlcv(sym, "1h", limit=500)
            kerzen[sym] = {int(k[0] / 1000): float(k[4]) for k in roh}
            time.sleep(boerse.rateLimit / 1000.0)
        except Exception:
            continue

    renditen = []
    for (stunde, sym), preis in je_stunde.items():
        k = kerzen.get(sym)
        if not k:
            continue
        try:
            t = datetime.fromisoformat(stunde + ":00:00+00:00")
        except Exception:
            continue
        ziel = int(t.timestamp()) + HORIZONT_H * 3600
        basis = ziel - (ziel % 3600)
        spaeter = None
        for versatz in range(0, 6 * 3600, 3600):
            spaeter = k.get(basis + versatz)
            if spaeter:
                break
        if not spaeter:
            continue
        renditen.append((spaeter / preis - 1) * 100 - KOSTEN_PCT)

    if not renditen:
        return 0, 0.0, 0.0
    mittel = sum(renditen) / len(renditen)
    plus = sum(1 for x in renditen if x > 0) / len(renditen) * 100
    return len(renditen), mittel, plus


def taeglicher_lauf(app=None):
    """Misst, entscheidet, protokolliert. Wirft nie nach aussen."""
    ergebnis = {"entscheidung": "FEHLER", "begruendung": "", "faelle": 0}
    try:
        con = _db()
        cfg = lade_cfg()
        vorher = int(cfg.get("min_confirmations", 2))

        phase = regime = "?"
        if app is not None:
            try:
                phase = str(app.state.get("cycle_phase", "?"))
                regime = str(getattr(app.regime_detector, "current_regime", "?"))
            except Exception:
                pass

        n, mittel, plus = messe(con)
        ergebnis.update({"faelle": n, "rendite": round(mittel, 3),
                         "anteil_plus": round(plus, 1)})

        # --- Sicherheitsgrenzen der Reihe nach ---
        letzte = letzte_aenderung(con)
        gesperrt_bis = (letzte + timedelta(days=SPERRE_TAGE)) if letzte else None
        nachher = vorher

        if n < MIN_FAELLE:
            ent = "UNVERAENDERT"
            grund = (f"Nur {n} unabhaengige Stunden gemessen, noetig sind "
                     f"{MIN_FAELLE}. Zu duenn fuer eine Aenderung.")
        elif gesperrt_bis and datetime.now(timezone.utc) < gesperrt_bis:
            ent = "GESPERRT"
            grund = (f"Letzte Aenderung am {letzte.date()}, Sperrfrist "
                     f"{SPERRE_TAGE} Tage. Wirkung erst abwarten.")
        elif mittel > SCHWELLE_PCT and vorher < GRENZE_MAX:
            ent = "LOCKERN"
            nachher = vorher + 1
            grund = (f"Geblockte Kaeufe waeren im Mittel {mittel:+.2f} % wert "
                     f"gewesen ({plus:.0f} % im Plus, {n} Stunden). Der Filter "
                     f"kostet in dieser Marktlage Geld.")
        elif mittel < -SCHWELLE_PCT and vorher > GRENZE_MIN:
            ent = "VERSCHAERFEN"
            nachher = vorher - 1
            grund = (f"Geblockte Kaeufe haetten im Mittel {mittel:+.2f} % "
                     f"verloren ({n} Stunden). Der Filter schuetzt - "
                     f"strenger stellen.")
        else:
            ent = "UNVERAENDERT"
            grund = (f"Ergebnis {mittel:+.2f} % liegt innerhalb der "
                     f"Neutralzone von +/-{SCHWELLE_PCT} %. Kein klarer "
                     f"Vorteil in eine Richtung.")

        if ent in ("LOCKERN", "VERSCHAERFEN"):
            if AKTIV:
                cfg["min_confirmations"] = nachher
                cfg["_zuletzt_geaendert"] = (
                    f"{datetime.now(timezone.utc).isoformat()[:19]} durch "
                    f"regime_adaptiv: {grund}")
                speichere_cfg(cfg)
                _log("warn", f"{ent}: min_confirmations {vorher} -> {nachher}. "
                             f"{grund}")
            else:
                ent = "UNVERAENDERT"
                nachher = vorher
                grund = "Lernen ist abgeschaltet (AKTIV=False). " + grund
                _log("info", f"Nur gemessen: {grund}")
        else:
            _log("info", f"{ent}: {grund}")

        con.execute(
            "INSERT INTO regime_lernen (ts_utc,marktphase,regime,faelle,"
            "rendite_24h,anteil_plus,wert_vorher,wert_nachher,entscheidung,"
            "begruendung) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), phase, regime, n,
             round(mittel, 4), round(plus, 2), vorher, nachher, ent, grund))
        con.commit()
        con.close()

        ergebnis.update({"entscheidung": ent, "begruendung": grund,
                         "vorher": vorher, "nachher": nachher})

        if app is not None and ent in ("LOCKERN", "VERSCHAERFEN"):
            try:
                app.telegram.send(
                    f"🧠 Regime-Filter angepasst\n\n"
                    f"min_confirmations: {vorher} -> {nachher}\n"
                    f"Marktphase: {phase}\n\n{grund}")
            except Exception:
                pass
        return ergebnis
    except Exception as e:
        _log("warn", f"Lauf fehlgeschlagen: {str(e)[:120]}")
        ergebnis["begruendung"] = str(e)[:200]
        return ergebnis


def gedaechtnis(phase=None, limit=20):
    """Was hat der Bot in dieser Marktphase frueher gelernt?"""
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=8)
        if phase:
            r = con.execute(
                "SELECT ts_utc,marktphase,faelle,rendite_24h,wert_vorher,"
                "wert_nachher,entscheidung,begruendung FROM regime_lernen "
                "WHERE marktphase=? ORDER BY ts_utc DESC LIMIT ?",
                (phase, limit)).fetchall()
        else:
            r = con.execute(
                "SELECT ts_utc,marktphase,faelle,rendite_24h,wert_vorher,"
                "wert_nachher,entscheidung,begruendung FROM regime_lernen "
                "ORDER BY ts_utc DESC LIMIT ?", (limit,)).fetchall()
        con.close()
        return r
    except Exception:
        return []


if __name__ == "__main__":
    import sys
    print("=" * 84)
    print(" REGIME-LERNEN - Messung und Entscheidung")
    print("=" * 84)
    e = taeglicher_lauf()
    print(f"\n  Gemessene Stunden : {e.get('faelle')}")
    print(f"  Rendite 24 h      : {e.get('rendite', 0):+.3f} % nach Kosten")
    print(f"  davon im Plus     : {e.get('anteil_plus', 0):.1f} %")
    print(f"  Entscheidung      : {e.get('entscheidung')}")
    print(f"  Begruendung       : {e.get('begruendung')}")
    if e.get("vorher") is not None:
        print(f"  min_confirmations : {e.get('vorher')} -> {e.get('nachher')}")

    g = gedaechtnis(limit=10)
    if g:
        print("\n" + "=" * 84)
        print(" GEDAECHTNIS - fruehere Entscheidungen")
        print("=" * 84)
        print(f"\n  {'Zeit':<12s}{'Phase':<12s}{'n':>5s}{'Rendite':>10s}"
              f"{'von':>5s}{'nach':>6s}  Entscheidung")
        print("  " + "-" * 70)
        for x in g:
            print(f"  {x[0][:10]:<12s}{str(x[1])[:11]:<12s}{x[2]:>5d}"
                  f"{x[3]:>+9.2f}%{x[4]:>5d}{x[5]:>6d}  {x[6]}")
    sys.exit(0)
