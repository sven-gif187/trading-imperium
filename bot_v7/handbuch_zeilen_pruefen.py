# -*- coding: utf-8 -*-
"""Haelt jede Zeilenangabe im BOT-HANDBUCH gegen den echten Code.

WOZU
    Zeilennummern sind die verderblichste Angabe im ganzen Handbuch. Am
    24.08.2026 waren im Rundgang SIEBEN VON ACHT falsch - um 20 bis 1.135
    Zeilen daneben, weil app.py zwischenzeitlich von 3.580 auf 4.634 Zeilen
    gewachsen war. Niemand hatte etwas falsch gemacht. Sie altern von allein,
    und zwar lautlos: Der Satz drumherum bleibt richtig, nur der Verweis
    zeigt ins Leere.

        > Was man von Hand pruefen muss, prueft man einmal.
        > Was ein Programm prueft, wird jedes Mal geprueft.

    Dieselbe Ueberlegung wie bei schon_bekannt.py und prozess_frische.py.

WAS ES PRUEFT
    1. `funktionsname`, Zeile N      -> steht die Funktion wirklich dort?
    2. `datei.py:N`                  -> gibt es die Datei, hat sie so viele Zeilen?
    3. `datei.py` (NNN Zeilen)       -> stimmt die genannte Laenge?

AUFRUF
    python handbuch_zeilen_pruefen.py              alles
    python handbuch_zeilen_pruefen.py --nur-fehler nur die Abweichungen
    python handbuch_zeilen_pruefen.py --selbsttest Gegentest in beide Richtungen

    Reine Leseoperation. Aendert nichts, weder am Handbuch noch am Bot.
"""
import io
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
BUCH = os.path.join(HIER, "BOT-HANDBUCH.md")

# Ordner, die nicht mitzaehlen: Archive und Fremdkopien fuehren zu
# Doppeltreffern und beantworten keine Frage ueber den laufenden Bot.
AUS = ("archiv", "_archive", ".git", "__pycache__", ".claude", "venv",
       "site-packages", "backup")

MUSTER_FN = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`[^`\n]{0,25}?Zeile\s+(\d+)")
MUSTER_DT = re.compile(r"`([\w/\\.-]+\.py):(\d+)`")
MUSTER_LN = re.compile(r"`([\w/\\.-]+\.py)`[^`\n]{0,12}?\((\d+)\s*Zeilen\)")


def _zeilen(pfad):
    try:
        with io.open(pfad, encoding="utf-8", errors="replace") as f:
            return f.read().split("\n")
    except Exception:
        return None


_BASIS = {}


def _basis_index():
    """Dateiname ohne Ordner -> [vollstaendige Pfade].

    [24.08.2026] Das Handbuch schreibt oft nur `engine.py:575`, ohne
    Ordner. Beim ersten Lauf meldete diese Pruefung neun solcher Stellen
    als 'Datei gibt es nicht' - und lag jedesmal selbst falsch: gemeint
    war `risk/engine.py`. Ein Pruefwerkzeug, das den Autor fuer seinen
    eigenen blinden Fleck ruegt, ist schlimmer als keines.

    Bleibt der Name mehrdeutig (engine.py gibt es dreimal), wird die
    Stelle als UNKLAR gemeldet, nicht als Fehler. Raten waere schlimmer
    als zugeben.
    """
    if _BASIS:
        return _BASIS
    for wurzel, ordner, dateien in os.walk(HIER):
        ordner[:] = [o for o in ordner
                     if not any(a in o.lower() for a in AUS)]
        for d in dateien:
            if d.endswith(".py"):
                rel = os.path.relpath(os.path.join(wurzel, d),
                                      HIER).replace("\\", "/")
                _BASIS.setdefault(d, []).append(rel)
    return _BASIS


def aufloesen(name):
    """-> (pfad, hinweis) oder (None, grund)"""
    p = os.path.join(HIER, name)
    if os.path.exists(p):
        return p, ""
    if "/" in name or "\\" in name:
        return None, "Pfad gibt es nicht"
    kand = _basis_index().get(os.path.basename(name), [])
    if len(kand) == 1:
        return os.path.join(HIER, kand[0]), "= " + kand[0]
    if len(kand) > 1:
        return None, "mehrdeutig: " + ", ".join(kand[:4])
    return None, "Datei gibt es nicht"


def index_bauen():
    """name -> [(datei, zeile), ...] fuer jedes def und class im Projekt."""
    idx = {}
    for wurzel, ordner, dateien in os.walk(HIER):
        ordner[:] = [o for o in ordner
                     if not any(a in o.lower() for a in AUS)]
        for d in dateien:
            if not d.endswith(".py"):
                continue
            p = os.path.join(wurzel, d)
            rel = os.path.relpath(p, HIER).replace("\\", "/")
            t = _zeilen(p)
            if t is None:
                continue
            for k, l in enumerate(t):
                m = re.match(r"\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", l)
                if not m:
                    m = re.match(r"\s*class\s+([A-Za-z_]\w*)\b", l)
                if m:
                    idx.setdefault(m.group(1), []).append((rel, k + 1))
    return idx


def datei_im_umfeld(zeilen, bis, fenster=60):
    """Welche .py-Datei wird kurz vor dieser Handbuchzeile genannt?

    Der Rundgang nennt die Datei in der Ueberschrift ('Runde 2 - risk/')
    und im Abschnittstitel. Ohne diesen Zusammenhang waere '__init__'
    nicht zuzuordnen - den gibt es dutzendfach.
    """
    for i in range(bis, max(-1, bis - fenster), -1):
        for m in re.finditer(r"`([\w/\\.-]+\.py)`", zeilen[i]):
            return m.group(1).replace("\\", "/")
    return None


def sammeln():
    z = _zeilen(BUCH)
    if z is None:
        print("BOT-HANDBUCH.md nicht lesbar."), sys.exit(2)
    treffer, drin = [], False
    for i, l in enumerate(z):
        if l.startswith("```"):
            drin = not drin
            continue
        if drin:
            continue
        for m in MUSTER_FN.finditer(l):
            treffer.append(("fn", m.group(1), int(m.group(2)), i + 1,
                            datei_im_umfeld(z, i)))
        for m in MUSTER_DT.finditer(l):
            treffer.append(("dt", m.group(1), int(m.group(2)), i + 1, None))
        for m in MUSTER_LN.finditer(l):
            treffer.append(("ln", m.group(1), int(m.group(2)), i + 1, None))
    return treffer


def pruefen(treffer, idx):
    """-> Liste (ampel, text). ampel: OK / FALSCH / UNKLAR"""
    aus = []
    for art, name, nr, hz, umfeld in treffer:
        if art == "dt":
            p, hinweis = aufloesen(name)
            t = _zeilen(p) if p else None
            if t is None:
                ampel = "UNKLAR" if hinweis.startswith("mehrdeutig") else "FALSCH"
                aus.append((ampel, "%s:%d  -> %s" % (name, nr, hinweis), hz))
            elif nr > len(t):
                aus.append(("FALSCH", "%s:%d  -> Datei hat nur %d Zeilen %s"
                            % (name, nr, len(t), hinweis), hz))
            else:
                aus.append(("OK", "%s:%d %s" % (name, nr, hinweis), hz))
            continue

        if art == "ln":
            p, hinweis = aufloesen(name)
            t = _zeilen(p) if p else None
            if t is None:
                ampel = "UNKLAR" if hinweis.startswith("mehrdeutig") else "FALSCH"
                aus.append((ampel, "%s (%d Zeilen) -> %s"
                            % (name, nr, hinweis), hz))
            elif abs(len(t) - nr) > 5:          # kleine Drift ist kein Fehler
                aus.append(("FALSCH", "%s: Handbuch %d Zeilen, echt %d  (%+d)"
                            % (name, nr, len(t), len(t) - nr), hz))
            else:
                aus.append(("OK", "%s (%d Zeilen)" % (name, nr), hz))
            continue

        kand = idx.get(name, [])
        if umfeld:
            eng = [k for k in kand if k[0].endswith(umfeld)]
            if eng:
                kand = eng
        if not kand:
            # [24.08.2026] Kein Funktionsname, sondern eine Epochenkennung
            # wie `E7` oder `E11`. Der Satz "Epoche `E7` ... Zeile 193"
            # sieht fuer das Muster aus wie ein Verweis, ist aber keiner.
            # Solche Treffer werden verschwiegen statt als unklar gemeldet -
            # sonst gewoehnt man sich an gelbe Zeilen, die nie gruen werden.
            if re.match(r"^[A-Z]\d{1,2}$", name):
                continue
            aus.append(("UNKLAR", "%s Zeile %d -> nirgends als def/class"
                        % (name, nr), hz))
        elif any(k[1] == nr for k in kand):
            aus.append(("OK", "%s Zeile %d" % (name, nr), hz))
        elif len(kand) == 1:
            d, e = kand[0]
            aus.append(("FALSCH", "%s: Handbuch %d, echt %d in %s  (%+d)"
                        % (name, nr, e, d, e - nr), hz))
        else:
            wo = ", ".join("%s:%d" % k for k in kand[:4])
            aus.append(("UNKLAR", "%s Zeile %d -> mehrdeutig: %s"
                        % (name, nr, wo), hz))
    return aus


def selbsttest():
    """Gegentest in BEIDE Richtungen - findet er den echten Fall, und
    meldet er nichts Falsches? Ein Pruefwerkzeug ohne diesen Test ist
    selbst ungeprueft."""
    print("=" * 74)
    print("SELBSTTEST - findet die Pruefung, was sie finden soll?")
    print("=" * 74)
    idx = index_bauen()
    fehler = 0

    # Richtung 1: eine absichtlich falsche Angabe MUSS auffallen.
    echt = idx.get("main", [("app.py", 1)])[0]
    falsch = [("fn", "main", echt[1] + 999, 1, echt[0])]
    r = pruefen(falsch, idx)
    ok = r and r[0][0] == "FALSCH"
    print("  %-5s falsche Zeilennummer wird gemeldet" % ("OK" if ok else "FEHLT"))
    fehler += 0 if ok else 1

    # Richtung 2: die richtige Angabe darf NICHT gemeldet werden.
    richtig = [("fn", "main", echt[1], 1, echt[0])]
    r = pruefen(richtig, idx)
    ok = r and r[0][0] == "OK"
    print("  %-5s richtige Zeilennummer bleibt still" % ("OK" if ok else "FEHLT"))
    fehler += 0 if ok else 1

    # Richtung 3: eine erfundene Datei MUSS auffallen.
    r = pruefen([("dt", "gibt_es_nicht.py", 5, 1, None)], idx)
    ok = r and r[0][0] == "FALSCH"
    print("  %-5s erfundene Datei wird gemeldet" % ("OK" if ok else "FEHLT"))
    fehler += 0 if ok else 1

    # Richtung 4: eine echte Datei mit unmoeglicher Zeile MUSS auffallen.
    r = pruefen([("dt", "app.py", 999999, 1, None)], idx)
    ok = r and r[0][0] == "FALSCH"
    print("  %-5s Zeile jenseits des Dateiendes wird gemeldet"
          % ("OK" if ok else "FEHLT"))
    fehler += 0 if ok else 1

    print()
    print("SELBSTTEST BESTANDEN" if not fehler
          else "SELBSTTEST GESCHEITERT (%d)" % fehler)
    return 0 if not fehler else 1


def main():
    if "--selbsttest" in sys.argv:
        return selbsttest()
    nur_fehler = "--nur-fehler" in sys.argv

    treffer = sammeln()
    idx = index_bauen()
    aus = pruefen(treffer, idx)

    print("=" * 78)
    print("  ZEILENANGABEN IM BOT-HANDBUCH  -  zeigen sie noch dorthin,")
    print("  wo sie hinzeigen sollen?")
    print("=" * 78)
    print()

    zaehl = {"OK": 0, "FALSCH": 0, "UNKLAR": 0}
    for ampel, text, hz in aus:
        zaehl[ampel] += 1
        if nur_fehler and ampel == "OK":
            continue
        print("  %-7s Handbuch %-6d %s" % (ampel, hz, text))

    print()
    print("-" * 78)
    print("  geprueft %d   stimmt %d   FALSCH %d   unklar %d"
          % (len(aus), zaehl["OK"], zaehl["FALSCH"], zaehl["UNKLAR"]))
    if zaehl["FALSCH"]:
        print()
        print("  Der Name der Funktion ist die Adresse, die Zeilennummer nur")
        print("  die Hausnummer. Oben steht bei jeder Abweichung die echte.")
    print("=" * 78)
    return 1 if zaehl["FALSCH"] else 0


if __name__ == "__main__":
    sys.exit(main())
