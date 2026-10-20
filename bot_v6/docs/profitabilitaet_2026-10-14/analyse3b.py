# Gegenprobe: dieselben Ausstiegsregeln in verschiedenen Marktphasen, auch im fallenden Markt Juni-August.
import json, os, statistics as st, bisect, time, urllib.request, math
from datetime import datetime, timezone
HIER = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HIER, "runden.json"), encoding="utf-8"))
SYM = {"BTC/USDC": "BTCUSDC", "ETH/USDC": "ETHUSDC", "SOL/USDC": "SOLUSDC"}
pfad = os.path.join(HIER, "kurse_1h_lang.json")
if not os.path.exists(pfad):
    START = int(datetime(2026, 6, 15, tzinfo=timezone.utc).timestamp() * 1000); ENDE = int(time.time() * 1000)
    K = {}
    for s in SYM.values():
        z = []; t = START
        while t < ENDE:
            with urllib.request.urlopen(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&startTime={t}&limit=1000", timeout=20) as r:
                d = json.loads(r.read())
            if not d: break
            z += [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in d]; t = d[-1][0] + 3600_000
        K[s] = z
    json.dump(K, open(pfad, "w"))
K = json.load(open(pfad))
ZT = {s: [k[0] for k in v] for s, v in K.items()}
def ms(s): return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
KOSTEN = 0.505

def sim(r, p):
    s = SYM[r["coin"]]; v = K[s]; e = r["kaufpreis"]
    i = bisect.bisect_right(ZT[s], ms(r["kauf"]))
    if p[0] == "halten":
        j = i + p[1]
        return v[j][4] / e * 100 - 100 - KOSTEN if j < len(v) else None
    stop, ab, trail = p; hoch = e
    for j in range(i, min(len(v), i + 24 * 30)):
        o, h, l, c = v[j][1:5]
        grenze = e * (1 - stop / 100)
        if hoch >= e * (1 + ab / 100): grenze = max(grenze, hoch * (1 - trail / 100))
        if l <= grenze: return min(o, grenze) / e * 100 - 100 - KOSTEN
        hoch = max(hoch, h)
    j = min(len(v), i + 24 * 30) - 1
    return v[j][4] / e * 100 - 100 - KOSTEN if j >= i else None

REGELN = [("IST-Regel 2,5 / ab 1,2 / 1,0", (2.5, 1.2, 1.0)), ("2,5 / ab 3 / 2", (2.5, 3.0, 2.0)),
          ("4 / ab 3 / 3", (4.0, 3.0, 3.0)), ("5 / ab 4 / 4", (5.0, 4.0, 4.0)), ("8 / ab 5 / 5", (8.0, 5.0, 5.0)),
          ("halten 24 h", ("halten", 24)), ("halten 48 h", ("halten", 48))]
PHASEN = [("22.06.-13.08. (seitwaerts)", "2026-06-22", "2026-08-13T13:21"), ("13.-31.08.", "2026-08-13T13:21", "2026-09-01"),
          ("September", "2026-09-01", "2026-10-01"), ("Oktober", "2026-10-01", "2026-10-15")]
for name, a, b in PHASEN:
    rr = [r for r in R if a <= r["kauf"] < b and r["coin"] in SYM]
    # Markt in der Phase
    mv = []
    for s in SYM.values():
        i = bisect.bisect_right(ZT[s], ms(a + ("T00:00:00+00:00" if "T" not in a else ":00+00:00")))
        j = min(bisect.bisect_right(ZT[s], ms(b + ("T00:00:00+00:00" if "T" not in b else ":00+00:00"))) - 1, len(K[s]) - 1)
        mv.append(f"{s[:3]} {K[s][j][4]/K[s][i][4]*100-100:+.1f}%")
    echt = [r["netto_pct"] for r in rr]
    print(f"\n== {name}: {len(rr)} Kaeufe   Markt: {', '.join(mv)}   echt gebucht je Runde {st.mean(echt):+.3f} % (Gebuehr damals teils 0,10 %)")
    for rn, p in REGELN:
        xs = [x for x in (sim(r, p) for r in rr) if x is not None]
        if xs:
            print(f"   {rn:28} n={len(xs):3}  je Runde {st.mean(xs):+.3f} %  Median {st.median(xs):+.3f} %  Treffer {sum(x>0 for x in xs)/len(xs)*100:3.0f} %")

