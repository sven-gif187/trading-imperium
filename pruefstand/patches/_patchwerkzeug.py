# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Gemeinsames Werkzeug fuer Pruefstand-Patches (Regel 9.4 MASTERPROMPT_AGENTEN.md).

Jeder Patch ist eine Liste von Ersetzungen (Datei, alt, neu). Das Werkzeug
  - findet jeden Anker GENAU einmal, sonst Abbruch ohne Aenderung,
  - erkennt "schon angewendet" an einer Marke und tut dann nichts (idempotent),
  - behaelt die Zeilenenden JE DATEI (v6 engine.py LF, v7 engine.py CRLF),
  - prueft das Ergebnis mit ast.parse, bevor es geschrieben wird,
  - legt <datei>.bak_<marke>_<JJJJMMTT_HHMMSS> an,
  - nimmt alles zurueck, wenn eine spaetere Datei scheitert.

Aufrufe je Patch-Skript:  --pruefen  |  --selbsttest  |  --anwenden
Der Bot muss beim Anwenden vollstaendig geschlossen sein (Regel 9.3).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psutil


@dataclass
class Ersetzung:
    datei: str      # relativ zum Bot-Ordner
    alt: str        # Anker, mit \n geschrieben
    neu: str        # Ersatz, mit \n geschrieben


def _zeilenende(b: bytes) -> str:
    return "\r\n" if b.count(b"\r\n") > b.count(b"\n") / 2 else "\n"


def _bot_laeuft(ordner: Path) -> list[int]:
    ziel = str(ordner.resolve()).lower()
    pids = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower().startswith("python") and \
                    any(c.endswith("app.py") for c in (p.info["cmdline"] or [])) and \
                    str(Path(p.cwd()).resolve()).lower() == ziel:
                pids.append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids


def pruefen(ordner: Path, ersetzungen: list[Ersetzung], marke: str) -> tuple[bool, list[str]]:
    """(bereit, meldungen). bereit=False auch dann, wenn schon angewendet."""
    msg, ok, schon = [], True, 0
    for e in ersetzungen:
        p = ordner / e.datei
        if not p.exists():
            msg.append(f"FEHLT  {e.datei}"); ok = False; continue
        b = p.read_bytes()
        nl = _zeilenende(b)
        t = b.decode("utf-8")
        alt, neu = e.alt.replace("\n", nl), e.neu.replace("\n", nl)
        if t.count(neu) == 1 and marke in t:
            msg.append(f"SCHON  {e.datei}: bereits angewendet"); schon += 1; continue
        n = t.count(alt)
        art = "CRLF" if nl == "\r\n" else "LF"
        if n != 1:
            msg.append(f"ANKER  {e.datei}: {n}x gefunden (erwartet 1)"); ok = False
        else:
            msg.append(f"BEREIT {e.datei} ({art})")
    if schon == len(ersetzungen):
        return False, msg + ["Alles bereits angewendet - nichts zu tun."]
    if schon:
        return False, msg + ["Teilweise angewendet - bitte von Hand ansehen."]
    return ok, msg


def anwenden(ordner: Path, ersetzungen: list[Ersetzung], marke: str, trocken_kopie: bool = False) -> int:
    ok, msg = pruefen(ordner, ersetzungen, marke)
    for m in msg:
        print("  " + m)
    if not ok:
        print("  NICHT angewendet."); return 1
    if not trocken_kopie:
        pids = _bot_laeuft(ordner)
        if pids:
            print(f"  ABBRUCH: Bot laeuft noch (PID {pids}). Erst vollstaendig schliessen (Regel 9.3).")
            return 1
    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    gesichert: list[tuple[Path, Path]] = []
    try:
        for e in ersetzungen:
            p = ordner / e.datei
            b = p.read_bytes()
            nl = _zeilenende(b)
            t = b.decode("utf-8")
            t2 = t.replace(e.alt.replace("\n", nl), e.neu.replace("\n", nl), 1)
            if p.suffix == ".py":
                ast.parse(t2)
            elif p.suffix == ".json":
                json.loads(t2)
            # [14.10.2026] Je Datei nur EINMAL sichern, vor der ersten Aenderung.
            # Vorher bekam eine zweimal geaenderte Datei zwei gleichnamige
            # Sicherungen (gleiche Sekunde) - die zweite ueberschrieb das Original.
            if p not in [g[0] for g in gesichert]:
                kurz = re.sub(r"[^A-Za-z0-9]+", "_", marke).strip("_").lower()
                bak = p.with_name(f"{p.name}.bak_{kurz}_{stempel}")
                shutil.copy2(p, bak)
                gesichert.append((p, bak))
            else:
                bak = next(g[1] for g in gesichert if g[0] == p)
            p.write_bytes(t2.encode("utf-8"))
            nach = p.read_bytes()
            if _zeilenende(nach) != nl or nach.decode("utf-8") != t2:
                raise RuntimeError(f"Nachkontrolle {e.datei} fehlgeschlagen")
            print(f"  GESCHRIEBEN {e.datei}  (Sicherung {bak.name})")
    except Exception as ex:
        # [14.10.2026] Rueckwaerts: aendert ein Patch dieselbe Datei zweimal,
        # muss die ERSTE Sicherung zuletzt zurueckgespielt werden.
        for p, bak in reversed(gesichert):
            shutil.copy2(bak, p)
        print(f"  FEHLER {ex!r} - alle Dateien zurueckgesetzt.")
        return 1
    return 0


def selbsttest(ordner: Path, ersetzungen: list[Ersetzung], marke: str) -> int:
    """Auf einer Kopie: anwenden, Idempotenz, Original unberuehrt, Zeilenenden."""
    fehler = 0
    _, msg = pruefen(ordner, ersetzungen, marke)
    if msg and msg[-1].startswith("Alles bereits angewendet"):
        print("  Patch ist im Bot bereits eingespielt - Selbsttest auf der Kopie entfaellt.")
        print("SELBSTTEST ENTFAELLT (schon angewendet)")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        kopie = Path(tmp) / "bot"
        for e in ersetzungen:
            ziel = kopie / e.datei
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ordner / e.datei, ziel)
        vorher = {e.datei: (ordner / e.datei).read_bytes() for e in ersetzungen}
        r = anwenden(kopie, ersetzungen, marke, trocken_kopie=True)
        fehler += r != 0
        print(f"  {'OK  ' if r == 0 else 'FEHL'} Kopie gepatcht")
        for e in ersetzungen:
            b = (kopie / e.datei).read_bytes()
            ok = _zeilenende(b) == _zeilenende(vorher[e.datei]) and marke in b.decode("utf-8")
            fehler += not ok
            print(f"  {'OK  ' if ok else 'FEHL'} {e.datei}: Marke da, Zeilenenden gleich")
            if e.datei.endswith(".py"):
                try:
                    compile(b.decode("utf-8"), e.datei, "exec"); print(f"  OK   {e.datei}: uebersetzbar")
                except SyntaxError as se:
                    fehler += 1; print(f"  FEHL {e.datei}: {se}")
        bereit, _ = pruefen(kopie, ersetzungen, marke)
        fehler += bereit
        print(f"  {'OK  ' if not bereit else 'FEHL'} zweiter Lauf erkennt 'schon angewendet' (idempotent)")
        unberuehrt = all((ordner / e.datei).read_bytes() == vorher[e.datei] for e in ersetzungen)
        fehler += not unberuehrt
        print(f"  {'OK  ' if unberuehrt else 'FEHL'} Original unberuehrt")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return 1 if fehler else 0


def main(ordner: Path, ersetzungen: list[Ersetzung], marke: str, titel: str, zusatztest=None) -> None:
    ap = argparse.ArgumentParser(description=titel)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pruefen", action="store_true")
    g.add_argument("--selbsttest", action="store_true")
    g.add_argument("--anwenden", action="store_true")
    a = ap.parse_args()
    print("=" * 70 + f"\n{titel}\nZiel: {ordner}\n" + "=" * 70)
    if a.pruefen:
        ok, msg = pruefen(ordner, ersetzungen, marke)
        for m in msg:
            print("  " + m)
        print("  " + ("BEREIT - mit --anwenden einspielen (Bot vorher schliessen)" if ok else "NICHT bereit"))
        sys.exit(0 if ok else 1)
    if a.selbsttest:
        r = selbsttest(ordner, ersetzungen, marke)
        if zusatztest:
            r |= zusatztest()
        sys.exit(r)
    sys.exit(anwenden(ordner, ersetzungen, marke))
