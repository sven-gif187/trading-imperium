# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Telegram-Waechter-Bot einrichten. Wird von TELEGRAM_EINRICHTEN.bat aufgerufen.

1. Token abfragen (unsichtbare Eingabe), Form pruefen, bei Telegram mit getMe pruefen
2. Token in pruefstand/.env schreiben
3. Auf deine erste Nachricht an den Bot warten (max. 3 Minuten) -> Chat-ID
4. Chat-ID in pruefstand/.env schreiben, Testnachricht schicken

Der Token wird an keiner Stelle ausgegeben.
  --selbsttest  prueft .env-Schreiben und Sperrlogik ohne Netz und ohne echten Token
"""
from __future__ import annotations

import getpass
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telegram_meldung as tm  # noqa: E402

FORM = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")


def zwischenablage() -> str:
    """Text aus der Windows-Zwischenablage, ohne ihn anzuzeigen. Leer bei Fehler."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                           capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
        return (r.stdout or "").strip()
    except Exception:
        return ""


def einrichten() -> int:
    env = tm.lade_env()
    print("\n  TELEGRAM-WAECHTER EINRICHTEN\n  " + "-" * 40)
    token = env.get("TELEGRAM_WAECHTER_TOKEN", "")
    if token:
        a = input("  Es ist schon ein Token eingetragen. Ersetzen? (j/n): ").strip().lower()
        if a != "j":
            print("  Behalte den vorhandenen Token.")
        else:
            token = ""
    versuch = 0
    while not token:
        versuch += 1
        # [14.10.2026] Erster Weg: Zwischenablage. Das Einfuegen in die
        # unsichtbare Eingabe hat bei Sven nicht geklappt (keine .env entstand).
        t = zwischenablage() if versuch == 1 else ""
        if t and FORM.match(t):
            print("\n  Token in der Zwischenablage gefunden (wird nicht angezeigt).")
        else:
            if versuch == 1:
                print("\n  In der Zwischenablage ist kein Token.")
                print("  So geht es am einfachsten: In Telegram im Chat mit @BotFather den Token")
                print("  (die lange Zeile mit Doppelpunkt) kopieren, dann HIER Enter druecken.")
                input("  Enter, sobald kopiert ... ")
                t = zwischenablage()
                if t and FORM.match(t):
                    print("  Token in der Zwischenablage gefunden (wird nicht angezeigt).")
            if not (t and FORM.match(t)):
                print("\n  Dann bitte einfuegen (Rechtsklick ins Fenster oder Strg+V), danach Enter.")
                print("  Die Eingabe bleibt UNSICHTBAR - das ist Absicht.")
                t = getpass.getpass("  Token: ")
        t = t.strip().strip('"').strip("'")
        if not FORM.match(t):
            print(f"  Das sieht nicht wie ein Token aus ({len(t)} Zeichen, erwartet z. B. 123456789:ABC...)."
                  " Nochmal.")
            continue
        r = tm.api(t, "getMe")
        if not r.get("ok"):
            print(f"  Telegram lehnt ab: {r.get('description', '?')}. Nochmal.")
            continue
        token = t
        tm.schreibe_env({"TELEGRAM_WAECHTER_TOKEN": token})
        if zwischenablage() == token:      # Token nicht in der Zwischenablage liegen lassen
            subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ' '"],
                           capture_output=True, timeout=10)
        print(f"  OK - Bot erkannt: @{r['result'].get('username')}  (Token gespeichert in pruefstand\\.env)")

    me = tm.api(token, "getMe")
    name = me.get("result", {}).get("username", "deinem Bot") if me.get("ok") else "deinem Bot"
    print(f"\n  JETZT: Telegram oeffnen, @{name} suchen, auf START tippen oder 'hallo' schicken.")
    print("  Ich warte bis zu 3 Minuten ...")
    chat, ende, offset = None, time.time() + 180, None
    while time.time() < ende and not chat:
        daten = {"timeout": 20}
        if offset:
            daten["offset"] = offset
        r = tm.api(token, "getUpdates", daten, timeout=30)
        for u in r.get("result", []) if r.get("ok") else []:
            offset = u["update_id"] + 1
            m = u.get("message") or u.get("edited_message") or {}
            if m.get("chat", {}).get("type") == "private":
                chat = str(m["chat"]["id"])
        if not r.get("ok"):
            time.sleep(3)
    if not chat:
        print("  Keine Nachricht angekommen. Einfach nochmal doppelklicken - der Token bleibt gespeichert.")
        return 1
    tm.schreibe_env({"TELEGRAM_WAECHTER_CHAT_ID": chat})
    ok = tm.sende("[WAECHTER][TEST] Verbindung steht. Ab jetzt meldet der Pruefstand hier, "
                  "wenn ein Bot ausfaellt oder eine Zahl nicht stimmt.", env=tm.lade_env())
    print(f"  Chat gespeichert. Testnachricht {'GESENDET - schau aufs Handy' if ok else 'FEHLGESCHLAGEN'}.")
    return 0 if ok else 1


def selbsttest() -> int:
    fehler = 0
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / ".env"
        p.write_text("ANDERES=1\n# Kommentar\n", encoding="utf-8")
        tm.schreibe_env({"TELEGRAM_WAECHTER_TOKEN": "111:abc"}, p)
        tm.schreibe_env({"TELEGRAM_WAECHTER_TOKEN": "222:def", "TELEGRAM_WAECHTER_CHAT_ID": "42"}, p)
        e = tm.lade_env(p)
        ok = e == {"ANDERES": "1", "TELEGRAM_WAECHTER_TOKEN": "222:def", "TELEGRAM_WAECHTER_CHAT_ID": "42"}
        fehler += not ok
        print(f"  {'OK  ' if ok else 'FEHL'} .env: ersetzt statt doppelt, fremde Zeilen bleiben ({e})")
    ok = tm.sende("x", env={}) is False
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} ohne Token: kein Versand, kein Absturz")
    ok = bool(FORM.match("123456789:" + "A" * 35)) and not FORM.match("hallo")
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} Token-Formpruefung")
    r = tm.api("123456789:" + "A" * 35, "getMe")
    ok = r.get("ok") is False and "AAAA" not in str(r)
    fehler += not ok
    print(f"  {'OK  ' if ok else 'FEHL'} falscher Token: abgelehnt, Token nicht in der Meldung ({r.get('description')})")
    print("SELBSTTEST", "BESTANDEN" if not fehler else f"{fehler} FEHLER")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(selbsttest() if "--selbsttest" in sys.argv else einrichten())
