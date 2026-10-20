# -*- coding: utf-8 -*-
"""schon_bekannt.py - beantwortet in zwei Sekunden: steht das schon in der Doku?

WARUM ES DIESES PROGRAMM GIBT
-----------------------------
Am 19.08.2026 habe ich die Gebuehren-Doppelbuchung als neuen Fund
gemeldet. Sie stand seit dem 18.08. in BOT-HANDBUCH.md 4.50 - mit
derselben Codezeile, die ich "entdeckt" hatte. Sven musste mich darauf
stossen.

Die Ursache war nicht Schlamperei, sondern Bauart: Das Handbuch hat
6.500 Zeilen. Niemand liest es vor jedem Befund. Die Ueberschriften sind
erzaehlerisch ("Die Kaufgebuehr wird doppelt abgezogen") - man erkennt
sie nur, wenn man den Befund schon kennt. Und es gab keine Moeglichkeit,
von einer CODESTELLE zurueck auf den Abschnitt zu kommen, der sie
beschreibt.

Genau das macht dieses Programm.

    Eine Regel, die man befolgen MUSS, wird vergessen.
    Eine Pruefung, die zwei Sekunden dauert, wird gemacht.

AUFRUF
------
    python schon_bekannt.py engine.py:401     eine Codestelle nachschlagen
    python schon_bekannt.py entry_score       einen Bezeichner nachschlagen
    python schon_bekannt.py --index           WISSENSSTAND.md neu schreiben
    python schon_bekannt.py --selbsttest      Gegentest in beide Richtungen

NUR LESEND. Beruehrt keine Bot-Datei, schreibt nur WISSENSSTAND.md.
"""
import os
import re
import sys

# [FIX 19.08.2026] Windows-Konsole laeuft auf cp1252 und stirbt an jedem
# Umlaut aus dem Handbuch. Ein Pruefwerkzeug, das beim Anzeigen des
# Ergebnisses abstuerzt, ist schlimmer als keins - es meldet nichts und
# sieht dabei aus wie ein Fehler im System.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))

# Die Dokumente, die als "bekannt" gelten. Reihenfolge = Rangfolge in der Ausgabe.
QUELLEN = [
    # PROJEKT-ENTSCHEIDUNGEN zuerst: was dort steht, ist eine Entscheidung
    # und kein Vorschlag - ein Treffer hier wiegt schwerer als alles andere.
    ("PROJEKT-ENTSCHEIDUNGEN.md",    "ENTSCHEIDUNG"),
    ("BOT-HANDBUCH.md",              "Handbuch"),
    ("GEFUNDENE-PROBLEME.md",        "Problemliste"),
    # [19.08.2026] Das Archiv MUSS mit durchsucht werden. Nach dem
    # Auslagern der 23 behobenen Punkte fiel WISSENSSTAND.md von 152 auf
    # 137 Codestellen - das Aufraeumen haette die Pruefung geschwaecht,
    # die es eigentlich schuetzen soll. Ein behobener Befund ist Wissen,
    # kein Muell: wer dieselbe Stelle wieder anfasst, muss erfahren, dass
    # dort schon einmal etwas war.
    (os.path.join("archiv", "GEFUNDENE-PROBLEME_behoben.md"), "behoben"),
    ("OFFEN.md",                     "Offen"),
    ("TODO-NACH-DEM-MESSFENSTER.md", "TODO"),
    ("ENTWICKLERHANDBUCH.md",        "Chronik"),
]

# datei.py:123  oder  datei.py:123-145
RE_STELLE = re.compile(r"\b([A-Za-z_][\w/\.-]*\.py):(\d+)(?:\s*[-–]\s*\d+)?\b")


def _lade():
    """Liest alle Quellen. Gibt {kurzname: (text, [zeilen])} zurueck."""
    out = {}
    for datei, kurz in QUELLEN:
        pfad = os.path.join(HIER, datei)
        if not os.path.exists(pfad):
            continue
        with open(pfad, encoding="utf-8", errors="replace") as f:
            zeilen = f.read().splitlines()
        out[kurz] = zeilen
    return out


def _ueberschrift_ueber(zeilen, nr):
    """Die naechste Ueberschrift oberhalb von Zeile nr (0-basiert)."""
    for i in range(nr, -1, -1):
        z = zeilen[i]
        if z.startswith("#"):
            return z.lstrip("#").strip()
    return "(ohne Abschnitt)"


def nachschlagen(begriff, quellen=None, still=False):
    """Sucht einen Begriff in allen Quellen. Gibt Trefferliste zurueck."""
    quellen = quellen if quellen is not None else _lade()
    treffer = []
    nadel = begriff.lower()
    for kurz, zeilen in quellen.items():
        for i, z in enumerate(zeilen):
            if nadel in z.lower():
                treffer.append((kurz, i + 1, _ueberschrift_ueber(zeilen, i), z.strip()))
    if not still:
        if not treffer:
            print(f"\n  NEU — '{begriff}' steht in keinem Dokument.")
            print("  (Das heisst: es darf als neuer Befund geschrieben werden.)\n")
        else:
            print(f"\n  BEKANNT — '{begriff}' steht bereits an {len(treffer)} Stelle(n):\n")
            gesehen = set()
            for kurz, nr, absch, text in treffer[:12]:
                schluessel = (kurz, absch)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                print(f"    {kurz:14s} Zeile {nr:<6d} {absch[:60]}")
                print(f"    {'':14s}       > {text[:88]}")
            if len(treffer) > 12:
                print(f"\n    ... und {len(treffer) - 12} weitere.")
            print("\n  Kein neuer Befund. Hoechstens eine ERGAENZUNG - und als solche schreiben.\n")
    return treffer


def index_schreiben():
    """Baut WISSENSSTAND.md: jede dokumentierte Codestelle mit ihrem Abschnitt."""
    quellen = _lade()
    stellen = {}
    for kurz, zeilen in quellen.items():
        for i, z in enumerate(zeilen):
            for m in RE_STELLE.finditer(z):
                schluessel = f"{os.path.basename(m.group(1))}:{m.group(2)}"
                stellen.setdefault(schluessel, set()).add(
                    (kurz, _ueberschrift_ueber(zeilen, i)))

    def sortier(s):
        d, _, n = s.rpartition(":")
        return (d, int(n) if n.isdigit() else 0)

    zeilen_out = [
        "# WISSENSSTAND — welche Codestelle ist schon dokumentiert?",
        "",
        "**Automatisch erzeugt mit `python schon_bekannt.py --index`. Nicht von Hand ändern.**",
        "",
        "Diese Tabelle beantwortet eine einzige Frage: *Habe ich diese Stelle",
        "schon einmal beschrieben?* Sie existiert, weil am 19.08.2026 ein Fund",
        "als neu gemeldet wurde, der seit dem Vortag im Handbuch stand.",
        "",
        "**Vor jedem neuen Befund:** `python schon_bekannt.py <datei.py:zeile>`",
        "",
        f"Erfasst: **{len(stellen)}** Codestellen aus {len(quellen)} Dokumenten.",
        "",
        "| Codestelle | dokumentiert in |",
        "|---|---|",
    ]
    for s in sorted(stellen, key=sortier):
        wo = "; ".join(f"{k} — {a[:52]}" for k, a in sorted(stellen[s]))
        zeilen_out.append(f"| `{s}` | {wo} |")
    ziel = os.path.join(HIER, "WISSENSSTAND.md")
    with open(ziel, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen_out) + "\n")
    print(f"Geschrieben: WISSENSSTAND.md ({len(stellen)} Codestellen)")
    return len(stellen)


def selbsttest():
    """Gegentest in BEIDE Richtungen - findet es den echten Fall, und
    meldet es nichts Falsches? (Regel vom 18.08.2026)"""
    quellen = _lade()
    fehler = 0

    print("\n=== Richtung 1: findet es einen BEKANNTEN Fall? ===")
    for begriff, erwartet_in in [("engine.py:401", "Handbuch"),
                                 ("filled_cost", "Handbuch"),
                                 ("risk/exit_rules.py", None)]:
        tr = nachschlagen(begriff, quellen, still=True)
        ok = bool(tr) and (erwartet_in is None or any(t[0] == erwartet_in for t in tr))
        print(f"  {'OK  ' if ok else 'FEHL'} {begriff:24s} {len(tr):4d} Treffer")
        if not ok:
            fehler += 1

    print("\n=== Richtung 2: meldet es bei etwas UNBEKANNTEM nichts? ===")
    for begriff in ["zzz_gibt_es_nicht.py:999", "quatsch_bezeichner_xyz"]:
        tr = nachschlagen(begriff, quellen, still=True)
        ok = not tr
        print(f"  {'OK  ' if ok else 'FEHL'} {begriff:24s} {len(tr):4d} Treffer (erwartet 0)")
        if not ok:
            fehler += 1

    print(f"\n  {'ALLE TESTS BESTANDEN' if not fehler else f'{fehler} TEST(S) FEHLGESCHLAGEN'}\n")
    return fehler


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--index":
        index_schreiben()
    elif arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)
    elif arg:
        nachschlagen(arg)
    else:
        print(__doc__)
