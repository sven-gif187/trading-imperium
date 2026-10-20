#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAS PROJEKTGEDAECHTNIS — einmal je Chat.

Legt Claude beim Start vor, was sonst nur in Dateien steht und dort
liegen bleibt:

  1. PROJEKT-ENTSCHEIDUNGEN.md  — vollstaendig. Was bewusst so ist.
  2. GEFUNDENE-PROBLEME.md      — nur die Ueberschriften, offene zuerst.
  3. WISSENSSTAND.md            — nur die Kennzahl und der Befehl dazu.

Warum einmal je Chat und nicht bei jeder Nachricht: Der Text ist gross.
Einmal ist er bezahlbar, hundertmal nicht.

Von Hand testen:
    echo {} | python sitzungsstart.py
"""

import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
PROJEKT = HIER.parent.parent            # .claude/hooks -> .claude -> Projekt

ENTSCHEIDUNGEN = PROJEKT / "PROJEKT-ENTSCHEIDUNGEN.md"
PROBLEME = PROJEKT / "GEFUNDENE-PROBLEME.md"
WISSEN = PROJEKT / "WISSENSSTAND.md"

# Obergrenze fuer das Ganze. Wird sie erreicht, wird gekuerzt — aber
# sichtbar, mit Angabe was fehlt. Stilles Abschneiden waere schlimmer
# als gar nichts vorzulegen.
OBERGRENZE = 45000

# Woran man erkennt, dass ein Befund erledigt ist.
ERLEDIGT = re.compile(r"BEHOBEN|ERLEDIGT|✅", re.IGNORECASE)


def lies(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8")
    except OSError:
        return ""


def befund_index() -> tuple[str, list[str]]:
    """Kurzliste der Befunde. Offene ausgeschrieben, erledigte nur gezaehlt."""
    text = lies(PROBLEME)
    if not text:
        return ("", [f"{PROBLEME.name} nicht lesbar"])

    offen: list[str] = []
    zu: list[str] = []
    for zeile in text.splitlines():
        if not zeile.startswith("### "):
            continue
        titel = zeile[4:].strip()
        nummer = titel.split(".", 1)[0].strip()
        if ERLEDIGT.search(titel):
            zu.append(nummer)
        else:
            offen.append(f"  {titel}")

    teile = [f"OFFENE BEFUNDE ({len(offen)} von {len(offen) + len(zu)}) "
             f"aus {PROBLEME.name}:"]
    teile.extend(offen if offen else ["  (keiner)"])
    if zu:
        teile.append("")
        teile.append(f"Bereits behoben ({len(zu)}), Nummern: " + ", ".join(zu))
    teile.append("")
    teile.append(f"Volltext bei Bedarf: {PROBLEME.name} "
                 f"({len(text.splitlines())} Zeilen).")
    return ("\n".join(teile), [])


def wissen_hinweis() -> str:
    text = lies(WISSEN)
    if not text:
        return ""
    treffer = re.search(r"Erfasst:\s*\*\*(\d+)\*\*", text)
    anzahl = treffer.group(1) if treffer else "?"
    return (f"NACHSCHLAGEWERK: {WISSEN.name} kennt {anzahl} bereits dokumentierte "
            f"Codestellen.\nDie Tabelle wird nicht gelesen, sondern abgefragt:\n"
            f"    python schon_bekannt.py <datei.py:zeile>\n"
            f"Antwortet sie BEKANNT, ist der Fund eine Ergaenzung - kein neuer Befund.")


def main() -> int:
    warnungen: list[str] = []
    bloecke: list[str] = []

    entsch = lies(ENTSCHEIDUNGEN).strip()
    if entsch:
        bloecke.append(f"=== {ENTSCHEIDUNGEN.name} (vollstaendig) ===\n\n"
                       "Was hier steht, ist eine ENTSCHEIDUNG, kein Vorschlag. "
                       "Nichts davon wird 'repariert'.\n\n" + entsch)
    else:
        warnungen.append(f"{ENTSCHEIDUNGEN.name} nicht lesbar")

    index, fehler = befund_index()
    warnungen.extend(fehler)
    if index:
        bloecke.append("=== " + PROBLEME.name + " (Kurzliste) ===\n\n" + index)

    hinweis = wissen_hinweis()
    if hinweis:
        bloecke.append("=== " + WISSEN.name + " ===\n\n" + hinweis)
    else:
        warnungen.append(f"{WISSEN.name} nicht lesbar")

    if not bloecke:
        print(json.dumps({"systemMessage":
                          "[Hook] Projektgedaechtnis: keine der drei Dateien lesbar."}))
        return 0

    trenner = "\n\n" + ("-" * 70) + "\n\n"
    text = ("PROJEKTGEDAECHTNIS — automatisch vorgelegt beim Sitzungsstart.\n"
            "Diese drei Dateien erreichen dich sonst nicht.\n\n"
            + trenner.join(bloecke))

    if len(text) > OBERGRENZE:
        weg = len(text) - OBERGRENZE
        text = (text[:OBERGRENZE]
                + f"\n\n[GEKUERZT: {weg} Zeichen fehlen hier. Der Rest steht "
                  f"in den Originaldateien - bei Bedarf selbst oeffnen.]")
        warnungen.append(f"Projektgedaechtnis um {weg} Zeichen gekuerzt")

    ausgabe: dict = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }
    if warnungen:
        ausgabe["systemMessage"] = "[Hook] " + "; ".join(warnungen)

    print(json.dumps(ausgabe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
