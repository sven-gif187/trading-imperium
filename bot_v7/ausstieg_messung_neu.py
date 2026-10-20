# -*- coding: utf-8 -*-
"""Schneidet das Trailing die Gewinne ab? - gegen die Verlaeufe gerechnet.

DIE FRAGE
---------
Gemessen an 419 Papier-Verkaeufen (netto, 17.09.2026):

    Trefferquote      59,7 %     noetig fuer die Null: 65,4 %
    Chance/Risiko     1 : 1,89
    Gesamt            -67,36 USD

Die Trefferquote ist also NICHT das Problem - das Verhaeltnis ist es.
Und die Hoechststaende legen nahe, woran das liegt:

    TRAILING_STOP   71 Faelle   Hoechststand +2,65 %   Verkauf +1,48 %

**1,17 Punkte je Trade bleiben liegen.** 21 der 71 Faelle erreichten
sogar das erste Fibonacci-Ziel (+2,72 %).

WARUM DAS NOCH KEIN BEWEIS IST
------------------------------
Man kann nicht am Hoechststand verkaufen. Die Frage ist nicht, wieviel
liegenblieb, sondern ob ein WEITERES Trailing unterm Strich mehr
einbringt - oder ob die Position dann zurueckfaellt und der Gewinn ganz
verschwindet. Das entscheidet sich nur am Verlauf, nicht am Endstand.

CLAUDE.md Abschnitt 7: "Nichts anschliessen ohne Messung. Vier fertige
Bausteine wurden schon verworfen, weil sie schlechter waren als die
einfachste Alternative."

WAS BEFUND 79 UNVERWERTBAR MACHTE - und wie es hier vermieden wird
------------------------------------------------------------------
ausstieg_vergleich.py meldete am 26.08., alle acht Regeln verloeren
gegen "Halten". Das Urteil trug nicht: echte Positionen sind im Median
4,6 h aufgezeichnet, Schattenpositionen 99,4 h - Faktor 21. Bei echten
endet die Aufzeichnung beim Verkauf, "Halten" heisst dort also "halten,
bis der Bot ohnehin verkauft". Verglichen wurden vier Stunden gegen vier
Tage, in einem steigenden Markt.

Hier deshalb: **nur echte Positionen** (Spalte `quelle`), und jede Regel
laeuft ueber genau denselben Verlauf, Punkt fuer Punkt. Damit vergleicht
jede Zeile dieselbe Zeitspanne mit sich selbst.

Aufruf:  python ausstieg_messung_neu.py
"""
import os
import sqlite3
import statistics as st
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
PAPIER = os.path.join(os.path.dirname(HIER), "trading_imperium_v6(21)")
DB = os.path.join(PAPIER, "data_store", "positionsverlauf.db")

K_BASIS_PCT = 0.505     # CLAUDE.md Abschnitt 8. Nie aus ccxt holen.

# Die heutige Leiter, aus risk/exit_rules.py gelesen, nicht abgeschrieben.
try:
    sys.path.insert(0, HIER)
    from risk.exit_rules import LEITER, TRAIL_AB_PCT, BREAKEVEN_AB_PCT, \
        BREAKEVEN_PUFFER_PCT
except Exception:
    LEITER = ((1.2, 1.0), (3.0, 1.3), (5.0, 1.7), (8.0, 2.2))
    TRAIL_AB_PCT, BREAKEVEN_AB_PCT, BREAKEVEN_PUFFER_PCT = 1.57, 1.0, 0.55

STOP = 2.5              # Basis-Stop laut data_store/config.json
TRAIL = 1.0             # Basis-Trailing


def _faktor(hoch):
    f = LEITER[0][1]
    for schwelle, x in LEITER:
        if hoch >= schwelle:
            f = x
    return f


# --------------------------------------------------------------- Die Regeln
# Jede bekommt den Verlauf Punkt fuer Punkt und sagt, ob JETZT verkauft
# wird. Rueckgabe: Grund (dann Ausstieg) oder None (weiter halten).

def regel_heute(p, hoch, stop=STOP, trail=TRAIL):
    """Was der Bot heute tut: Stop, Breakeven-Sperre, Trailing-Leiter."""
    if p <= -stop:
        return "STOP"
    if hoch >= BREAKEVEN_AB_PCT and p <= BREAKEVEN_PUFFER_PCT:
        return "BREAKEVEN"
    if hoch >= TRAIL_AB_PCT and (hoch - p) >= _faktor(hoch) * trail:
        return "TRAIL"
    return None


def regel_trail_weiter(p, hoch):
    """Wie heute, aber das Trailing haelt 1,5x soviel Rueckschlag aus."""
    return regel_heute(p, hoch, trail=TRAIL * 1.5)


def regel_ohne_breakeven(p, hoch):
    """Wie heute, nur ohne die Breakeven-Sperre.

    Sie verliert nachweislich Geld: 29 Faelle, -15,76 USD, 3 % Treffer.
    Die Frage ist, ob ihr Wegfall besser oder schlechter ist - ohne sie
    laufen diese Trades weiter und koennen im Stop landen.
    """
    if p <= -STOP:
        return "STOP"
    if hoch >= TRAIL_AB_PCT and (hoch - p) >= _faktor(hoch) * TRAIL:
        return "TRAIL"
    return None


def regel_fib_ziel(p, hoch):
    """Wie heute, aber mit festem Ziel beim ersten Fibonacci-Ziel."""
    if p >= 2.72:
        return "FIB-ZIEL"
    return regel_heute(p, hoch)


def regel_nur_stop(p, hoch):
    """Kein Trailing, nur der Stop. Laesst Gewinne voll laufen."""
    return "STOP" if p <= -STOP else None


def regel_halten(p, hoch):
    """DIE TRIVIAL-LATTE. Nie verkaufen - bis die Aufzeichnung endet.

    CLAUDE.md Abschnitt 7: ohne diesen Vergleich gilt ein Modell als
    ungemessen.
    """
    return None


REGELN = (
    ("heute (Ist-Zustand)", regel_heute),
    ("Trailing 1,5x weiter", regel_trail_weiter),
    ("ohne Breakeven-Sperre", regel_ohne_breakeven),
    ("Ziel +2,72 % (Fib)", regel_fib_ziel),
    ("nur Stop, kein Trail", regel_nur_stop),
    ("HALTEN (Trivial-Latte)", regel_halten),
)


def verlaeufe():
    """Nur ECHTE Positionen, je ein Verlauf als Liste von (pnl, hoch)."""
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    quellen = [r[0] for r in c.execute(
        "SELECT DISTINCT quelle FROM positionen")]
    echt = [q for q in quellen
            if q and ("echt" in str(q).lower() or "real" in str(q).lower()
                      or "live" in str(q).lower())]
    if not echt:
        echt = [q for q in quellen if "schatten" not in str(q).lower()]

    raus = []
    for (pid,) in c.execute(
            "SELECT pos_id FROM positionen WHERE quelle IN (%s)"
            % ",".join("?" * len(echt)), echt):
        punkte = c.execute(
            "SELECT pnl_pct, mfe_pct FROM verlauf WHERE pos_id=? "
            "ORDER BY minuten", (pid,)).fetchall()
        if len(punkte) >= 3:
            raus.append(punkte)
    c.close()
    return raus, quellen, echt


def abspielen(regel, punkte):
    """Spielt EINEN Verlauf ab. Rueckgabe: Ergebnis in % NACH Kosten."""
    hoch = 0.0
    for pnl, mfe in punkte:
        pnl = float(pnl or 0.0)
        hoch = max(hoch, pnl)
        if regel(pnl, hoch):
            return pnl - K_BASIS_PCT
    # Nie ausgeloest: am letzten bekannten Stand bewertet.
    return float(punkte[-1][0] or 0.0) - K_BASIS_PCT


def main():
    if not os.path.exists(DB):
        print(f"Datenbank fehlt: {DB}")
        return 1
    alle, quellen, echt = verlaeufe()
    print("\n" + "=" * 74)
    print("  SCHNEIDET DAS TRAILING DIE GEWINNE AB?")
    print("=" * 74)
    print(f"\n  Quellen in der Tabelle : {quellen}")
    print(f"  davon als 'echt' gewertet: {echt}")
    print(f"  verwertbare Verlaeufe    : {len(alle)}")
    if len(alle) < 10:
        print("\n  ZU WENIG FAELLE - kein Urteil moeglich.")
        return 1
    laengen = [len(p) for p in alle]
    print(f"  Messpunkte je Verlauf    : Median {st.median(laengen):.0f}, "
          f"laengster {max(laengen)}")
    print("\n  Jede Regel laeuft ueber DIESELBEN Verlaeufe - damit vergleicht")
    print("  jede Zeile dieselbe Zeitspanne mit sich selbst (Befund 79).")
    print(f"  Kosten je Runde abgezogen: {K_BASIS_PCT} % (K-BASIS)\n")

    print(f"  {'Regel':<26}{'Summe %':>10}{'je Trade':>10}"
          f"{'Treffer':>9}{'schlechtester':>15}")
    print("  " + "-" * 70)
    ergebnisse = {}
    for name, regel in REGELN:
        werte = [abspielen(regel, p) for p in alle]
        ergebnisse[name] = werte
        gew = sum(1 for w in werte if w > 0)
        print(f"  {name:<26}{sum(werte):>10.2f}{st.mean(werte):>10.3f}"
              f"{gew/len(werte)*100:>8.0f}%{min(werte):>15.2f}")

    ist = st.mean(ergebnisse["heute (Ist-Zustand)"])
    latte = st.mean(ergebnisse["HALTEN (Trivial-Latte)"])
    print("\n  " + "-" * 70)
    print(f"  Die Trivial-Latte 'HALTEN' bringt {latte:+.3f} % je Trade.")
    if latte >= max(st.mean(v) for k, v in ergebnisse.items()
                    if k != "HALTEN (Trivial-Latte)"):
        print("  KEINE Regel schlaegt sie. Dann ist keine Regel belegt -")
        print("  auch die heutige nicht.")
    print()
    beste = max(((k, st.mean(v)) for k, v in ergebnisse.items()
                 if k != "HALTEN (Trivial-Latte)"), key=lambda x: x[1])
    print(f"  Beste Regel: {beste[0]}  ({beste[1]:+.3f} % je Trade)")
    print(f"  Heute:       {ist:+.3f} % je Trade")
    unterschied = beste[1] - ist
    print(f"  Unterschied: {unterschied:+.3f} Punkte je Trade")
    if abs(unterschied) < 0.05:
        print("\n  Das ist kein Unterschied, sondern Rauschen. NICHT aendern.")
    elif unterschied <= 0:
        print("\n  Die heutige Regel ist die beste. NICHTS aendern.")
    else:
        print(f"\n  Auf {len(alle)} Verlaeufe hochgerechnet: "
              f"{unterschied*len(alle):+.1f} Punkte.")
        print("  ACHTUNG: gemessen an PAPIER-Verlaeufen in EINER Marktphase.")
    print("=" * 74 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
