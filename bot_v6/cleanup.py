#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  V6 WORKSPACE CLEANUP v4 - FUTURE-PROOF + BUCH-SCHUTZ
================================================================
Verschiebt alle erledigten Patches, Backups und Muell-Dateien
in einen Archiv-Ordner.

WICHTIG: NICHTS wird wirklich geloescht. Alles wandert in
_archive_<datum>/ und kann jederzeit zurueckgeholt werden.

>>> HARTER BUCH-SCHUTZ (neu in v3):
    ALLE .md-Dateien und ALLE .pdf-Dateien bleiben IMMER
    erhalten (Ausnahme: roadmap_*.pdf). Das Sensei-Handbuch
    in jeder Version und alle anderen Buecher/Doku sind damit
    sicher - sie koennen NIE ins Archiv wandern.

>>> MARKER-SCHUTZ (neu in v5, [MARKER-SCHUTZ v1] 27.07.2026):
    Jede Datei, die in ihrem KOPF (erste 4 KB) einen dieser
    Marker traegt, wird NIE archiviert - egal welches Muster
    sie sonst treffen wuerde:

        [COCKPIT-KEEP]      [CLEANUP-KEEP]

    Gedacht fuer Dauer-Werkzeuge, die zufaellig wie erledigte
    Installer aussehen. Neues Werkzeug schuetzen = Marker in
    den Docstring/Dateikopf schreiben, sonst nichts. Wirkt auch
    in den Unterordnern aus SUBDIRS_TO_SCAN.
    Traeger heute: cockpit_server.py

    Bewusst konservativ: Laesst sich eine Datei nicht lesen
    (Rechte, gesperrt, kaputt), gilt sie als GESCHUETZT. Ein
    zuviel behaltenes Werkzeug ist harmlos, ein faelschlich
    archiviertes nicht. "Nicht lesbar" ist kein Beweis fuer
    "kein Marker".

WAS BLEIBT (V6-Substanz):
  - app.py, cleanup.py, diagnose.py, bot_navigator.py
  - bot_uebersicht.html, start_bot.bat
  - ALLE .md (Buecher/Doku)  +  ALLE .pdf ausser roadmap_*.pdf
  - alle V6-Ordner: ui/ agents/ core/ risk/ execution/ models/
    data/ portfolio/ live/ features/ backtest/ reports/ tests/
    config/ scripts/ docs/ assets/
  - data_store/  (Lernfortschritt!)   v4_data/  (V4-Wissen!)
  - requirements.txt, config.example.json, .env, .env.example, .gitignore

WAS AUTOMATISCH INS ARCHIV WANDERT (Pattern):
  install*.py  fix_*.py  find_*.py  add_*.py  reset*.py
  repair*.py  deep_*.py  final_*.py  full_*.py  *_patch.py
  *patch*.py  rette_*.py  rebuild_*.py        (erledigte Skripte)
  *.backup  *_backup  *_backup_*  *.py.*backup*  (Backups)
  auto_export_*.txt  export_*.txt  trade_export.txt
  imperium_analyse_*.txt  *_output.txt  start_error.txt
  health_issue_extract.txt  roadmap_*.pdf
  # 279 python 2% copy cd Datei   (leere Tippfehler-Dateien)

UNBEKANNTES wird NIE angefasst, nur am Ende gelistet.
================================================================
"""
import os
import sys
import shutil
import fnmatch
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# === WHITELIST: das bleibt IMMER ===
KEEP_DIRS = {
    "ui", "agents", "core", "risk", "execution", "models",
    "data", "portfolio", "live", "features", "backtest",
    "reports", "tests", "config", "scripts", "docs", "assets",
    "data_store", "v4_data", "metals",
}

KEEP_FILES = {
    "app.py",
    ".env.example", ".env", "config.example.json",
    "requirements.txt", ".gitignore",
    "diagnose.py", "bot_navigator.py", "bot_uebersicht.html",
    "cleanup.py", "start_bot.bat",
}


# === PATTERNS: alles was matched, kommt weg ===
ARCHIVE_PATTERNS = [
    # Patch- und Fix-Skripte (alle Praefixe die wir je benutzt haben)
    "install*.py", "fix_*.py", "find_*.py", "add_*.py",
    "reset*.py", "repair*.py", "deep_*.py", "final_*.py",
    "full_*.py", "*_patch.py", "*patch*.py",
    "rette_*.py", "rebuild_*.py",
    "cleanup_workspace*.py",
    # Backup-Dateien + alle app.py-Schnappschuesse (app.py selbst bleibt!)
    "*.backup", "*.BACKUP",
    "*_backup", "*_backup_*",
    "*.py.*backup*", "*.py.*BACKUP*",
    "app.py.*",
    "*.bak",                                 # .bak-Backups (settings.py.bak, config.json.bak, ...)
    # Exports / Diagnose-Dumps
    "auto_export_*.txt", "export_*.txt", "trade_export.txt",
    "imperium_analyse_*.txt", "*_output.txt", "start_error.txt",
    "health_issue_extract.txt",
    # Alte Roadmap-PDFs (einzige PDF-Ausnahme!)
    "roadmap_*.pdf",
]

# Backups auch in Unterordnern aufraeumen
BACKUP_SUBDIR_PATTERNS = [
    "*.backup", "*.BACKUP", "*.bak",
    "*.py.*backup*", "*.py.*BACKUP*",
]
SUBDIRS_TO_SCAN = ["ui", "agents", "core", "risk", "execution", "models",
                   "features", "portfolio", "reports", "config"]

# Leere Tippfehler-Dateien
WEIRD_FILES = {"#", "279", "python", "2%", "copy", "cd", "Datei"}

# Alte Archive-Ordner
OLD_ARCHIVE_NAMES = {"_archiv", "_archive"}

# === MARKER-SCHUTZ [MARKER-SCHUTZ v1] ===
# Wer einen dieser Marker im Dateikopf traegt, bleibt. Siehe Docstring oben.
KEEP_MARKERS = ("[COCKPIT-KEEP]", "[CLEANUP-KEEP]")
KEEP_MARKER_HEAD_BYTES = 4096      # nur der Kopf zaehlt, nicht die ganze Datei


def banner(t): print("\n" + "=" * 64 + f"\n  {t}\n" + "=" * 64)
def ok(t):    print(f"  [OK] {t}")
def info(t):  print(f"  [i]  {t}")
def warn(t):  print(f"  [!]  {t}")
def err(t):   print(f"  [X]  {t}")


def matches_pattern(name, patterns):
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def has_keep_marker(path):
    """True, wenn im Kopf der Datei ein KEEP_MARKERS-Marker steht.

    Liest nur die ersten KEEP_MARKER_HEAD_BYTES Bytes - schnell, und ein
    Marker mitten im Text (z.B. ein Zitat) schuetzt nicht versehentlich.

    Nicht lesbar -> True (geschuetzt). Absicht: fehlende Information ist
    kein Beweis dafuer, dass kein Marker da ist. Im Zweifel behalten.
    """
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(KEEP_MARKER_HEAD_BYTES)
    except Exception:
        return True                       # unlesbar -> im Zweifel behalten
    text = head.decode("utf-8", errors="ignore")
    return any(m in text for m in KEEP_MARKERS)


def is_protected_book(name):
    """HARTER SCHUTZ: jede .md und jede .pdf (ausser roadmap_*.pdf) bleibt."""
    low = name.lower()
    if low.endswith(".md"):
        return True
    if low.endswith(".pdf") and not fnmatch.fnmatch(low, "roadmap_*.pdf"):
        return True
    return False


def collect_candidates():
    """Sammelt alles was archiviert wird."""
    candidates = []

    for entry in sorted(os.listdir(SCRIPT_DIR)):
        path = os.path.join(SCRIPT_DIR, entry)

        if os.path.isdir(path):
            if entry in KEEP_DIRS:
                continue
            # Nur alte Archiv-Ordner wandern weiter ins neue Archiv;
            # Daten-Backup-Ordner werden NICHT angefasst (nur gelistet).
            if entry in OLD_ARCHIVE_NAMES or entry.startswith("_archive_"):
                candidates.append(path)
            continue

        # Dateien
        if entry in KEEP_FILES:
            continue
        if is_protected_book(entry):          # <<< Buch-Schutz vor allem anderen
            continue
        if has_keep_marker(path):             # <<< Marker-Schutz [MARKER-SCHUTZ v1]
            continue
        if entry in WEIRD_FILES:
            candidates.append(path)
            continue
        if matches_pattern(entry, ARCHIVE_PATTERNS):
            candidates.append(path)

    # Unterordner nach Backups durchsuchen
    for subdir in SUBDIRS_TO_SCAN:
        sub_path = os.path.join(SCRIPT_DIR, subdir)
        if not os.path.isdir(sub_path):
            continue
        for entry in os.listdir(sub_path):
            full = os.path.join(sub_path, entry)
            if (os.path.isfile(full)
                    and matches_pattern(entry, BACKUP_SUBDIR_PATTERNS)
                    and not has_keep_marker(full)):     # [MARKER-SCHUTZ v1]
                candidates.append(full)

    return candidates


def find_unknown():
    """Sachen die nicht auf einer Liste stehen - werden NICHT angefasst."""
    unknown = []
    for entry in os.listdir(SCRIPT_DIR):
        path = os.path.join(SCRIPT_DIR, entry)
        if os.path.isdir(path):
            if entry in KEEP_DIRS or entry in OLD_ARCHIVE_NAMES:
                continue
            if entry.startswith("_archive_"):
                continue
            unknown.append(path)
            continue
        if entry in KEEP_FILES or entry in WEIRD_FILES:
            continue
        if is_protected_book(entry):
            continue
        if has_keep_marker(path):             # [MARKER-SCHUTZ v1] geschuetzt,
            continue                          # also kein Fall fuer "UNBEKANNT"
        if matches_pattern(entry, ARCHIVE_PATTERNS):
            continue
        unknown.append(path)
    return unknown


def find_marker_protected():
    """Dateien im Hauptordner, die per Marker geschuetzt sind (fuer die Anzeige)."""
    out = []
    for entry in sorted(os.listdir(SCRIPT_DIR)):
        path = os.path.join(SCRIPT_DIR, entry)
        if entry in KEEP_FILES:
            continue          # steht ohnehin auf der Whitelist - nicht doppelt melden
        if is_protected_book(entry):
            continue          # .md/.pdf sind schon durch den Buch-Schutz sicher
        if os.path.isfile(path) and has_keep_marker(path):
            out.append(entry)
    return out


def format_size(path):
    try:
        if os.path.isdir(path):
            total = 0
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
            kb = total / 1024
            return f"{kb/1024:.1f} MB" if kb > 1024 else f"{kb:.1f} KB"
        return f"{os.path.getsize(path) / 1024:.1f} KB"
    except Exception:
        return "?"


def main():
    banner("V6 WORKSPACE CLEANUP v4 - FUTURE-PROOF + BUCH-SCHUTZ")
    print(f"  Pfad: {SCRIPT_DIR}")
    ok("Buch-Schutz aktiv: ALLE .md und .pdf bleiben (ausser roadmap_*.pdf)")

    marked = find_marker_protected()
    if marked:
        ok(f"Marker-Schutz aktiv ({'/'.join(KEEP_MARKERS)}): {', '.join(marked)}")
    else:
        ok(f"Marker-Schutz aktiv ({'/'.join(KEEP_MARKERS)}) - derzeit keine Traeger")

    candidates = collect_candidates()
    unknown = find_unknown()

    print()
    if not candidates:
        ok("Nichts zum Archivieren - Ordner ist sauber!")
    else:
        info(f"{len(candidates)} Sache(n) wandern ins Archiv:")
        print()
        for c in candidates:
            rel = os.path.relpath(c, SCRIPT_DIR)
            marker = "[ORDNER]" if os.path.isdir(c) else "        "
            size = format_size(c)
            print(f"    {marker} {size:>10}  {rel}")

    if unknown:
        print()
        warn("UNBEKANNT (wird NICHT angefasst - du entscheidest selbst):")
        for u in unknown:
            rel = os.path.relpath(u, SCRIPT_DIR)
            marker = "[ORDNER]" if os.path.isdir(u) else "        "
            size = format_size(u)
            print(f"    {marker} {size:>10}  {rel}")

    if not candidates:
        print()
        info("Tipp: Dieses Skript behaeltst du im Ordner.")
        info("Nach jedem neuen Patch einfach nochmal laufen lassen.")
        return 0

    print()
    info("NICHTS wird geloescht. Alles wandert in _archive_<datum>/")
    print()
    try:
        answer = input("  Archivieren? (j/n): ").strip().lower()
    except KeyboardInterrupt:
        print()
        return 0

    if answer not in ("j", "ja", "y", "yes"):
        info("Abgebrochen - nichts veraendert.")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = os.path.join(SCRIPT_DIR, f"_archive_{ts}")
    os.makedirs(archive, exist_ok=True)
    print()
    ok(f"Archiv: _archive_{ts}/")

    moved = 0
    failed = 0
    for src in candidates:
        try:
            rel = os.path.relpath(src, SCRIPT_DIR)
            if os.sep in rel:
                dst = os.path.join(archive, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
            else:
                dst = os.path.join(archive, os.path.basename(src))

            if os.path.exists(dst):
                n = 2
                base, ext = os.path.splitext(dst)
                while os.path.exists(f"{base}_{n}{ext}"):
                    n += 1
                dst = f"{base}_{n}{ext}"

            shutil.move(src, dst)
            moved += 1
        except Exception as e:
            err(f"FEHLER bei {os.path.basename(src)}: {e}")
            failed += 1

    print()
    ok(f"{moved} Sache(n) archiviert")
    if failed > 0:
        warn(f"{failed} Fehler")

    banner("FERTIG!")
    print()
    print(f"  Archiv: _archive_{ts}/")
    print()
    print("  Bot starten:          python app.py")
    print("  Cleanup wiederholen:  python cleanup.py   (jederzeit)")
    print()
    print("  Wenn alles laeuft, irgendwann ganz weg mit:")
    print(f"    rmdir /s _archive_{ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
