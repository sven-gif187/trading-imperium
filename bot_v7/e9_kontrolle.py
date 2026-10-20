# -*- coding: utf-8 -*-
"""e9_kontrolle.py - ist die Epoche E9 wirklich scharf, oder nur eingetragen?

WOZU
----
Am 12.09.2026 wurden fuenf Aenderungen gleichzeitig scharf gestellt und EINE
Epochengrenze E9 gesetzt. Der Bot liest Quelltext und Schalter aber nur BEIM
START. Ohne Neustart laeuft alles Alte weiter - und die Grenze steht trotzdem
schon in der Datei. Trades unter alten Regeln wuerden dann in der neuen
Epoche gezaehlt, und die Messung waere von Anfang an verdorben.

Genau das ist am 14.08. schon einmal passiert, nur andersherum: die Grenze
zu E6 wurde beim Einfrieren VERGESSEN und musste nachtraeglich gesetzt
werden (siehe config_epochs.json, Notiz zu E6_messfenster).

Diese Pruefung beantwortet eine Frage: Laeuft, was in der Datei steht?

AENDERT NICHTS. Liest nur.

    python e9_kontrolle.py
"""
import datetime
import io
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HIER)


def _lies(pfad):
    with io.open(pfad, encoding="utf-8") as f:
        return json.load(f)


def _quelltext(pfad):
    with io.open(pfad, encoding="utf-8", errors="replace") as f:
        return f.read()


def main():
    fehlt = []
    print()

    # --- 1. Steht die Grenze? -----------------------------------------
    ep = _lies("config_epochs.json")
    e9 = next((e for e in ep["epochs"] if e["id"].startswith("E9")), None)
    if e9 is None:
        print("  Epochengrenze E9   FEHLT in config_epochs.json")
        return 1
    start = datetime.datetime.fromisoformat(e9["start"])
    print("  Epochengrenze E9   gesetzt %s UTC" % start.strftime("%d.%m.%Y %H:%M:%S"))
    print("                     %d Aenderungen eingetragen" % len(e9["changes"]))
    print()

    # --- 2. Steht der Schalter? ---------------------------------------
    cfg = _lies(os.path.join("data_store", "config.json"))
    w = cfg.get("warteauftraege") or {}
    print("  Warte-Auftraege    aktiv=%s, Abstand %.2f %%, %d Kerzen (%d min)"
          % (w.get("aktiv"), w.get("abstand_pct", 0), w.get("gueltig_kerzen", 0),
             int(w.get("gueltig_kerzen", 0)) * int(w.get("kerze_minuten", 15))))
    if not w.get("aktiv"):
        fehlt.append("Der Schalter warteauftraege.aktiv steht auf false")

    # --- 3. Stehen die vier Patchwerte im Quelltext? ------------------
    er = _quelltext(os.path.join("risk", "exit_rules.py"))
    sm = _quelltext(os.path.join("runtime", "state_manager.py"))
    ct = _quelltext(os.path.join("agents", "cycle_theory.py"))
    print()
    pruefungen = [
        ("Breakeven-Puffer 0,55 %", "BREAKEVEN_PUFFER_PCT = round(K_BASIS_PCT" in er),
        ("Trailing-Schwelle 1,57 %", "TRAIL_AB_PCT = 1.57" in er),
        ("Verlustzaehler gesichert", '"coin_consecutive_losses"' in sm),
        ("Allzeithoch dynamisch", "_ATH_RUECKFALL = 126_200" in ct),
        ("entry_score in Whitelist", '"entry_score": pos.get("entry_score")' in sm),
    ]
    for name, ok in pruefungen:
        print("  %-34s %s" % (name, "im Quelltext" if ok else "FEHLT"))
        if not ok:
            fehlt.append(name)

    # --- 4. Laeuft der Bot damit? -------------------------------------
    print()
    lauf, pid, seit = _bot_start()
    if not lauf:
        print("  Bot                LAEUFT NICHT")
        print()
        print("  Nichts davon wirkt, solange er nicht laeuft.")
        return 1

    print("  Bot                PID %s, gestartet %s UTC"
          % (pid, seit.strftime("%d.%m. %H:%M:%S")))

    if seit < start:
        minuten = (start - seit).total_seconds() / 60.0
        print()
        print("  " + "=" * 58)
        print("   NEUSTART NOETIG")
        print("  " + "=" * 58)
        print()
        print("   Der Bot laeuft seit %s, die Epochengrenze steht auf %s -"
              % (seit.strftime("%H:%M"), start.strftime("%H:%M")))
        print("   er ist also %.0f Minuten AELTER als die Grenze und arbeitet"
              % minuten)
        print("   noch mit den alten Regeln.")
        print()
        print("   Jeder Handel bis zum Neustart zaehlt in E9, folgt aber den")
        print("   ALTEN Regeln. Je frueher der Neustart, desto sauberer die")
        print("   Messung.")
        print()
        print("   Bot-Fenster schliessen, dann start_bot.bat doppelklicken.")
        return 2

    print()
    print("  Der Bot ist NACH der Grenze gestartet - alles wirkt.")
    if fehlt:
        print()
        print("  ABER: %d Punkt(e) stimmen nicht:" % len(fehlt))
        for f in fehlt:
            print("    - %s" % f)
        return 1

    # --- 5. Was hat die Warteschlange bisher getan? -------------------
    wpfad = os.path.join("data_store", "warteauftraege.json")
    print()
    if os.path.exists(wpfad):
        wd = _lies(wpfad)
        v = wd.get("verlauf") or {}
        offen = wd.get("auftraege") or {}
        print("  Warteschlange      %d angelegt, %d ausgefuehrt, %d verfallen"
              % (v.get("angelegt", 0), v.get("ausgefuehrt", 0),
                 v.get("verfallen", 0)))
        ges = v.get("ausgefuehrt", 0) + v.get("verfallen", 0)
        if ges >= 10:
            quote = 100.0 * v.get("ausgefuehrt", 0) / ges
            print("                     echte Ausfuehrungsquote %.1f %%" % quote)
            print("                     gemessen waren 73,3 %% - das war eine")
            print("                     OBERGRENZE, weil die Messung jedes")
            print("                     Kerzentief sah und der Bot nur alle 12 s")
        else:
            print("                     (unter 10 Faellen - noch keine Quote)")
        if offen:
            print("  offen gerade       %s" % ", ".join(offen))
    else:
        print("  Warteschlange      noch keine Datei - kein Kauf seit dem Start")

    print()
    print("  Alles scharf.")
    return 0


def _bot_start():
    """Findet den laufenden app.py-Prozess und seine Startzeit."""
    try:
        import psutil
    except ImportError:
        return False, None, None
    for pr in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cl = pr.info.get("cmdline") or []
            if any("app.py" in str(c) for c in cl) and "python" in str(cl[0]).lower():
                t = datetime.datetime.fromtimestamp(
                    pr.info["create_time"], datetime.timezone.utc)
                return True, pr.info["pid"], t
        except Exception:
            continue
    return False, None, None


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("\n  Die Kontrolle selbst ist gescheitert: %s" % e)
        print("  (Das ist ein Befund ueber die Pruefung, nicht ueber E9.)")
        sys.exit(3)
