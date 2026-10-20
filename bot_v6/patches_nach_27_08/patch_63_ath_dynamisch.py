#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  PATCH 63 - das Allzeithoch nicht mehr verdrahten
================================================================
NICHT VOR DEM 28.08.2026 ANWENDEN.

Es ist eine Verhaltensaenderung: die Zyklusphase steuert die
Positionsgroesse. Waehrend des Messfensters unzulaessig.

DAS PROBLEM (Befund 63)
-----------------------
agents/cycle_theory.py:28

    CURRENT_ATH = 109_114
    CURRENT_ATH_DATE = "2025-01-20"

Gegen drei Quellen geprueft (20.08.2026): das echte Hoch liegt bei
126.200 $ vom 06.10.2025 - 15,7 % hoeher und neun Monate juenger.

Folge: der Bot misst den Abstand zum Gipfel gegen einen Gipfel, der
laengst ueberboten wurde, und haelt den Baerenmarkt fuer flacher als
er ist.

    im Code      109.114 $  ->  -34,1 %  ->  EARLY_BEAR  (Groesse 0.6)
    tatsaechlich 126.200 $  ->  -43,0 %  ->  MID_BEAR    (Groesse 0.5)

Der Bot kauft also 20 % groessere Positionen, als die Lage hergibt.

DIE REPARATUR
-------------
Das Hoch wird nicht mehr eingetragen, sondern geholt: hoechster
Wochenkerzen-Hoechstkurs der letzten Jahre, einmal je Bot-Start
ermittelt und danach zwischengespeichert.

    > Eine Zahl, die man von Hand pflegen muss, veraltet.
    > Genau derselbe Fehler wie bei den Epochen im Cockpit (4.92)
    > und der Muenzzahl an sechs Stellen (4.93).

Faellt der Abruf aus, gilt der bisher hoechste bekannte Wert - nie
ein zu NIEDRIGER, denn ein zu niedriges Hoch macht den Baerenmarkt
kuenstlich flach und die Positionen zu gross. Im Zweifel lieber zu
vorsichtig.

ANWENDEN
--------
    python patches_nach_27_08/patch_63_ath_dynamisch.py --pruefen
    python patches_nach_27_08/patch_63_ath_dynamisch.py --anwenden

Danach: Epochengrenze in config_epochs.json eintragen (E8), sonst
sind die Vorher-Nachher-Vergleiche wertlos.
================================================================
"""
import os
import sys
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(HIER, "agents", "cycle_theory.py")

ANKER = '''CURRENT_ATH = 109_114
CURRENT_ATH_DATE = "2025-01-20"'''

ERSATZ = '''# [PATCH 63, ab 28.08.2026] Das Allzeithoch wird geholt, nicht gepflegt.
#
# Vorher stand hier fest 109_114 (Stand 20.01.2025). Am 20.08.2026 lag das
# echte Hoch bei 126.200 $ (06.10.2025, geprueft gegen Binance USDT, Binance
# USDC und Bybit). Der Bot hielt den Baerenmarkt dadurch fuer 9 Prozentpunkte
# flacher als er war - EARLY_BEAR statt MID_BEAR, und damit 20 % groessere
# Positionen (get_position_multiplier: 0.6 statt 0.5).
#
# Rueckfall ist bewusst der HOECHSTE bekannte Wert, nie ein niedrigerer:
# ein zu niedriges Hoch macht den Baerenmarkt kuenstlich flach.
_ATH_RUECKFALL = 126_200
_ATH_PUFFER = {"wert": None, "datum": None}


def _ath_ermitteln():
    """Hoechster Kurs, den die Boerse kennt. Einmal je Bot-Start."""
    if _ATH_PUFFER["wert"]:
        return _ATH_PUFFER["wert"], _ATH_PUFFER["datum"]
    hoch, datum = _ATH_RUECKFALL, "Rueckfall"
    try:
        import ccxt
        from datetime import datetime, timezone
        ex = ccxt.binance({"enableRateLimit": True})
        k = ex.fetch_ohlcv("BTC/USDT", "1w", limit=400)
        if k:
            h = max(x[2] for x in k)
            if h > hoch:                     # nie nach unten korrigieren
                w = [x for x in k if x[2] == h][0][0]
                hoch = h
                datum = datetime.fromtimestamp(
                    w / 1000, timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    _ATH_PUFFER["wert"], _ATH_PUFFER["datum"] = hoch, datum
    return hoch, datum


CURRENT_ATH, CURRENT_ATH_DATE = _ath_ermitteln()'''


def pruefen():
    print("=" * 70)
    print("PATCH 63 - Pruefung vor dem Anwenden")
    print("=" * 70)
    fehler = 0
    if not os.path.exists(ZIEL):
        print("  FEHLT: " + ZIEL)
        return 1
    t = open(ZIEL, encoding="utf-8").read()

    n = t.count(ANKER)
    print("\n  Anker genau einmal vorhanden : "
          + ("ja" if n == 1 else "NEIN (" + str(n) + "x)"))
    if n != 1:
        fehler += 1
    print("  Patch schon angewendet       : "
          + ("JA - nichts zu tun" if "_ath_ermitteln" in t else "nein"))
    if "_ath_ermitteln" in t:
        return 1

    print("\n  Gegenprobe gegen die Boerse:")
    try:
        import ccxt
        from datetime import datetime, timezone
        k = ccxt.binance({"enableRateLimit": True}).fetch_ohlcv(
            "BTC/USDT", "1w", limit=400)
        h = max(x[2] for x in k)
        w = [x for x in k if x[2] == h][0][0]
        print("    echtes Hoch : " + format(h, ",.0f") + " $ ("
              + datetime.fromtimestamp(w / 1000, timezone.utc)
              .strftime("%d.%m.%Y") + ")")
        print("    im Code     : 109,114 $ (20.01.2025)")
        print("    Unterschied : " + format((h / 109114 - 1) * 100, "+.1f") + " %")
    except Exception as e:
        print("    Abruf fehlgeschlagen: " + str(e)[:60])
        fehler += 1

    print("\n  " + ("BEREIT - mit --anwenden einspielen" if not fehler
                    else str(fehler) + " Problem(e), NICHT anwenden"))
    return 1 if fehler else 0


def anwenden():
    if pruefen():
        return 1
    t = open(ZIEL, encoding="utf-8").read()
    sicherung = ZIEL + ".bak_vor_patch63"
    open(sicherung, "w", encoding="utf-8").write(t)
    open(ZIEL, "w", encoding="utf-8").write(t.replace(ANKER, ERSATZ, 1))
    print("\n  Angewendet. Sicherung: " + os.path.basename(sicherung))
    print("  JETZT: Epochengrenze E8 in config_epochs.json eintragen.")
    print("  DANN:  Bot neu starten, damit es wirkt.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pruefen", action="store_true")
    p.add_argument("--anwenden", action="store_true")
    a = p.parse_args()
    sys.exit(anwenden() if a.anwenden else pruefen())
