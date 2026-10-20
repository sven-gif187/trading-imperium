# -*- coding: utf-8 -*-
"""Schaltet das Fraktal-Tor scharf - und setzt die Epochengrenze dazu.

WAS DIESES SKRIPT AENDERT
-------------------------
    data_store/config.json    trading.fraktal_tor_aktiv      -> true
                              trading.fraktal_tor_nur_messen -> false
    config_epochs.json        neue Epoche L2_fraktal_tor

Mehr nicht. Es startet nichts, handelt nicht und fasst keine
Zugangsdaten an. Von beiden Dateien wird vorher eine Sicherung gelegt.

WARUM DIE EPOCHENGRENZE PFLICHT IST
-----------------------------------
CLAUDE.md Abschnitt 5: Jede Verhaltensaenderung braucht eine
Epochengrenze, sonst sind alle Vorher-Nachher-Vergleiche wertlos. Das
Tor kann Kaeufe verhindern - es aendert das Verhalten. Ohne die Grenze
liefen die Zahlen von vorher und nachher in denselben Topf.

WAS VORHER GEMESSEN WURDE
-------------------------
    fraktal_rueckblick.py   4 von 4 Kaeufen vom 14.09. abgelehnt
    fraktal_oeffnung.py     Tor in 27,2 % der Stunden offen
                            (BTC 23,1 %, ETH 33,8 %, SOL 24,9 %)
    fraktal_tor_test.py     21 von 21 Pruefungen bestanden

Aufruf:  FRAKTAL_TOR_EINSCHALTEN.bat  (Doppelklick)
"""
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONFIG = os.path.join("data_store", "config.json")
EPOCHEN = "config_epochs.json"


def sichern(pfad):
    stempel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ziel = f"{pfad}.sicherung_{stempel}"
    shutil.copy(pfad, ziel)
    return ziel


def main():
    print()
    print("=" * 72)
    print("  FRAKTAL-TOR SCHARF STELLEN")
    print("=" * 72)
    print()

    if not os.path.exists(CONFIG):
        print(f"  FEHLER: {CONFIG} nicht gefunden.")
        print("  Laeuft dieses Skript im richtigen Ordner?")
        return 1

    # ---------------- Warnung, wenn der Bot laeuft ----------------
    # Eine Aenderung an config.json waehrend des Betriebs kann vom
    # laufenden Bot ueberschrieben werden - Befund 97 (ein
    # Speichervorgang setzte zwoelf Einstellungen zurueck).
    try:
        import psutil
        hier = os.path.dirname(os.path.abspath(__file__))
        laeuft = []
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                cl = " ".join(p.info["cmdline"] or [])
                if "app.py" in cl and os.path.normcase(p.cwd()) == os.path.normcase(hier):
                    laeuft.append(p.info["pid"])
            except Exception:
                pass
        if laeuft:
            print(f"  ACHTUNG: Der Live-Bot laeuft gerade (PID {laeuft}).")
            print()
            print("  Eine Aenderung an config.json kann vom laufenden Bot")
            print("  ueberschrieben werden - siehe Befund 97. Bitte erst")
            print("  den Bot beenden, dann dieses Skript, dann neu starten.")
            print()
            antwort = input("  Trotzdem weitermachen? (ja/nein): ").strip().lower()
            if antwort not in ("ja", "j"):
                print("\n  Abgebrochen. Nichts geaendert.\n")
                return 1
    except ImportError:
        print("  (psutil fehlt - konnte nicht pruefen, ob der Bot laeuft)")
        print()

    # ---------------- config.json ----------------
    sicherung = sichern(CONFIG)
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)

    vorher_aktiv = cfg.get("trading", {}).get("fraktal_tor_aktiv", False)
    cfg.setdefault("trading", {})["fraktal_tor_aktiv"] = True
    cfg["trading"]["fraktal_tor_nur_messen"] = False

    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    print(f"  config.json geaendert  (Sicherung: {os.path.basename(sicherung)})")
    print(f"    fraktal_tor_aktiv      : {vorher_aktiv}  ->  True")
    print(f"    fraktal_tor_nur_messen : False  (Tor lehnt wirklich ab)")
    print()
    print("  UNVERAENDERT geblieben:")
    print(f"    mode             = {cfg['trading'].get('mode')}")
    print(f"    min_signal_score = {cfg['trading'].get('min_signal_score')}"
          f"   (Befund 103, nicht angetastet)")
    print()

    # ---------------- Epochengrenze ----------------
    if os.path.exists(EPOCHEN):
        sicherung_e = sichern(EPOCHEN)
        with open(EPOCHEN, encoding="utf-8") as f:
            ep = json.load(f)

        jetzt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        schon_da = any(e.get("id") == "L2_fraktal_tor"
                       for e in ep.get("epochs", []))
        if schon_da:
            print("  Epoche L2_fraktal_tor steht bereits - nicht doppelt "
                  "eingetragen.")
        else:
            ep.setdefault("epochs", []).append({
                "id": "L2_fraktal_tor",
                "start": jetzt,
                "label": "Fraktal-Tor scharf - Einstieg nur in Konfluenzzonen",
                "note": (
                    "Svens Fraktal-Verfahren haengt ab jetzt am Handelspfad. "
                    "Vorher kaufte der Bot nach Trendfolge (MACD + EMA + ADX "
                    "+ VWAP), also nach dem Anstieg; features/fraktal_"
                    "konfluenz.py war von keinem Handelspfad importiert. "
                    "Das Tor kann nur ABLEHNEN, nie ausloesen - die Schwelle "
                    "7 aus Befund 103 bleibt unangetastet. Gemessen vor dem "
                    "Einschalten: 4 von 4 Kaeufen des 14.09. abgelehnt "
                    "(fraktal_rueckblick.py), Tor in 27,2 Prozent der Stunden "
                    "offen ueber 30 Tage (fraktal_oeffnung.py), 21 von 21 "
                    "Pruefungen bestanden (fraktal_tor_test.py)."),
                "changes": [
                    "fraktal_tor_aktiv=true",
                    "nur Aufwaertswellen bilden Kaufzonen",
                    "Wellen ab 2,0 % Spanne",
                    "Ruecksetzer ab 0,5",
                    "Live-Bestaende werden ins Register uebernommen",
                ],
            })
            with open(EPOCHEN, "w", encoding="utf-8") as f:
                json.dump(ep, f, indent=2, ensure_ascii=False)
            print(f"  Epochengrenze gesetzt  (Sicherung: "
                  f"{os.path.basename(sicherung_e)})")
            print(f"    L2_fraktal_tor ab {jetzt}")
    else:
        print(f"  WARNUNG: {EPOCHEN} fehlt - keine Epochengrenze gesetzt!")
        print("  Ohne sie sind Vorher-Nachher-Vergleiche wertlos.")

    print()
    print("=" * 72)
    print("  FERTIG. Die Aenderung wirkt beim NAECHSTEN Start des Bots.")
    print()
    print("  Was sich aendert:")
    print("    - Gekauft wird nur noch in Fibonacci-Konfluenzzonen")
    print("    - Der Bot uebernimmt die vorhandenen 0,00041 BTC ins")
    print("      Register, mit dem echten Einstand aus den Ausfuehrungen")
    print("      -> ab dann greift der Stop-Loss darauf")
    print()
    print("  Rueckgaengig: die Sicherungsdateien zurueckkopieren.")
    print("=" * 72)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen. Nichts geaendert.\n")
