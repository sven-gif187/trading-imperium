import json, os, statistics as st, collections, bisect
from datetime import datetime, timezone
HIER = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HIER, "runden.json"), encoding="utf-8"))
K = json.load(open(os.path.join(HIER, "kurse_1h.json")))
SYM = {"BTC/USDC": "BTCUSDC", "ETH/USDC": "ETHUSDC", "SOL/USDC": "SOLUSDC"}
ZT = {s: [k[0] for k in v] for s, v in K.items()}

def ts(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
def ms(s): return int(ts(s).timestamp() * 1000)

def kurs(coin, t_ms):
    """Schlusskurs der Stundenkerze, in der t_ms liegt (None wenn ausserhalb)."""
    s = SYM.get(coin)
    if not s: return None
    i = bisect.bisect_right(ZT[s], t_ms) - 1
    if i < 0 or i >= len(K[s]) - 1 and t_ms > ZT[s][-1] + 3600_000: return None
    return K[s][i][4]

def nach(coin, t_iso, h):
    t = ms(t_iso) + h * 3600_000
    if t > ZT[SYM[coin]][-1] + 3600_000: return None
    return kurs(coin, t)

def zeile(name, rr):
    if not rr: return f"{name:28} n=0"
    n = len(rr); net = sum(r["netto"] for r in rr)
    w = [r for r in rr if r["netto"] > 0]; l = [r for r in rr if r["netto"] <= 0]
    aw = st.mean(r["netto_pct"] for r in w) if w else 0
    al = -st.mean(r["netto_pct"] for r in l) if l else 0
    need = al / (aw + al) * 100 if (aw + al) else 0
    br = st.mean(r["brutto_pct"] for r in rr)
    return (f"{name:28} n={n:3}  netto {net:8.2f} $  je Runde {st.mean(r['netto_pct'] for r in rr):+6.3f} %  "
            f"brutto {br:+6.3f} %  Treffer {len(w)/n*100:5.1f} %  Ø Gewinn {aw:+.2f} %  Ø Verlust -{al:.2f} %  "
            f"noetig {need:5.1f} %  Gebuehren {sum(r['kauf_fee']+r['verk_fee'] for r in rr):6.2f} $")

GRENZEN = [("E6+E7 ab 13.08.", "2026-08-13T13:21"), ("E7 ab 15.08.", "2026-08-15T07:47"),
           ("nach Messfenster ab 18.09.", "2026-09-18T00:00"), ("letzte 4 Wochen ab 16.09.", "2026-09-16T00:00")]
for name, ab in GRENZEN:
    print(zeile(name, [r for r in R if r["verkauf"] >= ab]))
print()
E = [r for r in R if r["verkauf"] >= "2026-08-13T13:21"]

def gruppe(titel, key):
    print("==", titel)
    g = collections.defaultdict(list)
    for r in E: g[key(r)].append(r)
    for k, v in sorted(g.items(), key=lambda kv: sum(r["netto"] for r in kv[1])):
        print("  " + zeile(str(k), v))
    print()

gruppe("nach Ausstiegsgrund", lambda r: r["ausstieg"])
gruppe("nach Einstiegs-Strategie", lambda r: r["einstieg"])
gruppe("nach Muenze", lambda r: r["coin"])
gruppe("nach Regime beim Kauf", lambda r: r["regime_kauf"])
gruppe("nach Score beim Kauf", lambda r: r["score"])
gruppe("nach Zyklusphase", lambda r: r["phase"])
gruppe("nach Monat (Verkauf)", lambda r: r["verkauf"][:7])
gruppe("Anzahl Kaeufe je Runde (Nachkauf)", lambda r: r["n_kaeufe"])

# Haltedauer
w = [r for r in E if r["netto"] > 0]; l = [r for r in E if r["netto"] <= 0]
print("Haltedauer Median: Gewinner %.1f h, Verlierer %.1f h, alle %.1f h" % (
    st.median(r["halte_h"] for r in w), st.median(r["halte_h"] for r in l), st.median(r["halte_h"] for r in E)))

# MFE: wie weit lief der Handel ins Plus, bevor er endete?
m = [r for r in E if r["mfe"] is not None]
print("\nMFE vorhanden bei", len(m), "von", len(E))
if m:
    print("  Ø MFE %.2f %%, Ø realisiert brutto %.2f %%, Ø MAE %.2f %%" % (
        st.mean(r["mfe"] for r in m), st.mean(r["brutto_pct"] for r in m), st.mean(r["mae"] for r in m)))
    vl = [r for r in m if r["netto"] <= 0]
    for s in (0.5, 1.0, 1.5, 2.0):
        x = [r for r in vl if r["mfe"] >= s]
        print(f"  Verlierer, die vorher mindestens +{s} % im Plus waren: {len(x)} von {len(vl)}  (Verlust {sum(r['netto'] for r in x):.2f} $)")
    gw = [r for r in m if r["netto"] > 0]
    print("  Gewinner: Ø MFE %.2f %%, Ø mitgenommen brutto %.2f %%" % (st.mean(r["mfe"] for r in gw), st.mean(r["brutto_pct"] for r in gw)))

# Kurs danach: was passierte nach dem Verkauf, was nach dem Kauf?
print("\n== Kurs NACH dem Verkauf (vom Verkaufskurs aus)")
for h in (4, 24, 48, 168):
    g = collections.defaultdict(list)
    for r in E:
        p = nach(r["coin"], r["verkauf"], h)
        if p: g[r["ausstieg"]].append(p / r["verkpreis"] * 100 - 100)
    print(f"  +{h:3} h: " + "  ".join(f"{k} {st.mean(v):+.2f}% (n={len(v)})" for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])) if len(v) >= 3))

print("\n== Kurs NACH dem Kauf (Einstiegsguete) gegen Zufallszeitpunkt (Trivial-Latte)")
for h in (4, 24, 48, 168):
    xs = []
    for r in E:
        p = nach(r["coin"], r["kauf"], h)
        if p: xs.append(p / r["kaufpreis"] * 100 - 100)
    # Latte: alle Stunden im selben Zeitraum, dieselben Muenzen
    latte = []
    for coin, s in SYM.items():
        v = K[s]
        for i in range(len(v) - h):
            if v[i][0] >= ms("2026-08-13T13:21:00+00:00"):
                latte.append(v[i + h][4] / v[i][4] * 100 - 100)
    print(f"  +{h:3} h: Kaeufe des Bots {st.mean(xs):+.3f} % (n={len(xs)}, im Plus {sum(x>0 for x in xs)/len(xs)*100:.0f} %)   Zufall {st.mean(latte):+.3f} % (im Plus {sum(x>0 for x in latte)/len(latte)*100:.0f} %)")
json.dump(E, open(os.path.join(HIER, "runden_e6.json"), "w", encoding="utf-8"), ensure_ascii=False)
