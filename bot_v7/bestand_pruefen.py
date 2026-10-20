# -*- coding: utf-8 -*-
"""bestand_pruefen.py - Was liegt WIRKLICH auf dem Bybit-EU-Konto?

Reines Lesen. Legt keine Order an, aendert keine Datei, startet nichts.

WOZU
----
Der Bot fuehrte am 14.09. vier Kaeufe aus, die er selbst fuer
gescheitert hielt. Die Coins liegen auf dem Konto, in seinem Register
stehen sie nicht - also bewacht sie kein Stop-Loss.

Bevor die Reparatur (runtime/state_manager.py: _uebernehme_live_bestand)
diese Bestaende uebernimmt, muss feststehen:

    1. Wieviel liegt da?
    2. Zu welchem Preis wurde es gekauft?

Punkt 2 ist der wichtige. Der Stop-Loss haengt an dieser Zahl. Wuerde
man den AKTUELLEN Kurs als Einstand nehmen - so wie es die
Papier-Rekonstruktion tut -, waere ein bereits aufgelaufener
Buchverlust unsichtbar und der Stop-Loss saesse am falschen Punkt.

Der echte Einstand steht nur an einer Stelle: in den Ausfuehrungen der
Boerse (fetch_my_trades). Genau die Quelle, ueber die am 14.09. abends
auch die Fuell-Erkennung repariert wurde.

Aufruf:  FRAKTAL_PRUEFEN.bat  (Doppelklick, Schritt 1 von 3)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def verbinde():
    """Baut die Boersenverbindung GENAU wie execution/engine.py:180-202.

    Bewusst nachgebaut statt die App zu importieren: Der Import zieht
    den ganzen Bot hoch, inklusive Hintergrund-Jobs und Telegram. Dieses
    Werkzeug soll nur lesen.

    Die drei Fallen vom 14.09. sind alle drei beruecksichtigt:
      1. hostname bybit.eu     - sonst landet man auf bybit.com
      2. defaultType unified   - sonst "accountType only support UNIFIED"
                                 und ein leerer Kontostand trotz Guthaben
      3. recvWindow gross      - sonst Zeitversatz-Fehler
    """
    import ccxt

    # [25.09.2026] Hier stand `from dotenv import load_dotenv` in einem
    # try/except: pass. python-dotenv ist in diesem Projekt bewusst NICHT
    # installiert - requirements.txt Zeile 67: ".env-Laden nutzt einen
    # eigenen Parser in settings.py -> python-dotenv wird NICHT gebraucht."
    # Der Import schlug also JEDES Mal fehl, das `pass` verschluckte es,
    # und danach meldete dieses Werkzeug "Keine Bybit-Zugangsdaten in .env
    # gefunden" - obwohl beide Schluessel dastanden. Ein stilles Scheitern,
    # das als Sachaussage ueber die .env daherkam: die gefaehrlichere Sorte,
    # weil man aufhoert zu suchen.
    #
    # Richtig ist der Parser des Projekts, config/settings.py:21
    # (_load_env, laeuft beim Import und schreibt nach os.environ).
    import config.settings          # noqa: F401 - laedt .env nach os.environ

    key = os.getenv("BYBIT_API_KEY", "")
    secret = os.getenv("BYBIT_API_SECRET", "")
    if not key or not secret:
        print("  FEHLER: Keine Bybit-Zugangsdaten gefunden.")
        print("         Gesucht: BYBIT_API_KEY und BYBIT_API_SECRET,")
        print("         geladen ueber config/settings.py aus .env.")
        print("         Der Inhalt der .env wird nicht angezeigt.")
        return None

    ex = ccxt.bybit({
        "apiKey": key,
        "secret": secret,
        "enableRateLimit": True,
        "hostname": "bybit.eu",
        "options": {"defaultType": "unified",
                    "adjustForTimeDifference": True,
                    "recvWindow": 60000},
    })
    ex.load_markets()
    return ex


def einstand_aus_ausfuehrungen(ex, symbol, menge_vorhanden):
    """Rechnet den echten Einstand eines vorhandenen Bestands aus.

    Verfahren: Die Ausfuehrungen von neu nach alt durchgehen und die
    KAEUFE aufsammeln, bis ihre Summe die vorhandene Menge deckt. Der
    letzte Kauf wird anteilig angerechnet.

    GRENZE DES VERFAHRENS - bitte mitlesen:
    Das ist eine "zuletzt gekauft"-Annahme. Sie ist exakt richtig,
    solange zwischendurch NICHT verkauft wurde. Wurde verkauft, ist sie
    eine Naeherung. Die Funktion meldet deshalb mit, ob sie Verkaeufe
    gesehen hat.

    Dieselbe Rechnung steckt in execution/engine.py: bestand_einstand().
    Hier steht sie ein zweites Mal, damit dieses Werkzeug ohne die App
    laeuft - und damit man beide Ergebnisse gegeneinander halten kann.
    """
    try:
        trades = ex.fetch_my_trades(symbol, limit=100)
    except Exception as e:
        print(f"      fetch_my_trades fehlgeschlagen: {str(e)[:90]}")
        return None

    if not trades:
        return None

    trades = sorted(trades, key=lambda t: t.get("timestamp") or 0,
                    reverse=True)
    verkaeufe = sum(1 for t in trades
                    if str(t.get("side", "")).lower() == "sell")

    basis_coin = symbol.split("/")[0]
    rest = float(menge_vorhanden)
    menge_ges = 0.0
    kosten_ges = 0.0
    gebuehr_quote = 0.0     # Gebuehr in USDC
    gebuehr_basis = 0.0     # Gebuehr in BTC/ETH/SOL
    satz = None
    benutzt = []

    for t in trades:
        if rest <= 1e-12:
            break
        if str(t.get("side", "")).lower() != "buy":
            continue
        menge = float(t.get("amount") or 0)
        preis = float(t.get("price") or 0)
        if menge <= 0 or preis <= 0:
            continue
        nimm = min(menge, rest)
        anteil = nimm / menge

        # GEBUEHRENWAEHRUNG - an den echten Ausfuehrungen vom 14.09.
        # gefunden: Bybit zieht die Spot-Kaufgebuehr in der GEKAUFTEN
        # MUENZE ab, nicht in USDC:
        #     fee = {'currency': 'BTC', 'cost': 3.425e-07, 'rate': 0.0025}
        # Diese Zahl zu Dollar zu addieren, mischt zwei Waehrungen.
        # Wer in Coins zahlt, bekommt weniger Coins - der Dollarbetrag
        # ist bereits der volle Einsatz.
        f = t.get("fee") or {}
        fc = float(f.get("cost") or 0) * anteil
        fw = str(f.get("currency") or "").upper()
        if f.get("rate") is not None:
            satz = float(f.get("rate"))
        if fw == basis_coin:
            gebuehr_basis += fc
        else:
            gebuehr_quote += fc

        menge_ges += nimm
        kosten_ges += nimm * preis
        rest -= nimm
        benutzt.append({"zeit": t.get("datetime"), "menge": nimm,
                        "preis": preis, "gebuehr": fc, "waehrung": fw,
                        "teilweise": nimm < menge - 1e-12})

    if menge_ges <= 0:
        return None

    return {
        "menge": menge_ges,
        "preis_schnitt": kosten_ges / menge_ges,
        "kosten": kosten_ges,
        "gebuehr": gebuehr_quote,
        "gebuehr_in_coins": gebuehr_basis,
        "satz": satz,
        "kostenbasis": kosten_ges + gebuehr_quote,
        "ungedeckt": rest,
        "verkaeufe_gesehen": verkaeufe,
        "ausfuehrungen": benutzt,
        "gesamt_ausfuehrungen": len(trades),
    }


def main():
    print()
    print("=" * 72)
    print("  WAS LIEGT WIRKLICH AUF DEM KONTO?   (reines Lesen)")
    print("=" * 72)

    ex = verbinde()
    if ex is None:
        return 1

    print("\n  Verbunden mit bybit.eu (Konto UNIFIED)\n")

    try:
        bal = ex.fetch_balance()
    except Exception as e:
        print(f"  FEHLER beim Kontostand: {str(e)[:120]}")
        return 1

    total = bal.get("total", {}) or {}
    bestand = {k: float(v) for k, v in total.items() if float(v or 0) > 0}

    print("  KONTOSTAND")
    print("  " + "-" * 68)
    if not bestand:
        print("    (leer)")
    for coin, menge in sorted(bestand.items()):
        print(f"    {coin:8} {menge:>18.8f}")
    print()

    coins = ["BTC/USDC", "ETH/USDC", "SOL/USDC"]
    print("  BESTAENDE - echter Einstand aus den Ausfuehrungen")
    print("  " + "-" * 68)

    gefunden = False
    for symbol in coins:
        asset = symbol.split("/")[0]
        menge = bestand.get(asset, 0.0)
        if menge <= 0:
            continue
        gefunden = True

        try:
            kurs = float(ex.fetch_ticker(symbol).get("last") or 0)
        except Exception:
            kurs = 0.0

        # Kann die Boerse diese Menge ueberhaupt verkaufen? Wenn nicht,
        # taugt sie nicht als Position - ein Stop-Loss darauf wuerde bei
        # jedem Ausloesen scheitern.
        try:
            m = ex.market(symbol)
            min_menge = float(((m.get("limits") or {}).get("amount") or {})
                              .get("min") or 0)
        except Exception:
            min_menge = 0.0

        print(f"\n    {symbol}   Bestand {menge:.8f} {asset}"
              f"   Marktwert ~{menge * kurs:,.2f} $")
        if min_menge:
            passt = "ja" if menge >= min_menge else "NEIN - nicht verkaufbar!"
            print(f"      Mindestmenge Boerse: {min_menge:.8f}   verkaufbar: {passt}")

        e = einstand_aus_ausfuehrungen(ex, symbol, menge)
        if not e:
            print("      KEINE Ausfuehrungen gefunden - Einstand unbekannt.")
            print("      Dann darf KEINE Position angelegt werden: ein")
            print("      Stop-Loss auf geratener Zahl sieht aus wie Schutz")
            print("      und ist keiner.")
            continue

        print(f"      Einstand (Schnitt) : {e['preis_schnitt']:>14,.2f} $")
        print(f"      aktueller Kurs     : {kurs:>14,.2f} $")
        print(f"      Kostenbasis        : {e['kostenbasis']:>14,.4f} $")
        if e.get("satz") is not None:
            print(f"      GEBUEHRENSATZ      : {e['satz'] * 100:>14.4f} %"
                  f"   <- von der Boerse gemeldet, an echten Kaeufen")
        if e.get("gebuehr_in_coins"):
            print(f"      Gebuehr in {asset:<8}: {e['gebuehr_in_coins']:>14.8f}"
                  f"   (in Coins abgezogen, nicht in USDC)")
        if e.get("gebuehr"):
            print(f"      Gebuehr in USDC    : {e['gebuehr']:>14.4f} $")
        if kurs > 0:
            gv = (menge * kurs) - e["kostenbasis"]
            pct = gv / e["kostenbasis"] * 100 if e["kostenbasis"] else 0
            print(f"      Buchstand JETZT    : {gv:>+14,.4f} $   ({pct:+.3f} %)")
            # Der Grund, warum der echte Einstand zaehlt:
            sl_echt = e["preis_schnitt"] * 0.975
            sl_falsch = kurs * 0.975
            print(f"      Stop-Loss bei -2,5 %:")
            print(f"        auf echtem Einstand : {sl_echt:>12,.2f} $")
            print(f"        auf heutigem Kurs   : {sl_falsch:>12,.2f} $"
                  f"   <- waere {sl_echt - sl_falsch:+,.2f} $ zu tief")
        print(f"      Ausfuehrungen      : {len(e['ausfuehrungen'])} benutzt"
              f" von {e['gesamt_ausfuehrungen']} gefundenen")
        if e["ungedeckt"] > 1e-10:
            print(f"      ACHTUNG: {e['ungedeckt']:.8f} {asset} ohne passenden"
                  f" Kauf - Einstand nur teilweise belegt!")
        if e["verkaeufe_gesehen"]:
            print(f"      ACHTUNG: {e['verkaeufe_gesehen']} Verkauf/Verkaeufe in"
                  f" der Historie - Einstand ist eine Naeherung!")

        print("      Einzelne Ausfuehrungen (Gegenprobe von Hand):")
        for a in e["ausfuehrungen"]:
            marke = "  (anteilig)" if a["teilweise"] else ""
            print(f"        {a['zeit']}  {a['menge']:.8f} @ {a['preis']:,.2f} $"
                  f"  Geb {a['gebuehr']:.10f} {a.get('waehrung', '?')}{marke}")

        # GEGENPROBE (CLAUDE.md Abschnitt 0): Summe der Einzelposten
        # gegen die Sammelzahl. Stimmen sie nicht, ist die Zahl falsch -
        # und zwar bevor jemand sie benutzt.
        summe = sum(a["menge"] * a["preis"] for a in e["ausfuehrungen"])
        abw = abs(summe - e["kosten"])
        print(f"      GEGENPROBE: Summe Einzelposten {summe:,.6f} $ gegen"
              f" Sammelwert {e['kosten']:,.6f} $  ->  Abweichung {abw:.10f}")
        if abw > 1e-6:
            print("      !! ABWEICHUNG ZU GROSS - Zahl nicht verwenden !!")

    if not gefunden:
        print("    Keine Coin-Bestaende. Nichts zu uebernehmen.")

    print()
    print("=" * 72)
    print("  Fertig. Es wurde NICHTS veraendert und NICHTS gehandelt.")
    print("=" * 72)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen.")
