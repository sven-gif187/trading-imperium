# -*- coding: utf-8 -*-
"""
GELDFLUSS-Tab: Intermarket-Beobachtungsdeck. [GELDFLUSS-TAB 20.07.2026]
[AUDIT 06.08.2026 - reine Anzeige, keine Bot-Anbindung]

Zeigt: Marktgroessen-Landkarte (Aktien/Gold/Krypto/BTC), BTC-Dominanz-
Rotation, 30/90d-Asset-Rennen (BTC vs Gold vs S&P via yfinance),
Ratios - und schreibt taeglich EINEN Snapshot in
data_store/geldfluss_history.json (eigene Datei, kein Trading-Eingriff).

REINE ANZEIGE. Alle Netz-Calls: Timeout + Cache + sichtbarer Fehler.
Ehrlichkeit eingebaut: Beobachtungsdeck, keine Signale (macro_replay-
Lektion: Makro-Muster brauchen Beweis vor jeder Bot-Integration).

WAS DIESER TAB NICHT IST (Audit 06.08.2026): Er misst KEINEN Kapitalfluss.
Es gibt hier keine Exchange-Zu-/Abfluesse, keine Stablecoin-Supply, keine
ETF-Flows, kein Open Interest, kein Funding, keine Liquidationen. Gezeigt
werden Marktkapitalisierungs-ANTEILE und relative Preisperformance. Eine
steigende Dominanz kann aus Zufluessen, aus Abfluessen anderswo ODER aus
reiner Preisbewegung ohne jeden Fluss entstehen - der Tab kann diese Faelle
nicht unterscheiden.

Aenderungen 06.08.2026:
  - Datumsindex bleibt erhalten; Ratios und Renditen rechnen auf der
    gemeinsamen Datumsmenge statt auf Listenpositionen.
  - Renditen ueber Kalendertage statt Datenpunkte, mit Ausweis des
    tatsaechlich verwendeten Abstands.
  - Unvollstaendige Tagesschnappschuesse werden nachgeholt statt zementiert.
  - Netzfehler werden mit Grund angezeigt statt als "offline" verschluckt.
"""
import os, json, time
from datetime import datetime, date, timezone

C_HDR, C_LBL, C_POS, C_NEG, C_MAG, C_DIM, C_TXT, C_WRN = \
    "hdr", "lbl", "pos", "neg", "mag", "dim", "txt", "wrn"

REFRESH_MS = 15 * 60 * 1000          # 15 min - Makro-Daten sind langsam
CACHE_TTL = 14 * 60                   # Sekunden

# Referenz-Landkarte (traege Groessen; Quelle Jul 2026: WGC/SIFMA-Schaetzungen)
# [AUDIT] Statische Schaetzwerte. Sie altern still - deshalb steht das Datum
# jetzt auch im UI, damit niemand sie fuer Live-Werte haelt.
REF_AKTIEN_T = 120.0                  # Billionen $
REF_GOLD_T = 33.0
REF_STAND = "Jul 2026"

# Felder, die ein vollstaendiger Tagesschnappschuss enthalten muss.
PFLICHTFELDER = ("total_t", "btc_dom", "eth_dom", "btc", "gold", "spx")

_CACHE = {"t": 0, "cg": None, "yf": None, "fehler": {}}


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _hist_path():
    return os.path.join(_root(), "data_store", "geldfluss_history.json")


# ----------------------------------------------------------------------
# Netz
# ----------------------------------------------------------------------
def _fetch_coingecko():
    """Total-Cap + Dominanz. Kostenlos, kein Key. -> (daten, fehlertext)."""
    try:
        import requests
    except Exception as e:
        return None, f"requests fehlt: {str(e)[:40]}"
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        d = r.json().get("data", {})
        return {
            "total_t": d["total_market_cap"]["usd"] / 1e12,
            "btc_dom": d["market_cap_percentage"]["btc"],
            "eth_dom": d["market_cap_percentage"].get("eth"),
        }, ""
    except Exception as e:
        # [AUDIT] Vorher: except -> None. Rate-Limit, DNS-Fehler und eine
        # geaenderte JSON-Struktur sahen im UI alle identisch als "offline" aus.
        return None, f"{type(e).__name__}: {str(e)[:45]}"


def _fetch_yfinance():
    """120 Tage Schlusskurse fuer BTC / Gold / S&P - MIT Datum.

    [AUDIT 06.08.2026] Vorher wurde der Datumsindex verworfen (h.tolist()).
    Dadurch paarten die Ratios die letzten N Punkte zweier Reihen mit
    unterschiedlicher Handelsfrequenz elementweise: BTC-USD handelt 24/7,
    GC=F und ^GSPC nur an Handelstagen. Gemessen am 06.08.2026:
    BTC-USD n=119, GC=F n=99, ^GSPC n=120. Bei zip(a[-91:], b[-91:]) lagen
    die jeweils 91. Punkte damit rund sechs Wochen auseinander, und der
    Versatz zog sich durch die ganze Reihe.

    ZWEITER Befund derselben Messung: die Zeitzonen der Indizes sind
    verschieden - BTC-USD liefert UTC, GC=F und ^GSPC America/New_York.
    Der Datumsschluessel kam also aus zwei Zeitzonen. Wird hier auf UTC
    normalisiert, damit die Konvention explizit ist.

    DRITTER Befund: BTC-USD hatte am 06.08.2026 eine Luecke - der Index
    springt von 2026-08-04 auf 2026-08-06, der 05.08. fehlt ganz. Auch die
    24/7-Reihe ist also nicht lueckenlos. Deshalb wird die Punktzahl je
    Reihe mitgefuehrt und im UI ausgewiesen.

    Rueckgabe: ({key: {datum_iso_utc: close}}, {key: fehlertext}).
    """
    try:
        import yfinance as yf
    except Exception as e:
        return None, {"yfinance": f"Import: {str(e)[:45]}"}
    out, fehler = {}, {}
    for key, tick in (("BTC", "BTC-USD"), ("GOLD", "GC=F"), ("SPX", "^GSPC")):
        try:
            h = yf.Ticker(tick).history(period="120d")["Close"].dropna()
            if len(h) < 30:
                fehler[key] = f"nur {len(h)} Punkte"
                continue
            reihe = {}
            for idx, v in h.items():
                try:
                    tag = idx.tz_convert("UTC").date() if idx.tzinfo else idx.date()
                except Exception:
                    tag = idx.date()
                reihe[str(tag)] = float(v)
            out[key] = reihe
        except Exception as e:
            fehler[key] = f"{type(e).__name__}: {str(e)[:40]}"
    return (out or None), fehler


def _data():
    if time.time() - _CACHE["t"] < CACHE_TTL and (_CACHE["cg"] or _CACHE["yf"]):
        return _CACHE["cg"], _CACHE["yf"], _CACHE["fehler"]
    cg, cg_err = _fetch_coingecko()
    yfd, yf_err = _fetch_yfinance()
    fehler = dict(yf_err or {})
    if cg_err:
        fehler["CoinGecko"] = cg_err
    _CACHE["cg"], _CACHE["yf"], _CACHE["fehler"] = cg, yfd, fehler
    _CACHE["t"] = time.time()
    _write_snapshot(cg, yfd)
    return cg, yfd, fehler


# ----------------------------------------------------------------------
# Snapshot-Archiv
# ----------------------------------------------------------------------
def _write_snapshot(cg, yfd):
    """Ein Snapshot pro Tag - unvollstaendige Tage werden ERGAENZT.

    [AUDIT 06.08.2026] Vorher: "if today in hist: return". Ein Tag, an dem
    eine Quelle ausgefallen war, wurde damit dauerhaft zementiert. Belegt in
    geldfluss_history.json am 2026-08-05: dort fehlen total_t/btc_dom/eth_dom,
    weil CoinGecko offline war - nachgeholt wurde nie. Da diese Reihe die
    einzige Grundlage fuer "Dominanz 7d/30d" ist, entsteht daraus ein
    dauerhafter Rechenfehler. Jetzt wird ein vorhandener Tag beim naechsten
    Refresh ergaenzt, solange Pflichtfelder fehlen.
    """
    try:
        p = _hist_path()
        hist = {}
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                hist = json.load(f)
        heute = date.today().isoformat()
        alt = hist.get(heute) or {}
        if alt and all(k in alt for k in PFLICHTFELDER):
            return                      # vollstaendig - nichts nachzutragen
        snap = dict(alt)
        if cg:
            snap.update({"total_t": round(cg["total_t"], 3),
                         "btc_dom": round(cg["btc_dom"], 2),
                         "eth_dom": round(cg.get("eth_dom") or 0, 2)})
        if yfd:
            for k, dmap in yfd.items():
                s = _serie(dmap)
                if s:
                    snap[k.lower()] = round(s[-1][1], 2)
                    # [AUDIT] Beobachtungsdatum der Quelle mitschreiben. BTC ist
                    # 24/7, GC=F und ^GSPC nicht: am Montag 00:01 ist der letzte
                    # Close der von Freitag. Ohne dieses Feld sah es aus, als
                    # waere der Wert vom Tagesschluessel - belegt in der Datei:
                    # 2026-08-01/02/03 tragen alle spx 7489.72 (Freitags-Close).
                    snap[k.lower() + "_stand"] = s[-1][0]
        if len(snap) <= 1:
            return
        snap["ts"] = datetime.now().isoformat()[:16]          # Altformat, unveraendert
        snap["ts_utc"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
        snap["vollstaendig"] = all(k in snap for k in PFLICHTFELDER)
        hist[heute] = snap
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=1)
        with open(tmp, encoding="utf-8") as f:
            json.load(f)                                       # vor dem Ersetzen pruefen
        os.replace(tmp, p)
    except Exception:
        # Ein Schreibfehler darf den Tab nie crashen; der Zaehler unten zeigt,
        # wenn nichts ankommt.
        pass


def sammle_snapshot(force=False):
    """[AUDIT 06.08.2026] Oeffentlicher Einstieg fuer sammler.py.

    Holt beide Quellen und schreibt/ergaenzt den Tagesschnappschuss - ohne
    Tkinter, ohne Bot. Damit waechst das Archiv auch dann, wenn der Tab nie
    geoeffnet wird. Genau daran fehlte es bisher: gesammelt wurde nur,
    solange jemand hinsah.

    Rueckgabe: dict mit Status fuer die Konsolenausgabe.
    """
    if force:
        _CACHE["t"] = 0
    cg, yfd, fehler = _data()
    n, voll, herr = _hist_status()
    return {"coingecko": bool(cg), "yfinance": sorted(yfd) if yfd else [],
            "fehler": fehler, "tage": n, "vollstaendig": voll,
            "archiv_fehler": herr}


def _hist_status():
    """(anzahl_tage, anzahl_vollstaendig, fehlertext)."""
    try:
        with open(_hist_path(), encoding="utf-8") as f:
            hist = json.load(f)
        voll = sum(1 for v in hist.values()
                   if isinstance(v, dict) and all(k in v for k in PFLICHTFELDER))
        return len(hist), voll, ""
    except FileNotFoundError:
        return 0, 0, "noch nicht angelegt"
    except Exception as e:
        return 0, 0, f"{type(e).__name__}: {str(e)[:40]}"


def _dom_delta(days_back):
    """Dominanz-Aenderung aus eigener History.

    [AUDIT 06.08.2026] Gibt jetzt zusaetzlich den TATSAECHLICHEN Abstand
    zurueck. Vorher wurde still der naechstbeste aeltere Tag genommen -
    bei Luecken hiess "7d" in Wahrheit 9 oder 12 Tage, ohne Hinweis.
    Rueckgabe: (delta, ist_tage) oder (None, None).
    """
    try:
        with open(_hist_path(), encoding="utf-8") as f:
            hist = json.load(f)
        keys = sorted(k for k, v in hist.items()
                      if isinstance(v, dict) and v.get("btc_dom") is not None)
        if len(keys) < 2:
            return None, None
        cur = hist[keys[-1]]["btc_dom"]
        ziel = date.fromisoformat(keys[-1]).toordinal() - days_back
        past_key = None
        for k in keys[:-1]:
            if date.fromisoformat(k).toordinal() <= ziel:
                past_key = k
        if past_key is None:
            return None, None
        ist = date.fromisoformat(keys[-1]).toordinal() - date.fromisoformat(past_key).toordinal()
        return cur - hist[past_key]["btc_dom"], ist
    except Exception:
        return None, None


# ----------------------------------------------------------------------
# Reihen-Mathematik (datumsbewusst)
# ----------------------------------------------------------------------
def _serie(dmap):
    """dict{datum: wert} -> nach Datum sortierte Liste [(datum, wert)]."""
    return sorted(dmap.items()) if dmap else []


def _ret_kalender(dmap, tage):
    """Rendite ueber KALENDERtage statt ueber Datenpunkte.

    [AUDIT 06.08.2026] _ret(serie, 30) zaehlte vorher 30 Datenpunkte. Bei
    BTC-USD sind das 30 Kalendertage, bei GC=F/^GSPC rund 42 - die Spalten
    "30 Tage" und "90 Tage" verglichen also ungleiche Zeitraeume miteinander
    und rangierten die Assets danach. Jetzt: letzter Handelstag <=
    (letztes Datum - N Tage), mit Ausweis des tatsaechlichen Abstands.
    Rueckgabe: (rendite_pct, ist_tage) oder (None, None).
    """
    s = _serie(dmap)
    if len(s) < 2:
        return None, None
    end_ord = date.fromisoformat(s[-1][0]).toordinal()
    ziel = end_ord - tage
    kandidat = None
    for tag, wert in s[:-1]:
        if date.fromisoformat(tag).toordinal() <= ziel:
            kandidat = (tag, wert)
    if not kandidat or kandidat[1] <= 0:
        return None, None
    ist = end_ord - date.fromisoformat(kandidat[0]).toordinal()
    return (s[-1][1] / kandidat[1] - 1) * 100, ist


def _ratio_map(a, b):
    """Verhaeltnis zweier Reihen auf der GEMEINSAMEN Datumsmenge.

    [AUDIT 06.08.2026] Ersetzt zip(a[-91:], b[-91:]). Der alte Ausdruck
    paarte Listenpositionen, nicht Tage.
    """
    if not a or not b:
        return {}
    return {t: a[t] / b[t] for t in (set(a) & set(b)) if b.get(t)}


def _bar(val_t, max_t, width=30):
    n = max(1, int(val_t / max_t * width))
    return "#" * min(n, width)


# ----------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------
def render_geldfluss(engine=None):
    """Pure Render -> Liste (zeile, tag). Testbar (Cache injizierbar)."""
    L = []
    cg, yfd, fehler = _data()
    L.append((f"--- GELDFLUSS --- Intermarket-Deck --- {datetime.now().strftime('%H:%M')} ---\n", C_HDR))
    L.append(("    Kein Kapitalfluss: Anteile und relative Performance, keine Flows.\n\n", C_DIM))

    def row(label, value, vtag):
        L.append((f"| {label:<19}| ", C_LBL))
        L.append((f"{value}\n", vtag))

    # [0] Quellen-Status - [AUDIT] Ausfaelle sichtbar statt "offline"
    if fehler:
        L.append(("--- Quellen-Stoerungen ---\n", C_WRN))
        for quelle, grund in sorted(fehler.items()):
            L.append((f"  {quelle:<12} {grund}\n", C_NEG))
        L.append(("\n", C_DIM))

    # [1] Landkarte
    L.append(("--- Die Landkarte des Geldes ---\n", C_HDR))
    btc_t = (cg["total_t"] * cg["btc_dom"] / 100) if cg else None
    rows = [("Aktien global", REF_AKTIEN_T, C_TXT, f"statisch, {REF_STAND}"),
            ("Gold", REF_GOLD_T, C_WRN, f"statisch, {REF_STAND}"),
            ("Krypto gesamt", cg["total_t"] if cg else None, C_LBL, "live"),
            ("davon Bitcoin", btc_t, C_POS, "live")]
    for name, v, tag, herkunft in rows:
        if v is None:
            L.append((f"  {name:<14} {'?':>7}   (Quelle gestoert)\n", C_DIM))
        else:
            L.append((f"  {name:<14} {v:>6.1f}T  ", C_TXT))
            L.append((_bar(v, REF_AKTIEN_T), tag))
            L.append((f"  [{herkunft}]\n", C_DIM))
    if cg and btc_t:
        L.append((f"  Krypto = {cg['total_t']/REF_AKTIEN_T*100:.1f}% der Aktienwelt | "
                  f"BTC = {btc_t/REF_GOLD_T*100:.1f}% von Gold\n", C_DIM))
        L.append((f"  (Nenner sind Schaetzwerte von {REF_STAND} - die Prozente altern.)\n\n", C_DIM))
    else:
        L.append(("\n", C_DIM))

    # [2] Rotation
    L.append(("--- Rotation: Verschiebung der Anteile ---\n", C_HDR))
    L.append(("+--------------------+------------------------------+\n", C_DIM))
    if cg:
        row("BTC-Dominanz", f"{cg['btc_dom']:.2f}%  (ETH {cg.get('eth_dom') or 0:.1f}%)", C_TXT)
        for spanne in (7, 30):
            d, ist = _dom_delta(spanne)
            if d is None:
                row(f"Dominanz {spanne}d", "sammelt... (History waechst taeglich)", C_DIM)
                continue
            # [AUDIT] Tatsaechlichen Abstand ausweisen, wenn er abweicht.
            hinweis = "" if ist == spanne else f"  [tatsaechlich {ist}d]"
            pfeil = ("Anteil zu BTC" if d > 0.05 else
                     "Anteil zu Alts" if d < -0.05 else "neutral")
            row(f"Dominanz {spanne}d", f"{d:+.2f}%  ({pfeil}){hinweis}",
                C_POS if d > 0 else C_NEG if d < 0 else C_DIM)
    else:
        row("CoinGecko", "gestoert - naechster Versuch in 15 min", C_WRN)
    L.append(("+--------------------+------------------------------+\n\n", C_DIM))

    # [3] Asset-Rennen
    L.append(("--- Das Asset-Rennen (Performance ueber Kalendertage) ---\n", C_HDR))
    hdr = (f"| {'Asset':<8}| {'Kurs':>12} | {'Stand':>10} | {'Pkt':>4} | "
           f"{'30 Tage':>9} | {'90 Tage':>9} |\n")
    sep = "+" + "-" * (len(hdr) - 3) + "+\n"
    L.append((sep, C_DIM)); L.append((hdr, C_LBL)); L.append((sep, C_DIM))
    if yfd:
        for key, name in (("BTC", "BTC"), ("GOLD", "Gold"), ("SPX", "S&P500")):
            dmap = yfd.get(key)
            if not dmap:
                continue
            s = _serie(dmap)
            r30, i30 = _ret_kalender(dmap, 30)
            r90, i90 = _ret_kalender(dmap, 90)
            t30 = f"{r30:+8.1f}%" if r30 is not None else "      - "
            t90 = f"{r90:+8.1f}%" if r90 is not None else "      - "
            tag = C_POS if (r30 or 0) >= 0 else C_NEG
            L.append((f"| {name:<8}| {s[-1][1]:>12,.2f} | {s[-1][0]:>10} | {len(s):>4} | "
                      f"{t30} | {t90} |\n", tag))
        L.append((sep, C_DIM))
        L.append(("  'Stand' = letzter Handelstag der Quelle (UTC-normalisiert), 'Pkt' =\n"
                  "  gelieferte Datenpunkte in 120 Tagen. BTC handelt 24/7, Gold und S&P\n"
                  "  nur werktags. Renditen rechnen ueber Kalendertage, nicht ueber Punkte.\n",
                  C_DIM))
    else:
        L.append(("|  yfinance gestoert - naechster Versuch in 15 min\n", C_WRN))
        L.append((sep, C_DIM))
    try:
        dxy = (getattr(engine, "state", {}) or {}).get("dxy")
        if dxy:
            L.append((f"  DXY {dxy} (live vom Bot-Feed, nur Momentanwert)\n", C_DIM))
    except Exception:
        pass
    L.append(("\n", C_DIM))

    # [4] Ratios - auf gemeinsamer Datumsmenge
    if yfd and yfd.get("BTC") and yfd.get("GOLD"):
        L.append(("--- Ratios (Staerke-Vergleich, datumsgleich) ---\n", C_HDR))
        rmap = _ratio_map(yfd["BTC"], yfd["GOLD"])
        rs = _serie(rmap)
        if rs:
            r30, ist = _ret_kalender(rmap, 30)
            zusatz = (f"30d: {r30:+.1f}% -> "
                      f"{'BTC staerker' if r30 > 0 else 'Gold staerker'}"
                      if r30 is not None else "30d: zu wenig gemeinsame Tage")
            L.append((f"  BTC/Gold: {rs[-1][1]:.2f} Unzen pro BTC  ({zusatz})\n",
                      C_POS if (r30 or 0) > 0 else C_NEG))
            L.append((f"    Basis: {len(rmap)} gemeinsame Handelstage, Stand {rs[-1][0]}\n", C_DIM))
        if yfd.get("SPX"):
            smap = _ratio_map(yfd["BTC"], yfd["SPX"])
            ss = _serie(smap)
            if ss:
                rs30, _ = _ret_kalender(smap, 30)
                txt = f"{rs30:+.1f}%" if rs30 is not None else "-"
                L.append((f"  BTC/S&P : {ss[-1][1]:.2f}  (30d: {txt})\n",
                          C_POS if (rs30 or 0) > 0 else C_NEG))
        L.append(("\n", C_DIM))

    # [5] Archiv-Status
    n, voll, herr = _hist_status()
    if herr:
        L.append((f"  Snapshot-Archiv: {herr}\n", C_WRN))
    else:
        tag = C_POS if voll == n else C_WRN
        L.append((f"  Snapshot-Archiv: {n} Tage, davon {voll} vollstaendig "
                  f"(alle {len(PFLICHTFELDER)} Felder)\n", tag))
        if voll < n:
            L.append((f"  {n - voll} Tag(e) unvollstaendig - werden beim naechsten\n"
                      "  Refresh nachgetragen, solange es derselbe Kalendertag ist.\n", C_DIM))
    L.append(("\n", C_DIM))

    L.append(("  Ehrlichkeit: Beobachtungsdeck, keine Handels-Signale.\n", C_WRN))
    L.append(("  Anteilsverschiebung ist kein gemessener Kapitalfluss.\n", C_WRN))
    L.append(("  Bot-Integration nur als spaetere, vorregistrierte Epoche\n", C_DIM))
    L.append(("  mit Beweis (macro_replay-Lektion).\n", C_DIM))
    return L


def build_geldfluss_tab(parent, engine=None):
    import tkinter as tk
    sb = tk.Scrollbar(parent)
    sb.pack(side="right", fill="y")
    txt = tk.Text(parent, bg="#000000", fg="#d0d0d0", insertbackground="#00ff88",
                  font=("Consolas", 11), relief="flat", wrap="none", cursor="arrow",
                  yscrollcommand=sb.set)
    txt.pack(fill="both", expand=True, padx=4, pady=4)
    sb.config(command=txt.yview)
    for tag, col in [(C_HDR, "#00ff88"), (C_LBL, "#00c8ff"), (C_POS, "#00ff88"),
                     (C_NEG, "#ff4655"), (C_MAG, "#ff66ff"), (C_DIM, "#666666"),
                     (C_TXT, "#e8e8e8"), (C_WRN, "#ffb020")]:
        txt.tag_configure(tag, foreground=col)

    def _render():
        try:
            lines = render_geldfluss(engine)
            _view = txt.yview()
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            for line, tag in lines:
                txt.insert("end", line, tag)
            txt.configure(state="disabled")
            txt.yview_moveto(_view[0])
        except Exception as e:
            # [AUDIT 06.08.2026] Vorher "pass" - bei dauerhaftem Fehler blieb
            # das letzte Bild stehen und sah weiter aktuell aus.
            try:
                txt.configure(state="normal")
                txt.delete("1.0", "end")
                txt.insert("end", "--- GELDFLUSS: Anzeige gestoert ---\n\n", C_NEG)
                txt.insert("end", f"  {type(e).__name__}: {str(e)[:120]}\n", C_WRN)
                txt.configure(state="disabled")
            except Exception:
                pass
        finally:
            try:
                txt.after(REFRESH_MS, _render)
            except Exception:
                pass

    _render()
