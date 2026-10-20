# -*- coding: utf-8 -*-
"""A4 Erkundung: Felder der Kauf-Eintraege in v6 trades_v5.json (nur lesen)."""
import sys, json
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from runden_lib import lade, runden

V6 = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)")
rows = lade(V6)
VON, BIS = "2026-08-13T13:21:19", "2026-10-14T09:18:25"
rd = runden(rows, VON, BIS)
print("Runden", len(rd), "brutto", round(sum(r["brutto"] for r in rd), 2), "netto", round(sum(r["netto"] for r in rd), 2))
kauf_t = {r["kauf_t"] for r in rd}
kaeufe = [r for r in rows if str(r.get("type","")).upper()=="BUY" and r["time"] in kauf_t]
print("Kaeufe gefunden", len(kaeufe))
keys = Counter()
for k in kaeufe: keys.update(k.keys())
print(keys)
print(json.dumps(kaeufe[0], indent=1, ensure_ascii=False)[:3000])
print(json.dumps(kaeufe[-1], indent=1, ensure_ascii=False)[:3000])
print("strategy", Counter(k.get("strategy") for k in kaeufe))
print("regime", Counter(k.get("market_regime") for k in kaeufe))
print("score", Counter(k.get("score") for k in kaeufe))
print("signal_score", Counter(k.get("signal_score") for k in kaeufe))
print("time format", rows[-1]["time"], rows[0]["time"])
sells = [r for r in rows if str(r.get("type","")).upper()=="SELL" and VON <= r["time"] < BIS]
print("sells keys", Counter(k for s in sells for k in s.keys()))
print("ausstieg", Counter(r["ausstieg"] for r in rd))
