# -*- coding: utf-8 -*-
"""Prueft OHNE Schluessel, ob Bybit EU unsere Muenzen handelbar fuehrt.

Bybit EU (MiCA, Lizenz Oesterreich 28.05.2025) ist eine EIGENE Plattform mit
eigenem Konto und eigener Adresse: api.bybit.eu statt api.bybit.com.
Die oeffentliche Instrumentenliste braucht keine Anmeldung.

Die Muenzliste wird NICHT hier gepflegt, sondern aus features/chart_refresher.py
gelesen - sonst laufen zwei Listen auseinander.
"""
import io, json, os, re, sys, urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))


def muenzen():
    """Liest COINS aus features/chart_refresher.py - die eine Quelle."""
    p = os.path.join(HIER, "features", "chart_refresher.py")
    t = io.open(p, encoding="utf-8").read()
    m = re.search(r"^COINS\s*=\s*\[(.*?)\]", t, re.S | re.M)
    if not m:
        raise RuntimeError("COINS in chart_refresher.py nicht gefunden")
    return [x.split("/")[0] for x in re.findall(r'"([A-Z0-9/]+)"', m.group(1))]


def paare(host):
    url = f"https://{host}/v5/market/instruments-info?category=spot&limit=1000"
    with urllib.request.urlopen(url, timeout=20) as r:
        d = json.loads(r.read().decode())
    if d.get("retCode") != 0:
        raise RuntimeError(f"{host}: retCode {d.get('retCode')} {d.get('retMsg')}")
    return {i["symbol"]: i for i in d.get("result", {}).get("list", [])}


def bericht():
    mz = muenzen()
    print("=" * 70)
    print("  BYBIT EU - handelbare Paare, geprueft ohne Anmeldung")
    print("=" * 70)
    print(f"\n  Muenzliste aus features/chart_refresher.py: {len(mz)} Stueck")
    try:
        eu = paare("api.bybit.eu")
    except Exception as e:
        print(f"\n  api.bybit.eu NICHT ERREICHBAR: {e}")
        return 2
    print(f"  api.bybit.eu antwortet: {len(eu)} Spot-Paare\n")

    ok, ersatz, fehlt = [], [], []
    print(f"  {'Muenze':9s} {'USDC':6s} {'USDT':6s} Mindestbetrag  Schrittweite")
    print("  " + "-" * 66)
    for m in mz:
        c, t = f"{m}USDC" in eu, f"{m}USDT" in eu
        it = eu.get(f"{m}USDC") or eu.get(f"{m}USDT")
        lf = (it or {}).get("lotSizeFilter", {})
        det = (f"{lf.get('minOrderAmt','?'):>6s} $     {lf.get('basePrecision','?')}"
               if it else "")
        print(f"  {m:9s} {'JA' if c else '--':6s} {'JA' if t else '--':6s} {det}")
        (ok if c else (ersatz if t else fehlt)).append(m)

    print()
    print(f"  In USDC handelbar : {len(ok)} von {len(mz)}")
    if ersatz:
        print(f"  nur in USDT       : {len(ersatz)}  {' '.join(ersatz)}")
    if fehlt:
        print(f"  GAR NICHT         : {len(fehlt)}  {' '.join(fehlt)}")
    else:
        print("  GAR NICHT         : keine")

    try:
        com = paare("api.bybit.com")
        nur_com = [m for m in mz
                   if (f"{m}USDC" in com or f"{m}USDT" in com)
                   and not (f"{m}USDC" in eu or f"{m}USDT" in eu)]
        print(f"\n  Gegenprobe api.bybit.com ({len(com)} Paare): "
              f"auf .com handelbar, auf EU nicht -> "
              f"{', '.join(nur_com) if nur_com else 'keine'}")
    except Exception as e:
        print(f"\n  Gegenprobe .com fehlgeschlagen: {e}")

    print("\n  Hinweis: Der Mindestbetrag (minOrderAmt) ist die Zahl, die in")
    print("  Befund 68 fehlt - der Bot prueft ihn nirgends.")
    print("=" * 70)
    return 0 if not fehlt else 1


def selbsttest():
    """Gegentest in beide Richtungen (CLAUDE.md 0)."""
    print("SELBSTTEST bybit_eu_pruefen.py")
    mz = muenzen()
    assert len(mz) >= 10, f"zu wenige Muenzen gelesen: {mz}"
    assert "BTC" in mz, "BTC fehlt - Liste falsch gelesen"
    assert "/" not in "".join(mz), "Symbole nicht sauber getrennt"
    print(f"  OK  Muenzliste gelesen: {len(mz)} Stueck, erste drei {mz[:3]}")
    eu = paare("api.bybit.eu")
    assert "BTCUSDC" in eu, "BTCUSDC fehlt - Antwort unplausibel"
    assert "GIBTESNICHTUSDC" not in eu, "findet Erfundenes - Gegenrichtung kaputt"
    print(f"  OK  findet BTCUSDC, findet nichts Erfundenes ({len(eu)} Paare)")
    print("SELBSTTEST BESTANDEN")


if __name__ == "__main__":
    if "--selbsttest" in sys.argv:
        selbsttest()
    else:
        sys.exit(bericht())
