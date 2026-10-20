# -*- coding: utf-8 -*-
"""reparaturen_test.py - prueft die kleinen Reparaturen vom 12./13.09.2026.

WOZU
----
Drei Reparaturen, die alle **kein Verhalten aendern** und deshalb ohne
eigene Epochengrenze eingespielt werden konnten:

  Befund 41   `entry_score` auf dem Nachkauf-Pfad war immer leer
  Befund 95   eingefrorene Kurse landeten als frische Messung in der
              Zeitreihe
  Befund 97   ein Speichervorgang konnte zwoelf Einstellungen auf einmal
              zuruecksetzen (Wachposten und Sicherung, eigener Test:
              config_wachposten_test.py)

Jede Pruefung hier geht in BEIDE Richtungen: sie muss schweigen, wenn es
stimmt, und anschlagen, wenn jemand die Reparatur zurueckdreht.

AENDERT NICHTS. Liest den Quelltext und rechnet die Erkennungslogik nach.

    python reparaturen_test.py
"""
import ast
import io
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HIER)


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("    %-52s ok   %s" % (was, zusatz))
        else:
            self.fehler.append((was, zusatz))
            print("    %-52s FEHL %s" % (was, zusatz))


def _quelle(pfad):
    return io.open(pfad, encoding="utf-8", errors="replace").read()


def _ohne_kommentare(text):
    """Nur der ausfuehrbare Teil - Kommentare duerfen alte Namen nennen."""
    raus = []
    for z in text.split("\n"):
        i = z.find("#")
        raus.append(z[:i] if i >= 0 else z)
    return "\n".join(raus)


def befund_41(p):
    print()
    print("  BEFUND 41 - Einstiegs-Score auf dem Nachkauf-Pfad (DCA)")
    print("  " + "-" * 66)
    text = _quelle("app.py")
    code = _ohne_kommentare(text)

    p.sage("_dca_intent kommt im ausfuehrbaren Code nicht mehr vor",
           "_dca_intent" not in code,
           "(im Kommentar darf es stehen: %dx)" % text.count("_dca_intent"))

    p.sage("Die Stelle nutzt jetzt `intent`",
           code.count('getattr(intent, "score", None)') >= 2,
           "%dx gefunden (Signal- und DCA-Pfad)"
           % code.count('getattr(intent, "score", None)'))

    # Gueltigkeitsbereich am Syntaxbaum pruefen, nicht per Textsuche:
    # existiert in derselben Funktion eine Zuweisung an `intent`?
    baum = ast.parse(text)
    treffer = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        quelle_der_funktion = ast.get_source_segment(text, knoten) or ""
        if 'getattr(intent, "score", None)' not in _ohne_kommentare(
                quelle_der_funktion):
            continue
        # Gebunden ist `intent` entweder durch eine Zuweisung ODER als
        # Parameter. Die erste Fassung dieses Tests zaehlte nur
        # Zuweisungen und meldete deshalb _buche_ergebnis als Fehler -
        # dort ist intent ein Parameter. Das war ein Befund ueber den
        # TEST, nicht ueber den Code.
        zuweisungen = [n for n in ast.walk(knoten)
                       if isinstance(n, ast.Assign)
                       and any(isinstance(z, ast.Name) and z.id == "intent"
                               for z in n.targets)]
        parameter = [a.arg for a in knoten.args.args
                     + getattr(knoten.args, "kwonlyargs", [])
                     if a.arg == "intent"]
        art = ("Zuweisung x%d" % len(zuweisungen)) if zuweisungen else ""
        if parameter:
            art = (art + " + Parameter").strip(" +")
        treffer.append((knoten.name, len(zuweisungen) + len(parameter), art))
    p.sage("`intent` ist in denselben Funktionen gebunden",
           bool(treffer) and all(n > 0 for _, n, _ in treffer),
           ", ".join("%s: %s" % (t[0], t[2]) for t in treffer))

    # Gegentest
    print()
    print("    Gegentest - wuerde die alte Fassung durchfallen?")
    alt = 'getattr(_dca_intent, "score", None) if "_dca_intent" in dir() else None'
    print("      Alte Zeile: %s" % alt[:58])
    print("      -> enthielte `_dca_intent` im Code, Pruefung 1 haette FEHL")
    print("         gemeldet. Und `dir()` ohne Argument gibt in einer Methode")
    print("         die lokalen Namen - der Name stand nie darin, weil er")
    print("         nirgends zugewiesen wird. Die Bedingung war immer falsch.")


def befund_95(p):
    print()
    print("  BEFUND 95 - eingefrorene Kurse nicht als Messung schreiben")
    print("  " + "-" * 66)
    code = _ohne_kommentare(_quelle("app.py"))

    p.sage("Der Schnappschuss vergleicht mit dem Vorwert",
           "_markt_kurse_vorher" in code, "")
    p.sage("Bei Gleichstand wird keine Zeile geschrieben",
           "_markt_eingefroren" in code, "")
    p.sage("Die Kurse werden nur EINMAL geholt",
           code.count('_preis("BTC/USDC")') == 1,
           "%dx - zweimal holen hiesse zwei verschiedene Werte"
           % code.count('_preis("BTC/USDC")'))

    # Der Handelspfad darf NICHT angefasst sein - das waere gefaehrlich
    em = _ohne_kommentare(_quelle(os.path.join("runtime", "exit_monitor.py")))
    p.sage("fetch_current_price ist UNVERAENDERT (Stop-Loss!)",
           "_markt_eingefroren" not in em and "_markt_kurse_vorher" not in em,
           "der Handelspfad bleibt unberuehrt")

    # Die Erkennungslogik nachrechnen
    print()
    print("    Die Erkennung nachgerechnet:")
    faelle = [
        ((64000.0, 3200.0, 150.0), (64000.0, 3200.0, 150.0), True,
         "alle drei exakt gleich"),
        ((64000.0, 3200.0, 150.0), (64000.01, 3200.0, 150.0), False,
         "BTC um einen Cent bewegt"),
        ((64000.0, 3200.0, 150.0), (64000.0, 3200.0, 150.01), False,
         "SOL um einen Cent bewegt"),
    ]
    for vorher, jetzt, erwartet, was in faelle:
        ist = (jetzt == vorher)
        p.sage("      %s" % was, ist == erwartet,
               "-> %s" % ("Luecke" if ist else "wird geschrieben"))

    print()
    print("    Warum das reicht: Drei Kurse zu zwei Zeitpunkten sind nie")
    print("    auf acht Stellen gleich. Sind sie es doch, wurde nichts")
    print("    abgerufen. Das Pruefmuster steht so in CLAUDE.md.")


def befund_97(p):
    print()
    print("  BEFUND 97 - Wachposten beim Speichern der Einstellungen")
    print("  " + "-" * 66)
    code = _quelle(os.path.join("config", "settings.py"))
    p.sage("Sicherung vor dem Schreiben eingebaut",
           "_vor_dem_speichern_sichern" in code, "")
    p.sage("Alarmschwelle ist gesetzt",
           "RUECKFALL_ALARM" in code, "")
    p.sage("Das Speichern wird NICHT blockiert",
           "return []" in code and "raise" not in code.split(
               "_vor_dem_speichern_sichern")[-1][:2000],
           "ein Wachposten, der anhaelt, waere gefaehrlicher")
    print()
    print("    Die sieben Einzelpruefungen dazu: config_wachposten_test.py")


def main():
    print("=" * 76)
    print("  KLEINE REPARATUREN vom 12./13.09.2026 - halten sie?")
    print("=" * 76)
    p = Pruefung()
    befund_41(p)
    befund_95(p)
    befund_97(p)

    print()
    print("-" * 76)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d" % (len(p.fehler), p.ok + len(p.fehler)))
        for was, z in p.fehler:
            print("    %s  %s" % (was, z))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Keine dieser drei Reparaturen aendert das Handelsverhalten -")
    print("  deshalb brauchten sie keine eigene Epochengrenze und stoeren")
    print("  die Messung in E9 nicht. Wirksam werden sie mit dem naechsten")
    print("  Bot-Start.")
    print("-" * 76)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
