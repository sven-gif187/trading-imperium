import json, os, collections
HIER = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HIER, "runden.json"), encoding="utf-8"))
AB = "2026-08-13T13:21:19"
R = [r for r in R if r["verkauf"] >= AB]
print("Runden ab E6:", len(R))
abw = []
for r in R:
    if r["pnl_gebucht"] is None:
        continue
    d = r["netto"] - r["pnl_gebucht"]
    abw.append((d, d - r["kauf_fee"], r))
# erwartet: netto - gebucht == kauf_fee (Doppelbuchung) -> zweite Spalte ~0
grob = [a for a in abw if abs(a[1]) > 0.05]
print("Vergleiche:", len(abw), " davon Abweichung > 5 Cent nach Abzug Kaufgebuehr:", len(grob))
for d, d2, r in grob[:25]:
    print(f"  {r['verkauf'][:16]} {r['coin']:9} netto {r['netto']:8.3f} gebucht {r['pnl_gebucht']:8.3f} kauffee {r['kauf_fee']:.3f} rest {d2:8.3f} n_kaeufe {r['n_kaeufe']} {r['ausstieg']} ungedeckt {r['rest_ungedeckt']:.6f} kauf {r['kauf'][:16]}")
print("Summe (netto - gebucht):", round(sum(a[0] for a in abw), 2), " Summe Kaufgebuehren:", round(sum(r['kauf_fee'] for r in R), 2))
ae = collections.Counter(r["ausstieg"] for r in R)
print(ae.most_common())
