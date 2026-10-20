#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DER ZETTEL BEI JEDER NACHRICHT.

Laeuft automatisch, sobald Sven etwas abschickt, und legt Claude den
Inhalt von DAUERREGELN.txt vor. Kein Nachdenken, kein Erinnern.

WICHTIG: Dieser Text kostet bei JEDER Nachricht Platz. Deshalb die
Obergrenze unten. Was selten gebraucht wird, gehoert nicht hierher,
sondern in sitzungsstart.py — der laeuft nur einmal je Chat.

Von Hand testen:
    echo {} | python jede_nachricht.py
"""

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
REGELN = HIER / "DAUERREGELN.txt"

# Ab hier wird es teuer: 3000 Zeichen sind rund 800 Token bei jeder
# einzelnen Nachricht. Wer mehr braucht, nimmt den Sitzungsstart.
OBERGRENZE = 3000


def main() -> int:
    try:
        text = REGELN.read_text(encoding="utf-8").strip()
    except OSError as exc:
        # Kein stilles Scheitern: lieber eine sichtbare Meldung als ein
        # Zettel, der einfach nicht mehr kommt und den niemand vermisst.
        print(json.dumps({"systemMessage":
                          f"[Hook] DAUERREGELN.txt nicht lesbar: {exc}"}))
        return 0

    if not text:
        print(json.dumps({"systemMessage":
                          "[Hook] DAUERREGELN.txt ist leer - es wird nichts vorgelegt."}))
        return 0

    ausgabe: dict = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext":
                "STEHENDE PROJEKTREGELN (automatisch vorgelegt, "
                ".claude/hooks/DAUERREGELN.txt):\n\n" + text,
        }
    }
    if len(text) > OBERGRENZE:
        ausgabe["systemMessage"] = (
            f"[Hook] DAUERREGELN.txt ist auf {len(text)} Zeichen gewachsen "
            f"(Richtwert {OBERGRENZE}). Das kostet bei jeder Nachricht. "
            f"Selten Gebrauchtes besser in den Sitzungsstart verschieben.")

    print(json.dumps(ausgabe))
    return 0


if __name__ == "__main__":
    sys.exit(main())
