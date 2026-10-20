# -*- coding: utf-8 -*-
"""Raeumt Positionen auf, die verkauft wurden, aber im Register stehen.

DER VORFALL (15.09.2026, 14:23)
-------------------------------
Der Stop-Loss fuer ETH loeste aus, der Verkauf ging durch - die Boerse
fuehrte 0,0041 ETH fuer 9,99 $ aus. Eine Sekunde spaeter stand im Log:

    [ERROR] Order ueber KEINEN Weg abfragbar - Zustand UNBEKANNT
    [ERROR] Order NICHT gefuellt - Boerse meldet keine Ausfuehrung

Der Bot hielt seinen eigenen, erfolgreichen Verkauf fuer gescheitert.
Folgen, zwei Stunden lang:

    * Die Position blieb im Register
    * Alle 30 Sekunden loeste derselbe Stop-Loss erneut aus
    * Die Buchhaltung wies 27 % Gewinn aus, den es nicht gab
    * Der Verkauf fehlte im Journal - und damit in jeder Auswertung

URSACHE ist in execution/engine.py behoben (dreimal nachfragen statt
in derselben Sekunde aufzugeben). Dieses Werkzeug raeumt auf, was
vorher liegengeblieben ist.

WARUM EIN WERKZEUG UND KEIN AUTOMATISMUS
----------------------------------------
Eine Position aus dem Register zu loeschen ist Datenaenderung. Wenn
die Annahme falsch ist - die Coins liegen doch noch da -, verliert der
Bot den Stop-Loss auf einen echten Bestand. Das waere schlimmer als
das Problem.

Deshalb entscheidet ein Mensch, und deshalb prueft dieses Programm
VORHER drei Dinge, von denen jede einzelne den Abbruch ausloest:

    1. Steht die Position wirklich im Register?
    2. Ist der Boersenbestand wirklich (fast) leer?
    3. Gibt es in den Ausfuehrungen einen passenden Verkauf?

Erst wenn alle drei zutreffen, wird etwas geaendert - und dann mit
den ECHTEN Zahlen der Boerse, damit Gewinn und Verlust im Journal
stimmen.

Aufruf:  PHANTOM_BEREINIGEN.bat  (Doppelklick)
"""
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE = os.path.join("data_store", "bot_state.json")
TRADES = os.path.join("data_store", "trades_v5.json")


def sichern(pfad):
    stempel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ziel = f"{pfad}.vor_bereinigung_{stempel}"
    shutil.copy(pfad, ziel)
    return ziel


def main():
    print()
    print("=" * 74)
    print("  PHANTOM-POSITIONEN BEREINIGEN")
    print("=" * 74)
    print()

    if not os.path.exists(STATE):
        print(f"  {STATE} nicht gefunden.")
        return 1

    # --- Bot darf dabei NICHT laufen -------------------------------
    # Er haelt die Positionen im Arbeitsspeicher und schreibt sie
    # zyklisch in die Datei. Eine Aenderung an der Datei waere beim
    # naechsten Speichern ueberschrieben - Befund 97.
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
            print(f"  DER BOT LAEUFT (PID {laeuft}).")
            print()
            print("  Er haelt die Positionen im Arbeitsspeicher und schreibt")
            print("  sie zyklisch in die Datei. Was hier geaendert wird,")
            print("  waere beim naechsten Speichern wieder weg - Befund 97.")
            print()
            print("  Bitte erst den Bot beenden, dann dieses Werkzeug,")
            print("  dann neu starten.")
            print()
            return 1
    except ImportError:
        print("  (psutil fehlt - konnte nicht pruefen, ob der Bot laeuft)")
        print()

    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    positionen = state.get("open_positions_backup", {}) or {}
    if not positionen:
        print("  Keine Positionen im Register. Nichts zu tun.")
        return 0

    print(f"  Register: {len(positionen)} Position(en)")
    for sym, p in positionen.items():
        print(f"    {sym}  qty={p.get('qty')}  Einstand={p.get('entry_price')}")
    print()

    # --- Boerse fragen ---------------------------------------------
    try:
        from bestand_pruefen import verbinde
        ex = verbinde()
        if ex is None:
            return 1
        bal = ex.fetch_balance()
    except Exception as e:
        print(f"  Boerse nicht erreichbar: {str(e)[:100]}")
        print("  Ohne den echten Bestand wird hier NICHTS geaendert.")
        return 1

    total = bal.get("total", {}) or {}
    verdaechtig = []

    for sym, p in positionen.items():
        asset = sym.split("/")[0]
        reg = float(p.get("qty") or 0)
        echt = float(total.get(asset) or 0)
        try:
            m = ex.market(sym)
            minmenge = float(((m.get("limits") or {}).get("amount") or {})
                             .get("min") or 0)
            minwert = float(((m.get("limits") or {}).get("cost") or {})
                            .get("min") or 0)
        except Exception:
            minmenge = minwert = 0.0
        try:
            kurs = float(ex.fetch_ticker(sym).get("last") or 0)
        except Exception:
            kurs = 0.0

        wert = echt * kurs
        print(f"  {sym}")
        print(f"    Register  {reg:.8f}")
        print(f"    Boerse    {echt:.8f}   (~{wert:.2f} $)")

        # Phantom heisst: Das Register fuehrt etwas, das die Boerse
        # nicht mehr hat - und der Rest ist so klein, dass er gar
        # nicht verkauft werden koennte.
        if echt >= reg * 0.98:
            print(f"    -> in Ordnung, Bestand deckt die Position")
            continue
        if minwert and wert >= minwert:
            print(f"    -> Bestand kleiner als das Register, aber noch")
            print(f"       verkaufbar ({wert:.2f} $ >= {minwert:.2f} $).")
            print(f"       KEINE Bereinigung - hier koennte ein Teilverkauf")
            print(f"       vorliegen. Bitte von Hand ansehen.")
            continue

        print(f"    -> VERDAECHTIG: Register fuehrt {reg:.8f}, verkaufbar")
        print(f"       sind nur {wert:.2f} $ (Mindestwert {minwert:.2f} $)")
        verdaechtig.append((sym, p, reg, echt, kurs))

    if not verdaechtig:
        print()
        print("  Keine Phantom-Position gefunden. Nichts zu tun.")
        return 0

    # --- Den echten Verkauf suchen ---------------------------------
    print()
    print("  Suche die zugehoerigen Verkaeufe in den Ausfuehrungen...")
    print()
    bereinigen = []
    for sym, p, reg, echt, kurs in verdaechtig:
        try:
            trades = ex.fetch_my_trades(sym, limit=50)
        except Exception as e:
            print(f"    {sym}: Ausfuehrungen nicht abrufbar ({str(e)[:60]})")
            continue

        # Der juengste Verkauf, der zur Position passt
        verkaeufe = [t for t in (trades or [])
                     if str(t.get("side", "")).lower() == "sell"]
        verkaeufe.sort(key=lambda t: t.get("timestamp") or 0, reverse=True)
        if not verkaeufe:
            print(f"    {sym}: KEIN Verkauf in den Ausfuehrungen gefunden.")
            print(f"       Dann ist unklar, wo die Coins geblieben sind -")
            print(f"       hier wird NICHTS geaendert. Bitte nachsehen.")
            continue

        v = verkaeufe[0]
        menge = float(v.get("amount") or 0)
        preis = float(v.get("price") or 0)
        erloes = float(v.get("cost") or 0)
        geb = float((v.get("fee") or {}).get("cost") or 0)
        gw = str((v.get("fee") or {}).get("currency") or "").upper()

        # P&L gegen die echte Kostenbasis
        basis = float(p.get("cost_basis") or 0)
        if basis <= 0:
            basis = menge * float(p.get("entry_price") or 0)
        anteil = (menge / reg) if reg else 1.0
        pnl = erloes - basis * anteil - (geb if gw not in
                                         (sym.split("/")[0].upper(),) else 0)

        print(f"    {sym}: Verkauf gefunden")
        print(f"       {v.get('datetime')}  {menge:.8f} @ {preis:,.2f} $")
        print(f"       Erloes {erloes:.4f} $, Kostenbasis {basis * anteil:.4f} $")
        print(f"       -> P&L {pnl:+.4f} $")
        bereinigen.append((sym, v, menge, preis, erloes, pnl))

    if not bereinigen:
        print()
        print("  Nichts belegbar. Es wurde NICHTS geaendert.")
        return 1

    # --- Nachfragen -------------------------------------------------
    print()
    print("  " + "-" * 70)
    print("  Zu bereinigen:")
    for sym, v, menge, preis, erloes, pnl in bereinigen:
        print(f"    {sym}: Position entfernen, Verkauf ins Journal "
              f"({menge:.8f} @ {preis:,.2f} $, P&L {pnl:+.4f} $)")
    print("  " + "-" * 70)
    print()
    antwort = input("  Durchfuehren? (ja/nein): ").strip().lower()
    if antwort not in ("ja", "j"):
        print("\n  Abgebrochen. Nichts geaendert.\n")
        return 1

    # --- Ausfuehren -------------------------------------------------
    s1 = sichern(STATE)
    print(f"\n  Sicherung: {os.path.basename(s1)}")

    for sym, v, menge, preis, erloes, pnl in bereinigen:
        positionen.pop(sym, None)
    state["open_positions_backup"] = positionen
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  {len(bereinigen)} Position(en) aus dem Register entfernt")

    # Journal ergaenzen, damit der Verkauf in den Auswertungen auftaucht
    if os.path.exists(TRADES):
        s2 = sichern(TRADES)
        print(f"  Sicherung: {os.path.basename(s2)}")
        with open(TRADES, encoding="utf-8") as f:
            trades = json.load(f)
        if not isinstance(trades, list):
            trades = []
        for sym, v, menge, preis, erloes, pnl in bereinigen:
            trades.append({
                "time": v.get("datetime"),
                "type": "SELL",
                "coin": sym,
                "qty": menge,
                "price": preis,
                "amount": erloes,
                "pnl": pnl,
                "strategy": "STOP_LOSS",
                "reason": ("Nachgetragen am "
                           + datetime.datetime.now().strftime("%d.%m.%Y")
                           + ": Verkauf ging durch, der Bot hielt ihn fuer "
                             "gescheitert (Abfrage in derselben Sekunde). "
                             "Zahlen aus den Boersen-Ausfuehrungen."),
                "_nachgetragen": True,
            })
        with open(TRADES, "w", encoding="utf-8") as f:
            json.dump(trades, f, indent=2, ensure_ascii=False)
        print(f"  {len(bereinigen)} Verkauf/Verkaeufe ins Journal nachgetragen")

    print()
    print("=" * 74)
    print("  FERTIG. Der Bot kann wieder gestartet werden.")
    print()
    print("  Beim naechsten Start sollte er:")
    print("    - die Phantom-Position nicht mehr fuehren")
    print("    - keinen Stop-Loss mehr darauf ausloesen")
    print("    - eine Buchhaltung zeigen, die zum Konto passt")
    print()
    print("  Rueckgaengig: die Sicherungsdateien zurueckkopieren.")
    print("=" * 74)
    print()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Abgebrochen. Nichts geaendert.\n")
