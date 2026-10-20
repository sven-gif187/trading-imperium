# -*- coding: utf-8 -*-
"""whitelist_test.py - ueberlebt der Einstiegs-Score einen Neustart?

WOZU
----
Befund 88, Glied 3. `runtime/state_manager.py` speichert eine offene Position
nach `bot_state.json` - aber nicht vollstaendig, sondern nach einer
**Whitelist**. Der Kommentar an der Stelle warnt woertlich:

    "Diese Liste ist eine Whitelist: was nicht aufgezaehlt ist, ueberlebt
     keinen Neustart."

`entry_score` und `entry_strategie` standen nicht darin. Die Folge: `app.py`
schrieb den Score beim Kauf an die Position, der Exit-Monitor las ihn beim
Verkauf wieder aus - aber dazwischen lag ein Neustart, und der warf ihn weg.
Jede Position, die einen Neustart erlebte, wurde mit `entry_score=None`
verkauft.

Am 11.09.2026 am lebenden Objekt belegt: die damals offene BTC-Position in
`bot_state.json` trug genau 13 Felder, keines davon der Score. Bis dahin war
die Stelle nur vermutet - es hatte nie eine offene Position zum Mitlesen
gegeben.

Behoben am 11.09.2026: zwei Felder in die Whitelist.

DIESES PROGRAMM prueft den vollstaendigen Rundlauf - Position anlegen,
speichern, wieder laden - und zaehlt nach, welche Felder ankommen. Es prueft
in BEIDE Richtungen: es muss den Fehler finden, wenn er da ist, und
schweigen, wenn alles stimmt.

AENDERT NICHTS AM LAUFENDEN BOT. Es liest den Quelltext und rechnet den
Rundlauf auf einer eigenen Kopie nach - kein Zugriff auf bot_state.json.

    python whitelist_test.py
"""
import io
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(HIER, "runtime", "state_manager.py")

# Was eine Position mitbringen muss, damit die Auswertungen sie brauchen
# koennen. Die ersten vier sind die Ueberlebensfelder aus E9/Toepfe, die
# letzten zwei die aus Befund 88.
PFLICHT = [
    ("entry_price",     "ohne ihn rechnet der Stop-Loss am falschen Bezugspunkt"),
    ("cost_basis",      "ohne ihn rechnet der Gewinn wieder ohne Kaufgebuehr"),
    ("dca_levels",      "ohne ihn faengt die Nachkauf-Leiter bei 1 an"),
    ("position_id",     "ohne ihn bekommt dieselbe Position bei jedem Start eine neue Kennung"),
    ("entry_score",     "ohne ihn ist Befund 103 nicht vorwaerts pruefbar"),
    ("entry_strategie", "ohne ihn laesst sich nicht sagen, welche Strategie traegt"),
]

# Ein Feld, das es nicht geben darf - die Gegenprobe gegen ein Werkzeug,
# das einfach immer "ja" sagt.
ERFUNDEN = "gibt_es_nicht_xyz"


def whitelist_felder(text):
    """Liest die Feldnamen aus dem positions_data-Block."""
    anfang = text.find("positions_data[sym] = {")
    if anfang < 0:
        return None
    # bis zur schliessenden Klammer auf gleicher Einrueckung
    ende = text.find("\n                    }", anfang)
    if ende < 0:
        return None
    block = text[anfang:ende]
    # "feldname": ...   - Kommentarzeilen faengt das nicht, die haben kein "
    return set(re.findall(r'"([a-z_]+)"\s*:', block))


def rundlauf(felder, position):
    """Spielt Speichern und Laden nach: nur was in der Whitelist steht,
    kommt zurueck. Genau das macht state_manager.py."""
    gespeichert = {k: v for k, v in position.items() if k in felder}
    # Der Rueckladepfad (state_manager.py:239) nimmt das Dict ungefiltert:
    #     self.app.risk_engine.open_positions[sym] = pos
    return dict(gespeichert)


def main():
    print("=" * 70)
    print("  WHITELIST - ueberlebt der Einstiegs-Score einen Neustart?")
    print("=" * 70)
    print()

    if not os.path.exists(QUELLE):
        print("  runtime/state_manager.py nicht gefunden.")
        return 2

    text = io.open(QUELLE, encoding="utf-8").read()
    felder = whitelist_felder(text)
    if felder is None:
        print("  Der positions_data-Block wurde nicht gefunden.")
        print("  Wurde state_manager.py umgebaut? Dann muss dieser Test mit.")
        return 2

    print("  Die Whitelist fuehrt %d Felder:" % len(felder))
    print("    " + ", ".join(sorted(felder)))
    print()

    # Eine vollstaendige Position, wie app.py sie beim Kauf anlegt
    vorher = {
        "entry_price": 64925.31, "highest_price": 65052.0, "qty": 0.00276625,
        "active": True, "mode": "SL", "cost_basis": 179.78, "dca_levels": 1,
        "lowest_price": 64901.0, "hoechst_pnl_pct": 0.0,
        "position_id": "pos_BTC_pruefung", "topf": "haupt",
        "strategie_id": "EMA_TREND", "eroeffnet_ts": 1786000000.0,
        "entry_score": 8, "entry_strategie": "EMA_TREND",
        ERFUNDEN: "darf nicht ankommen",
    }
    nachher = rundlauf(felder, vorher)

    print("  Rundlauf: Position anlegen -> speichern -> neu laden")
    print()
    print("    %-18s %-12s %-12s %s" % ("Feld", "vorher", "nachher", ""))
    print("    " + "-" * 58)
    fehlt = []
    for name, warum in PFLICHT:
        da = name in nachher
        gleich = da and nachher[name] == vorher[name]
        zeichen = "ok" if gleich else "WEG"
        if not gleich:
            fehlt.append((name, warum))
        print("    %-18s %-12s %-12s %s" % (
            name, repr(vorher[name])[:11], repr(nachher.get(name))[:11], zeichen))
    print()

    # Gegenprobe: ein erfundenes Feld darf NICHT durchkommen
    print("  Gegenprobe - ein erfundenes Feld:")
    if ERFUNDEN in nachher:
        print("    %-20s ist durchgekommen - der Test taugt nichts," % ERFUNDEN)
        print("    denn er wuerde auch bei einer kaputten Whitelist 'ok' sagen.")
        return 2
    print("    %-20s nicht durchgekommen, richtig" % ERFUNDEN)
    print()

    # Gegentest: findet der Test den Fehler, wenn er da ist?
    print("  Gegentest - die alte Fassung ohne die zwei Felder:")
    alt = felder - {"entry_score", "entry_strategie"}
    alt_nachher = rundlauf(alt, vorher)
    verloren = [n for n, _ in PFLICHT if alt_nachher.get(n) != vorher[n]]
    if set(verloren) == {"entry_score", "entry_strategie"}:
        print("    entry_score und entry_strategie gehen verloren - erkannt.")
    else:
        print("    Der Gegentest erkennt den alten Fehler NICHT (%s)." % verloren)
        print("    Damit ist auch das 'bestanden' oben wertlos.")
        return 2
    print()

    print("-" * 70)
    if fehlt:
        print("  DURCHGEFALLEN: %d Pflichtfeld(er) ueberleben den Neustart nicht." % len(fehlt))
        for name, warum in fehlt:
            print("    %-18s %s" % (name, warum))
        return 1

    print("  BESTANDEN: alle %d Pflichtfelder ueberleben den Neustart." % len(PFLICHT))
    print()
    print("  Was das NICHT beweist: dass der Score beim Kauf ueberhaupt")
    print("  gesetzt wird. Auf dem Nachkauf-Pfad (DCA) ist er weiterhin")
    print("  immer leer - app.py:3029 liest eine Variable, die es nicht")
    print("  gibt (Befund 41, offen).")
    print("-" * 70)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
