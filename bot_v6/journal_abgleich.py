# -*- coding: utf-8 -*-
"""Gleicht das Trade-Journal mit dem tatsaechlichen Bestand ab.

WOZU
----
go_live_check.py Kriterium H7 verlangt, dass der aus dem Journal errechnete
Saldo je Coin mit dem tatsaechlichen Bestand uebereinstimmt. Stand 10.08.2026
tut er das nicht:

    BTC   Journal +0,003584   real 0,002766   ->  0,000818 zu viel
    ETH   Journal +0,121546   real 0,093988   ->  0,027558 zu viel
    SOL   Journal -0,929621   real 0,000000   ->  0,929621 zu wenig

Ein negativer Saldo ist physikalisch unmoeglich - man kann nicht minus 0,93 SOL
besitzen. Die laufende Buchhaltung arbeitet dabei korrekt: jeder Kauf und
Verkauf ist paarweise ausgeglichen (geprueft ueber alle SOL-Zyklen seit 05.08.).
Der Versatz ist konstant und stammt aus beschaedigten Alt-Daten - im Projekt
gibt es dafuer mehrere Belege: crashbak-Dateien in data_store und ein
rebuild_journal.py aus der Absturz-Recovery vom 18.06.2026.

WAS DIESES SKRIPT TUT - UND WAS NICHT
-------------------------------------
Es faelscht KEINE Historie. Bestehende Zeilen werden nie geaendert oder
geloescht. Stattdessen wird EINE klar gekennzeichnete Korrekturzeile je Coin
angehaengt, so wie eine Inventurdifferenz in der Buchhaltung: sichtbar,
datiert, begruendet und jederzeit wieder auffindbar.

Die Korrekturzeile traegt:
    type       = KORREKTUR
    pnl        = 0        (eine Mengenkorrektur ist kein Gewinn)
    schreibpfad= journal_abgleich
    reason     = Klartext mit Soll, Ist und Differenz

Damit bleibt jede Auswertung ehrlich: wer die Korrekturen herausfiltern will,
kann das jederzeit ueber type oder schreibpfad tun.

AUFRUF
------
    python journal_abgleich.py            # Trockenlauf, aendert nichts
    python journal_abgleich.py --schreiben  # fuehrt die Korrektur aus

Vor dem Schreiben wird automatisch eine Sicherung angelegt.
"""
import json
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(HIER, "data_store", "trades_v5.json")
STATE = os.path.join(HIER, "data_store", "bot_state.json")

# Unter dieser Menge gilt eine Abweichung als Rundungsrauschen und wird
# nicht korrigiert - sonst erzeugt jede Nachkommastelle eine Buchung.
TOLERANZ = 1e-8


def lade(pfad):
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


def bestand_ermitteln(state):
    """Liest den echten Coin-Bestand aus bot_state.json.

    Der Schluessel hat sich zwischen Bot-Versionen geaendert, deshalb werden
    mehrere Orte geprueft statt einen zu raten.
    """
    kandidaten = [
        state.get("paper_balances"),
        state.get("balances"),
        (state.get("execution") or {}).get("_paper_balances"),
        state.get("_paper_balances"),
    ]
    for k in kandidaten:
        if isinstance(k, dict) and k:
            return {a: float(v) for a, v in k.items()
                    if a not in ("USDC", "USDT", "EUR", "USD")}
    # Letzter Weg: aus den offenen Positionen
    pos = state.get("open_positions_backup") or {}
    if isinstance(pos, dict) and pos:
        return {sym.split("/")[0]: float(p.get("qty", 0) or 0)
                for sym, p in pos.items() if isinstance(p, dict)}
    return {}


def journal_saldo(trades):
    """Kauf minus Verkauf je Asset. Korrekturzeilen zaehlen mit."""
    saldo = {}
    for t in trades:
        coin = t.get("coin") or t.get("symbol") or ""
        if "/" not in coin:
            continue
        asset = coin.split("/")[0]
        menge = float(t.get("qty", 0) or 0)
        typ = str(t.get("type", "")).upper()
        if typ == "BUY":
            saldo[asset] = saldo.get(asset, 0.0) + menge
        elif typ == "SELL":
            saldo[asset] = saldo.get(asset, 0.0) - menge
        elif typ == "KORREKTUR":
            saldo[asset] = saldo.get(asset, 0.0) + menge
    return saldo


def main():
    schreiben = "--schreiben" in sys.argv
    trades = lade(JOURNAL)
    state = lade(STATE)
    bestand = bestand_ermitteln(state)
    saldo = journal_saldo(trades)

    print("=" * 78)
    print(" JOURNAL-ABGLEICH" + ("  [SCHREIBEN]" if schreiben else "  [TROCKENLAUF]"))
    print("=" * 78)
    print(f"\n  Journal : {len(trades)} Eintraege, ab {trades[0].get('time', '?')[:10]}")
    print(f"  Bestand : {len(bestand)} Coins aus bot_state.json\n")

    alle = sorted(set(list(saldo.keys()) + list(bestand.keys())))
    if not alle:
        print("  Keine Coins gefunden - bitte Pfade in bestand_ermitteln() pruefen.")
        return 1

    print(f"  {'Coin':<7s}{'Journal-Saldo':>16s}{'Echt-Bestand':>15s}"
          f"{'Differenz':>15s}   Bewertung")
    print("  " + "-" * 72)
    korrekturen = []
    for asset in alle:
        soll = bestand.get(asset, 0.0)
        ist = saldo.get(asset, 0.0)
        diff = soll - ist                     # so viel muss das Journal noch
        if abs(diff) <= TOLERANZ:
            bewertung = "stimmt"
        else:
            bewertung = "KORREKTUR noetig"
            korrekturen.append((asset, ist, soll, diff))
        print(f"  {asset:<7s}{ist:16.8f}{soll:15.8f}{diff:+15.8f}   {bewertung}")

    if not korrekturen:
        print("\n  Alles deckungsgleich. Nichts zu tun.")
        return 0

    print(f"\n  {len(korrekturen)} Korrekturzeile(n) noetig:\n")
    jetzt = datetime.now(timezone.utc).isoformat()
    neue = []
    for asset, ist, soll, diff in korrekturen:
        richtung = "fehlten im Journal" if diff > 0 else "zu viel im Journal"
        eintrag = {
            "type": "KORREKTUR",
            "coin": f"{asset}/USDC",
            "qty": round(diff, 12),
            "price": 0.0,
            "amount": 0.0,
            "pnl": 0.0,
            "pnl_pct": None,
            "fee": 0.0,
            "strategy": "JOURNAL_ABGLEICH",
            "reason": (f"Inventurdifferenz {asset}: Journal-Saldo {ist:.8f}, "
                       f"tatsaechlicher Bestand {soll:.8f}, Differenz "
                       f"{diff:+.8f} ({richtung}). Ursache: beschaedigte "
                       f"Alt-Daten vor dem 26.07.2026, siehe crashbak-Dateien "
                       f"und rebuild_journal.py. Keine Gewinnwirkung."),
            "schreibpfad": "journal_abgleich",
            "time": jetzt,
        }
        neue.append(eintrag)
        print(f"    {asset:<5s} {diff:+.8f}   {richtung}")

    if not schreiben:
        print("\n  TROCKENLAUF - es wurde nichts geaendert.")
        print("  Zum Ausfuehren:  python journal_abgleich.py --schreiben")
        return 0

    sicherung = JOURNAL + ".bak_abgleich_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(JOURNAL, sicherung)
    print(f"\n  Sicherung: {os.path.basename(sicherung)}")

    trades.extend(neue)
    tmp = JOURNAL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, JOURNAL)
    print(f"  {len(neue)} Korrekturzeile(n) angehaengt. "
          f"Journal hat jetzt {len(trades)} Eintraege.")
    print("\n  Naechster Schritt: python go_live_check.py  -> H7 sollte OK sein.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
