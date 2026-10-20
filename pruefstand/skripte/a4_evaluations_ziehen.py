# -*- coding: utf-8 -*-
"""
A4: Kaufkandidaten aus v6 telemetrie.db (evaluations, side=BUY) im E7-Fenster, verdichtet
auf Muenze x Stunde. NUR LESEN (mode=ro). Ziel: pruefstand/daten/a4_eval_stunden_v6.csv
Je Stunde: hoechster Score, Kaufweg des hoechsten Scores, Anzahl Bewertungen, ob genehmigt,
haeufigstes Regime. Die Stunde ist die Stunde, in der bewertet wurde (Vorwaertsrendite wird
spaeter ab der NAECHSTEN vollen Stunde gemessen -> kein Blick in die Zukunft).
"""
import csv, sqlite3, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB = Path(r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\data_store\telemetrie.db")
ZIEL = Path(r"C:\Users\<BENUTZER>\Desktop\pruefstand\daten\a4_eval_stunden_v6.csv")
VON, BIS = "2026-08-12T00:00:00", "2026-10-14T09:18:25"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
print("Indizes:", con.execute("select name, sql from sqlite_master where type='index' and tbl_name='evaluations'").fetchall())
t0 = time.time()
cur = con.execute("select ts_utc, symbol, decision, reject_art, score, strategy_id, regime from evaluations "
                  "where ts_utc >= ? and ts_utc < ? and side = 'BUY'", (VON, BIS))
agg = defaultdict(lambda: {"n": 0, "max_score": None, "strat": None, "approved": 0, "regime": Counter(), "reject": Counter()})
n = 0
dec = Counter()
for ts, sym, d, rej, sc, st, rg in cur:
    n += 1
    dec[d] += 1
    key = (sym, ts[:13])
    a = agg[key]
    a["n"] += 1
    if sc is not None and (a["max_score"] is None or sc > a["max_score"]):
        a["max_score"], a["strat"] = sc, st
    if d and d.upper().startswith("APPROV"):
        a["approved"] += 1
    a["regime"][rg] += 1
    a["reject"][rej] += 1
print(f"{n} BUY-Bewertungen in {time.time()-t0:.0f} s, Entscheidungen: {dec}")
with ZIEL.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["symbol", "stunde_utc", "n_bewertungen", "max_score", "kaufweg_max", "n_genehmigt", "regime", "haeufigste_ablehnung"])
    for (sym, h), a in sorted(agg.items()):
        w.writerow([sym, h + ":00:00Z", a["n"], a["max_score"], a["strat"], a["approved"],
                    a["regime"].most_common(1)[0][0], a["reject"].most_common(1)[0][0]])
print(len(agg), "Muenze-Stunden ->", ZIEL)
