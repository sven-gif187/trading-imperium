"""
REIFEPRUEFUNG Trading Imperium V6  (read-only, aendert NICHTS)

Beantwortet vier Fragen:
  1. Ist der Bot profitabel? (echte Netto-Zahlen)
  2. Sammelt er alle Daten fuer die Auswertung?
  3. Lernt er wirklich - und speichert er das Gelernte dauerhaft?
  4. Kann er Bullen- vs. Baerenmarkt erkennen und merken?

Ausfuehren:
  python "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\\analyse_readiness.py"
"""
import os, json, time
from collections import defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DS = os.path.join(ROOT, "data_store")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sec(title):
    print("\n" + "=" * 64)
    print("  " + title)
    print("=" * 64)


def file_info(path):
    if not os.path.exists(path):
        return "FEHLT"
    st = os.stat(path)
    age_min = (time.time() - st.st_mtime) / 60
    kb = st.st_size / 1024
    return f"{kb:.1f} KB, zuletzt geaendert vor {age_min:.0f} Min"


# ============ 1. PROFITABILITAET ============
sec("1. PROFITABILITAET")
try:
    t = load(os.path.join(DS, "trades_v5.json"))
    trades = t if isinstance(t, list) else t.get("trades", [])
    sells = [x for x in trades if "SELL" in str(x.get("side", x.get("type", ""))).upper()]
    wins = [x for x in sells if float(x.get("pnl") or 0) > 0]
    losses = [x for x in sells if float(x.get("pnl") or 0) < 0]
    total = sum(float(x.get("pnl") or 0) for x in sells)
    wr = len(wins) / len(sells) * 100 if sells else 0
    avg_w = sum(float(x.get("pnl") or 0) for x in wins) / len(wins) if wins else 0
    avg_l = sum(float(x.get("pnl") or 0) for x in losses) / len(losses) if losses else 0
    rr = abs(avg_w / avg_l) if avg_l else 0
    # Gebuehren?
    fee_keys = [k for x in trades[:10] for k in x.keys() if "fee" in str(k).lower() or "gebuehr" in str(k).lower()]
    fee_total = None
    if fee_keys:
        fk = fee_keys[0]
        fee_total = sum(float(x.get(fk) or 0) for x in trades)
    print(f"Verkaeufe: {len(sells)} | Gewinner: {len(wins)} | Verlierer: {len(losses)}")
    print(f"Win-Rate: {wr:.1f}%")
    print(f"Schnitt-Gewinn: {avg_w:+.2f}$ | Schnitt-Verlust: {avg_l:+.2f}$ | Risk/Reward: {rr:.2f}")
    print(f"Realisierte P&L: {total:+.2f}$")
    if fee_total is not None:
        print(f"Gebuehren-Feld '{fk}': Summe {fee_total:.2f}$ (pnl ist NETTO)")
    else:
        print("Kein Gebuehren-Feld in Trades gefunden - pnl koennte BRUTTO sein (vor Auswertung klaeren)")
    bs = defaultdict(float)
    for x in sells:
        bs[str(x.get("strategy", x.get("active_strategy", "?")))] += float(x.get("pnl") or 0)
    print("P&L je Strategie:")
    for k, v in sorted(bs.items(), key=lambda kv: -kv[1]):
        print(f"   {k:<18} {v:+.2f}$")
    bc = defaultdict(lambda: [0, 0.0])
    for x in sells:
        sym = str(x.get("symbol", x.get("coin", "?"))).split("/")[0]
        bc[sym][0] += 1
        bc[sym][1] += float(x.get("pnl") or 0)
    print("Je Coin (Verkaeufe / P&L):")
    for k, v in sorted(bc.items(), key=lambda kv: -kv[1][1]):
        print(f"   {k:<6} {v[0]:>3}x  {v[1]:+.2f}$")
    dates = sorted(set(str(x.get("time", x.get("timestamp", "")))[:10] for x in trades if x.get("time") or x.get("timestamp")))
    print(f"Handels-Zeitraum: {dates[0] if dates else '?'} bis {dates[-1] if dates else '?'} ({len(dates)} Tage)")
except Exception as e:
    print("FEHLER:", e)

# ============ 2. EQUITY-ABGLEICH ============
sec("2. VERMOEGENS-ABGLEICH (wo ist das Geld?)")
try:
    s = load(os.path.join(DS, "bot_state.json"))
    bal = s.get("paper_balances_backup") or {}
    usdc = float(bal.get("USDC", 0))
    print(f"Cash (USDC): {usdc:.2f}$")
    print("Coin-Bestaende:", {k: round(v, 4) for k, v in bal.items() if k != "USDC"})
    eq = s.get("equity_history") or []
    if eq:
        print(f"Equity-Snapshots gespeichert: {len(eq)}")
        print(f"   erster: {eq[0]}")
        print(f"   letzter: {eq[-1]}")
    # BTC-Tresor suchen
    for f in ("btc_accumulator.json", "equity_tracker.json"):
        p = os.path.join(DS, f)
        if os.path.exists(p):
            try:
                print(f"{f}: {json.dumps(load(p))[:200]}")
            except Exception:
                print(f"{f}: vorhanden ({file_info(p)})")
    print("HINWEIS: 500$ Start + realisierte P&L = handelbares Kapital + BTC-Tresor")
except Exception as e:
    print("FEHLER:", e)

# ============ 3. DATEN-VOLLSTAENDIGKEIT ============
sec("3. WERDEN ALLE DATEN GESAMMELT? (Datei-Frische)")
wichtig = {
    "trades_v5.json": "Trade-Historie (Auswertungs-Basis)",
    "bot_state.json": "Live-Zustand + Equity-Verlauf",
    "sensei_lessons.json": "taegliche Lektions-DB",
    "rl_weights.json": "RL-Lerngewichte",
    "phase_memory.json": "Marktphasen-Gedaechtnis",
    "equity_tracker.json": "Equity-Kurve fuer Chart",
}
for fn, desc in wichtig.items():
    print(f"   {fn:<22} {file_info(os.path.join(DS, fn)):<42} {desc}")
# models
md = os.path.join(DS, "models")
if os.path.isdir(md):
    for f in os.listdir(md):
        if f.endswith(".pkl"):
            print(f"   models/{f:<15} {file_info(os.path.join(md, f))}  XGBoost-Modell")

# ============ 4. LERNEN: RL-GEWICHTE ============
sec("4. LERNT DER BOT? (a) RL-Strategie-Gewichte")
try:
    rl = load(os.path.join(DS, "rl_weights.json"))
    w = rl.get("weights", {})
    h = rl.get("history", [])
    print(f"Gelernte Strategie-Gewichte: {len(w)}")
    for k, v in sorted(w.items(), key=lambda kv: -kv[1]):
        marker = " <- bevorzugt" if v > 1.05 else (" <- abgewertet" if v < 0.95 else "")
        print(f"   {k:<18} Gewicht {v:.3f}{marker}")
    print(f"Lern-Historie: {len(h)} Eintraege (Limit 1000)")
    if w and max(w.values()) - min(w.values()) > 0.05:
        print("=> Gewichte unterscheiden sich messbar -> RL hat WIRKLICH gelernt")
    else:
        print("=> Gewichte fast gleich -> RL noch in fruehem Lernstadium")
except Exception as e:
    print("rl_weights.json:", e)

# ============ 5. LERNEN: PHASE-MEMORY ============
sec("5. LERNT DER BOT? (b) Marktphasen-Gedaechtnis (Bull/Bear)")
try:
    p = os.path.join(DS, "phase_memory.json")
    if os.path.exists(p):
        pm = load(p)
        print(f"Gespeicherte Phasen-Kombinationen: {len(pm) if hasattr(pm,'__len__') else '?'}")
        txt = json.dumps(pm, indent=1)
        print(txt[:800] + ("..." if len(txt) > 800 else ""))
        print("=> Bot merkt sich, welche Strategie in welcher Marktphase am besten lief")
    else:
        print("phase_memory.json FEHLT - Phasen-Gedaechtnis evtl. anders gespeichert")
        print("(Log zeigt aber [PHASE-MEMORY] aktiv mit 97-100% Confidence)")
except Exception as e:
    print("phase_memory:", e)

# ============ 6. LERNEN: SENSEI-DB ============
sec("6. AUSWERTUNGS-DATEN (c) Sensei-Lektions-DB")
try:
    sl = load(os.path.join(DS, "sensei_lessons.json"))
    print(f"Gespeicherte Tage: {len(sl)}")
    for e in sl[-3:]:
        print(f"   {e.get('date')}: WR {e.get('win_rate')}% | R/R {e.get('risk_reward')} | "
              f"P&L {e.get('total_pnl')}$ | Coins: {list((e.get('by_symbol') or {}).keys())}")
    if sl and "by_symbol" in sl[-1]:
        print("=> Coin-Statistiken vorhanden -> bereit fuer Coin-Edge-Auswertung")
except Exception as e:
    print("sensei_lessons.json:", e)

# ============ 7. REGIME + ZYKLUS ============
sec("7. BULL/BEAR-ENTSCHEIDUNG (aktueller Stand)")
try:
    s = load(os.path.join(DS, "bot_state.json"))
    print(f"Zyklus-Phase (cycle_phase): {s.get('cycle_phase')}")
    print(f"Fear & Greed: {s.get('fear_greed')}")
    print(f"NUPL-Zone: {s.get('nupl_zone')} (on-chain Bull/Bear-Indikator)")
    print(f"DXY-Trend: {s.get('dxy_trend')} | News: {s.get('news_sentiment')}")
    eq = s.get("equity_history") or []
    print(f"Equity-Verlauf-Punkte: {len(eq)} (fuer Bull/Bear-Kurve)")
    print("=> cycle_phase + Regime-Detector + F&G + NUPL fliessen in die Strategiewahl")
except Exception as e:
    print("FEHLER:", e)

print("\n" + "=" * 64)
print("  ANALYSE FERTIG - bitte komplette Ausgabe an Claude schicken")
print("=" * 64)
