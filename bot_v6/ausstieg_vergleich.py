#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  AUSSTIEG-VERGLEICH - welche Regel holt wirklich am meisten?
================================================================
Angelegt 20.08.2026 auf Svens Auftrag: "stelle sicher, dass nach
dem Freeze nach der bestmoeglichen Moeglichkeit geguckt wird,
damit nicht so viel hergeschenkt wird."

DIE FRAGE
---------
Gemessen ist, DASS zurueckgegeben wird: im Schnitt 1,24
Prozentpunkte je Verkauf (n=20 Tage, t=7,2 - kein Zufall,
Handbuch 4.95). Offen ist, WELCHE Regel es besser machen wuerde.

Bisher standen dafuer nur Meinungen zur Verfuegung. Dieses
Werkzeug rechnet stattdessen: es nimmt den aufgezeichneten
VERLAUF jeder geschlossenen Position und spielt jede
Ausstiegsregel darauf ab. Gleiche Kurse, gleiche Reihenfolge,
nur andere Regel.

DIE TRIVIAL-LATTE
-----------------
Jede Regel wird gegen "gar nichts tun" gehalten - halten bis zum
Ende der Aufzeichnung. CLAUDE.md Dauerregel 2: eine Regel ohne
diesen Vergleich gilt als ungemessen. Wer die Latte nicht
schlaegt, ist teure Beschaeftigung.

WAS ES NICHT KANN
-----------------
* Es kennt nur, was aufgezeichnet wurde - alle 5 Minuten ein
  Punkt. Was zwischen zwei Messungen passiert, sieht es nicht.
  Ein Stop, der zwischendurch gestreift wurde, fehlt.
* Es rechnet OHNE Kapitalkonkurrenz. In Wirklichkeit sind
  hoechstens drei Positionen offen; im Verlauf sind alle offen.
  Es beantwortet "welche Regel holt aus DIESEM Verlauf mehr",
  nicht "welches Depot haette mehr verdient".
* Schattenpositionen laufen bis MAX_TAGE=7 ohne Ausstieg. Genau
  das macht sie brauchbar: man sieht den vollen Weg, nicht nur
  den bis zum ersten Ausstieg.

AUFRUF
------
    python ausstieg_vergleich.py              alle geschlossenen
    python ausstieg_vergleich.py --echt       nur echte Positionen
    python ausstieg_vergleich.py --selbsttest Gegentest beide Richtungen

Reine Leseoperation. Aendert nichts, entscheidet nichts.
================================================================
"""
import os
import sys
import sqlite3
import argparse
import statistics as st

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
DB = os.path.join(HIER, "data_store", "positionsverlauf.db")
K = 0.505                    # K-BASIS je Runde, CLAUDE.md 8
MIN_PUNKTE = 12              # weniger ist kein Verlauf, sondern ein Schlaglicht
NL = chr(10)


# ----------------------------------------------------------------
#  Die Kandidaten
#
#  Jede Regel bekommt den Verlauf Punkt fuer Punkt und sagt, ob sie
#  JETZT aussteigen wuerde. Sie sieht dabei nur, was zu diesem
#  Zeitpunkt bekannt war - kein Blick nach vorn.
# ----------------------------------------------------------------
def _leiter_faktor(hoch, leiter):
    f = 1.0
    for schwelle, faktor in leiter:
        if hoch >= schwelle:
            f = faktor
    return f


def regel_bot(p, zustand, trail_ab=1.2, be_ab=1.0, be_puffer=0.35,
              stop=-2.5, leiter=None, trend_bonus=1.3):
    """Die Leiter des Bots, wie sie in risk/exit_rules.py steht.

    trail_ab / be_puffer sind Schrauben - genau die, an denen die
    vorbereiteten Patches drehen.
    """
    from risk.exit_rules import LEITER as ECHTE_LEITER
    leiter = leiter or ECHTE_LEITER
    pnl, hoch = p["pnl_pct"], p["hoch"]

    if pnl <= stop:
        return "Stop-Loss"
    if hoch >= be_ab and pnl <= be_puffer:
        return "Breakeven-Sperre"
    if hoch >= trail_ab:
        f = _leiter_faktor(hoch, leiter)
        if (p.get("regime") or "").upper().startswith("TREND"):
            f *= trend_bonus
        if hoch - pnl >= trail_ab * f:
            return "Trailing-Stop"
    return None


def regel_chandelier(p, zustand, mal=3.0, stop=-2.5):
    """Ausstieg, wenn der Kurs mehr als ATR x N unter das Hoch faellt.

    Der Lehrbuch-Klassiker. In veroeffentlichten Backtests schlaegt er
    feste Abstaende deutlich - gemessen an UNSEREN Daten aber bisher
    nicht (Handbuch 4.72): er ist fuer Tageskerzen gebaut, unser
    Median-Hoch liegt bei 1,43 %.
    """
    if p["pnl_pct"] <= stop:
        return "Stop-Loss"
    atr_pct = p.get("atr_pct")
    if not atr_pct:
        return None
    if p["hoch"] - p["pnl_pct"] >= mal * atr_pct:
        return "Chandelier"
    return None


def regel_fester_stop(p, zustand, ziel=2.0, stop=-2.5):
    """Verkauf bei festem Gewinnziel, sonst Stop. Die einfachste Regel."""
    if p["pnl_pct"] >= ziel:
        return "Ziel erreicht"
    if p["pnl_pct"] <= stop:
        return "Stop-Loss"
    return None


def regel_halten(p, zustand):
    """Die Trivial-Latte: nichts tun, bis die Aufzeichnung endet."""
    return None


KANDIDATEN = [
    ("Halten (Trivial-Latte)", regel_halten, {}),
    ("Bot heute", regel_bot, {}),
    ("Patch 00a: Puffer 0,55", regel_bot, {"be_puffer": 0.55}),
    ("Patch 45: Trail ab 1,57", regel_bot, {"trail_ab": 1.57}),
    ("00a + 45 zusammen", regel_bot, {"be_puffer": 0.55, "trail_ab": 1.57}),
    ("Breakeven ab 0,6 %", regel_bot, {"be_ab": 0.6, "be_puffer": 0.55}),
    ("Chandelier ATRx3", regel_chandelier, {}),
    ("Festes Ziel +2 %", regel_fester_stop, {}),
]


# ----------------------------------------------------------------
#  Mechanik
# ----------------------------------------------------------------
def verlaeufe(nur_echt=False, con=None):
    """Alle geschlossenen Positionen mit genug Messpunkten."""
    eigen = con is None
    if eigen:
        if not os.path.exists(DB):
            return []
        con = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro",
                              uri=True, timeout=10)
    wo = "WHERE geschlossen IS NOT NULL"
    if nur_echt:
        wo += " AND quelle='echt'"
    raus = []
    try:
        zeilen = con.execute(
            "SELECT pos_id, quelle, muenze, einstieg, schluss_grund "
            "FROM positionen " + wo).fetchall()
    except sqlite3.OperationalError:
        # Datenbank ohne die erwarteten Tabellen - das ist kein Absturz
        # wert. Wer nichts gesammelt hat, bekommt eine leere Liste und
        # oben die Erklaerung, warum.
        if eigen:
            con.close()
        return []
    for pid, quelle, muenze, einstieg, grund in zeilen:
        punkte = [dict(pnl_pct=r[0], hoch=r[1], tief=r[2], atr_pct=r[3],
                       regime=r[4], minuten=r[5])
                  for r in con.execute(
                      "SELECT pnl_pct, mfe_pct, mae_pct, atr_pct, regime, "
                      "minuten FROM verlauf WHERE pos_id=? ORDER BY ts_utc",
                      (pid,))
                  if r[0] is not None]
        if len(punkte) < MIN_PUNKTE:
            continue
        # hoch/tief absichern: manche Zeilen tragen sie nicht
        h = t = None
        for p in punkte:
            h = p["pnl_pct"] if h is None else max(h, p["pnl_pct"])
            t = p["pnl_pct"] if t is None else min(t, p["pnl_pct"])
            if p["hoch"] is None:
                p["hoch"] = h
            if p["tief"] is None:
                p["tief"] = t
        raus.append(dict(pos_id=pid, quelle=quelle, muenze=muenze,
                         grund=grund, punkte=punkte))
    if eigen:
        con.close()
    return raus


def abspielen(regel, punkte, **kw):
    """Wann haette diese Regel ausgestiegen, und mit welchem Ergebnis?

    Gibt (netto_pct, grund, minuten) zurueck. Loest die Regel nie aus,
    gilt der letzte Punkt der Aufzeichnung - das ist die ehrliche
    Entsprechung zu "hat bis zum Schluss gehalten".
    """
    zustand = {}
    for p in punkte:
        g = regel(p, zustand, **kw)
        if g:
            return p["pnl_pct"] - K, g, p["minuten"]
    letzter = punkte[-1]
    return letzter["pnl_pct"] - K, "bis zum Ende gehalten", letzter["minuten"]


def bericht(nur_echt=False):
    v = verlaeufe(nur_echt)
    print("=" * 88)
    print("  AUSSTIEG-VERGLEICH - dieselben Kurse, verschiedene Regeln")
    print("=" * 88)
    if not v:
        print(NL + "  Noch keine geschlossene Position mit mindestens "
              + str(MIN_PUNKTE) + " Messpunkten.")
        print("  Schattenpositionen schliessen nach 7 Tagen (MAX_TAGE),")
        print("  dann kommen 16 auf einmal. Stand ansehen:")
        print("      python positionsverlauf.py --status")
        return 1

    echt = sum(1 for x in v if x["quelle"] == "echt")
    print(NL + "  " + str(len(v)) + " Verlaeufe (" + str(echt) + " echt, "
          + str(len(v) - echt) + " Schatten), je mindestens "
          + str(MIN_PUNKTE) + " Messpunkte.")
    print("  Gerechnet nach Kosten: " + str(K) + " % je Runde." + NL)

    ergebnisse = {}
    ausgeloest = {}
    for name, regel, kw in KANDIDATEN:
        lauf = [abspielen(regel, x["punkte"], **kw) for x in v]
        ergebnisse[name] = [z[0] for z in lauf]
        ausgeloest[name] = sum(1 for z in lauf
                               if z[1] != "bis zum Ende gehalten")

    latte = ergebnisse["Halten (Trivial-Latte)"]
    latte_m = sum(latte) / len(latte)

    print("  " + "Regel".ljust(26) + "Mittel".rjust(9) + "Median".rjust(9)
          + "im Plus".rjust(9) + "greift".rjust(8) + "  gegen die Latte")
    print("  " + "-" * 84)
    for name, _r, _k in KANDIDATEN:
        w = ergebnisse[name]
        m = sum(w) / len(w)
        plus = 100.0 * sum(1 for x in w if x > 0) / len(w)
        d = m - latte_m
        urteil = ("Latte selbst" if name.startswith("Halten")
                  else (format(d, "+.3f") + " PP  "
                        + ("BESSER" if d > 0.05 else
                           "schlechter" if d < -0.05 else "gleichauf")))
        print("  " + name.ljust(26) + format(m, "+8.3f") + "%"
              + format(st.median(w), "+8.3f") + "%"
              + format(plus, "8.0f") + "%"
              + (str(ausgeloest[name]) + "/" + str(len(v))).rjust(8)
              + "  " + urteil)

    # [20.08.2026] Die wichtigste Einschraenkung gehoert UNTER die Tabelle,
    # nicht in eine Fussnote. Sonst liest man aus lauter Nullen heraus,
    # die Regeln seien gleichwertig - dabei hatten sie nur nichts zu tun.
    stumm = [n for n, _r, _k in KANDIDATEN
             if not n.startswith("Halten") and ausgeloest[n] == 0]
    if stumm:
        print(NL + "  " + str(len(stumm)) + " von " + str(len(KANDIDATEN) - 1)
              + " Regeln haben in KEINEM Verlauf ausgeloest:")
        print("    " + ", ".join(stumm))
        print("  Sie stehen deshalb gleichauf mit der Latte - nicht weil sie")
        print("  gleich gut sind, sondern weil es nichts zu entscheiden gab.")

    if echt:
        print(NL + "  WICHTIG zu den " + str(echt) + " ECHTEN Verlaeufen:")
        print("  Ihre Aufzeichnung endet, wenn der Bot verkauft. Eine Regel,")
        print("  die SPAETER ausgestiegen waere, laesst sich daran nicht")
        print("  messen - der Verlauf hoert vorher auf. Nur Schatten-")
        print("  positionen laufen bis MAX_TAGE=7 durch und erlauben den")
        print("  Vergleich in BEIDE Richtungen.")

    print(NL + "  Lesehilfe:")
    print("    * 'Mittel' ist der Netto-Erwartungswert je Position.")
    print("    * 'greift' sagt, in wie vielen Verlaeufen die Regel ueberhaupt")
    print("      ausgeloest hat. Steht dort 0, sagt die Zeile nichts aus.")
    print("    * Eine Regel taugt nur, wenn sie die Trivial-Latte schlaegt.")
    print("    * Unter 30 Verlaeufen traegt keine Zeile ein Urteil - der")
    print("      Unterschied waere auch bei zwei gleich guten Regeln so gross.")
    if len(v) < 30:
        print(NL + "  ACHTUNG: nur " + str(len(v)) + " Verlaeufe. Das ist eine")
        print("  Momentaufnahme, keine Entscheidungsgrundlage.")
    return 0


# ----------------------------------------------------------------
#  Gegentest in beide Richtungen
# ----------------------------------------------------------------
def selbsttest():
    fehler = 0
    print("=" * 74)
    print("SELBSTTEST - trifft jede Regel, was sie treffen soll?")
    print("=" * 74)

    def lauf(werte, hoch=None, regime="", atr=0.3):
        """Baut einen Verlauf aus reinen PnL-Werten."""
        punkte, h = [], None
        for i, x in enumerate(werte):
            h = x if h is None else max(h, x)
            punkte.append(dict(pnl_pct=x, hoch=hoch if hoch is not None else h,
                               tief=min(werte[:i + 1]), atr_pct=atr,
                               regime=regime, minuten=i * 5))
        return punkte

    print(NL + "  Erwartete Ausstiege:")
    faelle = [
        ("Stop bei -3 %", regel_bot, {}, [0.5, -1.0, -3.0, -1.0], "Stop-Loss"),
        ("Breakeven nach Hoch +1,5 %", regel_bot, {},
         [0.5, 1.5, 1.2, 0.3, -1.0], "Breakeven-Sperre"),
        ("Puffer 0,55 greift frueher", regel_bot, {"be_puffer": 0.55},
         [0.5, 1.5, 1.2, 0.5, -1.0], "Breakeven-Sperre"),
        ("Halten loest nie aus", regel_halten, {},
         [0.5, 3.0, -1.0], "bis zum Ende gehalten"),
        ("Festes Ziel +2 %", regel_fester_stop, {},
         [0.5, 1.0, 2.4], "Ziel erreicht"),
    ]
    for name, regel, kw, werte, soll in faelle:
        _n, grund, _m = abspielen(regel, lauf(werte), **kw)
        ok = grund == soll
        print("    " + ("OK  " if ok else "FEHL") + "  " + name.ljust(30)
              + "-> " + grund)
        if not ok:
            fehler += 1

    print(NL + "  Andere Richtung - loest sie aus, wo sie NICHT darf?")
    gegen = [
        ("kein Stop bei -1 %", regel_bot, {}, [0.2, -1.0, -0.5]),
        ("keine Sperre ohne Hoch ueber 1 %", regel_bot, {},
         [0.2, 0.8, 0.1, 0.0]),
        ("kein Ziel unter +2 %", regel_fester_stop, {}, [0.5, 1.9, 1.5]),
    ]
    for name, regel, kw, werte in gegen:
        _n, grund, _m = abspielen(regel, lauf(werte), **kw)
        ok = grund == "bis zum Ende gehalten"
        print("    " + ("OK  " if ok else "FEHL") + "  " + name.ljust(30)
              + "-> " + grund)
        if not ok:
            fehler += 1

    print(NL + "  Rechnet er die Kosten ab?")
    n, _g, _m = abspielen(regel_halten, lauf([0.0, 1.0]))
    ok = abs(n - (1.0 - K)) < 1e-9
    print("    " + ("OK  " if ok else "FEHL") + "  brutto +1,0 % -> netto "
          + format(n, "+.3f") + " % (erwartet " + format(1.0 - K, "+.3f") + ")")
    if not ok:
        fehler += 1

    print(NL + "  Faellt er sauber aus, wenn nichts da ist?")
    try:
        leer = verlaeufe(con=sqlite3.connect(":memory:"))
    except Exception as e:
        print("    FEHL  leere Datenbank -> " + type(e).__name__)
        fehler += 1
    else:
        print("    " + ("OK  " if leer == [] else "FEHL")
              + "  leere Datenbank -> " + str(len(leer)) + " Verlaeufe")
        if leer != []:
            fehler += 1

    print(NL + ("SELBSTTEST BESTANDEN" if not fehler
                else str(fehler) + " FEHLER"))
    return 1 if fehler else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Ausstiegsregeln vergleichen")
    p.add_argument("--echt", action="store_true",
                   help="nur echte Positionen, ohne Schatten")
    p.add_argument("--selbsttest", action="store_true")
    a = p.parse_args()
    sys.exit(selbsttest() if a.selbsttest else bericht(nur_echt=a.echt))
