#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  TESTNETZ-PROBE - der Order-Pfad an einer echten Boerse
================================================================
Angelegt 21.08.2026 auf Svens Wunsch: "ich will endlich einen
Live-Probelauf machen und endlich mal zum Ziel kommen."

WAS DAS IST - UND WAS NICHT
---------------------------
Das Bybit-Testnetz ist eine vollwertige Boerse mit echten
Schnittstellen und SPIELGELD. Kein Euro im Feuer.

Es beantwortet genau die Fragen, die der Papiermodus
GRUNDSAETZLICH nicht beantworten kann - weil dort gerechnet und
nicht gesendet wird:

  1. Kommt eine Order ueberhaupt an?
  2. Was passiert bei einer Teilausfuehrung (partial fill)?
  3. Was sagt die Boerse zu einer zu kleinen Order?
  4. Wird bei einer Wiederholung (Retry) ZWEIMAL gekauft?
  5. Kennt der Bot nach einem Neustart seinen Zustand?
  6. Wie gross sind Spanne (Spread) und Schlupf (Slippage) wirklich?

WAS ES NICHT ANFASST
--------------------
Den Bot. Kein Import aus execution/, kein Schreiben in
data_store/, kein Eingriff in den laufenden Handel. Der
Handelspfad (execution/engine.py:138) kennt gar kein Testnetz -
ihn dafuer umzubauen waere eine Verhaltensaenderung mitten im
Messfenster. Dieses Werkzeug laeuft daneben und benutzt ccxt
direkt.

DIE SCHLUESSEL
--------------
Du brauchst EIGENE Testnetz-Schluessel. NICHT die Live-Schluessel.

  1. https://testnet.bybit.com aufrufen
  2. Konto anlegen (eigenes Testnetz-Konto, NICHT das echte)
  3. Unter API -> "Create New Key" einen Schluessel erzeugen,
     Rechte: nur "Trade" und "Read". KEIN Withdraw.
  4. Beide Werte in die Datei .env eintragen:

        BYBIT_TESTNET_KEY=...
        BYBIT_TESTNET_SECRET=...

Eigene Namen mit _TESTNET_, damit sie nie mit den echten
verwechselt werden. Dieses Werkzeug liest AUSSCHLIESSLICH diese
zwei - an die Live-Schluessel kommt es nicht heran.

Testnetz-Konten bekommen automatisch Spielgeld. Geht es aus:
neuen Schluessel erzeugen.

AUFRUF
------
    python testnetz_probe.py            Trockenlauf, sendet nichts
    python testnetz_probe.py --pruefen  nur Verbindung und Kontostand
    python testnetz_probe.py --echt     die sechs Pruefungen wirklich
================================================================
"""
import os
import sys
import time
import argparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HIER = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)
PAAR = "BTC/USDT"          # Bybit Spot fuehrt USDT, nicht USDC


def schluessel():
    """Testnetz-Schluessel aus .env - und NUR diese."""
    k = os.environ.get("BYBIT_TESTNET_KEY", "")
    s = os.environ.get("BYBIT_TESTNET_SECRET", "")
    if not k or not s:
        p = os.path.join(HIER, ".env")
        if os.path.exists(p):
            for zeile in open(p, encoding="utf-8", errors="replace"):
                zeile = zeile.strip()
                if zeile.startswith("BYBIT_TESTNET_KEY="):
                    k = zeile.split("=", 1)[1].strip()
                elif zeile.startswith("BYBIT_TESTNET_SECRET="):
                    s = zeile.split("=", 1)[1].strip()
    return k, s


def boerse():
    """ccxt gegen das Testnetz. set_sandbox_mode ist der Schalter."""
    import ccxt
    k, s = schluessel()
    if not k or not s:
        return None
    # [14.09.2026] Umgestellt von Binance auf BYBIT.
    #
    # Warum: Gehandelt wird bei Bybit EU (MiCA-lizenziert) - das ist seit
    # dem 11.08. die Zielboerse, und alle Kostenannahmen des Projekts
    # stammen von dort (K_BASIS_PCT 0,505 % = 2 x 0,25 % Taker, siehe
    # core/kosten.py). Eine Probe am Binance-Testnetz haette den
    # Order-Pfad einer Boerse geprueft, auf der nie gehandelt wird:
    # anderes Orderbuch, andere Mindestgroessen, andere Fehlermeldungen,
    # andere Gebuehrenfelder in der Antwort.
    #
    # Das Testnetz ist Spielgeld - bei MiCA geht es nicht darum. Aber
    # eine Probe soll die Boerse pruefen, die man wirklich benutzt.
    ex = ccxt.bybit({"apiKey": k, "secret": s, "enableRateLimit": True,
                     "options": {"defaultType": "spot",
                                 "adjustForTimeDifference": True}})
    ex.set_sandbox_mode(True)
    return ex


def anleitung():
    print(NL + "  So kommst du an Testnetz-Schluessel:" + NL)
    print("    1. https://testnet.bybit.com aufrufen")
    print("    2. Konto anlegen - ein eigenes TESTNETZ-Konto,")
    print("       nicht das echte")
    print("    3. Unter API auf 'Create New Key'")
    print("       Rechte: nur Trade und Read. KEIN Withdraw.")
    print("    4. Beide Werte in die Datei .env schreiben:" + NL)
    print("         BYBIT_TESTNET_KEY=dein_schluessel")
    print("         BYBIT_TESTNET_SECRET=dein_geheimnis" + NL)
    print("  WICHTIG: das sind EIGENE Testnetz-Schluessel, nicht die")
    print("  echten. Dieses Werkzeug liest nur die zwei mit _TESTNET_")
    print("  im Namen - an deine Live-Schluessel kommt es nicht heran." + NL)
    print("  Danach:  python testnetz_probe.py --pruefen")


def verbindung_pruefen():
    print("=" * 74)
    print("  TESTNETZ - Verbindung und Kontostand")
    print("=" * 74)
    ex = boerse()
    if ex is None:
        print(NL + "  Keine Testnetz-Schluessel gefunden.")
        anleitung()
        return 1
    try:
        ex.load_markets()
        b = ex.fetch_balance()
        t = ex.fetch_ticker(PAAR)
    except Exception as e:
        print(NL + "  Verbindung fehlgeschlagen: " + str(e)[:110])
        print(NL + "  Haeufigste Ursachen:")
        print("    * Schluessel vertippt oder abgelaufen (Testnetz-Schluessel")
        print("      werden regelmaessig zurueckgesetzt)")
        print("    * Uhrzeit des Rechners weicht ab - Bybit lehnt dann ab")
        return 1

    print(NL + "  Verbunden. " + str(len(ex.markets)) + " Maerkte geladen.")
    print("  " + PAAR + ": " + format(t["last"], ",.2f") + " USDT"
          + "   Spanne " + format(
              (t["ask"] - t["bid"]) / t["last"] * 100 if t.get("ask") and t.get("bid")
              else 0, ".4f") + " %")
    print(NL + "  Guthaben (Spielgeld):")
    frei = {k: v for k, v in (b.get("free") or {}).items() if v and v > 0}
    for k in sorted(frei, key=lambda x: -frei[x])[:6]:
        print("    " + k.ljust(8) + format(frei[k], ">18,.8f"))
    if not frei:
        print("    leer - neuen Schluessel erzeugen, das setzt das Guthaben zurueck")
    m = ex.market(PAAR)
    print(NL + "  Regeln der Boerse fuer " + PAAR + ":")
    print("    kleinste Menge   : " + str(m["limits"]["amount"]["min"]))
    print("    kleinster Betrag : " + str(m["limits"]["cost"]["min"]) + " USDT")
    print("    Schrittweite     : " + str(m["precision"]["amount"]))
    print(NL + "  Bereit. Die sechs Pruefungen: python testnetz_probe.py --echt")
    return 0


def probe(echt=False):
    """Die sechs Fragen, die der Papiermodus nicht beantworten kann."""
    print("=" * 74)
    print("  TESTNETZ-PROBE" + ("" if echt else "   -   TROCKENLAUF, sendet nichts"))
    print("=" * 74)
    ex = boerse()
    if ex is None:
        print(NL + "  Keine Testnetz-Schluessel gefunden.")
        anleitung()
        return 1
    try:
        ex.load_markets()
        m = ex.market(PAAR)
        t = ex.fetch_ticker(PAAR)
    except Exception as e:
        print(NL + "  Verbindung fehlgeschlagen: " + str(e)[:110])
        return 1

    kurs = float(t["last"])
    min_kosten = float(m["limits"]["cost"]["min"] or 10)
    # Bewusst knapp ueber dem Mindestbetrag - kleinstmoegliche Probe.
    menge = float(ex.amount_to_precision(PAAR, (min_kosten * 1.05) / kurs))
    print(NL + "  Kurs " + format(kurs, ",.2f") + " USDT, Mindestbetrag "
          + str(min_kosten) + " USDT")
    print("  Probemenge: " + str(menge) + " BTC (rund "
          + format(menge * kurs, ".2f") + " USDT)")

    ergebnisse = []

    def melde(nr, frage, ergebnis, gut):
        ergebnisse.append(gut)
        print(NL + "  " + str(nr) + ") " + frage)
        print("     " + ("OK   " if gut else "PRUEFEN ") + ergebnis)

    if not echt:
        print(NL + "  Im Trockenlauf wird NICHTS gesendet. Was passieren wuerde:")
        for nr, txt in ((1, "Marktorder ueber " + format(menge * kurs, ".2f")
                            + " USDT kaufen und den Fill-Preis mit dem"
                            + NL + "        Sollpreis vergleichen"),
                        (2, "denselben Kauf ein zweites Mal mit DERSELBEN"
                            + " Kennung senden -" + NL
                            + "        die Boerse muss ihn ablehnen, nicht doppelt"
                            + " ausfuehren"),
                        (3, "eine absichtlich ZU KLEINE Order senden - die"
                            + " Boerse muss sie" + NL + "        ablehnen"),
                        (4, "den Auftragsstatus abfragen und mit dem lokalen"
                            + " Stand vergleichen"),
                        (5, "das Gekaufte wieder verkaufen und Gebuehr und"
                            + " Schlupf messen"),
                        (6, "den Kontostand vor und nach allem gegenrechnen")):
            print("    " + str(nr) + ") " + txt)
        print(NL + "  Wirklich ausfuehren:  python testnetz_probe.py --echt")
        return 0

    # ---------------- 1) Kommt eine Order an? ----------------
    kennung = "probe" + str(int(time.time()))
    vorher = ex.fetch_balance()
    try:
        o = ex.create_order(PAAR, "market", "buy", menge,
                            params={"newClientOrderId": kennung})
        gefuellt = float(o.get("filled") or 0)
        preis = float(o.get("average") or o.get("price") or 0)
        schlupf = (preis / kurs - 1) * 100 if preis and kurs else 0
        melde(1, "Kommt eine Order an?",
              "gefuellt " + str(gefuellt) + " zu " + format(preis, ",.2f")
              + " (Sollpreis " + format(kurs, ",.2f") + ", Schlupf "
              + format(schlupf, "+.3f") + " %)", gefuellt > 0)
    except Exception as e:
        melde(1, "Kommt eine Order an?", str(e)[:90], False)
        return 1

    # ---------------- 2) Wird bei Wiederholung doppelt gekauft? ----------------
    try:
        ex.create_order(PAAR, "market", "buy", menge,
                        params={"newClientOrderId": kennung})
        melde(2, "Wiederholung mit derselben Kennung",
              "DURCHGELASSEN - die Boerse hat ein zweites Mal gekauft!", False)
    except Exception as e:
        melde(2, "Wiederholung mit derselben Kennung",
              "abgelehnt (" + type(e).__name__ + ") - richtig so", True)

    # ---------------- 3) Zu kleine Order ----------------
    try:
        ex.create_order(PAAR, "market", "buy", menge / 100.0)
        melde(3, "Zu kleine Order", "DURCHGELASSEN - unerwartet", False)
    except Exception as e:
        melde(3, "Zu kleine Order",
              "abgelehnt: " + str(e)[:70], True)

    # ---------------- 4) Kennt die Boerse den Auftrag? ----------------
    try:
        st = ex.fetch_order(o["id"], PAAR)
        melde(4, "Auftragsstatus abfragbar?",
              "Status '" + str(st.get("status")) + "', gefuellt "
              + str(st.get("filled")), str(st.get("status")) in ("closed", "filled"))
    except Exception as e:
        melde(4, "Auftragsstatus abfragbar?", str(e)[:80], False)

    # ---------------- 5) Rueckverkauf, Gebuehr und Schlupf ----------------
    try:
        t2 = ex.fetch_ticker(PAAR)
        v = ex.create_order(PAAR, "market", "sell", gefuellt)
        vpreis = float(v.get("average") or v.get("price") or 0)
        geb = v.get("fee") or {}
        melde(5, "Rueckverkauf mit Gebuehr und Schlupf",
              "verkauft zu " + format(vpreis, ",.2f") + ", Gebuehr "
              + str(geb.get("cost", "?")) + " " + str(geb.get("currency", ""))
              + ", Schlupf " + format((vpreis / float(t2["last"]) - 1) * 100,
                                      "+.3f") + " %", vpreis > 0)
    except Exception as e:
        melde(5, "Rueckverkauf", str(e)[:90], False)

    # ---------------- 6) Stimmt der Kontostand? ----------------
    try:
        nachher = ex.fetch_balance()
        a = float((vorher.get("total") or {}).get("USDT") or 0)
        b = float((nachher.get("total") or {}).get("USDT") or 0)
        melde(6, "Kontostand nachgerechnet",
              "vorher " + format(a, ",.4f") + " -> nachher " + format(b, ",.4f")
              + "  (Differenz " + format(b - a, "+.4f") + " USDT = Gebuehren)",
              abs(b - a) < max(2.0, menge * kurs * 0.05))
    except Exception as e:
        melde(6, "Kontostand nachgerechnet", str(e)[:80], False)

    gut = sum(1 for x in ergebnisse if x)
    print(NL + "=" * 74)
    print("  " + str(gut) + " von " + str(len(ergebnisse)) + " Pruefungen bestanden")
    if gut < len(ergebnisse):
        print("  Jede nicht bestandene Zeile ist eine Frage, die beim ersten")
        print("  echten Trade aufgetaucht waere - jetzt taucht sie hier auf.")
    print("=" * 74)
    return 0 if gut == len(ergebnisse) else 1


def ohne_schluessel():
    """Die Pruefungen, die KEINE Anmeldung brauchen.

    [21.08.2026] Sven kam an die Testnetz-Seite nicht heran und war mit
    den Nerven am Ende. Beim Nachsehen: die Boersenregeln liefert die Boerse
    ohne jede Anmeldung. Damit lassen sich vier der sechs Fragen sofort
    beantworten - nicht an einer echten Order, sondern am eigenen Code
    gegen die echten Regeln.

    Das ist sogar der bessere Teil: eine Testnetz-Order zeigt, DASS es
    schiefgeht. Diese Pruefung zeigt, WO im Code es schiefgehen wird.
    """
    print("=" * 74)
    print("  VORPRUEFUNG OHNE ANMELDUNG - Code gegen die echten Boersenregeln")
    print("=" * 74)

    # [14.09.2026] Umgestellt von einem festen Binance-Aufruf auf ccxt
    # gegen BYBIT. Gehandelt wird dort, also muessen auch die Regeln von
    # dort kommen: Mindestmengen, Schrittweiten und Mindestbetraege sind
    # je Boerse verschieden, und genau daran scheitert eine erste Order.
    #
    # ccxt statt urllib, weil load_markets() fuer oeffentliche Daten
    # keinen Schluessel braucht und die Felder ueber alle Boersen gleich
    # benennt. Ein fester API-Pfad muesste bei jedem Boersenwechsel neu
    # geschrieben werden.
    try:
        import ccxt
        ex = ccxt.bybit({"enableRateLimit": True,
                         "options": {"defaultType": "spot"}})
        maerkte = ex.load_markets()
    except Exception as e:
        print(NL + "  Regeln nicht abrufbar: " + str(e)[:80])
        return 1

    # Bybit fuehrt USDT-Paare; USDC gibt es dort nur fuer wenige Muenzen.
    wunsch = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    gefunden = [m for m in wunsch if m in maerkte]
    if not gefunden:
        print(NL + "  Keines der drei Paare gefunden - Boerse erreichbar?")
        return 1

    print(NL + "  Was die Boerse verlangt (Bybit Spot):")
    for name in gefunden:
        m = maerkte[name]
        grenzen = m.get("limits") or {}
        menge = (grenzen.get("amount") or {}).get("min")
        betrag = (grenzen.get("cost") or {}).get("min")
        schritt = (m.get("precision") or {}).get("amount")
        print("    " + name.ljust(10)
              + "Mindestmenge " + str(menge).ljust(12)
              + "Schrittweite " + str(schritt).ljust(12)
              + "Mindestbetrag " + str(betrag) + " USDT")

    quelle = open(os.path.join(HIER, "execution", "engine.py"),
                  encoding="utf-8", errors="replace").read()
    pruef = [
        ("Menge auf Schrittweite gerundet",
         "amount_to_precision" in quelle or "amountToPrecision" in quelle,
         "sonst lehnt die Boerse die Order ab"),
        ("Eindeutige Auftragskennung",
         any(w in quelle for w in ("clientOrderId", "newClientOrderId")),
         "ohne sie kauft eine Wiederholung ein zweites Mal"),
        ("Teilausfuehrung behandelt",
         "partial" in quelle.lower(),
         "sonst gilt eine halb gefuellte Order als ganz"),
        ("Mindestbetrag geprueft",
         any(w in quelle for w in ("minNotional", "min_notional", "MIN_NOTIONAL")),
         "kleine Orders werden abgelehnt - im Papiermodus faellt das nie auf"),
        ("Auftragsstatus abgefragt",
         "fetch_order(" in quelle,
         "nach Zeitueberschreitung oder Neustart weiss der Bot sonst nicht, "
         "ob die Order durchging"),
    ]
    print(NL + "  Was unser Order-Pfad tut (execution/engine.py):" + NL)
    fehlt = []
    for name, ok, warum in pruef:
        print("    " + ("OK    " if ok else "FEHLT ") + name)
        if not ok:
            fehlt.append((name, warum))
            print("           -> " + warum)

    print(NL + "  " + str(len(pruef) - len(fehlt)) + " von " + str(len(pruef))
          + " vorhanden.")
    if fehlt:
        print(NL + "  Diese Luecken fallen im Papiermodus NIE auf - dort wird")
        print("  gerechnet, nicht gesendet. Sie tauchen beim ersten echten")
        print("  Trade auf, und dann kosten sie Geld.")
    print(NL + "  Nicht ohne Anmeldung pruefbar: der echte Fill-Preis und der")
    print("  echte Schlupf. Dafuer braucht es Testnetz-Schluessel.")
    return 1 if fehlt else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Order-Pfad am Bybit-Testnetz")
    p.add_argument("--pruefen", action="store_true",
                   help="nur Verbindung und Kontostand")
    p.add_argument("--echt", action="store_true",
                   help="die sechs Pruefungen wirklich senden")
    p.add_argument("--ohne-schluessel", action="store_true",
                   help="was ohne Anmeldung geht: Code gegen die Boersenregeln")
    a = p.parse_args()
    if getattr(a, "ohne_schluessel", False):
        sys.exit(ohne_schluessel())
    if a.pruefen:
        sys.exit(verbindung_pruefen())
    sys.exit(probe(echt=a.echt))
