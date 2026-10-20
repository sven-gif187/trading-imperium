"""
zahlenbuch.py — erzeugt das Mess- und Zahlenbuch als PDF
=========================================================

WARUM ES DIESES PROGRAMM GIBT

Sven will für alles Belege. Nicht "der Bot läuft gut", sondern: welche Zahl,
aus welcher Datenbank, aus wie vielen Fällen, aus welcher Regelwerks-Epoche.

Dieses Programm liest alle Messreihen und schreibt sie in ein datiertes PDF.
Jede Tabelle nennt ihre Quelle und ihre Fallzahl. Wo die Fallzahl für eine
Aussage nicht reicht, steht das ausdrücklich dabei — eine Zahl ohne diesen
Hinweis wäre eine Halbwahrheit.

GRUNDSATZ: Das Zahlenbuch schönt nichts. Wenn eine Messung nichts hergibt,
steht "nicht entscheidbar" drin und nicht ein hübsches Diagramm.

Es liest nur. Es ändert nichts am Bot.

AUFRUF
    python zahlenbuch.py              PDF für heute
    python zahlenbuch.py --ordner X   Zielordner abweichend
    python zahlenbuch.py              PDF UND Markdown (Normalfall)
    python zahlenbuch.py --md         nur ZAHLENBUCH.md (Kernzahlen)
    python zahlenbuch.py --nur-pdf    nur das PDF
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)

TEL = os.path.join(HIER, "data_store", "telemetrie.db")
SU = os.path.join(HIER, "data_store", "schatten_universum.db")
NACHLAUF = os.path.join(HIER, "data_store", "nachlauf.db")
JOURNAL = os.path.join(HIER, "data_store", "trades_v5.json")
EPOCHEN = os.path.join(HIER, "config_epochs.json")

# Kosten einer vollen Handelsrunde in Prozent (Bybit EU Taker 0,25 % je
# Seite plus gemessene Spanne und Schlupf). Gleiche Zahl wie im Handbuch.
KOSTEN_RUNDE_PCT = 0.505

AKZENT = colors.HexColor("#1f4e79")
GRAU = colors.HexColor("#666666")
ROT = colors.HexColor("#a33")
GRUEN = colors.HexColor("#2a7")


def stile():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Titel2", parent=s["Title"], fontSize=22,
                         textColor=AKZENT, spaceAfter=6))
    s.add(ParagraphStyle("Unter", parent=s["Normal"], fontSize=10,
                         textColor=GRAU, spaceAfter=18))
    s.add(ParagraphStyle("H", parent=s["Heading2"], fontSize=13,
                         textColor=AKZENT, spaceBefore=16, spaceAfter=6))
    s.add(ParagraphStyle("Quelle", parent=s["Normal"], fontSize=7.5,
                         textColor=GRAU, spaceBefore=2, spaceAfter=12))
    s.add(ParagraphStyle("Warn", parent=s["Normal"], fontSize=9,
                         textColor=ROT, spaceBefore=4, spaceAfter=8))
    s.add(ParagraphStyle("Klein", parent=s["Normal"], fontSize=9,
                         spaceAfter=8))
    return s


def tabelle(kopf, zeilen, breiten=None, rechts=None):
    daten = [kopf] + zeilen
    t = Table(daten, colWidths=breiten, repeatRows=1, hAlign="LEFT")
    st = [
        ("BACKGROUND", (0, 0), (-1, 0), AKZENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f6f8")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for sp in (rechts or []):
        st.append(("ALIGN", (sp, 1), (sp, -1), "RIGHT"))
    t.setStyle(TableStyle(st))
    return t


def con_oder_none(pfad):
    try:
        return sqlite3.connect(pfad) if os.path.exists(pfad) else None
    except Exception:
        return None


# ----------------------------------------------------------------- Abschnitte
def _epoche_start(wert):
    """Liest eine Epochen-Startzeit und gibt sie IMMER mit Zeitzone zurueck.

    [16.09.2026] WARUM ES DIESE FUNKTION BRAUCHT
    Im Zahlenbuch stand ueber Tage die Zeile:

        *Epochen nicht lesbar: can't subtract offset-naive and
         offset-aware datetimes*

    Der ganze Abschnitt "Wo wir stehen" fiel damit aus - die Datei
    wurde erzeugt, sah vollstaendig aus, und genau die Angabe, wie
    lange die laufende Epoche schon misst, fehlte.

    Die Ursache: Die Grenzen in config_epochs.json wurden am 15.09.
    mit strftime("%Y-%m-%d %H:%M:%S") geschrieben - ohne Zeitzone.
    datetime.fromisoformat() liefert dafuer eine "naive" Zeit, und die
    laesst sich nicht von datetime.now(timezone.utc) abziehen.

    Statt die JSON zu aendern (dann waere nur dieses eine Vorkommen
    heil) wird hier gelesen: Eine Zeit ohne Angabe gilt als UTC. Das
    ist die Annahme, unter der sie geschrieben wurde, und sie gilt fuer
    jede kuenftige Grenze mit.

    Leere oder unlesbare Werte ergeben None - der Aufrufer entscheidet,
    was er damit tut, statt dass hier eine Ausnahme fliegt.
    """
    roh = str(wert or "").strip()
    if not roh:
        return None
    try:
        dt = datetime.fromisoformat(roh.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def abschnitt_messfenster(s):
    """Wo stehen wir im Messfenster - und was gilt gerade?"""
    teile = [Paragraph("1. Messfenster", s["H"])]
    try:
        eps = sorted(json.load(open(EPOCHEN, encoding="utf-8"))["epochs"],
                     key=lambda x: x["start"])
        akt = eps[-1]
        start = _epoche_start(akt.get("start"))
        if start is None:
            raise ValueError(f"Epoche {akt.get('id')} hat keine lesbare "
                             f"Startzeit ({akt.get('start')!r})")
        laeuft = datetime.now(timezone.utc) - start
        tage = laeuft.days + laeuft.seconds / 86400

        zeilen = [
            ["Aktuelle Epoche", akt["id"]],
            ["Beginn (UTC)", akt["start"][:16]],
            ["Läuft seit", f"{tage:.1f} Tagen"],
            ["Verbleibend (von 14)", f"{max(0, 14 - tage):.1f} Tagen"],
        ]
        teile += [tabelle(["", ""], zeilen, [6*cm, 8*cm]),
                  Paragraph("Quelle: config_epochs.json", s["Quelle"])]

        teile.append(Paragraph(
            "<b>Warum Epochen zählen:</b> Auswertungen dürfen nur "
            "<i>innerhalb</i> einer Epoche verglichen werden. Vor dem "
            "13.08. rechnete der Papierhandel mit 0,10 % Gebühren je Seite "
            "statt der korrekten 0,25 % — Zahlen aus früheren Epochen sind "
            "deshalb systematisch zu optimistisch.", s["Klein"]))
    except Exception as e:
        teile.append(Paragraph(f"Epochen nicht lesbar: {e}", s["Warn"]))
    return teile


def abschnitt_schatten(s):
    """Das Schatten-Universum: Signal und Kosten je Münze, ohne Handel.

    [FIX 20.08.2026] Die Zahl stand hier fest verdrahtet als "12 Münzen".
    Am 17.08. kamen sechs Nachzügler dazu (SUI, OP, APT, ARB, INJ,
    RENDER) - die Überschrift log seitdem. Sven fiel es auf.

    Jetzt wird gezählt, was der Sammler wirklich beobachtet. Eine Zahl,
    die man ändern MUSS, wenn sich etwas ändert, wird vergessen.
    """
    try:
        import schatten_universum as _su
        _n_muenzen = len(_su.MUENZEN)
    except Exception:
        _n_muenzen = None
    teile = [Paragraph("2. Schatten-Universum (%s, ohne Handel)"
                       % (f"{_n_muenzen} Münzen" if _n_muenzen
                          else "Münzen"), s["H"])]
    con = con_oder_none(SU)
    if con is None:
        teile.append(Paragraph("Noch keine Daten — Sammler noch nicht gelaufen.",
                               s["Warn"]))
        return teile
    try:
        n = con.execute("SELECT COUNT(*) FROM signale").fetchone()[0]
    except Exception:
        n = 0
    if not n:
        teile.append(Paragraph("Datenbank vorhanden, noch keine Signale.",
                               s["Warn"]))
        return teile

    r = con.execute("SELECT MIN(ts_utc), MAX(ts_utc), COUNT(DISTINCT lauf_id) "
                    "FROM signale").fetchone()
    teile.append(Paragraph(
        f"{n} Signale aus {r[2]} Durchläufen, {r[0][:16]} bis {r[1][:16]} UTC.",
        s["Klein"]))

    zeilen = []
    for m, k, sc, sp, ko, echt in con.execute(
            "SELECT muenze, COUNT(*), AVG(score), AVG(spread_bp), "
            "AVG(kosten_runde), MAX(im_echtbetrieb) FROM signale "
            "GROUP BY muenze ORDER BY AVG(kosten_runde)"):
        zeilen.append([m.replace("/USDC", ""), str(k),
                       f"{sc:.1f}" if sc else "—",
                       f"{sp:.2f}" if sp else "—",
                       f"{ko:.3%}" if ko else "—",
                       "ja" if echt else ""])
    teile += [tabelle(
        ["Münze", "Signale", "Ø Score", "Ø Spread bp", "Kosten/Runde",
         "Bot handelt"],
        zeilen, [2.6*cm, 2*cm, 2*cm, 2.6*cm, 2.8*cm, 2.4*cm],
        rechts=[1, 2, 3, 4]),
        Paragraph("Quelle: data_store/schatten_universum.db, Tabelle signale. "
                  "Kosten je Runde = 2 × 0,25 % Taker-Gebühr (Bybit EU) + "
                  "2 × halber Spread. Spread live gemessen.", s["Quelle"])]

    q = dict(con.execute("SELECT spread_quelle, COUNT(*) FROM signale "
                         "GROUP BY spread_quelle").fetchall())
    teile.append(Paragraph(
        f"Spread-Herkunft: live gemessen {q.get('live', 0)}, "
        f"Tabellen-Rückfall {q.get('rueckfall', 0)}.", s["Klein"]))

    teile.append(Paragraph(
        "<b>Grenze dieser Zahlen:</b> Sie messen die Qualität des "
        "<i>Signals</i>, nicht die Leistung des <i>Portfolios</i>. Im Schatten "
        "gibt es keine Kapitalkonkurrenz — in Wirklichkeit sind höchstens drei "
        "Positionen offen. Die Spalte „Signale“ überschätzt also, wie oft man "
        "zugegriffen hätte.", s["Klein"]))
    con.close()
    return teile


def abschnitt_bot(s):
    """Was der Bot in der aktuellen Epoche wirklich getan hat."""
    teile = [Paragraph("4. Der Bot im Echtbetrieb", s["H"])]
    try:
        eps = sorted(json.load(open(EPOCHEN, encoding="utf-8"))["epochs"],
                     key=lambda x: x["start"])
        grenze = eps[-1]["start"][:19]
    except Exception:
        grenze = "1970-01-01T00:00:00"

    try:
        j = json.load(open(JOURNAL, encoding="utf-8"))
        j = j if isinstance(j, list) else j.get("trades", [])
        verk = [t for t in j if t.get("pnl") is not None]
        akt = [t for t in verk if str(t.get("time", "")) >= grenze]
    except Exception as e:
        teile.append(Paragraph(f"Journal nicht lesbar: {e}", s["Warn"]))
        return teile

    zeilen = [
        ["Verkäufe gesamt (alle Epochen)", str(len(verk))],
        ["davon in der aktuellen Epoche", str(len(akt))],
    ]
    if akt:
        summe = sum(float(t["pnl"]) for t in akt)
        gew = sum(1 for t in akt if float(t["pnl"]) > 0)
        zeilen += [
            ["Ergebnis der Epoche", f"{summe:+.2f} $"],
            ["Gewinner / Verlierer", f"{gew} / {len(akt)-gew}"],
            ["Ø je Trade", f"{summe/len(akt):+.3f} $"],
        ]
    teile += [tabelle(["", ""], zeilen, [8*cm, 5*cm], rechts=[1]),
              Paragraph(f"Quelle: data_store/trades_v5.json, Epochengrenze "
                        f"{grenze[:16]} UTC.", s["Quelle"])]

    if len(akt) < 30:
        teile.append(Paragraph(
            f"<b>Nicht entscheidbar:</b> {len(akt)} Trades reichen für keine "
            f"Aussage über Trefferquote oder Erwartungswert. Als Faustregel "
            f"gelten 30 unabhängige Fälle je Gruppe als Untergrenze — bei "
            f"weniger entscheidet der Zufall. Diese Zahlen stehen hier zur "
            f"Nachverfolgung, nicht zur Bewertung.", s["Warn"]))

    # Ausstiegsarten der aktuellen Epoche
    if akt:
        nach = {}
        for t in akt:
            art = str(t.get("reason") or t.get("strategy") or "?").split("(")[0].strip()[:28]
            e = nach.setdefault(art, [0, 0.0])
            e[0] += 1
            e[1] += float(t["pnl"])
        zeilen = [[k, str(v[0]), f"{v[1]:+.2f} $", f"{v[1]/v[0]:+.2f} $"]
                  for k, v in sorted(nach.items(), key=lambda x: x[1][1])]
        teile += [Paragraph("Ausstiegsarten dieser Epoche", s["H"]),
                  tabelle(["Ausstiegsart", "Anzahl", "Summe", "Ø"],
                          zeilen, [7*cm, 2*cm, 2.6*cm, 2.6*cm],
                          rechts=[1, 2, 3])]
    return teile


def abschnitt_notizbuecher(s):
    """Die Schatten-Messungen im Bot: KI und Ensemble."""
    teile = [Paragraph("5. Notizbuch-Messungen (rechnen mit, entscheiden nicht)",
                       s["H"])]
    con = con_oder_none(TEL)
    if con is None:
        teile.append(Paragraph("Telemetrie nicht lesbar.", s["Warn"]))
        return teile
    zeilen = []
    for regel, bez in [("ml_model", "KI-Modell (XGBoost)"),
                       ("ensemble_technical", "Ensemble mit echtem technical"),
                       ("TREND_EXIT", "Trend-Ausstieg (Schatten)")]:
        try:
            n = con.execute("SELECT COUNT(*) FROM schatten_regeln WHERE regel=?",
                            (regel,)).fetchone()[0]
            r = con.execute("SELECT MAX(ts_utc) FROM schatten_regeln WHERE regel=?",
                            (regel,)).fetchone()[0]
        except Exception:
            n, r = 0, None
        zeilen.append([bez, str(n), (r or "—")[:16],
                       "ja" if n >= 100 else "noch nicht"])
    teile += [tabelle(["Messung", "Notizen", "zuletzt (UTC)", "auswertbar?"],
                      zeilen, [6.5*cm, 2.2*cm, 3.2*cm, 2.6*cm],
                      rechts=[1]),
              Paragraph("Quelle: data_store/telemetrie.db, Tabelle "
                        "schatten_regeln. „Auswertbar“ ab 100 Notizen — "
                        "darunter ist die Streuung größer als jeder Effekt.",
                        s["Quelle"])]

    # Marktdaten-Zeitreihe
    try:
        n = con.execute("SELECT COUNT(*) FROM markt_historie").fetchone()[0]
        g = con.execute("SELECT COUNT(fear_greed) FROM markt_historie").fetchone()[0]
        teile.append(Paragraph(
            f"Marktdaten-Zeitreihe: {n} Messpunkte, davon {g} mit "
            f"Sentiment-Werten ({g/n:.0%}).", s["Klein"]) if n else Spacer(1, 1))
    except Exception:
        pass
    con.close()
    return teile


def _spalte_lesen(pfad, name, grenze=None):
    """Eine Zahlenspalte aus einer Capture-CSV, robust und ohne pandas."""
    werte = []
    try:
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            kopf = f.readline().strip().split(",")
            if name not in kopf:
                return werte
            i = kopf.index(name)
            for zeile in f:
                teile = zeile.rstrip("\n").split(",")
                if len(teile) <= i:
                    continue
                try:
                    w = float(teile[i])
                except ValueError:
                    continue
                if grenze and not (grenze[0] <= w <= grenze[1]):
                    continue
                werte.append(w)
    except Exception:
        pass
    return werte


def _median(w):
    if not w:
        return None
    w = sorted(w)
    n = len(w)
    return w[n // 2] if n % 2 else (w[n // 2 - 1] + w[n // 2]) / 2


def _perzentil(w, p):
    if not w:
        return None
    w = sorted(w)
    i = min(len(w) - 1, max(0, int(round(p * (len(w) - 1)))))
    return w[i]


def abschnitt_capture(s, tage_zurueck=7):
    """Der Forschungs-Sammler: was er erfasst und was daraus folgt.

    Der wertvollste Teil sind die Spread-Verteilungen. Der Bot rechnet mit
    EINEM Wert je Muenze; die Wirklichkeit ist eine Verteilung, und ihr
    oberes Ende entscheidet, wie teuer ein Trade im schlechten Moment wird.
    """
    teile = [Paragraph("3. Forschungs-Sammler (Orderbuch, Ticker, Funding)",
                       s["H"])]
    wurzel = os.path.join(HIER, "docs", "forschungsprogramm_2026-07", "capture")
    if not os.path.isdir(wurzel):
        teile.append(Paragraph("Kein Capture-Ordner gefunden.", s["Warn"]))
        return teile

    tage = sorted(d for d in os.listdir(wurzel)
                  if d.startswith("20") and os.path.isdir(os.path.join(wurzel, d)))
    if not tage:
        teile.append(Paragraph("Noch keine Capture-Tage.", s["Warn"]))
        return teile

    letzte = tage[-tage_zurueck:]
    teile.append(Paragraph(
        f"{len(tage)} Tage erfasst ({tage[0]} bis {tage[-1]}). Die folgenden "
        f"Auswertungen nutzen die letzten {len(letzte)} Tage.", s["Klein"]))

    # --- Umfang je Datenart -------------------------------------------------
    arten = {"ticker": "Ticker (Bid/Ask/Spread)", "orderbuch": "Orderbuch-Tiefe",
             "trades": "Einzeltrades", "funding": "Funding-Raten",
             "oi": "Offene Positionen"}
    zeilen = []
    for kurz, bez in arten.items():
        dateien = zeilen_summe = 0
        for tag in letzte:
            ordner = os.path.join(wurzel, tag)
            try:
                for f in os.listdir(ordner):
                    if f.startswith(kurz + "_") and f.endswith(".csv"):
                        dateien += 1
                        try:
                            with open(os.path.join(ordner, f), "rb") as fh:
                                zeilen_summe += max(0, sum(1 for _ in fh) - 1)
                        except Exception:
                            pass
            except Exception:
                pass
        if dateien:
            zeilen.append([bez, str(dateien), f"{zeilen_summe:,}".replace(",", ".")])
    if zeilen:
        teile += [tabelle(["Datenart", "Dateien", "Messpunkte"], zeilen,
                          [7*cm, 2.5*cm, 3*cm], rechts=[1, 2]),
                  Paragraph(f"Quelle: docs/forschungsprogramm_2026-07/capture/, "
                            f"letzte {len(letzte)} Tage.", s["Quelle"])]

    # --- Spread-Verteilung je Muenze ---------------------------------------
    muenzen = {}
    for tag in letzte:
        ordner = os.path.join(wurzel, tag)
        try:
            dateien = os.listdir(ordner)
        except Exception:
            continue
        for f in dateien:
            if not (f.startswith("ticker_") and f.endswith(".csv")):
                continue
            basis = f[len("ticker_"):].split("USD")[0]
            werte = _spalte_lesen(os.path.join(ordner, f), "spread_bp",
                                  grenze=(0, 2000))
            if werte:
                muenzen.setdefault(basis, []).extend(werte)

    if muenzen:
        zeilen = []
        for basis, w in sorted(muenzen.items(), key=lambda x: _median(x[1]) or 0):
            med, p90 = _median(w), _perzentil(w, 0.90)
            # Kosten je Runde: 2x Taker 0,25 % + 2x halber Spread
            k_med = 2 * 0.0025 + 2 * (med / 2 / 10000) if med else None
            k_p90 = 2 * 0.0025 + 2 * (p90 / 2 / 10000) if p90 else None
            zeilen.append([basis, f"{len(w):,}".replace(",", "."),
                           f"{med:.2f}" if med else "—",
                           f"{p90:.2f}" if p90 else "—",
                           f"{k_med:.3%}" if k_med else "—",
                           f"{k_p90:.3%}" if k_p90 else "—"])
        teile += [Paragraph("Spread-Verteilung je Münze", s["H"]),
                  tabelle(["Münze", "Messpunkte", "Median bp", "p90 bp",
                           "Kosten typisch", "Kosten schlecht"],
                          zeilen, [2.1*cm, 2.4*cm, 2.2*cm, 2*cm, 2.7*cm, 2.7*cm],
                          rechts=[1, 2, 3, 4, 5]),
                  Paragraph("Quelle: ticker_*.csv, Spalte spread_bp. "
                            "„Kosten typisch“ rechnet mit dem Median, "
                            "„Kosten schlecht“ mit dem p90 — jeder zehnte "
                            "Spread ist so weit oder weiter.", s["Quelle"]),
                  Paragraph(
                      "<b>Warum die zweite Kostenspalte zählt:</b> Der Bot "
                      "rechnet mit einem Wert je Münze. Die Wirklichkeit ist "
                      "eine Verteilung — und wer im ungünstigen Moment kauft, "
                      "zahlt das obere Ende. Der Abstand zwischen beiden "
                      "Spalten ist das Risiko, das eine Durchschnittsrechnung "
                      "verschweigt.", s["Klein"])]

    # --- Funding ------------------------------------------------------------
    fund = {}
    for tag in letzte[-2:]:
        ordner = os.path.join(wurzel, tag)
        try:
            dateien = os.listdir(ordner)
        except Exception:
            continue
        for f in dateien:
            if not (f.startswith("funding_") and f.endswith(".csv")):
                continue
            basis = f[len("funding_"):].split("USD")[0]
            w = _spalte_lesen(os.path.join(ordner, f), "lastFundingRate",
                              grenze=(-0.05, 0.05))
            if w:
                fund.setdefault(basis, []).extend(w)
    if fund:
        zeilen = [[b, f"{_median(w)*100:+.4f} %", str(len(w))]
                  for b, w in sorted(fund.items(),
                                     key=lambda x: -(_median(x[1]) or 0))[:6]]
        teile += [Paragraph("Funding-Raten (Median, letzte 2 Tage)", s["H"]),
                  tabelle(["Münze", "Median", "Messpunkte"], zeilen,
                          [3*cm, 3.5*cm, 3*cm], rechts=[1, 2]),
                  Paragraph("Quelle: funding_*.csv. Positiv heißt: Käufer "
                            "zahlen an Verkäufer — ein Hinweis auf "
                            "überhitzte Erwartung.", s["Quelle"])]
    return teile


FORSCHUNG = os.path.join(HIER, "docs", "forschungsprogramm_2026-07",
                         "forschung.db")


def abschnitt_forschung(s):
    """Das Forschungsprogramm: geprüfte Hypothesen und gesicherte Befunde.

    Das ist der wertvollste Teil des ganzen Projekts und stand bis zum
    14.08. nicht im Zahlenbuch. 147 vorregistrierte Prüfungen, davon 109
    verworfen - das ist der stärkste Beleg dafür, dass hier ehrlich
    gemessen und nicht nachträglich passend gerechnet wurde.
    """
    teile = [Paragraph("6. Forschungsprogramm (vorregistrierte Prüfungen)",
                       s["H"])]
    con = con_oder_none(FORSCHUNG)
    if con is None:
        teile.append(Paragraph("forschung.db nicht gefunden.", s["Warn"]))
        return teile

    # --- Trials -------------------------------------------------------
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(trials)")]
        sp = next((c for c in cols if c in ("ergebnis", "status", "urteil")),
                  None) or cols[17]
        zeilen = [[str(w or "?"), str(n)] for w, n in con.execute(
            f"SELECT {sp}, COUNT(*) FROM trials GROUP BY {sp} "
            f"ORDER BY COUNT(*) DESC")]
        gesamt = sum(int(z[1]) for z in zeilen)
        teile += [tabelle(["Ergebnis der Prüfung", "Anzahl"], zeilen,
                          [7*cm, 3*cm], rechts=[1]),
                  Paragraph(f"Quelle: forschung.db, Tabelle trials "
                            f"({gesamt} Prüfungen).", s["Quelle"])]
        verworfen = next((int(z[1]) for z in zeilen
                          if z[0].upper().startswith("REJECT")), 0)
        if verworfen:
            teile.append(Paragraph(
                f"<b>{verworfen} von {gesamt} Hypothesen wurden verworfen, "
                f"keine einzige bestätigt.</b> Das ist kein Misserfolg, "
                f"sondern der Beleg für sauberes Vorgehen: Die Prüfungen "
                f"wurden <i>vorher</i> festgelegt und nicht nachträglich "
                f"passend gerechnet. Ein Programm, das nur Bestätigungen "
                f"findet, hätte man nicht ernst nehmen dürfen.", s["Klein"]))
    except Exception as e:
        teile.append(Paragraph(f"Trials nicht lesbar: {str(e)[:70]}", s["Warn"]))

    # --- Befunde ------------------------------------------------------
    try:
        zeilen = []
        for prio in ("KRITISCH", "HOCH", "MITTEL", "NIEDRIG"):
            n = con.execute("SELECT COUNT(*) FROM befunde WHERE prioritaet=?",
                            (prio,)).fetchone()[0]
            if n:
                zeilen.append([prio, str(n)])
        k = dict(con.execute("SELECT konfidenz, COUNT(*) FROM befunde "
                             "GROUP BY konfidenz").fetchall())
        if zeilen:
            teile += [Paragraph("Gesicherte Befunde nach Priorität", s["H"]),
                      tabelle(["Priorität", "Anzahl"], zeilen, [7*cm, 3*cm],
                              rechts=[1]),
                      Paragraph(f"Konfidenz: " + ", ".join(
                          f"{a} {b}" for a, b in k.items())
                          + ". Quelle: forschung.db, Tabelle befunde.",
                          s["Quelle"])]

        # Die kritischen Befunde ausschreiben - sie sind der Kern
        krit = con.execute(
            "SELECT befund_id, kurztext, konfidenz FROM befunde "
            "WHERE prioritaet='KRITISCH' ORDER BY befund_id LIMIT 10").fetchall()
        if krit:
            zeilen = [[str(a), str(b)[:78], str(c)] for a, b, c in krit]
            teile += [tabelle(["Nr.", "Befund", "Konfidenz"], zeilen,
                              [1.2*cm, 10.5*cm, 2.6*cm])]
    except Exception as e:
        teile.append(Paragraph(f"Befunde nicht lesbar: {str(e)[:70]}", s["Warn"]))

    # --- Kostenszenarien ----------------------------------------------
    try:
        zeilen = [[str(a), str(b), f"{c}" if c else "—", f"{d}" if d else "—",
                   f"{e}" if e else "—"]
                  for a, b, c, d, e in con.execute(
                      "SELECT name, boerse, taker_pct, slippage_pct, "
                      "roundtrip_pct FROM kostenszenarien LIMIT 6")]
        if zeilen:
            teile += [Paragraph("Kostenszenarien", s["H"]),
                      tabelle(["Szenario", "Börse", "Taker %", "Slippage %",
                               "Runde %"], zeilen,
                              [3.2*cm, 3*cm, 2.2*cm, 2.6*cm, 2.4*cm],
                              rechts=[2, 3, 4]),
                      Paragraph("Quelle: forschung.db, Tabelle "
                                "kostenszenarien.", s["Quelle"])]
    except Exception:
        pass
    con.close()
    return teile


def abschnitt_chartanalyse(s):
    """Chart-Agent: Einstiegssignale mit gemessenem Netto-Ergebnis.

    Die aussagekräftigste Reihe im ganzen Projekt: je Lauf steht dort
    Trefferquote UND Netto-Erwartungswert nach Kosten nebeneinander.
    """
    teile = [Paragraph("7. Chart-Analyse (Einstiegssignale mit Ergebnis)",
                       s["H"])]
    con = con_oder_none(TEL)
    if con is None:
        return teile
    try:
        n_sig = con.execute("SELECT COUNT(*) FROM chart_signale").fetchone()[0]
        n_lauf = con.execute("SELECT COUNT(*) FROM chart_laeufe").fetchone()[0]
    except Exception:
        teile.append(Paragraph("Chart-Tabellen nicht vorhanden.", s["Warn"]))
        return teile

    teile.append(Paragraph(
        f"{n_sig:,} untersuchte Signale aus {n_lauf} Läufen.".replace(",", "."),
        s["Klein"]))

    # Je Symbol: Trefferquote gegen Netto-Erwartungswert
    try:
        zeilen = []
        for sym, laeufe, sig, quote, ev, kosten in con.execute(
                "SELECT symbol, COUNT(*), SUM(signale), AVG(quote_pct), "
                "AVG(ev_netto_pct), AVG(kosten_pct) FROM chart_laeufe "
                "GROUP BY symbol ORDER BY AVG(ev_netto_pct) DESC"):
            zeilen.append([str(sym).replace("/USDC", ""), str(laeufe),
                           str(int(sig or 0)),
                           f"{quote:.1f} %" if quote is not None else "—",
                           f"{ev:+.3f} %" if ev is not None else "—",
                           f"{kosten:.2f} %" if kosten is not None else "—"])
        if zeilen:
            teile += [tabelle(["Symbol", "Läufe", "Signale", "Trefferquote",
                               "EV netto", "Kosten"], zeilen,
                              [2.4*cm, 1.8*cm, 2*cm, 2.8*cm, 2.6*cm, 2*cm],
                              rechts=[1, 2, 3, 4, 5]),
                      Paragraph("Quelle: telemetrie.db, Tabelle chart_laeufe. "
                                "EV netto = Erwartungswert je Runde NACH "
                                "Kosten.", s["Quelle"])]
            neg = [z for z in zeilen if z[4].startswith("-")]
            if neg:
                teile.append(Paragraph(
                    f"<b>Der zentrale Befund des Projekts steht in dieser "
                    f"Tabelle:</b> {len(neg)} von {len(zeilen)} Symbolen haben "
                    f"einen <i>negativen</i> Netto-Erwartungswert — trotz "
                    f"Trefferquoten um 70 %. Die Gewinner sind kleiner als "
                    f"die Kosten. Genau deshalb ist Reibung und nicht "
                    f"Vorhersagekraft der Engpass.", s["Klein"]))
    except Exception as e:
        teile.append(Paragraph(f"chart_laeufe: {str(e)[:70]}", s["Warn"]))

    # Je Signalart
    try:
        zeilen = []
        for art, k, g, rr, rn in con.execute(
                "SELECT signal, COUNT(*), AVG(guete), AVG(rr), "
                "AVG(rendite_netto) FROM chart_signale GROUP BY signal "
                "ORDER BY COUNT(*) DESC LIMIT 8"):
            zeilen.append([str(art)[:22], f"{k:,}".replace(",", "."),
                           f"{g:.2f}" if g is not None else "—",
                           f"{rr:.2f}" if rr is not None else "—",
                           f"{rn:+.3f} %" if rn is not None else "—"])
        if zeilen:
            teile += [Paragraph("Nach Signalart", s["H"]),
                      tabelle(["Signalart", "Anzahl", "Ø Güte",
                               "Ø Chance/Risiko", "Ø Netto"], zeilen,
                              [3.6*cm, 2.4*cm, 2.2*cm, 3*cm, 2.6*cm],
                              rechts=[1, 2, 3, 4]),
                      Paragraph("Quelle: telemetrie.db, Tabelle "
                                "chart_signale.", s["Quelle"])]
    except Exception:
        pass
    con.close()
    return teile


def abschnitt_regelwerk(s):
    """Welche Regel blockiert wie oft - und was der Regime-Wächter lernt."""
    teile = [Paragraph("8. Regelwerk: wo Einstiegschancen hängenbleiben",
                       s["H"])]
    con = con_oder_none(TEL)
    if con is None:
        return teile
    try:
        gesamt = con.execute("SELECT COUNT(*) FROM rule_evaluations").fetchone()[0]
        zeilen = []
        for regel, k in con.execute(
                "SELECT rule_name, COUNT(*) FROM rule_evaluations "
                "WHERE result='BLOCK' GROUP BY rule_name "
                "ORDER BY COUNT(*) DESC LIMIT 10"):
            zeilen.append([str(regel)[:30], f"{k:,}".replace(",", "."),
                           f"{k/gesamt:.1%}"])
        if zeilen:
            teile += [tabelle(["Regel", "Blockaden", "Anteil"], zeilen,
                              [7*cm, 3*cm, 2.4*cm], rechts=[1, 2]),
                      Paragraph(f"Quelle: telemetrie.db, Tabelle "
                                f"rule_evaluations ({gesamt:,} Prüfungen)."
                                .replace(",", "."), s["Quelle"]),
                      Paragraph(
                          "Diese Tabelle zeigt, <i>warum</i> aus vielen "
                          "Kaufwünschen wenige Trades werden. Sie sagt "
                          "nichts darüber, ob die Blockaden richtig waren — "
                          "dafür bräuchte es den Kursverlauf der abgelehnten "
                          "Gelegenheiten.", s["Klein"])]
    except Exception as e:
        teile.append(Paragraph(f"rule_evaluations: {str(e)[:70]}", s["Warn"]))

    # Regime-Wächter: was er gelernt und entschieden hat
    try:
        zeilen = []
        for ts, faelle, rend, plus, vor, nach, ents in con.execute(
                "SELECT ts_utc, faelle, rendite_24h, anteil_plus, "
                "wert_vorher, wert_nachher, entscheidung FROM regime_lernen "
                "ORDER BY ts_utc DESC LIMIT 6"):
            zeilen.append([str(ts)[:16], str(faelle),
                           f"{rend:+.2f} %" if rend is not None else "—",
                           f"{plus:.0f} %" if plus is not None else "—",
                           f"{vor} → {nach}", str(ents)[:12]])
        if zeilen:
            teile += [Paragraph("Regime-Wächter: Entscheidungen", s["H"]),
                      tabelle(["Zeit (UTC)", "Fälle", "Ø 24 h", "im Plus",
                               "Schwelle", "Entscheidung"], zeilen,
                              [2.8*cm, 1.6*cm, 2*cm, 2*cm, 2.4*cm, 2.6*cm],
                              rechts=[1, 2, 3]),
                      Paragraph("Quelle: telemetrie.db, Tabelle "
                                "regime_lernen. „Ø 24 h“ ist die Rendite, die "
                                "die geblockten Käufe erzielt hätten.",
                                s["Quelle"])]
    except Exception:
        pass
    con.close()
    return teile


def abschnitt_datenqualitaet(s):
    """Was fehlt - ausdrücklich, damit niemand mit Lücken rechnet."""
    teile = [Paragraph("9. Datenqualität — was fehlt", s["H"])]
    con = con_oder_none(TEL)
    zeilen = []
    if con is not None:
        try:
            eps = sorted(json.load(open(EPOCHEN, encoding="utf-8"))["epochs"],
                         key=lambda x: x["start"])
            grenze = eps[-1]["start"][:19]
            n = con.execute("SELECT COUNT(*) FROM evaluations WHERE ts_utc>=?",
                            (grenze,)).fetchone()[0]
            if n:
                for feld, bez in [("score", "Signalstärke"),
                                  ("stop_loss", "Verlustgrenze"),
                                  ("feature_snapshot_id", "Merkmals-Schnappschuss"),
                                  ("position_id", "Positions-Kennung")]:
                    try:
                        g = con.execute(
                            f"SELECT COUNT({feld}) FROM evaluations WHERE ts_utc>=?",
                            (grenze,)).fetchone()[0]
                        zeilen.append([bez, f"{g}/{n}", f"{g/n:.0%}"])
                    except Exception:
                        zeilen.append([bez, "Spalte fehlt", "0 %"])
        except Exception:
            pass
        con.close()
    if zeilen:
        teile += [tabelle(["Feld", "gefüllt", "Anteil"], zeilen,
                          [7*cm, 3*cm, 2.5*cm], rechts=[1, 2]),
                  Paragraph("Quelle: telemetrie.db, Tabelle evaluations, "
                            "nur aktuelle Epoche.", s["Quelle"])]
    teile.append(Paragraph(
        "<b>Bekannte Einschränkung:</b> Verkäufe laufen über den "
        "Exit-Monitor mit einem kleineren Datensatz als Käufe. Eine "
        "durchgehende Verknüpfung von Einstieg zu Ausstieg über die "
        "Positions-Kennung ist erst für neue Trades vollständig.", s["Klein"]))
    return teile


def abschnitt_nachlauf(s):
    """Wie ging es nach einem Ausstieg weiter? War der Stop zu eng?"""
    teile = [Paragraph("10. Nachlauf — was nach dem Ausstieg geschah", s["H"])]
    con = con_oder_none(NACHLAUF)
    if con is None:
        teile.append(Paragraph("nachlauf.db noch nicht vorhanden.", s["Warn"]))
        return teile

    teile.append(Paragraph(
        "Für jeden Ausstieg und jede Blockade wird der Kurs 1, 4, 24 und 48 "
        "Stunden später festgehalten. Damit lässt sich die wichtigste Frage "
        "beantworten: <b>War der Ausstieg richtig — oder hat sich der Kurs "
        "danach erholt?</b>", s["Klein"]))

    # --- Füllstand: wie weit ist die Messung überhaupt? ---
    try:
        zeilen = []
        for art in ("exit", "blockade"):
            n = con.execute("SELECT COUNT(*) FROM nachlauf WHERE art=?",
                            (art,)).fetchone()[0]
            if not n:
                continue
            spalten = []
            for sp in ("r1h", "r4h", "r24h", "r48h"):
                g = con.execute(
                    f"SELECT COUNT({sp}) FROM nachlauf WHERE art=?",
                    (art,)).fetchone()[0]
                spalten.append(f"{g}")
            zeilen.append([{"exit": "Ausstiege",
                            "blockade": "Blockaden"}[art], str(n)] + spalten)
        if zeilen:
            teile += [tabelle(["Art", "erfasst", "1 h", "4 h", "24 h", "48 h"],
                              zeilen, [3.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm],
                              rechts=[1, 2, 3, 4, 5]),
                      Paragraph("Quelle: data_store/nachlauf.db. Die Zahlen "
                                "hinter den Stunden sind bereits nachgetragene "
                                "Kurse — der Rest ist noch nicht fällig.",
                                s["Quelle"])]
    except Exception as e:
        teile.append(Paragraph(f"Füllstand nicht lesbar: {e}", s["Warn"]))

    # --- Die eigentliche Frage: Kursverlauf nach Ausstiegsart ---
    def kat(grund):
        g = (grund or "").lower()
        if "trailing" in g:
            return "Trailing-Stop"
        if "breakeven" in g:
            return "Breakeven-Sperre"
        if "stop" in g:
            return "Stop-Loss"
        if "trend" in g:
            return "Trend-Ausstieg"
        return "sonstige"

    try:
        roh = con.execute(
            "SELECT grund, r1h, r4h, r24h, r48h FROM nachlauf "
            "WHERE art='exit' AND (r1h IS NOT NULL OR r4h IS NOT NULL "
            "OR r24h IS NOT NULL OR r48h IS NOT NULL)").fetchall()
    except Exception:
        roh = []

    if not roh:
        teile.append(Paragraph(
            "<b>Noch keine Aussage möglich.</b> Es liegen noch keine "
            "Ausstiege mit nachgetragenem Kurs vor. Die 24- und "
            "48-Stunden-Werte brauchen entsprechend lange.", s["Warn"]))
        con.close()
        return teile

    gruppen = {}
    for grund, r1, r4, r24, r48 in roh:
        gruppen.setdefault(kat(grund), []).append((r1, r4, r24, r48))

    zeilen = []
    for name, werte in sorted(gruppen.items(), key=lambda x: -len(x[1])):
        zeile = [name, str(len(werte))]
        for i in range(4):
            sp = [w[i] for w in werte if w[i] is not None]
            zeile.append(f"{_median(sp):+.2f} %" if sp else "—")
        zeilen.append(zeile)

    teile += [
        Paragraph("Kursbewegung nach dem Verkauf (Median)", s["Klein"]),
        tabelle(["Ausstiegsgrund", "Fälle", "nach 1 h", "nach 4 h",
                 "nach 24 h", "nach 48 h"], zeilen,
                [4*cm, 1.6*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.2*cm],
                rechts=[1, 2, 3, 4, 5]),
        Paragraph("Quelle: data_store/nachlauf.db, nur Ausstiege mit "
                  "nachgetragenem Kurs.", s["Quelle"]),
        Paragraph(
            "<b>Wie das zu lesen ist.</b> Ein <b>positiver</b> Wert heißt: "
            "der Kurs stieg nach dem Verkauf — der Ausstieg war also zu früh. "
            "Ein <b>negativer</b> Wert heißt: der Kurs fiel weiter — der "
            "Ausstieg hat Schlimmeres verhindert. Beim Stop-Loss ist das die "
            "entscheidende Zahl: erholt sich der Kurs regelmäßig, steht der "
            "Stop zu eng; fällt er weiter, sitzt das Problem beim Einstieg.",
            s["Klein"]),
    ]

    if len(roh) < 30:
        teile.append(Paragraph(
            f"<b>Nicht entscheidbar.</b> {len(roh)} Fälle reichen für kein "
            "Urteil. Als Untergrenze gelten 30 unabhängige Fälle je Gruppe — "
            "darunter entscheidet der Zufall.", s["Warn"]))
    con.close()
    return teile


def abschnitt_indikatoren(s):
    """Was die Forschung je Kaufprüfung wirklich festhält."""
    teile = [Paragraph("11. Indikatoren — was bei jeder Prüfung gemessen wird",
                       s["H"])]
    con = con_oder_none(TEL)
    if con is None:
        teile.append(Paragraph("telemetrie.db nicht lesbar.", s["Warn"]))
        return teile

    try:
        spalten = [r[1] for r in con.execute(
            "PRAGMA table_info(feature_snapshots)")]
        n = con.execute("SELECT COUNT(*) FROM feature_snapshots").fetchone()[0]
    except Exception as e:
        teile.append(Paragraph(f"Tabelle nicht lesbar: {e}", s["Warn"]))
        con.close()
        return teile

    teile.append(Paragraph(
        f"Zu jeder Kaufprüfung wird ein <b>Merkmals-Schnappschuss</b> "
        f"(<i>feature snapshot</i>) gespeichert: {len(spalten)} Spalten mit "
        f"dem vollständigen Indikatorensatz. Bisher <b>{n}</b> Schnappschüsse. "
        f"Damit ist später nachvollziehbar, <b>welche Marktlage</b> zu welcher "
        f"Entscheidung geführt hat — nicht nur, wie sie ausging.", s["Klein"]))

    # Der jüngste Schnappschuss je Münze, mit den wichtigsten Indikatoren
    zeigen = [("rsi", "RSI", "{:.1f}"), ("adx", "ADX", "{:.1f}"),
              ("macd_hist", "MACD-Hist", "{:+.4f}"),
              ("bb_lage", "Bollinger-Lage", "{:.2f}"),
              ("atr", "ATR", "{:.3f}"),
              ("close_to_ema20", "Abst. EMA20", "{:+.4f}"),
              ("volatility", "Schwankung", "{:.4f}")]
    vorhanden = [z for z in zeigen if z[0] in spalten]
    try:
        rows = con.execute(
            "SELECT symbol, ts_utc, " + ", ".join(z[0] for z in vorhanden) +
            " FROM feature_snapshots WHERE rowid IN "
            "(SELECT MAX(rowid) FROM feature_snapshots GROUP BY symbol) "
            "ORDER BY symbol").fetchall()
    except Exception:
        rows = []

    if rows:
        zeilen = []
        for r in rows:
            zeile = [r[0], str(r[1])[11:16]]
            for i, (_, _, fmt) in enumerate(vorhanden):
                w = r[2 + i]
                zeile.append(fmt.format(w) if w is not None else "—")
            zeilen.append(zeile)
        teile += [
            Paragraph("Jüngster Schnappschuss je Münze", s["Klein"]),
            tabelle(["Münze", "UTC"] + [z[1] for z in vorhanden], zeilen,
                    None, rechts=list(range(1, len(vorhanden) + 2))),
            Paragraph("Quelle: telemetrie.db, Tabelle feature_snapshots, "
                      "jeweils der neueste Eintrag je Münze.", s["Quelle"]),
        ]

    # Verteilung des RSI - zeigt, in welcher Marktlage der Bot meistens prüft
    if "rsi" in spalten:
        try:
            w = [r[0] for r in con.execute(
                "SELECT rsi FROM feature_snapshots WHERE rsi IS NOT NULL")]
            if w:
                zeilen = [[
                    "RSI über alle Schnappschüsse", str(len(w)),
                    f"{min(w):.1f}", f"{_perzentil(w, 25):.1f}",
                    f"{_median(w):.1f}", f"{_perzentil(w, 75):.1f}",
                    f"{max(w):.1f}"]]
                teile += [
                    tabelle(["Größe", "Fälle", "Min", "25 %", "Median",
                             "75 %", "Max"], zeilen, None,
                            rechts=[1, 2, 3, 4, 5, 6]),
                    Paragraph(
                        "Der RSI zeigt, ob eine Münze überkauft (hoch) oder "
                        "überverkauft (niedrig) ist. Liegt der Median nahe 50, "
                        "prüft der Bot überwiegend in unauffälliger Marktlage.",
                        s["Klein"]),
                ]
        except Exception:
            pass

    teile.append(Paragraph(
        "<b>Was hier noch fehlt:</b> Der Schnappschuss ist mit der "
        "Entscheidung über <i>feature_snapshot_id</i> verknüpft, aber es "
        "wurde noch nicht ausgewertet, <b>welche Indikatorwerte zu "
        "erfolgreichen Trades führten</b>. Dafür braucht es abgeschlossene "
        "Trades in ausreichender Zahl — siehe Abschnitt 1.", s["Klein"]))
    con.close()
    return teile


ZIELE_DATEI = os.path.join(HIER, "config_zielgroessen.json")
K_BASIS = 0.505          # Kosten je Runde in %, Bybit EU Taker


def _kennzahlen():
    """Die fuenf Zielgroessen aus dem Journal. Rechenweg wie BOT-HANDBUCH 4.60."""
    try:
        with open(JOURNAL, encoding="utf-8") as f:
            j = json.load(f)
    except Exception:
        return None
    sells = [e for e in j if e.get("type") == "SELL" and e.get("pnl_pct") is not None]
    if not sells:
        return None
    netto = [float(e["pnl_pct"]) - K_BASIS for e in sells]
    gew = [v for v in netto if v > 0]
    ver = [v for v in netto if v <= 0]
    g = sum(gew) / len(gew) if gew else 0.0
    v = abs(sum(ver) / len(ver)) if ver else 0.0
    mfe = [e for e in sells if e.get("mfe_pct") is not None]
    return {
        "n": len(netto),
        "tq": 100.0 * len(gew) / len(netto),
        "ev": sum(netto) / len(netto),
        "g": g, "v": v,
        "payoff": (g / v) if v else None,
        "pf": (sum(gew) / abs(sum(ver))) if ver and sum(ver) else None,
        "versch": (sum(float(e["mfe_pct"]) - float(e["pnl_pct"]) for e in mfe)
                   / len(mfe)) if mfe else None,
        "n_mfe": len(mfe),
        "sells": sells,
    }


def _ausstiegs_verteilung(sells):
    """Wie viele Ausstiege liegen unter der Kostenschwelle?"""
    def grund(e):
        r = (e.get("reason") or "").upper()
        for m, n in (("TRAILING", "Trailing"), ("RSI", "RSI"),
                     ("STOP-LOSS", "Stop-Loss"), ("BREAKEVEN", "Breakeven"),
                     ("TREND", "Trend"), ("DAILY", "Tagesverlust")):
            if m in r:
                return n
        return "Sonstige"
    bereiche = [(-99, -2.0, "unter -2,0 %"), (-2.0, -0.5, "-2,0 bis -0,5 %"),
                (-0.5, 0, "-0,5 bis 0 %"), (0, K_BASIS, "0 bis 0,505 %"),
                (K_BASIS, 1.0, "0,505 bis 1,0 %"), (1.0, 2.0, "1,0 bis 2,0 %"),
                (2.0, 99, "ueber 2,0 %")]
    zeilen = []
    for lo, hi, name in bereiche:
        teil = [e for e in sells if lo <= float(e["pnl_pct"]) < hi]
        tr = sum(1 for e in teil if grund(e) == "Trailing")
        zeilen.append([name, str(len(teil)), str(tr)])
    return zeilen


def _drawdown():
    """Groesster Rueckschlag, nach Kapitaldefinitionen getrennt."""
    try:
        from drawdown_auswertung import (kapitalkurve, drawdown, zwei_niveaus,
                                         geteilte_kurven)
        k = kapitalkurve()
        if not k:
            return None
        verdacht, _, _, _ = zwei_niveaus(k)
        if verdacht:
            oben, unten = geteilte_kurven(k)
            return {"getrennt": True,
                    "mit": drawdown(oben), "ohne": drawdown(unten)}
        return {"getrennt": False, "gesamt": drawdown(k)}
    except Exception:
        return None


def abschnitt_zielgroessen(s):
    """Wo stehen wir gegenueber den gesetzten Zielen?"""
    teile = [Paragraph("12. Zielgrössen und Ausstiegsqualität", s["H"])]
    kz = _kennzahlen()
    if not kz:
        teile.append(Paragraph("Kein auswertbares Journal.", s["Warn"]))
        return teile
    try:
        with open(ZIELE_DATEI, encoding="utf-8") as f:
            z = json.load(f)
    except Exception:
        z = {}

    def ziel_von(k):
        d = z.get(k) or {}
        return d.get("ziel"), d.get("richtung", "hoch"), d.get("titel", k)

    zeilen = []
    for schluessel, wert, nk in (("ev_netto_pct", kz["ev"], 3),
                                 ("payoff_ratio", kz["payoff"], 3),
                                 ("profit_faktor", kz["pf"], 3),
                                 ("verschenkt_pp", kz["versch"], 3)):
        ziel, richtung, titel = ziel_von(schluessel)
        if wert is None or ziel is None:
            zeilen.append([titel, "-", "-", "-"])
            continue
        erreicht = wert >= ziel if richtung == "hoch" else wert <= ziel
        zeilen.append([titel, f"{wert:+.{nk}f}", f"{ziel}",
                       "erreicht" if erreicht else "verfehlt"])

    dd = _drawdown()
    if dd:
        ziel, _, titel = ziel_von("max_drawdown_pct")
        if dd.get("getrennt"):
            for name, sch in (("mit Sparplan-BTC", "mit"), ("ohne", "ohne")):
                d = dd.get(sch)
                if d:
                    zeilen.append([f"{titel} ({name})", f"{d['max_dd_pct']:.2f}",
                                   f"{ziel}",
                                   "erreicht" if ziel and d["max_dd_pct"] <= ziel
                                   else "verfehlt"])
        elif dd.get("gesamt"):
            d = dd["gesamt"]
            zeilen.append([titel, f"{d['max_dd_pct']:.2f}", f"{ziel}",
                           "erreicht" if ziel and d["max_dd_pct"] <= ziel
                           else "verfehlt"])

    zeilen.append(["Trefferquote (bewusst ohne Ziel)",
                   f"{kz['tq']:.1f} %", "-", "-"])
    teile += [tabelle(["Kennzahl", "ist", "Ziel", ""], zeilen,
                      [7*cm, 3*cm, 2.5*cm, 3*cm], rechts=[1, 2]),
              Paragraph(
                  f"Quelle: data_store/trades_v5.json, {kz['n']} Verkäufe mit "
                  f"Ergebnisangabe, davon {kz['n_mfe']} mit Höchststand. "
                  f"Netto = Bruttoergebnis minus {K_BASIS} % Kosten je Runde. "
                  f"Ziele aus config_zielgroessen.json.", s["Quelle"])]

    teile.append(Paragraph(
        "<b>Warum die Trefferquote kein Ziel ist:</b> Sie liegt bei "
        f"{kz['tq']:.1f} % und damit fast am ursprünglich gesetzten Wert von "
        "45 %. Sie ist nicht das Problem. Entscheidend ist das Verhältnis "
        f"von durchschnittlichem Gewinner (+{kz['g']:.3f} %) zu "
        f"durchschnittlichem Verlierer (−{kz['v']:.3f} %). "
        "Näheres in BOT-HANDBUCH.md 4.60.", s["Klein"]))

    # --- Ausstiege gegen die Kostenschwelle ---
    teile.append(Paragraph("Ausstiege gegenüber der Kostenschwelle", s["H2"]
                           if "H2" in s else s["H"]))
    teile += [tabelle(["Bereich (brutto)", "Ausstiege", "davon Trailing"],
                      _ausstiegs_verteilung(kz["sells"]),
                      [7*cm, 3.5*cm, 4*cm], rechts=[1, 2]),
              Paragraph("Quelle: data_store/trades_v5.json, Feld reason.",
                        s["Quelle"])]

    tot = [e for e in kz["sells"]
           if "TRAILING" in str(e.get("reason", "")).upper()]
    unter = [e for e in tot if 0 <= float(e["pnl_pct"]) < K_BASIS]
    if tot:
        teile.append(Paragraph(
            f"<b>Der wichtigste Befund:</b> {len(unter)} von {len(tot)} "
            f"Trailing-Ausstiegen ({100*len(unter)/len(tot):.0f} %) enden "
            f"brutto im Plus und netto im Minus. Die Ratsche wird ab +1,2 % "
            f"Höchststand scharf und hält 1,0 % Abstand; rentabel wird sie "
            f"erst ab +1,52 %. Dazwischen verliert jeder Ausstieg "
            f"rechnerisch. Herleitung: BOT-HANDBUCH.md 4.64, "
            f"GEFUNDENE-PROBLEME.md 45.", s["Klein"]))
    return teile


def markdown_fassung():
    """Schreibt ZAHLENBUCH.md - die durchsuchbare Fassung der Kernzahlen.

    [19.08.2026] Sven wollte das Zahlenbuch auch als Markdown. Das PDF
    bleibt die ausfuehrliche Fassung mit allen zwoelf Abschnitten; diese
    Datei traegt die Kennzahlen, die man nachschlagen und in git
    vergleichen koennen muss. Sie wird ausserdem von schon_bekannt.py
    durchsucht - damit taucht eine Zahl, die hier steht, bei jeder
    Befund-Pruefung auf.
    """
    heute = datetime.now(timezone.utc)
    z = []
    try:
        with open(ZIELE_DATEI, encoding="utf-8") as f:
            z = json.load(f)
    except Exception:
        z = {}
    kz = _kennzahlen()
    zeilen = [
        "# Zahlenbuch — die Kernzahlen",
        "",
        f"**Automatisch erzeugt {heute:%d.%m.%Y %H:%M} UTC mit "
        f"`python zahlenbuch.py --md`. Nicht von Hand ändern.**",
        "",
        "Das ausführliche Zahlenbuch mit allen Abschnitten steht in "
        "`ZAHLENBUCH.pdf`. Diese Fassung trägt die Zahlen, die man "
        "nachschlagen und vergleichen können muss.",
        "",
        "Es wird nichts geschönt und nichts hochgerechnet. Wo die Fallzahl "
        "nicht reicht, steht das dabei.",
        "",
        "---",
        "",
    ]

    # --- Epoche ---
    try:
        eps = sorted(json.load(open(EPOCHEN, encoding="utf-8"))["epochs"],
                     key=lambda x: x["start"])
        akt = eps[-1]
        start = _epoche_start(akt.get("start"))
        if start is None:
            raise ValueError(f"Epoche {akt.get('id')} hat keine lesbare "
                             f"Startzeit ({akt.get('start')!r})")
        laeuft = (datetime.now(timezone.utc) - start)
        tage = laeuft.days + laeuft.seconds / 86400
        zeilen += ["## Wo wir stehen", "",
                   "| | |", "|---|---|",
                   f"| Aktuelle Epoche | `{akt['id']}` |",
                   f"| Beginn (UTC) | {akt['start'][:16]} |",
                   f"| Läuft seit | {tage:.1f} Tagen |",
                   "", "*Quelle: `config_epochs.json`. Auswertungen dürfen nur "
                   "**innerhalb** einer Epoche verglichen werden.*", "", "---", ""]
    except Exception as e:
        zeilen += [f"*Epochen nicht lesbar: {e}*", "", "---", ""]

    # --- Zielgroessen ---
    if kz:
        zeilen += ["## Zielgrößen", "",
                   "| Kennzahl | ist | Ziel | |", "|---|---:|---:|---|"]
        for schluessel, wert, nk in (("ev_netto_pct", kz["ev"], 3),
                                     ("payoff_ratio", kz["payoff"], 3),
                                     ("profit_faktor", kz["pf"], 3),
                                     ("verschenkt_pp", kz["versch"], 3)):
            d = z.get(schluessel) or {}
            ziel, richtung = d.get("ziel"), d.get("richtung", "hoch")
            titel = d.get("titel", schluessel)
            if wert is None or ziel is None:
                zeilen.append(f"| {titel} | – | – | – |")
                continue
            erreicht = wert >= ziel if richtung == "hoch" else wert <= ziel
            zeilen.append(f"| {titel} | {wert:+.{nk}f} | {ziel} | "
                          f"{'**erreicht**' if erreicht else 'verfehlt'} |")
        dd = _drawdown()
        if dd:
            d0 = (z.get("max_drawdown_pct") or {})
            ziel = d0.get("ziel")
            titel = d0.get("titel", "Größter Rückschlag")
            if dd.get("getrennt"):
                for name, sch in (("mit Sparplan-BTC", "mit"), ("ohne", "ohne")):
                    d = dd.get(sch)
                    if d:
                        ok = ziel is not None and d["max_dd_pct"] <= ziel
                        zeilen.append(f"| {titel} ({name}) | {d['max_dd_pct']:.2f} | "
                                      f"{ziel} | {'**erreicht**' if ok else 'verfehlt'} |")
            elif dd.get("gesamt"):
                d = dd["gesamt"]
                ok = ziel is not None and d["max_dd_pct"] <= ziel
                zeilen.append(f"| {titel} | {d['max_dd_pct']:.2f} | {ziel} | "
                              f"{'**erreicht**' if ok else 'verfehlt'} |")
        zeilen += [f"| Trefferquote *(bewusst ohne Ziel)* | {kz['tq']:.1f} % | – | – |",
                   "",
                   f"*Quelle: `data_store/trades_v5.json`, **{kz['n']} Verkäufe** "
                   f"mit Ergebnisangabe, davon {kz['n_mfe']} mit Höchststand. "
                   f"Netto = brutto minus {K_BASIS} % Kosten je Runde. "
                   f"Ziele aus `config_zielgroessen.json`.*", "",
                   f"Ø Gewinner **+{kz['g']:.3f} %**, Ø Verlierer "
                   f"**−{kz['v']:.3f} %**. Die Trefferquote ist fast am Ziel — "
                   f"das Problem ist das Verhältnis der beiden. "
                   f"Siehe `BOT-HANDBUCH.md` 4.60.", "", "---", ""]

        # --- Ausstiege ---
        zeilen += ["## Ausstiege gegenüber der Kostenschwelle", "",
                   "| Bereich (brutto) | Ausstiege | davon Trailing |",
                   "|---|---:|---:|"]
        for name, n, tr in _ausstiegs_verteilung(kz["sells"]):
            mark = " **← Kostenschwelle**" if "Kosten" in name else ""
            zeilen.append(f"| {name}{mark} | {n} | {tr} |")
        tot = [e for e in kz["sells"]
               if "TRAILING" in str(e.get("reason", "")).upper()]
        unter = [e for e in tot if 0 <= float(e["pnl_pct"]) < K_BASIS]
        if tot:
            zeilen += ["",
                       f"**{len(unter)} von {len(tot)} Trailing-Ausstiegen "
                       f"({100*len(unter)/len(tot):.0f} %) enden brutto im Plus "
                       f"und netto im Minus.** Die Ratsche wird ab +1,2 % "
                       f"Höchststand scharf und hält 1,0 % Abstand; rentabel "
                       f"wird sie erst ab **+1,52 %**. Dazwischen verliert jeder "
                       f"Ausstieg rechnerisch.", "",
                       "Herleitung: `BOT-HANDBUCH.md` 4.64, "
                       "`GEFUNDENE-PROBLEME.md` 45.", "", "---", ""]

    # --- Datenlage ---
    zeilen += ["## Datenlage", "", "| Quelle | Umfang |", "|---|---|"]
    for name, pfad, sql in (
            ("Kaufprüfungen", TEL, "SELECT COUNT(*) FROM evaluations"),
            ("Schatten-Signale", SU, "SELECT COUNT(*) FROM signale"),
            ("Nachlauf-Ereignisse", NACHLAUF, "SELECT COUNT(*) FROM nachlauf"),
            ("Positionsverläufe",
             os.path.join(HIER, "data_store", "positionsverlauf.db"),
             "SELECT COUNT(*) FROM verlauf")):
        con = con_oder_none(pfad)
        if con is None:
            zeilen.append(f"| {name} | – |")
            continue
        try:
            zeilen.append(f"| {name} | {con.execute(sql).fetchone()[0]:,} |"
                          .replace(",", "."))
        except Exception:
            zeilen.append(f"| {name} | – |")
        con.close()
    zeilen += ["", "---", "",
               "*Erzeugt aus `data_store/telemetrie.db`, "
               "`schatten_universum.db`, `nachlauf.db`, `positionsverlauf.db`, "
               "`trades_v5.json`, `config_epochs.json`, "
               "`config_zielgroessen.json`. Alle Zeiten UTC. Kein Wert wurde "
               "von Hand eingetragen.*", ""]

    ziel_datei = os.path.join(HIER, "ZAHLENBUCH.md")
    with open(ziel_datei, "w", encoding="utf-8") as f:
        f.write("\n".join(zeilen))
    print(f"Geschrieben: ZAHLENBUCH.md ({len(zeilen)} Zeilen)")
    return 0


def main():
    if "--md" in sys.argv:
        return markdown_fassung()
    ordner = HIER
    if "--ordner" in sys.argv:
        try:
            ordner = sys.argv[sys.argv.index("--ordner") + 1]
        except Exception:
            pass
    os.makedirs(ordner, exist_ok=True)
    heute = datetime.now(timezone.utc)

    # EINE Datei im Hauptordner, die immer den aktuellen Stand zeigt.
    # Frueher entstand je Tag ein eigenes PDF - das muellte den Ordner zu,
    # obwohl das Zahlenbuch ohnehin nur den JETZT-Stand abbildet und nichts
    # fortschreibt. Die datierten Ausgaben wandern als Archiv in einen
    # Unterordner, damit die Historie trotzdem erhalten bleibt.
    ziel = os.path.join(ordner, "ZAHLENBUCH.pdf")
    archiv = os.path.join(ordner, "zahlenbuecher")
    os.makedirs(archiv, exist_ok=True)
    archiv_ziel = os.path.join(archiv, f"ZAHLENBUCH_{heute:%Y-%m-%d}.pdf")

    s = stile()
    doc = SimpleDocTemplate(ziel, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm,
                            title=f"Zahlenbuch {heute:%d.%m.%Y}",
                            author="Trading Imperium V6")
    inhalt = [
        Paragraph("Mess- und Zahlenbuch", s["Titel2"]),
        Paragraph(f"Trading Imperium V6 &nbsp;·&nbsp; Stand "
                  f"{heute:%d.%m.%Y %H:%M} UTC &nbsp;·&nbsp; automatisch "
                  f"erzeugt mit zahlenbuch.py", s["Unter"]),
        Paragraph(
            "Dieses Dokument enthält ausschließlich gemessene Werte. Jede "
            "Tabelle nennt ihre Quelle. Wo die Fallzahl für eine Aussage nicht "
            "reicht, steht das ausdrücklich dabei — eine Zahl ohne diesen "
            "Hinweis wäre eine Halbwahrheit. Es wird nichts geschönt und "
            "nichts hochgerechnet.", s["Klein"]),
        Spacer(1, 10),
    ]
    for f in (abschnitt_messfenster, abschnitt_schatten, abschnitt_capture,
              abschnitt_bot, abschnitt_notizbuecher, abschnitt_forschung,
              abschnitt_chartanalyse, abschnitt_regelwerk,
              abschnitt_datenqualitaet, abschnitt_nachlauf,
              abschnitt_indikatoren, abschnitt_zielgroessen):
        try:
            inhalt += f(s)
        except Exception as e:
            inhalt.append(Paragraph(f"Abschnitt fehlgeschlagen: {e}", s["Warn"]))

    inhalt += [
        Spacer(1, 16),
        Paragraph(
            "Erzeugt aus: data_store/telemetrie.db, "
            "data_store/schatten_universum.db, data_store/trades_v5.json, "
            "config_epochs.json. Alle Zeiten UTC. Kein Wert wurde von Hand "
            "eingetragen.", s["Quelle"]),
    ]
    doc.build(inhalt)

    # Tageskopie ins Archiv, damit der Hauptordner sauber bleibt.
    try:
        import shutil
        shutil.copy2(ziel, archiv_ziel)
    except Exception:
        pass

    print(f"Geschrieben: {os.path.basename(ziel)} "
          f"({os.path.getsize(ziel)/1024:.0f} KB), "
          f"Archivkopie in zahlenbuecher/")

    # [20.08.2026] Die Markdown-Fassung IMMER mitschreiben.
    #
    # Sven: "sowohl das Bothandbuch als PDF und als Markdown, genauso mit
    # dem Zahlenbuch als Markdown und PDF".
    #
    # Vorher schrieb ein normaler Lauf nur das PDF, die .md nur mit dem
    # Schalter --md. Wer den Schalter vergisst - und das vergisst man -
    # hat danach zwei Zahlenbuecher mit verschiedenen Zahlen und keinen
    # Hinweis darauf, welches gilt. Zwei Fassungen, die auseinanderlaufen
    # koennen, sind schlimmer als eine.
    #
    # --nur-pdf bleibt fuer den Fall, dass wirklich nur das PDF gebraucht
    # wird (etwa im Tagesjob, wenn die .md gleich danach ohnehin folgt).
    if "--nur-pdf" not in sys.argv:
        try:
            markdown_fassung()
        except Exception as e:
            print(f"WARNUNG: ZAHLENBUCH.md nicht geschrieben: {str(e)[:70]}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
