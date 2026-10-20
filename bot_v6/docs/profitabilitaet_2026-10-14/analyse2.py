import json, os, statistics as st, bisect
from datetime import datetime, timezone
HIER = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HIER, "runden_e6.json"), encoding="utf-8"))
K = json.load(open(os.path.join(HIER, "kurse_1h.json")))
SYM = {"BTC/USDC": "BTCUSDC", "ETH/USDC": "ETHUSDC", "SOL/USDC": "SOLUSDC"}
ZT = {s: [k[0] for k in v] for s, v in K.items()}
def ts(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
def ms(s): return int(ts(s).timestamp() * 1000)
START = ms("2026-08-13T13:21:19+00:00"); ENDE = ZT["BTCUSDC"][-1] + 3600_000
KOSTEN = 0.505  # K-BASIS je Runde in %

# 1) Markt im Zeitraum
print("== Markt 13.08. -> 14.10.")
for s in SYM.values():
    i = bisect.bisect_right(ZT[s], START) - 1
    a, b = K[s][i][4], K[s][-1][4]
    print(f"  {s}: {a:.2f} -> {b:.2f}  {b/a*100-100:+.1f} %")
# Wochen BTC
print("  BTC Wochenschluss:", " ".join(f"{datetime.fromtimestamp(K['BTCUSDC'][i][0]/1000, timezone.utc):%d.%m}={K['BTCUSDC'][i][4]:.0f}" for i in range(0, len(K['BTCUSDC']), 168)))

# 2) Wie viel Zeit war Geld im Markt? (Dollar-Stunden)
dauer_h = (ENDE - START) / 3600_000
dollar_h = sum(r["kosten"] * r["halte_h"] for r in E)
print(f"\n== Investiert: Ø {dollar_h/dauer_h:.1f} $ im Markt (von rund 500-600 $ Handelskapital), Zeitraum {dauer_h/24:.1f} Tage")
stunden_mit_pos = set()
for r in E:
    a = ms(r["kauf"]) // 3600_000; b = ms(r["verkauf"]) // 3600_000
    stunden_mit_pos.update(range(a, b + 1))
print(f"  Stunden mit mindestens einer offenen Position: {len(stunden_mit_pos)/dauer_h*100:.0f} %")

# Anteil des Muenzanstiegs, der in Haltezeiten fiel
for coin, s in SYM.items():
    v = K[s]; drin = set()
    for r in E:
        if r["coin"] == coin:
            drin.update(range(ms(r["kauf"]) // 3600_000, ms(r["verkauf"]) // 3600_000))
    log_ges = 0; log_drin = 0
    import math
    for i in range(1, len(v)):
        if v[i][0] < START: continue
        x = math.log(v[i][4] / v[i-1][4]); log_ges += x
        if v[i][0] // 3600_000 in drin: log_drin += x
    print(f"  {coin}: Anstieg gesamt {math.exp(log_ges)*100-100:+.1f} %, davon in Haltezeiten {math.exp(log_drin)*100-100:+.1f} %, ausserhalb {math.exp(log_ges-log_drin)*100-100:+.1f} %")

# 3) Gegenrechnung: dieselben Kaeufe, andere Ausstiege (auf Stundenkerzen, vorsichtig: Tief vor Hoch)
def sim(r, art, p1=None, p2=None):
    s = SYM[r["coin"]]; v = K[s]; e = r["kaufpreis"]
    i = bisect.bisect_right(ZT[s], ms(r["kauf"]))  # erste volle Kerze nach dem Kauf
    if art == "halten":
        j = i + p1
        if j >= len(v): return None
        return v[j][4] / e * 100 - 100 - KOSTEN
    hoch = e
    for j in range(i, len(v)):
        o, h, l, c = v[j][1], v[j][2], v[j][3], v[j][4]
        # Stop zuerst (vorsichtig)
        if art == "stop_trail":
            stop, trail_ab, trail = p1
            grenze = e * (1 - stop / 100)
            if hoch >= e * (1 + trail_ab / 100):
                grenze = max(grenze, hoch * (1 - trail / 100))
            if l <= grenze:
                return min(o, grenze) / e * 100 - 100 - KOSTEN
            hoch = max(hoch, h)
        if j - i > 24 * 30: return c / e * 100 - 100 - KOSTEN
    return None  # noch offen

def bericht(name, xs):
    xs = [x for x in xs if x is not None]
    if not xs: return
    w = [x for x in xs if x > 0]
    print(f"  {name:42} n={len(xs):3}  je Runde {st.mean(xs):+.3f} %  Median {st.median(xs):+.3f} %  Treffer {len(w)/len(xs)*100:4.0f} %  Summe bei 180 $ je Runde {sum(xs)*1.8:+8.1f} $")

print("\n== Dieselben 136 Kaeufe, anderer Ausstieg (nach 0,505 % Kosten, Stundenkerzen)")
bericht("IST (echt gebucht, Kassenrechnung)", [r["netto_pct"] for r in E])
bericht("IST-Regel nachgespielt (Stop 2,5 / ab 1,2 Trail 1,0)", [sim(r, "stop_trail", (2.5, 1.2, 1.0)) for r in E])
for h in (24, 48, 96, 168):
    bericht(f"stumpf halten {h} h", [sim(r, "halten", h) for r in E])
for p in [(2.5, 2.0, 2.0), (2.5, 3.0, 2.0), (4.0, 3.0, 3.0), (5.0, 4.0, 4.0), (8.0, 5.0, 5.0)]:
    bericht(f"Stop {p[0]} / Trail ab +{p[1]} / Abstand {p[2]}", [sim(r, "stop_trail", p) for r in E])
