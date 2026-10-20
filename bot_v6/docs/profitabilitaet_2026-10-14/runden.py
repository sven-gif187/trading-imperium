# Baut aus trades_v5.json abgeschlossene Runden (Kauf ... Verkauf) per FIFO je Muenze.
# Nur lesen. Ergebnis: runden.json im Scratchpad.
import json, os, sys, collections
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
T = json.load(open("data_store/trades_v5.json", encoding="utf-8"))

def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

T = sorted(T, key=lambda t: ts(t["time"]))
ab = ts(sys.argv[1]) if len(sys.argv) > 1 else None

# Vollstaendigkeit pruefen
fehlt = collections.Counter()
for t in T:
    if ab and ts(t["time"]) < ab:
        continue
    for k in ("amount", "fee"):
        if t.get(k) is None:
            fehlt[(t["type"], k)] += 1
print("fehlende Felder ab Start:", dict(fehlt))

offen = collections.defaultdict(list)   # coin -> [lots]
runden = []
for t in T:
    coin = t["coin"]
    q = float(t["qty"] or 0)
    p = float(t["price"])
    if t["type"] == "BUY":
        fee = t.get("fee")
        amt = t.get("amount")
        # [16.10.2026] Kaufbetrag MIT oder OHNE Gebuehr? Bis E9 stand im
        # Journal der Betrag samt Gebuehr (qty = (amount-fee)/Kurs), ab E9
        # (14.10.) ohne (amount = qty*Kurs). Erkannt am Abstand zu qty*Kurs.
        if amt is None:
            amt = p * q + (fee or 0)
        elif fee and abs(float(amt) - p * q) < abs(float(amt) - (p * q + fee)):
            amt = float(amt) + fee
        lot = {"qty": q, "rest": q, "kosten": float(amt), "preis": p,
               "fee": float(fee or 0), "time": t["time"], "strategy": t.get("strategy"),
               "reason": t.get("reason"), "score": t.get("score"), "regime": t.get("market_regime"),
               "fg": t.get("fear_greed_at_entry"), "phase": t.get("cycle_phase"),
               "stop": t.get("stop_initial"), "id": t.get("_id")}
        offen[coin].append(lot)
    elif t["type"] == "SELL":
        rest = q
        # [16.10.2026 BERICHTIGT] Verkaufsbetrag VOR oder NACH Gebuehr?
        # Der Ausstiegs-Pfad (exit_monitor) schreibt den Betrag vor Gebuehr,
        # der Signal-Pfad (execute_approved_trade) schon NACH Gebuehr. Die
        # erste Fassung zog die Gebuehr bei allen ab - bei den 21
        # Signal-Verkaeufen der E7 also doppelt, zusammen 9,02 $ zu
        # schlecht (gefunden vom Pruefstand, A5/A10, 14.10.). Erkannt wird
        # es am Abstand zu qty*Kurs.
        _vfee = float(t.get("fee") or 0)
        _vamt = float(t.get("amount") or p * q)
        if _vfee and abs(_vamt - (p * q - _vfee)) < abs(_vamt - p * q):
            erloes_netto = _vamt
        else:
            erloes_netto = _vamt - _vfee
        kosten = 0.0
        kauf_fee = 0.0
        lots = []
        while rest > 1e-12 and offen[coin]:
            lot = offen[coin][-1]
            nimm = min(lot["rest"], rest)
            anteil = nimm / lot["qty"]
            kosten += lot["kosten"] * anteil
            kauf_fee += lot["fee"] * anteil
            lots.append((lot, nimm))
            lot["rest"] -= nimm
            rest -= nimm
            if lot["rest"] <= 1e-12:
                offen[coin].pop()
        if not lots:
            print("VERKAUF OHNE KAUF:", t["time"], coin, t.get("pnl"))
            continue
        gedeckt = q - rest
        if rest > 1e-9 * max(q, 1):
            # Verkauf groesser als gebuchte Kaeufe: anteilig rechnen
            erloes_netto *= gedeckt / q
        erster = min((l for l, _ in lots), key=lambda l: l["time"])
        kaufwert_ohne_fee = kosten - kauf_fee
        r = {
            "coin": coin, "kauf": erster["time"], "verkauf": t["time"],
            "n_kaeufe": len(lots),
            "kosten": kosten, "kauf_fee": kauf_fee, "verk_fee": float(t.get("fee") or 0),
            "erloes_netto": erloes_netto,
            "netto": erloes_netto - kosten,
            "netto_pct": (erloes_netto - kosten) / kosten * 100,
            "brutto_pct": (float(t["price"]) * gedeckt) / kaufwert_ohne_fee * 100 - 100 if kaufwert_ohne_fee > 0 else None,
            "pnl_gebucht": t.get("pnl"), "pnl_pct_gebucht": t.get("pnl_pct"),
            "ausstieg": t.get("strategy"), "ausstieg_text": t.get("reason"),
            "einstieg": erster["strategy"], "einstieg_text": erster["reason"], "score": erster["score"],
            "regime_kauf": erster["regime"], "regime_verk": t.get("market_regime"),
            "fg": erster["fg"], "phase": erster["phase"],
            "mfe": t.get("mfe_pct"), "mae": t.get("mae_pct"),
            "halte_h": (ts(t["time"]) - ts(erster["time"])).total_seconds() / 3600,
            "rest_ungedeckt": rest, "kauf_id": erster["id"], "verk_id": t.get("_id"),
            "pos_id": t.get("position_id"), "stop": erster["stop"], "kaufpreis": erster["preis"],
            "verkpreis": float(t["price"]),
        }
        runden.append(r)

print("Runden gesamt:", len(runden))
print("noch offen:", {c: round(sum(l["rest"] for l in v), 8) for c, v in offen.items() if v})
json.dump(runden, open(os.path.join(HIER, "runden.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)

