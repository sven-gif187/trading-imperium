# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Handbuch-Abschnitt vor "# TEIL 11" einfuegen und Tickets anhaengen (CLAUDE.md 7.5:
jede Aenderung -> Abschnitt in BOT-HANDBUCH.md UND Ticket in tickets.txt).

Zeilenenden werden aus der Zieldatei uebernommen (Handbuch und tickets.txt sind
in v6 und v7 CRLF, byte-genau geprueft 14.10.2026). Idempotent ueber die erste
Zeile des Abschnitts (Ueberschrift).

Aufruf: python doku_eintragen.py <bot-ordner> <abschnitt.md oder -> [<tickets.txt>]
Tickets-Datei: eine Zeile je Ticket, nur SPEICHERN/ERLEDIGT/BUG/DOKUMENTIEREN/NOTIZ.
"""
import sys
from pathlib import Path

GUELTIG = ("SPEICHERN:", "ERLEDIGT:", "BUG:", "DOKUMENTIEREN:", "NOTIZ:")


def nl_von(b: bytes) -> bytes:
    return b"\r\n" if b.count(b"\r\n") > b.count(b"\n") / 2 else b"\n"


def abschnitt(bot: Path, text: str) -> None:
    hb = bot / "BOT-HANDBUCH.md"
    roh = hb.read_bytes()
    nl = nl_von(roh)
    kopf = text.strip().splitlines()[0].encode("utf-8")
    if kopf in roh:
        print(f"Handbuch: '{kopf.decode()[:50]}' schon da - nichts getan"); return
    marke = "# TEIL 11 — Wie wir arbeiten".encode("utf-8")
    if roh.count(marke) != 1:
        raise SystemExit("Marke TEIL 11 nicht genau einmal")
    pos = roh.index(marke)
    trenner = b"---" + nl + nl
    if not roh[:pos].endswith(trenner):
        raise SystemExit("unerwartete Zeilen vor TEIL 11")
    neu = text.strip().replace("\r\n", "\n").replace("\n", nl.decode()).encode("utf-8") + nl + nl
    ergebnis = roh[:pos] + neu + trenner + roh[pos:]
    if nl == b"\r\n" and ergebnis.count(b"\r\n") != ergebnis.count(b"\n"):
        raise SystemExit("gemischte Zeilenenden - abgebrochen")
    hb.write_bytes(ergebnis)
    print(f"Handbuch: '{kopf.decode()[:60]}' eingefuegt")


def tickets(bot: Path, zeilen: list[str]) -> None:
    tk = bot / "tickets.txt"
    t = tk.read_bytes()
    nl = nl_von(t)
    for z in zeilen:
        if not z.startswith(GUELTIG):
            raise SystemExit(f"ungueltiges Stichwort: {z[:40]}")
    if not t.endswith(nl):
        t += nl
    tk.write_bytes(t + b"".join(z.encode("utf-8") + nl for z in zeilen))
    print(f"Tickets: {len(zeilen)} angehaengt")


if __name__ == "__main__":
    bot = Path(sys.argv[1])
    if sys.argv[2] != "-":
        abschnitt(bot, Path(sys.argv[2]).read_text(encoding="utf-8"))
    if len(sys.argv) > 3:
        tickets(bot, [z for z in Path(sys.argv[3]).read_text(encoding="utf-8").splitlines() if z.strip()])
