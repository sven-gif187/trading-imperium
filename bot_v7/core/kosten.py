# -*- coding: utf-8 -*-
"""core/kosten.py - die EINE Stelle, an der die Handelskosten stehen.

WOZU DIESE DATEI EXISTIERT
--------------------------
Am 13.09.2026 standen in neun Dateien neun eigene Kostenzahlen. Vier davon
waren falsch - sie trugen noch die alte Annahme **0,32 %** je Runde aus der
Zeit vor dem Wechsel auf Bybit EU. Der richtige Wert ist seit dem 11.08.
**0,505 %**.

Das ist kein Schreibfehler, sondern eine Bauart: Wer eine Zahl an neun
Stellen pflegen muss, pflegt sie irgendwann an acht.

> **Eine zweite Wahrheit geht irgendwann falsch aus.** Genau dasselbe
> Muster steht in `.claude/hooks/DAUERREGELN.txt` ueber das Messfenster-
> Datum (Befund 90): ein festes Datum in einer zweiten Datei meldete am
> 30.08. den Freeze fuer beendet, obwohl er laengst verlaengert war.

WORAUS SICH DIE ZAHL ZUSAMMENSETZT
----------------------------------
    Kauf   Taker  0,25 %      Bybit EU Spot, MiCA-lizenziert
    Verkauf Taker 0,25 %
    Schlupf       0,005 %     gemessen am Orderbuch, Median ueber BTC/ETH/SOL
    ------------------------
    K_BASIS_PCT   0,505 %     je vollstaendiger Runde

**NIE aus ccxt holen.** `ccxt.bybit().fees` meldet 0,01 % Maker und 0,075 %
Taker - fuer den EU-Spotmarkt schlicht falsch. Eine zu guenstige Annahme
laesst jede Auswertung besser aussehen als die Wirklichkeit, und zwar still.

Quelle: Bybit Help-Center "Bybit Spot Fees Explained", Stand 08.03.2026,
vom Eigentuemer selbst geprueft. Siehe `backtest/fees.py:24` und
`docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v1.1.md`.

WER SICH HIER BEDIENT - und wer bewusst nicht
----------------------------------------------
Umgestellt am 13.09.2026 (alle vier rechnen nur, sie handeln nicht):

    datenexport.py                 Auswertung
    features/regime_adaptiv.py     misst nur, AKTIV = False
    risk/exit_rules_schatten.py    Schattenregel, verkauft nichts
    chartanalyse_backtest.py       Auswertung

**Bewusst NICHT umgestellt:** `risk/exit_rules.py`. Dort steht seit dem
12.09. `K_BASIS_PCT = 0.505` als eigene Zeile (Patch 00a). Diese Datei
liegt im HANDELSPFAD - sie bestimmt Breakeven-Sperre und Trailing-Schwelle.
Ein zusaetzlicher Import waere dort ein neuer Weg, auf dem der Start
scheitern kann, und das Risiko steht in keinem Verhaeltnis zum Gewinn.
Ihre Zahl wird stattdessen von `kosten_pruefen()` gegengelesen.

    python core/kosten.py      zeigt alle Fundstellen und prueft sie
"""
import io
import os
import re

# ====================================================================
# DIE ZAHL. Alles andere in dieser Datei erklaert oder prueft sie nur.
# ====================================================================
# [KOSTENLATTE BITVAVO 14.10.2026] Zielboerse Bitvavo USDC-Maerkte (Kategorie B), vorher Bybit EU 0,25.
TAKER_PCT = 0.05            # je Seite, Bitvavo USDC
# [EINHEITSGEBUEHR 05.10.2026] Bybit EU: Einheitsgebuehr, Maker = Taker (vorher 0,10).
MAKER_PCT = 0.05            # je Seite, Warte-Auftrag (Limit-Order), Bitvavo: Maker = Taker
SCHLUPF_PCT = 0.050         # je Runde, Bitvavo-Stichprobe 14.10. (0.043, gerundet)

K_BASIS_PCT = 0.150         # zwei Taker-Seiten plus Schlupf (Bitvavo USDC, vorher 0.505)

# Eine Runde ueber Warte-Auftraege: Maker beim Kauf, Taker beim Verkauf.
# Verkaeufe bleiben immer Sofort-Auftraege - ein Stop-Loss, der als
# Limit-Order liegen bleibt, waere stilles Scheitern (Handbuch 4.9).
K_WARTE_PCT = round(MAKER_PCT + TAKER_PCT + SCHLUPF_PCT, 3)   # 0,355 %

# Die alte, falsche Annahme. Steht hier, damit die Pruefung unten sie
# wiedererkennt - nicht, damit jemand sie benutzt.
_VERALTET = (0.32, 0.30, 0.20, 0.50, 0.10)


def kosten_pruefen():
    """Sucht Kostenzahlen im Projekt und meldet veraltete.

    Gibt (gefunden, veraltet) zurueck, je Liste von (datei, zeile, wert).
    """
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    muster = re.compile(
        r"^\s*(KOSTEN_PCT|K_BASIS|K_BASIS_PCT|KOSTEN_RUNDE)\s*=\s*([\d.]+)")
    ueberspringen = ("archiv", "docs", "__pycache__", ".git",
                     "patches_nach_27_08", "backtest")
    gefunden, veraltet = [], []
    for ordner, unter, dateien in os.walk(wurzel):
        unter[:] = [u for u in unter if u not in ueberspringen]
        for name in dateien:
            if not name.endswith(".py") or name == "kosten.py":
                continue
            pfad = os.path.join(ordner, name)
            try:
                text = io.open(pfad, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for nr, zeile in enumerate(text.split("\n"), 1):
                m = muster.match(zeile)
                if not m:
                    continue
                wert = float(m.group(2))
                kurz = os.path.relpath(pfad, wurzel)
                gefunden.append((kurz, nr, wert))
                if abs(wert - K_BASIS_PCT) > 1e-9:
                    veraltet.append((kurz, nr, wert))
    return gefunden, veraltet


if __name__ == "__main__":
    print("=" * 74)
    print("  HANDELSKOSTEN - die eine Quelle, und wer sie noch nicht nutzt")
    print("=" * 74)
    print()
    print("  Taker je Seite    %.3f %%" % TAKER_PCT)
    print("  Maker je Seite    %.3f %%" % MAKER_PCT)
    print("  Schlupf je Runde  %.3f %%" % SCHLUPF_PCT)
    print("  " + "-" * 34)
    print("  K_BASIS_PCT       %.3f %%   (Sofortkauf und -verkauf)" % K_BASIS_PCT)
    print("  K_WARTE_PCT       %.3f %%   (Warte-Auftrag beim Kauf)" % K_WARTE_PCT)
    print()

    gefunden, veraltet = kosten_pruefen()
    print("  Eigene Kostenzahlen im Projekt: %d" % len(gefunden))
    print()
    print("  %-44s %6s %8s" % ("Datei", "Zeile", "Wert"))
    print("  " + "-" * 62)
    for datei, nr, wert in sorted(gefunden):
        marke = "" if abs(wert - K_BASIS_PCT) < 1e-9 else "   <-- veraltet"
        print("  %-44s %6d %8.3f%s" % (datei, nr, wert, marke))

    print()
    if veraltet:
        print("  %d Datei(en) rechnen noch mit einer anderen Zahl." % len(veraltet))
        print("  Jede davon macht ihre Auswertung falsch - und zwar still.")
    else:
        print("  Alle gefundenen Zahlen stimmen mit K_BASIS_PCT ueberein.")
    print()
