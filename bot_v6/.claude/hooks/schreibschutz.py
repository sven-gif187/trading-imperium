#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCHREIBSCHUTZ — die Sperre, die nicht auf Erinnerung baut.

Laeuft automatisch, BEVOR Claude Code eine Datei schreibt oder aendert.
Steht das Ziel in GESCHUETZTE-DATEIEN.txt, wird der Versuch abgelehnt.

Warum es das gibt: Am 19.08.2026 waeren beinahe Befunde in
forschung.db geschrieben worden. Die Entscheidung dagegen stand
dokumentiert und durchsuchbar da. Sie wurde nicht gelesen. Sven hat es
von Hand gestoppt. Diese Datei ersetzt das Erinnern durch eine Sperre.

Von Hand testen:
    echo {"tool_name":"Write","tool_input":{"file_path":"x/forschung.db"}} | python schreibschutz.py
"""

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
LISTE = HIER / "GESCHUETZTE-DATEIEN.txt"


def geschuetzte_muster() -> list[str]:
    """Liest die Liste. Fehlt sie, schuetzt der Hook nichts — und sagt das."""
    if not LISTE.exists():
        return []
    muster = []
    for zeile in LISTE.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if zeile and not zeile.startswith("#"):
            muster.append(zeile.replace("\\", "/").lower())
    return muster


def main() -> int:
    try:
        eingang = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Kein verwertbarer Eingang: nichts entscheiden, aber nicht schweigen.
        print(json.dumps({"systemMessage":
                          "[Schreibschutz] Eingang unlesbar - es wurde NICHT geprueft."}))
        return 0

    ziel = (eingang.get("tool_input") or {}).get("file_path") or ""
    if not ziel:
        return 0

    normal = str(ziel).replace("\\", "/").lower()
    muster = geschuetzte_muster()

    if not muster:
        print(json.dumps({"systemMessage":
                          "[Schreibschutz] GESCHUETZTE-DATEIEN.txt fehlt oder ist leer "
                          "- es wird nichts geschuetzt."}))
        return 0

    for m in muster:
        if m in normal:
            grund = (
                f"ABGELEHNT: '{ziel}' steht unter Bestandsschutz "
                f"(Treffer auf '{m}').\n\n"
                "Nachzulesen in CLAUDE.md Abschnitt 4 und in "
                "PROJEKT-ENTSCHEIDUNGEN.md. Das ist eine Entscheidung, "
                "kein Versehen.\n\n"
                "Soll hier wirklich geschrieben werden, muss Sven es "
                "ausdruecklich freigeben - dann die Zeile in "
                ".claude/hooks/GESCHUETZTE-DATEIEN.txt entfernen. "
                "Nicht am Hook vorbeiarbeiten."
            )
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": grund,
                },
                "systemMessage": f"Schreibschutz hat '{Path(ziel).name}' abgewiesen.",
            }))
            return 0

    # Kein Treffer: keine Ausgabe. Der Schreibvorgang laeuft normal weiter.
    return 0


if __name__ == "__main__":
    sys.exit(main())
