# -*- coding: utf-8 -*-
"""telegram_pruefen.py - sagt in Klartext, warum Telegram nicht funktioniert.

WOZU
----
Am 08.09.2026 kamen keine Telegram-Nachrichten an. Sven hatte den Token neu
eingetragen und alles sah richtig aus. Die Ursache: In TELEGRAM_CHAT_ID stand
die Zahl VOR dem Doppelpunkt des Tokens - das ist die Nummer des BOTS, nicht
die eigene. Ein Bot darf sich nicht selbst anschreiben.

Der Fehler ist von aussen nicht zu sehen: Die Zahl ist echt, sie ist lang, sie
sieht aus wie eine Chat-ID. Nur gehoert sie dem Falschen.

DIESES PROGRAMM
---------------
Fragt Telegram der Reihe nach ab und benennt den Fehler beim Namen.
Der Token wird NIE ausgegeben - nur, ob er funktioniert.

    TELEGRAM_PRUEFEN.bat        (Doppelklick)
    python telegram_pruefen.py

AENDERT NICHTS. Liest .env und fragt Telegram. Kein Schreibzugriff.
"""
import io, os, sys

HIER = os.path.dirname(os.path.abspath(__file__))


def lies_env():
    p = os.path.join(HIER, ".env")
    if not os.path.exists(p):
        return None, "Die Datei .env fehlt."
    cfg = {}
    for z in io.open(p, encoding="utf-8", errors="replace"):
        if "=" in z and not z.lstrip().startswith("#"):
            k, v = z.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg, None


def main():
    print("=" * 66)
    print("  TELEGRAM-PRUEFUNG - warum kommt keine Nachricht an?")
    print("=" * 66)

    cfg, fehler = lies_env()
    if fehler:
        print("\n  " + fehler)
        return 2

    tok = cfg.get("TELEGRAM_BOT_TOKEN", "")
    chat = cfg.get("TELEGRAM_CHAT_ID", "")

    if not tok:
        print("\n  TELEGRAM_BOT_TOKEN fehlt in der .env.")
        return 2
    if not chat:
        print("\n  TELEGRAM_CHAT_ID fehlt in der .env.")
        return 2

    # --- Der haeufigste Fehler, ohne jeden Netzzugriff erkennbar ---
    vorne = tok.split(":")[0]
    print("\n[1] Sind Token und Chat-ID verschiedene Dinge?")
    if chat == vorne:
        print("    NEIN - und das ist der Fehler.")
        print()
        print("    Ihr Token beginnt mit  %s:..." % vorne)
        print("    Ihre Chat-ID lautet    %s" % chat)
        print()
        print("    Die Zahl VOR dem Doppelpunkt ist die Nummer des BOTS.")
        print("    Sie steht in jedem Token drin. Ein Bot darf sich nicht")
        print("    selbst anschreiben - deshalb kommt nichts an.")
        print()
        print("    SO BEKOMMEN SIE IHRE EIGENE NUMMER:")
        print("      1. In Telegram nach  @userinfobot  suchen")
        print("      2. Auf START tippen")
        print("      3. Er antwortet mit  Id: 123456789")
        print("      4. Diese Zahl als TELEGRAM_CHAT_ID in die .env")
        print("      5. Ihren eigenen Bot einmal anschreiben (/start)")
        print("      6. Bot neu starten")
        return 1
    print("    ja - die Chat-ID ist nicht die Bot-Nummer.")

    try:
        import requests
    except ImportError:
        print("\n  Das Paket 'requests' fehlt:  pip install requests")
        return 2

    def frag(pfad, **a):
        try:
            return requests.get("https://api.telegram.org/bot%s/%s" % (tok, pfad),
                                params=a, timeout=20).json()
        except Exception as e:
            return {"ok": False, "description": "%s: %s" % (type(e).__name__, str(e)[:160])}

    print("\n[2] Ist der Token gueltig?")
    r = frag("getMe")
    if not r.get("ok"):
        d = str(r.get("description", ""))
        print("    NEIN: %s" % d)
        if "CERTIFICATE" in d.upper() or "SSL" in d.upper():
            print("    Das ist KEIN Token-Problem, sondern die Verschluesselung:")
            print("    ein Virenscanner oder Firmennetz klinkt sich dazwischen.")
        elif "401" in d or "Unauthorized" in d:
            print("    Der Token ist falsch oder wurde zurueckgezogen.")
            print("    Neu holen: in Telegram @BotFather -> /mytoken")
        return 1
    b = r["result"]
    print("    ja - Bot '%s' (@%s)" % (b.get("first_name"), b.get("username")))

    print("\n[3] Ist die Chat-ID erreichbar?")
    r2 = frag("getChat", chat_id=chat)
    if not r2.get("ok"):
        d = str(r2.get("description", ""))
        print("    NEIN: %s" % d)
        if "not found" in d.lower():
            print("    Die Nummer gibt es nicht, oder Sie haben dem Bot noch nie")
            print("    geschrieben. Oeffnen Sie @%s und tippen Sie /start."
                  % b.get("username"))
        return 1
    c = r2["result"]
    print("    ja - Typ '%s', Name '%s'"
          % (c.get("type"), c.get("first_name") or c.get("title")))
    if str(c.get("id")) == str(b.get("id")):
        print("    ABER: Das ist der Bot selbst. Siehe Schritt 1.")
        return 1

    print("\n[4] Kommt eine Nachricht wirklich an?")
    r3 = frag("sendMessage", chat_id=chat,
              text="Pruefung von telegram_pruefen.py - alles in Ordnung.")
    if r3.get("ok"):
        print("    JA. Eine Testnachricht wurde zugestellt.")
        print("\n" + "=" * 66)
        print("  ALLES IN ORDNUNG - sehen Sie in Telegram nach.")
        print("=" * 66)
        return 0
    d = str(r3.get("description", ""))
    print("    NEIN: %s" % d)
    if "blocked" in d.lower():
        print("    Sie haben den Bot blockiert. In Telegram entsperren.")
    elif "can't initiate" in d.lower() or "not found" in d.lower():
        print("    Sie haben dem Bot noch nie geschrieben. Ein Bot darf erst")
        print("    antworten, wenn Sie ihn zuerst angesprochen haben:")
        print("    @%s oeffnen und /start tippen." % b.get("username"))
    return 1


if __name__ == "__main__":
    code = main()
    try:
        input("\nEnter zum Schliessen...")
    except EOFError:
        pass
    sys.exit(code)
