#!/usr/bin/env python3
# check_install.py - prueft, was WIRKLICH installiert ist. Aendert nichts.
#   python "C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\check_install.py"
import os, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def ok(b):
    return "JA  ✓" if b else "NEIN ✗"


def main():
    app = os.path.join(HERE, "app.py")
    print("Pruefe Installation in:")
    print(" ", HERE)
    print("=" * 60)

    if not os.path.exists(app):
        print("app.py NICHT gefunden!")
        return
    t = open(app, encoding="utf-8").read()

    cap = ('_fg_entry = self.state.get("fear_greed", 50)' in t
           and 'hasattr(self, "current_regime")' not in t)
    reg = "REGIME-FILTER: KEIN neuer Kauf" in t
    rfpy = os.path.exists(os.path.join(HERE, "regime_filter.py"))
    cfg_p = os.path.join(HERE, "config_regime_filter.json")
    cfg_ok = os.path.exists(cfg_p)

    print("Capture-Fix (echtes Regime/F&G im Journal):", ok(cap))
    print("Regime-Filter im app.py-Code:              ", ok(reg))
    print("regime_filter.py vorhanden:                ", ok(rfpy))
    print("config_regime_filter.json vorhanden:       ", ok(cfg_ok))

    if cfg_ok:
        try:
            c = json.load(open(cfg_p, encoding="utf-8"))
            print("   -> enabled =", c.get("enabled"),
                  "| min_confirmations =", c.get("min_confirmations"))
        except Exception as e:
            print("   -> Config kaputt:", e)

    ep = os.path.join(HERE, "config_epochs.json")
    if os.path.exists(ep):
        try:
            eps = json.load(open(ep, encoding="utf-8")).get("epochs", [])
            has_e2 = any("regime" in (e.get("id", "") + e.get("label", "")).lower()
                         for e in eps)
            print("Epoche fuer Regime-Filter markiert:        ", ok(has_e2))
            print("   Epochen:", ", ".join(e.get("id", "?") for e in eps))
        except Exception as e:
            print("config_epochs.json kaputt:", e)

    if rfpy and cfg_ok:
        try:
            sys.path.insert(0, HERE)
            import regime_filter as rf
            block_knife, _, _ = rf.evaluate(regime="RANGING", cycle="MID_BEAR",
                                            mtf_direction="BEARISH",
                                            indicators={"ema20": 60, "ema50": 62}, price=58)
            block_floor, _, _ = rf.evaluate(regime="RANGING", cycle="ACCUMULATION",
                                            mtf_direction="NEUTRAL",
                                            indicators={"ema20": 61, "ema50": 60}, price=63)
            print("Filter-Selbsttest (Messer->block):         ", ok(block_knife))
            print("Filter-Selbsttest (Boden->erlaubt):        ", ok(not block_floor))
        except Exception as e:
            print("Filter-Import-Fehler:", e)

    print("=" * 60)
    if cap and reg and rfpy and cfg_ok:
        print("ALLES DRIN. Filter ist scharf - er meldet sich nur,")
        print("wenn er einen bestaetigten Abwaertstrend blockt.")
    else:
        print("NICHT alles drin - siehe ✗ oben. Schick mir die ✗-Zeile.")


if __name__ == "__main__":
    main()
