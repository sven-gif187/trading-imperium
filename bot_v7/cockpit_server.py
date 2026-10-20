# -*- coding: utf-8 -*-
"""
cockpit_server.py - V6 Analyse-Cockpit (read-only, lokal)   [COCKPIT-KEEP]
==========================================================================
Liest data_store/trades_v5.json + equity_history.json (NUR lesend), rechnet
alle Kennzahlen selbst und zeigt sie im Browser. Refresh alle 60s.

- Fasst den Bot mit KEINER Zeile an. Reine Anzeige. E7-konform.
- Bindet auf 127.0.0.1 (nur dieser Rechner, kein Netz-Zugriff).
- Nur Python-Standardbibliothek. Nichts zu installieren.
- Robust: halb-geschriebene JSON -> letzter guter Stand bleibt stehen.
- Pfad-sicher: findet die Dateien, egal ob im Hauptordner ODER in data_store.

NUR V6-DATEN. brain_performance.json wird bewusst NICHT genutzt (V4-Bootstrap).

[COCKPIT-KEEP]  <- Marker: von cleanup.py NICHT loeschen/archivieren!

START (ein Befehl):
  cd /d "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v7" && python cockpit_server.py
  -> Browser: http://localhost:<PORT>    STOP: Strg+C

Der Anschluss steht NICHT mehr hier im Quelltext, sondern in
data_store/config.json unter dashboard.cockpit_port. In v7 ist es 8170,
weil der v6-Papier-Bot auf demselben Rechner 8110 haelt (Befund 111).
Beim Start wird er ausgegeben.
"""
import json, os, math, collections
import statistics as st
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def _port_aus_config(vorgabe=8170):
    """Anschluss aus data_store/config.json lesen.

    [25.09.2026, Befund 111] Vorher stand hier fest PORT = 8110. Auf
    diesem Rechner haelt der v6-Papier-Bot diesen Anschluss; ein zweites
    Cockpit darauf stirbt mit "address already in use" - oder, schlimmer,
    der Knopf in der Oberflaeche sieht dort eine Antwort, haelt sie fuer
    das eigene Cockpit und zeigt v6-Daten als die eigenen an.

    Die Zahl steht jetzt an EINER Stelle: dashboard.cockpit_port. Die
    Oberflaeche (ui/main_window.py) liest dieselbe.

    Faellt das Lesen aus, gilt die Vorgabe 8170 - NICHT 8110. Ein
    Rueckfall darf nicht still auf dem Anschluss des anderen Bots landen.
    """
    for pfad in (os.path.join(HERE, "data_store", "config.json"),
                 os.path.join(os.path.dirname(HERE), "data_store",
                              "config.json")):
        try:
            with open(pfad, encoding="utf-8") as f:
                wert = (json.load(f).get("dashboard") or {}).get("cockpit_port")
            if isinstance(wert, int) and 1024 < wert < 65536:
                return wert
        except Exception:
            continue
    return vorgabe


PORT = _port_aus_config()

def _find(name):
    """Sucht eine Datendatei robust: neben dem Skript, in data_store daneben,
    oder in data_store EINE Ebene hoeher. Egal ob Skript im Hauptordner oder
    im data_store liegt - es findet die Datei."""
    cands = [
        os.path.join(HERE, "data_store", name),   # Skript im Hauptordner
        os.path.join(HERE, name),                 # Skript direkt in data_store
        os.path.join(os.path.dirname(HERE), "data_store", name),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[0]  # Standard-Erwartung fuer die Fehlermeldung

def _find2(name):
    """Wie _find, aber fuer Dateien im HAUPTordner (config_*.json)."""
    for c in (os.path.join(HERE, name),
              os.path.join(os.path.dirname(HERE), name)):
        if os.path.exists(c):
            return c
    return os.path.join(HERE, name)


DB     = _find("trades_v5.json")
EQ_DB  = _find("equity_history.json")
EPOCHEN_DATEI = _find2("config_epochs.json")
ZIELE_DATEI = _find2("config_zielgroessen.json")
NACHLAUF_DB = _find("nachlauf.db")


def epochen():
    """Alle Epochen aus config_epochs.json, aelteste zuerst.

    [20.08.2026] Vorher standen im Cockpit zwei fest verdrahtete Karten:
    "E6.1 ab 14.07" und "E7 ab 17.07". Beide Daten stammten aus einer
    frueheren Zaehlung und existierten in config_epochs.json gar nicht
    mehr - die echte E7 begann am 15.08. Zwei verschiedene E7 auf einem
    Bildschirm, und die angezeigte war die falsche.

    Sven am 20.08.: "die E5-Messung ist ja veraltet und brauchen wir ja
    darauf nicht mehr, oder?" - richtig. Deshalb wird nichts mehr
    verdrahtet: die Karten lesen die Epochen und zeigen immer die
    LAUFENDE und die davor. Das veraltet nicht mehr.
    """
    try:
        with open(EPOCHEN_DATEI, encoding="utf-8") as f:
            e = json.load(f).get("epochs", [])
        e = [x for x in e if x.get("start")]
        e.sort(key=lambda x: x["start"])
        return e
    except Exception:
        return []


def ziele():
    try:
        with open(ZIELE_DATEI, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def nachlauf_bilanz():
    """Wie lief der Kurs NACH dem Ausstieg weiter? (Befund 59/60)

    Zeigt je Ausstiegsart den Mittelwert - und daneben die Zahl der
    unabhaengigen TAGE, nicht der Verkaeufe. 35 RSI-Ausstiege sehen nach
    viel aus und stammen von elf Tagen; auf Tagesebene traegt der Befund
    nicht. Wer nur die linke Zahl zeigt, verspricht Sicherheit, die es
    nicht gibt.
    """
    import sqlite3
    try:
        if not os.path.exists(NACHLAUF_DB):
            return []
        con = sqlite3.connect("file:" + NACHLAUF_DB.replace("\\", "/")
                              + "?mode=ro", uri=True, timeout=5)
        rows = con.execute(
            "SELECT grund, ts_utc, r1h, r24h FROM nachlauf "
            "WHERE art='exit' AND r1h IS NOT NULL").fetchall()
        con.close()
    except Exception:
        return []

    def art(g):
        g = (g or "").upper()
        for schl, name in (("RSI", "RSI overbought"),
                           ("TRAILING", "Trailing-Stop"),
                           ("BREAKEVEN", "Breakeven-Sperre"),
                           ("STOP", "Stop-Loss"),
                           ("TREND", "Trend-Exit"),
                           ("TAKE", "Take-Profit")):
            if schl in g:
                return name
        return "sonstiges"

    grp = collections.defaultdict(lambda: {"r1": [], "r24": [], "tage": set()})
    for g, ts, r1, r24 in rows:
        d = grp[art(g)]
        d["r1"].append(r1)
        if r24 is not None:
            d["r24"].append(r24)
        d["tage"].add(str(ts)[:10])
    raus = []
    for name, d in grp.items():
        raus.append(dict(
            art=name, n=len(d["r1"]), tage=len(d["tage"]),
            r1=round(sum(d["r1"]) / len(d["r1"]), 2) if d["r1"] else None,
            r24=round(sum(d["r24"]) / len(d["r24"]), 2) if d["r24"] else None))
    raus.sort(key=lambda x: -x["n"])
    return raus


_last_good = None  # letzter erfolgreich gelesener Stand (gegen halb-geschriebene Datei)


def load_equity():
    """Liest equity_history.json (Gesamt-Kapital ueber Zeit). Fehlt sie -> None."""
    try:
        with open(EQ_DB, encoding="utf-8") as f:
            e = json.load(f)
        tot = e.get("total", []) if isinstance(e, dict) else []
        vals = [p[1] for p in tot if isinstance(p, list) and len(p) == 2]
        if len(vals) > 120:
            step = len(vals) // 120
            vals = vals[::step]
        return vals
    except Exception:
        return None


def load_trades():
    global _last_good
    try:
        with open(DB, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, list):
            d = d.get("trades", []) if isinstance(d, dict) else []
        _last_good = d
        return d, None
    except FileNotFoundError:
        return _last_good, f"trades_v5.json nicht gefunden unter {DB}"
    except json.JSONDecodeError:
        return _last_good, "JSON wird gerade geschrieben - zeige letzten guten Stand"
    except Exception as e:
        return _last_good, str(e)[:100]


def _rr(rows):
    G = [float(t.get("pnl") or 0) for t in rows if float(t.get("pnl") or 0) > 0]
    L = [abs(float(t.get("pnl") or 0)) for t in rows if float(t.get("pnl") or 0) < 0]
    g = sum(G) / len(G) if G else 0
    l = sum(L) / len(L) if L else 0
    return dict(n=len(rows), net=round(sum(float(t.get("pnl") or 0) for t in rows), 2),
                wr=round(100 * len(G) / len(rows), 1) if rows else 0,
                g=round(g, 2), l=round(l, 2), rr=round(g / l, 2) if l else None,
                wins=len(G), losses=len(L))


def _wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * (c - h), 1), round(100 * (c + h), 1))


_DD_PUFFER = {"t": 0.0, "wert": None, "laeuft": False}


def _drawdown_gepuffert(gueltig_sek=600):
    """Siehe unten - rechnet im HINTERGRUND, blockiert die Seite nie."""
    import threading
    import time
    if (time.time() - _DD_PUFFER["t"]) < gueltig_sek:
        return _DD_PUFFER["wert"]
    # [FIX 20.08.2026] Nicht mehr im Anfrage-Faden rechnen.
    #
    # Gemessen: kapitalkurve() liest 210.401 Punkte und braucht 4,25 s,
    # die ganze Rechnung 4,88 s. Beim ersten Aufruf lief die Seite
    # deshalb in eine Zeitueberschreitung - ein Cockpit, das nicht
    # aufgeht, nuetzt niemandem.
    #
    # Jetzt: die Seite kommt sofort und zeigt "wird berechnet", der Wert
    # erscheint beim naechsten Refresh (60 s). Der Zeitstempel wird SOFORT
    # gesetzt, damit nicht bei jeder Anfrage ein neuer Faden startet.
    if not _DD_PUFFER.get("laeuft"):
        _DD_PUFFER["laeuft"] = True
        _DD_PUFFER["t"] = time.time()
        threading.Thread(target=_drawdown_rechnen, daemon=True,
                         name="drawdown").start()
    return _DD_PUFFER["wert"]


def _drawdown_rechnen():
    """Groesster Rueckschlag vom Hoechststand, hoechstens alle 10 Minuten neu.

    Nutzt drawdown_auswertung.py - dasselbe Werkzeug, das auch der
    Terminal-Reiter und stichtag.py benutzen. Zwei Wege zur selben Zahl
    waeren zwei Gelegenheiten, sich zu widersprechen.
    """
    import time
    wert = None
    try:
        import sys
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import drawdown_auswertung as da
        k = da.kapitalkurve()
        # [FIX 20.08.2026] Genau derselbe Weg wie in stichtag.py:214 -
        # sonst zeigen zwei Werkzeuge zwei Zahlen fuer dieselbe Sache.
        #
        # Ohne die Teilung stand hier 27,36 % statt 13,11 %. Grund: die
        # Kurve enthaelt zwei Kapital-NIVEAUS (vor und nach einer Ein-
        # oder Auszahlung). Ein Sprung zwischen zwei Niveaus ist kein
        # Rueckschlag des Handels - er saehe nur so aus.
        verdacht = da.zwei_niveaus(k)[0]
        erg = da.drawdown(da.geteilte_kurven(k)[0] if verdacht else k)
        if erg:
            wert = round(float(erg.get("max_dd_pct") or 0), 2)
    except Exception:
        wert = None
    _DD_PUFFER["t"] = time.time()
    _DD_PUFFER["wert"] = wert
    _DD_PUFFER["laeuft"] = False
    return wert


def compute(d):
    d = sorted(d, key=lambda t: (t.get("time", ""), t.get("_id", 0)))
    sells = [t for t in d if t.get("type") == "SELL"]
    if not sells:
        return None
    dt = lambda t: datetime.fromisoformat(t["time"])
    out = {}
    out["meta"] = dict(entries=len(d), sells=len(sells),
                       first=d[0]["time"][:10], last=d[-1]["time"][:16])
    out["gesamt"] = _rr(sells)
    # [20.08.2026] Epochen kommen jetzt aus config_epochs.json statt aus
    # fest verdrahteten Daten - siehe epochen(). Gezeigt werden die
    # LAUFENDE und die davor.
    ep = epochen()
    jetzt_ep = ep[-1] if ep else None

    # Als Vergleich die letzte Epoche VOR der laufenden, die ueberhaupt
    # Verkaeufe enthaelt.
    #
    # [20.08.2026] Die direkt vorhergehende (E6_messfenster, 13.-15.08.)
    # hat null Verkaeufe - zwei Tage, in denen nichts geschlossen wurde.
    # Eine Vergleichskarte mit n=0 vergleicht nichts. Welche Epoche es
    # geworden ist, steht in der Ueberschrift, es wird also nichts
    # verschleiert.
    vor_ep = None
    if jetzt_ep:
        _bis = datetime.fromisoformat(jetzt_ep["start"])
        if _bis.tzinfo is None:
            _bis = _bis.replace(tzinfo=timezone.utc)
        for e in reversed(ep[:-1]):
            _von = datetime.fromisoformat(e["start"])
            if _von.tzinfo is None:
                _von = _von.replace(tzinfo=timezone.utc)
            if any(_von <= dt(x) < _bis for x in sells):
                vor_ep = e
                break
            _bis = _von
    def _grenze(e):
        if not e:
            return None
        g = datetime.fromisoformat(e["start"])
        return g if g.tzinfo else g.replace(tzinfo=timezone.utc)

    # [FIX 20.08.2026] Die vorige Epoche muss OBEN begrenzt werden.
    #
    # Ohne Obergrenze hiess "seit dem 13.08." auch "einschliesslich allem,
    # was seit dem 15.08. kam" - beide Karten zeigten dieselben neun
    # Trades und dieselben 4,41 $. Ein Vergleich, bei dem beide Seiten
    # dasselbe enthalten, vergleicht nichts.
    ende_vor = _grenze(jetzt_ep)
    for schl, e, bis in (("e61", vor_ep, ende_vor), ("e7", jetzt_ep, None)):
        if not e:
            out[schl] = _rr([])
            out[schl + "_label"] = "-"
            continue
        grenze = _grenze(e)
        out[schl] = _rr([t for t in sells if dt(t) >= grenze
                         and (bis is None or dt(t) < bis)])
        out[schl + "_label"] = e["id"].replace("_", " ")
        out[schl + "_ab"] = grenze.strftime("%d.%m.")
        out[schl + "_tage"] = round(
            (datetime.now(timezone.utc) - grenze).total_seconds() / 86400, 1)

    out["ziele"] = ziele()
    out["nachlauf"] = nachlauf_bilanz()

    # Die zwei Kennzahlen, die den Live-Gang sperren.
    #
    # Erwartungswert: Mittel aus (Brutto-PnL minus K-BASIS) ueber ALLE
    # Verkaeufe. Nicht aus der Anzeige uebernommen, sondern hier eigens
    # gerechnet - eine Zahl, die man aus einer anderen Zahl abschreibt,
    # ist keine zweite Quelle.
    K = float(out["ziele"].get("kosten_je_runde_pct") or 0.505)
    netto = [float(x["pnl_pct"]) - K for x in sells
             if x.get("pnl_pct") is not None]
    out["ev_netto"] = round(sum(netto) / len(netto), 3) if netto else None

    # Groesster Rueckschlag: teuer zu rechnen (ueber 200.000 Messpunkte),
    # deshalb hoechstens alle zehn Minuten. Ohne den Zwischenspeicher
    # wuerde jeder 60-Sekunden-Refresh die ganze Kurve neu durchlaufen.
    out["drawdown"] = _drawdown_gepuffert()
    z = out["ziele"]
    fenster = z.get("messfenster_ende") or ""
    out["fenster_ende"] = fenster
    try:
        rest = (datetime.fromisoformat(fenster + "T00:00:00+00:00")
                - datetime.now(timezone.utc)).total_seconds() / 86400
        out["fenster_rest"] = round(rest, 1)
    except Exception:
        out["fenster_rest"] = None
    g = out["gesamt"]; out["wr_ci"] = _wilson(g["wins"], g["n"])

    coin = collections.defaultdict(list)
    for t in sells: coin[t["coin"].split("/")[0]].append(t)
    out["coins"] = sorted([dict(coin=c, **_rr(v)) for c, v in coin.items()], key=lambda x: -x["net"])

    ex = collections.defaultdict(list)
    for t in sells: ex[t.get("strategy") or "?"].append(t)
    out["exits"] = sorted([dict(strat=s, **_rr(v)) for s, v in ex.items()], key=lambda x: -x["net"])

    pos = collections.defaultdict(lambda: {"qty": 0.0, "cost": 0.0, "nbuys": 0})
    rows = []
    for t in d:
        c = t["coin"]; p = float(t["price"]); q = float(t["qty"]); P = pos[c]
        if t["type"] == "BUY":
            P["qty"] += q; P["cost"] += p * q; P["nbuys"] += 1
        elif t["type"] == "SELL" and P["qty"] > 1e-12:
            rows.append(dict(nbuys=P["nbuys"], pnl=float(t.get("pnl") or 0)))
            used = min(q, P["qty"]); P["cost"] -= (P["cost"] / P["qty"]) * used; P["qty"] -= used
            if P["qty"] < 1e-9: P.update({"qty": 0.0, "cost": 0.0, "nbuys": 0})
    dca = collections.defaultdict(list)
    for r in rows: dca[min(r["nbuys"], 3)].append(r["pnl"])
    out["dca"] = []
    for k in sorted(dca):
        v = dca[k]; G = [x for x in v if x > 0]; L = [abs(x) for x in v if x < 0]
        gg = sum(G) / len(G) if G else 0; ll = sum(L) / len(L) if L else 0
        out["dca"].append(dict(kaeufe=("1" if k == 1 else "2" if k == 2 else "3+"),
                               n=len(v), net=round(sum(v), 2),
                               rr=round(gg / ll, 2) if ll else None, ovl=round(ll, 2)))

    wf = [t for t in sells if isinstance(t.get("fee"), (int, float))]
    rates = [float(t["fee"]) / float(t["amount"]) * 100 for t in wf
             if float(t.get("amount") or 0) > 0 and float(t.get("fee") or 0) > 0]
    pcts = [float(t["pnl_pct"]) for t in sells if isinstance(t.get("pnl_pct"), (int, float))]
    wins = [w for w in pcts if w > 0]
    mr = st.median(rates) if rates else 0.1
    below = sum(1 for w in wins if w < 2 * mr)
    out["fee"] = dict(rate=round(mr, 4), roundtrip=round(2 * mr, 3),
                      median_win=round(st.median(wins), 3) if wins else None,
                      drag=round(100 * 2 * mr / st.median(wins), 0) if wins else None,
                      below_n=below, win_n=len(wins),
                      below_pct=round(100 * below / len(wins), 0) if wins else 0)

    mm = [t for t in sells if isinstance(t.get("mfe_pct"), (int, float))]
    out["mfe"] = [dict(coin=t["coin"].split("/")[0], pnl_pct=t.get("pnl_pct"),
                       mfe=t.get("mfe_pct"), mae=t.get("mae_pct"),
                       giveback=round(float(t["mfe_pct"]) - float(t.get("pnl_pct") or 0), 2),
                       strat=t.get("strategy")) for t in mm]
    out["mfe_n"] = len(mm)

    # [20.08.2026] E61 gab es nicht mehr, seit die Epochen aus der
    # Konfiguration kommen. Die Kurve laeuft jetzt ueber die Verkaeufe
    # der VORIGEN Epoche - dieselbe Menge, nur nicht mehr an ein festes
    # Datum genagelt.
    cum = 0
    spark = []
    _vor = vor_ep and datetime.fromisoformat(vor_ep["start"])
    if _vor is not None and _vor.tzinfo is None:
        _vor = _vor.replace(tzinfo=timezone.utc)
    for x in sells:
        if _vor is None or dt(x) >= _vor:
            cum += float(x.get("pnl") or 0)
            spark.append(round(cum, 2))
    out["spark_e61"] = spark
    # Fortschrittsbalken: Tage bis zum Ende des Messfensters, nicht bis
    # zum 31.07. - das lag beim Umbau schon drei Wochen zurueck.
    out["e7_progress"] = dict(
        sells=out["e7"]["n"], target=out["ziele"].get("mindest_fallzahl", 30),
        days_left=max(0, int(out.get("fenster_rest") or 0)))
    eq = load_equity()
    out["equity"] = eq if eq else []
    return out


def render(D, err):
    if D is None:
        return ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<meta http-equiv=refresh content=15><title>V6 Cockpit</title></head>"
                "<body style='background:#0d1117;color:#e6edf3;font-family:monospace;padding:40px'>"
                f"<h2>Cockpit wartet auf Daten…</h2><p>{err or 'keine Verkaeufe gefunden'}</p>"
                f"<p style='color:#8b98a9'>Gesucht: {DB}</p></body></html>")
    data_js = json.dumps(D, ensure_ascii=False)
    banner = f"<div style='background:rgba(210,153,34,.12);border:1px solid #d29922;color:#d29922;font-family:monospace;font-size:12px;padding:8px 14px;border-radius:8px;margin-bottom:14px'>⚠ {err}</div>" if err else ""
    return TEMPLATE.replace("__BANNER__", banner) \
        .replace("__LAST__", D["meta"]["last"]).replace("__ENTRIES__", str(D["meta"]["entries"])) \
        .replace("__SELLS__", str(D["meta"]["sells"])).replace("__DATA__", data_js)


TEMPLATE = r"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60"><title>V6 Analyse-Cockpit</title>
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2230;--line:#2b3444;--ink:#e6edf3;--dim:#8b98a9;--faint:#5b6675;--green:#3fb950;--red:#f85149;--amber:#d29922;--blue:#58a6ff;--mono:ui-monospace,'Cascadia Code','Consolas',monospace;--sans:-apple-system,'Segoe UI',Roboto,sans-serif;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.5}
.wrap{max-width:1160px;margin:0 auto;padding:22px 18px 60px}
header{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:4px}h1{font-size:20px;margin:0}
.ro{font-family:var(--mono);font-size:10px;color:var(--amber);border:1px solid var(--amber);border-radius:4px;padding:2px 7px;letter-spacing:1px}
.sub{color:var(--dim);font-size:12px;font-family:var(--mono);margin:2px 0 20px}
.grid{display:grid;gap:14px}.g3{grid-template-columns:repeat(3,1fr)}.g2{grid-template-columns:repeat(2,1fr)}
@media(max-width:820px){.g3,.g2{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.card h2{font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:var(--faint);margin:0 0 14px;font-weight:600;font-family:var(--mono)}
.big{font-size:30px;font-weight:700;font-family:var(--mono);line-height:1}.lbl{font-size:11px;color:var(--dim);font-family:var(--mono);margin-top:5px}
.kv{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--line);font-family:var(--mono);font-size:13px}.kv:last-child{border-bottom:0}.kv .v{font-weight:600}
.pos{color:var(--green)}.neg{color:var(--red)}.neu{color:var(--dim)}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12.5px}
th{text-align:right;color:var(--faint);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--line);font-size:10.5px}th:first-child,td:first-child{text-align:left}
td{padding:6px 8px;border-bottom:1px solid #212836}tr:last-child td{border-bottom:0}
.bar{height:5px;border-radius:3px;background:var(--panel2);overflow:hidden;margin-top:3px}.bar>i{display:block;height:100%}
.note{font-size:12px;color:var(--dim);margin-top:10px;line-height:1.55}
.flag{border-left:3px solid var(--red);padding:10px 14px;background:rgba(248,81,73,.06);border-radius:0 8px 8px 0;margin-top:12px}
.flag.amber{border-color:var(--amber);background:rgba(210,153,34,.06)}.flag b{font-family:var(--mono);font-size:12px}
.pill{font-family:var(--mono);font-size:10px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);color:var(--dim)}
.foot{color:var(--faint);font-size:11px;font-family:var(--mono);margin-top:26px;text-align:center;line-height:1.7}
.spark{width:100%;height:auto;display:block;margin-top:6px}
</style></head><body><div class="wrap">
__BANNER__
<header><h1>⚡ Trading Imperium V7 · Analyse-Cockpit</h1><span class="ro">LIVE · READ-ONLY · 60s</span></header>
<div class="sub">Stand: __LAST__ UTC · __ENTRIES__ Eintraege · __SELLS__ Verkaeufe · nur V6-Daten, selbst berechnet</div>
<div class="grid g3">
  <div class="card"><h2>Gesamt</h2><div class="big neg" id="g_net"></div><div class="lbl">Netto-PnL · <span id="g_n"></span> Trades</div>
    <div style="margin-top:14px"><div class="kv"><span>Win-Rate</span><span class="v" id="g_wr"></span></div><div class="kv"><span>WR 95%-CI</span><span class="v neu" id="g_ci"></span></div><div class="kv"><span>R/R</span><span class="v neg" id="g_rr"></span></div><div class="kv"><span>Ø Gew/Verl</span><span class="v" id="g_gl"></span></div></div></div>
  <div class="card"><h2><span id="e61_title">Epoche davor</span> <span class="pill">Vergleich</span></h2><div class="big pos" id="e61_net"></div><div class="lbl">Netto-PnL · <span id="e61_n"></span> Trades</div>
    <div style="margin-top:14px"><div class="kv"><span>Win-Rate</span><span class="v" id="e61_wr"></span></div><div class="kv"><span>R/R</span><span class="v" id="e61_rr"></span></div><div class="kv"><span>Ø Gew/Verl</span><span class="v" id="e61_gl"></span></div><div class="kv"><span>Aussagekraft</span><span class="v neu" id="e61_warn"></span></div></div></div>
  <div class="card"><h2><span id="e7_title">laufende Epoche</span> <span class="pill">laeuft</span></h2><div class="big pos" id="e7_net"></div><div class="lbl">Netto-PnL · <span id="e7_n"></span> Trades</div>
    <div style="margin-top:14px"><div class="kv"><span>R/R vs Basis</span><span class="v" id="e7_rr"></span></div><div class="kv"><span>Sells</span><span class="v" id="e7_sells"></span></div><div class="kv"><span>Messfenster endet</span><span class="v neu" id="e7_days"></span></div><div class="bar" style="margin-top:8px"><i id="e7_bar" style="background:var(--green)"></i></div></div></div>
</div>
<div class="grid g2" style="margin-top:14px">
  <div class="card"><h2>Freischaltung fuer Live <span class="pill">config_zielgroessen</span></h2>
    <div id="ziel_body"></div>
    <div class="note">Nur diese zwei Kennzahlen sperren den Live-Gang. Alle
    uebrigen laufen im Schattenmodus mit: gemessen und angezeigt, aber ohne
    Sperrwirkung. Die verschenkte Bewegung liesse sich trivial auf null
    bringen, indem man sofort verkauft - eine Zielgroesse, die man durch
    Verschlechtern erreicht, taugt nicht als Bedingung.</div></div>
  <div class="card"><h2>Nach dem Ausstieg <span class="pill">nachlauf.db</span></h2>
    <table><tr><th>Ausstiegsart</th><th>n</th><th>Tage</th><th>+1h</th><th>+24h</th></tr>
    <tbody id="nach_rows"></tbody></table>
    <div class="note" id="nach_note"></div></div>
</div>
<div class="grid g2" style="margin-top:14px">
  <div class="card"><h2>Kapitalverlauf · echte Equity <span class="pill">equity_history</span></h2>
    <svg class="spark" id="eq_svg" viewBox="0 0 520 90" preserveAspectRatio="none"></svg>
    <div class="note" id="eq_note"></div></div>
  <div class="card"><h2>🔑 Kernbefund · Averaging Down <span class="pill">aus trades_v5</span></h2><table><tr><th>Kaeufe/Position</th><th>n</th><th>Netto$</th><th>Ø&nbsp;Verl.</th><th>R/R</th></tr><tbody id="dca_rows"></tbody></table>
    <div class="flag" id="dca_flag"></div></div>
</div>
<div class="grid g2" style="margin-top:14px">
  <div class="card"><h2>Nach Ausstiegs-Grund</h2><table><tr><th>Strategie</th><th>n</th><th>Netto$</th><th>WR%</th><th>R/R</th></tr><tbody id="exit_rows"></tbody></table>
    <div class="note">STOP_LOSS/TREND_EXIT sind per Definition negativ (Ausstiegsgrund). Aussagekraeftig ist der Netto-Saldo pro Coin.</div></div>
  <div class="card"><h2>Nach Coin (Netto-Saldo)</h2><table><tr><th>Coin</th><th>n</th><th>Netto$</th><th>WR%</th><th>R/R</th></tr><tbody id="coin_rows"></tbody></table>
    <div class="note">Kumuliert seit Datei-Beginn. XRP ist in E6 bereits aus dem aktiven Handel.</div></div>
</div>
<div class="card" style="margin-top:14px"><h2>Hinweis · Strategie-Performance (bewusst weggelassen)</h2>
  <div class="note">In V6 steigt real nur <b>DCA_FEAR_GREED</b> ein (bei 329 von 405 Verkaeufen ist keine andere Entry-Strategie gesetzt). Die Datei <b>brain_performance.json</b> zeigt zwar ICHIMOKU/FIBONACCI/EMA mit hohen Gewinnen — das sind aber <b>V4-Bootstrap-Werte</b> (source: v4_bootstrap, v6_trades_added = 0), kein reiner V6-Ertrag. Um V6 sauber zu halten, wird sie hier NICHT angezeigt. Was V6 real steuert, sind die <b>Ausstiegs-Wege</b> (Tabelle oben links).</div></div>
<div class="grid g2" style="margin-top:14px">
  <div class="card"><h2>Gebuehren-Analyse</h2><div class="kv"><span>Gebuehr pro Seite</span><span class="v" id="f_rate"></span></div><div class="kv"><span>Roundtrip</span><span class="v" id="f_rt"></span></div><div class="kv"><span>Median-Gewinntrade</span><span class="v" id="f_mw"></span></div><div class="kv"><span>Fee-Anteil am Rohgewinn</span><span class="v neg" id="f_drag"></span></div>
    <div class="flag amber"><b id="f_below"></b> Unter der Fee-Schwelle = nach Gebuehren Nullnummern. Kandidat E8/E9: Trailing-Schwelle ueber Fee-Niveau heben.</div></div>
  <div class="card"><h2>MFE/MAE-Messung <span class="pill">neu · sammelt</span></h2><div id="mfe_body"></div></div>
</div>
<div class="foot">Lokales Live-Cockpit · liest trades_v5.json + equity_history.json bei jedem Refresh (60s) · nur dieser Rechner (127.0.0.1) · nur V6-Daten · kein Eingriff ins Trading.</div>
</div>
<script>
const D=__DATA__;
const f2=x=>(x==null?'–':(x>0?'+':'')+Number(x).toFixed(2));
const cls=x=>x==null?'neu':(x>0?'pos':(x<0?'neg':'neu'));
const set=(id,txt,c)=>{const e=document.getElementById(id);if(!e)return;e.textContent=txt;if(c)e.className=e.className.replace(/\b(pos|neg|neu)\b/g,'').trim()+' '+c;};
set('g_net',f2(D.gesamt.net)+'$');set('g_n',D.gesamt.n);set('g_wr',D.gesamt.wr+'%');set('g_ci',D.wr_ci[0]+'–'+D.wr_ci[1]+'%');set('g_rr',D.gesamt.rr);set('g_gl','+'+D.gesamt.g+' / −'+D.gesamt.l);
set('e61_net',f2(D.e61.net)+'$');set('e61_n',D.e61.n);set('e61_wr',D.e61.wr+'%');set('e61_rr',D.e61.rr,cls((D.e61.rr||0)-1));set('e61_gl','+'+D.e61.g+' / −'+D.e61.l);
const basis=D.e61.rr||0;
set('e7_net',f2(D.e7.net)+'$');set('e7_n',D.e7.n);set('e7_rr',D.e7.rr+((D.e7.rr>=basis)?'  ▲':'  ▼'),cls((D.e7.rr||0)-basis));set('e7_sells',D.e7.n+' / '+D.e7_progress.target+' ✓');set('e7_days',D.e7_progress.days_left+' Tage');
document.getElementById('e7_bar').style.width=Math.min(100,100*D.e7.n/D.e7_progress.target)+'%';
(function(){
  const eq=D.equity||[]; const svg=document.getElementById('eq_svg'); if(!svg) return;
  if(eq.length<2){svg.innerHTML='<text x="10" y="45" fill="#5b6675" font-size="11">keine Equity-Daten</text>';document.getElementById('eq_note').textContent='equity_history.json nicht gefunden.';return;}
  const W=520,H=80,lo=Math.min(...eq),hi=Math.max(...eq),rng=(hi-lo)||1;
  const pts=eq.map((v,i)=>`${(i*(W/(eq.length-1))).toFixed(1)},${(H-((v-lo)/rng)*H).toFixed(1)}`).join(' ');
  svg.innerHTML=`<polyline points="${pts}" fill="none" stroke="#58a6ff" stroke-width="2"/>`;
  document.getElementById('eq_note').textContent='Gesamt-Kapital ueber die letzten '+eq.length+' Messpunkte · '+lo.toFixed(1)+'$ bis '+hi.toFixed(1)+'$ · aktuell '+eq[eq.length-1].toFixed(2)+'$.';
})();
document.getElementById('dca_rows').innerHTML=D.dca.map(r=>`<tr><td>${r.kaeufe}</td><td>${r.n}</td><td class="${cls(r.net)}">${f2(r.net)}</td><td>${r.ovl}</td><td>${r.rr??'–'}</td></tr>`).join('');
document.getElementById('dca_flag').innerHTML='<b>Positionen ohne Nachkauf: '+f2(D.dca[0].net)+'$. Das gesamte Minus stammt aus nachgekauften Positionen.</b> Fix = E8 (nach E7): Nachkauf in Verlustpositionen abschalten.';
document.getElementById('exit_rows').innerHTML=D.exits.map(r=>`<tr><td>${r.strat}</td><td>${r.n}</td><td class="${cls(r.net)}">${f2(r.net)}</td><td>${r.wr}</td><td>${r.rr??'–'}</td></tr>`).join('');
document.getElementById('coin_rows').innerHTML=D.coins.map(r=>`<tr><td>${r.coin}</td><td>${r.n}</td><td class="${cls(r.net)}">${f2(r.net)}</td><td>${r.wr}</td><td>${r.rr??'–'}</td></tr>`).join('');
set('f_rate',D.fee.rate+'%');set('f_rt',D.fee.roundtrip+'%');set('f_mw',(D.fee.median_win!=null?'+'+D.fee.median_win+'%':'–'));set('f_drag',(D.fee.drag!=null?D.fee.drag+'% weg':'–'));
document.getElementById('f_below').textContent=D.fee.below_n+' von '+D.fee.win_n+' Gewinnern ('+D.fee.below_pct+'%).';
// [20.08.2026] Epochen-Titel aus config_epochs.json
if(D.e61_label){document.getElementById('e61_title').textContent=D.e61_label+' · ab '+(D.e61_ab||'?');}
if(D.e7_label){document.getElementById('e7_title').textContent=D.e7_label+' · ab '+(D.e7_ab||'?');}
// Kleine Fallzahl NICHT verschweigen. Acht gegen neun Verkaeufe sehen aus
// wie ein Ergebnis und sind keins - der Unterschied waere auch bei zwei
// gleich guten Regeln so gross.
(function(){
  const noetig=(D.ziele&&D.ziele.mindest_fallzahl)||30;
  const a=(D.e61&&D.e61.n)||0, b=(D.e7&&D.e7.n)||0;
  const el=document.getElementById('e61_warn');
  if(el){el.textContent=(a<noetig||b<noetig)
    ?(a+' vs '+b+' Verkaeufe · zu wenig fuer ein Urteil')
    :(a+' vs '+b+' Verkaeufe');
   el.className='v '+((a<noetig||b<noetig)?'neu':'pos');}
})();
set('e7_days',(D.fenster_ende||'?')+(D.fenster_rest!=null?' ('+D.fenster_rest+' Tage)':''));

// Freischaltung: nur Erwartungswert und groesster Rueckschlag sperren
(function(){
  const z=D.ziele||{}, g=D.gesamt||{};
  const ev=(g.n?(g.net_pct!=null?g.net_pct:null):null);
  const zeilen=[];
  const reihe=(name,ist,huerde,hoch,quelle)=>{
    if(ist==null){return `<div class="kv"><span>${name}</span><span class="v neu">noch nicht gemessen</span></div>`;}
    const ok=hoch?(ist>huerde):(ist<=huerde);
    return `<div class="kv"><span>${name} <span class="pill">${quelle}</span></span>`
         + `<span class="v ${ok?'pos':'neg'}">${ist>0&&hoch?'+':''}${ist} ${ok?'· LIVE OK':'· SPERRT'}</span></div>`;
  };
  const ez=(z.ev_netto_pct||{}), dz=(z.max_drawdown_pct||{});
  zeilen.push(reihe('Erwartungswert je Trade',D.ev_netto,ez.freischaltung_ab!=null?ez.freischaltung_ab:0,true,'Huerde &gt;'+(ez.freischaltung_ab!=null?ez.freischaltung_ab:0)+'%'));
  zeilen.push(reihe('Groesster Rueckschlag',D.drawdown,dz.freischaltung_ab!=null?dz.freischaltung_ab:20,false,'Huerde &le;'+(dz.freischaltung_ab!=null?dz.freischaltung_ab:20)+'%'));
  zeilen.push(`<div class="kv"><span>Fallzahl</span><span class="v ${g.n>=(z.mindest_fallzahl||30)?'pos':'neu'}">${g.n} Verkaeufe · noetig ${z.mindest_fallzahl||30}</span></div>`);
  zeilen.push(`<div class="kv"><span>Kosten je Runde (K-BASIS)</span><span class="v neu">${z.kosten_je_runde_pct||'?'}%</span></div>`);
  document.getElementById('ziel_body').innerHTML=zeilen.join('');
})();

// Nach dem Ausstieg - Tage statt Verkaeufe als Mass der Sicherheit
(function(){
  const n=D.nachlauf||[];
  const tb=document.getElementById('nach_rows');
  if(!n.length){tb.innerHTML='<tr><td colspan="5">Noch keine Nachlaufwerte.</td></tr>';return;}
  tb.innerHTML=n.map(r=>`<tr><td>${r.art}</td><td>${r.n}</td><td>${r.tage}</td>`
    +`<td class="${r.r1>0?'pos':'neg'}">${r.r1>0?'+':''}${r.r1}%</td>`
    +`<td class="${r.r24>0?'pos':'neg'}">${r.r24==null?'–':(r.r24>0?'+':'')+r.r24+'%'}</td></tr>`).join('');
  document.getElementById('nach_note').innerHTML=
    'Positiv heisst: der Kurs lief nach dem Verkauf WEITER hoch - der Ausstieg kam zu frueh. '
    +'Die Spalte <b>Tage</b> ist das eigentliche Mass: der Bot verkauft mehrere Muenzen '
    +'in derselben Marktbewegung, deshalb sind 35 Verkaeufe an elf Tagen keine 35 '
    +'unabhaengigen Faelle. Unter etwa 25 Tagen traegt keine Zeile ein Urteil.';
})();

const m=D.mfe;
if(m.length){document.getElementById('mfe_body').innerHTML=`<div class="kv"><span>Erfasste Trades</span><span class="v">${D.mfe_n}</span></div>`+m.map(t=>`<div class="kv"><span>${t.coin} · ${t.strat}</span><span class="v">MFE +${t.mfe}% / MAE ${t.mae}%</span></div><div class="kv"><span>&nbsp;&nbsp;↳ Ausstieg / Give-Back</span><span class="v neu">+${t.pnl_pct}% · gab ${t.giveback}% zurueck</span></div>`).join('')+`<div class="note">Sammelt ab jedem Verkauf. Ab ~20–30 Trades wird die Give-Back-Analyse aussagekraeftig.</div>`;}else{document.getElementById('mfe_body').innerHTML='<div class="note">Noch keine Trades mit MFE/MAE erfasst.</div>';}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200); self.send_header("Content-Type", "text/plain"); self.end_headers()
            self.wfile.write(b"ok"); return
        d, err = load_trades()
        try:
            D = compute(d) if d else None
        except Exception as e:
            D, err = None, f"Rechenfehler: {str(e)[:80]}"
        html = render(D, err)
        b = html.encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)


if __name__ == "__main__":
    print(f"V6 Analyse-Cockpit laeuft:  http://localhost:{PORT}")
    print(f"Liest Trades:  {DB}")
    print(f"Liest Equity:  {EQ_DB}")
    print("Stoppen mit Strg+C.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()