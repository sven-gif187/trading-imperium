# -*- coding: utf-8 -*-
"""config_wachposten_test.py - schlaegt der Wachposten an, wenn er soll?

WOZU
----
Befund 97: Am 08.09.2026 setzte ein einziger Speichervorgang in der
Einstellungsmaske zwoelf Werte gleichzeitig auf ihre Vorgabe zurueck -
`trading.coins` von 3 auf 12 Muenzen, `stop_loss_pct` von 2,5 auf 2,0,
`initial_paper_balance` von 500 auf 300 und weitere. Wiederhergestellt
werden musste aus einem git-Stand vom 12.08., also vier Wochen alt.

**Die Ursache ist OFFEN.** Am Code nachgesehen gibt es keine Stelle, die
eine frische `AppConfig()` baut und speichert. Deshalb steht in
`config/settings.py` kein Fallback, der den Fehler wegbuegelt, sondern
zwei Dinge, die nichts verstecken: eine Sicherung vor jedem Schreiben und
ein lauter Hinweis bei Massen-Rueckfaellen.

Ein Wachposten ist nur so gut wie sein Gegentest. Dieser hier prueft
BEIDE Richtungen:

  1  Normales Speichern            legt eine Sicherung an
  2  Einzelne Aenderung            KEIN Alarm (sonst schreit er immer)
  3  Aenderung auf einen anderen
     Wert als die Vorgabe          KEIN Alarm (das ist eine Einstellung)
  4  Zwoelf Rueckfaelle wie am
     08.09.                        ALARM
  5  Ganzer Block verschwunden     erkannt (das war Befund 31)
  6  Sicherungen rollieren         nicht mehr als vorgesehen

AENDERT NICHTS. Arbeitet auf einer Kopie im Temp-Ordner, fasst die echte
data_store/config.json nicht an.

    python config_wachposten_test.py
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config.settings as einst                            # noqa: E402
from config.settings import AppConfig                      # noqa: E402
from dataclasses import asdict                             # noqa: E402


class Pruefung:
    def __init__(self):
        self.ok = 0
        self.fehler = []

    def sage(self, nr, was, bedingung, zusatz=""):
        if bedingung:
            self.ok += 1
            print("  %d  %-44s ok   %s" % (nr, was, zusatz))
        else:
            self.fehler.append((nr, was, zusatz))
            print("  %d  %-44s FEHL %s" % (nr, was, zusatz))


def _sicherungen(ordner):
    return sorted(f for f in os.listdir(ordner)
                  if f.startswith("config.json.sicherung_"))


def main():
    print("=" * 78)
    print("  CONFIG-WACHPOSTEN - schlaegt er an, wenn er soll? (Befund 97)")
    print("=" * 78)
    print()

    ordner = tempfile.mkdtemp(prefix="config_wacht_")
    echte_datei = einst.CONFIG_FILE
    p = Pruefung()
    try:
        einst.CONFIG_FILE = os.path.join(ordner, "config.json")

        # Ein Ausgangsstand, der sich in mehreren Feldern von der Vorgabe
        # unterscheidet - so wie Svens echte Datei.
        cfg = AppConfig()
        cfg.risk.stop_loss_pct = 2.5
        cfg.risk.take_profit_pct = 0.0
        cfg.risk.trailing_stop_pct = 1.0
        cfg.trading.initial_paper_balance = 500.0
        cfg.trading.position_size_pct = 30.0
        cfg.telegram.enabled = True
        cfg.save()

        p.sage(1, "Erstes Speichern legt die Datei an",
               os.path.exists(einst.CONFIG_FILE), "")

        # --- 2  Eine einzelne Aenderung -> kein Alarm ------------------
        cfg.risk.stop_loss_pct = 2.0          # das IST die Vorgabe
        verdacht = cfg._vor_dem_speichern_sichern(asdict(cfg))
        p.sage(2, "Eine Aenderung auf die Vorgabe",
               len(verdacht) == 1 and len(verdacht) < cfg.RUECKFALL_ALARM,
               "%d verdaechtig, Alarm ab %d" % (len(verdacht), cfg.RUECKFALL_ALARM))

        # --- 3  Aenderung auf einen ANDEREN Wert -> gar nichts ---------
        cfg2 = AppConfig()
        cfg2.risk.stop_loss_pct = 2.5
        cfg2.save()
        cfg2.risk.stop_loss_pct = 3.7          # weder alt noch Vorgabe
        verdacht = cfg2._vor_dem_speichern_sichern(asdict(cfg2))
        p.sage(3, "Aenderung auf einen eigenen Wert",
               len(verdacht) == 0,
               "%d verdaechtig - eine Einstellung ist kein Unfall" % len(verdacht))

        # --- 4  Der Fall vom 08.09.: alles auf Vorgabe -----------------
        cfg3 = AppConfig()
        cfg3.risk.stop_loss_pct = 2.5
        cfg3.risk.take_profit_pct = 0.0
        cfg3.risk.trailing_stop_pct = 1.0
        cfg3.risk.max_daily_loss_pct = 6.0
        cfg3.trading.initial_paper_balance = 500.0
        cfg3.trading.position_size_pct = 30.0
        cfg3.trading.max_trades = 3
        cfg3.telegram.enabled = True
        cfg3.save()
        frisch = asdict(AppConfig())           # alles auf Vorgabe - der Unfall
        verdacht = cfg3._vor_dem_speichern_sichern(frisch)
        p.sage(4, "Viele Rueckfaelle gleichzeitig (08.09.)",
               len(verdacht) >= cfg3.RUECKFALL_ALARM,
               "%d verdaechtig, Alarm ab %d" % (len(verdacht), cfg3.RUECKFALL_ALARM))

        # --- 5  Ganzer Block verschwindet (Befund 31) ------------------
        with open(einst.CONFIG_FILE, encoding="utf-8") as f:
            d = json.load(f)
        d["regel_modi"] = {"trend_exit": "SHADOW"}
        with open(einst.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f)
        ohne = asdict(cfg3)                    # kennt regel_modi nicht
        verdacht = cfg3._vor_dem_speichern_sichern(ohne)
        gefunden = any("regel_modi" in v for v in verdacht)
        p.sage(5, "Ganzer Block verschwindet (Befund 31)",
               gefunden, "erkannt" if gefunden else "NICHT erkannt")

        # --- 6  Sicherungen rollieren ---------------------------------
        for _ in range(cfg3.SICHERUNGEN_BEHALTEN + 6):
            cfg3._vor_dem_speichern_sichern(asdict(cfg3))
        n = len(_sicherungen(ordner))
        p.sage(6, "Sicherungen rollieren",
               n <= cfg3.SICHERUNGEN_BEHALTEN + 1,
               "%d Stueck, behalten werden %d" % (n, cfg3.SICHERUNGEN_BEHALTEN))

        # --- 7  Ist der alte Stand in der Sicherung wirklich drin? ----
        letzte = os.path.join(ordner, _sicherungen(ordner)[-1])
        with open(letzte, encoding="utf-8") as f:
            gesichert = json.load(f)
        p.sage(7, "Die Sicherung enthaelt den alten Stand",
               isinstance(gesichert, dict) and "risk" in gesichert,
               os.path.basename(letzte))

        # --- Gegentest -------------------------------------------------
        print()
        print("  Gegentest - wuerde ein blinder Wachposten durchfallen?")
        print("    Einer, der IMMER Alarm gibt, haette Pruefung 2 und 3")
        print("    nicht bestanden (dort darf er nicht anschlagen).")
        print("    Einer, der NIE Alarm gibt, waere an 4 und 5 gescheitert.")
        print("    Beide Richtungen sind also abgedeckt.")

    finally:
        einst.CONFIG_FILE = echte_datei
        shutil.rmtree(ordner, ignore_errors=True)

    print()
    print("-" * 78)
    if p.fehler:
        print("  DURCHGEFALLEN: %d von %d" % (len(p.fehler), p.ok + len(p.fehler)))
        for nr, was, z in p.fehler:
            print("    %d  %s  %s" % (nr, was, z))
        return 1
    print("  BESTANDEN: alle %d Pruefungen." % p.ok)
    print()
    print("  Was das NICHT tut: die Ursache beheben. Sie ist OFFEN - im")
    print("  ganzen Projekt baut keine Stelle eine frische AppConfig() und")
    print("  speichert sie. Der Wachposten faengt den Schaden und macht ihn")
    print("  sichtbar; gefunden werden muss die Ursache trotzdem.")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
