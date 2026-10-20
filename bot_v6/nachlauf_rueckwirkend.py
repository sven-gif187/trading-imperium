#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  NACHLAUF RUECKWIRKEND - die verlorenen Faelle zurueckholen
================================================================
Angelegt 19.08.2026 auf Svens Frage: "koennen wir die verloren
gegangenen 437 aelteren rekonstruieren damit wir da auch
ergebnisse haben?"

WARUM SIE FEHLTEN
-----------------
nachlauf.py holt die Kerzen ueber data_agent.fetch_snapshot(limit=200).
Bei 1-Stunden-Kerzen reicht das rund acht Tage zurueck. Alles, was
laenger her war, lief in diesen Zweig:

    if ziel < erste:   # Zielzeitpunkt vor der aeltesten geholten Kerze
        continue       # mit diesem Fenster nicht mehr aufloesbar

und wurde danach als "vollstaendig" abgehakt - abgeschlossen, aber
nie gemessen. Am 19.08. betraf das 437 von 453 Ausstiegen.

WARUM SIE TROTZDEM DA SIND
--------------------------
Nicht die Daten waren weg, sondern der Griff danach. Binance liefert
ueber ccxt.fetch_ohlcv(..., since=...) beliebig alte Kerzen. Geprueft
am 19.08. mit dem 10.06. - kommt zurueck.

Das ist derselbe Fehlertyp wie beim Projektgedaechtnis:

  > Das Gedaechtnis fehlt nicht - der Griff danach fehlt.

WAS DIESES WERKZEUG TUT
-----------------------
1. Holt je Muenze EINMAL alle 1-Stunden-Kerzen des gesamten Zeitraums
   (in 1000er-Bloecken) und legt sie in den Speicher.
2. Traegt fuer jedes Ereignis ohne Werte die vier Fristen nach - nach
   genau derselben Regel wie die Live-Messung: erste Kerze bei oder
   nach dem Zielzeitpunkt, deren Schlusskurs.
3. Schreibt in die Spalte `quelle`, ob ein Wert live gemessen,
   nachgetragen oder korrigiert wurde. Wer auswertet, kann trennen.

WAS DIE GEGENPROBE GEFUNDEN HAT (Befund 60)
-------------------------------------------
Beim Nachrechnen der bereits live gemessenen Werte stimmten 3.870 von
11.200 (34,6 %) mit KEINER fertigen Kerze ueberein. Ursache: eine
Kerze traegt ihre OEFFNUNGS-Zeit als Stempel und ist erst eine Stunde
spaeter fertig. Wer sie vorher ausliest, bekommt keinen Schlusskurs,
sondern den gerade laufenden Preis - und speichert ihn dauerhaft.

nachlauf.py ist repariert (fertige Kerzen only). Die alten Werte
lassen sich mit --korrigieren ueberschreiben.

WAS ES NICHT TUT
----------------
Kein Eingriff in den Bot, keine Verhaltensaenderung, kein Schreiben in
eine andere Datenbank. Es schreibt ausschliesslich Messwerte in
data_store/nachlauf.db. Freeze-vertraeglich.

BENUTZUNG
---------
    python nachlauf_rueckwirkend.py --gegenprobe    # Pflicht zuerst
    python nachlauf_rueckwirkend.py                 # Probelauf
    python nachlauf_rueckwirkend.py --schreiben     # nachtragen
    python nachlauf_rueckwirkend.py --korrigieren --schreiben
    python nachlauf_rueckwirkend.py --stand
================================================================
"""
import os
import sys
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "data_store", "nachlauf.db")
FENSTER = [1, 4, 24, 48]
KERZE_H = 1                    # Laenge einer Kerze in Stunden
TAKT_MS = KERZE_H * 3600 * 1000

NL = chr(10)


# ----------------------------------------------------------------
#  Kerzen holen
# ----------------------------------------------------------------
def kerzen_holen(muenze, von_utc, bis_utc, still=False):
    """Alle 1h-Kerzen zwischen zwei Zeitpunkten, als sortierte Liste
    von (ts_ms, close). In 1000er-Bloecken, weil Binance nicht mehr
    auf einmal liefert."""
    import ccxt
    ex = ccxt.binance({"enableRateLimit": True})
    seit = int(von_utc.timestamp() * 1000)
    ende = int(bis_utc.timestamp() * 1000)
    raus = []
    letzter = None
    while seit <= ende:
        try:
            block = ex.fetch_ohlcv(muenze, "1h", since=seit, limit=1000)
        except Exception as e:
            if not still:
                print("    " + muenze + ": Abruf fehlgeschlagen - " + str(e)[:60])
            break
        if not block:
            break
        raus.extend((k[0], float(k[4])) for k in block if k[0] <= ende)
        neu = block[-1][0]
        if letzter is not None and neu <= letzter:
            break                      # keine Bewegung mehr - Abbruch
        letzter = neu
        seit = neu + TAKT_MS
        if len(block) < 1000:
            break
    raus.sort()
    return raus


def kurs_bei(kerzen, ziel_ms, jetzt_ms=None):
    """Schlusskurs der ersten FERTIGEN Kerze bei oder nach ziel_ms.

    Dieselbe Regel wie in nachlauf.py - sonst waeren nachgetragene und
    live gemessene Werte nicht vergleichbar. Zusaetzlich der Schutz aus
    Befund 60: eine Kerze mit Oeffnungszeit T ist erst bei T+1h fertig.
    """
    lo, hi = 0, len(kerzen)
    while lo < hi:
        mit = (lo + hi) // 2
        if kerzen[mit][0] < ziel_ms:
            lo = mit + 1
        else:
            hi = mit
    if lo >= len(kerzen):
        return None
    if jetzt_ms is not None and kerzen[lo][0] + TAKT_MS > jetzt_ms:
        return None                    # Kerze laeuft noch
    return kerzen[lo][1]


def _zeit(ts):
    z = datetime.fromisoformat(ts)
    if z.tzinfo is None:
        z = z.replace(tzinfo=timezone.utc)
    return z


def _ist_ein_kerzenschluss(kerzen, wert, toleranz=0.01):
    """Gibt es ueberhaupt eine fertige Kerze mit diesem Schlusskurs?

    Wenn nein, kann der Wert nur aus einer laufenden Kerze stammen -
    ein Preis, der beim Ablesen noch in Bewegung war (Befund 60).
    """
    for _ts, c in kerzen:
        if abs(c - wert) < toleranz:
            return True
    return False


def _vorrat(zeilen, ts_spalte, muenz_spalte, still=True):
    """Kerzen fuer alle vorkommenden Muenzen einmal holen."""
    muenzen = sorted({z[muenz_spalte] for z in zeilen})
    von = min(_zeit(z[ts_spalte]) for z in zeilen) - timedelta(hours=2)
    bis = max(_zeit(z[ts_spalte]) for z in zeilen) + timedelta(hours=50)
    bis = min(bis, datetime.now(timezone.utc))
    vorrat = {}
    for m in muenzen:
        vorrat[m] = kerzen_holen(m, von, bis, still=still)
        print("  " + m.ljust(12) + str(len(vorrat[m])).rjust(7) + " Kerzen")
    return vorrat


# ----------------------------------------------------------------
#  Gegenprobe - gegen einen BEKANNTEN Wert, nicht gegen Plausibilitaet
# ----------------------------------------------------------------
def gegenprobe():
    """Prueft den Nachtrag in drei Richtungen.

    TEIL 1 - gegen einen von Hand nachgerechneten Einzelfall.
        Das ist die Pruefung, die CLAUDE.md Regel 0 verlangt: nicht
        gegen Plausibilitaet, nicht gegen eine Anzahl, sondern gegen
        einen bekannten Wert. Die vier Erwartungswerte stammen aus
        einer von Hand durchgesehenen Kerzenliste (SOL/USDC, 16.08.).
        Historische Kerzen aendern sich nicht - dieser Test veraltet
        also nie, anders als ein Test gegen laufende Kennzahlen.

    TEIL 2 - gegen die bereits live gemessenen Werte.
        Kein Bestehen/Durchfallen, sondern eine Statistik mit
        Erklaerung: die Live-Messung hat einen eigenen Fehler
        (Befund 60, laufende Kerzen), deshalb MUSS es Abweichungen
        geben. Zu sehen ist nur, ob die Groessenordnung passt.

    TEIL 3 - faellt der Nachtrag sauber aus, wenn er nichts weiss?
        Laufende Kerze, leere Kerzenliste, Ziel in der Zukunft.
    """
    fehler = 0

    # ---------------- TEIL 1 ----------------
    print("=" * 74)
    print("TEIL 1 - gegen einen von Hand nachgerechneten Einzelfall")
    print("=" * 74)
    fall_zeit = datetime(2026, 8, 16, 21, 40, tzinfo=timezone.utc)
    erwartet = {1: 74.55, 4: 75.42, 24: 75.68, 48: 76.91}
    print(NL + "SOL/USDC, Ereignis am 16.08.2026 21:40 UTC.")
    print("Von Hand aus der Kerzenliste abgelesen (Oeffnungszeit -> Schluss):"
          + NL)
    kerzen = kerzen_holen("SOL/USDC", fall_zeit - timedelta(hours=2),
                          fall_zeit + timedelta(hours=50), still=True)
    print("  Frist   Zielzeit      erwartet   berechnet   Urteil")
    print("  " + "-" * 52)
    for h in FENSTER:
        ziel = fall_zeit + timedelta(hours=h)
        ist = kurs_bei(kerzen, int(ziel.timestamp() * 1000))
        soll = erwartet[h]
        ok = ist is not None and abs(ist - soll) < 0.005
        print("  " + (str(h) + "h").rjust(4) + "   "
              + format(ziel, "%d.%m %H:%M") + "   "
              + format(soll, ">9,.2f") + "   "
              + (format(ist, ">9,.2f") if ist is not None else "    fehlt")
              + "   " + ("OK" if ok else "FALSCH"))
        if not ok:
            fehler += 1
    print(NL + "  Regel: die erste Kerze, deren OEFFNUNGSzeit bei oder nach")
    print("  dem Zielzeitpunkt liegt. 22:40 trifft also die 23:00-Kerze.")

    # ---------------- TEIL 3 (vor Teil 2, weil schnell) ----------------
    print(NL + "=" * 74)
    print("TEIL 3 - faellt er sauber aus, wenn er nichts weiss?")
    print("=" * 74)
    jetzt_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    faelle = [
        ("leere Kerzenliste", kurs_bei([], jetzt_ms) is None),
        ("Ziel nach der letzten Kerze",
         kurs_bei(kerzen, jetzt_ms + 99 * 3600 * 1000) is None),
        ("laufende Kerze wird verweigert",
         kurs_bei([(jetzt_ms, 100.0)], jetzt_ms, jetzt_ms) is None),
        ("fertige Kerze wird geliefert",
         kurs_bei([(jetzt_ms - 2 * 3600 * 1000, 100.0)],
                  jetzt_ms - 2 * 3600 * 1000, jetzt_ms) == 100.0),
    ]
    for name, ok in faelle:
        print("  " + ("OK  " if ok else "FEHL") + "  " + name)
        if not ok:
            fehler += 1

    # ---------------- TEIL 2 ----------------
    con = sqlite3.connect(DB, timeout=30)
    zeilen = con.execute(
        "SELECT id, art, ts_utc, muenze, preis, p1h, p4h, p24h, p48h "
        "FROM nachlauf WHERE p1h IS NOT NULL ORDER BY ts_utc").fetchall()
    print(NL + "=" * 74)
    print("TEIL 2 - Abgleich mit den live gemessenen Werten")
    print("=" * 74)
    if not zeilen:
        print(NL + "Keine live gemessenen Zeilen - Abgleich entfaellt.")
    else:
        print(NL + str(len(zeilen)) + " Zeilen mit Live-Werten." + NL)
        vorrat = _vorrat(zeilen, 2, 3)
        gleich = anders = 0
        groesste = 0.0
        for zid, art, ts, muenze, preis, *werte in zeilen:
            zeit = _zeit(ts)
            kz = vorrat.get(muenze) or []
            for h, live in zip(FENSTER, werte):
                if live is None:
                    continue
                neu = kurs_bei(kz, int((zeit + timedelta(hours=h)).timestamp() * 1000))
                if neu is None:
                    continue
                if abs(neu - live) < 0.01:
                    gleich += 1
                else:
                    anders += 1
                    groesste = max(groesste, abs(neu - live) / live * 100)
        ges = gleich + anders
        print(NL + "  gleich  : " + str(gleich).rjust(6)
              + "  (" + format(100.0 * gleich / ges, ".1f") + " %)")
        print("  anders  : " + str(anders).rjust(6)
              + "  (" + format(100.0 * anders / ges, ".1f") + " %)")
        print("  groesste Abweichung: " + format(groesste, ".3f") + " %")
        print(NL + "  Die Abweichungen sind ERWARTET: die Live-Messung las in")
        print("  einem Drittel der Faelle eine noch laufende Kerze (Befund 60).")
        print("  Nachgewiesen an SOL/USDC 16.08. 21:40 - live stand 74,45,")
        print("  das ist der Stand MITTEN in der 23:00-Kerze; fertig schloss")
        print("  sie bei 74,55. Mit --korrigieren werden solche Werte ersetzt.")

    print(NL + "=" * 74)
    if fehler == 0:
        print("BESTANDEN - Teil 1 und 3 fehlerfrei. Nachtragen ist zulaessig.")
    else:
        print("DURCHGEFALLEN - " + str(fehler) + " Fehler in Teil 1 oder 3.")
    print("=" * 74)
    return 1 if fehler else 0


# ----------------------------------------------------------------
#  Der eigentliche Nachtrag
# ----------------------------------------------------------------
def _spalte_quelle(con, schreiben):
    hat = [r[1] for r in con.execute("PRAGMA table_info(nachlauf)")]
    if "quelle" in hat:
        return True
    if schreiben:
        con.execute("ALTER TABLE nachlauf ADD COLUMN quelle TEXT DEFAULT 'live'")
        con.commit()
        print("Spalte 'quelle' angelegt (Vorgabe 'live')." + NL)
        return True
    print("Spalte 'quelle' fehlt noch - wird beim Schreiben angelegt." + NL)
    return False


def nachtragen(schreiben=False, art=None, korrigieren=False):
    con = sqlite3.connect(DB, timeout=30)
    _spalte_quelle(con, schreiben)

    if korrigieren:
        wo = "WHERE p1h IS NOT NULL"
        titel = "KORREKTUR der Werte aus laufenden Kerzen (Befund 60)"
    else:
        wo = "WHERE (p1h IS NULL OR p4h IS NULL OR p24h IS NULL OR p48h IS NULL)"
        titel = "NACHTRAG der nie gemessenen Ereignisse"
    if art:
        wo += " AND art='" + art + "'"

    zeilen = con.execute(
        "SELECT id, art, ts_utc, muenze, preis, p1h, p4h, p24h, p48h "
        "FROM nachlauf " + wo + " ORDER BY ts_utc").fetchall()

    print("=" * 74)
    print(titel + ("" if schreiben else "   -   PROBELAUF, schreibt nichts"))
    print("=" * 74)
    if not zeilen:
        print(NL + "Nichts zu tun.")
        return 0

    jetzt = datetime.now(timezone.utc)
    jetzt_ms = int(jetzt.timestamp() * 1000)
    faellig = [z for z in zeilen if _zeit(z[2]) + timedelta(hours=1) <= jetzt]
    print(NL + str(len(zeilen)) + " Ereignisse betroffen, davon "
          + str(len(faellig)) + " ueberhaupt schon faellig." + NL)

    nach_art = {}
    for z in faellig:
        nach_art[z[1]] = nach_art.get(z[1], 0) + 1
    for a, n in sorted(nach_art.items()):
        print("    " + a.ljust(12) + str(n).rjust(6))

    if not faellig:
        return 0
    print(NL + "Kerzen holen (einmal je Muenze, danach nur Nachschlagen):")
    vorrat = _vorrat(faellig, 2, 3)

    getragen = teilweise = ohne = unveraendert = 0
    for zid, _a, ts, muenze, preis, *vorhanden in faellig:
        kerzen = vorrat.get(muenze) or []
        if not kerzen or not preis or preis <= 0:
            ohne += 1
            continue
        zeit = _zeit(ts)
        sp, wt = [], []
        offen_geblieben = False
        for h, schon in zip(FENSTER, vorhanden):
            if korrigieren:
                if schon is None:
                    continue
                if _ist_ein_kerzenschluss(kerzen, schon):
                    continue           # war schon eine fertige Kerze
            elif schon is not None:
                continue
            ziel = zeit + timedelta(hours=h)
            if ziel > jetzt:
                offen_geblieben = True
                continue
            kurs = kurs_bei(kerzen, int(ziel.timestamp() * 1000), jetzt_ms)
            if kurs is None:
                offen_geblieben = True
                continue
            sp.append("p" + str(h) + "h=?")
            wt.append(kurs)
            sp.append("r" + str(h) + "h=?")
            wt.append((kurs / preis - 1) * 100)
        if not sp:
            unveraendert += 1
            continue
        if schreiben:
            marke = "korrigiert" if korrigieren else "nachgetragen"
            con.execute("UPDATE nachlauf SET " + ",".join(sp)
                        + ", quelle=? WHERE id=?", (*wt, marke, zid))
            if not offen_geblieben:
                con.execute("UPDATE nachlauf SET vollstaendig=1 WHERE id=?", (zid,))
        getragen += 1
        teilweise += 1 if offen_geblieben else 0

    if schreiben:
        con.commit()
    print(NL + "  geaendert           : " + str(getragen))
    print("  davon teilweise     : " + str(teilweise)
          + "  (spaetere Fristen noch offen)")
    print("  schon in Ordnung    : " + str(unveraendert))
    print("  ohne Kurs           : " + str(ohne))
    if not schreiben:
        print(NL + "  PROBELAUF - mit --schreiben wird es eingetragen.")
    return 0


def stand():
    con = sqlite3.connect(DB, timeout=30)
    print("=" * 74)
    print("STAND der Nachlauf-Messung")
    print("=" * 74)
    hat_quelle = "quelle" in [r[1] for r in con.execute("PRAGMA table_info(nachlauf)")]
    for (art,) in con.execute("SELECT DISTINCT art FROM nachlauf ORDER BY art"):
        n = con.execute("SELECT COUNT(*) FROM nachlauf WHERE art=?",
                        (art,)).fetchone()[0]
        m = con.execute("SELECT COUNT(*) FROM nachlauf WHERE art=? "
                        "AND r1h IS NOT NULL", (art,)).fetchone()[0]
        anteil = (100.0 * m / n) if n else 0.0
        print(NL + "  " + art.ljust(12) + str(n).rjust(6) + " Ereignisse, davon "
              + str(m).rjust(6) + " mit 1h-Wert (" + format(anteil, ".1f") + " %)")
        if hat_quelle:
            for q, k in con.execute(
                    "SELECT COALESCE(quelle,'live'), COUNT(*) FROM nachlauf "
                    "WHERE art=? AND r1h IS NOT NULL GROUP BY 1", (art,)):
                print("       " + str(q).ljust(14) + str(k).rjust(6))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Nachlauf rueckwirkend nachtragen")
    p.add_argument("--gegenprobe", action="store_true",
                   help="live gemessene Faelle nachrechnen und vergleichen")
    p.add_argument("--schreiben", action="store_true",
                   help="wirklich schreiben (ohne: Probelauf)")
    p.add_argument("--korrigieren", action="store_true",
                   help="Werte aus laufenden Kerzen ueberschreiben (Befund 60)")
    p.add_argument("--art", choices=["exit", "blockade"],
                   help="nur eine Ereignisart")
    p.add_argument("--stand", action="store_true", help="nur den Stand zeigen")
    a = p.parse_args()
    if a.gegenprobe:
        sys.exit(gegenprobe())
    if a.stand:
        sys.exit(stand())
    sys.exit(nachtragen(schreiben=a.schreiben, art=a.art,
                        korrigieren=a.korrigieren))
