# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Phase 6: Subagenten-Dateien aus MASTERPROMPT_AGENTEN.md Anhang A WOERTLICH anlegen
unter pruefstand/.claude/agents/<name>.md (Dateiname = name-Feld). Vorhandene Dateien
werden nicht ueberschrieben, sondern gemeldet. Danach Claude Code neu starten.
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = Path(__file__).resolve().parent.parent
mp = (P / "MASTERPROMPT_AGENTEN.md").read_text(encoding="utf-8")
anhang = mp[mp.index("## ANHANG A"):mp.index("## ANHANG B")]
bloecke = re.findall(r"### (A\d+) · `([a-z\-]+)\.md`\s*```markdown\n(.*?)\n```", anhang, re.S)
ziel = P / ".claude" / "agents"
ziel.mkdir(parents=True, exist_ok=True)
for nr, datei, inhalt in bloecke:
    name = re.search(r"^name:\s*(\S+)", inhalt, re.M).group(1)
    if name != datei:
        print(f"WARNUNG {nr}: Dateiname {datei} != name {name}")
    p = ziel / f"{name}.md"
    if p.exists():
        print(f"vorhanden, nicht ueberschrieben: {p.name}")
        continue
    p.write_text(inhalt.rstrip() + "\n", encoding="utf-8")
    print(f"angelegt {nr}: {p.name} ({len(inhalt)} Zeichen)")
print(f"{len(bloecke)} Bloecke im Anhang A gefunden")
