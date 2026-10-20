# -*- coding: utf-8 -*-
"""papierwechsel.py - der Weg vom Echtgeld zurueck in den Papierbetrieb.

Aufruf:  python papierwechsel.py
         python papierwechsel.py --kapital 500

Fragt vor jeder Aenderung nach. Ohne ein getipptes "ja" passiert nichts.

WARUM ES DIESES WERKZEUG GIBT
-----------------------------
Der Wechsel braucht drei Schritte, und zwei davon fassen Dateien an, die
unter Bestandsschutz stehen (.claude/hooks/GESCHUETZTE-DATEIEN.txt):

    1. bot_state.json      die Phantom-Position aus dem Register nehmen
    2. config_epochs.json  die Epochengrenze eintragen
    3. data_store/config.json   trading.mode auf paper

Genau wie phantom_position_bereinigen.py ist das bewusst ein WERKZEUG und
kein Automatismus: Ein Mensch startet es, ein Mensch bestaetigt. Deshalb
darf es schreiben, was ein Hook einem Assistenten verwehrt.

WARUM NICHT phantom_position_bereinigen.py
------------------------------------------
Das gibt es schon - aber es loest einen ANDEREN Fall. Es wurde am
15.09.2026 fuer die Verkaufsseite gebaut: Der Bot verkaufte erfolgreich,
hielt den Verkauf fuer gescheitert, und die Position blieb im Register.
Seine Bedingung 3 verlangt deshalb einen passenden VERKAUF in den
Ausfuehrungen der Boerse.

Der Fall hier ist die Kaufseite. Am 17.09. lag eine BTC-Position im
Register, und danach hat Sven sein Geld selbst vom Konto genommen,
waehrend der Bot aus war. Es gibt also keinen Verkauf DES BOTS zu
finden - und wegen des Abruffensters der Boerse (die Ausfuehrungen sind
acht bis zehn Tage alt) waere er ohnehin unsichtbar. Bedingung 3 schlaegt
fehl, obwohl die Lage eindeutig ist.

Deshalb prueft dieses Werkzeug anders, aber nicht schwaecher:

    A. Laeuft ein Bot aus diesem Ordner?   -> dann Abbruch
    B. Liegt die Muenze WIRKLICH nicht auf dem Konto?
       Gefragt wird die Boerse, nur lesend. Liegt sie doch da, Abbruch -
       eine Position aus dem Register zu nehmen, die es gibt, heisst den
       Stop-Loss auf einen echten Bestand zu verlieren. Das waere
       schlimmer als das Problem.

WARUM DIE PHANTOM-POSITION UEBERHAUPT WEG MUSS
----------------------------------------------
Nicht aus Ordnungsliebe. app.py:4749 sagt es selbst, im Kommentar zum
Doppelverkauf-Fix vom 13.08.2026:

    "Im Papiermodus kostet das nur falsche Zahlen."

Beim Start holt restore_positions() die Position aus dem Register zurueck.
Im Papierbetrieb wuerde der Bot sie dann als echte Position fuehren, ihr
Stop-Loss loest aus, und ein erfundener Trade landet im Journal - in genau
der Messung, fuer die der Papierbetrieb da ist.

core/state_store.py:30 liest Haupt-, .bak- und .tmp-Datei der Reihe nach.
Alle drei werden deshalb behandelt, sonst kommt das Phantom zurueck.

Angelegt 25.09.2026, Freigabe Sven ausdruecklich.
"""
import argparse
import io
import json
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HIER, "data_store", "config.json")
ZUSTAND = os.path.join(HIER, "data_store", "bot_state.json")
EPOCHEN = os.path.join(HIER, "config_epochs.json")

EPOCHE_ID = "L5_zurueck_auf_papier"


def banner(t):
    print()
    print("=" * 72)
    print("  " + t)
    print("=" * 72)


def ok(t):
    print("  [ok]    " + t)


def warn(t):
    print("  [!]     " + t)


def stop(t):
    print("  [STOP]  " + t)


def info(t):
    print("  [i]     " + t)


def lies(pfad):
    with io.open(pfad, encoding="utf-8") as f:
        return json.load(f)


def schreib_atomar(pfad, daten):
    """Erst .schreibtmp + fsync, dann os.replace - wie core/state_store.py."""
    tmp = pfad + ".schreibtmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, pfad)


def bot_laeuft():
    """Laeuft app.py AUS DIESEM ORDNER? app.py muss ein eigenes Argument
    sein - als Teilstring trifft es auch Pruefskripte, die den Namen nur
    im Text fuehren."""
    try:
        import psutil
    except ImportError:
        return None
    eigene = {os.getpid()}
    try:
        eigene.update(a.pid for a in psutil.Process().parents())
    except Exception:
        pass
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["pid"] in eigene:
                continue
            if "python" not in (p.info["name"] or "").lower():
                continue
            teile = p.info["cmdline"] or []
            if not any(os.path.basename(t).lower() == "app.py" for t in teile):
                continue
            if os.path.normcase(p.cwd()) == os.path.normcase(HIER):
                return p.info["pid"]
        except Exception:
            continue
    return None


def boersenbestand(symbole):
    """Was liegt wirklich auf dem Konto? NUR LESEN.

    Dieselben drei Einstellungen wie bestand_pruefen.py - hostname
    bybit.eu, defaultType unified, recvWindow gross. Ohne sie landet man
    auf bybit.com oder bekommt einen leeren Kontostand trotz Guthaben.
    """
    try:
        import config.settings          # noqa: F401 - laedt .env
        import ccxt
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)

    key = os.getenv("BYBIT_API_KEY", "")
    secret = os.getenv("BYBIT_API_SECRET", "")
    if not key or not secret:
        return None, "keine Zugangsdaten (BYBIT_API_KEY/_SECRET)"

    try:
        ex = ccxt.bybit({
            "apiKey": key, "secret": secret, "enableRateLimit": True,
            "hostname": "bybit.eu",
            "options": {"defaultType": "unified",
                        "adjustForTimeDifference": True,
                        "recvWindow": 60000},
        })
        b = ex.fetch_balance()
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:120])

    gesamt = b.get("total") or {}
    return dict((s, float(gesamt.get(s.split("/")[0], 0) or 0))
                for s in symbole), None


def main():
    p = argparse.ArgumentParser(
        description="Vom Echtgeld zurueck in den Papierbetrieb.")
    p.add_argument("--kapital", type=float, default=None,
                   help="Startkapital Papier in USDC (sonst unveraendert)")
    a = p.parse_args()

    banner("WECHSEL IN DEN PAPIERBETRIEB")

    cfg = lies(CONFIG)
    modus = cfg.get("trading", {}).get("mode", "?")
    print()
    print("  Modus jetzt            %s" % str(modus).upper())
    print("  Startkapital Papier    %s USDC"
          % cfg.get("trading", {}).get("initial_paper_balance"))
    if a.kapital is not None:
        print("  Startkapital neu       %s USDC" % a.kapital)

    # --- A. Laeuft der Bot? ------------------------------------------
    print()
    pid = bot_laeuft()
    if pid:
        stop("Der Bot laeuft (PID %s)." % pid)
        info("Er liest die Konfiguration nur beim Start. Erst beenden, "
             "dann wechseln, dann starten.")
        return 1
    ok("Kein Bot aus diesem Ordner aktiv.")

    # --- Register lesen ----------------------------------------------
    zustand = lies(ZUSTAND)
    register = dict((k, v) for k, v in
                    (zustand.get("open_positions_backup") or {}).items()
                    if isinstance(v, dict) and v.get("active"))

    if not register:
        ok("Register ist leer - keine Phantom-Position zu entfernen.")
    else:
        print()
        warn("%d Position(en) im Register:" % len(register))
        for sym, pos in register.items():
            print("            %-10s Menge %s  Einstand %.2f  Einsatz %.2f USD"
                  % (sym, pos.get("qty"), pos.get("entry_price") or 0,
                     pos.get("cost_basis") or 0))

        # --- B. Gegenprobe an der Boerse -----------------------------
        print()
        info("Frage die Boerse, was wirklich da liegt (nur lesend)...")
        bestand, fehler = boersenbestand(list(register))
        if bestand is None:
            print()
            stop("Boerse nicht abfragbar: %s" % fehler)
            info("Ohne diese Gegenprobe wird NICHTS geaendert. Eine "
                 "Position aus dem Register zu nehmen, die es in "
                 "Wirklichkeit gibt, heisst den Stop-Loss auf einen "
                 "echten Bestand zu verlieren.")
            return 1

        echte = []
        for sym, pos in register.items():
            liegt = bestand.get(sym, 0.0)
            soll = float(pos.get("qty") or 0)
            print("            %-10s Register %.8f   Boerse %.8f"
                  % (sym, soll, liegt))
            # 1 % Toleranz: Staub und Rundung zaehlen nicht als Bestand.
            if liegt > soll * 0.01:
                echte.append(sym)

        if echte:
            print()
            stop("Diese Muenzen liegen WIRKLICH auf dem Konto: %s"
                 % ", ".join(echte))
            info("Das sind keine Phantome. Erst verkaufen oder bewusst "
                 "uebernehmen - hier wird nichts geaendert.")
            return 1
        ok("Keine der Positionen liegt auf dem Konto - alles Phantome.")

    # --- Was passieren wird ------------------------------------------
    print()
    print("  " + "-" * 68)
    print("  DAS WIRD GEAENDERT:")
    if register:
        print("    1. bot_state.json (+ .bak, .tmp): %d Position(en) raus"
              % len(register))
    print("    2. config_epochs.json: neue Epoche %s" % EPOCHE_ID)
    print("    3. data_store/config.json: trading.mode -> paper")
    if a.kapital is not None:
        print("       initial_paper_balance -> %s" % a.kapital)
    print("  Von jeder Datei wird vorher eine Sicherung angelegt.")
    print("  " + "-" * 68)
    print()
    try:
        antwort = input("  Durchfuehren? (ja/nein): ").strip().lower()
    except EOFError:
        print()
        stop("Keine Eingabe moeglich - abgebrochen, nichts geaendert.")
        return 1
    if antwort != "ja":
        print()
        stop("Abgebrochen. Es wurde NICHTS geaendert.")
        return 1

    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")

    def sichern(pfad):
        if os.path.exists(pfad):
            shutil.copy2(pfad, pfad + ".vor_papierwechsel_" + stempel)

    banner("AENDERUNGEN")

    # --- 1. Phantom raus, aus allen drei Zustandsdateien -------------
    if register:
        print()
        for endung in ("", ".bak", ".tmp"):
            pfad = ZUSTAND + endung
            if not os.path.exists(pfad):
                continue
            sichern(pfad)
            try:
                d = lies(pfad)
            except Exception as e:
                warn("%s nicht lesbar (%s) - unangetastet"
                     % (os.path.basename(pfad), type(e).__name__))
                continue
            pos = d.get("open_positions_backup") or {}
            entfernt = [s for s in register if s in pos]
            for s in entfernt:
                pos.pop(s, None)
            d["open_positions_backup"] = pos
            schreib_atomar(pfad, d)
            ok("%-22s %d entfernt, %d verbleiben"
               % (os.path.basename(pfad), len(entfernt), len(pos)))

    # --- 2. Epochengrenze -------------------------------------------
    print()
    sichern(EPOCHEN)
    alt = lies(EPOCHEN)
    alter_kommentar = alt.get("_comment", "")

    sys.path.insert(0, HIER)
    import epochs

    if any(e.get("id") == EPOCHE_ID for e in alt.get("epochs", [])):
        info("Epoche %s steht schon - nicht doppelt eingetragen." % EPOCHE_ID)
    else:
        jetzt = datetime.now(timezone.utc).isoformat()
        epochs.add_epoch(
            label="Zurueck auf Papierbetrieb",
            note=("Echtgeld beendet. Sven hat das Kapital am 25.09.2026 "
                  "selbst vom Konto genommen; die Boerse fuehrte danach "
                  "nur noch Staub (ETH 0.000268, USDC ~0). Der Bot lief "
                  "seit dem 17.09. nicht mehr. Ab hier ist jeder Trade "
                  "PAPIER - die Eintraege in trades_v5.json tragen KEIN "
                  "Modus-Feld (43 Felder geprueft, keines nennt paper "
                  "oder live), die Trennung von den 10 Echtgeld-Trades "
                  "laeuft daher ausschliesslich ueber diese Epochengrenze "
                  "und den Zeitstempel. Auswertungen muessen epochs.py "
                  "split_trades benutzen, sonst mischen sie Echtgeld und "
                  "Papier."),
            changes=["mode=live -> mode=paper",
                     "Phantom-Position BTC/USDC aus dem Register entfernt",
                     "veralteter Warte-Auftrag 2305796432030230786 verworfen"],
            start=jetzt,
            epoch_id=EPOCHE_ID)
        ok("Epoche %s eingetragen (%s)" % (EPOCHE_ID, jetzt))

        # epochs.save_epochs() schreibt einen eigenen _comment und wuerfe
        # damit den Hinweis auf die eigene Zeitrechnung dieses Ordners weg.
        neu = lies(EPOCHEN)
        if alter_kommentar and neu.get("_comment") != alter_kommentar:
            neu["_comment"] = (alter_kommentar +
                               "  [ab L5, 25.09.2026: PAPIERBETRIEB. Die "
                               "Trades davor sind Echtgeld, die danach "
                               "nicht - immer nach Epoche trennen.]")
            schreib_atomar(EPOCHEN, neu)
            ok("_comment erhalten und um den Papier-Hinweis ergaenzt")

    # --- 3. Modus ----------------------------------------------------
    print()
    sichern(CONFIG)
    cfg = lies(CONFIG)
    cfg.setdefault("trading", {})["mode"] = "paper"
    if a.kapital is not None:
        cfg["trading"]["initial_paper_balance"] = float(a.kapital)
    schreib_atomar(CONFIG, cfg)
    ok("trading.mode = paper")

    # --- Gegenprobe --------------------------------------------------
    banner("GEGENPROBE - nachgelesen, nicht angenommen")
    print()
    nach_cfg = lies(CONFIG)
    nach_modus = nach_cfg.get("trading", {}).get("mode")
    print("  trading.mode            %s" % nach_modus)
    print("  initial_paper_balance   %s"
          % nach_cfg.get("trading", {}).get("initial_paper_balance"))

    fehler = []
    if nach_modus != "paper":
        fehler.append("trading.mode steht nicht auf paper")

    for endung in ("", ".bak", ".tmp"):
        pfad = ZUSTAND + endung
        if not os.path.exists(pfad):
            continue
        try:
            rest = lies(pfad).get("open_positions_backup") or {}
        except Exception:
            continue
        aktiv = [k for k, v in rest.items()
                 if isinstance(v, dict) and v.get("active")]
        print("  %-22s aktive Positionen: %d"
              % (os.path.basename(pfad), len(aktiv)))
        if aktiv:
            fehler.append("%s fuehrt noch %s"
                          % (os.path.basename(pfad), ", ".join(aktiv)))

    ids = [e.get("id") for e in lies(EPOCHEN).get("epochs", [])]
    print("  Epochen                 %s" % ", ".join(ids))
    if EPOCHE_ID not in ids:
        fehler.append("Epoche %s fehlt" % EPOCHE_ID)

    print()
    if fehler:
        for f in fehler:
            stop(f)
        print("=" * 72)
        return 1

    ok("Alles wie gewollt.")
    print()
    info("Der Bot kann jetzt im Papierbetrieb gestartet werden.")
    info("Vorher noch: python prozess_frische.py")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
