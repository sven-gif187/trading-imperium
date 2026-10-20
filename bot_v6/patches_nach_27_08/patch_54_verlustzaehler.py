# -*- coding: utf-8 -*-
"""
patch_54_verlustzaehler.py — der Verlustzähler übersteht jetzt einen Neustart
=============================================================================

NICHT VOR DEM 27.08.2026 ANWENDEN.
Diese Änderung lässt die Cooldown-Sperre erstmals greifen und ist damit
eine Verhaltensänderung. Sie braucht eine Epochengrenze.

DAS PROBLEM (Befund 54, BOT-HANDBUCH.md 4.74)
---------------------------------------------
Der Cooldown nach Verlusten soll nach drei Verlusten in Folge auf einer
Münze pausieren (cooldown_after_losses = 3). In 12 Tagen mit 197.511
Kaufprüfungen: 0 Auslösungen.

Und es hätte greifen müssen. Nach der Bot-eigenen Definition gab es seit
dem 06.08.:

    BTC/USDC   längste Verlustserie 4   (zuletzt 12.08. 18:55)
    SOL/USDC   längste Verlustserie 3   (zuletzt 16.08. 21:40)
    ETH/USDC   längste Verlustserie 3   (zuletzt 11.08. 15:10)

DIE URSACHE
-----------
coin_consecutive_losses ist ein reines Speicher-Dict (risk/engine.py:78).
Es steht NICHT in bot_state.json - die Datei kennt nur daily_loss. Bei
jedem Neustart beginnt der Zähler bei null, und die Telemetrie führt 12
verschiedene git-Commits in 12 Tagen.

Eine Serie von drei Verlusten auf derselben Münze müsste also innerhalb
eines einzigen Programmlaufs zustande kommen - bei 3,7 Trades pro Woche
praktisch unmöglich.

Der Widerspruch, der es verrät: Der Kill-Switch speichert seinen
Tagesverlust. Der Cooldown-Zähler nicht. Zwei Schutzmechanismen, zwei
Behandlungen, keine Begründung.

DIE ÄNDERUNG
------------
Zwei Stellen in runtime/state_manager.py:

  auto_save()          schreibt coin_consecutive_losses mit
  restore_positions()  liest sie zurück

Damit wird der Zähler genauso behandelt wie die offenen Positionen und
die Paper-Balance - beide werden dort bereits gesichert.

WAS DIESE ÄNDERUNG BEWUSST NICHT TUT
------------------------------------
Sie ändert NICHT, was als Verlust zählt. Der Zähler misst weiterhin den
gebuchten Dollar-Wert (pnl < 0), nicht das Netto-Ergebnis nach echten
Kosten. Nach der ehrlichen Rechnung wären die Serien 37, 25, 25 statt
4, 3, 3.

Das ist Absicht: Diese zweite Änderung hängt an Befund 42 (Gebühren an
der Quelle) und gehört in denselben Schritt wie die Kostenkorrektur -
sonst ändert sich zweimal hintereinander das Verhalten, und keine der
beiden Wirkungen ist mehr zuzuordnen.

AUFRUF
------
    python patches_nach_27_08/patch_54_verlustzaehler.py --pruefen
    python patches_nach_27_08/patch_54_verlustzaehler.py --anwenden
    python patches_nach_27_08/patch_54_verlustzaehler.py --selbsttest
"""
import io
import json
import os
import shutil
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIEL = os.path.join(HIER, "runtime", "state_manager.py")
STATE = os.path.join(HIER, "data_store", "bot_state.json")

MARKE = "[PATCH 54]"

# --- was eingesetzt wird -------------------------------------------------
# Der naheliegende Anker - state.set("open_positions_backup", ...) - kommt
# ZWEIMAL vor (if/else, Zeile 92 und 101). Ein replace(..., 1) haette
# vielleicht den falschen Zweig getroffen. Der Selbsttest hat das gefunden.
# Deshalb der Kommentar direkt DANACH: er steht genau einmal, und der
# Zaehler wird dort in jedem Fall gesichert - egal welcher Zweig lief.
ANKER_SAVE = "            # === BALANCE PERSIST FIX ==="
EINSATZ_SAVE = """            # [PATCH 54] Verlustzaehler mitsichern. Ohne das beginnt er bei
            # jedem Neustart bei null - und die Cooldown-Sperre kann nie
            # greifen (0 Ausloesungen in 12 Tagen, obwohl es Serien von
            # 4/3/3 gab). Der Kill-Switch sichert seinen Tagesverlust
            # laengst; hier fehlte dieselbe Behandlung. Befund 54.
            try:
                self.app.state.set(
                    "coin_consecutive_losses",
                    dict(getattr(self.app.risk_engine,
                                 "coin_consecutive_losses", {}) or {}))
                self.app.state.set(
                    "consecutive_losses",
                    int(getattr(self.app.risk_engine,
                                "consecutive_losses", 0) or 0))
            except Exception as _cl_e:
                from core.logger import log as _log
                _log.warn("STATE", f"Verlustzaehler nicht gesichert: "
                                   f"{str(_cl_e)[:60]}")

            # === BALANCE PERSIST FIX ==="""

ANKER_LOAD = '        positions = self.app.state.get("open_positions_backup", {})'
EINSATZ_LOAD = '''        # [PATCH 54] Verlustzaehler zurueckholen, bevor Positionen geladen
        # werden. Reihenfolge ist egal fuers Ergebnis, aber so steht der
        # Zaehler auch dann richtig, wenn kein Positions-Backup existiert.
        try:
            _cl = self.app.state.get("coin_consecutive_losses", {}) or {}
            if isinstance(_cl, dict) and _cl:
                self.app.risk_engine.coin_consecutive_losses = {
                    str(k): int(v) for k, v in _cl.items()}
                from core.logger import log as _log
                _log.info("STATE", f"Verlustzaehler wiederhergestellt: "
                                   f"{self.app.risk_engine.coin_consecutive_losses}")
            _g = self.app.state.get("consecutive_losses", 0)
            if _g:
                self.app.risk_engine.consecutive_losses = int(_g)
        except Exception as _cl_e:
            from core.logger import log as _log
            _log.warn("STATE", f"Verlustzaehler nicht geladen: {str(_cl_e)[:60]}")

        positions = self.app.state.get("open_positions_backup", {})'''


def schon_drin():
    try:
        return MARKE in io.open(ZIEL, encoding="utf-8").read()
    except Exception:
        return False


def bericht():
    print(f"\n{'='*68}")
    print("  PATCH 54 — Verlustzähler übersteht einen Neustart")
    print(f"{'='*68}\n")
    if schon_drin():
        print("  Bereits angewendet.\n")
        return True
    t = io.open(ZIEL, encoding="utf-8").read()
    ok_save = ANKER_SAVE in t
    ok_load = ANKER_LOAD in t
    print(f"  Ziel: runtime/state_manager.py")
    print(f"    Ankerpunkt zum Sichern gefunden : {'JA' if ok_save else 'NEIN'}")
    print(f"    Ankerpunkt zum Laden gefunden   : {'JA' if ok_load else 'NEIN'}")
    try:
        st = json.load(open(STATE, encoding="utf-8"))
        print(f"\n  bot_state.json führt heute:")
        print(f"    daily_loss                 : {'JA' if 'daily_loss' in st else 'nein'}")
        print(f"    coin_consecutive_losses    : "
              f"{'JA' if 'coin_consecutive_losses' in st else 'NEIN  <- das fehlt'}")
    except Exception as e:
        print(f"  bot_state.json nicht lesbar: {e}")
    if not (ok_save and ok_load):
        print("\n  ACHTUNG: mindestens ein Ankerpunkt fehlt - state_manager.py")
        print("  wurde seit dem 19.08. geändert. Patch von Hand prüfen.\n")
    return ok_save and ok_load


def anwenden():
    if schon_drin():
        print("\n  Bereits angewendet - nichts zu tun.\n")
        return 0
    if not bericht():
        return 1
    sicherung = ZIEL + f".bak_patch54_{datetime.now():%Y%m%d_%H%M%S}"
    shutil.copy2(ZIEL, sicherung)
    t = io.open(ZIEL, encoding="utf-8").read()
    t = t.replace(ANKER_SAVE, EINSATZ_SAVE, 1)
    t = t.replace(ANKER_LOAD, EINSATZ_LOAD, 1)
    io.open(ZIEL, "w", encoding="utf-8").write(t)
    import py_compile
    try:
        py_compile.compile(ZIEL, doraise=True)
    except Exception as e:
        shutil.copy2(sicherung, ZIEL)
        print(f"\n  FEHLER beim Übersetzen: {e}")
        print("  Änderung zurückgenommen.\n")
        return 1
    print(f"\n  Sicherung: {os.path.basename(sicherung)}")
    print("  Zwei Stellen in runtime/state_manager.py ergänzt.")
    print("\n  NICHT VERGESSEN:")
    print("   1. Epochengrenze in config_epochs.json eintragen")
    print("   2. Bot neu starten")
    print("   3. Nach dem ersten Verlust prüfen, ob der Zähler in")
    print("      bot_state.json auftaucht (Schlüssel coin_consecutive_losses)")
    print("   4. python prozess_frische.py\n")
    return 0


def selbsttest():
    fehler = 0
    print("\n=== Richtung 1: sind die Ankerpunkte eindeutig? ===")
    t = io.open(ZIEL, encoding="utf-8").read()
    for name, anker in [("Sichern", ANKER_SAVE), ("Laden", ANKER_LOAD)]:
        n = t.count(anker)
        ok = n == 1
        print(f"  {'OK  ' if ok else 'FEHL'} {name}: {n}x gefunden (soll genau 1)")
        if not ok:
            fehler += 1

    print("\n=== Richtung 2: ist der Einsatz gültiges Python? ===")
    for name, code in [("Sichern", EINSATZ_SAVE), ("Laden", EINSATZ_LOAD)]:
        try:
            # Einrückung entfernen und in eine Testfunktion packen
            zeilen = [z[8:] if z.startswith(" " * 8) else z
                      for z in code.splitlines()]
            compile("def _t(self):\n" + "\n".join("    " + z for z in zeilen),
                    "<test>", "exec")
            print(f"  OK   {name}")
        except SyntaxError as e:
            print(f"  FEHL {name}: {e}")
            fehler += 1

    print("\n=== Richtung 3: wirkt der Patch auf eine Kopie? ===")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        kopie = os.path.join(d, "state_manager.py")
        shutil.copy2(ZIEL, kopie)
        k = io.open(kopie, encoding="utf-8").read()
        k = k.replace(ANKER_SAVE, EINSATZ_SAVE, 1).replace(ANKER_LOAD, EINSATZ_LOAD, 1)
        io.open(kopie, "w", encoding="utf-8").write(k)
        import py_compile
        try:
            py_compile.compile(kopie, doraise=True)
            print("  OK   gepatchte Kopie ist übersetzbar")
        except Exception as e:
            print(f"  FEHL gepatchte Kopie: {e}")
            fehler += 1
        for marke in ("coin_consecutive_losses", MARKE):
            ok = marke in k
            print(f"  {'OK  ' if ok else 'FEHL'} '{marke}' steht in der Kopie")
            if not ok:
                fehler += 1

    print("\n=== Richtung 4: ist die Original-Datei unberührt? ===")
    unberuehrt = MARKE not in io.open(ZIEL, encoding="utf-8").read()
    print(f"  {'OK  ' if unberuehrt else 'FEHLER'} "
          f"state_manager.py {'unverändert' if unberuehrt else 'WURDE VERÄNDERT'}")
    if not unberuehrt:
        fehler += 1

    print("\n" + ("ALLE TESTS BESTANDEN" if not fehler
                  else f"{fehler} TEST(S) FEHLGESCHLAGEN") + "\n")
    return fehler


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "--pruefen"
    if arg == "--selbsttest":
        sys.exit(1 if selbsttest() else 0)
    if arg == "--anwenden":
        sys.exit(anwenden())
    bericht()
    print("\n  Nur geprüft. NICHT VOR DEM 27.08.2026 anwenden.\n")
