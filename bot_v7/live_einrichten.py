# -*- coding: utf-8 -*-
"""live_einrichten.py - legt eine ZWEITE Instanz fuer den Echtgeld-Betrieb an.

WOZU
----
Sven am 14.09.2026: *"koennen wir trotzdem nebenbei den paperbetrieb weiter
laufen lassen damit wir da daten sammeln"*

Ja - aber nicht im selben Prozess. `trading.mode` ist eine einzige
Einstellung: ein Bot ist entweder Papier oder Echtgeld, nie beides.

WARUM DAS WICHTIG IST, UND NICHT NUR BEQUEM
-------------------------------------------
Die laufende Epoche E9 misst die Warte-Auftraege und vier Patches. Am
14.09. standen dort **3 Verkaeufe** von 100, die Kriterium A braucht.
Wuerde der Papierhandel jetzt abgeschaltet, waere diese Messung nach
1,8 Tagen zu Ende - und das ist genau der Mechanismus, der das Projekt
sieben Monate zurueckgeworfen hat: aus sieben Monaten Laufzeit wurden
durch staendige Umstellungen sechs Tage verwertbare Daten.

Zwei getrennte Instanzen loesen das:

    Ordner 1 (dieser)   Papier, E9 laeuft weiter, sammelt Daten
    Ordner 2 (neu)      Echtgeld, kleiner Deckel, eigene Buchhaltung

WARUM SIE SICH NICHT IN DIE QUERE KOMMEN
----------------------------------------
Die Doppelstart-Sperre (Befund 93, `core/startsperre.py`) legt ihre
Sperrdatei in `data_store/` ab - also **pro Ordner**. Zwei Installationen
in getrennten Ordnern sehen einander nicht und blockieren sich nicht.
Innerhalb eines Ordners bleibt der Schutz dagegen bestehen.

Ebenso getrennt: `bot_state.json`, alle Datenbanken, das Journal, die
Logs. Nichts davon wird geteilt - sonst schriebe der Echtgeld-Bot in die
Messung des Papier-Bots.

WAS DIESES PROGRAMM NICHT TUT
-----------------------------
**Es fasst keine Schluessel an.** Die `.env` mit den API-Daten wird NICHT
kopiert - das muss von Hand geschehen. Ein Werkzeug, das Zugangsdaten
herumreicht, ist ein Werkzeug zu viel.

Es startet auch nichts. Am Ende steht ein fertiger Ordner und eine
Anleitung, was noch von Hand zu tun ist.

    python live_einrichten.py --pruefen    zeigt nur, was passieren wuerde
    python live_einrichten.py --anlegen    legt den Ordner wirklich an
"""
import io
import json
import os
import shutil
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(os.path.dirname(HIER), "trading_imperium_LIVE")

# Was NICHT mitkommt. Daten, Geschichte und alles, was die zweite
# Instanz mit der ersten verkleben wuerde.
NICHT_MIT = {
    "data_store",        # 808 MB Messdaten - die zweite Instanz faengt frisch an
    ".git", "docs", "archiv", "__pycache__", "grafiken",
    "BOT-DATEN_20260810_2119", "_archive_20260812_144758",
    "aufgabenplanung_backup", "patches_nach_27_08",
    ".claude", "chartlabor",
}
NICHT_MIT_DATEI = {
    ".env",              # SCHLUESSEL - kommen nie automatisch mit
}

# ====================================================================
# Diese Einstellungen bekommt die neue Instanz.
#
# AUF 35 EURO STARTKAPITAL ZUGESCHNITTEN, am 14.09.2026 durchgerechnet.
# Mit den Papier-Einstellungen (30 %, 3 Positionen, 3 Nachkaeufe) waere
# der Bot bei diesem Betrag halb gelaehmt:
#
#     Position 1  10,50 $     Position 2  7,35 $     Position 3  5,14 $
#     Nachkauf    3,60 $  ->  UNTER dem Boersen-Minimum von 5 $
#
# Drei winzige Positionen, und die Nachkaeufe werden von der Boerse
# abgelehnt - jede Ablehnung zaehlt auf den Rejection-Counter und kann
# den Bot in den Schlafmodus schicken.
# ====================================================================
LIVE_EINSTELLUNGEN = {
    "trading": {
        "mode": "live",
        # Nur noch gute Signale. Befund 103, an 57 Verkaeufen gemessen:
        #   Score 3-6   -0,540 %   60,9 % Treffer
        #   Score 7-10  +0,468 %   79,4 % Treffer
        # Der Papier-Bot bleibt bei 3 und misst weiter - damit ist der
        # Vergleich erhalten und die Schwelle bestaetigt sich vorwaerts
        # oder eben nicht.
        "min_signal_score": 7,
        # EINE ordentliche Position statt drei winzige.
        "position_size_pct": 50.0,
        "max_open_positions": 1,
        "max_trades": 1,
        # Nachkaeufe aus: bei 35 $ liegt die dritte Stufe unter dem
        # Boersen-Mindestbetrag und wuerde nur Ablehnungen erzeugen.
        "dca_enabled": False,
    },
    "risk": {
        "live_require_gate": False,   # bewusst aus, Freigabe Sven 14.09.
        "live_max_order_usd": 25.0,
        "live_max_capital_usd": 200.0,
    },
}


def groesse(pfad):
    n = 0
    for w, u, d in os.walk(pfad):
        u[:] = [x for x in u if x not in NICHT_MIT]
        for f in d:
            try:
                n += os.path.getsize(os.path.join(w, f))
            except OSError:
                pass
    return n


def kopieren(nur_zeigen=True):
    print("=" * 74)
    print("  ZWEITE INSTANZ FUER DEN ECHTGELD-BETRIEB")
    print("=" * 74)
    print()
    print("  Von : %s" % HIER)
    print("  Nach: %s" % ZIEL)
    print()

    if os.path.exists(ZIEL):
        print("  Der Zielordner gibt es schon.")
        print("  Es wird NICHTS ueberschrieben - bitte vorher wegraeumen")
        print("  oder umbenennen.")
        return 1

    mb = groesse(HIER) / 1024.0 / 1024.0
    print("  Zu kopieren: rund %.0f MB (nur Programmcode)" % mb)
    print()
    print("  Ausgenommen, und zwar mit Absicht:")
    for x in sorted(NICHT_MIT):
        grund = {"data_store": "die Messdaten - die neue Instanz faengt frisch an",
                 ".git": "Versionsgeschichte",
                 "docs": "Dokumentation",
                 "archiv": "Altlasten"}.get(x, "")
        print("    %-26s %s" % (x, grund))
    for x in sorted(NICHT_MIT_DATEI):
        print("    %-26s %s" % (x, "SCHLUESSEL - von Hand, nie automatisch"))

    if nur_zeigen:
        print()
        print("-" * 74)
        print("  Das war der Trockenlauf. Wirklich anlegen mit:")
        print("      python live_einrichten.py --anlegen")
        print("-" * 74)
        return 0

    # ------------------------------------------------------- kopieren
    print()
    print("  kopiere ...")

    def ignoriere(ordner, eintraege):
        raus = set()
        for e in eintraege:
            if e in NICHT_MIT or e in NICHT_MIT_DATEI:
                raus.add(e)
            elif e.endswith(".pyc") or e == "__pycache__":
                raus.add(e)
        return raus

    shutil.copytree(HIER, ZIEL, ignore=ignoriere)
    print("    Programmcode ist drueben.")

    # ------------------------------------- frisches Datenverzeichnis
    ds = os.path.join(ZIEL, "data_store")
    os.makedirs(ds, exist_ok=True)

    # Die Konfiguration: aus der bestehenden ableiten, damit Muenzen,
    # Schwellen und Modi gleich bleiben - nur der Betriebsmodus aendert
    # sich. Eine frisch gebaute Konfiguration haette alle Vorgabewerte
    # und damit ein anderes Verhalten als der Papier-Bot.
    quelle_cfg = os.path.join(HIER, "data_store", "config.json")
    with io.open(quelle_cfg, encoding="utf-8") as f:
        cfg = json.load(f)
    for block, werte in LIVE_EINSTELLUNGEN.items():
        cfg.setdefault(block, {}).update(werte)
    cfg["_kommentar_live"] = (
        "ECHTGELD-INSTANZ, angelegt 14.09.2026. Abgeleitet aus der "
        "Papier-Konfiguration, damit Muenzen und Schwellen identisch sind - "
        "geaendert wurden NUR mode, live_require_gate und die Deckel. "
        "Der Papier-Bot laeuft daneben weiter und misst Epoche E9.")
    with io.open(os.path.join(ds, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("    Konfiguration geschrieben: mode=live, Gate aus, Deckel 25/200 $.")

    # Epochendatei: die neue Instanz beginnt eine eigene Zeitrechnung
    epochen = {
        "_comment": ("Echtgeld-Instanz. Eigene Zeitrechnung - die Epochen des "
                     "Papier-Bots gelten hier NICHT, weil dort mit anderen "
                     "Kosten und ohne Orderbuch gerechnet wird."),
        "epochs": [{
            "id": "L1_echtgeld_start",
            "start": "",
            "label": "Erster Echtgeld-Betrieb, Bybit EU",
            "note": ("Startzeit wird beim ersten Lauf eingetragen. Deckel: "
                     "25 $ je Order, 200 $ Kapital. Freigabepruefung "
                     "ausgeschaltet - Sven am 14.09.2026, ausdruecklich und "
                     "im Wissen, dass die Kriterien B, C, E und F nicht "
                     "erfuellt sind."),
            "changes": ["mode=live", "boerse=bybit.eu", "gate=aus"],
        }],
    }
    with io.open(os.path.join(ZIEL, "config_epochs.json"), "w",
                 encoding="utf-8") as f:
        json.dump(epochen, f, indent=2, ensure_ascii=False)
    print("    Eigene Epochendatei angelegt (L1_echtgeld_start).")

    print()
    print("=" * 74)
    print("  FERTIG - drei Dinge noch von Hand")
    print("=" * 74)
    print()
    print("  1. Die Datei .env aus diesem Ordner hierher kopieren:")
    print("       %s" % os.path.join(ZIEL, ".env"))
    print("     Sie enthaelt die Schluessel. Deshalb macht das kein Programm.")
    print()
    print("  2. Geld auf das Bybit-EU-Konto einzahlen. Am 14.09. war es leer -")
    print("     ohne Guthaben kauft der Bot nichts.")
    print()
    print("  3. Starten mit START_LIVE.bat im neuen Ordner.")
    print()
    print("  Der Papier-Bot hier laeuft unabhaengig weiter und misst E9.")
    return 0


if __name__ == "__main__":
    anlegen = "--anlegen" in sys.argv
    code = kopieren(nur_zeigen=not anlegen)
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
