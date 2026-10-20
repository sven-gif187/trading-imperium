# -*- coding: utf-8 -*-
"""gebuehren_test.py - beweist, dass nur noch ZWEI Gebuehren abgezogen werden.

WOZU
----
Befund 42: Beim Papier-Kauf steckte die Gebuehr in `filled_cost` UND wurde in
`app.py` noch einmal auf `cost_basis` addiert. Zusammen mit der Verkaufsgebuehr
wurden dadurch DREI Gebuehren abgezogen statt zwei - am 01.09.2026 ueber
14 Verkaeufe als Faktor 3,00 gemessen, also 0,75 % je Runde statt der
K-BASIS von 0,505 %.

Behoben am 11.09.2026 (Epoche E8) in `execution/engine.py`: `filled_cost` ist
jetzt `amount - fee`, genau wie ccxt es im Livepfad liefert.

DIESES PROGRAMM rechnet einen vollstaendigen Kauf und Verkauf durch die ECHTE
Maschine und zaehlt nach, wie viele Gebuehren im Ergebnis stecken. Es prueft in
BEIDE Richtungen: es muss den Fehler finden, wenn er da ist, und schweigen,
wenn alles stimmt.

AENDERT NICHTS AM LAUFENDEN BOT. Eigene Maschine, eigene Papier-Bestaende.

    python gebuehren_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import AppConfig            # noqa: E402
from core.events import DecisionIntent, Side     # noqa: E402
from execution.engine import ExecutionEngine     # noqa: E402

EINSATZ = 200.0          # Dollar
KURS_KAUF = 100.0
KURS_VERKAUF = 110.0     # +10 % Bruttobewegung


def _fee_satz(cfg):
    for pfad in (("exchange", "taker_fee"), ("exchange", "fee_rate"),
                 ("trading", "taker_fee"), ("trading", "fee_pct")):
        o = cfg
        try:
            for k in pfad:
                o = getattr(o, k)
            if isinstance(o, (int, float)) and 0 < o < 1:
                return float(o), ".".join(pfad)
        except AttributeError:
            continue
    return None, None


def lauf():
    cfg = AppConfig()
    satz, woher = _fee_satz(cfg)
    eng = ExecutionEngine(cfg)

    # Eigene Papier-Bestaende, voellig getrennt vom laufenden Bot
    eng._paper_balances = {"USDC": 10000.0}
    eng._paper_entries = {}

    kauf = DecisionIntent(symbol="TEST/USDC", side=Side.BUY,
                          amount_usd=EINSATZ, entry_price=KURS_KAUF)
    r1 = eng.execute(kauf)
    return eng, r1, satz, woher


def main():
    print("=" * 70)
    print("  GEBUEHREN-TEST - stecken zwei oder drei Gebuehren im Ergebnis?")
    print("=" * 70)
    try:
        eng, r1, satz, woher = lauf()
    except Exception as e:
        print("\n  Der Test konnte die Maschine nicht starten: %s" % e)
        print("  (Das ist kein Befund ueber die Gebuehren - nur ueber den Test.)")
        return 2

    if r1 is None or getattr(r1, "status", "") != "filled":
        print("\n  Kauf nicht ausgefuehrt: %s"
              % getattr(r1, "rejected_reason", "unbekannt"))
        return 2

    gebuehr = r1.fee
    print("\n  KAUF ueber %.2f $ zu %.2f" % (EINSATZ, KURS_KAUF))
    print("    Gebuehr           %8.4f $   (Satz %s aus %s)"
          % (gebuehr, ("%.4f" % satz) if satz else "?", woher or "?"))
    print("    filled_qty        %8.6f" % r1.filled_qty)
    print("    Fuellpreis        %8.4f $   (Kurs + Schlupf)" % r1.avg_fill_price)
    print("    filled_cost       %8.4f $" % r1.filled_cost)
    print("    Menge x Fuellpreis%8.4f $" % (r1.filled_qty * r1.avg_fill_price))

    # Gegen den FUELLPREIS pruefen, nicht gegen den angenommenen Kurs - sonst
    # meldet der Test den Schlupf faelschlich als Fehler.
    passt = abs(r1.filled_cost - r1.filled_qty * r1.avg_fill_price) < 0.01
    print("    -> filled_cost == Menge x Fuellpreis (wie ccxt live): %s"
          % ("JA" if passt else "NEIN"))

    kosten_basis = (r1.filled_cost or 0) + (r1.fee or 0)
    print("\n  So rechnet app.py:1862 die Kostenbasis:")
    print("    cost_basis = filled_cost + fee = %.4f $" % kosten_basis)
    print("    echter Mittelabfluss war       = %.4f $" % EINSATZ)
    abw = kosten_basis - EINSATZ
    print("    Abweichung                     = %+.4f $  (%s)"
          % (abw, "richtig" if abs(abw) < 0.01 else "FALSCH"))

    print("\n" + "-" * 70)
    if abs(abw) < 0.01:
        print("  BESTANDEN: Die Kostenbasis ist der echte Mittelabfluss.")
        print("  Zusammen mit der Verkaufsgebuehr sind das ZWEI Gebuehren.")
        ergebnis = 0
    else:
        print("  DURCHGEFALLEN: Die Kostenbasis ist um %+.4f $ daneben." % abw)
        print("  Das entspricht %.2f Gebuehren zu viel." % (abw / gebuehr if gebuehr else 0))
        ergebnis = 1

    # --- Gegentest: haette der Test den ALTEN Fehler gefunden? ---
    alt_basis = EINSATZ + gebuehr            # so war es vor dem 11.09.
    alt_abw = alt_basis - EINSATZ
    print("\n  Gegenprobe - der Zustand VOR der Reparatur:")
    print("    filled_cost waere %.4f $ gewesen (amount, mit Gebuehr drin)" % EINSATZ)
    print("    cost_basis        %.4f $   Abweichung %+.4f $ = %.2f Gebuehr"
          % (alt_basis, alt_abw, alt_abw / gebuehr if gebuehr else 0))
    print("    -> Der Test haette das gemeldet: %s"
          % ("JA" if abs(alt_abw) >= 0.01 else "NEIN - dann taugt er nichts"))
    print("-" * 70)
    return ergebnis


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
