# -*- coding: utf-8 -*-
"""
ZYKLUS-Tab: Der Bitcoin-Zyklus-Atlas. [ZYKLUS-TAB 19.07.2026]
Liest data_store/situation_history.json (3.045 Tage BTC + F&G,
vom history_harvester erzeugt) und zeigt: Wo stehen wir heute,
was geschah historisch bei diesem Angst-Level, die grossen Phasen,
Extreme und den 8-Jahres-Zeitstrahl. REINE ANZEIGE - kein Einfluss
auf Trading. Ehrlichkeits-Regel eingebaut: Historie != Prognose
(macro_replay-Lektion: naives Muster-Matching hatte keinen Edge).
"""
import os, json, math
from datetime import datetime, date

# [AUDIT 06.08.2026] Ab wie vielen Tagen Abstand zum letzten Datensatz die
# Anzeige als veraltet gilt. situation_history.json wird von history_harvester.py
# erzeugt - einem manuellen Skript ohne Scheduler. Am 06.08.2026 war die Datei
# 32 Tage alt und wurde trotzdem als "heute" gerendert.
STALE_WARN_TAGE = 2
FWD_HORIZONT = 90        # Tage Vorlauf des Outcomes fwd_90d -> Ueberlappungsfaktor

C_HDR, C_LBL, C_POS, C_NEG, C_MAG, C_DIM, C_TXT, C_WRN = \
    "hdr", "lbl", "pos", "neg", "mag", "dim", "txt", "wrn"

_CACHE = {"mtime": 0, "data": None, "fehler": ""}

BUCKETS = [(0, 10, "Extreme Panik  0-10"), (10, 20, "Starke Angst  10-20"),
           (20, 30, "Angst         20-30"), (30, 45, "Unruhe        30-45"),
           (45, 55, "Neutral       45-55"), (55, 75, "Gier          55-75"),
           (75, 101, "Extreme Gier    75+")]


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    p = os.path.join(_root(), "data_store", "situation_history.json")
    try:
        m = os.path.getmtime(p)
        if _CACHE["data"] is not None and _CACHE["mtime"] == m:
            return _CACHE["data"]
        d = json.load(open(p, encoding="utf-8"))
        _CACHE["mtime"], _CACHE["data"] = m, d
        _CACHE["fehler"] = ""
        return d
    except Exception as e:
        # [AUDIT 06.08.2026] Vorher stumm None. Fehlende Datei und kaputtes
        # JSON sahen im UI identisch aus.
        _CACHE["fehler"] = f"{type(e).__name__}: {str(e)[:70]}"
        return None


def _med(x):
    s = sorted(x)
    n = len(s)
    if n == 0:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _alter_tage(letztes_datum):
    """[AUDIT 06.08.2026] Abstand des letzten Datensatzes zu heute, oder None."""
    try:
        return (date.today() - date.fromisoformat(str(letztes_datum)[:10])).days
    except Exception:
        return None


def _n_eff(n_tage, horizont=FWD_HORIZONT):
    """[AUDIT 06.08.2026] Effektive Stichprobe bei ueberlappenden Fenstern.

    Die Zeilen sind Kalendertage, das Outcome ist der Ertrag der FOLGENDEN
    90 Tage. Zwei aufeinanderfolgende Zeilen teilen sich 89 von 90 Tagen
    Zukunft - sie sind fast dieselbe Beobachtung. Aus 412 Tagen werden so
    rund 4-5 unabhaengige Episoden. Ohne diese Zahl liest sich die Tabelle
    wie eine grosse Stichprobe, die sie nicht ist.
    """
    try:
        return max(1.0, float(n_tage) / float(horizont))
    except Exception:
        return 1.0


def _wilson(treffer_pct, n_eff, z=1.96):
    """95%-Konfidenzintervall der Trefferquote (Wilson) auf n_eff."""
    try:
        n = float(n_eff)
        if n <= 0:
            return None
        p = max(0.0, min(1.0, float(treffer_pct) / 100.0))
        nenner = 1.0 + z * z / n
        mitte = (p + z * z / (2 * n)) / nenner
        halb = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / nenner
        return (max(0.0, (mitte - halb) * 100.0), min(100.0, (mitte + halb) * 100.0))
    except Exception:
        return None


def _spark(vals, width=58):
    if len(vals) < 2:
        return ""
    step = max(1, len(vals) // width)
    v = [vals[i] for i in range(0, len(vals), step)][:width]
    lo, hi = min(v), max(v)
    if hi - lo < 1e-9:
        return "-" * len(v)
    blocks = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    return "".join(blocks[int((x - lo) / (hi - lo) * 7)] for x in v)


def render_atlas():
    """Pure Render-Funktion -> Liste (zeile, farbtag). Ohne GUI testbar."""
    L = []
    d = _load()
    if not d or not d.get("days"):
        L.append(("  situation_history.json nicht lesbar.\n", C_WRN))
        if _CACHE.get("fehler"):
            L.append((f"  Grund: {_CACHE['fehler']}\n", C_NEG))
        L.append(("  Erzeugen mit: python history_harvester.py\n", C_DIM))
        L.append(("  oder:         python sammler.py --nur zyklus\n", C_DIM))
        return L
    days = d["days"]
    fg_days = [x for x in days if x["features"].get("fear_greed") is not None]

    L.append((f"--- ZYKLUS-ATLAS --- {d.get('count', len(days))} Tage Bitcoin "
              f"({days[0]['date'][:7]} bis {days[-1]['date'][:7]}) ---\n", C_HDR))
    L.append((f"    Datenstand: {days[-1]['date']}  |  Quelle: {d.get('source','?')}"
              f"  |  Labels: {d.get('label_version','?')}\n", C_DIM))

    # [AUDIT 06.08.2026] Frischepruefung. Vorher wurde die letzte Zeile der
    # Datei ohne jede Pruefung als "heute" gerendert - am 06.08.2026 war das
    # ein 32 Tage alter Stand (BTC 62.464$, F&G 22), waehrend der TERMINAL-Tab
    # zeitgleich F&G 27 aus der Live-Quelle zeigte. Zwei Tabs, zwei "heute".
    alter = _alter_tage(days[-1]["date"])
    veraltet = alter is not None and alter > STALE_WARN_TAGE
    if veraltet:
        L.append(("\n" + "!" * 66 + "\n", C_NEG))
        L.append((f"  DATENSTAND IST {alter} TAGE ALT - das ist NICHT die heutige Lage.\n", C_NEG))
        L.append(("  Alle Zahlen unten beziehen sich auf den "
                  f"{days[-1]['date']}.\n", C_WRN))
        L.append(("  Auffrischen:  python history_harvester.py\n", C_TXT))
        L.append(("  (oder python sammler.py --nur zyklus)\n", C_DIM))
        L.append(("!" * 66 + "\n\n", C_NEG))
    elif alter is not None:
        L.append((f"    Aktualitaet: {alter} Tag(e) alt - ok\n\n", C_POS))
    else:
        L.append(("\n", C_DIM))
    _heute_marker = " <- letzter Datenstand" if veraltet else " <- heute"

    def row(label, value, vtag):
        L.append((f"| {label:<19}| ", C_LBL))
        L.append((f"{value}\n", vtag))

    # --- Heute ---
    t = days[-1]
    f = t["features"]
    cur_fg = f.get("fear_greed")
    fg_sorted = sorted(x["features"]["fear_greed"] for x in fg_days)
    pct = (sum(1 for v in fg_sorted if v < cur_fg) / len(fg_sorted) * 100) if cur_fg is not None else None
    L.append((f"--- Wo stehen wir? (Stand {days[-1]['date']}) ---\n", C_HDR))
    L.append(("+--------------------+--------------------------------+\n", C_DIM))
    row("BTC / Phase", f"{t['close']:,.0f} $  |  {t['phase']}", C_TXT)
    if cur_fg is not None:
        row("Fear & Greed", f"{cur_fg}  (nur {pct:.0f}% aller Tage waren aengstlicher)",
            C_NEG if cur_fg < 45 else C_POS if cur_fg > 55 else C_TXT)
    row("Drawdown vom ATH", f"{f.get('drawdown_ath', 0):+.1f}%",
        C_NEG if f.get('drawdown_ath', 0) < -20 else C_TXT)
    row("Mayer / RSI", f"{f.get('mayer', '?')}  /  {f.get('rsi', '?')}", C_TXT)
    for lo, hi, label in BUCKETS:
        if cur_fg is not None and lo <= cur_fg < hi:
            sel = [x["outcome"]["fwd_90d"] for x in fg_days
                   if lo <= x["features"]["fear_greed"] < hi
                   and x["outcome"].get("fwd_90d") is not None]
            if sel:
                hit = sum(1 for v in sel if v > 0) / len(sel) * 100
                m = _med(sel)
                ne = _n_eff(len(sel))
                ki = _wilson(hit, ne)
                ki_txt = f", 95%-KI {ki[0]:.0f}-{ki[1]:.0f}%" if ki else ""
                row("Dieser F&G-Bereich",
                    f"historisch +90d: {m:+.1f}% Median, {hit:.0f}% Treffer"
                    f"  (n_eff {ne:.1f}{ki_txt})",
                    C_POS if m > 0 else C_NEG)
    L.append(("+--------------------+--------------------------------+\n\n", C_DIM))

    # --- F&G-Tabelle ---
    L.append(("--- Was geschah historisch nach Angst/Gier? ---\n", C_HDR))
    hdr = (f"| {'F&G-Bereich':<20}| {'Tage':>5} | {'n_eff':>6} | {'+30d':>7} | "
           f"{'+90d':>7} | {'90d>0':>6} | {'95%-Intervall':>14} |\n")
    sep = "+" + "-" * (len(hdr) - 3) + "+\n"
    L.append((sep, C_DIM))
    L.append((hdr, C_LBL))
    L.append((sep, C_DIM))
    for lo, hi, label in BUCKETS:
        sel = [x for x in fg_days if lo <= x["features"]["fear_greed"] < hi
               and x["outcome"].get("fwd_90d") is not None]
        if not sel:
            continue
        f30 = [x["outcome"]["fwd_30d"] for x in sel if x["outcome"].get("fwd_30d") is not None]
        f90 = [x["outcome"]["fwd_90d"] for x in sel]
        hit = sum(1 for v in f90 if v > 0) / len(f90) * 100
        m90 = _med(f90)
        mark = _heute_marker if (cur_fg is not None and lo <= cur_fg < hi) else ""
        # [AUDIT 06.08.2026] n_eff + Wilson-Intervall. Zeilen mit n_eff < 10
        # werden grau gesetzt: dort ist die Trefferquote nicht von Zufall zu
        # unterscheiden, egal wie gross die Spalte "Tage" aussieht.
        ne = _n_eff(len(sel))
        ki = _wilson(hit, ne)
        ki_txt = f"{ki[0]:.0f}-{ki[1]:.0f}%" if ki else "-"
        tag = C_DIM if ne < 10 else (C_POS if m90 > 0 else C_NEG)
        L.append((f"| {label:<20}| {len(sel):>5} | {ne:>6.1f} | {_med(f30):>+6.1f}% | "
                  f"{m90:>+6.1f}% | {hit:>5.0f}% | {ki_txt:>14} |{mark}\n", tag))
    L.append((sep, C_DIM))
    L.append(("  n_eff = Tage / 90, weil sich benachbarte Tage 89 von 90 Zukunftstagen\n"
              "  teilen. Aus 412 Tagen werden so ~4,6 unabhaengige Episoden. Graue\n"
              "  Zeilen (n_eff < 10) sind statistisch nicht belastbar - das 95%-Intervall\n"
              "  zeigt, wie breit die Unsicherheit tatsaechlich ist.\n\n", C_DIM))

    # --- Phasen ---
    L.append(("--- Die grossen Phasen (Median-Rendite +90 Tage) ---\n", C_HDR))
    ph = {}
    for x in days:
        o = x.get("outcome", {}).get("fwd_90d")
        if o is not None:
            ph.setdefault(x["phase"], []).append(o)
    for p, v in sorted(ph.items(), key=lambda kv: -_med(kv[1])):
        m = _med(v)
        bar = "#" * min(24, max(1, int(abs(m) * 1.1)))
        L.append((f"  {p:<14} {len(v):>4}d  {m:>+6.1f}%  ", C_TXT))
        L.append((bar + "\n", C_POS if m > 0 else C_NEG))
    L.append(("\n", C_DIM))

    # --- Extreme ---
    L.append(("--- Die extremsten Momente ---\n", C_HDR))
    worst = sorted(fg_days, key=lambda x: x["features"]["fear_greed"])[:2]
    for x in worst:
        o = x["outcome"].get("fwd_90d")
        L.append((f"  Panik F&G {x['features']['fear_greed']:>2}  {x['date']}  "
                  f"BTC {x['close']:>9,.0f}$  -> 90d: {o:+.1f}%\n",
                  C_POS if (o or 0) > 0 else C_NEG))
    best = max(fg_days, key=lambda x: x["features"]["fear_greed"])
    o = best["outcome"].get("fwd_90d")
    L.append((f"  Gier  F&G {best['features']['fear_greed']:>2}  {best['date']}  "
              f"BTC {best['close']:>9,.0f}$  -> 90d: {o:+.1f}%\n",
              C_POS if (o or 0) > 0 else C_NEG))
    dd = min(days, key=lambda x: x["features"]["drawdown_ath"])
    L.append((f"  Tiefster Drawdown: {dd['features']['drawdown_ath']:.1f}% am {dd['date']} "
              f"(BTC {dd['close']:,.0f}$)\n\n", C_MAG))

    # --- Zeitstrahl ---
    closes = [x["close"] for x in days]
    L.append(("--- 8 Jahre in einer Zeile ---\n", C_HDR))
    L.append(("  " + _spark(closes) + "\n", C_TXT))
    L.append((f"  {days[0]['date'][:7]}  (Tief {min(closes):,.0f}$ / "
              f"Hoch {max(closes):,.0f}$)  {days[-1]['date'][:7]}\n\n", C_DIM))

    L.append(("  Ehrlichkeit: Historie ist KEINE Prognose. Naives Zyklus-\n", C_WRN))
    L.append(("  Muster-Matching wurde via macro_replay getestet: kein Edge.\n", C_WRN))
    L.append(("  Diese Statistiken sind Landkarte, nicht Navi.\n", C_DIM))
    # [AUDIT 06.08.2026] Zweite Ehrlichkeitsschicht: die Grenzen der Stichprobe.
    L.append((f"  Grenzen: Daten ab {days[0]['date']} (F&G startet Feb 2018), also\n", C_DIM))
    L.append(("  nur ZWEI vollstaendige Halving-Zyklen. Fuer Zyklusaussagen ist die\n", C_DIM))
    L.append(("  Stichprobe n=2 - unabhaengig davon, wie viele Tage in der Tabelle\n", C_DIM))
    L.append(("  stehen. Die Phasen-Labels sind eine Heuristik mit nicht-disjunkten\n", C_DIM))
    L.append(("  Regeln; die Reihenfolge der Pruefung entscheidet die Klasse.\n", C_DIM))
    return L


def build_zyklus_tab(parent, engine=None):
    """Baut den Tab. engine wird nicht benoetigt (reine Datei-Anzeige)."""
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
            lines = render_atlas()
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            for line, tag in lines:
                txt.insert("end", line, tag)
            txt.configure(state="disabled")
        except Exception:
            pass
        finally:
            try:
                txt.after(3600 * 1000, _render)  # 1x pro Stunde reicht (Tagesdaten)
            except Exception:
                pass

    _render()
