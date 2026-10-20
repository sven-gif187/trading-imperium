# -*- coding: utf-8 -*-
"""Hatte der lernende Waechter recht, als er den Filter strenger stellte?

DIE FRAGE
---------
Am 15.08.2026 um 07:47 UTC hat features/regime_adaptiv.py die Schwelle
min_confirmations selbstaendig von 3 auf 2 gesenkt - der Filter blockt
seitdem also FRUEHER. Die Aenderung fiel mitten ins Messfenster und wurde
erst am 17.08. entdeckt.

Statt den Lerner abzuschalten, wird seine Entscheidung nachgemessen. Das
ist Svens Idee und die bessere: eine abgeschaltete Regel lernt nichts,
eine nachgemessene schon.

DIE METHODE - warum das ueberhaupt geht
---------------------------------------
Der Regime-Filter schreibt seine Begruendung im Klartext mit, zum Beispiel
"Regime-Filter: 2/2 Bestaetigungen [Kurs<EMA50, Cycle-Baer]". Die erste
Zahl ist, WIE VIELE Warnsignale zusammenkamen, die zweite die geltende
Schwelle. Damit laesst sich jede Vergangenheit nachrechnen:

    gefundene Bestaetigungen >= Schwelle  ->  haette geblockt

Die entscheidende Menge sind die Faelle mit GENAU 2 Bestaetigungen:

    unter Schwelle 2  ->  geblockt   (so laeuft es heute)
    unter Schwelle 3  ->  gekauft    (so lief es vorher)

Nur diese Faelle unterscheiden die beiden Einstellungen. Fuer sie wird
nachgeschlagen, was der Kauf tatsaechlich gebracht haette.

    Ergebnis NEGATIV  ->  der Lerner hatte recht, das Blocken sparte Geld
    Ergebnis POSITIV  ->  der Lerner lag falsch, er verhindert Gewinne

MIT UND OHNE STOP-LOSS
----------------------
Die erste Messung (regime_filter_messung.py) tat so, als wuerde ein Kauf
stur bis zum Horizont gehalten. Das ist unrealistisch - in Wirklichkeit
haette der Stop-Loss vorher gekappt. Dieses Programm rechnet BEIDES:

    "gehalten"   Kurs am Horizont, ohne Stop  (wie bisher)
    "mit Stop"   Stunde fuer Stunde geprueft; faellt der Kurs unter die
                 Stop-Marke, endet der Trade dort

Der Unterschied zwischen beiden Zahlen zeigt, wie viel der Stop-Loss
ueberhaupt rettet.

EHRLICHKEIT
-----------
- Gerechnet wird nach den GEMESSENEN Kosten von 0,505 % je Runde
  (Bybit EU Taker 0,25 % je Seite plus Spanne und Schlupf) - nicht nach
  den zu guenstigen 0,32 % der ersten Messung.
- Gezaehlt werden unabhaengige STUNDEN, nicht Einzelpruefungen. Der Bot
  prueft alle 12 Sekunden und wuerde dieselbe Marktlage sonst
  hundertfach zaehlen (Pseudo-Replikation). Beide Zahlen werden
  ausgewiesen, damit der Unterschied sichtbar bleibt.
- Ein Ergebnis unterhalb von 24 unabhaengigen Stunden gilt als
  "nicht entscheidbar" und wird auch so benannt.

Reine Leseoperation. Aendert nichts am Bot.

Aufruf:  python schwelle_vergleich.py
"""
import os
import re
import sqlite3
import statistics as st
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "data_store", "telemetrie.db")

# Gemessene Kosten einer vollen Runde. Bewusst die ehrliche Zahl.
KOSTEN_PCT = 0.505
# Stop-Loss, wie er im Messfenster tatsaechlich stand.
STOP_PCT = 2.0
HORIZONTE = (4, 12, 24, 48)
# Zeitpunkt der Umstellung durch den lernenden Waechter.
UMSTELLUNG = "2026-08-15T07:47:32"
MIN_STUNDEN = 24


def gelegenheiten():
    """Geblockte Kaeufe mit der Zahl der gefundenen Bestaetigungen."""
    if not os.path.exists(DB):
        print("  telemetrie.db fehlt.")
        return []
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    rows = con.execute(
        "SELECT ts_utc, symbol, entry_price, primary_reason "
        "FROM evaluations "
        "WHERE decision='REJECTED' AND entry_price > 0 "
        "  AND primary_reason LIKE '%Bestaetigung%' "
        "ORDER BY ts_utc").fetchall()
    con.close()

    raus = []
    for ts, sym, preis, grund in rows:
        m = re.search(r"(\d+)/(\d+) Bestaetigung", grund or "")
        if not m:
            continue
        raus.append((ts, sym, float(preis), int(m.group(1)), int(m.group(2))))
    return raus


def kerzen_laden(symbole):
    """Stundenkerzen je Coin - Hoch, Tief und Schluss werden gebraucht."""
    import ccxt
    boerse = ccxt.binance({"enableRateLimit": True})
    daten = {}
    for sym in symbole:
        try:
            roh = boerse.fetch_ohlcv(sym, "1h", limit=1000)
            # {epoch_stunde: (tief, schluss)} - das Tief entscheidet, ob
            # der Stop-Loss innerhalb der Kerze ausgeloest haette.
            daten[sym] = {int(k[0] / 1000): (float(k[3]), float(k[4]))
                          for k in roh}
            print(f"    {sym}: {len(roh)} Stundenkerzen")
            time.sleep(boerse.rateLimit / 1000.0)
        except Exception as e:
            print(f"    {sym}: Fehler {type(e).__name__}: {e}")
    return daten


def verlauf(kerzen, ts_epoch, stunden):
    """Liste der Kerzen von Stunde 1 bis `stunden` nach dem Zeitpunkt."""
    basis = int(ts_epoch) - (int(ts_epoch) % 3600)
    raus = []
    for h in range(1, stunden + 1):
        k = kerzen.get(basis + h * 3600)
        if k:
            raus.append(k)
    return raus


def rendite(kerzen, ts_epoch, preis, stunden):
    """(ohne_stop, mit_stop) in Prozent nach Kosten. None wenn unbekannt."""
    weg = verlauf(kerzen, ts_epoch, stunden)
    if not weg:
        return None, None

    # ohne Stop: einfach der Schlusskurs am Ende des Horizonts
    ohne = (weg[-1][1] / preis - 1) * 100 - KOSTEN_PCT

    # mit Stop: Stunde fuer Stunde pruefen, ob das Tief die Marke reisst
    stop_kurs = preis * (1 - STOP_PCT / 100)
    mit = None
    for tief, schluss in weg:
        if tief <= stop_kurs:
            mit = -STOP_PCT - KOSTEN_PCT
            break
    if mit is None:
        mit = ohne
    return ohne, mit


def echte_fenster(spanne_tage, horizont_h):
    """Wie viele WIRKLICH unabhaengige Beobachtungen gibt es?

    Zwei Beobachtungen, die weniger als der Horizont auseinanderliegen,
    teilen sich denselben Kursverlauf - sie sind keine zwei Belege,
    sondern anderthalb. Bei 48 Stunden Horizont und 10 Tagen Datenlage
    bleiben hoechstens fuenf unabhaengige Fenster uebrig, egal wie viele
    Einzelpruefungen dahinterstehen.

    Genau das macht lange Horizonte truegerisch: Sie sehen nach der
    interessantesten Aussage aus und ruhen auf der duennsten Grundlage.
    """
    return spanne_tage * 24.0 / horizont_h


def urteil(werte, fenster_n):
    if fenster_n < MIN_STUNDEN:
        return "nicht entscheidbar"
    m = st.mean(werte)
    if m < -0.1:
        return "Blocken war richtig"
    if m > 0.1:
        return "Blocken war teuer"
    return "kein klarer Vorteil"


def main():
    print("=" * 92)
    print(" SCHWELLEN-VERGLEICH - hatte der lernende Waechter recht?")
    print("=" * 92)
    print(f"\n  Umstellung am {UMSTELLUNG} UTC: min_confirmations 3 -> 2")
    print(f"  Gerechnet nach Kosten von {KOSTEN_PCT} % je Runde, "
          f"Stop-Loss bei -{STOP_PCT} %.")

    alle = gelegenheiten()
    if not alle:
        print("\n  Keine auswertbaren Gelegenheiten gefunden.")
        return 1

    # Die Differenzmenge: genau 2 Bestaetigungen. Unter Schwelle 3 waeren
    # das Kaeufe gewesen, unter Schwelle 2 sind es Blockaden.
    strittig = [g for g in alle if g[3] == 2]
    print(f"\n  {len(alle)} geblockte Gelegenheiten insgesamt")
    print(f"  davon {len(strittig)} mit GENAU 2 Bestaetigungen "
          f"- nur diese unterscheiden die beiden Einstellungen")

    if not strittig:
        print("\n  Keine strittigen Faelle - kein Unterschied messbar.")
        return 0

    symbole = sorted({g[1] for g in strittig})
    print(f"\n  Lade historische Kurse:")
    kerzen = kerzen_laden(symbole)
    if not kerzen:
        print("\n  Keine Kursdaten - Messung nicht moeglich.")
        return 1

    ohne_d = defaultdict(list)
    mit_d = defaultdict(list)
    stunden_d = defaultdict(set)
    ohne_kurs = 0

    for ts, sym, preis, gef, noetig in strittig:
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            epoch = t.timestamp()
        except Exception:
            continue
        k = kerzen.get(sym)
        if not k:
            continue
        for h in HORIZONTE:
            o, m = rendite(k, epoch, preis, h)
            if o is None:
                ohne_kurs += 1
                continue
            ohne_d[h].append(o)
            mit_d[h].append(m)
            stunden_d[h].add(ts[:13] + sym)

    print("\n" + "=" * 92)
    print(" WAS DIE STRITTIGEN KAEUFE GEBRACHT HAETTEN")
    print("=" * 92)
    # Zeitspanne der strittigen Faelle - Grundlage der Unabhaengigkeit
    zeiten = sorted(g[0] for g in strittig)
    try:
        a = datetime.fromisoformat(zeiten[0].replace("Z", "+00:00"))
        b = datetime.fromisoformat(zeiten[-1].replace("Z", "+00:00"))
        spanne = (b - a).total_seconds() / 86400.0
    except Exception:
        spanne = 0.0

    print(f"\n  Datenlage: {spanne:.1f} Tage, "
          f"{zeiten[0][:16]} bis {zeiten[-1][:16]} UTC")
    print(f"\n  {'Horizont':>9} {'Pruefungen':>11} {'unabh.':>7} "
          f"{'ohne Stop':>11} {'mit Stop':>11} {'im Plus':>9}  Urteil")
    print("  " + "-" * 88)

    for h in HORIZONTE:
        if not ohne_d[h]:
            continue
        o, m = ohne_d[h], mit_d[h]
        # NICHT die Zahl der Stunden nehmen: bei 48 h Horizont ueberlappen
        # sich benachbarte Stunden fast vollstaendig.
        n_f = echte_fenster(spanne, h)
        plus = 100 * sum(1 for x in m if x > 0) / len(m)
        print(f"  {h:>7} h {len(o):>11} {n_f:>7.0f} "
              f"{st.mean(o):>+10.3f}% {st.mean(m):>+10.3f}% "
              f"{plus:>8.1f}%  {urteil(m, n_f)}")

    print(f"\n  Die Spalte 'unabh.' ist die einzige, die zaehlt: wie viele "
          f"nicht\n  ueberlappende Zeitfenster in {spanne:.1f} Tagen "
          f"ueberhaupt Platz haben.\n  Je laenger der Horizont, desto "
          f"weniger - und desto weniger belastbar\n  das Ergebnis, so "
          f"deutlich es auch aussieht.")

    print("\n" + "=" * 92)
    print(" WAS DAS BEDEUTET")
    print("=" * 92)

    h = 24
    if ohne_d[h]:
        m = st.mean(mit_d[h])
        o = st.mean(ohne_d[h])
        n_std = echte_fenster(spanne, h)
        print(f"\n  24-Stunden-Sicht, {n_std:.0f} unabhaengige Fenster "
              f"aus {len(ohne_d[h])} Pruefungen.")
        if n_std < MIN_STUNDEN:
            print(f"  NICHT ENTSCHEIDBAR - unter {MIN_STUNDEN} unabhaengigen "
                  f"Fenstern entscheidet der Zufall.\n"
                  f"  Die Frage ist damit heute NICHT beantwortbar, egal wie "
                  f"eindeutig die\n  Zahlen aussehen. Es braucht schlicht "
                  f"mehr Tage.")
        elif m < -0.1:
            print(f"  Die strittigen Kaeufe haetten im Mittel {m:+.3f} % "
                  f"gebracht (mit Stop-Loss).")
            print(f"  -> Der lernende Waechter hatte RECHT. Die strengere "
                  f"Schwelle spart Geld.")
        elif m > 0.1:
            print(f"  Die strittigen Kaeufe haetten im Mittel {m:+.3f} % "
                  f"gebracht (mit Stop-Loss).")
            print(f"  -> Der lernende Waechter lag FALSCH. Die strengere "
                  f"Schwelle verhindert Gewinne.")
        else:
            print(f"  Ergebnis {m:+.3f} % - kein klarer Vorteil in eine "
                  f"Richtung.")
        d = m - o
        print(f"\n  Wirkung des Stop-Loss: ohne {o:+.3f} %, mit {m:+.3f} % "
              f"- Unterschied {d:+.3f} Prozentpunkte.")
        if abs(d) < 0.01:
            print(f"  Praktisch KEIN Unterschied: die Stop-Marke von "
                  f"-{STOP_PCT} % wurde in diesen\n  Faellen so gut wie nie "
                  f"erreicht. In einem Seitwaertsmarkt ist das zu erwarten -\n"
                  f"  der Stop kann nur dort wirken, wo es auch faellt.")
        elif d > 0:
            print(f"  Der Stop haette Verlust begrenzt.")
        else:
            print(f"  Der Stop haette hier geschadet - er kappte Positionen, "
                  f"die sich noch erholten.")

    if ohne_kurs:
        print(f"\n  {ohne_kurs} Pruefungen ohne spaeteren Kurs "
              f"(zu frisch oder ausserhalb des Kerzenfensters).")

    print(f"\n  Hinweis zur Fallzahl: Der Bot prueft alle 12 Sekunden. "
          f"'Pruefungen' zaehlt jede\n  einzelne davon - diese Zahl sagt "
          f"NICHTS ueber die Belastbarkeit aus.\n  Massgeblich ist allein "
          f"die Spalte 'unabh.'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
