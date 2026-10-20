# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Zeilenenden zuruecksetzen: CRLF -> LF fuer Dateien, die VOR einem Patch LF waren.

ANLASS 14.10.2026: patch_00a/45/63 aus patches_nach_27_08 lesen und schreiben im
Textmodus (open(..., "w")). Unter Windows macht das aus jedem \\n ein \\r\\n.
v6 risk/exit_rules.py und agents/cycle_theory.py waren vor E8 LF (Beleg:
pruefstand/sicherungen/20261014_111551_vor_E8_v6, byte-genau), danach CRLF.
Regel 9.4: Zeilenenden erhalten.

Aendert NUR die Zeilenenden. Inhalt wird verglichen: nach dem Umbau muss
der Text Zeichen fuer Zeichen gleich sein (bis auf \\r), und ast.parse muss gehen.
Aufruf: python zeilenenden_zurueck_lf.py <datei> [<datei> ...]   (Bot geschlossen!)
"""
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
fehler = 0
for arg in sys.argv[1:]:
    p = Path(arg)
    b = p.read_bytes()
    lf, crlf = b.count(b"\n"), b.count(b"\r\n")
    if crlf == 0:
        print(f"{p.name}: schon LF - nichts zu tun"); continue
    if crlf != lf or b.count(b"\r") != crlf:
        print(f"{p.name}: gemischt (LF {lf}, CRLF {crlf}) - NICHT angefasst"); fehler += 1; continue
    neu = b.replace(b"\r\n", b"\n")
    if neu.decode("utf-8") != b.decode("utf-8").replace("\r\n", "\n"):
        print(f"{p.name}: Inhaltsvergleich fehlgeschlagen"); fehler += 1; continue
    if p.suffix == ".py":
        ast.parse(neu.decode("utf-8"))
    shutil.copy2(p, p.with_name(f"{p.name}.bak_crlf_{stempel}"))
    p.write_bytes(neu)
    nach = p.read_bytes()
    ok = nach.count(b"\r") == 0 and nach.count(b"\n") == lf
    fehler += not ok
    print(f"{p.name}: {'LF wiederhergestellt' if ok else 'FEHLER'} ({lf} Zeilen)")
sys.exit(1 if fehler else 0)
