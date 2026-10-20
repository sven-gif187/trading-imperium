# -*- coding: utf-8 -*-
"""hold_recovery_rueckblick.py - haette Aussitzen die echten Verluste gerettet?

DIE FRAGE
---------
Svens Handelsweg sieht vor, Verlierer auszusitzen statt sie zu verkaufen.
Ob das traegt, muss nicht erraten werden: `nachlauf.db` schreibt seit dem
25.07.2026 zu jedem Ausstieg mit, wie der Kurs 1, 4, 24 und 48 Stunden
DANACH stand. Genau dafuer wurde sie gebaut (Befund 59/60).

Diese Auswertung nimmt jeden Ausstieg MIT VERLUST und rechnet nach, was
Durchhalten gebracht haette.

DREI DINGE, DIE DIESE MESSUNG NICHT KANN - vorweg, nicht im Kleingedruckten
--------------------------------------------------------------------------
1. **Sie endet nach 48 Stunden.** Hold/Recovery kann Wochen dauern. Was
   nach zwei Tagen noch im Minus steht, ist hier "offen", nicht "verloren".
   Die Zahl unten ist deshalb eine OBERGRENZE fuer den Nutzen des Haltens.

2. **Sie kennt die Struktur nicht.** Ob das Swing-Tief gebrochen war, steht
   nicht in `nachlauf.db`. Gerechnet wird nur die Notbremse bei -15 %. Eine
   echte Hold-Regel haette einen Teil dieser Positionen frueher geschlossen,
   weil die These widerlegt war - meist mit kleinerem Verlust.

3. **Die Stichprobe ist nicht zufaellig.** Nachlaufwerte gibt es nur, wenn
   der Sammler zum passenden Zeitpunkt lief. Und der Grossteil der Faelle
   stammt aus der Zeit, als der Trend-Ausstieg noch scharf war - er ist
   seit dem 10.08. im Schattenmodus. Das wird unten nach Grund getrennt
   ausgewiesen, damit es niemand uebersieht.

WAS GERECHNET WIRD
------------------
Fuer jeden Verlust-Ausstieg:

    verkauft  der gebuchte Verlust, nach Kosten
    gehalten  derselbe Handel, aber erst nach 1/4/24/48 h geschlossen,
              ebenfalls nach Kosten - ausser die Notbremse haette gegriffen

Und die Trivial-Latte, ohne die kein Urteil gilt: **gar nicht handeln.**

AENDERT NICHTS. Liest nur.

    python hold_recovery_rueckblick.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.kosten import K_BASIS_PCT                      # noqa: E402
from risk.hold_recovery import NOTBREMSE_PCT             # noqa: E402

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "data_store", "nachlauf.db")
FENSTER = (("r1h", "1 Stunde"), ("r4h", "4 Stunden"),
           ("r24h", "24 Stunden"), ("r48h", "48 Stunden"))


def hole():
    if not os.path.exists(DB):
        return []
    con = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    con.row_factory = sqlite3.Row
    r = con.execute(
        "SELECT muenze, pnl_pct, grund, r1h, r4h, r24h, r48h, ts_utc "
        "FROM nachlauf WHERE art='exit' AND pnl_pct < 0 "
        "ORDER BY ts_utc").fetchall()
    con.close()
    return [dict(z) for z in r]


def mittel(werte):
    return sum(werte) / len(werte) if werte else 0.0


def auswerten(faelle, spalte):
    """Gibt (verkauft, gehalten, notbremsen, n) je in Prozent zurueck."""
    verkauft, gehalten, notbremsen = [], [], 0
    for f in faelle:
        weiter = f.get(spalte)
        if weiter is None:
            continue
        gebucht = float(f["pnl_pct"])
        # Der gebuchte Verlust steht brutto in der Tabelle; die Kosten
        # einer Runde kommen in beiden Faellen gleich obendrauf.
        verkauft.append(gebucht - K_BASIS_PCT)
        # Gehalten: der Kurs lief nach dem Ausstieg um `weiter` Prozent
        # weiter. Der Gewinn der gehaltenen Position ist der gebuchte
        # Stand PLUS diese Bewegung.
        weiter_gehalten = gebucht + float(weiter)
        # Notbremse: waere sie unterwegs gerissen worden? Das laesst sich
        # hier nur am ENDSTAND pruefen - der Verlauf dazwischen ist nicht
        # gespeichert. Also eine Untergrenze fuer die Zahl der Notbremsen.
        if weiter_gehalten <= NOTBREMSE_PCT:
            weiter_gehalten = NOTBREMSE_PCT
            notbremsen += 1
        gehalten.append(weiter_gehalten - K_BASIS_PCT)
    return mittel(verkauft), mittel(gehalten), notbremsen, len(verkauft)


def main():
    print("=" * 82)
    print("  HOLD/RECOVERY im Rueckblick - haette Aussitzen die Verluste gerettet?")
    print("  Gerechnet auf nachlauf.db, Kosten %.3f %% je Runde" % K_BASIS_PCT)
    print("=" * 82)

    alle = hole()
    if not alle:
        print("  Keine Verlust-Ausstiege mit Nachlaufdaten gefunden.")
        return 2

    # [Berichtigt 14.09.] Die erste Fassung rechnete jedes Fenster auf
    # den Faellen, die GERADE diesen Wert hatten - 57 beim 24-Stunden-
    # Fenster, 39 beim 48-Stunden-Fenster. Damit verglich die Zeile
    # "24h gegen 48h" zwei verschiedene Stichproben, und der Sprung von
    # +0,314 auf -0,489 haette auch daher kommen koennen.
    #
    # Jetzt zaehlen nur Faelle, die ALLE vier Werte tragen.
    faelle = [f for f in alle
              if all(f.get(sp) is not None for sp, _ in FENSTER)]

    print()
    print("  Verlust-Ausstiege mit Nachlaufdaten : %d" % len(alle))
    print("  davon mit ALLEN vier Fenstern       : %d   <- nur diese zaehlen"
          % len(faelle))
    if len(alle) > len(faelle):
        print("  (%d Faelle sind noch zu jung fuer den 48-Stunden-Wert)"
              % (len(alle) - len(faelle)))
    if not faelle:
        print("  Kein Fall hat alle vier Werte - nicht entscheidbar.")
        return 2
    print()
    print("  %-12s %5s %12s %12s %12s %10s"
          % ("Fenster", "n", "verkauft", "gehalten", "Unterschied", "Notbremse"))
    print("  " + "-" * 70)

    ergebnisse = {}
    for spalte, name in FENSTER:
        v, g, nb, n = auswerten(faelle, spalte)
        ergebnisse[spalte] = (v, g, nb, n)
        if n == 0:
            print("  %-12s %5s   keine Daten" % (name, "-"))
            continue
        print("  %-12s %5d %11.3f%% %11.3f%% %+11.3f %10d"
              % (name, n, v, g, g - v, nb))

    print("  " + "-" * 70)
    print()
    print("  ZUR TRIVIAL-LATTE: gar nicht handeln waere 0,000 % und schlaegt")
    print("  beide Spalten. Das ist aber KEIN Urteil ueber den Bot - die")
    print("  Stichprobe enthaelt ausschliesslich VERLUST-Ausstiege, die")
    print("  Gewinner fehlen per Konstruktion. Verglichen werden darf hier")
    print("  nur: verkauft GEGEN gehalten.")

    # ------------------------------------------------------- nach Grund
    print()
    print("  Nach Ausstiegsgrund getrennt (24-Stunden-Fenster):")
    print("  " + "-" * 70)
    nach_grund = {}
    for f in faelle:
        if f.get("r24h") is None:
            continue
        art = (f.get("grund") or "?").split("(")[0].strip()[:28]
        nach_grund.setdefault(art, []).append(f)
    for art, gruppe in sorted(nach_grund.items(), key=lambda x: -len(x[1])):
        v, g, nb, n = auswerten(gruppe, "r24h")
        print("    %-30s %4d %+8.3f%% -> %+8.3f%%  (%+.3f)"
              % (art, n, v, g, g - v))

    # ------------------------------------------------------- das Urteil
    print()
    print("=" * 82)
    v24, g24, nb24, n24 = ergebnisse.get("r24h", (0, 0, 0, 0))
    if n24 < 30:
        print("  NICHT ENTSCHEIDBAR: nur %d Faelle im 24-Stunden-Fenster." % n24)
        print("  Unter 30 unabhaengigen Faellen ist jede Richtung Zufall.")
    else:
        print("  Ueber %d Faelle waere Halten um %+.3f Prozentpunkte anders"
              % (n24, g24 - v24))
        print("  ausgegangen als Verkaufen.")
    print()
    print("  WAS DIESE ZAHL NICHT IST:")
    print("    - Sie endet nach 48 Stunden. Hold/Recovery kann Wochen")
    print("      dauern; was dann noch im Minus steht, ist hier nicht")
    print("      verloren, sondern OFFEN. Die Zahl ist eine Obergrenze.")
    print("    - Sie kennt die Struktur nicht. Nur die Notbremse bei")
    print("      %.0f %% ist gerechnet, nicht der Bruch des Swing-Tiefs." % NOTBREMSE_PCT)
    print("    - Die Notbremse ist am ENDSTAND geprueft, nicht am Verlauf.")
    print("      Zwischendurch tiefer gefallene Positionen fehlen - die")
    print("      Zahl der Notbremsen ist also eine Untergrenze.")
    print("    - Der Grossteil der Faelle stammt aus der Zeit, als der")
    print("      Trend-Ausstieg scharf war (seit 10.08. im Schattenmodus).")
    print("      Deshalb die Aufschluesselung nach Grund oben.")
    print()
    print("  Die belastbare Messung ist der Schattenbetrieb ab jetzt:")
    print("  risk/hold_recovery.py schreibt bei jedem Kurs-Update mit,")
    print("  was sie getan haette - mit Struktur und Verlauf.")
    print("=" * 82)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
