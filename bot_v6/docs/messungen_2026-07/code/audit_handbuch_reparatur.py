# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Reparatur ENTWICKLERHANDBUCH.md, Freigabe 3.3 vom 04.08.2026.
"""
Schneidet den fuehrenden Nullblock aus ENTWICKLERHANDBUCH.md.

STANDARD IST DRY-RUN. Schreiben nur mit --schreiben.

BEFUND: genau EIN zusammenhaengender Nullblock ab Offset 0. Der Rest der
Datei ist intakter Markdown, beginnend mit "## EVENTS-LOG". Die verlorenen
Bytes sind aus keiner Projektquelle rekonstruierbar - alle drei Kopien
(ENTWICKLERHANDBUCH.md, .bak_2026-07-31, _KORRUPT_28072026.md) tragen
denselben Schaden von 68.328 Bytes.

VORGEHEN: Nullblock entfernen, davor einen Vermerk setzen, der den
Datenverlust benennt. Nichts geloescht - das Original liegt als
ENTWICKLERHANDBUCH.md.nullbyte_20260804 daneben.

WETTLAUF MIT DEM DOCAGENT: app.py laeuft und haengt ueber
features/doc_agent.py:145-175 weiter an die Datei an. Der Agent liest bei
jedem Append die ganze Datei frisch, haengt an und schreibt zurueck.
Schreibt er zwischen unserem Lesen und Schreiben, ginge sein Eintrag
verloren. Deshalb: Groesse und mtime unmittelbar vor dem Schreiben erneut
pruefen und bei Abweichung abbrechen statt ueberschreiben.
"""
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
PROJEKT = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
ZIEL = os.path.join(PROJEKT, "ENTWICKLERHANDBUCH.md")
BACKUP = os.path.join(PROJEKT, "ENTWICKLERHANDBUCH.md.nullbyte_20260804")

VERMERK = (
    "# ENTWICKLERHANDBUCH\n"
    "\n"
    "> **Reparaturvermerk 04.08.2026.** Die ersten {n} Bytes dieser Datei\n"
    "> bestanden ausschliesslich aus Nullbytes (ein einziger\n"
    "> zusammenhaengender Block ab Offset 0) und wurden entfernt. Der\n"
    "> Inhalt dieses Kopfteils - die urspruengliche Kapitelstruktur des\n"
    "> Handbuchs - ist verloren und aus keiner Projektquelle\n"
    "> rekonstruierbar: alle drei vorhandenen Kopien tragen denselben\n"
    "> Schaden. Ursache ist mit hoher Wahrscheinlichkeit ein\n"
    "> NTFS-delayed-write nach hartem Systemabbruch, nicht der DocAgent -\n"
    "> dieser haengt ausschliesslich unter `## EVENTS-LOG` an und hat den\n"
    "> Schaden nur fortgeschrieben. Das unveraenderte Original liegt als\n"
    "> `ENTWICKLERHANDBUCH.md.nullbyte_20260804` daneben. Der EVENTS-LOG\n"
    "> ab hier ist vollstaendig und unberuehrt.\n"
    "\n"
)


def analysiere(pfad):
    d = open(pfad, "rb").read()
    n = d.count(b"\x00")
    if n == 0:
        return d, 0, 0
    # zusammenhaengende Nullbloecke
    bloecke, s = [], None
    for i, b in enumerate(d):
        if b == 0 and s is None:
            s = i
        elif b != 0 and s is not None:
            bloecke.append((s, i - s))
            s = None
    if s is not None:
        bloecke.append((s, len(d) - s))
    return d, n, bloecke


def main():
    schreiben = "--schreiben" in sys.argv
    if not os.path.isfile(ZIEL):
        print("FEHLER: Zieldatei fehlt:", ZIEL)
        return 2
    if not os.path.isfile(BACKUP):
        print("ABBRUCH: Backup fehlt:", BACKUP)
        return 2

    d, n, bloecke = analysiere(ZIEL)
    print(f"Datei:   {ZIEL}")
    print(f"Groesse: {len(d)} Bytes, mtime "
          f"{time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(os.path.getmtime(ZIEL)))}")
    print(f"Backup:  {BACKUP} ({os.path.getsize(BACKUP)} Bytes)")
    if n == 0:
        print("\nKeine Nullbytes mehr vorhanden - nichts zu tun.")
        return 0
    print(f"\nNullbytes: {n} ({n/len(d)*100:.2f} %), "
          f"{len(bloecke)} zusammenhaengende(r) Block/Bloecke")
    for off, laenge in bloecke[:5]:
        print(f"   Offset {off}, Laenge {laenge}")

    if len(bloecke) != 1 or bloecke[0][0] != 0:
        print("\nABBRUCH: Erwartet wurde genau EIN Block ab Offset 0. "
              "Das Schadensbild hat sich geaendert - kein automatischer "
              "Eingriff.")
        return 3

    laenge = bloecke[0][1]
    rest = d[laenge:]
    if b"\x00" in rest:
        print("\nABBRUCH: Rest enthaelt weitere Nullbytes.")
        return 3
    try:
        rest.decode("utf-8")
    except UnicodeDecodeError as e:
        print("\nABBRUCH: Rest ist kein gueltiges UTF-8:", e)
        return 3

    neu = VERMERK.format(n=laenge).encode("utf-8") + rest.lstrip(b"\r\n")
    print(f"\nErgebnis waere: {len(neu)} Bytes "
          f"(vorher {len(d)}, entfernt {laenge}, Vermerk "
          f"+{len(VERMERK.format(n=laenge).encode('utf-8'))})")
    print(f"Erste 200 Zeichen nach der Reparatur:")
    print("  " + repr(neu[:200].decode("utf-8"))[:220])

    if not schreiben:
        print("\nDRY-RUN. Nichts geschrieben. Mit --schreiben ausfuehren.")
        return 0

    # Wettlauf mit dem DocAgent: Zustand direkt vor dem Schreiben pruefen
    groesse_jetzt = os.path.getsize(ZIEL)
    if groesse_jetzt != len(d):
        print(f"\nABBRUCH: Datei hat sich waehrend der Analyse geaendert "
              f"({len(d)} -> {groesse_jetzt} Bytes). Der DocAgent hat "
              f"geschrieben. Erneut ausfuehren.")
        return 4

    tmp = ZIEL + ".tmp_reparatur"
    with open(tmp, "wb") as f:
        f.write(neu)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ZIEL)

    d2, n2, _b2 = analysiere(ZIEL)
    print(f"\nGESCHRIEBEN. Verifikation:")
    print(f"  Groesse:   {len(d2)} Bytes")
    print(f"  Nullbytes: {n2}")
    print(f"  Backup unveraendert: "
          f"{os.path.getsize(BACKUP)} Bytes")
    if n2 != 0:
        print("  WARNUNG: Es sind wieder Nullbytes vorhanden - der "
              "DocAgent hat den alten Stand zurueckgeschrieben. "
              "Erneut ausfuehren.")
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
