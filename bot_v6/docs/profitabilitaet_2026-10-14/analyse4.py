import json, os, statistics as st, bisect, math, collections
from datetime import datetime
HIER = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HIER, "runden_e6.json"), encoding="utf-8"))
K = json.load(open(os.path.join(HIER, "kurse_1h_lang.json")))
SYM = {"BTC/USDC": "BTCUSDC", "ETH/USDC": "ETHUSDC", "SOL/USDC": "SOLUSDC"}
ZT = {s: [k[0] for k in v] for s, v in K.items()}
def ms(s): return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)

def se(xs): return st.stdev(xs) / math.sqrt(len(xs))
n = [r["netto_pct"] for r in E]; b = [r["brutto_pct"] for r in E]
print(f"netto je Runde {st.mean(n):+.3f} % (Streuung {st.stdev(n):.2f}, Standardfehler {se(n):.3f})  -> {st.mean(n)/se(n):+.1f} Standardfehler von null")
print(f"brutto je Runde {st.mean(b):+.3f} % (Standardfehler {se(b):.3f})  -> {st.mean(b)/se(b):+.1f} Standardfehler von null")
# Tagesweise (unabhaengiger): netto je Verkaufstag
tag = collections.defaultdict(float)
for r in E: tag[r["verkauf"][:10]] += r["netto"]
tv = list(tag.values())
print(f"Handelstage mit Verkauf: {len(tv)}, Ø {st.mean(tv):+.2f} $/Tag, Standardfehler {se(tv):.2f}, im Plus {sum(x>0 for x in tv)} Tage")

def fwd(coin, t_iso, preis, h):
    s = SYM[coin]; i = bisect.bisect_right(ZT[s], ms(t_iso)) - 1 + h
    return K[s][i][4] / preis * 100 - 100 if i < len(K[s]) else None

print("\nEinstiegsguete je Phase, +24 h nach dem Kauf, gegen Zufall (alle Stunden, gleiche Muenzen, gleiche Phase)")
for name, a, z in (("13.-31.08.", "2026-08-13T13:21", "2026-09-01"), ("September", "2026-09-01", "2026-10-01"), ("Oktober", "2026-10-01", "2026-10-15")):
    rr = [r for r in E if a <= r["kauf"] < z]
    xs = [x for x in (fwd(r["coin"], r["kauf"], r["kaufpreis"], 24) for r in rr) if x is not None]
    lat = []
    for s in SYM.values():
        v = K[s]
        for i in range(len(v) - 24):
            if ms(a + ":00+00:00" if "T" in a else a + "T00:00:00+00:00") <= v[i][0] < ms(z + "T00:00:00+00:00"):
                lat.append(v[i + 24][4] / v[i][4] * 100 - 100)
    print(f"  {name:12} Bot {st.mean(xs):+.3f} % (n={len(xs)})   Zufall {st.mean(lat):+.3f} %   Unterschied {st.mean(xs)-st.mean(lat):+.3f} Prozentpunkte")
# Kaufte der Bot nach einem Anstieg? Kursveraenderung der 24 h VOR dem Kauf
vor = [x for x in (fwd(r["coin"], r["kauf"], r["kaufpreis"], -24) for r in E) if x is not None]
print(f"\nKurs 24 h VOR dem Kauf, vom Kaufkurs aus gesehen: Ø {st.mean(vor):+.2f} %  (negativ = der Kurs stand vorher tiefer, der Bot kaufte nach einem Anstieg)")
# Schwankung je Muenze: mittlere Stundenspanne und Tagesspanne
print("\nSchwankung je Muenze (13.08.-14.10.): Ø Stundenspanne (Hoch-Tief)/Schluss, Ø Tagesbewegung")
for coin, s in SYM.items():
    v = [k for k in K[s] if k[0] >= ms("2026-08-13T13:21:19+00:00")]
    hs = st.mean((k[2] - k[3]) / k[4] * 100 for k in v)
    tb = st.mean(abs(v[i + 24][4] / v[i][4] - 1) * 100 for i in range(0, len(v) - 24, 24))
    sl = sum(1 for r in E if r["coin"] == coin and r["ausstieg"] == "STOP_LOSS"); nn = sum(1 for r in E if r["coin"] == coin)
    print(f"  {coin}: Stundenspanne {hs:.2f} %, Tagesbewegung {tb:.2f} %, Stop-Loss {sl} von {nn} Runden ({sl/nn*100:.0f} %)")
print("\nEinstiegs-Strategie: Anteil an den Runden und an den Stop-Loss-Faellen")
for k in ("EMA_TREND", "FIBONACCI_SUPPORT", "MACD_CROSS", "RSI_OVERSOLD"):
    rr = [r for r in E if r["einstieg"] == k]
    print(f"  {k:18} {len(rr):3} Runden, Stop-Loss {sum(r['ausstieg']=='STOP_LOSS' for r in rr):2}, netto {sum(r['netto'] for r in rr):+7.2f} $")
gebucht = sum(r["pnl_gebucht"] for r in E)
print(f"\nGebucht (Cockpit-Sicht) {gebucht:+.2f} $  gegen Kassenrechnung {sum(r['netto'] for r in E):+.2f} $")
