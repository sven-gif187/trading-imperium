# -*- coding: utf-8 -*-
"""Misst, ob der Regime-Filter sein Geld wert ist.

DIE FRAGE
---------
Der Regime-Filter blockt Kaeufe, wenn genug Warnsignale zusammenkommen
(Standard: 2 von 4). Am 10.08.2026 blockte er dadurch BTC UND ETH
gleichzeitig - bei RSI 29, also stark ueberverkauft. Zusammen mit der
Baerenmarkt-Regel fuer SOL stand der Bot komplett still.

Die Frage ist nicht "blockt er zu viel", sondern: WAS HAETTEN DIE
GEBLOCKTEN KAEUFE GEBRACHT? Nur das entscheidet, ob die Schwelle richtig
steht.

METHODE
-------
Jede geblockte Kaufgelegenheit steht mit Zeitstempel und Kurs in
telemetrie.db. Fuer jede wird geprueft: wie stand der Kurs 4, 12, 24 und
48 Stunden spaeter? Daraus ergibt sich, ob der Block Geld gespart oder
Gewinn verhindert hat.

Historische Kurse kommen ueber ccxt von derselben Boerse wie der Bot.

EHRLICHKEIT
-----------
- Gerechnet wird NACH Kosten (0,32 % je Runde, gemessen ueber 11 Tage).
- Ein positives Ergebnis heisst NICHT automatisch "Filter abschalten".
  Es heisst nur: in DIESEM Zeitraum haetten die Kaeufe gelohnt. Ein
  Baerenmarkt kann jederzeit weiterlaufen.
- Ist die Stichprobe klein, steht das ausdruecklich dabei.

Reine Leseoperation. Aendert nichts am Bot.

Aufruf:  python regime_filter_messung.py
"""
import os
import sqlite3
import statistics as st
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HIER, "data_store", "telemetrie.db")

# [KORREKTUR 19.08.2026] 0,32 -> 0,505. Die alte Zahl stammte aus der
# Kostenmatrix ueber 11 Tage bei den ALTEN Gebuehren. Gehandelt wird bei
# Bybit EU mit 0,25 % Taker je Seite, K-BASIS ist 0,505 % je Runde
# (CLAUDE.md Abschnitt 8). Jede 0,32 macht ein Ergebnis um 0,185
# Prozentpunkte zu schoen - und genau hier entscheidet das Vorzeichen
# darueber, ob ein Block als "hat gespart" oder "war teuer" gilt.
# Diese Datei steht auf der Liste in Handbuch 4.53. Reine Messung, kein
# Handelsverhalten - deshalb schon jetzt und nicht erst nach dem 27.08.
KOSTEN_PCT = 0.505                # K-BASIS je Runde, Bybit EU Taker
HORIZONTE = (4, 12, 24, 48)       # Stunden nach dem Block


def blockaden():
    """Alle geblockten Kaufgelegenheiten mit Zeit, Coin, Preis und Regel."""
    if not os.path.exists(DB):
        print("  telemetrie.db fehlt.")
        return []
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    rows = con.execute(
        "SELECT e.ts_utc, e.symbol, e.entry_price, r.rule_name, e.score "
        "FROM evaluations e JOIN rule_evaluations r "
        "  ON r.evaluation_id = e.evaluation_id "
        "WHERE r.rule_name IN ('REGIME_FILTER','BAERENMARKT_NUR_BTC_ETH') "
        "  AND e.entry_price > 0 "
        "ORDER BY e.ts_utc").fetchall()
    con.close()
    return rows


def kerzen_laden(symbole):
    """Stundenkerzen je Coin, damit der spaetere Kurs nachschlagbar ist."""
    import ccxt
    boerse = ccxt.binance({"enableRateLimit": True})
    daten = {}
    for sym in symbole:
        try:
            roh = boerse.fetch_ohlcv(sym, "1h", limit=1000)
            # {epoch_stunde: schlusskurs}
            daten[sym] = {int(k[0] / 1000): float(k[4]) for k in roh}
            print(f"    {sym}: {len(roh)} Stundenkerzen")
            time.sleep(boerse.rateLimit / 1000.0)
        except Exception as e:
            print(f"    {sym}: Fehler {type(e).__name__}: {e}")
    return daten


def kurs_nach(kerzen, ts_epoch, stunden):
    """Schlusskurs `stunden` nach dem Zeitpunkt. None wenn nicht abgedeckt."""
    ziel = int(ts_epoch) + stunden * 3600
    # auf volle Stunde abrunden, dann die naechste vorhandene Kerze suchen
    basis = ziel - (ziel % 3600)
    for versatz in range(0, 6 * 3600, 3600):
        k = kerzen.get(basis + versatz)
        if k:
            return k
    return None


def main():
    print("=" * 96)
    print(" REGIME-FILTER-MESSUNG - was haetten die geblockten Kaeufe gebracht?")
    print("=" * 96)

    b = blockaden()
    if not b:
        print("\n  Keine geblockten Kaufgelegenheiten mit Preis gefunden.")
        return 1

    symbole = sorted({r[1] for r in b})
    print(f"\n  {len(b)} geblockte Gelegenheiten, {len(symbole)} Coins")
    print(f"  Zeitraum: {b[0][0][:16]} bis {b[-1][0][:16]}")
    print(f"\n  Lade historische Kurse:")
    kerzen = kerzen_laden(symbole)
    if not kerzen:
        print("\n  Keine Kursdaten - Messung nicht moeglich.")
        return 1

    # ------------------------------------------------------------------
    # Auswertung je Horizont
    # ------------------------------------------------------------------
    print("\n" + "=" * 96)
    print(" ERGEBNIS - Rendite nach Kosten, wenn der Bot trotzdem gekauft haette")
    print("=" * 96)

    ergebnisse = defaultdict(list)      # (regel, horizont) -> [rendite_netto]
    je_coin = defaultdict(list)         # (coin, horizont) -> [rendite_netto]
    ohne_kurs = 0

    # [KORREKTUR 19.08.2026] Unabhaengigkeit.
    #
    # Der Bot prueft alle rund 12 Sekunden. Bleibt eine Lage eine Stunde
    # bestehen, steht dieselbe geblockte Gelegenheit 300-mal in der
    # Datenbank - und wurde bisher 300-mal gezaehlt. Aus 89.291 "Faellen"
    # wurden so Zahlen, die Sicherheit vortaeuschen, die es nicht gibt:
    # in 12 Tagen passen bei 24-Stunden-Sicht nur 12 nicht ueberlappende
    # Fenster je Coin, nicht 53.806.
    #
    # CLAUDE.md, Regel 0: "Immer fragen, wie viele davon UNABHAENGIG sind.
    # Bei Horizont H passen in T Tage nur T*24/H nicht ueberlappende
    # Fenster."
    #
    # Deshalb wird je (Coin, Regel, Horizont) nur der ERSTE Fall eines
    # Fensters gezaehlt; alles, was innerhalb der naechsten H Stunden
    # folgt, ist dieselbe Beobachtung. Die rohe Anzahl wird weiter
    # ausgewiesen, damit der Unterschied sichtbar bleibt.
    zuletzt = {}                       # (sym, regel, h) -> epoch
    roh_gezaehlt = defaultdict(int)

    for ts, sym, preis, regel, score in b:
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            epoch = t.timestamp()
        except Exception:
            continue
        k = kerzen.get(sym)
        if not k:
            continue
        for h in HORIZONTE:
            roh_gezaehlt[(regel, h)] += 1
            _schl = (sym, regel, h)
            _vor = zuletzt.get(_schl)
            if _vor is not None and epoch - _vor < h * 3600:
                continue               # dasselbe Fenster, schon gezaehlt
            zuletzt[_schl] = epoch
            spaeter = kurs_nach(k, epoch, h)
            if spaeter is None:
                ohne_kurs += 1
                continue
            brutto = (spaeter / float(preis) - 1) * 100
            netto = brutto - KOSTEN_PCT
            ergebnisse[(regel, h)].append(netto)
            je_coin[(sym, h)].append(netto)

    if not ergebnisse:
        print("\n  Keine auswertbaren Faelle - vermutlich sind die Blockaden")
        print("  zu frisch und es fehlen die spaeteren Kurse.")
        return 1

    print(f"\n  {'Regel':<26s}{'Horizont':>10s}{'unabh.':>8s}{'roh':>9s}"
          f"{'Mittel':>10s}{'Median':>10s}{'im Plus':>9s}{'Urteil':>20s}")
    print("  " + "-" * 104)
    for regel in sorted({k[0] for k in ergebnisse}):
        for h in HORIZONTE:
            w = ergebnisse.get((regel, h))
            if not w:
                continue
            mittel = sum(w) / len(w)
            plus = sum(1 for x in w if x > 0) / len(w) * 100
            # Ein Urteil braucht genug UNABHAENGIGE Faelle. Unter 30 sagt
            # die Zeile ausdruecklich, dass sie nichts sagt - lieber ein
            # "zu wenig" als eine Zahl, die gut aussieht.
            if len(w) < 30:
                urteil = "zu wenig Faelle"
            elif mittel > 0.1:
                urteil = "Block war TEUER"
            elif mittel < -0.1:
                urteil = "Block hat GESPART"
            else:
                urteil = "neutral"
            print(f"  {regel:<26s}{h:>8d} h{len(w):>8d}"
                  f"{roh_gezaehlt[(regel, h)]:>9d}{mittel:>+9.3f}%"
                  f"{st.median(w):>+9.3f}%{plus:>8.1f}%{urteil:>20s}")
    print("\n  'unabh.' = nicht ueberlappende Fenster, jede Marktlage einmal.")
    print("  'roh'    = jede Pruefung des Bots einzeln, alle 12 Sekunden.")
    print("  Nur die Spalte 'unabh.' traegt ein Urteil.")

    # ------------------------------------------------------------------
    print("\n" + "=" * 96)
    print(" NACH COIN (Horizont 24 h)")
    print("=" * 96)
    print(f"\n  {'Coin':<12s}{'Faelle':>8s}{'Mittel':>10s}{'im Plus':>10s}")
    print("  " + "-" * 40)
    for sym in symbole:
        w = je_coin.get((sym, 24))
        if not w:
            continue
        plus = sum(1 for x in w if x > 0) / len(w) * 100
        print(f"  {sym:<12s}{len(w):>8d}{sum(w)/len(w):>+9.3f}%{plus:>9.1f}%")

    # ------------------------------------------------------------------
    print("\n" + "=" * 96)
    print(" WAS DAS BEDEUTET")
    print("=" * 96)
    w24 = ergebnisse.get(("REGIME_FILTER", 24), [])
    if w24:
        m = sum(w24) / len(w24)
        print(f"\n  Regime-Filter, 24-Stunden-Sicht: {len(w24)} Faelle, "
              f"im Mittel {m:+.3f} % nach Kosten.")
        if m > 0.1:
            print("  -> Die geblockten Kaeufe waeren im Schnitt PROFITABEL gewesen.")
            print("     Der Filter kostet in dieser Marktlage Geld.")
            print("     min_confirmations von 2 auf 3 ist damit begruendbar.")
        elif m < -0.1:
            print("  -> Die geblockten Kaeufe haetten VERLUST gebracht.")
            print("     Der Filter arbeitet korrekt. NICHT lockern.")
        else:
            print("  -> Kein klarer Vorteil in eine Richtung. Die Aenderung")
            print("     waere ein Muenzwurf - lieber weiter messen.")
        if len(w24) < 100:
            print(f"\n  ACHTUNG: nur {len(w24)} Faelle. Das ist eine Momentaufnahme")
            print("  eines einzelnen Marktabschnitts, keine allgemeine Wahrheit.")
    if ohne_kurs:
        print(f"\n  {ohne_kurs} Faelle ohne spaeteren Kurs (zu frisch) - "
              f"nicht mitgerechnet.")
    print("\n  Gerechnet nach Kosten von {:.2f} % je Runde.".format(KOSTEN_PCT))
    print("  Ein Kauf gilt als 'gehalten bis zum Horizont', ohne Stop-Loss.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
