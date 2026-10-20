# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Rettung der durch Doppelstart beschaedigten Capture-Dateien, 03.08.2026.
"""
Block 1.4 - Tolerantes Lesen der gzip-Dateien vom 03.08.2026.

URSACHE DES SCHADENS: Bis zu 19 gleichzeitig laufende Daemon-Instanzen
haben je Zeile ein eigenes gzip-Mitglied in dieselbe Datei geschrieben.
Die Mitglieder verschraenken sich; ab der ersten Verschraenkung bricht
jeder Standardleser mit "zlib.error: invalid block type" ab.

VERFAHREN: Mitglied fuer Mitglied dekomprimieren, solange es geht. Beim
ersten Fehler wird versucht, hinter dem defekten Mitglied wieder
aufzusetzen (Suche nach der naechsten gzip-Signatur 1f 8b 08). So werden
auch Zeilen NACH der Bruchstelle geborgen.

RETTUNGSRATE als ZEILEN-Verhaeltnis (nicht Bytes): geborgene Datenzeilen
gegen geschaetzte Gesamtzeilen. Die Schaetzung nutzt die mittlere
Mitgliedsgroesse der erfolgreich gelesenen Mitglieder - sie ist eine
NAEHERUNG und wird als solche ausgewiesen.

NICHTS WIRD GELOESCHT. Die Originale bleiben; Geborgenes geht nach
capture/gerettet_2026-08-03/ als Plain-CSV.
"""
import glob
import os
import sys
import zlib

BASIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(BASIS, "capture")
SIG = b"\x1f\x8b\x08"


def berge(pfad):
    """(zeilen, gelesene_mitglieder, uebersprungene_bytes, restbytes)"""
    roh = open(pfad, "rb").read()
    text, pos, member, sprung = b"", 0, 0, 0
    while pos < len(roh):
        try:
            d = zlib.decompressobj(31)
            stueck = d.decompress(roh[pos:])
            text += stueck
            member += 1
            if d.unused_data:
                pos = len(roh) - len(d.unused_data)
            else:
                break
        except zlib.error:
            n = roh.find(SIG, pos + 1)
            if n < 0:
                return text, member, sprung, len(roh) - pos
            sprung += n - pos
            pos = n
    return text, member, sprung, 0


def main():
    tage = sorted(d for d in glob.glob(os.path.join(CAP, "2026-*"))
                  if os.path.isdir(d))
    if not tage:
        print("  Keine Tagesordner gefunden.")
        return 1
    for tag in tage:
        gz = sorted(glob.glob(os.path.join(tag, "*.csv.gz")))
        if not gz:
            continue
        ziel = os.path.join(CAP, "gerettet_" + os.path.basename(tag))
        os.makedirs(ziel, exist_ok=True)
        print("=" * 92)
        print(f" RETTUNG {os.path.basename(tag)} - {len(gz)} Dateien")
        print("=" * 92)
        print(f"    {'Datei':<30s} {'Zeilen':>8s} {'Mitgl.':>7s} "
              f"{'uebersprungen':>13s} {'Rate (geschaetzt)':>18s}")
        print("    " + "-" * 82)
        sum_z = sum_ges = 0
        for p in gz:
            text, member, sprung, rest = berge(p)
            s = text.decode("utf-8", errors="replace")
            zeilen = [z for z in s.splitlines()
                      if z.strip() and not z.startswith("ts,")
                      and not z.startswith("fundingTime,")]
            n = len(zeilen)
            groesse = os.path.getsize(p)
            # Naeherung: mittlere Bytes je gelesenem Mitglied
            mit_avg = (groesse - sprung - rest) / member if member else 0
            verloren = int((sprung + rest) / mit_avg) if mit_avg > 0 else 0
            ges = n + verloren
            rate = n / ges * 100 if ges else 0.0
            sum_z += n
            sum_ges += ges
            with open(os.path.join(ziel, os.path.basename(p)[:-3]),
                      "w", encoding="utf-8", newline="") as f:
                f.write(s)
            print(f"    {os.path.basename(p):<30s} {n:8d} {member:7d} "
                  f"{sprung:12d}B {rate:17.1f}%")
        print("    " + "-" * 82)
        gesamt = sum_z / sum_ges * 100 if sum_ges else 0.0
        print(f"    {'GESAMT':<30s} {sum_z:8d} {'':>7s} {'':>13s} "
              f"{gesamt:17.1f}%")
        print(f"\n    Geborgen nach: {ziel}")
        print(f"    Originale unveraendert, nichts geloescht.")
        print(f"    Die Rate ist eine NAEHERUNG - die wahre Zeilenzahl der")
        print(f"    zerstoerten Mitglieder ist nicht rekonstruierbar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
