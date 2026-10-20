#!/usr/bin/env python3
"""
EDELMETALL-CHECK (welche Metalle gibt es auf Binance?)
Risikoloser Standalone-Check. Faesst deinen Bot NICHT an.
Braucht keine API-Keys (nur oeffentliche Marktdaten).
"""
import sys

try:
    import ccxt
except ImportError:
    print("FEHLER: ccxt fehlt. Installieren mit:")
    print("  pip install ccxt")
    sys.exit(1)


KANDIDATEN = {
    "PAXG": "Gold  (PAX Gold - durch echtes Gold gedeckt)",
    "XAUT": "Gold  (Tether Gold - Alternative)",
    "KAG":  "Silber (Kinesis Silver)",
    "KAU":  "Gold  (Kinesis Gold)",
    "AABBG": "Gold  (AABB Gold)",
}

QUOTES = ["USDT", "USDC", "FDUSD", "BUSD"]


def banner(t): print("\n" + "=" * 60 + f"\n  {t}\n" + "=" * 60)


def main():
    banner("EDELMETALL-CHECK auf Binance")

    print("  Verbinde mit Binance (oeffentliche Daten)...")
    ex = ccxt.binance()
    try:
        ex.load_markets()
    except Exception as e:
        print(f"  FEHLER beim Verbinden: {e}")
        return 1
    print(f"  OK - {len(ex.markets)} Maerkte geladen\n")

    print("=" * 60)
    print("  BEKANNTE EDELMETALL-TOKEN")
    print("=" * 60)
    gefunden = []
    for base, beschreibung in KANDIDATEN.items():
        paare = []
        for q in QUOTES:
            sym = f"{base}/{q}"
            if sym in ex.markets and ex.markets[sym].get("active", True):
                paare.append(sym)
        if paare:
            sym = paare[0]
            try:
                t = ex.fetch_ticker(sym)
                preis = t.get("last", 0)
                vol = t.get("quoteVolume", 0) or 0
                print(f"\n  [JA] {base:<6} {beschreibung}")
                print(f"       Paare: {', '.join(paare)}")
                print(f"       Kurs:  {preis:,.2f} $")
                print(f"       24h-Volumen: {vol:,.0f} $", end="")
                if vol > 1_000_000:
                    print("  (gut handelbar)")
                elif vol > 100_000:
                    print("  (ok handelbar)")
                else:
                    print("  (WENIG Volumen - Vorsicht)")
                gefunden.append((base, sym, preis, vol))
            except Exception as e:
                print(f"\n  [?]  {base:<6} gelistet, aber Kurs-Fehler: {str(e)[:40]}")
        else:
            print(f"  [NEIN] {base:<6} {beschreibung} - nicht auf Binance")

    print("\n" + "=" * 60)
    print("  FREIE SUCHE (alles mit 'gold'/'silver' im Namen)")
    print("=" * 60)
    treffer = set()
    for sym, m in ex.markets.items():
        base = str(m.get("base", ""))
        quote = str(m.get("quote", ""))
        if quote not in QUOTES:
            continue
        if any(w in base.lower() for w in ["gold", "silver", "xau", "xag"]):
            treffer.add(base)
    if treffer:
        for b in sorted(treffer):
            print(f"       gefunden: {b}")
    else:
        print("       (nichts zusaetzliches gefunden)")

    banner("FAZIT")
    gold = [g for g in gefunden if "Gold" in KANDIDATEN.get(g[0], "")]
    silber = [g for g in gefunden if "Silber" in KANDIDATEN.get(g[0], "")]

    if gold:
        best = max(gold, key=lambda x: x[3])
        print(f"  GOLD: {best[0]} ({best[1]}) - bestes Volumen")
        print(f"        -> dafuer bauen wir den Tab")
    else:
        print("  GOLD: kein handelbares Token gefunden (?!)")

    if silber:
        best_s = max(silber, key=lambda x: x[3])
        print(f"  SILBER: {best_s[0]} ({best_s[1]}) verfuegbar")
        if best_s[3] < 100_000:
            print(f"          ABER wenig Volumen - eher per externe Preisquelle")
    else:
        print(f"  SILBER: kein handelbares Token - bestaetigt unsere Vermutung")
        print(f"          (Silber spaeter ggf. per externe Preis-API)")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())