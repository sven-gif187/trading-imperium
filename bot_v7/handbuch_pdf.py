"""Erzeugt BOT-HANDBUCH.pdf aus BOT-HANDBUCH.md.

NUR LESEND, was den Bot angeht. Schreibt ausschliesslich das PDF.

WARUM ES DIESES PROGRAMM GIBT
-----------------------------
Am 18.08.2026 fiel Sven auf, dass BOT-HANDBUCH.pdf vom **11.08.** war -
eine Woche alt. Die Kapitel 4.20 bis 4.56 fehlten darin komplett.

Der Grund: Es gab nie einen Generator. Das PDF wurde einmal von Hand
erzeugt und danach nie wieder. Die Regel "jede Aenderung bekommt einen
Handbuch-Eintrag" wurde eingehalten - aber nur in der Markdown-Datei.

> Eine Aufgabe, die von Hand erledigt werden muss, wird genau so lange
> erledigt, wie jemand daran denkt.

Deshalb: ein Programm, ein Aufruf, und ein Haken nach jedem Commit
(.git/hooks/post-commit), der daran erinnert, wenn das PDF aelter ist
als die Markdown-Datei.

WAS UMGESETZT WIRD
------------------
Ueberschriften, Absaetze, Tabellen, Aufzaehlungen, Zitatbloecke,
Quelltextbloecke sowie **fett**, *kursiv* und `Code` im Fliesstext.
Das Handbuch benutzt nichts darueber hinaus.

Aufruf:
    python handbuch_pdf.py                 BOT-HANDBUCH.md -> .pdf
    python handbuch_pdf.py DATEI.md        andere Datei
"""
import html
import os
import re
import sys
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak, KeepTogether)

HIER = os.path.dirname(os.path.abspath(__file__))

BLAU = colors.HexColor("#1a3a5c")
GRAU = colors.HexColor("#f2f2f2")
RAND = colors.HexColor("#cccccc")
ZITAT = colors.HexColor("#8a6d3b")


def stile():
    s = getSampleStyleSheet()
    eigen = {}
    eigen["fliess"] = ParagraphStyle(
        "fliess", parent=s["BodyText"], fontSize=9.5, leading=13,
        spaceAfter=5, alignment=TA_LEFT)
    eigen["h1"] = ParagraphStyle(
        "h1", parent=s["Heading1"], fontSize=17, leading=21,
        textColor=BLAU, spaceBefore=16, spaceAfter=8)
    eigen["h2"] = ParagraphStyle(
        "h2", parent=s["Heading2"], fontSize=13.5, leading=17,
        textColor=BLAU, spaceBefore=14, spaceAfter=6)
    eigen["h3"] = ParagraphStyle(
        "h3", parent=s["Heading3"], fontSize=11, leading=14,
        textColor=colors.HexColor("#33587a"), spaceBefore=10, spaceAfter=4)
    eigen["punkt"] = ParagraphStyle(
        "punkt", parent=eigen["fliess"], leftIndent=14, bulletIndent=5,
        spaceAfter=3)
    eigen["zitat"] = ParagraphStyle(
        "zitat", parent=eigen["fliess"], leftIndent=16, rightIndent=8,
        textColor=ZITAT, borderPadding=4, spaceBefore=5, spaceAfter=7)
    eigen["code"] = ParagraphStyle(
        "code", parent=eigen["fliess"], fontName="Courier", fontSize=8,
        leading=10, leftIndent=8, backColor=GRAU, borderPadding=5,
        spaceBefore=5, spaceAfter=7)
    eigen["zelle"] = ParagraphStyle(
        "zelle", parent=eigen["fliess"], fontSize=8, leading=10, spaceAfter=0)
    eigen["kopf"] = ParagraphStyle(
        "kopf", parent=eigen["zelle"], fontName="Helvetica-Bold",
        textColor=colors.white)
    eigen["titel"] = ParagraphStyle(
        "titel", parent=s["Title"], fontSize=26, leading=32, textColor=BLAU)
    return eigen


def inline(text):
    """Markdown im Fliesstext -> Auszeichnung, die reportlab versteht.

    [FEHLER 18.08.2026] Erst wurden die Code-Abschnitte ersetzt und
    DANACH fett/kursiv. Das ging schief, sobald in einem Code-Abschnitt
    ein Sternchen stand - etwa bei `install_*`/`fix_*` (Handbuch 4.13).
    Die Kursiv-Erkennung griff dann quer durch zwei fertige <font>-Marken
    und erzeugte verschraenkte Auszeichnungen; reportlab brach ab mit
    "saw </font> instead of expected </i>".

    Jetzt werden Code-Abschnitte zuerst durch Platzhalter ersetzt, die
    kein Sonderzeichen enthalten, und ganz am Ende zurueckgetauscht.
    Damit kann keine spaetere Regel mehr hineingreifen.

    Merke: Wer Text in mehreren Durchgaengen ersetzt, muss die fertigen
    Stellen aus dem Weg nehmen - sonst bearbeitet der zweite Durchgang
    das Ergebnis des ersten.
    """
    text = html.escape(text, quote=False)

    tresor = []

    def einlagern(m):
        tresor.append(m.group(1))
        return f"\x00{len(tresor)-1}\x00"

    text = re.sub(r"`([^`]+)`", einlagern, text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", text)

    for nr, inhalt in enumerate(tresor):
        text = text.replace(
            f"\x00{nr}\x00",
            f'<font face="Courier" size="8.5">{inhalt}</font>')
    return text


def tabelle_bauen(zeilen, st, breite):
    """Eine Markdown-Tabelle in eine gesetzte Tabelle verwandeln."""
    daten = []
    for i, z in enumerate(zeilen):
        felder = [f.strip() for f in z.strip().strip("|").split("|")]
        if i == 1 and all(set(f) <= set("-: ") for f in felder if f):
            continue                      # die Trennzeile ---|---
        stil = st["kopf"] if i == 0 else st["zelle"]
        daten.append([Paragraph(inline(f), stil) for f in felder])
    if not daten:
        return None

    spalten = max(len(z) for z in daten)
    for z in daten:                       # fehlende Zellen auffuellen
        while len(z) < spalten:
            z.append(Paragraph("", st["zelle"]))

    t = Table(daten, colWidths=[breite / spalten] * spalten, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLAU),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAU]),
        ("GRID", (0, 0), (-1, -1), 0.4, RAND),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def umwandeln(md, st, breite):
    fluss = []
    zeilen = md.split("\n")
    i = 0
    while i < len(zeilen):
        z = zeilen[i]
        blank = z.strip()

        # --- Quelltextblock
        if blank.startswith("```"):
            i += 1
            block = []
            while i < len(zeilen) and not zeilen[i].strip().startswith("```"):
                block.append(html.escape(zeilen[i], quote=False))
                i += 1
            i += 1
            if block:
                fluss.append(Paragraph("<br/>".join(
                    b.replace(" ", "&nbsp;") or "&nbsp;" for b in block),
                    st["code"]))
            continue

        # --- Tabelle
        if blank.startswith("|") and i + 1 < len(zeilen) \
                and set(zeilen[i + 1].strip()) <= set("|-: "):
            block = []
            while i < len(zeilen) and zeilen[i].strip().startswith("|"):
                block.append(zeilen[i])
                i += 1
            t = tabelle_bauen(block, st, breite)
            if t is not None:
                fluss.append(Spacer(1, 4))
                fluss.append(t)
                fluss.append(Spacer(1, 7))
            continue

        # --- Trennlinie
        if blank in ("---", "***", "___"):
            fluss.append(Spacer(1, 6))
            fluss.append(Table([[""]], colWidths=[breite], rowHeights=[0.6],
                               style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), RAND)])))
            fluss.append(Spacer(1, 8))
            i += 1
            continue

        # --- Ueberschriften
        if blank.startswith("#"):
            grad = len(blank) - len(blank.lstrip("#"))
            text = blank.lstrip("#").strip()
            stil = st["h1"] if grad == 1 else st["h2"] if grad == 2 else st["h3"]
            fluss.append(Paragraph(inline(text), stil))
            i += 1
            continue

        # --- Zitatblock
        if blank.startswith(">"):
            block = []
            while i < len(zeilen) and zeilen[i].strip().startswith(">"):
                block.append(zeilen[i].strip().lstrip(">").strip())
                i += 1
            fluss.append(Paragraph(inline(" ".join(block)), st["zitat"]))
            continue

        # --- Aufzaehlung
        if re.match(r"^\s*([-*+]|\d+\.)\s+", z):
            block = []
            while i < len(zeilen) and (
                    re.match(r"^\s*([-*+]|\d+\.)\s+", zeilen[i])
                    or (zeilen[i].startswith("  ") and zeilen[i].strip()
                        and block)):
                roh = zeilen[i]
                if re.match(r"^\s*([-*+]|\d+\.)\s+", roh):
                    block.append(re.sub(r"^\s*([-*+]|\d+\.)\s+", "", roh))
                else:
                    block[-1] += " " + roh.strip()
                i += 1
            for punkt in block:
                fluss.append(Paragraph(inline(punkt), st["punkt"],
                                       bulletText="•"))
            fluss.append(Spacer(1, 4))
            continue

        # --- Leerzeile
        if not blank:
            i += 1
            continue

        # --- Absatz (Folgezeilen anhaengen, Markdown bricht weich um)
        block = [z.strip()]
        i += 1
        while i < len(zeilen) and zeilen[i].strip() and not re.match(
                r"^\s*(#|\||>|```|---|[-*+]\s|\d+\.\s)", zeilen[i]):
            block.append(zeilen[i].strip())
            i += 1
        fluss.append(Paragraph(inline(" ".join(block)), st["fliess"]))
    return fluss


def fusszeile(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(2 * cm, 1.1 * cm, doc._titel_kurz)
    canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Seite {doc.page}")
    canvas.restoreState()


def main():
    quelle = sys.argv[1] if len(sys.argv) > 1 else "BOT-HANDBUCH.md"
    quelle = os.path.join(HIER, quelle) if not os.path.isabs(quelle) else quelle
    if not os.path.exists(quelle):
        print(f"Nicht gefunden: {quelle}")
        return 1
    ziel = os.path.splitext(quelle)[0] + ".pdf"

    with open(quelle, encoding="utf-8") as f:
        md = f.read()

    st = stile()
    breite = A4[0] - 4 * cm
    doc = SimpleDocTemplate(
        ziel, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=1.8 * cm,
        title=os.path.basename(ziel), author="Trading Imperium V6")
    doc._titel_kurz = os.path.basename(quelle)

    jetzt = datetime.now(timezone.utc)
    deckel = [
        Spacer(1, 5 * cm),
        Paragraph(os.path.basename(quelle).replace(".md", ""), st["titel"]),
        Spacer(1, 0.8 * cm),
        Paragraph(f"Stand {jetzt.strftime('%d.%m.%Y %H:%M')} UTC", st["fliess"]),
        Paragraph(f"{len(md.splitlines()):,} Zeilen Quelltext, "
                  f"erzeugt mit <font face='Courier'>handbuch_pdf.py</font>"
                  .replace(",", "."), st["fliess"]),
        Spacer(1, 0.6 * cm),
        Paragraph("Diese Datei wird aus der Markdown-Fassung erzeugt. "
                  "Aenderungen bitte dort vornehmen - beim naechsten Lauf "
                  "gehen sie hier sonst verloren.", st["fliess"]),
        PageBreak(),
    ]

    fluss = deckel + umwandeln(md, st, breite)
    doc.build(fluss, onFirstPage=fusszeile, onLaterPages=fusszeile)

    gr = os.path.getsize(ziel) / 1024
    print(f"Geschrieben: {os.path.basename(ziel)} ({gr:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
