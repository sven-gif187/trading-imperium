# epoch_report.py - P&L pro Epoche getrennt ausweisen
# Aufruf:  python epoch_report.py [trades_datei]
# Ohne Argument sucht es die ueblichen Journal-Dateien automatisch.
import json, os, sys
import epochs

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILES = ["data_store/trades_v5.json", "trades_v5.json",
                 "data_store/order_history.json", "order_history.json"]
PNL_KEYS = ["pnl", "realized_pnl", "net_pnl", "profit", "pnl_usdc", "pnl_net"]

def find_file(arg):
    if arg:
        return arg if os.path.isabs(arg) else os.path.join(HERE, arg)
    for f in DEFAULT_FILES:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            return p
    return None

def get_pnl(tr):
    for k in PNL_KEYS:
        v = tr.get(k) if isinstance(tr, dict) else None
        if isinstance(v, (int, float)):
            return float(v)
    return None

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = find_file(arg)
    if not path or not os.path.exists(path):
        print("Keine Trade-Datei gefunden. Aufruf:  python epoch_report.py <datei>")
        print("Automatisch gesucht:", DEFAULT_FILES)
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    trades = data if isinstance(data, list) else data.get("trades", [])
    print("Datei:", os.path.basename(path), " | Eintraege:", len(trades))
    print("=" * 70)
    buckets = epochs.split_trades(trades)
    eps = {e["id"]: e for e in epochs.load_epochs()}
    order = list(eps.keys()) + ["_no_time"]
    for eid in order:
        items = buckets.get(eid, [])
        if not items and eid == "_no_time":
            continue
        pnls = [get_pnl(t) for t in items]
        pnls = [p for p in pnls if p is not None]
        wins = sum(1 for p in pnls if p > 0)
        total = sum(pnls)
        wr = (wins / len(pnls) * 100) if pnls else 0.0
        label = eps[eid]["label"] if eid in eps else "(ohne Zeitstempel)"
        print("%-24s | Trades m.PnL: %4d | Netto: %+9.2f | WR: %5.1f%%  %s"
              % (eid, len(pnls), total, wr, label))
    print("=" * 70)
    print("WICHTIG: Nur INNERHALB einer Epoche vergleichen - die Regeln")
    print("unterscheiden sich zwischen den Epochen.")

if __name__ == "__main__":
    main()
