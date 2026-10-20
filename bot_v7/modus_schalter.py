# -*- coding: utf-8 -*-
"""modus_schalter.py - zwischen Papierhandel und Echtgeld umschalten.

Aufruf:
    python modus_schalter.py --stand        nur nachsehen, aendert nichts
    python modus_schalter.py --paper        auf Papierhandel
    python modus_schalter.py --live         auf Echtgeld (fragt nach)
    python modus_schalter.py --kapital 25   Startkapital Papier setzen

WOZU ES DIESES WERKZEUG GIBT
----------------------------
Umgeschaltet wird eine einzige Zahl: trading.mode in
data_store/config.json. Das von Hand zu aendern waere ein Zweizeiler -
gefaehrlich sind nicht die zwei Zeilen, sondern die drei Dinge, die man
dabei vergisst.

1. DER BOT LIEST DIE KONFIGURATION NUR BEIM START.
   execution/engine.py:35 setzt _paper_mode im Konstruktor. Wer im
   laufenden Betrieb umschaltet - auch ueber den Knopf in der
   Oberflaeche (ui/main_window.py:2067) -, aendert die Datei und NICHT
   das Verhalten. Der Bot handelt weiter wie vorher, die Anzeige
   behauptet das Gegenteil. Dieses Werkzeug verweigert deshalb den
   Dienst, solange der Bot laeuft.

2. EINE OFFENE ECHTE POSITION UEBERLEBT DEN WECHSEL NICHT.
   Schaltet man auf Papier, waehrend an der Boerse Coins liegen, fuehrt
   der Bot sie nicht mehr in seinem Register - und damit bewacht sie
   kein Stop-Loss mehr. Die Position bleibt liegen, sie verschwindet
   nur aus dem Blick. Genau diese Lage gab es am 14.09.2026 schon
   einmal, nachzulesen im Kopf von bestand_pruefen.py: die Coins liegen
   auf dem Konto, im Register stehen sie nicht, also bewacht sie kein
   Stop-Loss.

3. EIN OFFENER WARTE-AUFTRAG LIEGT AN DER BOERSE, NICHT IM PROGRAMM.
   Seit Epoche L4 kauft der Bot ueber Limit-Orders. Traegt ein Auftrag
   in data_store/warteauftraege.json eine live_order_id, dann kennt
   Bybit ihn. Ein Moduswechsel loescht ihn nicht. Er kann danach
   bedient werden, wenn niemand mehr hinsieht.

Punkt 2 und 3 pruefe ich gegen die ZUSTANDSDATEIEN, nicht gegen die
Boerse. Das ist Absicht: dieses Werkzeug laeuft ohne Netz und ohne
Zugangsdaten. Was wirklich auf dem Konto liegt, beantwortet allein
python bestand_pruefen.py.

Beide Sperren lassen sich mit --trotzdem uebergehen. Wer das tut,
sollte vorher bestand_pruefen.py gelesen haben.

Angelegt 21.09.2026 beim Umzug auf den Windows-11-Rechner.
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HIER, "data_store", "config.json")
ZUSTAND = os.path.join(HIER, "data_store", "bot_state.json")
WARTE = os.path.join(HIER, "data_store", "warteauftraege.json")


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


def _lies(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def bot_laeuft():
    """Laeuft ein Bot AUS DIESEM ORDNER? Gibt (pid, aufruf) oder None.

    Der Vergleich geht ueber das Arbeitsverzeichnis, nicht ueber die
    Befehlszeile: app.py passt auf jeden Bot-Ordner auf diesem Rechner.
    Denselben blinden Fleck hatte schatten_starter.py bis zum
    16.09.2026.

    Zwei Fallen, beide am 25.09.2026 in der Praxis zugeschnappt:

    1. "app.py" IRGENDWO in der Befehlszeile zu suchen trifft auch
       Prozesse, die den Namen nur als Text fuehren - etwa eine Shell
       oder ein Pruefskript, das selbst nach "app.py" sucht. Genau das
       meldete dreimal einen laufenden Bot, wo keiner lief. Deshalb muss
       app.py ein EIGENES Argument sein, kein Teilstring.

    2. Der eigene Prozess und seine Elternprozesse werden ausgenommen -
       sie laufen im selben Ordner und wuerden sich sonst selbst finden.
    """
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
                return (p.info["pid"], " ".join(teile)[:70])
        except Exception:
            continue
    return None


def offene_positionen():
    roh = _lies(ZUSTAND).get("open_positions_backup") or {}
    if not isinstance(roh, dict):
        return {}
    return dict((k, v) for k, v in roh.items()
                if isinstance(v, dict) and v.get("active"))


def offene_warteauftraege():
    """Auftraege, die eine echte Boersen-Auftragsnummer tragen."""
    roh = _lies(WARTE).get("auftraege") or {}
    if not isinstance(roh, dict):
        return {}
    treffer = {}
    for k, v in roh.items():
        if isinstance(v, dict) and (v.get("angaben") or {}).get("live_order_id"):
            treffer[k] = v
    return treffer


def _zeitstempel(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%d.%m. %H:%M")
    except Exception:
        return "?"


def stand_zeigen(cfg):
    banner("BETRIEBSMODUS - Stand")
    t = cfg.get("trading", {})
    r = cfg.get("risk", {})
    modus = t.get("mode", "?")
    print()
    print("  Modus                " + str(modus).upper())
    if modus == "live":
        warn("ECHTES GELD. Jeder Kauf geht an die Boerse.")
    elif modus == "paper":
        ok("Papierhandel. Keine echte Order verlaesst den Rechner.")
    else:
        stop("Unbekannter Wert. engine.py behandelt alles ausser "
             "paper als ECHTGELD.")

    print("  Startkapital Papier  %s USDC" % t.get("initial_paper_balance"))
    print("  Deckel je Order      %s USD" % r.get("live_max_order_usd"))
    print("  Deckel Gesamt        %s USD" % r.get("live_max_capital_usd"))
    print("  Muenzen              %s" % ", ".join(t.get("coins", [])))

    print()
    lauf = bot_laeuft()
    if lauf:
        warn("Bot laeuft (PID %s) - Umschalten ist gesperrt." % lauf[0])
    else:
        ok("Kein Bot aus diesem Ordner aktiv.")

    pos = offene_positionen()
    if pos:
        warn("%d offene Position(en) im Register:" % len(pos))
        for sym, p in pos.items():
            print("            %-10s Menge %s  Einstand %.2f  Einsatz %.2f USD"
                  % (sym, p.get("qty"), p.get("entry_price") or 0,
                     p.get("cost_basis") or 0))
        info("Was WIRKLICH auf dem Konto liegt: python bestand_pruefen.py")
    else:
        ok("Keine offene Position im Register.")

    wa = offene_warteauftraege()
    if wa:
        warn("%d Warte-Auftrag/-Auftraege mit Boersen-Nummer:" % len(wa))
        for sym, a in wa.items():
            print("            %-10s Limit %.2f  verfiel %s  Nr. %s"
                  % (sym, a.get("limitpreis") or 0,
                     _zeitstempel(a.get("verfaellt_ts")),
                     (a.get("angaben") or {}).get("live_order_id")))
        info("Ein Moduswechsel loescht diese Auftraege NICHT.")
    else:
        ok("Kein Warte-Auftrag mit Boersen-Nummer.")
    print()
    print("=" * 72)
    return 0


def umschalten(cfg, ziel, trotzdem, kapital):
    banner("BETRIEBSMODUS umschalten  ->  " + ziel.upper())
    jetzt = cfg.get("trading", {}).get("mode", "?")
    print()
    print("  von %s  nach  %s" % (str(jetzt).upper(), ziel.upper()))
    print()

    if jetzt == ziel and kapital is None:
        info("Steht bereits auf %s. Nichts zu tun." % ziel)
        return 0

    sperren = []

    lauf = bot_laeuft()
    if lauf:
        stop("Der Bot laeuft (PID %s)." % lauf[0])
        info("Er liest die Konfiguration nur beim Start. Umschalten "
             "waehrend des Betriebs aendert die Datei, nicht das "
             "Verhalten. Erst beenden, dann umschalten, dann starten.")
        sperren.append("bot_laeuft")

    pos = offene_positionen()
    if pos and ziel == "paper":
        stop("%d offene Position(en) im Register." % len(pos))
        for sym, p in pos.items():
            print("            %-10s Einsatz %.2f USD"
                  % (sym, p.get("cost_basis") or 0))
        info("Auf Papier fuehrt der Bot sie nicht mehr - dann bewacht sie "
             "kein Stop-Loss. Erst verkaufen oder bewusst uebernehmen.")
        info("Pruefen mit: python bestand_pruefen.py")
        sperren.append("offene_position")

    wa = offene_warteauftraege()
    if wa:
        stop("%d Warte-Auftrag/-Auftraege mit Boersen-Nummer." % len(wa))
        info("Die liegen bei Bybit, nicht im Programm. Ein Moduswechsel "
             "loescht sie nicht.")
        sperren.append("warteauftrag")

    if sperren and not trotzdem:
        print()
        print("  " + "-" * 68)
        stop("NICHT umgeschaltet. Grund: " + ", ".join(sperren))
        info("Bewusst uebergehen: --trotzdem")
        print("=" * 72)
        return 1

    if sperren and trotzdem:
        warn("Sperren uebergangen (--trotzdem): " + ", ".join(sperren))

    if ziel == "live":
        print()
        warn("ZIEL IST ECHTGELD. Ab dem naechsten Start gehen Kaeufe "
             "an die Boerse.")
        antwort = input("  Zum Bestaetigen genau  ECHTGELD  eingeben: ")
        if antwort.strip() != "ECHTGELD":
            print()
            stop("Abgebrochen, nichts geaendert.")
            return 1

    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    sicherung = CONFIG + ".sicherung_" + stempel
    shutil.copy2(CONFIG, sicherung)
    print()
    ok("Sicherung: " + os.path.basename(sicherung))

    cfg.setdefault("trading", {})["mode"] = ziel
    if kapital is not None:
        alt = cfg["trading"].get("initial_paper_balance")
        cfg["trading"]["initial_paper_balance"] = float(kapital)
        ok("Startkapital Papier: %s -> %s USDC" % (alt, float(kapital)))

    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    ok("trading.mode = " + ziel)

    nach = _lies(CONFIG).get("trading", {}).get("mode")
    if nach != ziel:
        stop("Nachlesen ergab einen anderen Wert - die Datei wurde NICHT "
             "richtig geschrieben.")
        return 1
    ok("Nachgelesen: steht auf " + str(nach))

    print()
    info("Der Bot muss NEU GESTARTET werden - er liest die Konfiguration "
         "beim Start.")
    print("=" * 72)
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Zwischen Papierhandel und Echtgeld umschalten.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--stand", action="store_true",
                   help="nur nachsehen, aendert nichts (Vorgabe)")
    g.add_argument("--paper", action="store_true", help="auf Papierhandel")
    g.add_argument("--live", action="store_true", help="auf Echtgeld")
    p.add_argument("--kapital", type=float, default=None,
                   help="Startkapital fuer den Papierhandel in USDC")
    p.add_argument("--trotzdem", action="store_true",
                   help="Sperren bewusst uebergehen")
    a = p.parse_args()

    if not os.path.exists(CONFIG):
        stop("data_store/config.json nicht gefunden: " + CONFIG)
        return 1
    cfg = _lies(CONFIG)
    if not cfg:
        stop("config.json ist leer oder unlesbar - nichts geaendert.")
        return 1

    if a.paper:
        return umschalten(cfg, "paper", a.trotzdem, a.kapital)
    if a.live:
        return umschalten(cfg, "live", a.trotzdem, a.kapital)
    if a.kapital is not None:
        jetzt = cfg.get("trading", {}).get("mode", "paper")
        return umschalten(cfg, jetzt, a.trotzdem, a.kapital)
    return stand_zeigen(cfg)


if __name__ == "__main__":
    sys.exit(main())
