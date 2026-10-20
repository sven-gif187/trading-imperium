#!/usr/bin/env python3
# regime_diag_toggle.py
# ---------------------------------------------------------------------------
# Legt das "diag"-Flag in config_regime_filter.json sauber um -
# damit du nicht von Hand in der JSON-Datei editieren musst.
#
#   python "...\regime_diag_toggle.py" on     -> Diagnose AN
#   python "...\regime_diag_toggle.py" off    -> Diagnose AUS
#   python "...\regime_diag_toggle.py"        -> nur Status anzeigen
#
# Wirkt live (der Bot laedt die config automatisch neu) - KEIN Neustart noetig.
# ---------------------------------------------------------------------------
import os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, "config_regime_filter.json")

ON = {"on", "true", "1", "an", "ein"}
OFF = {"off", "false", "0", "aus"}


def main():
    if not os.path.exists(CFG):
        print("config_regime_filter.json nicht gefunden in:", HERE)
        return
    try:
        with open(CFG, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        print("config nicht lesbar:", e)
        return

    arg = sys.argv[1].strip().lower() if len(sys.argv) > 1 else ""

    if arg == "":
        print("Aktueller Stand: diag =", bool(d.get("diag", False)))
        print('Umschalten:  python "%s" on   /   off' % os.path.join(HERE, "regime_diag_toggle.py"))
        return

    if arg in ON:
        new = True
    elif arg in OFF:
        new = False
    else:
        print("Unbekanntes Argument:", repr(arg), "- nutze 'on' oder 'off'.")
        return

    d["diag"] = new
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print("diag = %s gesetzt." % new)
    if new:
        print("-> Bot laeuft lassen, ~1 Minute warten, dann die [REGIME-DIAG]-Zeilen")
        print("   aus dem Log kopieren und schicken. Danach wieder 'off'.")
    else:
        print("-> Diagnose-Log ist wieder aus.")


if __name__ == "__main__":
    main()
