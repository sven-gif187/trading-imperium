# -*- coding: utf-8 -*-
"""
erledigtes_archivieren.py — nimmt Erledigtes aus den aktiven Listen heraus
==========================================================================

WARUM ES DIESES PROGRAMM GIBT
-----------------------------
Sven am 19.08.2026:

    "koennen wir das nicht so klaeren das du das erledigte in zukunft aus
     dem kontextfenster nimmst automatisch damit wir immer auf dem
     aktuellsten stand sind; und die rausgeschmissenen sachen in einen
     ordner ablegst das wir das zur not nochmals gegenpruefen koennen"

Der Gedanke ist richtig, die Umsetzung liegt eine Ebene tiefer: Ein
Sprachmodell kann sein eigenes Kontextfenster nicht leeren - was gelesen
wurde, bleibt bis zum Sitzungsende drin. Aber **die Dateien lassen sich
kleiner machen**, und das bewirkt dasselbe: weniger lesen, und das
Gelesene ist relevant.

Gemessen am 19.08.2026:
    GEFUNDENE-PROBLEME.md   23 Punkte offen  (27.730 Bytes)
                            23 Punkte behoben (45.724 Bytes)
    Die behobenen belegen 62 % der Datei.

WAS ES TUT
----------
Verschiebt behobene Punkte aus der aktiven Liste in
`archiv/GEFUNDENE-PROBLEME_behoben.md`. In der aktiven Liste bleibt je
Punkt **eine Zeile** stehen - Nummer, Titel, Datum, Verweis. Damit:

  * bleiben die Nummern eindeutig (Punkt 25 bleibt Punkt 25)
  * ist auf einen Blick sichtbar, dass es ihn gab
  * ist der volle Text eine Datei weiter jederzeit nachlesbar

NICHTS WIRD GELOESCHT. Vor jedem Lauf entsteht eine Sicherung.

WAS ES NICHT ANFASST
--------------------
`BOT-HANDBUCH.md` und `ENTWICKLERHANDBUCH.md`. Beide sind **Chronik** -
ihr Zweck ist gerade, dass Altes stehenbleibt. Wer dort kuerzt, zerstoert
den Wert. Fuer sie ist der richtige Weg ein Auszug, keine Auslagerung.

AUFRUF
------
    python erledigtes_archivieren.py --pruefen     zeigen, was gehen wuerde
    python erledigtes_archivieren.py --schreiben   ausfuehren
    python erledigtes_archivieren.py --selbsttest  Gegentest beide Richtungen
"""
import io
import os
import re
import shutil
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(HIER, "GEFUNDENE-PROBLEME.md")
ARCHIV_ORDNER = os.path.join(HIER, "archiv")
ARCHIV = os.path.join(ARCHIV_ORDNER, "GEFUNDENE-PROBLEME_behoben.md")

ERLEDIGT = re.compile(r"✅|BEHOBEN|GEKL[AÄ]ERT|ERLEDIGT", re.I)
# Eine Zeile, die schon ein Verweis ist - die wird nicht nochmal verschoben
IST_VERWEIS = re.compile(r"^### \d+\.\s*✅.*→ `archiv/", re.M)


def zerlegen(text):
    """(vorspann, [(kopf, rumpf), ...]) - Punkte in der Reihenfolge der Datei."""
    teile = re.split(r"^(### \d+\..*)$", text, flags=re.M)
    vorspann = teile[0]
    punkte = []
    for i in range(1, len(teile), 2):
        punkte.append((teile[i], teile[i + 1] if i + 1 < len(teile) else ""))
    return vorspann, punkte


def nummer_von(kopf):
    m = re.match(r"### (\d+)\.", kopf)
    return int(m.group(1)) if m else None


def titel_von(kopf):
    m = re.match(r"### \d+\.\s*(.*)", kopf)
    t = m.group(1).strip() if m else kopf
    return re.sub(r"^[✅✓]\s*", "", t)


def datum_von(kopf, rumpf):
    """Erstes Datum im Kopf oder in den ersten Zeilen des Rumpfs."""
    for quelle in (kopf, rumpf[:400]):
        m = re.search(r"(\d{1,2}\.\d{2}\.(?:\d{4})?)", quelle)
        if m:
            return m.group(1)
    return ""


def analysieren():
    if not os.path.exists(QUELLE):
        return None
    text = io.open(QUELLE, encoding="utf-8").read()
    vorspann, punkte = zerlegen(text)
    offen, fertig = [], []
    for kopf, rumpf in punkte:
        # Schon verschobene Punkte (nur noch Verweis) nicht erneut anfassen
        if "→ `archiv/" in kopf or "→ `archiv/" in rumpf[:200]:
            offen.append((kopf, rumpf))
            continue
        (fertig if ERLEDIGT.search(kopf) else offen).append((kopf, rumpf))
    return {"text": text, "vorspann": vorspann, "offen": offen,
            "fertig": fertig, "gesamt": len(punkte)}


def archivieren(schreiben=False):
    a = analysieren()
    if not a:
        print(f"Datei fehlt: {QUELLE}")
        return 1
    b_bytes = sum(len(k) + len(r) for k, r in a["fertig"])
    o_bytes = sum(len(k) + len(r) for k, r in a["offen"])

    print(f"\n{'='*72}")
    print(f"  GEFUNDENE-PROBLEME.md — {len(a['text']):,} Bytes".replace(",", "."))
    print(f"{'='*72}")
    print(f"  offen   : {len(a['offen']):3d} Punkte  {o_bytes:7,} Bytes".replace(",", "."))
    print(f"  behoben : {len(a['fertig']):3d} Punkte  {b_bytes:7,} Bytes".replace(",", "."))
    if a["text"]:
        print(f"\n  Auslagern wuerde {b_bytes/len(a['text'])*100:.0f} % einsparen.")

    if not a["fertig"]:
        print("\n  Nichts zu archivieren.\n")
        return 0

    print(f"\n  {'Nr':>4}  {'Datum':<10}Titel")
    print("  " + "-" * 66)
    for kopf, rumpf in a["fertig"]:
        print(f"  {nummer_von(kopf) or '?':>4}  {datum_von(kopf, rumpf):<10}"
              f"{titel_von(kopf)[:52]}")

    if not schreiben:
        print(f"\n  Nur geprueft. Zum Ausfuehren: "
              f"python erledigtes_archivieren.py --schreiben\n")
        return 0

    # ---------------------------------------------------------- schreiben
    os.makedirs(ARCHIV_ORDNER, exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d_%H%M%S")
    sicherung = os.path.join(ARCHIV_ORDNER,
                             f"GEFUNDENE-PROBLEME.md.bak_{stempel}")
    shutil.copy2(QUELLE, sicherung)
    print(f"\n  Sicherung: archiv/{os.path.basename(sicherung)}")

    # Archivdatei aufbauen (anhaengen, falls schon vorhanden)
    kopfzeilen = [
        "# Behobene Punkte — Archiv",
        "",
        "**Ausgelagert aus `GEFUNDENE-PROBLEME.md`, damit die aktive Liste",
        "kurz bleibt. Nichts wurde geloescht.**",
        "",
        "Erzeugt mit `python erledigtes_archivieren.py --schreiben`.",
        "Die Nummern entsprechen denen der aktiven Liste — dort steht je",
        "Punkt noch eine Zeile mit Verweis hierher.",
        "",
        "---",
        "",
    ]
    alt = ""
    if os.path.exists(ARCHIV):
        alt = io.open(ARCHIV, encoding="utf-8").read()
        alt = re.sub(r"^# Behobene Punkte.*?^---\n\n", "", alt, flags=re.S | re.M)
    neu_teile = [f"\n## Ausgelagert am {datetime.now():%d.%m.%Y %H:%M}\n"]
    for kopf, rumpf in a["fertig"]:
        neu_teile.append(kopf + "\n" + rumpf.rstrip() + "\n")
    io.open(ARCHIV, "w", encoding="utf-8").write(
        "\n".join(kopfzeilen) + alt.rstrip() + "\n" + "\n".join(neu_teile))

    # Aktive Liste neu aufbauen: offene voll, behobene als Einzeiler
    raus = [a["vorspann"].rstrip(), ""]
    alle = a["offen"] + a["fertig"]
    alle.sort(key=lambda p: nummer_von(p[0]) or 0)
    for kopf, rumpf in alle:
        if (kopf, rumpf) in a["fertig"]:
            nr = nummer_von(kopf)
            d = datum_von(kopf, rumpf)
            raus.append(f"### {nr}. ✅ {titel_von(kopf)}")
            raus.append("")
            raus.append(f"Behoben{' ' + d if d else ''}. Voller Text: "
                        f"→ `archiv/GEFUNDENE-PROBLEME_behoben.md`")
            raus.append("")
        else:
            raus.append(kopf)
            raus.append(rumpf.rstrip())
            raus.append("")
    io.open(QUELLE, "w", encoding="utf-8").write("\n".join(raus).rstrip() + "\n")

    neu_groesse = os.path.getsize(QUELLE)
    print(f"  {len(a['fertig'])} Punkte ausgelagert.")
    print(f"  Aktive Liste: {len(a['text']):,} -> {neu_groesse:,} Bytes "
          f"({100 - neu_groesse/len(a['text'])*100:.0f} % kleiner)"
          .replace(",", "."))
    print(f"  Archiv: archiv/{os.path.basename(ARCHIV)}\n")
    return 0


def selbsttest():
    fehler = 0
    print("\n=== Richtung 1: erkennt es offen und behoben richtig? ===")
    a = analysieren()
    if not a:
        print("  FEHLER: Datei nicht lesbar")
        return 1
    print(f"  Punkte gesamt : {a['gesamt']}")
    print(f"  davon offen   : {len(a['offen'])}")
    print(f"  davon behoben : {len(a['fertig'])}")
    if len(a["offen"]) + len(a["fertig"]) != a["gesamt"]:
        print("  FEHLER: Summe stimmt nicht"); fehler += 1
    else:
        print("  OK: offen + behoben = gesamt")

    # [FIX 19.08.2026] Nach dem ersten Archivieren sind behobene Punkte
    # nur noch Verweise - analysieren() sortiert sie dann unter "offen"
    # ein, weil dort nichts mehr zu verschieben ist. Der erste Testaufbau
    # erwartete sie weiter unter "fertig" und schlug deshalb nach dem
    # ersten erfolgreichen Lauf fehl.
    #
    # Ein Test, der nach dem ersten Erfolg fehlschlaegt, prueft nicht das
    # Programm, sondern einen Zustand, den es nicht mehr gibt.
    print("\n  Stichprobe — drei Punkte, die ERLEDIGT sein muessen")
    print("  (entweder noch mit Volltext oder bereits als Verweis):")
    for nr in (3, 4, 25):
        im_voll = [k for k, _ in a["fertig"] if nummer_von(k) == nr]
        als_verweis = [(k, r) for k, r in a["offen"]
                       if nummer_von(k) == nr
                       and ("→ `archiv/" in k or "→ `archiv/" in r[:200])]
        if im_voll:
            print(f"    #{nr:<3} OK   Volltext, wird ausgelagert: "
                  f"{titel_von(im_voll[0])[:38]}")
        elif als_verweis:
            print(f"    #{nr:<3} OK   bereits archiviert (Verweis): "
                  f"{titel_von(als_verweis[0][0])[:34]}")
        else:
            print(f"    #{nr:<3} FEHLT — weder Volltext noch Verweis")
            fehler += 1
    print("\n  Stichprobe — drei Punkte, die OFFEN sein muessen:")
    for nr in (40, 45, 47):
        tr = [k for k, _ in a["offen"] if nummer_von(k) == nr]
        ok = bool(tr)
        print(f"    #{nr:<3} {'OK  ' if ok else 'FALSCH EINSORTIERT'} "
              f"{titel_von(tr[0])[:44] if tr else ''}")
        if not ok:
            fehler += 1

    print("\n=== Richtung 2: bleiben alle Nummern erhalten? ===")
    nummern = sorted(n for n in (nummer_von(k) for k, _ in a["offen"] + a["fertig"])
                     if n)
    print(f"  {len(nummern)} Nummern, {min(nummern)} bis {max(nummern)}")
    doppelt = [n for n in set(nummern) if nummern.count(n) > 1]
    print(f"  Doppelte: {len(doppelt)} (soll 0)"
          + ("  OK" if not doppelt else f"  FEHLER: {doppelt}"))
    if doppelt:
        fehler += 1

    print("\n=== Richtung 3: faellt es sauber aus, wenn die Datei fehlt? ===")
    global QUELLE
    merk = QUELLE
    QUELLE = os.path.join(HIER, "gibt_es_nicht.md")
    leer = analysieren()
    print(f"  Ohne Datei: {leer} (erwartet None)"
          + ("  OK" if leer is None else "  FEHLER"))
    if leer is not None:
        fehler += 1
    QUELLE = merk

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


# ======================================================================
def offen_struktur_pruefen():
    """Prueft, ob OFFEN.md noch alle vier Gruppen hat.

    [19.08.2026] Zweimal an einem Abend passiert: Beim Ersetzen eines
    Punktes schnitt ein t.find("\n- ", i) zu viel weg und verschluckte die
    Ueberschrift "## C". Alle 20 C-Punkte landeten in Gruppe B, ohne dass
    es beim Lesen auffiel - die Liste sah normal aus, nur die Zuordnung
    war weg.

    Ein Schnitt an einer Textstelle kennt keine Struktur. Diese Pruefung
    schon. Sie gehoert nach JEDER Aenderung an OFFEN.md gelaufen.
    """
    p = os.path.join(HIER, "OFFEN.md")
    if not os.path.exists(p):
        print("OFFEN.md fehlt."); return 1
    t = io.open(p, encoding="utf-8").read()
    fehler = 0
    print(f"\n{'='*60}\n  OFFEN.md — Strukturpruefung\n{'='*60}\n")
    for g in ("A", "B", "C", "D"):
        da = bool(re.search(rf"^## {g} ", t, re.M))
        print(f"  Gruppe {g}: {'vorhanden' if da else 'FEHLT'}")
        if not da:
            fehler += 1
    teile = re.split(r"^(## [A-Z] .*)$", t, flags=re.M)
    print()
    for i in range(1, len(teile), 2):
        rumpf = teile[i + 1] if i + 1 < len(teile) else ""
        o = len(re.findall(r"^- \[ \]", rumpf, re.M))
        e = len(re.findall(r"^- \[x\]", rumpf, re.M))
        print(f"  {teile[i][:44]:<46} {o:>3} offen, {e:>3} erledigt")
    m = re.search(r"^## C .*?\n\n.*?\n\n(.*?)(?=^## D )", t, re.S | re.M)
    if m:
        nr = [(int(a), b) for a, b in
              re.findall(r"^- \[[ x]\] \*\*(\d+)([a-z]?)\.", m.group(1), re.M)]
        sortiert = nr == sorted(nr)
        print(f"\n  Gruppe C Reihenfolge: "
              f"{' '.join(f'{a}{b}' for a, b in nr)}")
        print(f"  {'OK  ' if sortiert else 'FEHLER'} "
              f"{'aufsteigend' if sortiert else 'NICHT sortiert'}")
        if not sortiert:
            fehler += 1
        doppelt = [x for x in set(nr) if nr.count(x) > 1]
        if doppelt:
            print(f"  FEHLER doppelte Nummern: {doppelt}"); fehler += 1
    print("\n  " + ("STRUKTUR IN ORDNUNG" if not fehler
                    else f"{fehler} PROBLEM(E)") + "\n")
    return fehler


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--pruefen"
    if arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)
    if arg == "--offen-struktur":
        sys.exit(1 if offen_struktur_pruefen() else 0)
    sys.exit(archivieren(schreiben=(arg == "--schreiben")))

