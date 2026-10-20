"""
Telegram-Diagnose: prueft Token und Chat-ID direkt gegen die Telegram-API.
Voellig unabhaengig vom Bot - einfach ausfuehren und Anweisungen folgen.
"""
import json
import urllib.request

def api(token, method, payload=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if payload is None:
            req = urllib.request.Request(url)
        else:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"ok": False, "description": str(e)}
    except Exception as e:
        return {"ok": False, "description": str(e)}

def main():
    print("=" * 60)
    print("  TELEGRAM-DIAGNOSE")
    print("=" * 60)
    token = input("Bot-Token einfuegen (von @BotFather): ").strip()
    chat_id = input("Deine Chat-ID einfuegen (von @userinfobot): ").strip()
    print()

    # Test 1: Token gueltig?
    me = api(token, "getMe")
    if not me.get("ok"):
        print("FEHLER BEIM TOKEN: " + str(me.get("description")))
        print("-> Token ist ungueltig. Neues Token bei @BotFather holen.")
        return
    bot_name = me["result"].get("username", "?")
    print(f"[OK] Token gueltig. Bot: @{bot_name}")

    # Test 2: Hat der Bot ueberhaupt schon Nachrichten gesehen?
    upd = api(token, "getUpdates")
    chats = set()
    for u in upd.get("result", []):
        c = (u.get("message") or {}).get("chat") or {}
        if c.get("id"):
            chats.add(str(c["id"]))
    if chats:
        print(f"[INFO] Der Bot hat Nachrichten von folgenden Chat-IDs gesehen: {', '.join(chats)}")
        if chat_id not in chats:
            print(f"[!] Deine eingegebene ID ({chat_id}) ist NICHT dabei!")
            print(f"    -> Wahrscheinlich ist eine der obigen IDs die richtige.")
    else:
        print("[!] Der Bot hat noch NIE eine Nachricht empfangen.")
        print(f"    -> Oeffne Telegram, such @{bot_name}, druecke START,")
        print("       schick 'test' und fuehre dieses Script NOCHMAL aus.")

    # Test 3: Kann der Bot dir schreiben?
    res = api(token, "sendMessage",
              {"chat_id": chat_id, "text": "Diagnose-Test vom Trading Imperium - es funktioniert!"})
    if res.get("ok"):
        print("[OK] TESTNACHRICHT GESENDET - schau auf dein Handy!")
        print()
        print("Diese Werte in die Bot-Settings eintragen:")
        print("  Token:   " + token)
        print("  Chat-ID: " + chat_id)
    else:
        desc = str(res.get("description", ""))
        print("FEHLER BEIM SENDEN: " + desc)
        if "chat not found" in desc.lower():
            print("-> Die Chat-ID ist falsch ODER du hast bei deinem Bot")
            print("   noch nie START gedrueckt. Beides pruefen, nochmal testen.")
        elif "unauthorized" in desc.lower():
            print("-> Token falsch oder widerrufen. Neues bei @BotFather holen.")

if __name__ == "__main__":
    main()
