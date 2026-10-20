# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""Berichtigungs-Absatz ans Ende von BOT-HANDBUCH 10.13 (v6, v7) und Abschnitt 0 in die Zielboersen-Vorlage."""
import sys
from pathlib import Path

D = Path(r"C:\Users\<BENUTZER>\Desktop")
ANKER = "Vorab-Registrierung: `pruefstand\\epochen\\E10_L9_kostenlatte_bitvavo.md`."
ABSATZ = (
    "\n\n**Berichtigung 14.10.2026, 16:30 (nach Prüf-Agent A5).** Die E7-Zahlen dieses Abschnitts waren zuerst "
    "falsch. Bei den 21 Verkäufen über ein Verkaufssignal (`execute_approved_trade`) steht im Journal der Betrag "
    "**nach** Abzug der Gebühr. Das Prüfstand-Skript zog sie ein zweites Mal ab. Der Profitabilitäts-Bericht vom "
    "14.10. hatte denselben Fehler. Richtig für E7 (136 Runden): **brutto +75,51 $ (+0,33 % je Runde), Gebühren "
    "109,62 $, netto −34,11 $** (nicht −43,13 $). Unter Bitvavo-Kosten inkl. Schlupf wären es **+42,66 $** gewesen "
    "(nicht +33,65 $). Die doppelte Kaufgebühr (Befund 42) betraf **alle 136 Runden** (gebucht −88,89 $ = Kasse "
    "minus 54,78 $ Kaufgebühren), nicht nur die 115 über `exit_monitor`. Seit E9 ist sie für beide Wege behoben. "
    "Die Entscheidung für Bitvavo ändert das nicht."
)
for hb in (D / "trading_imperium_v6(21)" / "BOT-HANDBUCH.md", D / "trading_imperium_v7" / "BOT-HANDBUCH.md"):
    b = hb.read_bytes()
    nl = "\r\n" if b.count(b"\r\n") > b.count(b"\n") / 2 else "\n"
    t = b.decode("utf-8")
    if "Berichtigung 14.10.2026, 16:30" in t:
        print(hb.parent.name, "schon da"); continue
    assert t.count(ANKER) == 1, f"Anker {t.count(ANKER)}x in {hb}"
    t = t.replace(ANKER, ANKER + ABSATZ.replace("\n", nl), 1)
    nb = t.encode("utf-8")
    assert nl == "\n" or nb.count(b"\r\n") == nb.count(b"\n")
    hb.write_bytes(nb)
    print(hb.parent.name, "10.13 Berichtigung eingefuegt")

v = D / "pruefstand" / "berichte" / "2026-10-14_zielboerse.md"
t = v.read_text(encoding="utf-8")
if "## 0 · Berichtigung" not in t:
    t = t.replace("---\n\n## 1 · Was du entscheiden sollst", (
        "---\n\n## 0 · Berichtigung 14.10.2026, 16:30 (nach Prüf-Agent A5)\n\n"
        "Die Zahlen der ersten Fassung (Bitvavo +33,65 $, Bybit −43,85 $, brutto +0,29 % je Runde) waren um 9,02 $ zu schlecht. "
        "Bei den 21 Signal-Verkäufen steht im Journal der Betrag schon nach Abzug der Gebühr, und das Rundenskript zog sie ein zweites Mal ab. "
        "Alle Tabellen unten sind berichtigt: brutto **+75,51 $ / +0,332 % je Runde**, Bitvavo **+42,66 $**, OKX +29,52 $, Gate +19,45 $, Bybit −34,85 $. "
        "**An der Rangfolge und an der Empfehlung ändert das nichts.** Der Vorsprung vor Kosten bleibt im Block-Bootstrap unbelegt "
        "(−0,18 % bis +0,81 %). Bitvavo EUR (≈ −34,2 $), OKX ohne X-Perps (≈ −80 $) und Coinbase (≈ −187 $) sind nur um +9 $ verschoben, nicht neu gerechnet.\n\n"
        "## 1 · Was du entscheiden sollst"), 1)
    v.write_text(t, encoding="utf-8")
    print("Vorlage: Abschnitt 0 eingefuegt")
