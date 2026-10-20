"""
================================================================
  EDELMETALL-TAB (CustomTkinter)
================================================================
Baut den Inhalt des METALLE-Tabs: Karten + Charts + Performance.
Komplett isoliert - importiert nur die eigene Engine.

Wird vom Haupt-UI per build_metals_tab(parent_frame) aufgerufen,
gewrappt in try/except, damit ein Fehler hier den Bot nie crasht.
================================================================
"""
import threading
import queue

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import customtkinter as ctk

# Engine importieren (robust - egal von wo gestartet)
try:
    from metals.metals_engine import (analyze_metal, analyze_all, track_signals,
                                       get_stats, export_csv, METALLE)
except Exception:
    from metals_engine import (analyze_metal, analyze_all, track_signals,
                               get_stats, export_csv, METALLE)

# STUFE-1: Persistenz/Sammel-Modul (mit Fallback-Stubs, nie crashen)
#
# [WIEDERHERGESTELLT 12.08.2026] Dieser Block wurde am 06.08. um 04:34 von
# update_metals_indikatoren.py mit ueberschrieben - das Skript ersetzt Dateien,
# statt sie zu patchen (GEFUNDENE-PROBLEME.md, Punkt 25). Ohne ihn zeigte der
# Reiter nach jedem Neustart einen leeren Stand, und kein Scan wurde
# mitgeschrieben.
try:
    from metals.metals_store import save_state, load_state, log_scan
except Exception:
    try:
        from metals_store import save_state, load_state, log_scan
    except Exception:
        def save_state(*a, **k): return False
        def load_state(*a, **k): return None
        def log_scan(*a, **k): return False


# Farben (aus dem Haupt-UI uebernommen, damit's konsistent aussieht)
CLR_BG = "#0e0e10"
CLR_CARD = "#141417"
CLR_BORDER = "#2a2a30"
CLR_ACCENT = "#f1c40f"
CLR_GREEN = "#00ff88"
CLR_RED = "#ff4655"
CLR_CYAN = "#00d4ff"
CLR_ORANGE = "#ff9500"
CLR_MUTED = "#666"


def _wilson(treffer, n, z=1.96):
    """[AUDIT 06.08.2026] 95%-Konfidenzintervall der Trefferquote in Prozent.

    Wilson-Score, weil er bei kleinen n und bei 0%/100% nicht zusammenbricht
    (die Normalapproximation liefert dort das unsinnige Intervall [0,0]).
    """
    import math
    try:
        n = float(n)
        if n <= 0:
            return 0.0, 100.0
        p = max(0.0, min(1.0, float(treffer) / n))
        nenner = 1.0 + z * z / n
        mitte = (p + z * z / (2 * n)) / nenner
        halb = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / nenner
        return max(0.0, (mitte - halb) * 100.0), min(100.0, (mitte + halb) * 100.0)
    except Exception:
        return 0.0, 100.0


def build_metals_tab(parent):
    """Baut den kompletten Edelmetall-Tab in das parent-Frame."""
    widgets = {}

    # [LESBARKEIT 19.08.2026] Der Reiter hatte feste Hoehe: was unten nicht
    # mehr hinpasste (die Indikator-Gruende), wurde abgeschnitten - Sven:
    # "man kann auch die gruende unten nicht lesen weil alles reingequetscht
    # wurde". Ursache war nicht die Schriftgroesse, sondern dass der Inhalt
    # hoeher ist als das Fenster und es keine Rollleiste gab.
    # Der Rollrahmen ist reine Anzeige - er beruehrt weder Engine noch
    # Aufzeichnung. Faellt er aus, wird wie vorher direkt in parent gebaut.
    try:
        _roll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        _roll.pack(fill="both", expand=True)
        parent = _roll
    except Exception as _roll_err:
        print(f"[METALLE] Rollrahmen nicht verfuegbar: {_roll_err}")

    # --- Kopfzeile ---
    head = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=10)
    head.pack(fill="x", padx=8, pady=(6, 4))
    # [AUDIT 06.08.2026] Instrument benennen. Vorher stand hier nur
    # "Gold & Silber" - gehandelt/ausgewertet werden aber COMEX-Front-Month-
    # FUTURES (GC=F / SI=F) via yfinance, nicht Spot und nicht ETF. Der
    # Unterschied ist nicht kosmetisch: Futures haben Rollstichtage, eine
    # Kontraktgroesse (1 GC = 100 oz) und eine eigene Handelszeit.
    ctk.CTkLabel(head, text="🥇 EDELMETALLE  ·  Gold & Silber (COMEX-Futures GC=F / SI=F)",
                 font=("Bahnschrift", 16, "bold"),
                 text_color=CLR_ACCENT).pack(side="left", padx=12, pady=8)
    widgets["status"] = ctk.CTkLabel(head, text="lade Daten...",
                                     font=("Arial", 11), text_color=CLR_MUTED)
    widgets["status"].pack(side="left", padx=10)
    widgets["btn"] = ctk.CTkButton(head, text="🔄 Aktualisieren", width=130,
                                   fg_color=CLR_ACCENT, text_color="#000",
                                   hover_color="#d4a017",
                                   command=lambda: _refresh(parent, widgets))
    widgets["btn"].pack(side="right", padx=12, pady=6)

    # --- Gold-Silber-Ratio (global) ---
    widgets["ratio"] = ctk.CTkLabel(parent, text="", font=("Arial", 12, "bold"),
                                    text_color=CLR_CYAN)
    widgets["ratio"].pack(anchor="w", padx=16, pady=(2, 0))

    # --- Karten (Gold + Silber nebeneinander) ---
    cards = ctk.CTkFrame(parent, fg_color="transparent")
    cards.pack(fill="x", padx=8, pady=4)
    widgets["cards"] = {}
    for name in METALLE:
        card = ctk.CTkFrame(cards, fg_color=CLR_CARD, corner_radius=12,
                            border_width=1, border_color=CLR_BORDER)
        card.pack(side="left", expand=True, fill="both", padx=4, pady=2)
        c = {}
        ctk.CTkLabel(card, text=name, font=("Bahnschrift", 15, "bold"),
                     text_color="#fff").pack(anchor="w", padx=14, pady=(10, 0))
        c["price"] = ctk.CTkLabel(card, text="–", font=("Arial", 24, "bold"),
                                  text_color=CLR_ACCENT)
        c["price"].pack(anchor="w", padx=14)
        c["meta"] = ctk.CTkLabel(card, text="", font=("Arial", 11),
                                 text_color=CLR_MUTED, justify="left")
        c["meta"].pack(anchor="w", padx=14, pady=(0, 4))
        c["signal"] = ctk.CTkLabel(card, text="", font=("Arial", 14, "bold"),
                                   text_color=CLR_GREEN)
        c["signal"].pack(anchor="w", padx=14)
        c["levels"] = ctk.CTkLabel(card, text="", font=("Consolas", 12),
                                   text_color="#ddd", justify="left")
        c["levels"].pack(anchor="w", padx=14, pady=(2, 4))
        # [LESBARKEIT 19.08.2026] 10 -> 12 und #888 -> #b8b8c0. Das sind die
        # "Gruende", nach denen Sven ausdruecklich gefragt hat - sie waren die
        # kleinste und dunkelste Schrift im ganzen Reiter.
        c["votes"] = ctk.CTkLabel(card, text="", font=("Consolas", 12),
                                  text_color="#b8b8c0", justify="left")
        c["votes"].pack(anchor="w", padx=14, pady=(0, 10))
        widgets["cards"][name] = c

    # --- Charts (Gold + Silber nebeneinander) ---
    # [19.08.2026] expand=True gab den Charts allen uebrigen Platz - im
    # Rollrahmen waere das eine leere Flaeche, waehrend unten Text fehlt.
    charts = ctk.CTkFrame(parent, fg_color="transparent")
    charts.pack(fill="x", padx=8, pady=4)
    widgets["charts"] = {}
    for name in METALLE:
        cframe = ctk.CTkFrame(charts, fg_color=CLR_CARD, corner_radius=12)
        cframe.pack(side="left", expand=True, fill="both", padx=4)
        fig, ax = plt.subplots(figsize=(4.2, 2.4), dpi=80)
        fig.patch.set_facecolor(CLR_CARD)
        ax.set_facecolor("#0d0d0f")
        canvas = FigureCanvasTkAgg(fig, master=cframe)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
        widgets["charts"][name] = {"fig": fig, "ax": ax, "canvas": canvas}

    # --- Performance-Bereich ---
    perf = ctk.CTkFrame(parent, fg_color=CLR_CARD, corner_radius=12)
    perf.pack(fill="x", padx=8, pady=(4, 8))
    # [AUDIT 06.08.2026] "wie gut die Signale waren" behauptete ein Urteil,
    # das die Stichprobe nicht hergibt (am 06.08.2026: 5 geschlossene
    # Signale). Der Titel sagt jetzt, was es ist: eine laufende Aufzeichnung.
    ctk.CTkLabel(perf, text="📊 SIGNAL-AUFZEICHNUNG (Mitschrift, noch kein Urteil)",
                 font=("Bahnschrift", 13, "bold"),
                 text_color=CLR_CYAN).pack(anchor="w", padx=14, pady=(8, 2))
    widgets["perf_summary"] = ctk.CTkLabel(perf, text="–", font=("Arial", 12),
                                           text_color="#fff")
    widgets["perf_summary"].pack(anchor="w", padx=14)
    # [LESBARKEIT 19.08.2026] Sven: "man kann auch die gruende unten nicht
    # lesen weil alles reingequetscht wurde". Schrift 10 -> 12, mehr
    # Innenabstand, und die Liste bekommt Platz nach unten (fill/expand).
    # Der Reiter ist reines Beobachtungsdeck - wenn man ihn nicht lesen kann,
    # erfuellt er seinen einzigen Zweck nicht.
    widgets["perf_list"] = ctk.CTkLabel(perf, text="", font=("Consolas", 12),
                                        text_color="#ccc", justify="left")
    widgets["perf_list"].pack(anchor="w", padx=14, pady=(6, 14), fill="x")

    # Queue fuer Thread -> Main-Thread (thread-safe Datenuebergabe)
    widgets["queue"] = queue.Queue()

    # Referenzen halten (gegen Garbage Collection)
    parent._metals_widgets = widgets

    # Polling im Main-Thread starten - NUR der Main-Thread fasst Tkinter an
    parent.after(300, lambda: _poll(parent, widgets))
    # STUFE-1: zuerst letzten gespeicherten Stand zeigen (springt nicht mehr
    # beim Neustart).
    # [WIEDERHERGESTELLT 12.08.2026] Ging am 06.08. beim Ueberschreiben
    # verloren, siehe Punkt 25. Ohne diesen Block stand der Reiter nach jedem
    # Start leer da, bis der erste Scan durch war.
    _saved = None
    try:
        _saved = load_state()
    except Exception:
        _saved = None
    if _saved and _saved.get("analyses"):
        _fallback_stats = {"closed": 0, "open": 0, "win_rate": 0, "wins": 0,
                           "losses": 0, "total_pnl_pct": 0,
                           "closed_signals": [], "open_signals": []}
        try:
            _render(parent, widgets, _saved["analyses"],
                    _saved.get("stats") or _fallback_stats, _saved.get("gs_ratio"))
            widgets["status"].configure(
                text="gespeicherter Stand - 'Aktualisieren' fuer live",
                text_color=CLR_MUTED)
        except Exception:
            _refresh(parent, widgets)
    else:
        # Erste Ladung (startet nur den Hintergrund-Thread, der in die Queue schreibt)
        _refresh(parent, widgets)
    return widgets


def _refresh(parent, widgets):
    """Laedt Daten im Hintergrund (kein UI-Freeze) und rendert dann."""
    try:
        widgets["status"].configure(text="lade Daten...", text_color=CLR_MUTED)
        widgets["btn"].configure(state="disabled")
    except Exception:
        pass

    def _work():
        # WICHTIG: dieser Thread fasst KEIN Tkinter an - nur die Queue!
        try:
            analyses, gs_ratio = analyze_all()
            journal, neu = track_signals(analyses)
            export_csv(journal)
            stats = get_stats(journal)
            # STUFE-1: Stand speichern + Scan in metals_data/ loggen
            # [WIEDERHERGESTELLT 12.08.2026] Ging am 06.08. verloren (Punkt 25).
            # Ohne diese Zeilen wurde KEIN Scan mitgeschrieben - die Reihe in
            # metals_data/ waere seither nicht gewachsen.
            try:
                save_state(analyses, gs_ratio, stats)
                log_scan(analyses, gs_ratio)
            except Exception:
                pass
            widgets["queue"].put(("ok", analyses, stats, gs_ratio))
        except Exception as e:
            widgets["queue"].put(("err", str(e), None, None))

    threading.Thread(target=_work, daemon=True).start()


def _poll(parent, widgets):
    """Laeuft im Main-Thread (via after), liest Ergebnisse aus der Queue."""
    try:
        while True:
            kind, a, b, c = widgets["queue"].get_nowait()
            if kind == "ok":
                _render(parent, widgets, a, b, c)
            else:
                _show_error(widgets, a)
    except queue.Empty:
        pass
    except Exception:
        pass
    # immer weiter pollen (alle 500ms) - bleibt im Main-Thread
    try:
        parent.after(500, lambda: _poll(parent, widgets))
    except Exception:
        pass


def _show_error(widgets, msg):
    try:
        widgets["status"].configure(text=f"Fehler: {msg[:50]}", text_color=CLR_RED)
        widgets["btn"].configure(state="normal")
    except Exception:
        pass


def _render(parent, widgets, analyses, stats, gs_ratio=None):
    """Schreibt Analysen + Charts + Performance ins UI (Main-Thread)."""
    import datetime
    try:
        # Gold-Silber-Ratio (global)
        if gs_ratio:
            if gs_ratio > 80:
                rtxt = " (hoch -> Silber relativ guenstig)"
            elif gs_ratio < 50:
                rtxt = " (niedrig -> Gold relativ guenstig)"
            else:
                rtxt = " (neutral)"
            widgets["ratio"].configure(
                text=f"⚖  Gold-Silber-Ratio: {gs_ratio:.1f}{rtxt}")
        for a in analyses:
            name = a.get("name")
            c = widgets["cards"].get(name)
            if not c:
                continue
            if a.get("error"):
                c["price"].configure(text="Fehler")
                c["meta"].configure(text=str(a["error"]))
                c["signal"].configure(text="")
                c["levels"].configure(text="")
                c["votes"].configure(text="")
                continue

            c["price"].configure(text=f"{a['price']:,.2f} $")
            c["meta"].configure(
                text=f"Trend: {a['trend']}   RSI: {a['rsi']:.0f}   "
                     f"S {a['support']:,.0f}  /  W {a['resistance']:,.0f}")

            # STUFE-3: Richtung anzeigen (LONG gruen, SHORT rot)
            # [WIEDERHERGESTELLT 12.08.2026] Ging am 06.08. verloren (Punkt 25).
            # Ohne den Block stand bei einem SHORT-Signal derselbe gruene Pfeil
            # wie bei einem Kauf - die Richtung war nicht ablesbar.
            _dir = a.get("direction")
            if _dir == "SHORT":
                sig_color = CLR_RED
                _arrow = "▼ SHORT  "
            elif _dir == "LONG":
                sig_color = CLR_GREEN
                _arrow = "▲ LONG  "
            else:
                sig_color = CLR_ORANGE if "WARTEN" in a["signal"] else CLR_CYAN
                _arrow = ""
            c["signal"].configure(
                text=f"{_arrow}{a['signal']}  (Score {a.get('score', '?')})",
                text_color=sig_color)

            # Indikator-Aufschluesselung
            votes = a.get("votes", [])
            if votes:
                vtxt = "\n".join(f"  {ind:<10} {pts:+d}  {txt}"
                                 for ind, pts, txt in votes)
                c["votes"].configure(text=vtxt)
            else:
                c["votes"].configure(text="")

            # [KLARSTELLUNG 19.08.2026] Sven: "wenn ich es selbst aktualisiere
            # dann nimmt er einen komplett neuen einstieg (neue position)".
            #
            # Das tat er nie. metals_engine.track_signals() legt nur dann ein
            # neues Signal an, wenn fuer dieses Metall KEINES offen ist
            # ("has_open" -> continue). Der obere Block zeigte aber
            # a['entry'] - und das ist der AKTUELLE Kurs als hypothetische
            # Empfehlung, nicht die laufende Aufzeichnung. Zwei verschiedene
            # Dinge, gleich dargestellt.
            #
            # Jetzt steht dabei, ob bereits eine Aufzeichnung laeuft - mit
            # ihrem echten Einstieg und dem laufenden Stand.
            _offen = None
            for _s in (stats.get("open_signals") or []):
                if _s.get("name") == name:
                    _offen = _s
                    break

            if _offen:
                _ein = float(_offen.get("entry_price") or 0)
                _ri = _offen.get("direction", "LONG")
                _stand = ""
                try:
                    _k = float(a.get("price") or 0)
                    if _k > 0 and _ein > 0:
                        _p = ((_ein - _k) / _ein * 100) if _ri == "SHORT" \
                            else (_k / _ein - 1) * 100
                        _stand = f"  ->  laeuft {_p:+.2f} %"
                except (TypeError, ValueError):
                    pass
                _txt = (f"AUFZEICHNUNG LAEUFT ({_ri}) seit {_offen.get('entry_date','?')}\n"
                        f"  Einstieg  {_ein:,.2f} ${_stand}\n"
                        f"  Stop-Loss {float(_offen.get('stop_loss') or 0):,.2f} $\n"
                        f"  Ziel      {float(_offen.get('take_profit') or 0):,.2f} $\n")
                if a["is_entry"]:
                    _txt += (f"\nHeutige Empfehlung (wird NICHT aufgezeichnet,\n"
                             f"solange oben eines laeuft):\n"
                             f"  Einstieg  {a['entry']:,.2f} $   "
                             f"Stop {a['stop_loss']:,.2f}   Ziel {a['take_profit']:,.2f}")
                c["levels"].configure(text=_txt)
            elif a["is_entry"]:
                c["levels"].configure(
                    text=f"NEUES SIGNAL - wird jetzt aufgezeichnet\n"
                         f"  Einstieg  {a['entry']:,.2f} $\n"
                         f"  Stop-Loss {a['stop_loss']:,.2f} $\n"
                         f"  Ziel      {a['take_profit']:,.2f} $")
            else:
                c["levels"].configure(text=f"{a['reason']}")

            # Chart zeichnen
            _draw_chart(widgets["charts"].get(name), a)

        # Performance
        if stats["closed"]:
            # [AUDIT 06.08.2026] Trefferquote nie mehr ohne ihre Unsicherheit.
            # Bei 5 geschlossenen Signalen reicht das 95%-Intervall von ~0 bis
            # ~45% - "Trefferquote 0%" allein liest sich wie ein Befund, ist
            # aber mit reinem Zufall vereinbar. col war ausserdem tote Variable.
            n = int(stats["closed"])
            lo, hi = _wilson(stats["wins"], n)
            col = CLR_GREEN if stats["total_pnl_pct"] >= 0 else CLR_RED
            warnung = "   ⚠ zu wenig Signale fuer ein Urteil" if n < 20 else ""
            widgets["perf_summary"].configure(
                text=f"Trefferquote {stats['win_rate']:.0f}%  "
                     f"(95%-Intervall {lo:.0f}–{hi:.0f}%, n={n})   ·   "
                     f"{stats['wins']} Gewinn / {stats['losses']} Verlust   ·   "
                     f"Summe {stats['total_pnl_pct']:+.2f}%{warnung}",
                text_color=col if n >= 20 else CLR_ORANGE)
        else:
            widgets["perf_summary"].configure(
                text=f"{stats['open']} offene Signale werden beobachtet · "
                     f"geschlossene kommen mit der Zeit")

        lines = []
        # [19.08.2026] Alle statt der letzten sechs. Bei acht Signalen in
        # zwei Monaten ist die Liste kurz genug - und der Reiter dient der
        # Recherche, da gehoert die vollstaendige Mitschrift hin.
        for s in stats["closed_signals"]:
            mark = "✓ WIN " if s["status"] == "WIN" else "✗ LOSS"
            lines.append(f"{mark}  {s['name']:<7} {s.get('entry_date','')} → "
                         f"{s.get('close_date','?')}   {s.get('pnl_pct',0):+.2f}%")
        # [FIX 17.08.2026] Offene Signale zeigten nur SL und TP - also keinen
        # Gewinn und keinen Verlust. Sven fiel auf, dass unten "nichts
        # eingetragen" wurde: Silber stand seit dem 24.06. mit +14,8 % offen,
        # sichtbar war davon nichts. Geschlossene Signale kommen selten (sechs
        # in zwei Monaten), also war die Anzeige die meiste Zeit stumm.
        # Der laufende Stand ist KEIN realisiertes Ergebnis und wird deshalb
        # ausdruecklich als "laeuft" ausgewiesen, nie in die Summe gerechnet.
        kurse = {a["name"]: a.get("price") for a in analyses} if analyses else {}
        for s in stats["open_signals"]:
            kurs = kurse.get(s["name"])
            stand = ""
            try:
                ein = float(s.get("entry_price") or 0)
                if kurs and ein > 0:
                    if s.get("direction", "LONG") == "SHORT":
                        pnl = (ein - float(kurs)) / ein * 100
                    else:
                        pnl = (float(kurs) / ein - 1) * 100
                    stand = f"   laeuft {pnl:+.2f}%"
            except (TypeError, ValueError):
                stand = ""
            lines.append(f"⋯ OFFEN {s['name']:<7} seit {s.get('entry_date','')}"
                         f"{stand}   "
                         f"SL {s['stop_loss']:,.0f} / TP {s['take_profit']:,.0f}")
        widgets["perf_list"].configure(text="\n".join(lines) if lines else "")

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        widgets["status"].configure(text=f"Stand {ts}", text_color=CLR_GREEN)
        widgets["btn"].configure(state="normal")
    except Exception as e:
        _show_error(widgets, str(e))


def _draw_chart(chart, a):
    """Zeichnet den Kursverlauf mit SL/TP-Linien."""
    if not chart or "df" not in a:
        return
    try:
        ax = chart["ax"]
        ax.clear()
        ax.set_facecolor("#0d0d0f")
        df = a["df"].tail(90)
        ax.plot(df.index, df["Close"], color=CLR_ACCENT, linewidth=1.4)

        if a["is_entry"]:
            ax.axhline(a["stop_loss"], color=CLR_RED, linewidth=0.9,
                       linestyle="--", alpha=0.8)
            ax.axhline(a["take_profit"], color=CLR_GREEN, linewidth=0.9,
                       linestyle="--", alpha=0.8)
        ax.axhline(a["price"], color="#888", linewidth=0.7, alpha=0.5)

        ax.set_title(f"{a['name']} (90 Tage)", color="#ccc", fontsize=9)
        ax.tick_params(colors="#666", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color("#2a2a30")
        ax.grid(True, color="#1a1a1f", linewidth=0.5)
        chart["fig"].tight_layout()
        chart["canvas"].draw()
    except Exception:
        pass
