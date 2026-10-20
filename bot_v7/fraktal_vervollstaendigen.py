# -*- coding: utf-8 -*-
"""Schaltet den Regime-Filter ab und setzt die Epochengrenze L3.

WAS DIESES SKRIPT AENDERT
-------------------------
    config_regime_filter.json   enabled  ->  false
    config_epochs.json          neue Epoche L3_fraktal_komplett

Der Fibonacci-Ausstieg selbst braucht keinen Schalter: Er greift genau
dann, wenn eine Position eine Kaufwelle traegt - und die bekommt nur,
was durch das Fraktal-Tor gekauft wurde. Alte Positionen ohne Welle
laufen unveraendert ueber Stop-Loss und Trailing.

WARUM DER REGIME-FILTER WEG SOLL - UND WAS DAGEGEN SPRICHT
----------------------------------------------------------
Sven am 15.09.2026: *"wie waers wenn wir den streng gestellten waechter
abstellen, und das system vervollstaendigen damit er komplett nach dem
neuen muster handelt."*

Der Anlass ist belegt: Am 15.09. meldete das Fraktal-Tor stundenlang
"Einstiegspreis bestaetigt" fuer BTC und ETH, und jedes Mal kam
danach:

    [REGIME] BUY blockiert - 3/2 Bestaetigungen
    [Kurs<EMA50, Regime-Abwaerts, Cycle-Baer]

Zwei Filter hintereinander, und der zweite ist der engere. Der Bot
handelte seit 05:34 nicht mehr.

WAS DAGEGEN SPRICHT - ehrlich, damit die Entscheidung bewusst faellt:
Der Filter ist gemessen. In config_regime_filter.json steht der Vermerk
vom 15.08.2026: *"Geblockte Kaeufe haetten im Mittel -0,64 % verloren
(99 Stunden). Der Filter schuetzt - strenger stellen."* Die Messung
vom 10.08. sagt dasselbe fuer 4 Stunden (-0,417 %), dreht aber nach
24 h (+1,056 %) und 48 h (+3,643 %): Der Filter faengt den Ruecksetzer
und verpasst die Erholung.

WAS SICH SEITHER GEAENDERT HAT - und warum die Messung nicht mehr passt:
Beide Messungen entstanden, als ohne Fraktal-Tor gekauft wurde. Damals
blockte der Filter Kaeufe, die per Trendfolge am Hoch entstanden -
also genau die schlechten. Jetzt kommt vor ihm ein Tor, das nur noch
in Ruecksetzern kauft. Die Kaeufe, die er heute blockt, sind eine
ANDERE Stichprobe als die, an der er gemessen wurde.

Das macht das Abstellen nicht richtig - es macht die alte Zahl nur
ungueltig. Was der Filter MIT Tor davor noch bringt, ist ungemessen,
und diese Epoche ist die Messung.

Aufruf:  FRAKTAL_VERVOLLSTAENDIGEN.bat  (Doppelklick)
"""
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REGIME = "config_regime_filter.json"
EPOCHEN = "config_epochs.json"


def sichern(pfad):
    stempel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ziel = f"{pfad}.sicherung_{stempel}"
    shutil.copy(pfad, ziel)
    return ziel


def main():
    print()
    print("=" * 72)
    print("  FRAKTAL-SYSTEM VERVOLLSTAENDIGEN")
    print("=" * 72)
    print()
    print("  Der Fibonacci-Ausstieg ist bereits im Code und braucht keinen")
    print("  Schalter - er greift bei jeder Position, die das Tor gekauft")
    print("  hat. Dieses Skript aendert nur noch den Regime-Filter.")
    print()

    if not os.path.exists(REGIME):
        print(f"  FEHLER: {REGIME} nicht gefunden.")
        return 1

    # ---------------- Bot-Warnung ----------------
    try:
        import psutil
        hier = os.path.dirname(os.path.abspath(__file__))
        laeuft = []
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                cl = " ".join(p.info["cmdline"] or [])
                if "app.py" in cl and os.path.normcase(p.cwd()) == os.path.normcase(hier):
                    laeuft.append(p.info["pid"])
            except Exception:
                pass
        if laeuft:
            print(f"  ACHTUNG: Der Live-Bot laeuft gerade (PID {laeuft}).")
            print()
            print("  Der Fibonacci-Ausstieg steckt im PROGRAMMTEXT - der")
            print("  laufende Bot hat den alten Stand geladen und benutzt ihn")
            print("  weiter, bis er neu gestartet wird. Die Aenderung hier")
            print("  wirkt also erst nach einem Neustart vollstaendig.")
            print()
            antwort = input("  Trotzdem weitermachen? (ja/nein): ").strip().lower()
            if antwort not in ("ja", "j"):
                print("\n  Abgebrochen. Nichts geaendert.\n")
                return 1
            print()
    except ImportError:
        pass

    # ---------------- Regime-Filter ----------------
    sicherung = sichern(REGIME)
    with open(REGIME, encoding="utf-8") as f:
        rf = json.load(f)

    vorher = rf.get("enabled")
    if vorher is False:
        print("  Der Regime-Filter ist bereits aus. Nichts zu tun.")
        os.remove(sicherung)
    else:
        rf["enabled"] = False
        rf["_abgeschaltet_am"] = datetime.datetime.now().strftime(
            "%Y-%m-%dT%H:%M:%S")
        rf["_abgeschaltet_warum"] = (
            "Sven am 15.09.2026. Vor dem Filter steht seit L2 das "
            "Fraktal-Tor, das nur noch in Konfluenzzonen kauft. Der Filter "
            "blockte danach jeden Kauf (3 von 2 noetigen Bestaetigungen) - "
            "der Bot handelte seit 05:34 nicht mehr. Die Messungen vom "
            "10.08. und 15.08., die fuer den Filter sprachen, entstanden "
            "OHNE Tor davor und betreffen damit eine andere Stichprobe: "
            "damals blockte er Trendfolge-Kaeufe am Hoch. Was er mit Tor "
            "davor noch bringt, ist ungemessen - Epoche L3 ist die Messung. "
            "Wieder einschalten: enabled auf true.")

        with open(REGIME, "w", encoding="utf-8") as f:
            json.dump(rf, f, indent=2, ensure_ascii=False)

        print(f"  {REGIME} geaendert  (Sicherung: "
              f"{os.path.basename(sicherung)})")
        print(f"    enabled : {vorher}  ->  False")
        print(f"    (min_confirmations bleibt {rf.get('min_confirmations')} -"
              f" wirkt nur, wenn wieder eingeschaltet)")

    # ---------------- Epochengrenze ----------------
    print()
    if os.path.exists(EPOCHEN):
        sicherung_e = sichern(EPOCHEN)
        with open(EPOCHEN, encoding="utf-8") as f:
            ep = json.load(f)

        jetzt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if any(e.get("id") == "L3_fraktal_komplett" for e in ep.get("epochs", [])):
            print("  Epoche L3_fraktal_komplett steht bereits.")
            os.remove(sicherung_e)
        else:
            ep.setdefault("epochs", []).append({
                "id": "L3_fraktal_komplett",
                "start": jetzt,
                "label": "Fraktal-System komplett - Ein- UND Ausstieg nach Fibonacci",
                "note": (
                    "Zweite Haelfte von Svens Verfahren. Bis L2 stieg der Bot "
                    "nach dem Verfahren ein und nach dem alten Schema aus - "
                    "feste Prozentmarken. Jetzt ist das Ziel die Verlaengerung "
                    "derselben Welle, in deren Ruecksetzer gekauft wurde "
                    "(features/fraktal_ziele.py, Verhaeltnisse aus FIB_VOR in "
                    "chartanalyse.py:233, an Marks Charts nachgerechnet). "
                    "Verkauft wird bei Ziel 1,0 - dem Wellenhoch. Gestaffelte "
                    "Teilverkaeufe bei 1,272 und 1,618 sind vorbereitet, aber "
                    "NICHT angeschlossen: Der Verkaufspfad raeumt die Position "
                    "atomar weg (exit_monitor.py record_result), und bei der "
                    "aktuellen Kontogroesse laegen Teilmengen unter der "
                    "Boersen-Mindestmenge. Zugleich Regime-Filter aus. "
                    "36 von 36 Pruefungen bestanden (fraktal_tor_test.py)."),
                "changes": [
                    "Fibonacci-Ziel als Ausstieg (Ziel 1,0 = Wellenhoch)",
                    "Kaufwelle wird an der Position gespeichert",
                    "Whitelist in state_manager erweitert (Befund 88)",
                    "regime_filter enabled=false",
                    "Trailing-Kette repariert (elif -> if)",
                ],
            })
            with open(EPOCHEN, "w", encoding="utf-8") as f:
                json.dump(ep, f, indent=2, ensure_ascii=False)
            print(f"  Epochengrenze gesetzt  (Sicherung: "
                  f"{os.path.basename(sicherung_e)})")
            print(f"    L3_fraktal_komplett ab {jetzt}")
    else:
        print(f"  WARNUNG: {EPOCHEN} fehlt - keine Epochengrenze gesetzt!")

    print()
    print("=" * 72)
    print("  FERTIG.")
    print()
    print("  WICHTIG: Der Bot muss NEU GESTARTET werden. Der")
    print("  Fibonacci-Ausstieg steckt im Programmtext, nicht in einer")
    print("  Einstellung - der laufende Bot benutzt bis dahin den alten.")
    print()
    print("  Danach handelt er komplett nach dem Verfahren:")
    print("    Einstieg  - nur in Fibonacci-Konfluenzzonen (Golden Pocket)")
    print("    Ausstieg  - am Wellenhoch der Kaufwelle")
    print("    Notbremse - Stop-Loss und Trailing laufen unveraendert mit")
    print()
    print("  Rueckgaengig: die Sicherungsdateien zurueckkopieren.")
    print("=" * 72)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen. Nichts geaendert.\n")
