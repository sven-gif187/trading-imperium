import json, os, math, collections
HIER = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HIER, "runden_e6.json"), encoding="utf-8"))
K = json.load(open(os.path.join(HIER, "kurse_1h.json")))
for r in E:
    if r["verkauf"].startswith("2026-08-19T00:59") or r["verkauf"].startswith("2026-10-12T23:39"):
        print({k: r[k] for k in ("coin", "kauf", "verkauf", "kosten", "kauf_fee", "verk_fee", "erloes_netto", "netto", "netto_pct", "brutto_pct", "pnl_gebucht", "kaufpreis", "verkpreis", "ausstieg", "mfe", "mae")})
# eingefangener Anstieg je Muenze, exakt ueber Kauf- und Verkaufskurse
SYM = {"BTC/USDC": "BTCUSDC", "ETH/USDC": "ETHUSDC", "SOL/USDC": "SOLUSDC"}
from datetime import datetime
import bisect
START = int(datetime.fromisoformat("2026-08-13T13:21:19+00:00").timestamp()*1000)
for coin, s in SYM.items():
    v = K[s]; zt = [k[0] for k in v]
    a = v[bisect.bisect_right(zt, START)-1][4]; b = v[-1][4]
    eing = sum(math.log(r["verkpreis"]/r["kaufpreis"]) for r in E if r["coin"] == coin)
    n = sum(1 for r in E if r["coin"] == coin)
    print(f"{coin}: Markt {b/a*100-100:+.1f} %, vom Bot ueber {n} Runden eingefangen (Kurs Kauf->Verkauf, verkettet) {math.exp(eing)*100-100:+.1f} %, nach Kosten {math.exp(eing - n*0.00505)*100-100:+.1f} %")
gebuehren = sum(r["kauf_fee"] + r["verk_fee"] for r in E)
print("Gebuehren", round(gebuehren, 2), " netto", round(sum(r["netto"] for r in E), 2), " brutto (netto+Gebuehren)", round(sum(r["netto"] for r in E) + gebuehren, 2))
print("Ø Einsatz je Runde", round(sum(r["kosten"] for r in E)/len(E), 2))
# Gebuehren direkt aus der Handelsdatei gegenzaehlen
T = json.load(open("data_store/trades_v5.json", encoding="utf-8"))
ab = "2026-08-13T13:21"
f_sell = sum(t.get("fee") or 0 for t in T if t["type"] == "SELL" and t["time"] >= ab)
print("Gegenzaehlung Verkaufsgebuehren direkt:", round(f_sell, 2), " aus Runden:", round(sum(r['verk_fee'] for r in E), 2))
# Stop-Loss: wie tief lag der Stop wirklich?
sl = [r for r in E if r["ausstieg"] == "STOP_LOSS"]
print("Stop-Loss brutto: min %.2f max %.2f" % (min(r["brutto_pct"] for r in sl), max(r["brutto_pct"] for r in sl)))
print("Stop-Loss je Muenze:", collections.Counter(r["coin"] for r in sl))
print("Stop-Loss Haltedauer Median h:", sorted(r["halte_h"] for r in sl)[len(sl)//2])
