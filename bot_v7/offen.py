"""Zeigt die offenen Punkte aus OFFEN.md - kurz, ohne Bildlauf.

NUR LESEND.

WARUM ES DIESES SKRIPT GIBT
---------------------------
Am 18.08.2026 habe ich zweimal etwas als "fertig" gemeldet, das ich
selbst vorgeschlagen hatte. Beide Male stand der Vorschlag nur im Chat -
und ein Chat scrollt weiter.

    "Das kann so nicht weitergehen, dass du immer Sachen liegen laesst."

Dagegen hilft kein Vorsatz, sondern dieselbe Medizin wie gegen den
vergessenen Neustart: die Maschine fragt, nicht der Mensch. Der Haken
.git/hooks/post-commit ruft dieses Skript nach JEDEM Commit auf. Damit
endet jede Arbeitseinheit mit der Frage "und was ist noch offen?".

Aufruf:  python offen.py           nur Gruppe A (jetzt machbar)
         python offen.py --alle    alle Gruppen
"""
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
LISTE = os.path.join(HIER, "OFFEN.md")


def lies():
    """Gibt [(gruppe, text, erledigt)] zurueck."""
    if not os.path.exists(LISTE):
        return []
    punkte, gruppe = [], "?"
    with open(LISTE, encoding="utf-8") as f:
        for zeile in f:
            if zeile.startswith("## "):
                gruppe = zeile[3:].strip()
            m = re.match(r"\s*- \[( |x)\] (.+)", zeile)
            if m:
                # Fettschrift und Codezeichen raus - das soll im Terminal
                # lesbar sein, nicht huebsch.
                text = re.sub(r"[*`]", "", m.group(2)).strip()
                punkte.append((gruppe, text, m.group(1) == "x"))
    return punkte


def main():
    alle = "--alle" in sys.argv
    punkte = lies()
    if not punkte:
        print("OFFEN.md nicht gefunden oder leer.")
        return 1

    offen = [p for p in punkte if not p[2]]
    a_gruppe = [p for p in offen if p[0].startswith("A")]
    zeigen = offen if alle else a_gruppe

    print()
    print("-" * 62)
    if not zeigen:
        print("OFFEN.md: in dieser Gruppe ist nichts offen.")
    else:
        kopf = "alle offenen Punkte" if alle else "jetzt machbar (Gruppe A)"
        print(f"OFFEN.md - {kopf}:")
        letzte = None
        for gruppe, text, _ in zeigen:
            if alle and gruppe != letzte:
                print(f"\n  {gruppe}")
                letzte = gruppe
            kurz = text if len(text) <= 78 else text[:75] + "..."
            print(f"   - {kurz}")
    if not alle and len(offen) > len(a_gruppe):
        print(f"\n  ({len(offen)-len(a_gruppe)} weitere in B/C/D - "
              f"python offen.py --alle)")
    print("-" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
