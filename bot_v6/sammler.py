# -*- coding: utf-8 -*-
"""
sammler.py - Datensammler fuer METALLE / GELDFLUSS / ZYKLUS
============================================================
[AUDIT 06.08.2026]

WARUM DIESE DATEI EXISTIERT
---------------------------
Bis heute lief die Datenerfassung dieser drei Bereiche IN DER ANZEIGE:

  - METALLE sammelt nur beim Klick auf "Aktualisieren" oder beim Oeffnen
    des Tabs. Belegt in metals/metals_data/scan_log.jsonl: 64 Zeilen =
    32 Scans an 15 von 40 Tagen (27.06.-05.08.2026). An 25 Tagen nichts.
  - GELDFLUSS schreibt seinen Tagesschnappschuss nur, solange der Tab
    offen ist und der 14-Minuten-Cache ablaeuft.
  - ZYKLUS liest eine Datei, die von history_harvester.py erzeugt wird -
    einem manuellen Skript. Am 06.08.2026 war sie 33 Tage alt und wurde
    trotzdem als "heute" angezeigt.

Ergebnis: keine aequidistanten Zeitreihen, dafuer ein Auswahlfehler -
gesammelt wurde, wenn jemand hinsah, also typischerweise bei
Marktbewegung. Fuer Korrelations- oder Kausalanalysen disqualifizierend.

WARUM NICHT IN DEN BOT
----------------------
Der Scheduler in core/scheduler.py startet jeden Task in einem eigenen
Thread, ein langsamer Netz-Call wuerde den Trading-Loop also nicht
blockieren - technisch waere eine Registrierung dort moeglich. Dagegen
sprechen zwei Dinge:

  1. Der Sammler laeuft dann nur, wenn der Bot laeuft. Genau das ist die
     Ursache der bisherigen Luecken.
  2. Jede Zeile mehr im Trading-Prozess ist ein Risiko fuer den Handel.
     Die drei Tabs sind bewusst isoliert ("REINE ANZEIGE, kein
     Trading-Eingriff") - diese Isolation bleibt hier vollstaendig
     erhalten.

Dieses Skript importiert den Bot NICHT, faesst keinen Bot-State an und
handelt nichts. Es schreibt ausschliesslich in die drei eigenen Dateien:

    metals/metals_data/scan_log.jsonl      (append)
    metals/metals_data/metals_state.json   (ueberschreibt letzten Stand)
    metals/metals_journal.json             (Signale + Outcomes)
    data_store/geldfluss_history.json      (ein Eintrag je Tag)
    data_store/situation_history.json      (Vollaufbau, atomar)

BENUTZUNG
---------
    python sammler.py                     alles faellige
    python sammler.py --nur metalle
    python sammler.py --nur geldfluss
    python sammler.py --nur zyklus
    python sammler.py --force             Zyklus auch neu bauen, wenn frisch
    python sammler.py --max-alter 3       Zyklus erst ab 3 Tagen Alter neu

Taeglich automatisch (Windows, ohne Adminrechte):

    schtasks /create /tn "TI6-Sammler" /tr ^
      "cmd /c cd /d \"C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\" ^
       && python sammler.py >> data_store\\sammler.log 2>&1" ^
      /sc daily /st 06:00

Exit-Code 0 = alles gelaufen, 1 = mindestens ein Bereich fehlgeschlagen.
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime, date, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

ZYKLUS_DATEI = os.path.join(HIER, "data_store", "situation_history.json")
PROTOKOLL = os.path.join(HIER, "data_store", "sammler_status.json")


def log(bereich, text):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] [{bereich}] {text}", flush=True)


# ======================================================================
# METALLE
# ======================================================================
def sammle_metalle():
    """Ein Scan: analysieren, Signale fortschreiben, Zeile(n) anhaengen."""
    from metals.metals_engine import analyze_all, track_signals, get_stats, export_csv
    from metals.metals_store import save_state, log_scan, scan_count

    vorher = scan_count()
    analysen, gs_ratio = analyze_all()

    fehler = [a for a in analysen if a.get("error")]
    for a in fehler:
        log("METALLE", f"Quelle gestoert: {a.get('name')} -> {a['error']}")
    if len(fehler) == len(analysen):
        raise RuntimeError("keine einzige Metallreihe abrufbar")

    journal, neu = track_signals(analysen)
    export_csv(journal)
    stats = get_stats(journal)
    save_state(analysen, gs_ratio, stats)
    log_scan(analysen, gs_ratio)

    nachher = scan_count()
    for a in analysen:
        if a.get("error"):
            continue
        log("METALLE", f"{a['name']:<7} {a['price']:>10,.2f}$  Score {a['score']:>3}  "
                       f"{a['signal']}")
    log("METALLE", f"Zeilen im scan_log: {vorher} -> {nachher} (+{nachher - vorher})")
    log("METALLE", f"Signale: {neu} neu | offen {stats['open']} | "
                   f"geschlossen {stats['closed']}")
    if stats["closed"] and stats["closed"] < 30:
        log("METALLE", f"Hinweis: nur {stats['closed']} geschlossene Signale - "
                       f"die Trefferquote ist noch keine Aussage.")
    return {"scans": nachher, "neue_signale": neu,
            "offen": stats["open"], "geschlossen": stats["closed"]}


# ======================================================================
# GELDFLUSS
# ======================================================================
def sammle_geldfluss():
    """Tagesschnappschuss holen bzw. einen unvollstaendigen Tag ergaenzen."""
    from ui.geldfluss_tab import sammle_snapshot          # kein Tkinter beim Import
    st = sammle_snapshot(force=True)

    for quelle, grund in sorted((st.get("fehler") or {}).items()):
        log("GELDFLUSS", f"Quelle gestoert: {quelle} -> {grund}")
    if not st["coingecko"] and not st["yfinance"]:
        raise RuntimeError("keine einzige Quelle erreichbar")

    log("GELDFLUSS", f"CoinGecko {'ok' if st['coingecko'] else 'AUSFALL'} | "
                     f"yfinance {', '.join(st['yfinance']) or 'AUSFALL'}")
    if st.get("archiv_fehler"):
        log("GELDFLUSS", f"Archiv: {st['archiv_fehler']}")
    else:
        log("GELDFLUSS", f"Archiv: {st['tage']} Tage, davon {st['vollstaendig']} "
                         f"vollstaendig")
        if st["vollstaendig"] < st["tage"]:
            log("GELDFLUSS", f"{st['tage'] - st['vollstaendig']} Tag(e) unvollstaendig - "
                             f"nur der heutige kann noch ergaenzt werden.")
    return st


# ======================================================================
# ZYKLUS
# ======================================================================
def _zyklus_alter_tage():
    """Alter des letzten Datensatzes in situation_history.json, oder None."""
    try:
        with open(ZYKLUS_DATEI, encoding="utf-8") as f:
            d = json.load(f)
        letzter = d["days"][-1]["date"]
        return (date.today() - date.fromisoformat(letzter)).days, letzter, d.get("count")
    except Exception:
        return None, None, None


def sammle_zyklus(max_alter=1, force=False):
    """Baut situation_history.json neu, wenn sie zu alt ist.

    Der Harvester laedt die komplette Tageshistorie neu und schreibt atomar
    (tmp -> json.load-Pruefung -> os.replace). Damit ist der Lauf idempotent:
    zweimal ausgefuehrt ergibt denselben Stand. Ein Vollaufbau kostet ein
    paar Minuten (paginierte ccxt-Abfragen mit Rate-Limit) - fuer einen
    Tagesjob unkritisch und deutlich robuster als ein Teil-Merge.
    """
    alter, letzter, anzahl = _zyklus_alter_tage()
    if alter is not None:
        log("ZYKLUS", f"Bestand: {anzahl} Tage bis {letzter} ({alter} Tage alt)")
        if alter <= max_alter and not force:
            log("ZYKLUS", f"frisch genug (<= {max_alter} Tage) - uebersprungen")
            return {"uebersprungen": True, "alter": alter, "letzter": letzter}
    else:
        log("ZYKLUS", "kein Bestand gefunden - Erstaufbau")

    import history_harvester as hh
    bars = hh.fetch_candles("BTC/USDT")
    if len(bars) < 300:
        raise RuntimeError(f"nur {len(bars)} Kerzen erhalten - Abbruch")
    fg = hh.fetch_fear_greed()
    rows = hh.add_labels_and_outcomes(hh.build_rows(bars, fg))
    hh.save(rows, ZYKLUS_DATEI, "BTC/USDT")

    neu_alter, neu_letzter, neu_anzahl = _zyklus_alter_tage()
    log("ZYKLUS", f"neu: {neu_anzahl} Tage bis {neu_letzter} ({neu_alter} Tage alt)")
    # Die letzten 90 Zeilen haben bewusst outcome=null - das Vorhersagefenster
    # ist dort noch nicht abgelaufen. Das ist kein Fehler, sondern genau die
    # Regel, die Look-ahead-Bias verhindert.
    offen = sum(1 for r in rows if r["outcome"]["fwd_90d"] is None)
    log("ZYKLUS", f"{offen} Tage ohne fwd_90d (Vorhersagefenster laeuft noch) - korrekt")
    return {"uebersprungen": False, "tage": neu_anzahl, "letzter": neu_letzter}


# ======================================================================
# Hauptlauf
# ======================================================================
def _schreibe_protokoll(ergebnis):
    """Letzten Lauf festhalten - damit die Tabs zeigen koennen, wann zuletzt
    gesammelt wurde, statt nur wie alt die Daten sind."""
    try:
        os.makedirs(os.path.dirname(PROTOKOLL), exist_ok=True)
        tmp = PROTOKOLL + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ergebnis, f, indent=1, ensure_ascii=False)
        os.replace(tmp, PROTOKOLL)
    except Exception as e:
        log("SAMMLER", f"Protokoll nicht schreibbar: {str(e)[:60]}")


def main():
    ap = argparse.ArgumentParser(
        description="Sammelt Daten fuer METALLE / GELDFLUSS / ZYKLUS. "
                    "Faesst den Bot nicht an und handelt nichts.")
    ap.add_argument("--nur", choices=["metalle", "geldfluss", "zyklus"],
                    help="nur einen Bereich sammeln")
    ap.add_argument("--force", action="store_true",
                    help="Zyklus auch dann neu bauen, wenn er frisch ist")
    ap.add_argument("--max-alter", type=int, default=1,
                    help="ab wie vielen Tagen der Zyklus neu gebaut wird (Vorgabe 1)")
    args = ap.parse_args()

    bereiche = [args.nur] if args.nur else ["metalle", "geldfluss", "zyklus"]
    ergebnis = {"start_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "bereiche": {}}
    fehlgeschlagen = []

    print("=" * 66)
    print("  SAMMLER - METALLE / GELDFLUSS / ZYKLUS   (reine Datenerfassung)")
    print("=" * 66)

    for b in bereiche:
        try:
            if b == "metalle":
                ergebnis["bereiche"][b] = sammle_metalle()
            elif b == "geldfluss":
                ergebnis["bereiche"][b] = sammle_geldfluss()
            elif b == "zyklus":
                ergebnis["bereiche"][b] = sammle_zyklus(args.max_alter, args.force)
            ergebnis["bereiche"][b]["ok"] = True
        except Exception as e:
            fehlgeschlagen.append(b)
            ergebnis["bereiche"][b] = {"ok": False,
                                       "fehler": f"{type(e).__name__}: {str(e)[:150]}"}
            log(b.upper(), f"FEHLGESCHLAGEN: {type(e).__name__}: {str(e)[:120]}")
            traceback.print_exc()

    ergebnis["ende_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ergebnis["fehlgeschlagen"] = fehlgeschlagen
    _schreibe_protokoll(ergebnis)

    print("-" * 66)
    if fehlgeschlagen:
        print(f"  FERTIG MIT FEHLERN: {', '.join(fehlgeschlagen)}")
        return 1
    print(f"  FERTIG: {', '.join(bereiche)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
