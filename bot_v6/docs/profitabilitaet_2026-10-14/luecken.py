import sqlite3
from datetime import datetime
c = sqlite3.connect("file:data_store/telemetrie.db?mode=ro", uri=True)
alt = None; n = 0
for (t,) in c.execute("select ts_utc from evaluations where ts_utc >= '2026-08-13' order by ts_utc"):
    d = datetime.fromisoformat(t)
    if alt and (d - alt).total_seconds() > 3 * 3600:
        print(f"Luecke {alt:%d.%m. %H:%M} -> {d:%d.%m. %H:%M}  ({(d-alt).total_seconds()/3600:.1f} h)")
        n += 1
    alt = d
print("Luecken > 3 h:", n, " letzter Eintrag", alt)
