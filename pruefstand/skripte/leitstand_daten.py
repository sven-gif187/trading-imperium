# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Datenauszug fuer den headless Leitstand (Phase 6, MASTERPROMPT_AGENTEN.md 8).

Der unbeaufsichtigte Leitstand-Lauf hat KEIN Bash/Python (nur Lesen + Schreiben
unter berichte/). Deshalb bereitet dieses Skript vorher alles auf, was er aus
waechter.db und den Bot-Journalen braucht, und legt es als JSON ab:

    daten/leitstand/JJJJ-MM-TT_<art>_daten.json      (art = tag | woche)

Nur lesend: waechter.db mit mode=ro, Bot-Dateien nur gelesen, nichts in Bot-Ordnern.
v6 und v7 bleiben getrennt (eigener Schluessel je Instanz).

Aufruf:  python leitstand_daten.py --art tag   [--aus <datei>]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PRUEF = Path(__file__).resolve().parent.parent
DB = PRUEF / "waechter.db"
STATUS = PRUEF / "status.json"
BERICHTE = PRUEF / "berichte"
AUSORDNER = PRUEF / "daten" / "leitstand"
BERLIN = ZoneInfo("Europe/Berlin")

sys.path.insert(0, str(PRUEF / "skripte"))
import runden_lib  # noqa: E402


def lies_json(pfad: Path, versuche: int = 3):
    """Bot schreibt evtl. gerade: bei halbem Zustand kurz warten und wiederholen."""
    for i in range(versuche):
        try:
            return json.loads(pfad.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            if i == versuche - 1:
                raise
            time.sleep(1.0)


def db_zeilen(c: sqlite3.Connection, sql: str, para: tuple = ()) -> list[dict]:
    cur = c.execute(sql, para)
    namen = [d[0] for d in cur.description]
    return [dict(zip(namen, z)) for z in cur.fetchall()]


def neueste_je(c: sqlite3.Connection, tabelle: str, schluessel: str, zeit: str = "ts_utc") -> list[dict]:
    """Neueste Zeile je Schluessel-Kombination (z. B. instanz, pruefung)."""
    return db_zeilen(c, f"""
        SELECT t.* FROM {tabelle} t
        JOIN (SELECT {schluessel}, MAX({zeit}) AS m FROM {tabelle} GROUP BY {schluessel}) n
          ON {' AND '.join(f't.{s.strip()} = n.{s.strip()}' for s in schluessel.split(','))} AND t.{zeit} = n.m
        ORDER BY {schluessel}""")


def letzter_bericht(muster: str) -> tuple[str | None, str | None]:
    """Zeit (UTC) und Name des neuesten Leitstand-Berichts dieser Art."""
    kandidaten = sorted(BERICHTE.glob(muster), key=lambda p: p.stat().st_mtime)
    if not kandidaten:
        return None, None
    p = kandidaten[-1]
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"), p.name


def runden_fenster(instanzen: dict, jetzt: datetime) -> dict:
    """Kassenrechnung je Instanz (runden_lib) fuer 1/7/14/30 Tage und seit aktueller Epoche."""
    aus = {}
    for name, info in instanzen.items():
        bot = Path(info["pfad"])
        try:
            zeilen = runden_lib.lade(bot)
            epochen = lies_json(bot / "config_epochs.json").get("epochs", [])
            akt = epochen[-1] if epochen else {}
            fenster = {f"{t}_tage": (jetzt - timedelta(days=t)).isoformat() for t in (1, 7, 14, 30)}
            if akt.get("start"):
                fenster["seit_epoche"] = akt["start"]
            werte = {}
            for f, von in fenster.items():
                r = runden_lib.runden(zeilen, von=von)
                werte[f] = {
                    "von_utc": von[:19], "runden": len(r),
                    "netto_usd": round(sum(x["netto"] for x in r), 2),
                    "brutto_usd": round(sum(x["brutto"] for x in r), 2),
                    "gebuehren_usd": round(sum(x["kauf_fee"] + x["verkauf_fee"] for x in r), 2),
                    "gewinnrunden": sum(1 for x in r if x["netto"] > 0),
                }
            letzte = runden_lib.runden(zeilen)[-5:]
            aus[name] = {
                "epoche_aktuell": akt.get("id"), "epoche_start_utc": akt.get("start"),
                "letzte_journalzeile_utc": zeilen[-1]["time"] if zeilen else None,
                "fenster": werte,
                "letzte_5_runden": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()} for x in letzte],
                "hinweis": "Kassenrechnung (runden_lib), nicht pnl. Unter 30 Runden: nicht entscheidbar.",
            }
        except Exception as e:  # eine Instanz darf die andere nicht blockieren
            aus[name] = {"fehler": f"{type(e).__name__}: {e}"}
    return aus


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", choices=["tag", "woche"], required=True)
    ap.add_argument("--aus", type=Path)
    a = ap.parse_args()

    jetzt = datetime.now(timezone.utc)
    datum = jetzt.astimezone(BERLIN).date().isoformat()
    muster = "*_lage.md" if a.art == "tag" else "*_woche.md"
    seit_bericht, bericht_name = letzter_bericht(muster)
    # Ereignisse seit dem letzten Bericht dieser Art, mindestens 1 (Woche: 7) Tage, hoechstens 7 Tage zurueck.
    standard = (jetzt - timedelta(days=1 if a.art == "tag" else 7)).isoformat(timespec="seconds")
    grenze = (jetzt - timedelta(days=7)).isoformat(timespec="seconds")
    seit = max(min(seit_bericht or standard, standard), grenze)

    instanzen = lies_json(PRUEF / "instanzen.json")["instanzen"]
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        ereignisse = db_zeilen(c, "SELECT * FROM ereignisse WHERE ts_utc >= ? ORDER BY ts_utc", (seit,))
        betrieb_rot = db_zeilen(c, """SELECT instanz, pruefung, ampel, COUNT(*) AS anzahl, MIN(ts_utc) AS erstes, MAX(ts_utc) AS letztes
                                      FROM betrieb WHERE ts_utc >= ? AND ampel <> 'GRUEN'
                                      GROUP BY instanz, pruefung, ampel ORDER BY instanz, pruefung""", (seit,))
        kasse_nicht_gruen = db_zeilen(c, """SELECT instanz, pruefung, ampel, COUNT(*) AS anzahl, MAX(ts_utc) AS letztes
                                           FROM kasse WHERE ts_utc >= ? AND ampel <> 'GRUEN'
                                           GROUP BY instanz, pruefung, ampel""", (seit,))
        konto_neu = neueste_je(c, "konto", "instanz")
        konto_spanne = db_zeilen(c, """SELECT instanz, COUNT(*) AS zeilen, MIN(handel_gesamt) AS handel_min, MAX(handel_gesamt) AS handel_max,
                                      MIN(sparplan_btc_wert) AS sparplan_min, MAX(sparplan_btc_wert) AS sparplan_max
                                      FROM konto WHERE ts_utc >= ? GROUP BY instanz""", (seit,))
        vorsprung = neueste_je(c, "vorsprung", "instanz, fenster")
        for v in vorsprung:
            try:
                v["kennzahlen"] = json.loads(v["kennzahlen"])
            except Exception:
                pass
        tag_ml = c.execute("SELECT MAX(datum) FROM marktlage").fetchone()[0]
        marktlage = db_zeilen(c, "SELECT * FROM marktlage WHERE datum = ? ORDER BY coin", (tag_ml,))
        tag_vg = c.execute("SELECT MAX(tag) FROM vergleich").fetchone()[0]
        vergleich = db_zeilen(c, "SELECT * FROM vergleich WHERE tag = ? ORDER BY instanz, pruefung", (tag_vg,))
        nachlauf = db_zeilen(c, """SELECT instanz, lage, art, COUNT(*) AS verkaeufe, ROUND(AVG(r7d), 3) AS mittel_r7d_pct
                                  FROM nachlauf WHERE zeit >= ? GROUP BY instanz, lage, art""",
                             ((jetzt - timedelta(days=30)).isoformat(),))
        spanne = neueste_je(c, "kosten_spanne", "markt")
        daten = {
            "_cleanup": "[CLEANUP-KEEP]",
            "_hinweis": "Erzeugt von skripte/leitstand_daten.py, nur lesend aus waechter.db (mode=ro) und den Bot-Journalen. "
                        "v6 und v7 nie mischen. Zeiten UTC, Anzeige Europe/Berlin.",
            "art": a.art, "datum_berlin": datum,
            "erzeugt_utc": jetzt.isoformat(timespec="seconds"),
            "ereignisse_seit_utc": seit, "letzter_bericht": bericht_name,
            "status_json": lies_json(STATUS),
            "ereignisse": ereignisse,
            "betrieb_nicht_gruen_seit": betrieb_rot,
            "kasse_nicht_gruen_seit": kasse_nicht_gruen,
            "konto_neueste": konto_neu, "konto_spanne_seit": konto_spanne,
            "vorsprung_neueste": vorsprung,
            "marktlage_tag": tag_ml, "marktlage": marktlage,
            "vergleich_tag": tag_vg, "vergleich": vergleich,
            "nachlauf_30_tage": nachlauf,
            "kosten_spanne_neueste": spanne,
            "runden": runden_fenster(instanzen, jetzt),
        }
    finally:
        c.close()

    ziel = a.aus or (AUSORDNER / f"{datum}_{a.art}_daten.json")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp = ziel.with_suffix(".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(ziel)
    print(ziel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
