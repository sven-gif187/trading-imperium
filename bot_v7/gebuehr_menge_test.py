# -*- coding: utf-8 -*-
"""Pruefung: Gebuehr in Coins darf die Positionsmenge nicht aufblaehen.

DER VORFALL, den dieser Test nachstellt
---------------------------------------
15.09.2026, 13:39 Uhr. Der Stop-Loss fuer ETH loeste aus - und der
Verkauf scheiterte:

    [MONITOR] ETH: STOP_LOSS TRIGGERED! (STOP-LOSS (-2.15% <= -2.1%))
    [ORDERS]  Error: bybit {"retCode":170131,
              "retMsg":"Insufficient balance."}

Die Position lief danach UNGESCHUETZT weiter, waehrend sie fiel.

URSACHE, auf zwoelf Stellen nachgerechnet:
    Register  0,0042      ETH
    Boerse    0,0041895   ETH
    0,0042 x 0,25 % = 0,0000105   <- exakt die Differenz

Bybit zieht die Spot-Kaufgebuehr IN DER GEKAUFTEN MUENZE ab. Der Bot
schrieb die volle Ausfuehrungsmenge an die Position - also immer
0,25 % mehr, als er besass. Jeder Verkauf der vollen Position musste
daran scheitern.

ZWEI REPARATUREN, ZWEI PRUEFUNGEN
---------------------------------
  1. URSACHE  - app.py zieht die Gebuehr von der Menge ab, wenn sie in
                der Basiswaehrung anfaellt
  2. SICHERUNG - execution/engine.py kappt die Verkaufsmenge auf den
                echten Bestand, wie es der Papierhandel laengst tut

Beide werden hier geprueft, und beide in beide Richtungen: Sie
muessen greifen, wo sie sollen - und NICHT greifen, wo die Gebuehr in
USDC anfaellt.

Aufruf:  python gebuehr_menge_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["TI_LOG_FILE"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data_store", "test.log")

BESTANDEN = []
DURCHGEFALLEN = []


def pruefe(name, bedingung, zusatz=""):
    if bedingung:
        BESTANDEN.append(name)
        print(f"    OK    {name}")
    else:
        DURCHGEFALLEN.append(name)
        print(f"    FEHLT {name}   {zusatz}")


print()
print("=" * 72)
print("  GEBUEHR IN COINS - der Vorfall vom 15.09. 13:39")
print("=" * 72)

# ====================================================================
# TEIL 1 - Das Feld muss es ueberhaupt geben
# ====================================================================
print("\n  1) Traegt ExecutionResult die Gebuehrenwaehrung?")
from core.events import ExecutionResult  # noqa: E402

r = ExecutionResult()
pruefe("ExecutionResult hat fee_currency", hasattr(r, "fee_currency"),
       "ohne das Feld ist fee eine Zahl ohne Einheit")
pruefe("Vorgabe ist leer (= Quote-Waehrung wie bisher)",
       getattr(r, "fee_currency", None) == "")


# ====================================================================
# TEIL 2 - Die Mengenrechnung, mit den ECHTEN Zahlen
# ====================================================================
print("\n  2) Mengenrechnung gegen die echten Zahlen vom 15.09.")


def netto_menge(filled_qty, fee, fee_currency, symbol):
    """Bildet die Rechnung aus app.py nach (nach dem Fill).

    Wer app.py aendert, muss diese Nachbildung mitaendern - deshalb
    steht die Fundstelle hier: app.py, direkt nach result.filled_qty.
    """
    menge = filled_qty
    try:
        ccy = str(fee_currency or "").upper()
        basis = symbol.split("/")[0].upper()
        if ccy and ccy == basis:
            f = float(fee or 0)
            if 0 < f < filled_qty:
                menge = filled_qty - f
    except Exception:
        pass
    return menge


# Der echte Fall: ETH-Kauf am 15.09. um 05:34
m = netto_menge(0.0042, 1.05e-05, "ETH", "ETH/USDC")
print(f"      gekauft 0.0042 ETH, Gebuehr 0.0000105 ETH")
print(f"      -> Position fuehrt {m:.8f}")
print(f"      -> auf der Boerse lagen 0.00418950")
pruefe("Menge stimmt mit dem Konto ueberein",
       abs(m - 0.0041895) < 1e-12, f"ist {m!r}")

# Gegenprobe: Gebuehr in USDC -> Menge bleibt unveraendert
m2 = netto_menge(0.0042, 0.0105, "USDC", "ETH/USDC")
print(f"\n      Gegenprobe: dieselbe Order, Gebuehr aber in USDC")
print(f"      -> Position fuehrt {m2:.8f}")
pruefe("Gebuehr in USDC aendert die Menge NICHT", abs(m2 - 0.0042) < 1e-12,
       "sonst wuerde die Menge doppelt gekuerzt")

# Randfaelle
pruefe("Gebuehr 0 laesst die Menge unveraendert",
       netto_menge(0.0042, 0, "ETH", "ETH/USDC") == 0.0042)
pruefe("fehlende Waehrung laesst die Menge unveraendert",
       netto_menge(0.0042, 1.05e-05, "", "ETH/USDC") == 0.0042)
pruefe("unsinnig hohe Gebuehr wird ignoriert",
       netto_menge(0.0042, 9.9, "ETH", "ETH/USDC") == 0.0042,
       "eine Gebuehr groesser als die Menge ist ein Datenfehler")


# ====================================================================
# TEIL 3 - Die Kappung beim Verkauf
# ====================================================================
print("\n  3) Kappung der Verkaufsmenge auf den echten Bestand")


def gekappt(gewuenscht, frei):
    """Bildet die Kappung aus execution/engine.py _menge() nach."""
    if frei > 0 and gewuenscht > frei:
        return frei
    return gewuenscht


# Genau der Fall von 13:39
g = gekappt(0.0042, 0.0041895)
print(f"      Register will 0.0042 verkaufen, Konto hat 0.0041895")
print(f"      -> Order ueber {g:.8f}")
pruefe("Verkaufsmenge wird auf den Bestand gekappt",
       abs(g - 0.0041895) < 1e-12,
       "ohne Kappung: Insufficient balance, Stop-Loss scheitert")

pruefe("kleinere Menge als Bestand bleibt unveraendert",
       gekappt(0.002, 0.0041895) == 0.002,
       "ein Teilverkauf darf nicht hochgesetzt werden")
pruefe("bei Bestand 0 wird nicht gekappt, sondern gemeldet",
       gekappt(0.0042, 0) == 0.0042,
       "dann greift die Fehlermeldung eine Ebene hoeher")

# Der Fall, der am 13:39 passiert waere: reicht die gekappte Menge
# noch fuer Bybits Mindestwert?
kurs = 2460.0
wert = 0.0041895 * kurs
print(f"\n      Wert der gekappten Menge: {wert:.2f} $"
      f"   (Bybit-Minimum ETH: 5 $)")
pruefe("gekappte Menge liegt ueber dem Boersen-Mindestwert", wert >= 5.0,
       f"nur {wert:.2f} $ - Verkauf waere trotzdem abgelehnt worden!")


# ====================================================================
print()
print("=" * 72)
print(f"  ERGEBNIS: {len(BESTANDEN)} bestanden, {len(DURCHGEFALLEN)} durchgefallen")
print("=" * 72)
if DURCHGEFALLEN:
    print("\n  DURCHGEFALLEN:")
    for n in DURCHGEFALLEN:
        print(f"    - {n}")
    print()
    sys.exit(1)
print("\n  Alles in Ordnung.\n")
sys.exit(0)
