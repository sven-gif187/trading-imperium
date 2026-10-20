# -*- coding: utf-8 -*-
# [CLEANUP-KEEP] Block-A-Audit: Reichweite der Kapitalerschoepfung, 03.08.2026.
"""
BLOCK A - Entwertet die Kapitalerschoepfung des Harness auch die
Gate-Ergebnisse?

KEIN TRIAL. Read-only. Es wird keine Handelsregel geprueft, sondern die
Abdeckung bereits gelaufener Messungen beschrieben.

FRAGESTELLUNG
-------------
Am 03.08. wurde belegt: der Harness handelt in "Jahr 2" nur vom
26.09.2025 bis 15.02.2026, danach reicht das Eigenkapital nicht mehr
(49,44 $ gegen 50 $ Mindestbedarf bei groesse_pct=20 und der
10-$-Schwelle in ausstieg_backtest.py:198).

Die Behauptung "E2/E5/G2 und beide Gate-Batterien sind nicht betroffen,
weil sie Relativgroessen rechnen" war UNBELEGT - und, wie dieses Skript
zeigt, in der Begruendung falsch. Der relevante Mechanismus ist nicht
Dollar-gegen-Prozent, sondern die AUSWAHL: wenn der Harness aufhoert zu
handeln, existieren die Eintrittsereignisse nicht mehr, auf denen
E2/E5/G2 rechnen.

GEMESSEN WIRD
-------------
1. Abdeckung je Jahr: erster/letzter Eintritt, gehandelte Tage,
   Anteil am Nominaljahr, Kapitalverlauf.
2. Wann faellt das Eigenkapital unter die 50-$-Schwelle?
3. F3-Neurechnung: BTC-Halten ueber das NOMINALE Jahr gegen
   BTC-Halten ueber den TATSAECHLICH gehandelten Zeitraum.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from harness_ext import LaufMess, NEUE_LEITER, lade_jahr, TAG_MS

START = 500.0
GROESSE_PCT = 20.0
MIN_BETRAG = 10.0


def tag(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def main():
    print("=" * 100)
    print(" BLOCK A - REICHWEITE DER KAPITALERSCHOEPFUNG")
    print(" Read-only, kein Trial. Stand 03.08.2026")
    print("=" * 100)

    ergebnis = {}
    for jahr, marke in (("Jahr 2", ""), ("Jahr 1", "_v1")):
        daten, fg = lade_jahr(marke)
        L = LaufMess(NEUE_LEITER, "auditA", breakeven=True, stop_loss_pct=2.5)
        L.laufe(daten, fg)
        tr = sorted(L.trades, key=lambda t: t["eintritt"])

        alle_tage = sorted({k[0] // TAG_MS for ks in daten.values() for k in ks})
        nominal = len(alle_tage)
        e_erst, e_letzt = tr[0]["eintritt"] // TAG_MS, tr[-1]["eintritt"] // TAG_MS
        gehandelt = e_letzt - e_erst + 1
        e_tage = len({t["eintritt"] // TAG_MS for t in tr})

        # Kapitalverlauf: kumulierte P&L in Eintrittsreihenfolge
        eq, unter50 = START, None
        for t in sorted(tr, key=lambda x: x["zeit"]):
            eq += t["pnl"]
            if eq < START * MIN_BETRAG / GROESSE_PCT * 1.0 and unter50 is None:
                unter50 = t["zeit"]
        schwelle_eq = MIN_BETRAG / (GROESSE_PCT / 100.0)

        # BTC-Halten: nominal gegen tatsaechlich gehandelt
        btc = {k[0] // TAG_MS: k[4] for k in sorted(daten["BTC/USDC"])}
        def halten(a, e):
            pa = next((btc[x] for x in range(a, e + 1) if x in btc), None)
            pe = next((btc[x] for x in range(e, a, -1) if x in btc), None)
            return START * (pe / pa - 1) if pa and pe else None
        h_nom = halten(alle_tage[0], alle_tage[-1])
        h_ist = halten(e_erst, e_letzt)

        ergebnis[jahr] = dict(nominal=nominal, gehandelt=gehandelt,
                              e_tage=e_tage, n=len(tr),
                              erst=e_erst, letzt=e_letzt,
                              pnl=sum(t["pnl"] for t in tr),
                              bar=L.bar, h_nom=h_nom, h_ist=h_ist,
                              unter50=unter50, schwelle=schwelle_eq)

        print(f"\n  {jahr}")
        print(f"    Nominalzeitraum      {nominal} Tage "
              f"({tag(alle_tage[0]*TAG_MS)} .. {tag(alle_tage[-1]*TAG_MS)})")
        print(f"    Erster Eintritt      {tag(e_erst*TAG_MS)}")
        print(f"    LETZTER Eintritt     {tag(e_letzt*TAG_MS)}")
        print(f"    Gehandelte Spanne    {gehandelt} Tage "
              f"= {gehandelt/nominal*100:.1f} % des Nominaljahres")
        print(f"    Tage MIT Eintritt    {e_tage} "
              f"({e_tage/nominal*100:.1f} % der Kalendertage)")
        print(f"    Trades               {len(tr)}")
        print(f"    Netto-P&L            {sum(t['pnl'] for t in tr):+.2f} $")
        print(f"    Endkapital (bar)     {L.bar:.2f} $  "
              f"(Handelsschwelle: {schwelle_eq:.2f} $)")
        if unter50:
            print(f"    Eigenkapital erstmals unter {schwelle_eq:.0f} $: "
                  f"{tag(unter50)}")
        else:
            print(f"    Eigenkapital blieb ueber {schwelle_eq:.0f} $")
        print(f"    BTC-Halten NOMINAL   {h_nom:+.2f} $")
        print(f"    BTC-Halten IST-SPANNE{h_ist:+.2f} $  "
              f"(nur {tag(e_erst*TAG_MS)}..{tag(e_letzt*TAG_MS)})")
        sys.stdout.flush()

    # ---------------- A4: F3-Neurechnung ----------------
    print("\n" + "=" * 100)
    print(" A4 - F3-BENCHMARK: nominal gegen tatsaechlich gehandelt")
    print("=" * 100)
    print(f"\n    {'Jahr':<8s} {'Bot P&L':>10s} {'Halten NOM':>12s} "
          f"{'Diff NOM':>10s} {'Halten IST':>12s} {'Diff IST':>10s}")
    print("    " + "-" * 68)
    for jahr in ("Jahr 2", "Jahr 1"):
        e = ergebnis[jahr]
        print(f"    {jahr:<8s} {e['pnl']:+9.2f}$ {e['h_nom']:+11.2f}$ "
              f"{e['pnl']-e['h_nom']:+9.2f}$ {e['h_ist']:+11.2f}$ "
              f"{e['pnl']-e['h_ist']:+9.2f}$")
    print("\n    'Diff NOM' ist die bisher berichtete F3-Zahl (Bot minus")
    print("    Halten ueber das volle Jahr). 'Diff IST' vergleicht nur den")
    print("    Zeitraum, in dem der Bot ueberhaupt handelte.")
    print("\n    ACHTUNG: Auch 'Diff IST' ist keine saubere Korrektur. Der Bot")
    print("    haelt in seiner Spanne nicht durchgehend Positionen, und sein")
    print("    Einsatz schrumpft mit dem Kapital. Eine belastbare Benchmark")
    print("    braucht konstanten Einsatz - das bricht den Kontrollanker.")
    print("    Beide Zahlen sind daher Naeherungen, keine Ersatzmessung.")

    # ---------------- A2: Datenbasis der Gate-Batterien ----------------
    print("\n" + "=" * 100)
    print(" A2 - DATENBASIS DER GATE-BATTERIEN (Gegenprobe)")
    print("=" * 100)
    print("""
    Die Gate-Batterien T-016..T-033 laufen auf einer ANDEREN Datenbasis:
      Harness (E1/E2/E5/G2):  data_store/backtest/*_15m.csv, 2024-07..2026-07
      Gate-Batterien:         docs/forschungsprogramm_2026-07/daten/klines_1d/,
                              2017-08..2023-12
    Zeitliche Ueberschneidung: KEINE.

    Zusaetzlich kennen die Gate-Skripte keinen Kapitalpfad. Belege:
      batterie_h1.py netto_evs():   (exit/entry - 1)*100 - c
        -> reine Prozentrechnung je Runde, kein Eigenkapital, keine
           Positionsgroesse, keine Mindestbetragsschwelle.
      batterie_h1.py runden_aus_signal(): erzeugt Runden allein aus der
        Signalserie; es gibt keine Bedingung, die eine Runde wegen
        fehlenden Kapitals unterdruecken koennte.
      batterie_h5.py und neubewertung_v12.py nutzen dieselben Funktionen.

    Eine Kapitalerschoepfung ist in dieser Konstruktion nicht moeglich.
    """)
    return 0


if __name__ == "__main__":
    sys.exit(main())
