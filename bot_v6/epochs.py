# epochs.py - Config-Epochen fuer saubere Auswertung
# Jede Verhaltensaenderung des Bots = eine Epoche.
# Trades NUR innerhalb einer Epoche vergleichen, nie epochenuebergreifend.
import json, os, sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
EPOCH_FILE = os.path.join(HERE, "config_epochs.json")

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _parse(ts):
    if isinstance(ts, datetime):
        dt = ts
    else:
        s = str(ts).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            dt = datetime.fromisoformat(s[:10])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def load_epochs():
    with open(EPOCH_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    eps = data.get("epochs", [])
    eps.sort(key=lambda e: _parse(e["start"]))
    return eps

def save_epochs(eps):
    data = {"_comment": "Verhaltensaenderungen des Bots. Auswertung NUR innerhalb einer Epoche vergleichen.",
            "epochs": eps}
    tmp = EPOCH_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, EPOCH_FILE)

def epoch_for(ts):
    # Liefert die Epoche, in die ein Zeitstempel faellt.
    # Alles VOR der ersten Epoche faellt in die frueheste (Clamp).
    eps = load_epochs()
    if not eps:
        return None
    t = _parse(ts)
    chosen = eps[0]
    for e in eps:
        if _parse(e["start"]) <= t:
            chosen = e
        else:
            break
    return chosen

def add_epoch(label, note="", changes=None, start=None, epoch_id=None):
    eps = load_epochs()
    start = start or _now_iso()
    if epoch_id is None:
        slug = "".join(c for c in label.lower().replace(" ", "_") if c.isalnum() or c == "_")[:24]
        epoch_id = "E%d_%s" % (len(eps), slug)
    e = {"id": epoch_id, "start": _parse(start).isoformat(),
         "label": label, "note": note, "changes": changes or []}
    eps.append(e)
    save_epochs(eps)
    return e

def split_trades(trades, time_key=None):
    eps = load_epochs()
    buckets = {e["id"]: [] for e in eps}
    buckets["_no_time"] = []
    tkeys = [time_key] if time_key else ["time", "timestamp", "closed_at", "exit_time", "datetime", "date"]
    for tr in trades:
        if not isinstance(tr, dict):
            buckets["_no_time"].append(tr); continue
        ts = None
        for k in tkeys:
            if k and tr.get(k):
                ts = tr[k]; break
        if ts is None:
            buckets["_no_time"].append(tr); continue
        e = epoch_for(ts)
        buckets.setdefault(e["id"], []).append(tr)
    return buckets

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "add":
        label = args[1] if len(args) > 1 else "Unbenannte Epoche"
        note = args[2] if len(args) > 2 else ""
        changes = args[3].split(",") if len(args) > 3 else []
        e = add_epoch(label, note, changes)
        print("Epoche hinzugefuegt:", e["id"], "@", e["start"])
    else:
        for e in load_epochs():
            print("%-24s %s  %s" % (e["id"], e["start"], e["label"]))
