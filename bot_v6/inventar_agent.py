#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  INVENTUR-AGENT (14.07.2026) - ANALYSIERT NUR, loescht NICHTS
================================================================
Erfasst den kompletten V6-Ordner und klassifiziert jede Datei:
  KERN        - Python-Code, den der Bot von app.py aus erreicht
  WERKZEUG    - eigenstaendige Skripte (Analyse/Installer/Tests)
  VERWAIST    - .py, das NIEMAND importiert und keinen Main hat
  BACKUP      - .bak*-Dateien (Patch-Sicherungen)
  DUPLIKAT    - identischer Inhalt wie andere Datei (MD5)
  DATEN-ALT   - Daten/Logs, >30 Tage nicht angefasst
  DATEN/DOKU  - aktive Daten, Configs, Markdown

Schreibt INVENTAR.md (lesbar) + inventar_daten.json (fuer Sensei).
Verschiebt/loescht GARANTIERT nichts - reine Bestandsaufnahme.

  python "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\\inventar_agent.py" > "C:\\Users\\<BENUTZER>\\Desktop\\inventar_log.txt" 2>&1
Danach INVENTAR.md an den Sensei schicken.
================================================================
"""
import os, sys, ast, json, hashlib
from datetime import datetime, timedelta
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"__pycache__", ".git", ".idea", "venv", ".venv", "node_modules"}
ROOTS = ("app.py",)          # Einstiegspunkte fuer den Import-Graph
STALE_DAYS = 30
NOW = datetime.now()


def md5(path, limit=10 * 1024 * 1024):
    try:
        if os.path.getsize(path) > limit:
            return None
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def modname(relpath):
    return relpath.replace("\\", "/").rsplit(".py", 1)[0].replace("/", ".")


def scan():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                       and not d.startswith("_archive")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            try:
                st = os.stat(p)
                files.append({"rel": rel, "size": st.st_size,
                              "age_d": (NOW - datetime.fromtimestamp(st.st_mtime)).days,
                              "md5": md5(p)})
            except Exception:
                continue
    return files


def build_import_graph(files):
    """Wer importiert wen? Rueckgabe: modul -> set(importierte module)."""
    pyfiles = {modname(f["rel"]): f["rel"] for f in files if f["rel"].endswith(".py")}
    graph, has_main = defaultdict(set), set()
    for mod, rel in pyfiles.items():
        try:
            src = open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore").read()
            tree = ast.parse(src)
        except Exception:
            continue
        if "__main__" in src:
            has_main.add(mod)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                # nur projekt-interne Treffer (exakter Modulname o. Paketpfad)
                for cand in pyfiles:
                    if cand == n or cand.endswith("." + n) or n.startswith(cand + "."):
                        graph[mod].add(cand)
    return pyfiles, graph, has_main


def reachable(graph, starts):
    seen, stack = set(), [s for s in starts]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack.extend(graph.get(m, ()))
    return seen


def main():
    print("INVENTUR-AGENT - Bestandsaufnahme (loescht nichts)")
    print("-" * 52)
    files = scan()
    pyfiles, graph, has_main = build_import_graph(files)
    starts = [modname(r) for r in ROOTS if any(f["rel"] == r for f in files)]
    kern = reachable(graph, starts)

    dupes = defaultdict(list)
    for f in files:
        if f["md5"]:
            dupes[f["md5"]].append(f["rel"])
    dupes = {h: v for h, v in dupes.items() if len(v) > 1}
    dupe_files = {r for v in dupes.values() for r in v[1:]}

    cats = defaultdict(list)
    for f in files:
        rel, base = f["rel"], os.path.basename(f["rel"])
        if ".bak" in base:
            cats["BACKUP"].append(f)
        elif rel in dupe_files:
            cats["DUPLIKAT"].append(f)
        elif rel.endswith(".py"):
            m = modname(rel)
            if m in kern:
                cats["KERN"].append(f)
            elif base.startswith(("install_", "fix_", "check_", "test_")) or m in has_main:
                cats["WERKZEUG"].append(f)
            else:
                cats["VERWAIST"].append(f)
        elif f["age_d"] > STALE_DAYS and not base.endswith((".md",)):
            cats["DATEN-ALT"].append(f)
        else:
            cats["DATEN/DOKU"].append(f)

    total_mb = sum(f["size"] for f in files) / 1e6
    lines = [f"# INVENTAR V6 - {NOW.strftime('%d.%m.%Y %H:%M')}",
             f"\n**{len(files)} Dateien, {total_mb:.1f} MB gesamt. "
             f"Dieses Werkzeug loescht und verschiebt NICHTS.**\n"]
    empf = {"BACKUP": "-> Archiv-Kandidat (cleanup.py-Regel)",
            "DUPLIKAT": "-> Archiv-Kandidat (Original bleibt)",
            "VERWAIST": "-> PRUEFEN mit Sensei (evtl. toter Code)",
            "DATEN-ALT": f"-> PRUEFEN (>{STALE_DAYS} Tage unberuehrt)",
            "WERKZEUG": "-> behalten (erledigte Installer archiviert cleanup.py)",
            "KERN": "-> behalten (vom Bot erreichter Code)",
            "DATEN/DOKU": "-> behalten"}
    for cat in ("KERN", "WERKZEUG", "VERWAIST", "BACKUP", "DUPLIKAT",
                "DATEN-ALT", "DATEN/DOKU"):
        fl = sorted(cats.get(cat, []), key=lambda x: -x["size"])
        mb = sum(f["size"] for f in fl) / 1e6
        lines.append(f"\n## {cat} - {len(fl)} Dateien, {mb:.1f} MB  {empf[cat]}")
        for f in fl[:60]:
            lines.append(f"- `{f['rel']}` ({f['size']//1024} KB, {f['age_d']}d alt)")
        if len(fl) > 60:
            lines.append(f"- ... und {len(fl)-60} weitere (siehe inventar_daten.json)")
    if dupes:
        lines.append("\n## Duplikat-Gruppen (identischer Inhalt)")
        for h, grp in list(dupes.items())[:20]:
            lines.append("- " + "  ==  ".join(f"`{g}`" for g in grp))

    open(os.path.join(ROOT, "INVENTAR.md"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"erstellt": NOW.isoformat(), "dateien": files,
               "kern_module": sorted(kern), "duplikate": dupes},
              open(os.path.join(ROOT, "inventar_daten.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    for cat in ("KERN", "WERKZEUG", "VERWAIST", "BACKUP", "DUPLIKAT", "DATEN-ALT", "DATEN/DOKU"):
        print(f"  {cat:<11} {len(cats.get(cat, [])):>4} Dateien")
    print("-" * 52)
    print("INVENTAR.md + inventar_daten.json geschrieben.")
    print("-> INVENTAR.md an den Sensei schicken fuer die Analyse.")
    print("ERGEBNIS: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
