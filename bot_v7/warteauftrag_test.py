# -*- coding: utf-8 -*-
"""warteauftrag_test.py - haelt die Warteschlange, was sie verspricht?

WOZU
----
`execution/warteauftraege.py` ist ein Zustandsspeicher im Handelspfad. Das
ist die gefaehrlichste Art von Bauteil, die es hier gibt: es merkt sich
etwas ueber Neustarts hinweg, und wenn es dabei falsch aufraeumt, wird ein
laengst verfallener Auftrag Monate spaeter scharf - oder Geld ist gebunden,
das niemand mehr sucht.

Dieses Programm prueft jede Zusage einzeln und in BEIDE Richtungen: es muss
schweigen, wenn alles stimmt, und den Fehler finden, wenn er da ist. Ein
Test, der nur "ok" sagen kann, beweist nichts.

Die neun Pruefungen:

  1  Der Limitpreis stimmt            von Hand nachgerechnet
  2  Kurs ueber dem Limit             wartet weiter
  3  Kurs auf dem Limit               fuellt
  4  Frist abgelaufen                 verfaellt
  5  Fehlender Kurs                   fuellt NICHT und verfaellt NICHT
  6  Zweiter Auftrag, gleiche Muenze  abgelehnt
  7  Neustart, Auftrag noch gueltig   kommt zurueck
  8  Neustart, Auftrag abgelaufen     kommt NICHT zurueck
  9  Kaputte Datei                    startet leer statt abzustuerzen

AENDERT NICHTS AM LAUFENDEN BOT. Eigener Ordner, eigene Dateien.

    python warteauftrag_test.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from execution.warteauftraege import Warteschlange, VORGABE   # noqa: E402

EINST = {"aktiv": True, "abstand_pct": 0.10,
         "gueltig_kerzen": 4, "kerze_minuten": 15}
STUNDE = 3600.0
T0 = 1789000000.0          # fester Zeitpunkt, damit nichts von der Uhr abhaengt


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, nummer, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("  %2d  %-42s ok   %s" % (nummer, was, zusatz))
        else:
            self.fehler.append((nummer, was, zusatz))
            print("  %2d  %-42s FEHL %s" % (nummer, was, zusatz))


def main():
    print("=" * 78)
    print("  WARTE-AUFTRAEGE - haelt die Warteschlange, was sie verspricht?")
    print("=" * 78)
    print()

    ordner = tempfile.mkdtemp(prefix="warteauftrag_test_")
    pfad = os.path.join(ordner, "warteauftraege.json")
    p = Pruefung()
    try:
        # ---------------------------------------------------------------
        # 1  Limitpreis von Hand
        w = Warteschlange(pfad=pfad, einstellungen=EINST, jetzt=T0)
        a = w.anlegen("BTC/USDC", 100000.0, 150.0, jetzt=T0)
        # 100000 minus 0,10 % = 100000 x 0,999 = 99900
        p.sage(1, "Limitpreis 0,10 % unter 100.000 $",
               a is not None and abs(a["limitpreis"] - 99900.0) < 1e-6,
               "%.2f $ (erwartet 99.900,00)" % (a["limitpreis"] if a else -1))

        # 2  Kurs darueber -> wartet
        g, v = w.pruefen({"BTC/USDC": 99950.0}, jetzt=T0 + 60)
        p.sage(2, "Kurs 99.950 $ liegt ueber dem Limit",
               not g and not v and "BTC/USDC" in w.offene(),
               "wartet weiter")

        # 3  Kurs genau auf dem Limit -> fuellt
        g, v = w.pruefen({"BTC/USDC": 99900.0}, jetzt=T0 + 120)
        p.sage(3, "Kurs genau auf dem Limit",
               len(g) == 1 and not v and not w.offene(),
               "gefuellt zu %.2f $" % (g[0]["gefuellt_kurs"] if g else -1))

        # 4  Frist abgelaufen -> verfaellt
        w2 = Warteschlange(pfad=os.path.join(ordner, "b.json"),
                           einstellungen=EINST, jetzt=T0)
        w2.anlegen("ETH/USDC", 4000.0, 150.0, jetzt=T0)
        # gueltig 4 Kerzen x 15 min = 1 Stunde
        g, v = w2.pruefen({"ETH/USDC": 4000.0}, jetzt=T0 + STUNDE + 1)
        p.sage(4, "Frist von 1 Stunde abgelaufen",
               len(v) == 1 and not g and not w2.offene(),
               "verfallen")

        # 5  Fehlender Kurs -> weder noch (Befund 95)
        w3 = Warteschlange(pfad=os.path.join(ordner, "c.json"),
                           einstellungen=EINST, jetzt=T0)
        w3.anlegen("SOL/USDC", 200.0, 150.0, jetzt=T0)
        g, v = w3.pruefen({}, jetzt=T0 + STUNDE + 1)
        p.sage(5, "Kurs fehlt, Frist laengst abgelaufen",
               not g and not v and "SOL/USDC" in w3.offene(),
               "bleibt unberuehrt")
        g, v = w3.pruefen({"SOL/USDC": 0}, jetzt=T0 + STUNDE + 2)
        p.sage(5.1 if False else 5, "Kurs ist 0 (Netzausfall)",
               not g and not v and "SOL/USDC" in w3.offene(),
               "fuellt nicht")

        # --- 5b  NOTVERFALL: das Symbol kommt gar nicht mehr ----------
        # [14.09.2026] Ohne ihn bleibt so ein Auftrag EWIG stehen - und
        # weil anlegen() keinen zweiten auf dasselbe Symbol zulaesst,
        # SPERRT er die Muenze dauerhaft vom Handel aus.
        w3b = Warteschlange(pfad=os.path.join(ordner, "c2.json"),
                            einstellungen=EINST, jetzt=T0)
        w3b.anlegen("WEG/USDC", 200.0, 150.0, jetzt=T0)
        g, v = w3b.pruefen({}, jetzt=T0 + STUNDE + 60)
        p.sage(5, "Kurs fehlt, Frist gerade vorbei",
               not v and "WEG/USDC" in w3b.offene(),
               "bleibt - ein Netzausfall darf nichts loeschen")
        g, v = w3b.pruefen({}, jetzt=T0 + 2 * STUNDE + 1)
        p.sage(5, "Kurs fehlt seit dem DOPPELTEN der Frist",
               len(v) == 1 and not w3b.offene(),
               "Notverfall - sonst haengt er ewig")

        # 6  Zweiter Auftrag auf dieselbe Muenze
        w4 = Warteschlange(pfad=os.path.join(ordner, "d.json"),
                           einstellungen=EINST, jetzt=T0)
        erst = w4.anlegen("BTC/USDC", 100000.0, 150.0, jetzt=T0)
        zweit = w4.anlegen("BTC/USDC", 99000.0, 150.0, jetzt=T0 + 10)
        p.sage(6, "Zweiter Auftrag auf dieselbe Muenze",
               erst is not None and zweit is None and len(w4.offene()) == 1,
               "abgelehnt")

        # 7  Neustart, Auftrag noch gueltig
        npfad = os.path.join(ordner, "neu.json")
        wa = Warteschlange(pfad=npfad, einstellungen=EINST, jetzt=T0)
        wa.anlegen("BTC/USDC", 100000.0, 150.0, jetzt=T0)
        wb = Warteschlange(pfad=npfad, einstellungen=EINST, jetzt=T0 + 600)
        p.sage(7, "Neustart nach 10 Minuten",
               "BTC/USDC" in wb.offene()
               and abs(wb.offene()["BTC/USDC"]["limitpreis"] - 99900.0) < 1e-6,
               "Auftrag kommt zurueck")

        # 8  Neustart, Auftrag abgelaufen
        wc = Warteschlange(pfad=npfad, einstellungen=EINST, jetzt=T0 + STUNDE + 1)
        p.sage(8, "Neustart nach 1 Stunde und 1 Sekunde",
               not wc.offene() and wc.verlauf["verfallen"] >= 1,
               "Auftrag wird NICHT wieder scharf")

        # 9  Kaputte Datei
        kpfad = os.path.join(ordner, "kaputt.json")
        with open(kpfad, "w", encoding="utf-8") as f:
            f.write('{"auftraege": {"BTC/USDC": {"limitpr')   # abgeschnitten
        wd = Warteschlange(pfad=kpfad, einstellungen=EINST, jetzt=T0)
        p.sage(9, "Halb geschriebene Datei nach Absturz",
               not wd.offene(), "startet leer, kein Absturz")

        # ---------------------------------------------------------------
        # GEGENTEST: findet dieser Test einen echten Fehler?
        print()
        print("  Gegentest - eine absichtlich kaputte Warteschlange:")

        class Kaputt(Warteschlange):
            """Vergisst das Aufraeumen beim Laden - genau der Fehler, vor dem
            die ganze Datei schuetzen soll."""
            def _laden(self, jetzt):
                if not os.path.exists(self.pfad):
                    return
                import io as _io, json as _json
                try:
                    with _io.open(self.pfad, encoding="utf-8") as f:
                        d = _json.load(f)
                except Exception:
                    return
                self.auftraege = dict(d.get("auftraege") or {})   # ohne Frist-Pruefung

        wk = Kaputt(pfad=npfad, einstellungen=EINST, jetzt=T0 + STUNDE + 1)
        erkannt = bool(wk.offene())
        if erkannt:
            print("      Der abgelaufene Auftrag waere wieder scharf geworden")
            print("      - Pruefung 8 haette FEHL gemeldet. Der Test greift.")
        else:
            print("      Der Test erkennt den eingebauten Fehler NICHT.")
            print("      Damit ist auch das 'bestanden' oben wertlos.")
            p.fehler.append((0, "Gegentest", "erkennt nichts"))

        # Vorgabe-Schalter
        print()
        print("  Vorgabe im Auslieferungszustand:")
        print("      aktiv           %s" % VORGABE["aktiv"])
        print("      abstand_pct     %.2f %%" % VORGABE["abstand_pct"])
        print("      gueltig_kerzen  %d  (= %d Minuten)"
              % (VORGABE["gueltig_kerzen"],
                 VORGABE["gueltig_kerzen"] * VORGABE["kerze_minuten"]))
        if VORGABE["aktiv"]:
            print("      ACHTUNG: aktiv steht auf True. Das ist eine")
            print("      Verhaltensaenderung und braucht eine Epochengrenze.")
            p.fehler.append((0, "Vorgabe", "aktiv steht auf True"))

    finally:
        shutil.rmtree(ordner, ignore_errors=True)

    print()
    print("-" * 78)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d Pruefungen" % (len(p.fehler), p.ok + len(p.fehler)))
        for nummer, was, zusatz in p.fehler:
            print("    %s  %s" % (nummer, was))
        return 1
    print("  BESTANDEN: alle %d Pruefungen, und der Gegentest greift." % p.ok)
    print()
    print("  Was das NICHT beweist: dass der Vorteil im Betrieb eintritt.")
    print("  Die gemessenen 73,3 % Ausfuehrungsquote sind eine Obergrenze -")
    print("  der Bot sieht nur alle 12 Sekunden hin, die Messung sah jedes")
    print("  Kerzentief. Was wirklich herauskommt, steht nach dem Scharf-")
    print("  schalten in data_store/warteauftraege.json unter 'verlauf'.")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
