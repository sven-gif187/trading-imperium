# -*- coding: utf-8 -*-
"""Schaltet Warte-Auftraege im Echtbetrieb scharf - mit Epochengrenze.

WAS DIESES WERKZEUG TUT
-----------------------
Zwei Dinge, die zusammengehoeren und deshalb NICHT einzeln gemacht
werden:

  1. eine Epochengrenze L4 in config_epochs.json
  2. `warteauftraege.nur_paper` in data_store/config.json auf false

Wer nur den Schalter umlegt, bekommt Daten ohne Grenze - und jeder
Vorher-Nachher-Vergleich ist wertlos, ohne dass es auffaellt. Genau das
ist der Mechanismus, der dieses Projekt sieben Monate zurueckgeworfen
hat (CLAUDE.md Abschnitt 5).

WAS SICH DANACH AENDERT
-----------------------
Der Bot kauft nicht mehr sofort zum Marktpreis, sondern legt ein Angebot
0,10 % unter den Markt und wartet bis zu einer Stunde. Wird es bedient,
zahlt er 0,10 % Maker statt 0,25 % Taker - und kauft guenstiger ein.
Wird es nicht bedient, findet der Kauf NICHT statt.

    Kosten je Runde    0,505 % -> 0,355 %
    gemessener Vorteil +0,161 Prozentpunkte (an 382 echten Kaeufen,
                       Gegenauslese eingerechnet, Vertrauensintervall
                       +0,077 bis +0,237)

VERKAEUFE BLEIBEN UNVERAENDERT. Stop-Loss, Trailing und Notaus gehen
weiter als Sofort-Auftrag - ein Limit-Verkauf wird bei einem schnellen
Rutsch nicht bedient.

WAS DANACH ZU BEOBACHTEN IST
----------------------------
Die Ausfuehrungsquote. Gemessen wurden 73,3 %, aber an 15-Minuten-Kerzen
im Papierpfad. Im Echtbetrieb haelt die Boerse den Auftrag und sieht
jeden Handel - die Quote sollte also HOEHER liegen. Bleibt sie deutlich
darunter, stimmt etwas nicht.

    python warteauftraege_scharf.py --stand       nachsehen
    python warteauftraege_scharf.py --scharf      einschalten
    python warteauftraege_scharf.py --zurueck     wieder ausschalten
"""
import io
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HIER, "data_store", "config.json")
EPOCHS = os.path.join(HIER, "config_epochs.json")
EPOCHE = "L4_warteauftraege_live"


def _lies(pfad):
    return json.load(io.open(pfad, encoding="utf-8"))


def _schreib(pfad, daten):
    # Erst danebenlegen, dann umbenennen: ein Absturz mitten im Schreiben
    # hinterlaesst sonst eine halbe Konfiguration.
    tmp = pfad + ".neu"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)
    os.replace(tmp, pfad)


def stand():
    c = _lies(CONFIG)
    w = c.get("warteauftraege", {})
    e = _lies(EPOCHS)
    epochen = [x.get("id") for x in e.get("epochs", [])]

    print("\n" + "=" * 72)
    print("  WARTE-AUFTRAEGE IM ECHTBETRIEB - Stand")
    print("=" * 72)
    print(f"\n  Betriebsmodus        {c.get('trading', {}).get('mode')}")
    print(f"  warteauftraege.aktiv {w.get('aktiv')}")
    print(f"  nur_paper            {w.get('nur_paper')}"
          f"   {'<- sperrt den Echtbetrieb' if w.get('nur_paper') else '<- Echtbetrieb OFFEN'}")
    print(f"  Abstand              {w.get('abstand_pct')} %")
    print(f"  gueltig              {w.get('gueltig_kerzen')} Kerzen "
          f"a {w.get('kerze_minuten')} Minuten")
    print(f"\n  Epoche {EPOCHE} gesetzt: "
          f"{'ja' if EPOCHE in epochen else 'NEIN'}")
    print(f"  vorhandene Epochen   {epochen}")

    verl = os.path.join(HIER, "data_store", "warteauftraege.json")
    if os.path.exists(verl):
        try:
            v = _lies(verl).get("verlauf", {})
            ges = v.get("ausgefuehrt", 0) + v.get("verfallen", 0)
            quote = (v.get("ausgefuehrt", 0) / ges * 100) if ges else 0.0
            print(f"\n  Bisheriger Verlauf   {v}")
            if ges:
                print(f"  Ausfuehrungsquote    {quote:.1f} %  "
                      f"(gemessen im Papier: 73,3 % als Obergrenze)")
        except Exception:
            pass
    print("=" * 72 + "\n")
    return w.get("nur_paper", True), EPOCHE in epochen


def scharf(an=True):
    gesperrt, hat_epoche = stand()
    c = _lies(CONFIG)
    if c.get("trading", {}).get("mode") != "live":
        print("  ABBRUCH: Der Bot steht nicht auf 'live'. Dann aendert")
        print("  dieser Schalter nichts - und eine Epochengrenze fuer eine")
        print("  Aenderung, die nicht wirkt, waere irrefuehrend.\n")
        return 1

    if an and not hat_epoche:
        e = _lies(EPOCHS)
        # DIE FELDER HEISSEN id/label/note/changes - NICHT name/beschreibung.
        # Und `start` traegt ein LEERZEICHEN, kein "T": die drei vorhandenen
        # Epochen stehen so da, und die Auswertung vergleicht Zeitstempel
        # als Text. Ein "T" sortiert hinter jedem Leerzeichen und wuerfe
        # alles in die falsche Epoche - derselbe Fehler ist am 15.09.
        # schon einmal passiert.
        e.setdefault("epochs", []).append({
            "id": EPOCHE,
            "start": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "label": "Kaeufe als echte Warte-Auftraege (Limit-Order, Maker)",
            "note":
                "Der Bot kauft nicht mehr sofort zum Marktpreis, sondern "
                "legt ein Angebot 0,10 % unter den Markt und wartet bis zu "
                "einer Stunde. Wird es bedient, zahlt er 0,10 % Maker statt "
                "0,25 % Taker; wird es nicht bedient, findet der Kauf nicht "
                "statt. Kosten je Runde 0,505 % -> 0,355 %. Gemessener "
                "Vorteil +0,161 Prozentpunkte an 382 echten Kaeufen "
                "(11.09.2026), Gegenauslese eingerechnet, "
                "Vertrauensintervall +0,077 bis +0,237. VERKAEUFE bleiben "
                "Sofort-Auftraege - ein Limit-Verkauf wird bei einem "
                "schnellen Rutsch nicht bedient. Zu beobachten: die "
                "Ausfuehrungsquote. Im Papier wurden 73,3 % gemessen, aber "
                "als Obergrenze; live haelt die Boerse den Auftrag und "
                "sieht jeden Handel, die Quote sollte hoeher liegen.",
            "changes": [
                "warteauftraege.nur_paper=false",
                "Kaeufe: Limit-Order 0,10 % unter Markt statt Market-Order",
                "gueltig 4 Kerzen a 15 Minuten, danach Ruecknahme",
                "Verkaeufe unveraendert als Market-Order",
                "K-BASIS je Runde 0,505 % -> 0,355 % (K_WARTE)",
            ],
        })
        _schreib(EPOCHS, e)
        print(f"  Epochengrenze {EPOCHE} gesetzt.")

    c.setdefault("warteauftraege", {})["nur_paper"] = (not an)
    c["warteauftraege"]["_scharf_live_seit"] = (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        if an else "")
    _schreib(CONFIG, c)
    print(f"  nur_paper steht jetzt auf {not an}.")

    # === GEGENPROBE: nicht dem Schreiben glauben, sondern nachlesen ===
    nach = _lies(CONFIG).get("warteauftraege", {}).get("nur_paper")
    if nach != (not an):
        print(f"  FEHLER: nachgelesen steht dort {nach}. NICHT wirksam.")
        return 1
    print("  Gegengeprueft: der Wert steht wirklich in der Datei.\n")
    print("  WICHTIG: Der Bot liest die Konfiguration beim Start. Damit")
    print("  die Aenderung greift, muss er NEU GESTARTET werden.")
    print("  Danach im Log nach 'WARTE-LIVE' sehen - dort steht jeder")
    print("  gestellte Auftrag mit Limitpreis und Order-Nummer.\n")
    return 0


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else "--stand").lower()
    if arg in ("--stand", "-s"):
        stand()
        return 0
    if arg in ("--scharf", "-a"):
        return scharf(True)
    if arg in ("--zurueck", "-z"):
        return scharf(False)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
