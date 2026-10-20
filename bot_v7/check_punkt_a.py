# -*- coding: utf-8 -*-
# check_punkt_a.py - Liest NUR, aendert NICHTS.
# Prueft: E6-A (XRP raus), E6-B (ADA-Stop 3.0), F&G-URL-Fix, P1-Haertung, Doc-Dedupe
# Ausfuehren (Bot darf laufen, reine Lesezugriffe):
#   python check_punkt_a.py > check_a.txt 2>&1

import json, os, re, sys

# [17.09.2026] Hier stand der Papier-Ordner fest eingetragen:
#     BASE = r"C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)"
# Diese Datei liegt aber im LIVE-Ordner. Sie hat also die Einstellungen
# des PAPIER-Bots geprueft und das Ergebnis als das des Live-Bots
# ausgegeben - ohne Hinweis, dass sie woanders hinsieht. Seit dem 14.09.
# gibt es zwei Ordner; ein Werkzeug, das den falschen prueft, meldet
# "alles in Ordnung" ueber ein System, das es gar nicht angesehen hat.
BASE = os.path.dirname(os.path.abspath(__file__))

def find_file(name):
    # exakte Treffer zuerst im Root, dann Unterordner (Backup\v4 ausgeschlossen)
    root_hit = os.path.join(BASE, name)
    if os.path.isfile(root_hit):
        return root_hit
    for dirpath, dirnames, filenames in os.walk(BASE):
        low = dirpath.lower()
        if "backup" in low or "v4_archiv" in low or "__pycache__" in low:
            dirnames[:] = []
            continue
        if name in filenames:
            return os.path.join(dirpath, name)
    return None

def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return ""

def flag(ok):
    return "JA" if ok else "NEIN  <-- PRUEFEN"

print("=" * 60)
print("ABNAHME-CHECK PUNKT A  (nur lesen, nichts geaendert)")
print("=" * 60)

# ---------- 1) E6-A: XRP raus, 11 Coins ----------
print("\n[1] E6-A - XRP pausiert")
cfg_path = find_file("config.json")
if cfg_path and "data_store" not in cfg_path:
    # bevorzugt data_store\config.json
    alt = os.path.join(BASE, "data_store", "config.json")
    if os.path.isfile(alt):
        cfg_path = alt
if cfg_path:
    print("    Datei:", cfg_path)
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        tr = cfg.get("trading", {})
        coins = tr.get("coins", [])
        paused = tr.get("paused_coins", [])
        xrp_active = any("XRP" in str(c) for c in coins)
        print("    Aktive Coins:", len(coins), "->", [str(c).split("/")[0] for c in coins])
        print("    XRP in paused_coins:", flag(any("XRP" in str(c) for c in paused)))
        print("    XRP aus aktiver Liste raus:", flag(not xrp_active))
        print("    ERGEBNIS E6-A:", flag(len(coins) == 11 and not xrp_active))
    except Exception as e:
        print("    FEHLER beim Lesen:", e)
else:
    print("    config.json NICHT GEFUNDEN")

# ---------- 2) E6-B: ADA-Stop 3.0 Per-Coin-Override in app.py ----------
print("\n[2] E6-B - ADA-Stop 3.0% (Per-Coin-Override)")
app_path = find_file("app.py")
app = read(app_path) if app_path else ""
if app:
    print("    Datei:", app_path)
    hit = re.search(r'["\']ADA/USDC["\']\s*:\s*3(\.0|\.5)?', app)
    print("    Override-Dict mit ADA/USDC=3.x im Code:", flag(bool(hit)))
    if hit:
        print("    Fundstelle:", hit.group(0))
    print("    ERGEBNIS E6-B:", flag(bool(hit)))
else:
    print("    app.py NICHT GEFUNDEN")

# ---------- 3) F&G-URL-Fix in market_data.py ----------
print("\n[3] F&G-URL-Fix")
md_path = find_file("market_data.py")
md = read(md_path) if md_path else ""
if md:
    print("    Datei:", md_path)
    wrong = "/fnd/v2/crypto" in md
    right = "alternative.me/fng" in md or "/fng/" in md
    print("    Falsche URL (/fnd/v2/crypto) noch drin:", "JA  <-- PRUEFEN" if wrong else "NEIN (gut)")
    print("    Richtige URL (/fng/) drin:", flag(right))
    print("    ERGEBNIS F&G-Fix:", flag(right and not wrong))
else:
    print("    market_data.py NICHT GEFUNDEN")

# ---------- 4) P1-Haertung: blanke except: im Preis-Pfad ----------
print("\n[4] P1-Haertung - blanke except: im Preis-Pfad")
def bare_excepts(text):
    return [i + 1 for i, line in enumerate(text.splitlines())
            if re.match(r"^\s*except\s*:\s*(#.*)?$", line)]
if md:
    b = bare_excepts(md)
    print("    market_data.py blanke except: Zeilen:", b if b else "keine (gut)")
lr_path = find_file("live_runner.py")
lr = read(lr_path) if lr_path else ""
if lr:
    b2 = bare_excepts(lr)
    print("    live_runner.py blanke except: Zeilen:", b2 if b2 else "keine (gut)")
    ok_p1 = (not bare_excepts(md)) and (not b2) if md else (not b2)
    print("    ERGEBNIS P1-Haertung:", flag(ok_p1))
else:
    print("    live_runner.py NICHT GEFUNDEN")

# ---------- 5) Doc-Dedupe deployed? ----------
print("\n[5] Doc-Dedupe (install_doc_dedupe.py)")
da_path = find_file("doc_agent.py")
da = read(da_path) if da_path else ""
if da:
    print("    Datei:", da_path)
    marker = "last_report_date" in da
    print("    Dedupe-Guard (last_report_date) im Code:", flag(marker))
    print("    ERGEBNIS Doc-Dedupe:", "DEPLOYED" if marker else "NICHT deployed <-- Installer liegt bereit")
else:
    print("    doc_agent.py NICHT GEFUNDEN")

print("\n" + "=" * 60)
print("FERTIG. Diese Datei (check_a.txt) im Chat hochladen.")
print("=" * 60)
