"""
Trading Imperium V7 – Hauptfenster (UI)
Gleicher Dark-Theme Look wie V4, verbunden mit den V5-Agenten.
"""
import customtkinter as ctk
import threading
import time
import os
import json
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# === Background Image Support ===
try:
    from PIL import Image, ImageTk
    import tkinter as _tk_for_bg
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    print("[UI] Pillow nicht installiert - Hintergrundbild deaktiviert (pip install Pillow)")

# Farben (identisch mit V4)
CLR_BG = "#0e0e10"
CLR_CARD = "#141417"
CLR_BORDER = "#2a2a30"
CLR_ACCENT = "#f1c40f"
CLR_GREEN = "#00ff88"
CLR_RED = "#ff4655"
CLR_BLUE = "#4fa3e0"
CLR_PURPLE = "#e056fd"
CLR_ORANGE = "#ff9500"
CLR_CYAN = "#00d4ff"
CLR_AI = "#e056fd"


class MainWindow(ctk.CTk):
    """Trading Imperium V7 – Hauptfenster."""

    def __init__(self, engine):
        super().__init__()
        self.engine = engine  # TradingImperiumV5 Instanz

        # [26.09.2026, Wunsch Sven] Der Titel muss auf den ersten Blick
        # sagen, WELCHER Bot das ist. Auf diesem Rechner laufen zwei
        # nebeneinander - der Papier-Bot aus trading_imperium_v6(21) und
        # dieser hier aus trading_imperium_v7. Vorher stand in beiden
        # Fenstern derselbe Text "TRADING IMPERIUM V6 - Multi-Agent";
        # verwechselt man sie, stellt man Regeln am falschen Bot um.
        #
        # Deshalb stehen jetzt BEIDE Unterscheidungsmerkmale im Titel:
        # der Ordner (V7) und der Betriebsmodus. Der Modus ist das
        # wichtigere der zwei - ein Fenster, das PAPIER sagt, kann kein
        # echtes Geld bewegen, und umgekehrt.
        #
        # Die Codebasis bleibt Version 6.1.0 (config.json "version").
        # V7 bezeichnet die INSTANZ, nicht eine neue Programmversion.
        _modus = str(getattr(engine.config.trading, "mode", "?")).upper()
        _modus = {"PAPER": "PAPIER", "LIVE": "ECHTGELD"}.get(_modus, _modus)
        self.title("⚡ TRADING IMPERIUM V7 – Multi-Agent · %s" % _modus)
        self.geometry("1440x820")
        self.configure(fg_color=CLR_BG)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.is_running = False
        self.price_cache = {}
        self.chart_figs = {}
        self.chart_axes = {}
        self.chart_canvases = {}
        self.price_history = {}  # coin -> [prices]
        self._shared_client = None  # EIN geteilter ccxt Client
        self._ohlcv_cache = {}  # coin -> (timestamp, bars)

        self._build_header()
        self._build_tabs()
        self._build_cockpit()
        self._build_manuell_tab()
        self._build_backtest_tab()
        self._build_btc_tab()
        self._build_history_tab()
        self._build_agents_tab()
        self._build_settings_tab()
        self._build_log_tab()
        try:
            self._build_charts_tab()
        except Exception as _ce:
            print("[CHARTS] Tab nicht geladen:", _ce)
        self._build_footer()

        # Hintergrundbild laden (nach allen Widgets, damit es hinten landet)
        self._setup_background_image()

        # Periodisches Update
        self._start_updater()

        # [AUTOSTART-KLICK 14.10.2026, Pruefstand] Startet der Bot ueber
        # pruefstand/autostart/bots_starten.py (setzt TI_AUTOSTART=1), drueckt
        # das Fenster nach dem Aufbau selbst STARTEN. Ohne die Variable
        # (Doppelklick auf start_bot.bat) bleibt alles wie bisher.
        # Anlass: Windows-Update-Neustart 14.10.2026 - der Autostart oeffnete
        # nur das Fenster, gehandelt und ueberwacht wurde nichts.
        if os.environ.get("TI_AUTOSTART") == "1" and not self.is_running:
            self.after(5000, self._toggle_bot)

    # ==========================================================
    # HINTERGRUNDBILD
    # ==========================================================
    def _setup_background_image(self):
        """Laedt Hintergrundbild als unterste Schicht."""
        if not _HAS_PIL:
            return
        try:
            # Suche das Bild an typischen Stellen
            base = os.path.dirname(os.path.abspath(__file__))
            bg_paths = [
                os.path.join(base, "assets", "cockpit_bg.png"),
                os.path.join(base, "assets", "background.png"),
                os.path.join(base, "..", "ui", "assets", "cockpit_bg.png"),
            ]
            bg_path = next((p for p in bg_paths if os.path.exists(p)), None)
            if not bg_path:
                print("[UI] Kein Hintergrundbild gefunden (ui/assets/cockpit_bg.png)")
                return

            # Bild laden + speichern (gegen Garbage-Collection)
            self._bg_image_pil = Image.open(bg_path).convert("RGB")
            self._bg_image_tk = ImageTk.PhotoImage(self._bg_image_pil)

            # Label ganz hinten platzieren
            self._bg_label = _tk_for_bg.Label(self, image=self._bg_image_tk,
                                              bd=0, bg=CLR_BG)
            self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self._bg_label.lower()  # ganz hinten

            # Resize-Handler fuer adaptive Skalierung
            self.bind("<Configure>", self._on_bg_resize)

            print(f"[UI] Hintergrundbild geladen: {os.path.basename(bg_path)}")
        except Exception as e:
            print(f"[UI] Hintergrundbild-Fehler: {e}")

    def _on_bg_resize(self, event=None):
        """Skaliert Hintergrundbild bei Fenstergroessen-Aenderung."""
        try:
            if not hasattr(self, "_bg_image_pil"):
                return
            # Nur auf Hauptfenster-Events reagieren, nicht auf alle Children
            if event is not None and event.widget is not self:
                return
            w = self.winfo_width()
            h = self.winfo_height()
            if w < 100 or h < 100:
                return
            # Anti-Spam: nicht oefter als 10x pro Sekunde
            now = time.time()
            if hasattr(self, "_last_bg_resize") and now - self._last_bg_resize < 0.1:
                return
            self._last_bg_resize = now

            resized = self._bg_image_pil.resize((w, h), Image.LANCZOS)
            self._bg_image_tk = ImageTk.PhotoImage(resized)
            self._bg_label.configure(image=self._bg_image_tk)
        except Exception:
            pass

    # ==========================================================
    # HEADER – Stats-Leiste oben
    # ==========================================================
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(pady=(8, 4), padx=20, fill="x")
        ctk.CTkLabel(header, text="⚡ TRADING IMPERIUM V7", font=("Bahnschrift", 24, "bold"),
                     text_color=CLR_ACCENT).pack(side="left")
        ctk.CTkLabel(header, text="  Multi-Agent · KI-gesteuert",
                     font=("Arial", 11), text_color="#666").pack(side="left", padx=10)

        # Stats-Karten
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=20, pady=(0, 5))

        self.stat_labels = {}
        stat_items = [
            ("USDC", "usdc", "#fff"), ("SESSION P&L", "pnl", CLR_GREEN),
            ("BTC GESAMT", "btc", CLR_ORANGE), ("STRATEGIE", "strategy", CLR_AI),
            ("ZYKLUS", "cycle", CLR_CYAN), ("AGENTS", "agents", CLR_GREEN),
        ]
        for name, key, color in stat_items:
            card = ctk.CTkFrame(stats, fg_color=CLR_CARD, corner_radius=10,
                                border_width=1, border_color=CLR_BORDER)
            card.pack(side="left", expand=True, fill="x", padx=3, ipady=6)
            ctk.CTkLabel(card, text=f"◉ {name}", font=("Arial", 9),
                         text_color="#666").pack(pady=(4, 0))
            lbl = ctk.CTkLabel(card, text="–", font=("Arial", 18, "bold"), text_color=color)
            lbl.pack(pady=(0, 4))
            self.stat_labels[key] = lbl

    # ==========================================================
    # TABS
    # ==========================================================
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_fg_color=CLR_CARD,
                                   segmented_button_selected_color=CLR_ACCENT,
                                   segmented_button_selected_hover_color="#d4a017",
                                   segmented_button_unselected_color=CLR_CARD)
        self.tabs.pack(expand=True, fill="both", padx=12, pady=2)

        self.tab_cockpit = self.tabs.add("📊 COCKPIT")
        try:
            self.tab_cockpit.configure(fg_color="transparent")
        except Exception:
            pass
        self.tab_manuell = self.tabs.add("🛒 MANUELL")
        self.tab_backtest = self.tabs.add("📈 BACKTEST")
        self.tab_btc = self.tabs.add("₿ BTC")
        self.tab_history = self.tabs.add("📜 HISTORY")
        self.tab_agents = self.tabs.add("🤖 AGENTS")
        self.tab_settings = self.tabs.add("⚙️ SETTINGS")
        self.tab_log = self.tabs.add("📋 LOG")
        self.tab_charts = self.tabs.add("🕯️ CHARTS")

        # === EDELMETALL-TAB (isoliert, optional - crasht den Bot nie) ===
        try:
            self.tab_metals = self.tabs.add("🥇 METALLE")
            from metals.metals_tab import build_metals_tab
            build_metals_tab(self.tab_metals)
        except Exception as _metals_err:
            print(f"[METALLE] Tab nicht geladen: {_metals_err}")

        # === TERMINAL-TAB (isoliert, read-only - crasht den Bot nie) === [TERMINAL-TAB 14.07.]
        try:
            self.tab_terminal = self.tabs.add("\U0001F5A5 TERMINAL")
            from ui.terminal_tab import build_terminal_tab
            build_terminal_tab(self.tab_terminal, self.engine)
        except Exception as _term_err:
            print(f"[TERMINAL] Tab nicht geladen: {_term_err}")

        # === ZYKLUS-TAB (isoliert, read-only - crasht den Bot nie) === [ZYKLUS-TAB 19.07.]
        try:
            self.tab_zyklus = self.tabs.add("\U0001F30D ZYKLUS")
            from ui.zyklus_tab import build_zyklus_tab
            build_zyklus_tab(self.tab_zyklus, self.engine)
        except Exception as _zyk_err:
            print(f"[ZYKLUS] Tab nicht geladen: {_zyk_err}")

        # === GELDFLUSS-TAB (isoliert, read-only - crasht den Bot nie) === [GELDFLUSS-TAB 20.07.]
        try:
            self.tab_geldfluss = self.tabs.add("\U0001F30A GELDFLUSS")
            from ui.geldfluss_tab import build_geldfluss_tab
            build_geldfluss_tab(self.tab_geldfluss, self.engine)
        except Exception as _gf_err:
            print(f"[GELDFLUSS] Tab nicht geladen: {_gf_err}")

        # === CHARTANALYSE-TAB (isoliert, read-only - crasht den Bot nie) ===
        # [CHARTANALYSE-TAB 07.08.2026] Zeigt Zonen, Formationen und Signale
        # samt Backtest-Zahlen. Loest ausdruecklich KEINEN Handel aus - die
        # Analyse wird erst gemessen und nur bei belegtem Vorteil eingebaut.
        try:
            self.tab_chartanalyse = self.tabs.add("\U0001F4D0 ANALYSE")
            from ui.chartanalyse_tab import build_chartanalyse_tab
            build_chartanalyse_tab(self.tab_chartanalyse, self.engine)
        except Exception as _ca_err:
            print(f"[ANALYSE] Tab nicht geladen: {_ca_err}")

    # ==========================================================
    # COCKPIT – Coin-Karten mit Preisen
    # ==========================================================
    def _build_cockpit(self):
        # Trading Controls Leiste (SL, Trail, Position)
        ctrl = ctk.CTkFrame(self.tab_cockpit, fg_color=CLR_CARD, corner_radius=10, height=42)
        ctrl.pack(fill="x", padx=5, pady=(3, 0))
        ctrl.pack_propagate(False)

        ctk.CTkLabel(ctrl, text="⚙️ RISK:", font=("Arial", 11, "bold"),
                     text_color=CLR_ACCENT).pack(side="left", padx=(10, 5))

        ctk.CTkLabel(ctrl, text="Stop-Loss %:", text_color="#888", font=("Arial", 10)).pack(side="left")
        self.ck_sl_var = ctk.StringVar(value=str(self.engine.config.risk.stop_loss_pct))
        ctk.CTkEntry(ctrl, textvariable=self.ck_sl_var, width=50, height=26,
                     fg_color="#0d0d0f", font=("Arial", 10)).pack(side="left", padx=(3, 10))

        ctk.CTkLabel(ctrl, text="Trailing %:", text_color="#888", font=("Arial", 10)).pack(side="left")
        self.ck_trail_var = ctk.StringVar(value=str(self.engine.config.risk.trailing_stop_pct))
        ctk.CTkEntry(ctrl, textvariable=self.ck_trail_var, width=50, height=26,
                     fg_color="#0d0d0f", font=("Arial", 10)).pack(side="left", padx=(3, 10))

        ctk.CTkLabel(ctrl, text="Position %:", text_color="#888", font=("Arial", 10)).pack(side="left")
        self.ck_pos_var = ctk.StringVar(value=str(self.engine.config.trading.position_size_pct))
        ctk.CTkEntry(ctrl, textvariable=self.ck_pos_var, width=50, height=26,
                     fg_color="#0d0d0f", font=("Arial", 10)).pack(side="left", padx=(3, 10))

        ctk.CTkLabel(ctrl, text="Max Trades:", text_color="#888", font=("Arial", 10)).pack(side="left")
        self.ck_maxpos_var = ctk.StringVar(value=str(self.engine.config.risk.max_open_positions))
        ctk.CTkEntry(ctrl, textvariable=self.ck_maxpos_var, width=40, height=26,
                     fg_color="#0d0d0f", font=("Arial", 10)).pack(side="left", padx=(3, 5))

        ctk.CTkLabel(ctrl, text="TP%:", text_color="#888", font=("Arial", 10)).pack(side="left")
        self.ck_tp_var = ctk.StringVar(value=str(self.engine.config.risk.take_profit_pct))
        ctk.CTkEntry(ctrl, textvariable=self.ck_tp_var, width=40, height=26,
                     fg_color="#0d0d0f", font=("Arial", 10)).pack(side="left", padx=(3, 5))

        ctk.CTkButton(ctrl, text="Anwenden", font=("Arial", 10, "bold"), width=80, height=26,
                      fg_color=CLR_ACCENT, text_color="#000", hover_color="#d4a017",
                      command=self._apply_cockpit_risk).pack(side="left", padx=5)

        # Sparplan schnell AN/AUS
        self.ck_sp_var = ctk.BooleanVar(value=self.engine.config.trading.btc_dca_enabled)
        ctk.CTkSwitch(ctrl, variable=self.ck_sp_var, text="Sparplan",
                      font=("Arial", 10), onvalue=True, offvalue=False,
                      fg_color="#333", progress_color=CLR_GREEN,
                      command=self._toggle_sparplan_quick).pack(side="right", padx=10)

        # [BTC-ONLY 07.08.2026] Echter Modus-Umschalter. Bis hierher liessen
        # sich nur die WERTE des aktiven Modus aendern (Zeile ~319), zwischen
        # den Modi wechseln ging ausschliesslich per Hand in config.json.
        self.ck_modus_var = ctk.StringVar(
            value=getattr(self.engine.config.modes, "active_mode", "balanced"))
        ctk.CTkOptionMenu(ctrl, variable=self.ck_modus_var,
                          values=["balanced", "btc_only", "all_in", "diversified"],
                          width=118, height=26, font=("Arial", 10),
                          fg_color="#0d0d0f", button_color=CLR_ACCENT,
                          button_hover_color="#d4a017", text_color="#ddd",
                          command=self._modus_umschalten).pack(side="right", padx=(0, 4))
        ctk.CTkLabel(ctrl, text="Modus:", text_color="#888",
                     font=("Arial", 10)).pack(side="right", padx=(8, 3))

        # Links-Leiste (Dashboard, Webhook)
        links = ctk.CTkFrame(self.tab_cockpit, fg_color="transparent", height=28)
        links.pack(fill="x", padx=5, pady=(0, 2))
        # [25.09.2026, Befund 111] Port aus der Konfiguration, nicht fest.
        # Vorher standen hier zweimal 5050 - in der Beschriftung UND im
        # Ziel des Knopfes. Auf diesem Rechner haelt der v6-Bot die 5050;
        # der Knopf oeffnete also dessen Dashboard, und die Beschriftung
        # behauptete, es sei das eigene.
        _dash_port = self.engine.config.dashboard.port
        ctk.CTkButton(links, text="🌐 Dashboard (localhost:%d)" % _dash_port,
                      font=("Arial", 10),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER, height=24,
                      command=lambda p=_dash_port: __import__('webbrowser').open(
                          'http://localhost:%d' % p)
                      ).pack(side="left", padx=3)
        # [19.08.2026] Hier stand der Knopf "Webhook (stillgelegt)".
        #
        # Vorgeschichte: Bis zum 13.08. hiess er "Webhook (localhost:5051)"
        # und zeigte eine Anleitung, wie man Kaufsignale dorthin schickt -
        # obwohl der Webhook seit dem 13.08. abgeschaltet ist
        # (GEFUNDENE-PROBLEME #14). Danach sagte er wenigstens die Wahrheit,
        # blieb aber ein Knopf, der nichts tut.
        #
        # Sven am 19.08.: "koennten wir evtl die localhost:8110 in diese
        # stillgelegte webhook uebertragen im cockpit?"
        #
        # Der Platz macht sich jetzt nuetzlich: er oeffnet das Analyse-
        # Cockpit. Am Webhook aendert das NICHTS - er bleibt stillgelegt,
        # die fuenf Gruende und die fuenf Reparaturpunkte stehen weiter im
        # Kopf von ui/webhook_server.py, und der Systemstatus fuehrt ihn
        # weiter als {"running": False, "stillgelegt_am": "2026-08-13"}
        # (app.py:4428). Es verschwindet also keine Information, nur ein
        # toter Knopf.
        #
        # Zwei verschiedene Oberflaechen, nicht zu verwechseln:
        #   dashboard.port      = Dashboard des laufenden Bots (Knopf links)
        #   dashboard.cockpit_port = Analyse-Cockpit, eigenes Programm,
        #                            NUR LESEND
        # [25.09.2026, Befund 111] Beide Zahlen stehen jetzt in
        # data_store/config.json. In v7 sind es 5070 und 8170, weil der
        # v6-Bot auf diesem Rechner 5050 und 8110 haelt.
        ctk.CTkButton(links, text="🔬 Analyse-Cockpit (%d)"
                      % self.engine.config.dashboard.cockpit_port,
                      font=("Arial", 10),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER,
                      height=24,
                      command=self._analyse_cockpit_oeffnen
                      ).pack(side="left", padx=3)
        ctk.CTkButton(links, text="📊 Analyse Export", font=("Arial", 10),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER, height=24,
                      command=self._quick_export).pack(side="left", padx=3)
        ctk.CTkButton(links, text="💾 State speichern", font=("Arial", 10),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER, height=24,
                      command=self._save_full_state).pack(side="left", padx=3)

        # Coin-Karten
        self.coin_scroll = ctk.CTkScrollableFrame(self.tab_cockpit, fg_color="transparent",
                                                   orientation="horizontal", height=380)
        self.coin_scroll.pack(expand=True, fill="both", pady=3)

        self.coin_labels = {}
        coins = self.engine.config.trading.coins[:10]
        for coin in coins:
            self._create_coin_card(coin)

    def _modus_umschalten(self, neuer_modus: str):
        """[BTC-ONLY 07.08.2026] Wechselt den Trading-Modus zur Laufzeit.

        BESTANDSSCHUTZ - der Punkt, an dem es sonst Geisterpositionen gaebe:
        Ein Moduswechsel beruehrt OFFENE POSITIONEN NICHT. Sie behalten
        Stop-Loss und Trailing-Stop und werden vom Exit-Monitor ganz normal
        zu Ende verwaltet; die RiskEngine genehmigt Verkaeufe ohnehin immer
        (risk/engine.py:81). Gesperrt werden ausschliesslich NEUE Kaeufe.
        Wer beim Umschalten auf btc_only ETH und SOL haelt, behaelt sie also
        mit vollem Schutz - sie werden nur nicht mehr nachgekauft.
        """
        try:
            alt = getattr(self.engine.config.modes, "active_mode", "?")
            self.engine.config.modes.active_mode = neuer_modus
            m = self.engine.config.get_active_mode()

            # Die RiskEngine liest max_open_positions aus ihrer eigenen
            # Config-Kopie - ohne dieses Nachziehen wuerde der neue Modus
            # zwar in der Datei stehen, aber nicht wirken.
            try:
                self.engine.risk_engine.config.max_open_positions = m.max_positions
                self.engine.risk_engine.exposure.max_coin_pct = m.max_coin_pct
            except Exception as _re:
                self._add_log(f"WARNUNG: RiskEngine nicht aktualisiert ({str(_re)[:50]})")

            self.engine.config.trading.position_size_pct = m.position_size_pct
            self.engine.config.risk.max_open_positions = m.max_positions
            self.engine.config.save()

            # Anzeigefelder mitziehen, sonst zeigt die Maske alte Werte
            try:
                self.ck_pos_var.set(str(m.position_size_pct))
                self.ck_maxpos_var.set(str(m.max_positions))
            except Exception:
                pass

            nur = (getattr(m, "nur_asset", "") or "").upper()
            zusatz = f" | NUR {nur}" if nur else ""
            self._add_log(f"MODUS {alt} -> {neuer_modus}: "
                          f"{m.position_size_pct:.0f}% pro Trade, "
                          f"max {m.max_positions} Positionen{zusatz} | GESPEICHERT")

            # Explizite Bestandsmeldung - der Nutzer soll nie raten muessen,
            # was mit bereits gekauften Coins passiert.
            try:
                offen = [s for s, p in self.engine.risk_engine.open_positions.items()
                         if p.get("active")]
                if nur:
                    gesperrt = [s for s in offen
                                if not s.split("/")[0].upper() == nur]
                    if gesperrt:
                        self._add_log(
                            f"BESTAND: {', '.join(gesperrt)} bleibt offen und "
                            f"wird NICHT verkauft. Stop-Loss und Trailing laufen "
                            f"normal weiter - gesperrt sind nur neue Kaeufe.")
                    else:
                        self._add_log("BESTAND: keine gesperrten Coins offen.")
                if len(offen) > m.max_positions:
                    self._add_log(
                        f"HINWEIS: {len(offen)} Positionen offen, neues Limit ist "
                        f"{m.max_positions}. Es wird nichts zwangsverkauft - der "
                        f"Bot kauft nur nichts Neues, bis wieder Platz ist.")
            except Exception:
                pass
        except Exception as e:
            self._add_log(f"Modus-Wechsel fehlgeschlagen: {e}")

    def _apply_cockpit_risk(self):
        try:
            self.engine.config.risk.stop_loss_pct = float(self.ck_sl_var.get())
            self.engine.config.risk.trailing_stop_pct = float(self.ck_trail_var.get())
            self.engine.config.trading.position_size_pct = float(self.ck_pos_var.get())
            self.engine.config.risk.max_open_positions = int(self.ck_maxpos_var.get())
            tp = float(self.ck_tp_var.get())
            self.engine.config.risk.take_profit_pct = tp
            # === FIX: UI-Werte in aktiven Mode schreiben ===
            # Sonst werden sie ignoriert, weil app.py den Mode-Wert liest
            try:
                active_mode = self.engine.config.get_active_mode()
                active_mode.position_size_pct = float(self.ck_pos_var.get())
                active_mode.max_positions = int(self.ck_maxpos_var.get())
                self._add_log(f'[FIX] Mode {active_mode.name}: pos_size={active_mode.position_size_pct}%, max_pos={active_mode.max_positions}')
            except Exception as _e:
                self._add_log(f'[FIX] Mode-Update Fehler: {_e}')
            # === END FIX ===
            self.engine.config.risk.max_exposure_per_coin_pct = max(
                self.engine.config.trading.position_size_pct + 5, 25)
            self.engine.config.save()
            tp_text = f"TP {tp}%" if tp > 0 else "TP AUS"
            self._add_log(f"Risk: SL {self.ck_sl_var.get()}% | Trail {self.ck_trail_var.get()}% | "
                         f"Pos {self.ck_pos_var.get()}% | Max {self.ck_maxpos_var.get()} | {tp_text} | GESPEICHERT")
            # Settings-Tab synchronisieren
            self._sync_settings_from_config()
        except ValueError:
            self._add_log("Fehler: Ungueltige Werte!")

    def _toggle_sparplan_quick(self):
        active = self.ck_sp_var.get()
        self.engine.config.trading.btc_dca_enabled = active
        self.engine.btc_accumulator.sparplan_active = active
        self.engine.config.save()
        # Settings-Tab synchronisieren
        if hasattr(self, 'sparplan_var'):
            self.sparplan_var.set(active)
        self._add_log(f"₿ Sparplan: {'AN' if active else 'AUS'} | GESPEICHERT")

    def _sync_settings_from_config(self):
        """Synchronisiert ALLE UI-Felder aus der Config."""
        cfg = self.engine.config
        try:
            # Cockpit -> Settings sync
            if hasattr(self, 'risk_vars'):
                self.risk_vars["stop_loss"].set(str(cfg.risk.stop_loss_pct))
                self.risk_vars["trailing"].set(str(cfg.risk.trailing_stop_pct))
                self.risk_vars["pos_size"].set(str(cfg.trading.position_size_pct))
                self.risk_vars["max_positions"].set(str(cfg.risk.max_open_positions))
                self.risk_vars["max_daily_loss"].set(str(cfg.risk.max_daily_loss_usd))
            # Settings -> Cockpit sync
            self.ck_sl_var.set(str(cfg.risk.stop_loss_pct))
            self.ck_trail_var.set(str(cfg.risk.trailing_stop_pct))
            self.ck_pos_var.set(str(cfg.trading.position_size_pct))
            self.ck_maxpos_var.set(str(cfg.risk.max_open_positions))
            self.ck_tp_var.set(str(cfg.risk.take_profit_pct))
            # Sparplan sync
            self.ck_sp_var.set(cfg.trading.btc_dca_enabled)
            if hasattr(self, 'sparplan_var'):
                self.sparplan_var.set(cfg.trading.btc_dca_enabled)
            # Balance sync
            if hasattr(self, 'balance_var'):
                self.balance_var.set(str(cfg.trading.initial_paper_balance))
        except Exception:
            pass

    def _analyse_cockpit_oeffnen(self):
        """Oeffnet das Analyse-Cockpit. Anschluss: dashboard.cockpit_port
        aus data_store/config.json (in v7 8170, siehe Befund 111).

        [19.08.2026] Startet den Server nur, wenn er nicht schon laeuft -
        sonst gibt es zwei Prozesse auf demselben Anschluss, und der
        zweite stirbt lautlos mit "address already in use". Geprueft wird
        deshalb der ANSCHLUSS, nicht die Prozessliste: ob dort etwas
        antwortet, ist die Frage, nicht ob irgendwo ein Python laeuft.

        Das Cockpit ist ein eigenes Programm (cockpit_server.py), liest
        nur und bindet auf 127.0.0.1 - also ausschliesslich dieser
        Rechner, kein Zugriff aus dem Heimnetz. Genau das war der Fehler
        des alten Webhooks, dessen Platz dieser Knopf einnimmt.
        """
        import socket
        import subprocess
        import sys
        import webbrowser

        # [25.09.2026, Befund 111] Vorher fest 8110. Der v6-Bot haelt diesen
        # Anschluss auf diesem Rechner, und laeuft() unten prueft nur, ob
        # dort ETWAS antwortet - nicht ob es das eigene Cockpit ist. Der
        # Knopf meldete deshalb "laeuft bereits" und oeffnete v6-Daten,
        # ohne je ein eigenes Cockpit zu starten.
        HAFEN = self.engine.config.dashboard.cockpit_port
        adresse = "http://localhost:%d" % HAFEN

        def laeuft():
            s = socket.socket()
            s.settimeout(0.6)
            try:
                return s.connect_ex(("127.0.0.1", HAFEN)) == 0
            finally:
                s.close()

        try:
            if laeuft():
                self._add_log("🔬 Analyse-Cockpit laeuft bereits - oeffne %s"
                              % adresse)
                webbrowser.open(adresse)
                return

            wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            skript = os.path.join(wurzel, "cockpit_server.py")
            if not os.path.exists(skript):
                self._add_log("🔬 cockpit_server.py nicht gefunden: %s" % skript)
                return

            # sys.executable statt "pythonw" aus dem Suchpfad: so laeuft das
            # Cockpit mit demselben Python wie der Bot, samt derselben
            # Pakete.
            #
            # Anmerkung zum 0-Byte-Alias: sys.executable zeigt hier auf
            # ...\WindowsApps\python.exe - eine 0-Byte-Datei
            # (App-Ausfuehrungsalias). In schatten_universum_start.bat steht
            # gewarnt, dass daran am 14.08. drei Versuche ueber die
            # AUFGABENPLANUNG lautlos gescheitert sind. Aus einem laufenden
            # Python heraus greift er dagegen - am 19.08. nachgemessen:
            # Popen mit genau diesem Pfad, Anschluss nach 0,7 s offen.
            # Der Unterschied liegt an der Aufgabenplanung, nicht am Alias.
            ohne_fenster = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen([sys.executable, skript], cwd=wurzel,
                             creationflags=ohne_fenster,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            self._add_log("🔬 Analyse-Cockpit wird gestartet ...")

            # Nach dem Start nachsehen, ob wirklich etwas passiert ist -
            # kein stilles Scheitern (CLAUDE.md Dauerregel 4).
            def nachsehen(versuch=0):
                if laeuft():
                    self._add_log("🔬 Analyse-Cockpit laeuft - oeffne %s"
                                  % adresse)
                    webbrowser.open(adresse)
                elif versuch < 8:
                    self.after(700, lambda: nachsehen(versuch + 1))
                else:
                    self._add_log(
                        "🔬 Analyse-Cockpit ist nach 6 Sekunden nicht "
                        "erreichbar. Von Hand starten und die Meldung lesen: "
                        "python cockpit_server.py")

            self.after(900, nachsehen)
        except Exception as e:
            self._add_log("🔬 Analyse-Cockpit konnte nicht geoeffnet werden: %s"
                          % str(e)[:90])

    def _quick_export(self):
        """Exportiert alle Daten als TXT."""
        try:
            import os
            from datetime import datetime
            text = self.engine.generate_analyse_export()
            # Log-Daten anhaengen
            text += "\n\n" + "=" * 80 + "\nLOG (letzte 100 Zeilen)\n" + "=" * 80 + "\n"
            for entry in self.engine._log_buffer[-100:] if hasattr(self.engine, '_log_buffer') else []:
                text += f"{entry}\n"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", f"export_komplett_{ts}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._add_log(f"📊 Export: {path}")
        except Exception as e:
            self._add_log(f"Export Fehler: {e}")

    def _save_full_state(self):
        """Speichert kompletten Bot-Zustand."""
        try:
            self.engine.state.save()
            self.engine.config.save()
            self.engine.journal.save()
            self._add_log("💾 State + Config + Journal gespeichert!")
        except Exception as e:
            self._add_log(f"Speichern Fehler: {e}")

    def _create_coin_card(self, coin):
        card = ctk.CTkFrame(self.coin_scroll, fg_color=CLR_CARD, corner_radius=14,
                            width=260, border_width=1, border_color=CLR_BORDER)
        card.pack(side="left", padx=5, pady=4, fill="y")
        card.pack_propagate(False)
        card.configure(width=260)

        asset = coin.split("/")[0]
        is_btc = asset == "BTC"

        # Header
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(6, 1))
        prefix = "₿ " if is_btc else ""
        ctk.CTkLabel(top, text=f"{prefix}{asset}",
                     font=("Arial", 15, "bold"),
                     text_color=CLR_ORANGE if is_btc else "#fff").pack(side="left")

        status_lbl = ctk.CTkLabel(top, text="⏸", font=("Arial", 13))
        status_lbl.pack(side="right")

        # Preis
        price_lbl = ctk.CTkLabel(card, text="Lade...", font=("Arial", 20, "bold"), text_color=CLR_ACCENT)
        price_lbl.pack(pady=(2, 0))

        # 24h Change
        change_lbl = ctk.CTkLabel(card, text="24h: –", font=("Arial", 10), text_color="#666")
        change_lbl.pack(pady=(0, 1))

        # Guthaben
        balance_lbl = ctk.CTkLabel(card, text="Guthaben: –", font=("Arial", 9, "bold"), text_color="#888")
        balance_lbl.pack(pady=0)

        # Signal
        signal_lbl = ctk.CTkLabel(card, text="Warte auf Signal", font=("Arial", 9), text_color="#555")
        signal_lbl.pack(pady=1)

        # P&L Anzeige (wie V4!)
        pnl_lbl = ctk.CTkLabel(card, text="", font=("Arial", 9, "bold"), text_color="#555")
        pnl_lbl.pack(pady=0)

        # Risk-Status
        risk_lbl = ctk.CTkLabel(card, text="", font=("Arial", 9), text_color=CLR_BLUE)
        risk_lbl.pack(pady=0)

        # Per-Coin Controls (SL/HOLD)
        coin_ctrl = ctk.CTkFrame(card, fg_color="transparent", height=24)
        coin_ctrl.pack(side="bottom", fill="x", padx=8, pady=(0, 2))
        sl_var = ctk.StringVar(value="SL")
        ctk.CTkSegmentedButton(coin_ctrl, values=["SL", "HOLD", "TP"],
            variable=sl_var, font=("Arial", 8), height=20,
            fg_color="#1a1a20", selected_color=CLR_ACCENT, selected_hover_color="#d4a017",
            command=lambda v, c=coin: self._set_coin_mode(c, v)).pack(fill="x")

        # Sell Button
        sell_btn = ctk.CTkButton(card, text="VERKAUFEN", font=("Arial", 11, "bold"),
                                 fg_color=CLR_RED, hover_color="#cc3344",
                                 height=26, corner_radius=6,
                                 command=lambda c=coin: self._sell_coin(c))
        sell_btn.pack(side="bottom", fill="x", padx=10, pady=(0, 4))

        # Chart (matplotlib)
        fig, ax = plt.subplots(figsize=(3.0, 1.4), dpi=78)
        fig.patch.set_facecolor(CLR_CARD)
        ax.set_facecolor(CLR_CARD)
        ax.set_axis_off()
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(1, 2))
        self.chart_figs[coin] = fig
        self.chart_axes[coin] = ax
        self.chart_canvases[coin] = canvas
        self.price_history[coin] = []

        self.coin_labels[coin] = {
            "price": price_lbl, "change": change_lbl, "balance": balance_lbl,
            "signal": signal_lbl, "pnl": pnl_lbl, "risk": risk_lbl, "status": status_lbl,
        }

    def _sell_coin(self, coin):
        """Verkauft einen Coin sofort."""
        from core.events import DecisionIntent, Side, EVENT_SIGNAL
        self._add_log(f"⚠️ Verkauf {coin} angefordert...")
        try:
            pos = self.engine.risk_engine.open_positions.get(coin, {})
            qty = pos.get("qty", 0)
            price = self.engine.data_agent.price_cache.get(coin, 0)
            if qty > 0 and price > 0:
                intent = DecisionIntent(
                    symbol=coin, side=Side.SELL, confidence=1.0,
                    entry_price=price, quantity=qty,
                    strategy_id="MANUAL_SELL", entry_reason="Manuell verkauft",
                    score=10, agent_id="manual")
                self.engine.bus.publish(EVENT_SIGNAL, intent, source="manual")
                self._add_log(f"✅ SELL {coin}: {qty:.6f} @ {price:,.2f}$")
            else:
                self._add_log(f"Keine offene Position fuer {coin}")
        except Exception as e:
            self._add_log(f"Verkauf-Fehler: {e}")

    def _set_coin_mode(self, coin, mode):
        """Setzt den Modus fuer einen einzelnen Coin: SL, HOLD, TP."""
        if not hasattr(self.engine, '_coin_modes'):
            self.engine._coin_modes = {}
        self.engine._coin_modes[coin] = mode
        if mode == "SL":
            self._add_log(f"⚙️ {coin}: Stop-Loss AKTIV")
        elif mode == "HOLD":
            self._add_log(f"⚙️ {coin}: HALTEN (kein SL, kein Verkauf)")
        elif mode == "TP":
            self._add_log(f"⚙️ {coin}: Take-Profit Modus")
        # Modus im Risk-Engine speichern
        if coin in self.engine.risk_engine.open_positions:
            self.engine.risk_engine.open_positions[coin]["mode"] = mode

    def _update_all_charts(self):
        """Aktualisiert alle Charts. Versucht OHLCV zu laden, Fallback auf Preis-Line."""
        for coin in list(self.chart_figs.keys()):
            try:
                self._update_chart(coin)
            except Exception:
                pass

    def _update_chart(self, coin):
        """Zeichnet Chart für einen Coin."""
        if coin not in self.chart_figs:
            return

        fig = self.chart_figs[coin]
        ax = self.chart_axes[coin]
        canvas = self.chart_canvases[coin]

        # Alte Achsen komplett löschen
        ax.clear()
        ax.set_facecolor(CLR_CARD)
        ax.set_axis_off()

        # Versuche OHLCV-Daten zu laden (gecached, max alle 60s neu)
        ohlcv_data = None
        try:
            cached = self._ohlcv_cache.get(coin)
            if cached and (time.time() - cached[0]) < 60:
                ohlcv_data = cached[1]
            else:
                if not self._shared_client:
                    import ccxt as _ccxt
                    self._shared_client = _ccxt.binance({"enableRateLimit": True, "timeout": 10000})
                try:
                    bars = self._shared_client.fetch_ohlcv(coin, "15m", limit=40)
                except Exception:
                    alt = coin.replace("USDC", "USDT") if "USDC" in coin else coin.replace("USDT", "USDC")
                    bars = self._shared_client.fetch_ohlcv(alt, "15m", limit=40)
                if bars and len(bars) > 10:
                    ohlcv_data = bars
                    self._ohlcv_cache[coin] = (time.time(), bars)
        except Exception:
            pass

        if ohlcv_data:
            self._draw_candlestick(ax, ohlcv_data, coin)
        elif coin in self.price_history and len(self.price_history[coin]) > 3:
            self._draw_line_chart(ax, self.price_history[coin], coin)
        else:
            ax.text(0.5, 0.5, "Warte auf Daten...", ha='center', va='center',
                    fontsize=8, color='#444', transform=ax.transAxes)

        try:
            canvas.draw_idle()
        except Exception:
            pass

    def _draw_candlestick(self, ax, bars, coin):
        """Zeichnet Kerzen-Chart (wie V4)."""
        closes = [b[4] for b in bars]
        opens = [b[1] for b in bars]
        highs = [b[2] for b in bars]
        lows = [b[3] for b in bars]

        # Farben: grün wenn Close > Open, rot wenn Close < Open
        for i in range(len(bars)):
            c = CLR_GREEN if closes[i] >= opens[i] else CLR_RED
            # Kerzenkörper
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i])
            ax.bar(i, body_height, bottom=body_bottom, width=0.7,
                   color=c, edgecolor=c, linewidth=0.5)
            # Docht
            ax.vlines(i, lows[i], highs[i], color=c, linewidth=0.5)

        # EMA20 Linie (gelb)
        if len(closes) >= 20:
            ema = []
            mult = 2 / (20 + 1)
            ema.append(sum(closes[:20]) / 20)
            for j in range(20, len(closes)):
                ema.append((closes[j] - ema[-1]) * mult + ema[-1])
            x_ema = list(range(19, len(closes)))
            ax.plot(x_ema, ema, color=CLR_ACCENT, linewidth=0.8, alpha=0.7)

        # VWAP Linie (cyan, gestrichelt)
        volumes = [b[5] for b in bars]
        if len(volumes) > 5 and sum(volumes) > 0:
            import numpy as _np
            tp = [(_np.mean([highs[i], lows[i], closes[i]])) for i in range(len(bars))]
            cum_vol = _np.cumsum(volumes)
            cum_tp_vol = _np.cumsum([tp[i] * volumes[i] for i in range(len(bars))])
            vwap = [cum_tp_vol[i] / cum_vol[i] if cum_vol[i] > 0 else tp[i] for i in range(len(bars))]
            ax.plot(range(len(bars)), vwap, color=CLR_CYAN, linewidth=0.7, alpha=0.6, linestyle="--")

        # Buy/Sell Marker einzeichnen
        try:
            markers = self.engine._trade_markers.get(coin, [])
            bar_times = [b[0] for b in bars]
            for m in markers:
                mp = m["price"]
                # Finde naechste Kerze zum Trade-Zeitpunkt
                closest_idx = len(bars) - 1  # Default: letzte Kerze
                m_time_ms = m.get("time", 0) * 1000
                for bi, bt in enumerate(bar_times):
                    if bt >= m_time_ms:
                        closest_idx = bi; break
                if 0 <= closest_idx < len(bars):
                    if m["side"] == "BUY":
                        ax.scatter(closest_idx, mp, marker='^', color=CLR_GREEN, s=40, zorder=5)
                    else:
                        ax.scatter(closest_idx, mp, marker='v', color=CLR_RED, s=40, zorder=5)
        except Exception:
            pass

        # CVD-ähnlicher Indikator-Text
        pct_change = ((closes[-1] / closes[0]) - 1) * 100 if closes[0] > 0 else 0
        cvd_color = CLR_GREEN if pct_change >= 0 else CLR_RED
        ax.text(0.02, 0.92, f"CVD: {'▲' if pct_change >= 0 else '▼'}",
                fontsize=7, color=cvd_color, transform=ax.transAxes)

        ax.set_xlim(-0.5, len(bars) - 0.5)
        ax.margins(y=0.05)

    def _draw_line_chart(self, ax, prices, coin):
        """Fallback: Einfacher Linien-Chart aus gesammelten Preisen."""
        x = list(range(len(prices)))

        # Gradient-Farbe basierend auf Trend
        if prices[-1] >= prices[0]:
            line_color = CLR_GREEN
            fill_color = "#00ff8822"
        else:
            line_color = CLR_RED
            fill_color = "#ff465522"

        ax.plot(x, prices, color=line_color, linewidth=1.2)
        ax.fill_between(x, min(prices), prices, color=fill_color, alpha=0.3)

        ax.set_xlim(0, len(prices) - 1)
        ax.margins(y=0.05)

    # ==========================================================
    # BACKTEST TAB
    # ==========================================================
    def _build_backtest_tab(self):
        # Controls
        ctrl = ctk.CTkFrame(self.tab_backtest, fg_color=CLR_CARD, corner_radius=12)
        ctrl.pack(fill="x", padx=10, pady=5)

        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(row1, text="Coin:", text_color="#aaa").pack(side="left", padx=(0, 4))
        self.bt_coin_var = ctk.StringVar(value="BTC/USDC")
        ctk.CTkOptionMenu(row1, variable=self.bt_coin_var, width=130,
                          values=[c for c in self.engine.config.trading.coins[:10]],
                          fg_color="#0d0d0f").pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Timeframe:", text_color="#aaa").pack(side="left", padx=(10, 4))
        self.bt_tf_var = ctk.StringVar(value="1h")
        ctk.CTkOptionMenu(row1, variable=self.bt_tf_var, width=80,
                          values=["5m", "15m", "1h", "4h", "1d"],
                          fg_color="#0d0d0f").pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Kerzen:", text_color="#aaa").pack(side="left", padx=(10, 4))
        self.bt_limit_var = ctk.StringVar(value="500")
        ctk.CTkEntry(row1, textvariable=self.bt_limit_var, width=60, fg_color="#0d0d0f").pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="SL%:", text_color="#aaa").pack(side="left", padx=(10, 4))
        self.bt_sl_var = ctk.StringVar(value="4.0")
        ctk.CTkEntry(row1, textvariable=self.bt_sl_var, width=50, fg_color="#0d0d0f").pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Trail%:", text_color="#aaa").pack(side="left", padx=(10, 4))
        self.bt_trail_var = ctk.StringVar(value="1.5")
        ctk.CTkEntry(row1, textvariable=self.bt_trail_var, width=50, fg_color="#0d0d0f").pack(side="left", padx=4)

        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkButton(row2, text="▶ EINZELTEST", font=("Arial", 12, "bold"),
                      fg_color=CLR_ACCENT, text_color="#000", hover_color="#d4a017",
                      width=140, command=self._run_single_backtest).pack(side="left", padx=4)

        ctk.CTkButton(row2, text="🏆 MULTI-COIN TEST", font=("Arial", 12, "bold"),
                      fg_color=CLR_PURPLE, text_color="#fff", hover_color="#b040d0",
                      width=180, command=self._run_multi_backtest).pack(side="left", padx=4)

        ctk.CTkButton(row2, text="⚡ OPTIMIZER", font=("Arial", 11, "bold"),
                      fg_color="#ff6600", text_color="#fff", hover_color="#cc5500",
                      width=120, command=self._run_optimizer).pack(side="left", padx=4)

        self.bt_status = ctk.CTkLabel(row2, text="Bereit", font=("Arial", 10), text_color="#888")
        self.bt_status.pack(side="left", padx=10)

        # Ergebnis
        self.bt_result_text = ctk.CTkTextbox(self.tab_backtest, fg_color="#0d0d0f",
                                              font=("Consolas", 11), text_color="#ccc")
        self.bt_result_text.pack(expand=True, fill="both", padx=10, pady=5)
        self.bt_result_text.insert("end", "EINZELTEST: Testet einen Coin auf historischen Daten.\n"
                                          "MULTI-COIN: Testet alle Coins und erstellt Rangliste.\n"
                                          "OPTIMIZER: Findet beste SL/Trail/Pos Parameter.\n")
        self.bt_result_text.configure(state="disabled")

    def _run_single_backtest(self):
        self.bt_status.configure(text="Läuft...", text_color=CLR_ACCENT)
        self.update()
        threading.Thread(target=self._do_single_backtest, daemon=True).start()

    def _do_single_backtest(self):
        try:
            from backtest.engine import BacktestEngine
            import ccxt as _ccxt, pandas as pd, pandas_ta as ta
            bt = BacktestEngine(self.engine.config)
            coin = self.bt_coin_var.get()
            tf = self.bt_tf_var.get()
            limit = min(int(self.bt_limit_var.get()), 1000)  # Max 1000 (weniger Freeze)
            sl = float(self.bt_sl_var.get())
            trail = float(self.bt_trail_var.get())

            self.after(0, lambda: self.bt_status.configure(text=f"Lade {coin} ({limit} Kerzen)...", text_color=CLR_ACCENT))

            # Eigener Client (blockiert nicht den Preis-Ticker!)
            if not self._shared_client:
                import ccxt as _ccxt
                self._shared_client = _ccxt.binance({"enableRateLimit": True, "timeout": 15000})
            _c = self._shared_client
            try:
                bars = _c.fetch_ohlcv(coin, tf, limit=limit)
            except Exception:
                alt = coin.replace("USDC", "USDT")
                bars = _c.fetch_ohlcv(alt, tf, limit=limit)

            if not bars or len(bars) < 50:
                self.after(0, lambda: self._bt_output(f"❌ Keine Daten fuer {coin} ({len(bars) if bars else 0} Kerzen)"))
                return

            df = pd.DataFrame(bars, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            df["Date"] = pd.to_datetime(df["Date"], unit="ms")
            df.set_index("Date", inplace=True)
            df["RSI"] = ta.rsi(df["Close"], length=14)
            m = ta.macd(df["Close"])
            if m is not None:
                df["MACD"] = m.iloc[:, 0]; df["MACD_signal"] = m.iloc[:, 2]
            bb = ta.bbands(df["Close"], length=20, std=2)
            if bb is not None:
                for c in bb.columns: df[c] = bb[c]

            self.after(0, lambda: self.bt_status.configure(text="Berechne...", text_color=CLR_ACCENT))

            result = bt.run(df, coin=coin, stop_loss_pct=sl, trailing_pct=trail)
            result.timeframe = tf
            text = result.summary_text()

            text += "\n\n  TRADES:\n" + "─" * 65 + "\n"
            for t in result.trades[-30:]:  # Max 30 Trades anzeigen
                tp = t["type"]
                p = t.get("price", 0)
                pnl = t.get("pnl", "")
                pnl_s = f"  P&L: {pnl:+.2f}$" if isinstance(pnl, (int, float)) else ""
                reason = t.get("reason", "")[:30]
                text += f"  {tp:<6} @ {p:>10,.2f}${pnl_s}  {reason}\n"

            self.after(0, lambda: self._bt_output(text))
            self.after(0, lambda: self.bt_status.configure(text="Fertig!", text_color=CLR_GREEN))
        except Exception as e:
            self.after(0, lambda: self._bt_output(f"❌ Fehler: {e}"))
            self.after(0, lambda: self.bt_status.configure(text="Fehler", text_color=CLR_RED))

    def _run_multi_backtest(self):
        self.bt_status.configure(text="Läuft (kann dauern)...", text_color=CLR_ACCENT)
        self.update()
        threading.Thread(target=self._do_multi_backtest, daemon=True).start()

    def _do_multi_backtest(self):
        try:
            from backtest.engine import BacktestEngine
            import ccxt as _ccxt, pandas as pd, pandas_ta as ta
            bt = BacktestEngine(self.engine.config)
            coins = self.engine.config.trading.coins[:8]
            tf = self.bt_tf_var.get()
            limit = min(int(self.bt_limit_var.get()), 500)
            sl = float(self.bt_sl_var.get())
            trail = float(self.bt_trail_var.get())

            if not self._shared_client:
                import ccxt as _ccxt
                self._shared_client = _ccxt.binance({"enableRateLimit": True, "timeout": 15000})
            _c = self._shared_client
            results = []
            for i, coin in enumerate(coins):
                self.after(0, lambda c=coin, idx=i: self.bt_status.configure(
                    text=f"{c} ({idx+1}/{len(coins)})...", text_color=CLR_ACCENT))
                try:
                    try:
                        bars = _c.fetch_ohlcv(coin, tf, limit=limit)
                    except Exception:
                        bars = _c.fetch_ohlcv(coin.replace("USDC", "USDT"), tf, limit=limit)
                    if bars and len(bars) >= 50:
                        df = pd.DataFrame(bars, columns=["Date","Open","High","Low","Close","Volume"])
                        df["Date"] = pd.to_datetime(df["Date"], unit="ms"); df.set_index("Date", inplace=True)
                        df["RSI"] = ta.rsi(df["Close"], length=14)
                        m = ta.macd(df["Close"])
                        if m is not None: df["MACD"]=m.iloc[:,0]; df["MACD_signal"]=m.iloc[:,2]
                        bb = ta.bbands(df["Close"], length=20, std=2)
                        if bb is not None:
                            for c2 in bb.columns: df[c2]=bb[c2]
                        r = bt.run(df, coin=coin, stop_loss_pct=sl, trailing_pct=trail)
                        r.timeframe = tf
                        results.append(r)
                except Exception:
                    pass
                time.sleep(0.5)

            if results:
                text = bt.ranking(results)
                for r in results[:3]:  # Nur Top 3 Details
                    text += f"\n\n{r.summary_text()}"
            else:
                text = "Keine Ergebnisse"

            self.after(0, lambda: self._bt_output(text))
            self.after(0, lambda: self.bt_status.configure(
                text=f"Fertig! {len(results)} Coins", text_color=CLR_GREEN))

            self.after(0, lambda: self._bt_output(text))
            self.after(0, lambda: self.bt_status.configure(text=f"Fertig! {len(results)} Coins", text_color=CLR_GREEN))
        except Exception as e:
            self.after(0, lambda: self._bt_output(f"❌ Fehler: {e}"))
            self.after(0, lambda: self.bt_status.configure(text="Fehler", text_color=CLR_RED))

    def _bt_output(self, text):
        self.bt_result_text.configure(state="normal")
        self.bt_result_text.delete("1.0", "end")
        self.bt_result_text.insert("end", text)
        self.bt_result_text.configure(state="disabled")

    def _run_optimizer(self):
        self.bt_status.configure(text="Optimizer laeuft...", text_color="#ff6600")
        self.update()
        threading.Thread(target=self._do_optimizer, daemon=True).start()

    def _do_optimizer(self):
        try:
            from backtest.engine import BacktestEngine
            from backtest.optimizer import BacktestOptimizer
            import ccxt as _ccxt, pandas as pd, pandas_ta as ta

            bt = BacktestEngine(self.engine.config)
            opt = BacktestOptimizer()
            coin = self.bt_coin_var.get()
            tf = self.bt_tf_var.get()

            self.after(0, lambda: self.bt_status.configure(text=f"Lade {coin}...", text_color="#ff6600"))

            if not self._shared_client:
                import ccxt as _ccxt
                self._shared_client = _ccxt.binance({"enableRateLimit": True, "timeout": 15000})
            _c = self._shared_client
            try:
                bars = _c.fetch_ohlcv(coin, tf, limit=500)
            except Exception:
                bars = _c.fetch_ohlcv(coin.replace("USDC", "USDT"), tf, limit=500)

            if not bars or len(bars) < 50:
                self.after(0, lambda: self._bt_output(f"Keine Daten fuer {coin}")); return

            df = pd.DataFrame(bars, columns=["Date","Open","High","Low","Close","Volume"])
            df["Date"] = pd.to_datetime(df["Date"], unit="ms"); df.set_index("Date", inplace=True)
            df["RSI"] = ta.rsi(df["Close"], length=14)
            m = ta.macd(df["Close"])
            if m is not None: df["MACD"]=m.iloc[:,0]; df["MACD_signal"]=m.iloc[:,2]
            bb = ta.bbands(df["Close"], length=20, std=2)
            if bb is not None:
                for c in bb.columns: df[c]=bb[c]

            self.after(0, lambda: self.bt_status.configure(text="Optimiere (kann dauern)...", text_color="#ff6600"))

            result = opt.grid_search(bt, df, coin=coin,
                sl_range=(2, 3, 4, 5, 6),
                trail_range=(0.5, 1.0, 1.5, 2.0, 3.0),
                pos_range=(10, 15, 20, 25, 30))

            text = opt.format_results(result)
            self.after(0, lambda: self._bt_output(text))
            self.after(0, lambda: self.bt_status.configure(text="Optimizer fertig!", text_color=CLR_GREEN))

            # Beste Parameter vorschlagen
            if result.get("best"):
                b = result["best"]
                self.after(0, lambda: self.bt_sl_var.set(str(b["sl"])))
                self.after(0, lambda: self.bt_trail_var.set(str(b["trail"])))
        except Exception as e:
            self.after(0, lambda: self._bt_output(f"Optimizer Fehler: {e}"))
            self.after(0, lambda: self.bt_status.configure(text="Fehler", text_color=CLR_RED))

    # ==========================================================
    # MANUELL TAB – Kaufen/Verkaufen per Hand
    # ==========================================================
    def _build_manuell_tab(self):
        # Coin + Timeframe + Betrag
        top = ctk.CTkFrame(self.tab_manuell, fg_color=CLR_CARD, corner_radius=12)
        top.pack(fill="x", padx=10, pady=3)

        row1 = ctk.CTkFrame(top, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(row1, text="Coin:", text_color="#aaa", font=("Arial", 10)).pack(side="left")
        self.man_coin_var = ctk.StringVar(value="BTC/USDC")
        coins = self.engine.config.trading.coins[:12]
        ctk.CTkOptionMenu(row1, variable=self.man_coin_var, width=130,
                          values=coins, fg_color="#0d0d0f",
                          command=lambda v: self._update_manuell_chart()).pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Zeitraum:", text_color="#aaa", font=("Arial", 10)).pack(side="left", padx=(10, 4))
        self.man_tf_var = ctk.StringVar(value="15m")
        for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
            ctk.CTkRadioButton(row1, text=tf, variable=self.man_tf_var, value=tf,
                               font=("Arial", 9), fg_color=CLR_ACCENT, text_color="#aaa",
                               command=self._update_manuell_chart).pack(side="left", padx=2)

        # [GEFUNDENE-PROBLEME #13, 13.08.2026] KAUFEN-Knopf und das
        # Betrag-Feld entfernt. Beide gehoerten ausschliesslich zum
        # Handkauf, der jetzt weg ist - Begruendung bei _manual_buy
        # (weiter unten im Abschnitt "ENTFERNT").
        # Der VERKAUFEN-Knopf bleibt: ein Kaufweg ist ein Risiko-Eingang,
        # ein Verkaufsweg ist ein Sicherheitsventil.
        ctk.CTkButton(row1, text="VERKAUFEN", font=("Arial", 10, "bold"),
                      fg_color=CLR_RED, text_color="#fff", width=100, height=26,
                      command=self._manual_sell).pack(side="right", padx=3)

        # Indikatoren-Checkboxen
        ind_frame = ctk.CTkFrame(top, fg_color="transparent")
        ind_frame.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(ind_frame, text="Indikatoren:", text_color="#888", font=("Arial", 9)).pack(side="left")

        self.man_indicators = {}
        for name, default in [("EMA 20/50", True), ("Bollinger", False), ("MACD", False),
                              ("RSI", False), ("VWAP", True), ("Fibonacci", True),
                              ("Volume", True), ("ADX", False)]:
            var = ctk.BooleanVar(value=default)
            ctk.CTkCheckBox(ind_frame, text=name, variable=var, font=("Arial", 9),
                           fg_color=CLR_ACCENT, text_color="#aaa", height=20, width=20,
                           checkbox_width=16, checkbox_height=16,
                           command=self._update_manuell_chart).pack(side="left", padx=4)
            self.man_indicators[name] = var

        # KI-Prognose Toggle
        self.man_prognose_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ind_frame, text="KI-Prognose", variable=self.man_prognose_var,
                       font=("Arial", 9, "bold"), fg_color="#e056fd", text_color="#e056fd",
                       height=20, width=20, checkbox_width=16, checkbox_height=16,
                       command=self._update_manuell_chart).pack(side="left", padx=8)

        # Grosser Chart (wie V4!)
        chart_frame = ctk.CTkFrame(self.tab_manuell, fg_color=CLR_CARD, corner_radius=12)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=3)

        self.man_fig, (self.man_ax_price, self.man_ax_vol) = plt.subplots(
            2, 1, figsize=(10, 4.5), dpi=85, gridspec_kw={"height_ratios": [4, 1]})
        self.man_fig.patch.set_facecolor(CLR_BG)
        self.man_ax_price.set_facecolor(CLR_BG)
        self.man_ax_vol.set_facecolor(CLR_BG)
        self.man_fig.subplots_adjust(left=0.06, right=0.94, top=0.95, bottom=0.08, hspace=0.05)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.man_canvas = FigureCanvasTkAgg(self.man_fig, master=chart_frame)
        self.man_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Status-Leiste unten
        status_bar = ctk.CTkFrame(self.tab_manuell, fg_color=CLR_CARD, corner_radius=8, height=28)
        status_bar.pack(fill="x", padx=10, pady=(0, 3))
        self.man_status_lbl = ctk.CTkLabel(status_bar, text="Lade...", font=("Consolas", 9), text_color="#888")
        self.man_status_lbl.pack(side="left", padx=10, pady=3)
        self.man_price_lbl = ctk.CTkLabel(status_bar, text="", font=("Arial", 11, "bold"), text_color=CLR_ACCENT)
        self.man_price_lbl.pack(side="right", padx=10, pady=3)
        self.man_balance_lbl = ctk.CTkLabel(status_bar, text="", font=("Arial", 10), text_color="#aaa")
        self.man_balance_lbl.pack(side="right", padx=10, pady=3)

        self.man_qty_var = ctk.StringVar(value="")

        # Chart-Update Thread (BUGFIX THREADING: Initial-Sleep)
        def _man_chart_tick():
            # Warte bis UI komplett aufgebaut ist (verhindert "main thread is not in main loop")
            import time as _t
            _t.sleep(3)
            while True:
                try:
                    self._update_manuell_chart()
                    # Preis + Balance updaten
                    coin = self.man_coin_var.get()
                    price = self.engine.data_agent.price_cache.get(coin, 0)
                    if price > 0:
                        self.after(0, lambda p=price: self.man_price_lbl.configure(text=f"{p:,.2f} $"))
                    bal = self.engine.execution.get_balance()
                    usdc = bal.get('total', {}).get('USDC', 0) + bal.get('total', {}).get('USDT', 0)
                    asset = coin.split("/")[0]
                    qty = bal.get('total', {}).get(asset, 0)
                    self.after(0, lambda u=usdc, q=qty, a=asset:
                        self.man_balance_lbl.configure(text=f"Balance: {u:.2f} USDC | {a}: {q:.6f}"))
                except Exception:
                    pass
                time.sleep(30)
        threading.Thread(target=_man_chart_tick, daemon=True).start()

    def _update_manuell_chart(self):
        """Zeichnet den grossen V4-style Chart mit Indikatoren."""
        try:
            import pandas as pd, pandas_ta as ta, numpy as np
            coin = self.man_coin_var.get()
            tf = self.man_tf_var.get()

            if not self._shared_client:
                import ccxt as _ccxt
                self._shared_client = _ccxt.binance({"enableRateLimit": True, "timeout": 15000})
            try:
                bars = self._shared_client.fetch_ohlcv(coin, tf, limit=200)
            except Exception:
                bars = self._shared_client.fetch_ohlcv(coin.replace("USDC", "USDT"), tf, limit=200)

            if not bars or len(bars) < 30:
                return

            df = pd.DataFrame(bars, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            df["EMA20"] = ta.ema(df["Close"], length=20)
            df["EMA50"] = ta.ema(df["Close"], length=50)
            df["RSI"] = ta.rsi(df["Close"], length=14)
            bb = ta.bbands(df["Close"], length=20, std=2)
            if bb is not None:
                df["BB_upper"] = bb.iloc[:, 0]
                df["BB_lower"] = bb.iloc[:, 2]
            m = ta.macd(df["Close"])
            if m is not None:
                df["MACD_val"] = m.iloc[:, 0]
                df["MACD_sig"] = m.iloc[:, 2]
            df["ADX_val"] = ta.adx(df["High"], df["Low"], df["Close"], length=14).iloc[:, 0] if len(df) > 14 else 20
            # VWAP
            tp = (df["High"] + df["Low"] + df["Close"]) / 3
            cum_vol = df["Volume"].cumsum()
            df["VWAP"] = (tp * df["Volume"]).cumsum() / cum_vol

            ax = self.man_ax_price
            ax2 = self.man_ax_vol
            ax.clear(); ax2.clear()
            ax.set_facecolor(CLR_BG); ax2.set_facecolor(CLR_BG)

            closes = df["Close"].values
            opens = df["Open"].values
            highs = df["High"].values
            lows = df["Low"].values
            x = range(len(df))

            # Kerzen zeichnen
            for i in range(len(df)):
                c = CLR_GREEN if closes[i] >= opens[i] else CLR_RED
                body_bottom = min(opens[i], closes[i])
                body_height = abs(closes[i] - opens[i])
                ax.bar(i, body_height, bottom=body_bottom, width=0.7, color=c, edgecolor=c, linewidth=0.3)
                ax.vlines(i, lows[i], highs[i], color=c, linewidth=0.3)

            # Indikatoren zeichnen
            ind = self.man_indicators
            if ind.get("EMA 20/50", ctk.BooleanVar()).get():
                ax.plot(x, df["EMA20"].values, color="#00d4ff", linewidth=1, alpha=0.8, label="EMA20")
                ax.plot(x, df["EMA50"].values, color="#ff9500", linewidth=1, alpha=0.8, label="EMA50")
            if ind.get("Bollinger", ctk.BooleanVar()).get() and "BB_upper" in df:
                ax.plot(x, df["BB_upper"].values, color="#888", linewidth=0.7, linestyle="--")
                ax.plot(x, df["BB_lower"].values, color="#888", linewidth=0.7, linestyle="--")
                ax.fill_between(x, df["BB_upper"].values, df["BB_lower"].values, alpha=0.05, color="#888")
            if ind.get("VWAP", ctk.BooleanVar()).get():
                ax.plot(x, df["VWAP"].values, color=CLR_CYAN, linewidth=0.8, linestyle="--", alpha=0.7)

            # Fibonacci Levels
            if ind.get("Fibonacci", ctk.BooleanVar()).get():
                swing_high = df["High"].max()
                swing_low = df["Low"].min()
                diff = swing_high - swing_low
                # Die 0 liegt am ENDE der Bewegung, die 1 an ihrem ANFANG. Welcher
                # Anker das Ende ist, entscheidet die ZEIT, nicht die Hoehe: kam das
                # Tief zuerst, ging es aufwaerts, und das Hoch ist das Ende.
                # Vorher stand hier fest "0.0": swing_low - das gilt nur abwaerts.
                # Aufwaerts waren dadurch 0,382 und 0,618 vertauscht (Befund 91).
                auf = int(df["Low"].values.argmin()) < int(df["High"].values.argmax())
                _fp = (lambda r: swing_high - diff*r) if auf else (lambda r: swing_low + diff*r)
                fib_levels = {"0.0": _fp(0.0), "0.382": _fp(0.382),
                              "0.5": _fp(0.5), "0.618": _fp(0.618),
                              "1.0": _fp(1.0), "1.272": _fp(1.272),
                              "1.618": _fp(1.618), "2.0": _fp(2.0)}
                fib_colors = {"0.0": "#00ff88", "0.382": "#00d4ff", "0.5": "#f1c40f",
                              "0.618": "#ff9500", "1.0": "#e056fd", "1.272": "#ff4655",
                              "1.618": "#ff4655", "2.0": "#ff0000"}
                for level, price in fib_levels.items():
                    if swing_low * 0.95 <= price <= swing_high * 1.1:
                        col = fib_colors.get(level, "#666")
                        ax.axhline(y=price, color=col, linewidth=0.5, linestyle="--", alpha=0.6)
                        ax.text(len(df)+1, price, f"{level} ({price:,.0f})", fontsize=6, color=col, va="center")

            # Volume
            if ind.get("Volume", ctk.BooleanVar()).get():
                vol_colors = [CLR_GREEN if closes[i] >= opens[i] else CLR_RED for i in range(len(df))]
                ax2.bar(x, df["Volume"].values, color=vol_colors, alpha=0.6, width=0.7)

            # KI-Prognose
            if self.man_prognose_var.get():
                self._draw_ki_prognose(ax, df, closes, x)

            # Buy/Sell Marker
            markers = self.engine._trade_markers.get(coin, [])
            bar_times = [b[0] for b in bars]
            for mk in markers:
                m_time_ms = mk.get("time", 0) * 1000
                for bi, bt in enumerate(bar_times):
                    if bt >= m_time_ms:
                        if mk["side"] == "BUY":
                            ax.scatter(bi, mk["price"], marker='^', color=CLR_GREEN, s=60, zorder=5)
                        else:
                            ax.scatter(bi, mk["price"], marker='v', color=CLR_RED, s=60, zorder=5)
                        break

            # Achsen formatieren
            ax.legend(fontsize=7, loc="upper left", facecolor=CLR_BG, edgecolor="#333", labelcolor="#aaa")
            for a in [ax, ax2]:
                a.tick_params(colors="#555", labelsize=7)
                a.spines["top"].set_visible(False); a.spines["right"].set_visible(False)
                a.spines["bottom"].set_color("#333"); a.spines["left"].set_color("#333")
            ax.set_xlim(-1, len(df) + 8)

            # Status
            last_rsi = df["RSI"].iloc[-1] if "RSI" in df else 50
            last_adx = df["ADX_val"].iloc[-1] if "ADX_val" in df else 20
            self.after(0, lambda c=coin, t=tf, p=closes[-1], r=last_rsi, a=last_adx:
                self.man_status_lbl.configure(
                    text=f"{c} | {t} | Preis: {p:,.2f}$ | RSI: {r:.0f} | ADX: {a:.0f} | {len(df)} Kerzen"))

            self.after(0, lambda: self.man_canvas.draw_idle())
        except Exception as e:
            _chart_err_msg = f"Chart-Fehler: {str(e)[:50]}"
            print(f"[UI] Manuell-Chart: {_chart_err_msg}")  # Echter Fehler im Log
            self.after(0, lambda msg=_chart_err_msg: self.man_status_lbl.configure(text=msg))

    def _draw_ki_prognose(self, ax, df, closes, x):
        """Zeichnet 30-Kerzen KI-Prognose in die Zukunft."""
        # === BUGFIX KI-PROGNOSE-PD: import pandas as pd ===
        import pandas as pd
        import numpy as np
        n = len(closes)
        future_n = 30
        future_x = range(n, n + future_n)

        last_price = closes[-1]
        last_rsi = df.get("RSI", pd.Series([50])).iloc[-1] if "RSI" in df else 50
        last_adx = df.get("ADX_val", pd.Series([20])).iloc[-1] if "ADX_val" in df else 20
        last_ema20 = df.get("EMA20", pd.Series([last_price])).iloc[-1] if "EMA20" in df else last_price
        last_ema50 = df.get("EMA50", pd.Series([last_price])).iloc[-1] if "EMA50" in df else last_price

        # Volatilitaet der letzten 20 Kerzen
        if n > 20:
            returns = np.diff(closes[-20:]) / closes[-21:-1]
            volatility = np.std(returns) if len(returns) > 0 else 0.005
            momentum = (closes[-1] / closes[-10] - 1) if n > 10 else 0
        else:
            volatility = 0.005
            momentum = 0

        # Trend-Richtung bestimmen
        if last_ema20 > last_ema50 and momentum > 0.005:
            trend = 1  # Aufwaerts
            trend_strength = min(momentum * 10, 0.3)
        elif last_ema20 < last_ema50 and momentum < -0.005:
            trend = -1  # Abwaerts
            trend_strength = max(momentum * 10, -0.3)
        else:
            trend = 0  # Seitwaerts
            trend_strength = 0

        # RSI-Korrektur: Overbought = Umkehr wahrscheinlich
        rsi_factor = 0
        if last_rsi > 70:
            rsi_factor = -0.15  # Wahrscheinlich Korrektur
        elif last_rsi < 30:
            rsi_factor = 0.15   # Wahrscheinlich Erholung

        # 3 Szenarien berechnen
        np.random.seed(42)
        noise = np.random.normal(0, volatility * 0.3, future_n)

        # Szenario 1: Trendfortsetzung (wahrscheinlichstes)
        trend_line = []
        price = last_price
        for i in range(future_n):
            change = (trend_strength / future_n) + (rsi_factor / future_n) + noise[i]
            price = price * (1 + change)
            trend_line.append(price)

        # Szenario 2: Optimistisch (obere Grenze)
        bull_line = []
        price = last_price
        for i in range(future_n):
            change = abs(trend_strength / future_n) + volatility * 0.5 / future_n + abs(noise[i]) * 0.5
            price = price * (1 + change)
            bull_line.append(price)

        # Szenario 3: Pessimistisch (untere Grenze)
        bear_line = []
        price = last_price
        for i in range(future_n):
            change = -abs(trend_strength / future_n) - volatility * 0.5 / future_n - abs(noise[i]) * 0.5
            price = price * (1 + change)
            bear_line.append(price)

        # Zeichnen
        # Verbindungslinie zum letzten echten Preis
        connect_x = [n-1] + list(future_x)
        connect_trend = [last_price] + trend_line
        connect_bull = [last_price] + bull_line
        connect_bear = [last_price] + bear_line

        # Hauptlinie (Trendfortsetzung)
        trend_color = CLR_GREEN if trend >= 0 else CLR_RED
        ax.plot(connect_x, connect_trend, color=trend_color, linewidth=2, linestyle="--", alpha=0.8)

        # Bandbreite (Bull/Bear Korridor)
        ax.fill_between(connect_x, connect_bull, connect_bear, alpha=0.08, color=trend_color)
        ax.plot(connect_x, connect_bull, color=CLR_GREEN, linewidth=0.7, linestyle=":", alpha=0.5)
        ax.plot(connect_x, connect_bear, color=CLR_RED, linewidth=0.7, linestyle=":", alpha=0.5)

        # Preis-Labels am Ende
        ax.text(n + future_n + 1, trend_line[-1], f"{trend_line[-1]:,.0f}",
                fontsize=7, color=trend_color, va="center", fontweight="bold")
        ax.text(n + future_n + 1, bull_line[-1], f"{bull_line[-1]:,.0f}",
                fontsize=6, color=CLR_GREEN, va="center", alpha=0.7)
        ax.text(n + future_n + 1, bear_line[-1], f"{bear_line[-1]:,.0f}",
                fontsize=6, color=CLR_RED, va="center", alpha=0.7)

        # Trend-Pfeil
        if trend != 0:
            mid = n + future_n // 2
            mid_price = trend_line[future_n // 2]
            arrow_dir = 1 if trend > 0 else -1
            ax.annotate("", xy=(mid, mid_price + last_price * 0.01 * arrow_dir),
                        xytext=(mid, mid_price - last_price * 0.005 * arrow_dir),
                        arrowprops=dict(arrowstyle="->", color=trend_color, lw=2.5))

        # Vertikale Trennlinie
        ax.axvline(x=n - 0.5, color="#444", linewidth=1, linestyle="-", alpha=0.5)

        # Info-Box
        trend_text = "AUFWAERTS" if trend > 0 else "ABWAERTS" if trend < 0 else "SEITWAERTS"
        pct_change = ((trend_line[-1] / last_price) - 1) * 100
        ax.text(0.75, 0.95, f"KI-PROGNOSE ({trend_text})", fontsize=8, color="#e056fd",
                transform=ax.transAxes, fontweight="bold", alpha=0.9)
        ax.text(0.75, 0.87, f"30 Kerzen: {pct_change:+.1f}%", fontsize=7,
                color=trend_color, transform=ax.transAxes, alpha=0.8)
        ax.text(0.75, 0.80, f"RSI:{last_rsi:.0f} ADX:{last_adx:.0f}", fontsize=7,
                color="#888", transform=ax.transAxes, alpha=0.7)

        # X-Achse erweitern fuer Prognose
        ax.set_xlim(-1, n + future_n + 8)

    def _man_log_msg(self, msg):
        self._add_log(f"[MANUELL] {msg}")

    # ==========================================================
    # ENTFERNT: _manual_buy() - Handkauf im Manuell-Reiter
    # [GEFUNDENE-PROBLEME #13, entfernt am 13.08.2026]
    # ==========================================================
    # Die Methode rief execution.execute(intent) DIREKT auf. Damit umging
    # sie nicht nur die Risikopruefung - das war der bekannte Teil -,
    # sondern auch die Positionsverwaltung. Die Belegkette:
    #
    #   1. execution/engine.py:165 execute() prueft Doppel-Order,
    #      Schlafmodus und Bargeld-Reservierung. KEINE Risikopruefung,
    #      und es veroeffentlicht KEIN EVENT_ORDER_FILLED.
    #   2. Eine Position wird ausschliesslich in app.py:1677-1692
    #      (_execute_approved_trade) in risk_engine.open_positions
    #      eingetragen. Diesen Weg nahm der Handkauf nicht.
    #   3. Der Stop-Waechter laeuft ueber genau diese Liste:
    #      runtime/exit_monitor.py:101.
    #
    # Ergebnis: Eine per Hand gekaufte Muenze stand in KEINER
    # Positionsliste. Kein Stop-Loss, kein Take-Profit, kein Trailing-
    # Stop, kein Trend-Ausstieg. Sie lag im Depot, und niemand schaute
    # sie an. Sie erschien auch nicht in evaluations, nicht im Journal
    # und nicht im Lernen - nur das Geld war aus der Kasse verschwunden.
    #
    # Zusaetzlich lief sie am Kill-Switch vorbei: ein Klick haette selbst
    # bei ausgeloestem Not-Aus gekauft.
    #
    # WARUM ENTFERNT STATT REPARIERT (Entscheidung Sven, 13.08.2026):
    # Der Knopf stammt aus der Anfangszeit des Projekts und wird nicht
    # gebraucht - kaufen laesst sich zur Not direkt an der Boerse. Im
    # Papiermodus ist ein Handkauf ohnehin nur eine Simulation. Ein
    # Kaufweg, den es nicht gibt, kann die Pruefung nicht umgehen; das
    # ist die stabilste Form der Regel "jede Order laeuft durch die
    # Risikopruefung".
    #
    # Der VERKAUFEN-Knopf bleibt bewusst bestehen. Ein Kaufweg ist ein
    # Risiko-Eingang, ein Verkaufsweg ist ein Sicherheitsventil - dieselbe
    # Logik, nach der risk/engine.py:81-86 Verkaeufe grundsaetzlich immer
    # genehmigt und der Schlafmodus seit dem 04.08. nur Kaeufe bremst.
    #
    # Mit entfernt: der KAUFEN-Knopf und das Betrag-Eingabefeld
    # (man_amount_var) im Manuell-Reiter, beide nur hierfuer da.

    # Anteil der Positionsmenge, ab dem ein Verkauf als "ganze Position"
    # gilt. Noetig, weil _manual_sell_all die Menge aus get_balance() nimmt
    # und die durch Rundung minimal unter pos["qty"] liegen kann - ohne
    # Toleranz wuerde der Not-Verkauf-alles-Knopf faelschlich als
    # Teilverkauf abgelehnt. [GEFUNDENE-PROBLEME #32]
    VERKAUF_GANZ_AB = 0.99

    def _manual_sell(self):
        """Manueller Verkauf - das Sicherheitsventil.

        [GEFUNDENE-PROBLEME #32, repariert am 13.08.2026]

        VORHER: Die Methode rief execution.execute(intent) DIREKT auf,
        genau wie der (inzwischen entfernte) Handkauf. Folge: Die Position
        wurde nicht aus risk_engine.open_positions ausgetragen - dort
        passiert das ausschliesslich ueber _execute_approved_trade, das
        am Ende risk_engine.record_result() aufruft und den Eintrag
        atomar loescht (siehe app.py:1590 ff.).

        Der Bot glaubte danach weiter, die Position sei offen: eine
        Geisterposition. Der Stop-Waechter (runtime/exit_monitor.py:101)
        lief weiter ueber sie und haette irgendwann versucht, etwas zu
        verkaufen, das es nicht mehr gibt. Ausserdem fehlte der Verkauf
        komplett in Journal, Telemetrie und Lernen, weil
        execution/engine.py kein EVENT_ORDER_FILLED veroeffentlicht.

        JETZT zwei klar getrennte Wege:

        Weg A - die Position ist beim Bot gebucht (Normalfall):
            Der Verkaufswunsch geht ueber bus.publish(EVENT_SIGNAL) und
            damit durch den normalen Pfad - genauso wie es _sell_coin()
            in dieser Datei schon immer richtig gemacht hat. Dann stimmen
            P&L, Journal, Telemetrie, Wiedereinstiegs-Sperre und Lernen,
            und die Position wird sauber ausgetragen.
            Die Risikopruefung blockiert das nicht: Verkaeufe werden
            grundsaetzlich immer genehmigt (risk/engine.py:81-86).

        Weg B - der Bestand ist dem Bot NICHT bekannt (Notfall):
            Verwaiste Restbestaende, Dust, Altbestaende aus der Zeit vor
            dieser Reparatur. Hier gibt es keine Position zum Austragen,
            also bleibt nur der Direktverkauf - aber MIT deutlichem
            Protokoll, damit er nicht unsichtbar bleibt.

        Teilverkauf einer gebuchten Position wird bewusst ABGELEHNT statt
        still anders ausgefuehrt: record_result() loescht die Position
        immer ganz, ein Teilverkauf ueber Weg A wuerde den Rest also aus
        der Buchhaltung werfen und genau die Geisterposition erzeugen,
        die hier gerade beseitigt wird.
        """
        from core.events import DecisionIntent, Side, EVENT_SIGNAL

        coin = self.man_coin_var.get()
        asset = coin.split("/")[0]
        qty_str = self.man_qty_var.get().strip()
        bal = self.engine.execution.get_balance()
        available = bal.get('total', {}).get(asset, 0)
        if qty_str:
            try:
                qty = float(qty_str)
            except ValueError:
                self._man_log_msg("Ungueltige Menge!"); return
        else:
            qty = available
        if qty <= 0:
            self._man_log_msg(f"Kein {asset} zum Verkaufen!"); return

        pos = self.engine.risk_engine.open_positions.get(coin) or {}
        gebucht = bool(pos.get("active")) and (pos.get("qty", 0) or 0) > 0
        preis = self.engine.data_agent.price_cache.get(coin, 0)

        # ---------- Weg A: gebuchte Position -> normaler Pfad ----------
        if gebucht:
            pos_qty = pos.get("qty", 0)
            if qty < pos_qty * self.VERKAUF_GANZ_AB:
                self._man_log_msg(
                    f"Teilverkauf abgelehnt: {coin} ist beim Bot mit "
                    f"{pos_qty:.6f} gebucht, angefragt {qty:.6f}. "
                    f"Die Buchhaltung kann Teilmengen noch nicht - sie "
                    f"wuerde die Restmenge verlieren. Mengenfeld leer "
                    f"lassen = ganze Position verkaufen.")
                self.man_status_lbl.configure(text="Teilverkauf abgelehnt",
                                              text_color=CLR_RED)
                return
            if preis <= 0:
                self._man_log_msg(f"Kein Preis fuer {coin} - Verkauf nicht "
                                  f"angefordert (Marktdaten fehlen).")
                self.man_status_lbl.configure(text="Kein Preis", text_color=CLR_RED)
                return
            try:
                intent = DecisionIntent(
                    symbol=coin, side=Side.SELL, confidence=1.0,
                    entry_price=preis, quantity=pos_qty,
                    strategy_id="MANUAL_SELL", entry_reason="Manuell verkauft",
                    score=10, agent_id="manual")
                self.engine.bus.publish(EVENT_SIGNAL, intent, source="manual")
                self._man_log_msg(
                    f"Verkauf angefordert: {coin} {pos_qty:.6f} @ "
                    f"{preis:,.2f}$ - laeuft ueber den normalen Pfad "
                    f"(Position wird ausgetragen, Journal + Telemetrie "
                    f"schreiben mit).")
                self.man_status_lbl.configure(text="Verkauf angefordert",
                                              text_color=CLR_ACCENT)
            except Exception as e:
                self._man_log_msg(f"FEHLER beim Anfordern: {e}")
                self.man_status_lbl.configure(text="Fehler", text_color=CLR_RED)
            return

        # ---------- Weg B: unbekannter Bestand -> Notverkauf ----------
        self._man_log_msg(
            f"NOTVERKAUF: {qty:.6f} {asset} - der Bot fuehrt zu {coin} "
            f"KEINE Position. Direktverkauf ohne Buchhaltung; taucht "
            f"nicht in P&L, Journal und Lernen auf.")
        self.man_status_lbl.configure(text="Notverkauf...", text_color=CLR_ACCENT)

        def _do():
            try:
                intent = DecisionIntent(
                    symbol=coin, side=Side.SELL, amount_usd=qty * preis,
                    quantity=qty, confidence=1.0, strategy_id="MANUAL_NOTVERKAUF",
                    entry_reason="Notverkauf: Bestand ohne gebuchte Position",
                    score=10)
                intent.entry_price = preis
                result = self.engine.execution.execute(intent)
                if result.status == "filled":
                    self.after(0, lambda: self._man_log_msg(
                        f"NOTVERKAUF {coin}: {result.filled_qty:.6f} @ "
                        f"{result.avg_fill_price:,.2f}$ = {result.filled_cost:.2f}$"))
                    self.after(0, lambda: self.man_status_lbl.configure(
                        text="Notverkauf ok", text_color=CLR_GREEN))
                else:
                    self.after(0, lambda: self._man_log_msg(
                        f"FEHLER: {result.rejected_reason or result.error}"))
                    self.after(0, lambda: self.man_status_lbl.configure(
                        text="Fehler", text_color=CLR_RED))
            except Exception as e:
                self.after(0, lambda: self._man_log_msg(f"FEHLER: {e}"))
                self.after(0, lambda: self.man_status_lbl.configure(
                    text="Fehler", text_color=CLR_RED))
        threading.Thread(target=_do, daemon=True).start()

    def _manual_sell_all(self):
        """Not-Knopf: alles verkaufen.

        [GEFUNDENE-PROBLEME #32, 13.08.2026] Ruft _manual_sell() je Asset
        auf und profitiert damit automatisch von dessen Reparatur: gebuchte
        Positionen laufen jetzt ueber den normalen Pfad und werden sauber
        ausgetragen, unbekannte Bestaende gehen als protokollierter
        Notverkauf raus. Die Mengen stammen aus get_balance() und koennen
        durch Rundung minimal unter pos["qty"] liegen - dafuer gibt es die
        Toleranz VERKAUF_GANZ_AB, sonst wuerde dieser Knopf faelschlich als
        Teilverkauf abgelehnt.
        """
        self._man_log_msg("Verkaufe ALLE Positionen...")
        bal = self.engine.execution.get_balance()
        for asset, qty in bal.get('total', {}).items():
            if qty > 0 and asset not in ('USDC', 'USDT', 'USD'):
                coin = f"{asset}/USDC"
                self.man_coin_var.set(coin)
                self.man_qty_var.set(str(qty))
                self._manual_sell()
                time.sleep(0.5)

    # ==========================================================
    # BTC TAB – Akkumulations-Uebersicht
    # ==========================================================
    def _build_btc_tab(self):
        # Oben: BTC Stats
        stats = ctk.CTkFrame(self.tab_btc, fg_color=CLR_CARD, corner_radius=12)
        stats.pack(fill="x", padx=10, pady=5)

        stats_row = ctk.CTkFrame(stats, fg_color="transparent")
        stats_row.pack(fill="x", padx=12, pady=8)

        self.btc_stat_labels = {}
        for name, key, color in [("₿ BTC GESAMT", "total", CLR_ORANGE),
                                  ("INVESTIERT", "invested", "#fff"),
                                  ("AKTUELLER WERT", "value", CLR_GREEN),
                                  ("P&L", "pnl", CLR_GREEN),
                                  ("Ø PREIS", "avg", CLR_CYAN),
                                  ("KAEUFE", "count", "#aaa")]:
            card = ctk.CTkFrame(stats_row, fg_color="#1a1a20", corner_radius=8)
            card.pack(side="left", expand=True, fill="x", padx=3, ipady=4)
            ctk.CTkLabel(card, text=name, font=("Arial", 8), text_color="#666").pack(pady=(4, 0))
            lbl = ctk.CTkLabel(card, text="–", font=("Arial", 14, "bold"), text_color=color)
            lbl.pack(pady=(0, 4))
            self.btc_stat_labels[key] = lbl

        # Sparplan-Status
        sp = ctk.CTkFrame(self.tab_btc, fg_color=CLR_CARD, corner_radius=12)
        sp.pack(fill="x", padx=10, pady=5)
        sp_row = ctk.CTkFrame(sp, fg_color="transparent")
        sp_row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(sp_row, text="₿ DCA-SPARPLAN", font=("Arial", 12, "bold"),
                     text_color=CLR_ACCENT).pack(side="left")
        self.btc_sparplan_lbl = ctk.CTkLabel(sp_row, text="Status: –", font=("Arial", 11),
                                              text_color="#aaa")
        self.btc_sparplan_lbl.pack(side="left", padx=15)

        # Kauf-History
        self.btc_history_text = ctk.CTkTextbox(self.tab_btc, fg_color="#0d0d0f",
                                                font=("Consolas", 10), text_color="#ccc", height=100)
        self.btc_history_text.pack(fill="x", padx=10, pady=5)
        self.btc_history_text.insert("end", "BTC-Akkumulations-History wird geladen...\n")
        self.btc_history_text.configure(state="disabled")

        # Equity-Kurve Chart
        eq_frame = ctk.CTkFrame(self.tab_btc, fg_color=CLR_CARD, corner_radius=12)
        eq_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(eq_frame, text="📈 VERMOEGENSVERLAUF", font=("Arial", 12, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 2))
        self.equity_fig, self.equity_ax = plt.subplots(figsize=(8, 2.2), dpi=80)
        self.equity_fig.patch.set_facecolor(CLR_CARD)
        self.equity_ax.set_facecolor(CLR_CARD)
        self.equity_fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.15)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.equity_canvas = FigureCanvasTkAgg(self.equity_fig, master=eq_frame)
        self.equity_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(0, 6))
        self.equity_history = []

        # Update-Thread
        def _btc_tick():
            while True:
                try:
                    self._update_btc_tab()
                except Exception:
                    pass
                time.sleep(10)
        threading.Thread(target=_btc_tick, daemon=True).start()

    def _update_btc_tab(self):
        acc = self.engine.btc_accumulator
        btc_price = self.engine.data_agent.price_cache.get("BTC/USDC", 0) or \
                    self.engine.data_agent.price_cache.get("BTC/USDT", 0)
        pnl_data = acc.get_pnl(btc_price)

        self.after(0, lambda: self.btc_stat_labels["total"].configure(text=f"{pnl_data['total_btc']:.8f}"))
        self.after(0, lambda: self.btc_stat_labels["invested"].configure(text=f"{pnl_data['invested']:,.2f}$"))
        val = pnl_data['current_value']
        self.after(0, lambda: self.btc_stat_labels["value"].configure(text=f"{val:,.2f}$"))
        pnl = pnl_data['pnl']
        pnl_color = CLR_GREEN if pnl >= 0 else CLR_RED
        self.after(0, lambda: self.btc_stat_labels["pnl"].configure(
            text=f"{pnl:+,.2f}$ ({pnl_data['pnl_pct']:+.1f}%)", text_color=pnl_color))
        self.after(0, lambda: self.btc_stat_labels["avg"].configure(text=f"{pnl_data['avg_price']:,.2f}$"))
        self.after(0, lambda: self.btc_stat_labels["count"].configure(text=f"{pnl_data['purchases']}"))

        # Sparplan Status
        status = acc.get_status()
        sp_text = f"{'AN' if status['sparplan_active'] else 'AUS'} | {status['sparplan_pct']}% alle 60min | Gewinn-Puffer: {status['unrealized_profit']:.2f}$"
        self.after(0, lambda: self.btc_sparplan_lbl.configure(text=sp_text))

        # History
        history = acc.get_history_text()
        self.after(0, lambda: self._btc_update_history(history))

        # Equity-Kurve updaten
        try:
            bal = self.engine.execution.get_balance()
            usdc = bal["total"].get("USDC", 0) + bal["total"].get("USDT", 0)
            # Alle Coin-Werte addieren
            total_value = usdc
            for coin, price in self.engine.data_agent.price_cache.items():
                asset = coin.split("/")[0]
                qty = bal["total"].get(asset, 0)
                total_value += qty * price
            total_value += val  # BTC Akkumulation

            self.equity_history.append(total_value)
            if len(self.equity_history) > 500:
                self.equity_history = self.equity_history[-500:]

            if len(self.equity_history) > 2:
                self.after(0, self._draw_equity_curve)
        except Exception:
            pass

    def _draw_equity_curve(self):
        """Zeichnet die Equity-Kurve."""
        try:
            ax = self.equity_ax
            ax.clear()
            ax.set_facecolor(CLR_CARD)

            data = self.equity_history
            x = list(range(len(data)))
            start_val = data[0]
            current = data[-1]

            color = CLR_GREEN if current >= start_val else CLR_RED
            ax.plot(x, data, color=color, linewidth=1.5)
            ax.fill_between(x, data, min(data) * 0.99, color=color, alpha=0.1)

            # Start-Linie
            ax.axhline(y=start_val, color="#444", linewidth=0.5, linestyle="--")

            # Beschriftung
            pnl_pct = ((current / start_val) - 1) * 100 if start_val > 0 else 0
            ax.text(0.02, 0.88, f"Gesamt: {current:,.0f}$ ({pnl_pct:+.1f}%)",
                    fontsize=9, color=color, transform=ax.transAxes)
            ax.text(0.02, 0.72, f"Start: {start_val:,.0f}$",
                    fontsize=8, color="#666", transform=ax.transAxes)

            ax.tick_params(colors="#555", labelsize=7)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color("#333")
            ax.spines["left"].set_color("#333")
            self.equity_canvas.draw_idle()
        except Exception:
            pass

    def _btc_update_history(self, text):
        self.btc_history_text.configure(state="normal")
        self.btc_history_text.delete("1.0", "end")
        self.btc_history_text.insert("end", text)
        self.btc_history_text.configure(state="disabled")

    # ==========================================================
    # HISTORY TAB – Trade-Verlauf
    # ==========================================================
    def _build_history_tab(self):
        # Controls
        ctrl = ctk.CTkFrame(self.tab_history, fg_color=CLR_CARD, corner_radius=12)
        ctrl.pack(fill="x", padx=10, pady=5)
        ctrl_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(ctrl_row, text="📜 TRADE-HISTORY", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(side="left")

        ctk.CTkButton(ctrl_row, text="🔄 Aktualisieren", font=("Arial", 11),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER,
                      width=120, command=self._refresh_history).pack(side="right", padx=4)

        ctk.CTkButton(ctrl_row, text="💾 Export TXT", font=("Arial", 11),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER,
                      width=120, command=self._export_history).pack(side="right", padx=4)

        ctk.CTkButton(ctrl_row, text="📊 Analyse Export", font=("Arial", 11),
                      fg_color=CLR_CARD, border_width=1, border_color=CLR_BORDER,
                      width=130, command=self._export_analyse).pack(side="right", padx=4)

        self.hist_filter_var = ctk.StringVar(value="Alle")
        ctk.CTkOptionMenu(ctrl_row, variable=self.hist_filter_var, width=100,
                          values=["Alle", "BUY", "SELL", "Gewinn", "Verlust"],
                          fg_color="#0d0d0f", command=lambda _: self._refresh_history
                          ).pack(side="right", padx=4)

        # Stats-Zeile
        stats_frame = ctk.CTkFrame(self.tab_history, fg_color=CLR_CARD, corner_radius=12)
        stats_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.hist_stats_lbl = ctk.CTkLabel(stats_frame, text="Trades: – | P&L: – | Win-Rate: –",
                                            font=("Arial", 11), text_color="#aaa")
        self.hist_stats_lbl.pack(pady=6, padx=12)

        # Trade-Liste
        self.hist_text = ctk.CTkTextbox(self.tab_history, fg_color="#0d0d0f",
                                         font=("Consolas", 10), text_color="#ccc")
        self.hist_text.pack(expand=True, fill="both", padx=10, pady=5)
        self.hist_text.insert("end", "Druecke 'Aktualisieren' oder starte den Bot um Trades zu sehen.\n")
        self.hist_text.configure(state="disabled")

        # Auto-Update
        def _hist_tick():
            while True:
                try:
                    self._refresh_history()
                except Exception:
                    pass
                time.sleep(15)
        threading.Thread(target=_hist_tick, daemon=True).start()

    def _refresh_history(self):
        # Nur Journal verwenden (keine Duplikate!)
        all_trades = self.engine.journal.get_all() if hasattr(self.engine, 'journal') else []

        # Filter
        filt = self.hist_filter_var.get()
        if filt == "BUY":
            all_trades = [t for t in all_trades if t.get("type", t.get("side", "")) in ("BUY", "buy")]
        elif filt == "SELL":
            all_trades = [t for t in all_trades if t.get("type", t.get("side", "")) in ("SELL", "sell")]
        elif filt == "Gewinn":
            all_trades = [t for t in all_trades if (t.get("pnl") or 0) > 0]
        elif filt == "Verlust":
            all_trades = [t for t in all_trades if (t.get("pnl") or 0) < 0]

        # Stats
        sells = [t for t in all_trades if t.get("type", t.get("side", "")) in ("SELL", "sell")]
        total_pnl = sum((t.get("pnl") or 0) for t in sells if isinstance(t.get("pnl"), (int, float)))
        wins = sum(1 for t in sells if (t.get("pnl") or 0) > 0)
        wr = (wins / len(sells) * 100) if sells else 0
        stats_text = f"Trades: {len(all_trades)} | Sells: {len(sells)} | P&L: {total_pnl:+.2f}$ | Win-Rate: {wr:.0f}%"
        self.after(0, lambda: self.hist_stats_lbl.configure(text=stats_text))

        # Tabelle
        lines = [f"{'Zeit':<22}{'Typ':<8}{'Coin':<12}{'Menge':>12}{'Preis':>12}{'Betrag':>10}{'P&L':>10}{'Strategie':<15}",
                 "─" * 105]
        for t in reversed(all_trades[-50:]):
            _raw_ts = str(t.get("time", t.get("created_at", "")))
            try:
                from datetime import timezone as _tz
                _dt = datetime.fromisoformat(_raw_ts)
                if _dt.tzinfo is None:
                    _dt = _dt.replace(tzinfo=_tz.utc)
                ts = _dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts = _raw_ts[:19].replace("T", " ")
            typ = t.get("type", t.get("side", "?"))[:6]
            coin = t.get("coin", t.get("symbol", "?"))
            if "/" in coin:
                coin = coin.split("/")[0]
            qty = t.get("qty", t.get("fill_qty", 0))
            price = t.get("price", t.get("fill_price", 0))
            amount = t.get("amount", t.get("fill_cost", 0) if t.get("fill_cost") else 0)
            pnl = t.get("pnl", "")
            pnl_s = f"{pnl:+.2f}$" if isinstance(pnl, (int, float)) and pnl != 0 else ""
            strat = t.get("strategy", t.get("strategy_id", ""))[:14]
            lines.append(f"{ts:<22}{typ:<8}{coin:<12}{qty:>12.6f}{price:>11,.2f}${amount:>9,.2f}${pnl_s:>10}{strat:<15}")

        if not all_trades:
            lines.append("\n  Noch keine Trades. Starte den Bot oder mache einen manuellen Trade.")

        text = "\n".join(lines)
        self.after(0, lambda: self._hist_update_text(text))

    def _hist_update_text(self, text):
        self.hist_text.configure(state="normal")
        self.hist_text.delete("1.0", "end")
        self.hist_text.insert("end", text)
        self.hist_text.configure(state="disabled")

    def _export_history(self):
        try:
            import os
            trades = self.engine.execution.order_manager.get_history(500)
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_export.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"TRADING IMPERIUM V7 – Trade Export\n")
                f.write(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                for t in trades:
                    f.write(f"{t.get('created_at', '?')} | {t.get('side', '?')} {t.get('symbol', '?')} | "
                           f"Qty: {t.get('fill_qty', 0):.6f} @ {t.get('fill_price', 0):,.2f}$ | "
                           f"Fee: {t.get('fee', 0):.4f}\n")
            self._man_log_msg(f"Export gespeichert: {path}")
            self._add_log(f"💾 Trade-Export: {path}")
        except Exception as e:
            self._add_log(f"Export-Fehler: {e}")

    def _export_analyse(self):
        """Exportiert Analyse wie V4."""
        try:
            import os
            from datetime import datetime
            text = self.engine.generate_analyse_export()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", f"imperium_analyse_{ts}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._add_log(f"📊 Analyse-Export: {path}")
        except Exception as e:
            self._add_log(f"Analyse-Export Fehler: {e}")

    # ==========================================================
    # AGENTS TAB – Zeigt Status aller Agenten
    # ==========================================================
    def _build_agents_tab(self):
        # Datenfluss-Erklärung
        flow = ctk.CTkFrame(self.tab_agents, fg_color=CLR_CARD, corner_radius=12)
        flow.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(flow, text="🔄 DATENFLUSS: Marktdaten → Signal-Agent → Risk-Agent → Portfolio-Agent → Execution",
                     font=("Arial", 11, "bold"), text_color=CLR_ACCENT).pack(pady=8, padx=10)

        # Agent-Status-Karten (scrollbar fuer 20 Agenten)
        agents_frame = ctk.CTkScrollableFrame(self.tab_agents, fg_color="transparent")
        agents_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.agent_labels = {}
        agents = [
            ("📊 Data Agent", "data", "Holt Marktdaten + Indikatoren"),
            ("🧠 Strategy Brain", "brain", "Waehlt beste Strategie je Marktlage"),
            ("🎯 Signal Agent", "signal", "Multi-Signal Scoring + Ensemble"),
            ("🔄 Zyklustheorie", "cycle", "BTC 4-Jahres-Zyklus Erkennung"),
            ("🛡️ Risk Agent", "risk", "Veto-Recht + Kill-Switch + Drawdown"),
            ("📋 Portfolio Agent", "portfolio", "Kapitalverteilung + Anti-Klumpen"),
            ("⚡ Execution Engine", "execution", "Orders mit Retry + TWAP Split"),
            ("🌐 LLM Agent", "context", "News + Trade-Erklaerungen (Ollama)"),
            ("📱 Telegram", "telegram", "Alerts + Tages-/Wochenberichte"),
            ("₿ BTC Akkumulator", "btc_acc", "Sparplan + Auto-BTC aus Gewinnen"),
            ("📈 Regime Detector", "regime", "Bull/Bear/Sideways/Volatile"),
            ("📊 Multi-Timeframe", "mtf", "5m+15m+1h+4h Confluence"),
            ("🏛️ Capitol Trades", "capitol", "US-Politiker Trade-Tracking"),
            ("💰 Funding Rates", "funding", "Binance Futures Sentiment"),
            ("🐋 Whale Alerts", "whale", "Grosse On-Chain Transaktionen"),
            ("🤖 RL Feedback", "rl", "Q-Learning Strategie-Gewichtung"),
            ("📐 Grid Trader", "grid", "Grid-Trading fuer Seitwaerts"),
            ("⏱️ Smart Entry", "smart", "Wartet auf Pullback"),
            ("🔀 Arbitrage", "arb", "Cross-Exchange Preisunterschiede"),
            ("📏 Adaptive Sizing", "adaptive", "KI-Position Sizing"),
        ]

        for i, (name, key, desc) in enumerate(agents):
            row = i // 2
            col = i % 2
            card = ctk.CTkFrame(agents_frame, fg_color=CLR_CARD, corner_radius=12,
                                border_width=1, border_color=CLR_BORDER)
            card.grid(row=row, column=col, padx=5, pady=4, sticky="nsew")
            agents_frame.grid_columnconfigure(col, weight=1)

            ctk.CTkLabel(card, text=name, font=("Arial", 13, "bold"),
                         text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(card, text=desc, font=("Arial", 10),
                         text_color="#888").pack(anchor="w", padx=12, pady=(0, 2))

            status = ctk.CTkLabel(card, text="⏳ Warte...", font=("Arial", 10, "bold"),
                                  text_color="#555")
            status.pack(anchor="w", padx=12, pady=(0, 8))
            self.agent_labels[key] = status

    # ==========================================================
    # SETTINGS TAB
    # ==========================================================
    def _build_settings_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # Exchange Settings
        ex_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        ex_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(ex_frame, text="🔑 EXCHANGE API", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

        row1 = ctk.CTkFrame(ex_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row1, text="API Key:", width=100, text_color="#aaa").pack(side="left")
        self.api_key_entry = ctk.CTkEntry(row1, width=400, show="*", fg_color="#0d0d0f")
        self.api_key_entry.pack(side="left", padx=5)
        self.api_key_entry.insert(0, self.engine.config.exchange.api_key)

        row2 = ctk.CTkFrame(ex_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row2, text="API Secret:", width=100, text_color="#aaa").pack(side="left")
        self.api_secret_entry = ctk.CTkEntry(row2, width=400, show="*", fg_color="#0d0d0f")
        self.api_secret_entry.pack(side="left", padx=5)
        self.api_secret_entry.insert(0, self.engine.config.exchange.api_secret)

        row3 = ctk.CTkFrame(ex_frame, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(row3, text="Modus:", width=100, text_color="#aaa").pack(side="left")
        self.mode_var = ctk.StringVar(value=self.engine.config.trading.mode)
        ctk.CTkSegmentedButton(row3, values=["paper", "live"], variable=self.mode_var,
                               fg_color=CLR_CARD, selected_color=CLR_ACCENT,
                               selected_hover_color="#d4a017").pack(side="left", padx=5)

        # === STARTKAPITAL ===
        bal_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        bal_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(bal_frame, text="💰 STARTKAPITAL", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

        bal_row = ctk.CTkFrame(bal_frame, fg_color="transparent")
        bal_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(bal_row, text="Paper-Balance (USDC):", width=160, text_color="#aaa").pack(side="left")
        self.balance_var = ctk.StringVar(value=str(self.engine.config.trading.initial_paper_balance))
        ctk.CTkEntry(bal_row, textvariable=self.balance_var, width=100, fg_color="#0d0d0f",
                     font=("Arial", 12, "bold")).pack(side="left", padx=5)
        ctk.CTkButton(bal_row, text="Empfehlung zeigen", font=("Arial", 10),
                      width=130, height=26, fg_color="#333",
                      command=self._show_balance_recommendation).pack(side="left", padx=10)

        self.balance_recommendation_lbl = ctk.CTkLabel(bal_frame, text="", font=("Consolas", 10),
            text_color="#aaa", justify="left")
        self.balance_recommendation_lbl.pack(anchor="w", padx=12, pady=(0, 8))
        self._update_balance_recommendation()

        # Risk Settings
        risk_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        risk_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(risk_frame, text="🛡️ RISIKO", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

        self.risk_vars = {}
        risk_items = [
            ("Max Tages-Verlust $", "max_daily_loss", self.engine.config.risk.max_daily_loss_usd),
            ("Max Positionen", "max_positions", self.engine.config.risk.max_open_positions),
            ("Stop-Loss %", "stop_loss", self.engine.config.risk.stop_loss_pct),
            ("Trailing-Stop %", "trailing", self.engine.config.risk.trailing_stop_pct),
            ("Position Size %", "pos_size", self.engine.config.trading.position_size_pct),
        ]
        for label, key, default in risk_items:
            row = ctk.CTkFrame(risk_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)
            ctk.CTkLabel(row, text=f"{label}:", width=160, text_color="#aaa").pack(side="left")
            var = ctk.StringVar(value=str(default))
            ctk.CTkEntry(row, textvariable=var, width=80, fg_color="#0d0d0f").pack(side="left", padx=5)
            self.risk_vars[key] = var

        # === BUGFIX REBALANCER-UI: Portfolio Rebalancer Section ===
        rb_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        rb_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(rb_frame, text="⚖️ PORTFOLIO REBALANCER",
                     font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
        # Status-Zeile
        rb_status_row = ctk.CTkFrame(rb_frame, fg_color="transparent")
        rb_status_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(rb_status_row, text="Status:", width=80,
                     text_color="#aaa").pack(side="left")
        # Aktuellen Status abfragen
        _rb_obj = getattr(self.engine, "portfolio_rebalancer", None) or getattr(self.engine, "rebalancer", None)
        # === REBAL-PERSIST: gespeicherten Zustand wiederherstellen ===
        if _rb_obj is not None:
            try:
                import json as _json, os as _os
                _rb_state_file = _os.path.join("data_store", "rebalancer_state.json")
                if _os.path.exists(_rb_state_file):
                    with open(_rb_state_file, "r", encoding="utf-8") as _f:
                        _saved = _json.load(_f)
                    _rb_obj.enabled = bool(_saved.get("enabled", False))
                    _rb_obj.dry_run = bool(_saved.get("dry_run", True))
                    from core.logger import log as _rblog
                    _rblog.info("REBAL", "Zustand wiederhergestellt: enabled=" + str(_rb_obj.enabled) + ", dry_run=" + str(_rb_obj.dry_run))
            except Exception:
                pass
        _rb_enabled = bool(getattr(_rb_obj, "enabled", False)) if _rb_obj else False
        _rb_dry = bool(getattr(_rb_obj, "dry_run", True)) if _rb_obj else True
        self.rb_status_lbl = ctk.CTkLabel(
            rb_status_row,
            text=("AKTIV" if _rb_enabled else "DEAKTIVIERT") + (" (DRY-RUN)" if _rb_dry else ""),
            font=("Arial", 11, "bold"),
            text_color=(CLR_GREEN if _rb_enabled else "#888"))
        self.rb_status_lbl.pack(side="left", padx=8)
        # Allokations-Anzeige
        _target = getattr(_rb_obj, "target_alloc", {"BTC":55,"ETH":15,"SOL":10,"XRP":10,"alts":10}) if _rb_obj else {"BTC":55,"ETH":15,"SOL":10,"XRP":10,"alts":10}
        _alloc_txt = "Ziel: " + " / ".join(f"{k} {v}%" for k, v in _target.items())
        ctk.CTkLabel(rb_frame, text=_alloc_txt, font=("Consolas", 10),
                     text_color="#888").pack(anchor="w", padx=12, pady=(0, 4))
        ctk.CTkLabel(rb_frame, text="Schwelle: 5% Abweichung | Mindest-Cooldown: 6h",
                     font=("Consolas", 9), text_color="#666").pack(anchor="w", padx=12, pady=(0, 4))
        # Buttons
        rb_btn_row = ctk.CTkFrame(rb_frame, fg_color="transparent")
        rb_btn_row.pack(fill="x", padx=12, pady=(4, 8))
        self.rb_enable_btn = ctk.CTkButton(
            rb_btn_row,
            text=("DEAKTIVIEREN" if _rb_enabled else "AKTIVIEREN"),
            font=("Arial", 11, "bold"),
            width=140, height=34,
            fg_color=(CLR_RED if _rb_enabled else CLR_GREEN),
            hover_color=("#a02030" if _rb_enabled else "#1a8a44"),
            command=self._rb_toggle)
        self.rb_enable_btn.pack(side="left", padx=4)
        ctk.CTkButton(rb_btn_row, text="Dry-Run jetzt", font=("Arial", 11),
                      width=140, height=34, fg_color="#444",
                      hover_color="#555",
                      command=self._rb_dry_run_check).pack(side="left", padx=4)
        ctk.CTkButton(rb_btn_row, text="Status anzeigen", font=("Arial", 11),
                      width=140, height=34, fg_color="#333",
                      hover_color="#444",
                      command=self._rb_show_status).pack(side="left", padx=4)
        # Output-Label
        self.rb_output_lbl = ctk.CTkLabel(
            rb_frame, text="",
            font=("Consolas", 10),
            text_color="#aaa", justify="left", wraplength=720)
        self.rb_output_lbl.pack(anchor="w", padx=12, pady=(0, 8))

        # === SENSEI-MODE: Trading-Lehrer Section ===
        sm_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        sm_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(sm_frame, text="🥋 SENSEI-MODE",
                     font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(sm_frame,
                     text="Dein Trading-Lehrer: erklaert Signale in Klartext und "
                          "zieht Lektionen aus abgeschlossenen Trades.",
                     font=("Consolas", 10), text_color="#888",
                     wraplength=720, justify="left").pack(anchor="w", padx=12, pady=(0, 4))
        sm_btn_row = ctk.CTkFrame(sm_frame, fg_color="transparent")
        sm_btn_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkButton(sm_btn_row, text="Letzte Signale erklaeren",
                      font=("Arial", 11, "bold"), width=180, height=34,
                      fg_color="#2b6cb0", hover_color="#2c5282",
                      command=self._sensei_explain).pack(side="left", padx=4)
        ctk.CTkButton(sm_btn_row, text="Tages-Lektion erzeugen",
                      font=("Arial", 11, "bold"), width=180, height=34,
                      fg_color="#6b46c1", hover_color="#553c9a",
                      command=self._sensei_lesson).pack(side="left", padx=4)
        ctk.CTkButton(sm_btn_row, text="Trading-Akademie",
                      font=("Arial", 11, "bold"), width=180, height=34,
                      fg_color="#2f855a", hover_color="#276749",
                      command=self._open_akademie).pack(side="left", padx=4)
        self.sm_output = ctk.CTkTextbox(sm_frame, height=220,
                                        font=("Consolas", 11),
                                        fg_color="#0d0d0f", text_color="#ddd",
                                        wrap="word")
        self.sm_output.pack(fill="x", padx=12, pady=(0, 10))
        self.sm_output.insert("1.0", "Sensei bereit. Druecke einen der Knoepfe oben.")
        self.sm_output.configure(state="disabled")

        # Telegram Settings
        tg_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        tg_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(tg_frame, text="📱 TELEGRAM", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

        row_t = ctk.CTkFrame(tg_frame, fg_color="transparent")
        row_t.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(row_t, text="Token:", width=100, text_color="#aaa").pack(side="left")
        self.tg_token_entry = ctk.CTkEntry(row_t, width=400, fg_color="#0d0d0f")
        self.tg_token_entry.pack(side="left", padx=5)
        self.tg_token_entry.insert(0, self.engine.config.telegram.token)

        row_c = ctk.CTkFrame(tg_frame, fg_color="transparent")
        row_c.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(row_c, text="Chat-ID:", width=100, text_color="#aaa").pack(side="left")
        self.tg_chat_entry = ctk.CTkEntry(row_c, width=200, fg_color="#0d0d0f")
        self.tg_chat_entry.pack(side="left", padx=5)
        self.tg_chat_entry.insert(0, self.engine.config.telegram.chat_id)

        # BTC Sparplan Settings
        sp_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        sp_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(sp_frame, text="₿ BTC SPARPLAN", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

        sp_row1 = ctk.CTkFrame(sp_frame, fg_color="transparent")
        sp_row1.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(sp_row1, text="Sparplan aktiv:", width=160, text_color="#aaa").pack(side="left")
        self.sparplan_var = ctk.BooleanVar(value=self.engine.config.trading.btc_dca_enabled)
        ctk.CTkSwitch(sp_row1, variable=self.sparplan_var, text="AN / AUS",
                      onvalue=True, offvalue=False, fg_color="#333",
                      progress_color=CLR_GREEN).pack(side="left", padx=5)

        sp_row2 = ctk.CTkFrame(sp_frame, fg_color="transparent")
        sp_row2.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(sp_row2, text="DCA Anteil %:", width=160, text_color="#aaa").pack(side="left")
        self.sparplan_pct_var = ctk.StringVar(value=str(self.engine.config.trading.btc_dca_pct))
        ctk.CTkEntry(sp_row2, textvariable=self.sparplan_pct_var, width=80, fg_color="#0d0d0f").pack(side="left", padx=5)
        ctk.CTkLabel(sp_row2, text="(33 = 1/3 Regel)", text_color="#555").pack(side="left", padx=5)

        sp_row3 = ctk.CTkFrame(sp_frame, fg_color="transparent")
        sp_row3.pack(fill="x", padx=12, pady=(2, 8))
        ctk.CTkLabel(sp_row3, text="Intervall (Min):", width=160, text_color="#aaa").pack(side="left")
        self.sparplan_interval_var = ctk.StringVar(value=str(self.engine.config.trading.btc_dca_interval_min))
        ctk.CTkEntry(sp_row3, textvariable=self.sparplan_interval_var, width=80, fg_color="#0d0d0f").pack(side="left", padx=5)

        # Save Button
        ctk.CTkButton(scroll, text="💾 EINSTELLUNGEN SPEICHERN", font=("Arial", 13, "bold"),
                      fg_color=CLR_ACCENT, text_color="#000", hover_color="#d4a017",
                      height=40, command=self._save_settings).pack(fill="x", pady=10)

        # ============================================================
        # [ENTFERNT 11.08.2026 - Freigabe des Eigentuemers, Variante A]
        #
        # Hier stand ein Schiebeschalter "Auto-Optimizer (alle 30 Min)"
        # mit der Beschriftung "Findet automatisch die besten SL/Trail/Pos
        # Parameter". Ein Klick genuegte.
        #
        # WAS ER GETAN HAETTE (app.py:2644 _auto_optimize):
        # Alle 30 Minuten 27 Kombinationen aus Stop-Loss, Trailing und
        # Positionsgroesse auf 300 BTC-Stundenkerzen (rund 12 Tage)
        # durchprobieren, die beste nehmen und per config.save()
        # DAUERHAFT in die Konfiguration schreiben (app.py:2669-2672).
        #
        # WARUM ER WEG IST:
        # Das waehlt nicht die Regel, die funktioniert, sondern die, die
        # auf zwoelf zufaelligen Tagen am besten aussah - Overfitting im
        # Reinformat und ein Verstoss gegen Regel 5 des Projekts
        # ("nicht drehen, bis die Zahlen gefallen"). Es fehlte zudem jede
        # Sicherung aus Regel 6: keine harten Grenzen, keine
        # Mindestdatenmenge, keine Sperrfrist, keine Protokollierung ausser
        # einer Logzeile. Stuende der Stop-Loss morgen auf 5 % statt 2 %,
        # waere nicht mehr feststellbar warum.
        #
        # Das Projekt hat am 07.08. gemessen, dass 70 % Trefferquote nach
        # Kosten ein Verlustgeschaeft sein koennen. Ein Automat, der genau
        # solche Zahlen jagt, ist das Gegenteil der Lehre daraus.
        #
        # Der Schalter war freundlich beschriftet - man sah ihm nicht an,
        # was er anrichtet. Genau deshalb der Knopf und nicht nur ein
        # Warnhinweis.
        #
        # Der Code in app.py bleibt liegen (auto_optimize_enabled = False,
        # app.py:603). Wer ihn wieder will, baut ihn nach dem Vorbild von
        # features/regime_adaptiv.py MIT den fuenf Sicherungen neu -
        # nicht diesen Schalter zurueck.
        # ============================================================

        # Dynamic Sizing Toggle (WICHTIG!)
        dyn_frame = ctk.CTkFrame(scroll, fg_color=CLR_CARD, corner_radius=12)
        dyn_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(dyn_frame, text="🎯 POSITION SIZING", font=("Arial", 13, "bold"),
                     text_color=CLR_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
        dyn_row = ctk.CTkFrame(dyn_frame, fg_color="transparent")
        dyn_row.pack(fill="x", padx=12, pady=6)
        self.dyn_sizing_var = ctk.BooleanVar(value=self.engine.config.risk.use_dynamic_sizing)
        ctk.CTkSwitch(dyn_row, variable=self.dyn_sizing_var,
                      text="Dynamic Sizing (AdaptiveSizer + NUPL + DXY)",
                      font=("Arial", 11), fg_color="#333", progress_color=CLR_GREEN,
                      command=self._toggle_dynamic_sizing).pack(side="left")
        ctk.CTkLabel(dyn_row, text="AUS = Dein % wird genau verwendet | AN = KI optimiert",
                     font=("Arial", 9), text_color="#666").pack(side="left", padx=15)

        # Reset Buttons in einer Reihe
        reset_row = ctk.CTkFrame(scroll, fg_color="transparent")
        reset_row.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(reset_row, text="🗑️ SESSION ZURUECKSETZEN", font=("Arial", 11),
                      fg_color="#663333", text_color="#fff", hover_color="#883333",
                      height=36, command=self._reset_session).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(reset_row, text="🔓 NUR POSITIONEN SCHLIESSEN", font=("Arial", 11),
                      fg_color="#553355", text_color="#fff", hover_color="#774477",
                      height=36, command=self._close_all_positions_only).pack(side="left", fill="x", expand=True)

    # === BUGFIX REBALANCER-UI METHODS ===
    def _rb_get_obj(self):
        return getattr(self.engine, "portfolio_rebalancer", None) or getattr(self.engine, "rebalancer", None)

    def _rb_toggle(self):
        """ON/OFF Toggle fuer Rebalancer."""
        obj = self._rb_get_obj()
        if obj is None:
            self.rb_output_lbl.configure(text="Rebalancer nicht initialisiert!", text_color=CLR_RED)
            return
        try:
            curr = bool(getattr(obj, "enabled", False))
            new_state = not curr
            obj.enabled = new_state
            # === REBAL-PERSIST: Zustand speichern (ueberlebt Neustarts) ===
            try:
                import json as _json, os as _os
                _os.makedirs("data_store", exist_ok=True)
                with open(_os.path.join("data_store", "rebalancer_state.json"), "w", encoding="utf-8") as _f:
                    _json.dump({"enabled": new_state,
                                "dry_run": bool(getattr(obj, "dry_run", True))}, _f)
            except Exception:
                pass
            # UI updaten
            dry = bool(getattr(obj, "dry_run", True))
            self.rb_status_lbl.configure(
                text=("AKTIV" if new_state else "DEAKTIVIERT") + (" (DRY-RUN)" if dry else ""),
                text_color=(CLR_GREEN if new_state else "#888"))
            self.rb_enable_btn.configure(
                text=("DEAKTIVIEREN" if new_state else "AKTIVIEREN"),
                fg_color=(CLR_RED if new_state else CLR_GREEN),
                hover_color=("#a02030" if new_state else "#1a8a44"))
            self.rb_output_lbl.configure(
                text=("Rebalancer AKTIVIERT" if new_state else "Rebalancer DEAKTIVIERT") +
                     (" (Dry-Run: zeigt nur an, fuehrt keine Trades aus)" if dry else ""),
                text_color=(CLR_GREEN if new_state else "#aaa"))
            # Optional ins Doc-Log
            try:
                if hasattr(self.engine, "doc_agent") and self.engine.doc_agent:
                    self.engine.doc_agent.add_note(
                        "DOKUMENTIEREN",
                        f"Rebalancer per Settings-UI {'aktiviert' if new_state else 'deaktiviert'}")
            except Exception:
                pass
        except Exception as e:
            self.rb_output_lbl.configure(text=f"Toggle-Fehler: {e}", text_color=CLR_RED)

    def _rb_dry_run_check(self):
        """Berechnet aktuelle Abweichung ohne Trades auszufuehren."""
        obj = self._rb_get_obj()
        if obj is None:
            self.rb_output_lbl.configure(text="Rebalancer nicht initialisiert!", text_color=CLR_RED)
            return
        try:
            # Positionen + Preise sammeln
            positions = {}
            try:
                open_pos = getattr(self.engine.risk_engine, "open_positions", {}) or {}
                price_cache = getattr(self.engine.data_agent, "price_cache", {}) or {}
                for sym, p in open_pos.items():
                    if not p.get("active"):
                        continue
                    asset = sym.split("/")[0]
                    qty = p.get("qty", 0)
                    price = price_cache.get(sym, p.get("entry_price", 0))
                    positions[asset] = {"qty": qty, "value": qty * price}
            except Exception:
                pass
            # Equity bestimmen
            bal = self.engine.execution.get_balance()
            usdc = bal.get("total", {}).get("USDC", 0) + bal.get("total", {}).get("USDT", 0)
            pos_val = sum(p["value"] for p in positions.values())
            total_equity = usdc + pos_val
            target = getattr(obj, "target_alloc", {"BTC":55,"ETH":15,"SOL":10,"XRP":10,"alts":10})
            # Versuche calculate_trades oder check_rebalance
            trades = []
            price_cache = getattr(self.engine.data_agent, "price_cache", {})
            if hasattr(obj, "calculate_trades"):
                try:
                    trades = obj.calculate_trades(positions, total_equity, target, price_cache)
                except Exception:
                    trades = []
            if not trades:
                self.rb_output_lbl.configure(
                    text=f"Total: {total_equity:.2f}$ | Cash: {usdc:.2f}$ | Positionen: {pos_val:.2f}$\n"
                         f"Keine Rebalance-Trades noetig (Abweichung unter Schwelle 5%)",
                    text_color="#aaa")
            else:
                lines = [f"Total: {total_equity:.2f}$ | Cash: {usdc:.2f}$"]
                for t in trades[:8]:
                    lines.append(f"  {t.get('action','?')} {t.get('asset','?')}: {t.get('amount_usd',0):.2f}$ ({t.get('reason','')})")
                self.rb_output_lbl.configure(text="\n".join(lines), text_color=CLR_ACCENT)
        except Exception as e:
            self.rb_output_lbl.configure(text=f"Dry-Run-Fehler: {e}", text_color=CLR_RED)

    def _rb_show_status(self):
        """Zeigt Rebalancer-Status."""
        obj = self._rb_get_obj()
        if obj is None:
            self.rb_output_lbl.configure(text="Rebalancer nicht initialisiert!", text_color=CLR_RED)
            return
        try:
            enabled = getattr(obj, "enabled", False)
            dry = getattr(obj, "dry_run", True)
            threshold = getattr(obj, "threshold_pct", 5.0)
            target = getattr(obj, "target_alloc", {})
            cooldown = getattr(obj, "cooldown_h", 6)
            last_rb = getattr(obj, "last_rebalance", 0)
            lines = [
                f"Enabled: {enabled} | Dry-Run: {dry}",
                f"Schwelle: {threshold}% | Cooldown: {cooldown}h",
                f"Ziel-Allokation: " + ", ".join(f"{k}={v}%" for k,v in target.items()),
                f"Letzter Rebalance: " + (str(last_rb) if last_rb else "noch nie"),
            ]
            self.rb_output_lbl.configure(text="\n".join(lines), text_color="#aaa")
        except Exception as e:
            self.rb_output_lbl.configure(text=f"Status-Fehler: {e}", text_color=CLR_RED)

    # === SENSEI-MODE METHODS ===
    def _sensei_get(self):
        try:
            from features.sensei import Sensei
            return Sensei()
        except Exception as e:
            return None

    def _sensei_show(self, text: str):
        try:
            self.sm_output.configure(state="normal")
            self.sm_output.delete("1.0", "end")
            self.sm_output.insert("1.0", text)
            self.sm_output.configure(state="disabled")
        except Exception:
            pass

    def _sensei_explain(self):
        s = self._sensei_get()
        if s is None:
            self._sensei_show("Sensei-Modul nicht gefunden (features/sensei.py fehlt?)")
            return
        try:
            self._sensei_show(s.explain_last_signals(3))
        except Exception as e:
            self._sensei_show("Sensei-Fehler: " + str(e)[:200])

    def _sensei_lesson(self):
        s = self._sensei_get()
        if s is None:
            self._sensei_show("Sensei-Modul nicht gefunden (features/sensei.py fehlt?)")
            return
        try:
            self._sensei_show(s.daily_lesson())
        except Exception as e:
            self._sensei_show("Sensei-Fehler: " + str(e)[:200])

    # === TRADING-AKADEMIE ===
    def _open_akademie(self):
        try:
            import customtkinter as ctk
            from features.akademie import Akademie, CURRICULUM
        except Exception as e:
            self._sensei_show("Akademie nicht gefunden (features/akademie.py?): " + str(e)[:160])
            return
        ak = Akademie()
        prog = ak._load_progress()

        win = ctk.CTkToplevel(self)
        self._akademie_win = win   # Referenz halten
        win.title("Trading-Akademie")
        win.geometry("900x620")
        win.configure(fg_color="#0d0d0f")

        done = len(prog.get("erledigt", []))
        total = sum(len(ph["lessons"]) for ph in CURRICULUM)
        head = ctk.CTkLabel(win, text=f"  TRADING-AKADEMIE   -   {done}/{total} Lektionen   |   "
                                      f"Quiz {prog.get('quiz_richtig',0)}/{prog.get('quiz_gesamt',0)} richtig",
                            font=("Arial", 14, "bold"), text_color="#48bb78", anchor="w")
        head.pack(fill="x", padx=10, pady=(10, 4))

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=6)

        # linke Lektionsliste
        left = ctk.CTkScrollableFrame(body, fg_color="#141417", width=260)
        left.pack(side="left", fill="y", padx=(0, 8))
        # rechter Lesebereich
        out = ctk.CTkTextbox(body, font=("Consolas", 12), fg_color="#0d0d0f",
                             text_color="#ddd", wrap="word")
        out.pack(side="left", fill="both", expand=True)
        out.insert("1.0", "Waehle links eine Lektion.\n\nEmpfehlung fuer den Anfang: 1.1")
        out.configure(state="disabled")

        quiz_state = {"lesson": None}

        def show_text(txt):
            out.configure(state="normal")
            out.delete("1.0", "end")
            out.insert("1.0", txt)
            out.configure(state="disabled")

        def open_lesson(L):
            quiz_state["lesson"] = L
            t = f"LEKTION {L['id']}: {L['titel']}\n" + "=" * 50 + "\n\n" + L["text"]
            if L.get("trade_beispiel"):
                ex = ak.real_example(L["trade_beispiel"])
                if ex:
                    t += "\n\n>>> " + ex
            t += "\n\n(Unten 'Quiz starten' druecken, um dein Wissen zu testen.)"
            show_text(t)
            if L["id"] not in prog["erledigt"]:
                prog["erledigt"].append(L["id"])
                ak._save_progress(prog)

        for phase in CURRICULUM:
            ctk.CTkLabel(left, text=phase["phase"], font=("Arial", 11, "bold"),
                         text_color="#48bb78", anchor="w").pack(fill="x", padx=6, pady=(8, 2))
            for L in phase["lessons"]:
                mark = "[x] " if L["id"] in prog.get("erledigt", []) else "[  ] "
                ctk.CTkButton(left, text=mark + L["id"] + "  " + L["titel"],
                              font=("Arial", 10), anchor="w", height=30,
                              fg_color="#1f2937", hover_color="#374151",
                              command=lambda LL=L: open_lesson(LL)).pack(fill="x", padx=6, pady=1)

        # Quiz-Leiste unten
        bar = ctk.CTkFrame(win, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(0, 10))

        # Quiz-Anzeigebereich (inline, kein Popup) - erscheint unter der Leiste
        quiz_panel = ctk.CTkFrame(win, fg_color="#141417", corner_radius=8)
        quiz_widgets = {"items": []}

        def clear_quiz_panel():
            for w in quiz_widgets["items"]:
                try:
                    w.destroy()
                except Exception:
                    pass
            quiz_widgets["items"] = []
            quiz_panel.pack_forget()

        def start_quiz():
            L = quiz_state["lesson"]
            if not L or not L.get("quiz"):
                show_text("Erst links eine Lektion mit Quiz oeffnen, dann 'Quiz starten'.")
                return
            q = L["quiz"]
            clear_quiz_panel()
            quiz_panel.pack(fill="x", padx=10, pady=(0, 8))

            frage = ctk.CTkLabel(quiz_panel, text="QUIZ " + L["id"] + ":  " + q["frage"],
                                 font=("Arial", 12, "bold"), text_color="#48bb78",
                                 wraplength=820, justify="left", anchor="w")
            frage.pack(fill="x", padx=12, pady=(10, 6))
            quiz_widgets["items"].append(frage)

            res = ctk.CTkLabel(quiz_panel, text="", font=("Arial", 11),
                               wraplength=820, justify="left", text_color="#bbb", anchor="w")

            def answer(idx):
                prog["quiz_gesamt"] = prog.get("quiz_gesamt", 0) + 1
                if idx == q["richtig"]:
                    prog["quiz_richtig"] = prog.get("quiz_richtig", 0) + 1
                    res.configure(text="RICHTIG!   " + q["erklaerung"], text_color="#48bb78")
                else:
                    res.configure(text="Nicht ganz.   " + q["erklaerung"]
                                  + "   (Richtig: " + q["optionen"][q["richtig"]] + ")",
                                  text_color="#f6ad55")
                ak._save_progress(prog)

            for i, opt in enumerate(q["optionen"]):
                b = ctk.CTkButton(quiz_panel, text=opt, font=("Arial", 11),
                                  anchor="w", height=32, fg_color="#1f2937",
                                  hover_color="#374151", text_color="#ddd",
                                  command=lambda ii=i: answer(ii))
                b.pack(fill="x", padx=12, pady=2)
                quiz_widgets["items"].append(b)

            res.pack(fill="x", padx=12, pady=(6, 10))
            quiz_widgets["items"].append(res)

        ctk.CTkButton(bar, text="Quiz starten", font=("Arial", 11, "bold"),
                      width=160, height=34, fg_color="#6b46c1", hover_color="#553c9a",
                      command=start_quiz).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Schliessen", font=("Arial", 11, "bold"),
                      width=120, height=34, fg_color="#4a5568", hover_color="#2d3748",
                      command=win.destroy).pack(side="left", padx=4)

        try:
            win.after(200, win.lift)
        except Exception:
            pass

    def _save_settings(self):
        cfg = self.engine.config
        cfg.exchange.api_key = self.api_key_entry.get().strip()
        cfg.exchange.api_secret = self.api_secret_entry.get().strip()
        cfg.trading.mode = self.mode_var.get()
        cfg.telegram.token = self.tg_token_entry.get().strip()
        cfg.telegram.chat_id = self.tg_chat_entry.get().strip()
        try:
            # Startkapital - SOFORT in Execution Engine anwenden!
            new_bal = float(self.balance_var.get())
            if new_bal != cfg.trading.initial_paper_balance:
                cfg.trading.initial_paper_balance = new_bal
                self._add_log(f"💰 Startkapital geaendert: {new_bal:.0f} USDC")
                self._add_log(f"⚠️ Klicke SESSION ZURUECKSETZEN um mit {new_bal:.0f}$ zu starten!")
            # Risk
            cfg.risk.max_daily_loss_usd = float(self.risk_vars["max_daily_loss"].get())
            cfg.risk.max_open_positions = int(self.risk_vars["max_positions"].get())
            cfg.risk.stop_loss_pct = float(self.risk_vars["stop_loss"].get())
            cfg.risk.trailing_stop_pct = float(self.risk_vars["trailing"].get())
            cfg.trading.position_size_pct = float(self.risk_vars["pos_size"].get())
            cfg.risk.max_exposure_per_coin_pct = max(cfg.trading.position_size_pct + 5, 25)
        except ValueError:
            pass
        # Sparplan Settings
        cfg.trading.btc_dca_enabled = self.sparplan_var.get()
        self.engine.btc_accumulator.sparplan_active = self.sparplan_var.get()
        try:
            cfg.trading.btc_dca_pct = float(self.sparplan_pct_var.get())
            self.engine.btc_accumulator.sparplan_pct = cfg.trading.btc_dca_pct
            cfg.trading.btc_dca_interval_min = int(self.sparplan_interval_var.get())
            self.engine.btc_accumulator.sparplan_interval = cfg.trading.btc_dca_interval_min * 60
        except ValueError:
            pass
        cfg.save()
        self._sync_settings_from_config()
        sp_status = "AN" if cfg.trading.btc_dca_enabled else "AUS"
        self._add_log(f"💾 Einstellungen gespeichert! Sparplan: {sp_status}")

    def _show_balance_recommendation(self):
        """Zeigt Empfehlungen basierend auf eingegebenem Startkapital."""
        self._update_balance_recommendation()

    def _update_balance_recommendation(self):
        """Berechnet Empfehlungen fuer das Startkapital."""
        try:
            bal = float(self.balance_var.get())
        except ValueError:
            bal = 100

        # Auto-Empfehlung berechnen
        if bal < 50:
            coins = 1; max_pos = 1; pos_pct = 80; daily_loss = 5
            tip = "Nur BTC! Sehr kleines Kapital."
        elif bal < 150:
            coins = 1; max_pos = 2; pos_pct = 50; daily_loss = 10
            tip = "1-2 Coins (BTC, evtl. ETH)"
        elif bal < 300:
            coins = 2; max_pos = 3; pos_pct = 30; daily_loss = 15
            tip = "2-3 Coins (BTC + ETH + 1 Alt)"
        elif bal < 500:
            coins = 3; max_pos = 4; pos_pct = 25; daily_loss = 25
            tip = "3-4 Coins empfohlen"
        elif bal < 1000:
            coins = 4; max_pos = 5; pos_pct = 20; daily_loss = 30
            tip = "4-5 Coins, gute Diversifikation"
        elif bal < 3000:
            coins = 6; max_pos = 7; pos_pct = 15; daily_loss = 40
            tip = "6-7 Coins, solides Portfolio"
        else:
            coins = 8; max_pos = 10; pos_pct = 15; daily_loss = 50
            tip = "8-10 Coins, volle Diversifikation"

        trade_size = bal * pos_pct / 100
        sl_verlust = trade_size * 0.04
        fee = trade_size * 0.001

        text = (f"Kapital: {bal:.0f}$ → {tip}\n"
                f"Empfehlung: {coins} Coins | Pos {pos_pct}% | Max {max_pos} | SL 4%\n"
                f"Pro Trade: ~{trade_size:.0f}$ | Max Verlust/Trade: ~{sl_verlust:.1f}$ | Fee: ~{fee:.2f}$")
        self.balance_recommendation_lbl.configure(text=text)

    def _apply_balance_recommendation(self):
        """Wendet die Empfehlung automatisch an."""
        try:
            bal = float(self.balance_var.get())
        except ValueError:
            return
        if bal < 150:
            coins, max_pos, pos_pct = 1, 2, 50
        elif bal < 300:
            coins, max_pos, pos_pct = 2, 3, 30
        elif bal < 500:
            coins, max_pos, pos_pct = 3, 4, 25
        elif bal < 1000:
            coins, max_pos, pos_pct = 4, 5, 20
        elif bal < 3000:
            coins, max_pos, pos_pct = 6, 7, 15
        else:
            coins, max_pos, pos_pct = 8, 10, 15

        self.risk_vars["max_positions"].set(str(max_pos))
        self.risk_vars["pos_size"].set(str(pos_pct))

    def _close_all_positions_only(self):
        """Schliesst NUR offene Positionen (ohne Balance/Journal Reset)."""
        try:
            if hasattr(self.engine, 'twap'):
                self.engine.twap.cancel_all()
        except Exception:
            pass

        try:
            if hasattr(self.engine.risk_engine, 'reset_all_positions'):
                count = self.engine.risk_engine.reset_all_positions()
            else:
                count = len(self.engine.risk_engine.open_positions)
                self.engine.risk_engine.open_positions.clear()
        except Exception as e:
            self._add_log(f"⚠️ Positionen schliessen: {e}")
            return

        # Trade-Markers leeren (sonst werden Charts wirr)
        try:
            self.engine._trade_markers.clear()
        except Exception:
            pass

        # State updaten
        try:
            self.engine.state.set("open_positions", {})
            self.engine.state.set("open_positions_backup", {})
            self.engine.state.save()
        except Exception:
            pass

        # Verhindere Restore
        self.engine._positions_restored = True

        self._add_log(f"🔓 {count} Positionen geschlossen (Balance bleibt erhalten)")

    def _reset_session(self):
        """Setzt Paper-Balance + BTC zurueck. Stoppt alle TWAPs.
        Nutzt sichere Reset-Funktionen mit Fallbacks, kein Crash mehr."""
        # 1. ZUERST alle laufenden TWAPs stoppen!
        try:
            if hasattr(self.engine, 'twap'):
                self.engine.twap.cancel_all()
        except Exception as e:
            self._add_log(f"⚠️ TWAP cancel: {e}")

        # 2. Balance aus UI-Feld lesen (was User gerade eingegeben hat)
        try:
            bal = float(self.balance_var.get())
        except (ValueError, AttributeError):
            bal = self.engine.config.trading.initial_paper_balance

        # In Config schreiben + speichern
        self.engine.config.trading.initial_paper_balance = bal
        try:
            self.engine.config.save()
        except Exception as e:
            self._add_log(f"⚠️ Config save: {e}")

        # Paper-Balance DIREKT in Execution setzen
        try:
            self.engine.execution.set_paper_balance(bal)
        except Exception as e:
            self._add_log(f"⚠️ Balance set: {e}")

        # 3. BTC Accumulator zuruecksetzen
        try:
            self.engine.btc_accumulator.purchases = []
            self.engine.btc_accumulator.total_btc = 0
            self.engine.btc_accumulator.total_invested = 0
        except Exception as e:
            self._add_log(f"⚠️ BTC reset: {e}")

        # 4. Journal leeren (clear() existiert jetzt - BUG 1 fix!)
        try:
            self.engine.journal.clear()
        except AttributeError:
            # Fallback falls clear() doch nicht existiert
            try:
                self.engine.journal.trades = []
                if hasattr(self.engine.journal, '_save'):
                    self.engine.journal._save()
            except Exception as e:
                self._add_log(f"⚠️ Journal: {e}")
        except Exception as e:
            self._add_log(f"⚠️ Journal clear: {e}")

        # 5. RISK ENGINE: Sicheres Reset mit reset_all_positions (BUG 3 fix!)
        try:
            if hasattr(self.engine.risk_engine, 'reset_all_positions'):
                count = self.engine.risk_engine.reset_all_positions()
                if count > 0:
                    self._add_log(f"🔓 {count} offene Positionen geschlossen")
            else:
                # Fallback (alter Code)
                self.engine.risk_engine.open_positions.clear()
                self.engine.risk_engine.consecutive_losses = 0
                self.engine.risk_engine.daily_trades = 0
                self.engine.risk_engine.kill_switch.reset_daily()
        except Exception as e:
            self._add_log(f"⚠️ Risk reset: {e}")

        # 6. Trade-Markers leeren
        try:
            self.engine._trade_markers.clear()
        except Exception:
            pass

        # 7. Equity History leeren
        try:
            self.equity_history.clear()
        except Exception:
            pass

        # 8. State komplett leeren (sonst bleiben alte Positionen!)
        try:
            self.engine.state.set("equity_history", [])
            self.engine.state.set("open_positions", {})
            self.engine.state.set("open_positions_backup", {})
            self.engine.state.set("trade_markers", {})
            self.engine.state.save()
        except Exception as e:
            self._add_log(f"⚠️ State: {e}")

        # 9. Verhindere dass beim naechsten Tick die alten Positionen geladen werden
        try:
            self.engine._positions_restored = True
        except Exception:
            pass

        # 10. UI synchronisieren + History refreshen
        try:
            self._sync_settings_from_config()
        except Exception:
            pass
        try:
            self._refresh_history()
        except Exception:
            pass

        self._add_log(f"🗑️ SESSION ZURUECKGESETZT! Paper: {bal:,.0f}$ | BTC: 0 | Trades: 0")

    # [ENTFERNT 11.08.2026] _toggle_auto_optimizer() ist mit seinem Schalter
    # weggefallen (Begruendung oben im Einstellungs-Tab). Die Methode blieb
    # zunaechst stehen und griff auf self.auto_opt_var zu - eine Variable,
    # die es nicht mehr gibt. Aufgerufen wurde sie von niemandem mehr, aber
    # eine Methode, die beim ersten Aufruf mit AttributeError abstuerzt, ist
    # eine Falle fuer den Naechsten. Deshalb ganz entfernt statt liegen zu
    # lassen.

    def _toggle_dynamic_sizing(self):
        active = self.dyn_sizing_var.get()
        self.engine.config.risk.use_dynamic_sizing = active
        self.engine.config.save()
        if active:
            self._add_log(f"🎯 Dynamic Sizing: AN (AdaptiveSizer + NUPL + DXY)")
        else:
            pct = self.engine.config.trading.position_size_pct
            self._add_log(f"🎯 Dynamic Sizing: AUS - Dein Wert ({pct}%) wird exakt verwendet!")

        """Setzt Paper-Balance und BTC-Akkumulator zurueck."""
        # Paper Balance reset
        self.engine.execution._paper_balances = {"USDC": self.engine.config.trading.initial_paper_balance}
        # BTC Akkumulator reset
        self.engine.btc_accumulator.total_btc = 0.0
        self.engine.btc_accumulator.total_invested_usd = 0.0
        self.engine.btc_accumulator.purchases = []
        self.engine.btc_accumulator.profit_buffer = 0.0
        self.engine.btc_accumulator._save()
        # Risk reset
        self.engine.risk_engine.open_positions = {}
        self.engine.risk_engine.reset_daily()
        # Journal reset
        self.engine.journal.trades = []
        self.engine.journal._save()
        self._add_log("🗑️ SESSION ZURÜCKGESETZT! Paper: 10.000$ | BTC: 0 | Trades: 0")

    # ==========================================================
    # LOG TAB
    # ==========================================================
    def _build_charts_tab(self):
        import customtkinter as ctk
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        tab = self.tab_charts
        ctrl = ctk.CTkFrame(tab, fg_color=CLR_CARD, corner_radius=10, height=46)
        ctrl.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(ctrl, text="Coin:", font=("Arial", 11, "bold"),
                     text_color="#aaa").pack(side="left", padx=(12, 4), pady=8)
        try:
            _coin_list = list(self.engine.config.trading.coins)
        except Exception:
            _coin_list = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "XRP/USDC", "ADA/USDC"]
        self.chart_coin = ctk.StringVar(value=_coin_list[0] if _coin_list else "BTC/USDC")
        ctk.CTkOptionMenu(ctrl, variable=self.chart_coin,
                          values=_coin_list, width=130,
                          command=lambda _=None: self._update_charts_tab()).pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Intervall:", font=("Arial", 11, "bold"),
                     text_color="#aaa").pack(side="left", padx=(12, 4))
        self.chart_interval = ctk.StringVar(value="1h")
        ctk.CTkOptionMenu(ctrl, variable=self.chart_interval,
                          values=["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"], width=80,
                          command=lambda _=None: self._update_charts_tab()).pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Tage:", font=("Arial", 11, "bold"),
                     text_color="#aaa").pack(side="left", padx=(12, 4))
        self.chart_days = ctk.StringVar(value="14")
        ctk.CTkOptionMenu(ctrl, variable=self.chart_days,
                          values=["14", "30", "60", "90"], width=70,
                          command=lambda _=None: self._update_charts_tab()).pack(side="left", padx=4)

        self.chart_trades_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(ctrl, text="Meine Trades", variable=self.chart_trades_var,
                        font=("Arial", 10, "bold"), checkbox_width=16, checkbox_height=16,
                        command=self._update_charts_tab).pack(side="left", padx=12)

        ctk.CTkButton(ctrl, text="Aktualisieren (Binance)", font=("Arial", 11, "bold"),
                      width=180, fg_color="#2f855a", hover_color="#276749",
                      command=self._refresh_charts_data).pack(side="right", padx=12)
        ctk.CTkButton(ctrl, text="Stop-Loss-Analyse", font=("Arial", 11, "bold"),
                      width=160, fg_color="#b7791f", hover_color="#975a16",
                      command=self._open_sl_edge).pack(side="right", padx=4)
        ctk.CTkButton(ctrl, text="Strategie-Labor", font=("Arial", 11, "bold"),
                      width=150, fg_color="#6b46c1", hover_color="#553c9a",
                      command=self._open_strategy_lab).pack(side="right", padx=4)

        chart_frame = ctk.CTkFrame(tab, fg_color=CLR_CARD, corner_radius=12)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=4)
        self.chart_fig, (self.chart_ax_price, self.chart_ax_vol) = plt.subplots(
            2, 1, figsize=(11, 5), dpi=85, gridspec_kw={"height_ratios": [4, 1]})
        self.chart_fig.patch.set_facecolor(CLR_BG)
        self.chart_fig.subplots_adjust(left=0.07, right=0.97, top=0.96, bottom=0.08, hspace=0.05)
        self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, master=chart_frame)
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)

        ind_row = ctk.CTkFrame(tab, fg_color=CLR_CARD, corner_radius=8, height=34)
        ind_row.pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(ind_row, text="Indikatoren:", font=("Arial", 10, "bold"),
                     text_color="#aaa").pack(side="left", padx=(12, 6), pady=4)
        self.chart_ind_vars = {}
        for key, lab, col in [("ema", "EMA 20/50", "#42a5f5"),
                              ("boll", "Bollinger", "#888"),
                              ("vwap", "VWAP", "#ab47bc"),
                              ("rsi", "RSI", "#26a69a"),
                              ("macd", "MACD", "#ffa726")]:
            v = ctk.BooleanVar(value=False)
            self.chart_ind_vars[key] = v
            ctk.CTkCheckBox(ind_row, text=lab, variable=v, font=("Arial", 10, "bold"),
                            text_color=col, fg_color=col, checkbox_width=16, checkbox_height=16,
                            command=self._update_charts_tab).pack(side="left", padx=8)

        self.chart_status = ctk.CTkLabel(tab, text="Waehle einen Coin und druecke Aktualisieren.",
                                         font=("Consolas", 10), text_color="#888", anchor="w",
                                         justify="left")
        self.chart_status.pack(fill="x", padx=12, pady=(0, 8))

        self.after(400, self._update_charts_tab)

    def _update_charts_tab(self):
        try:
            from features.chart_view import render
        except Exception as e:
            if hasattr(self, "chart_status"):
                self.chart_status.configure(text="chart_view.py fehlt: " + str(e)[:80])
            return
        try:
            days = int(self.chart_days.get())
            _inds = [k for k, v in getattr(self, "chart_ind_vars", {}).items() if v.get()]
            msg = render(self.chart_fig, self.chart_ax_price, self.chart_ax_vol,
                         self.chart_coin.get(), interval=self.chart_interval.get(),
                         days=days, show_trades=self.chart_trades_var.get(),
                         indicators=_inds)
            self.chart_canvas.draw()
            self.chart_status.configure(text=msg)
        except Exception as e:
            self.chart_status.configure(text="Chart-Fehler: " + str(e)[:120])

    def _refresh_charts_data(self):
        if hasattr(self, "chart_status"):
            self.chart_status.configure(text="Lade neue Kerzen von Binance...")
        def worker():
            try:
                from features.chart_data import ChartData
                cd = ChartData()
                cd.load(self.chart_coin.get(), interval=self.chart_interval.get(),
                        days=int(self.chart_days.get()))
            except Exception as e:
                self.after(0, lambda: self.chart_status.configure(
                    text="Binance-Fehler: " + str(e)[:100]))
                return
            self.after(0, self._update_charts_tab)
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _open_strategy_lab(self):
        import customtkinter as ctk
        win = ctk.CTkToplevel(self)
        self._strat_lab_win = win
        win.title("Strategie-Labor")
        win.geometry("780x580")
        win.configure(fg_color="#0d0d0f")
        try:
            win.transient(self); win.after(150, win.lift); win.focus_force()
        except Exception:
            pass
        ctk.CTkLabel(win, text="  STRATEGIE-LABOR  (Was waere optimal gewesen?)",
                     font=("Arial", 14, "bold"), text_color="#b794f4",
                     anchor="w").pack(fill="x", padx=10, pady=(10, 2))
        box = ctk.CTkTextbox(win, font=("Consolas", 11), fg_color="#0d0d0f",
                             text_color="#ddd", wrap="none")
        box.pack(fill="both", expand=True, padx=10, pady=8)
        box.insert("1.0", "Rechne alle Stop+Trailing-Kombis auf den echten Kerzen durch...\n"
                          "(kann ein paar Sekunden dauern)")

        def _cur():
            s, t = 0.04, 0.01
            try:
                s = float(getattr(self.engine.config.risk, "stop_loss_pct", 4.0)); s = s/100 if s > 1 else s
                t = float(getattr(self.engine.config.risk, "trailing_stop_pct", 1.0)); t = t/100 if t > 1 else t
            except Exception:
                pass
            return s, t

        def worker():
            try:
                from features.strategy_lab import run, format_report
                s, t = _cur()
                txt = format_report(run(), cur_stop=s, cur_trail=t)
            except Exception as e:
                import traceback
                txt = "Fehler:\n" + str(e) + "\n\n" + traceback.format_exc()[:500]
            def show():
                try:
                    box.delete("1.0", "end"); box.insert("1.0", txt)
                except Exception:
                    pass
            try:
                self.after(0, show)
            except Exception:
                pass
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _open_sl_edge(self):
        import customtkinter as ctk
        # Referenz auf self halten, sonst raeumt der GC das Fenster sofort weg
        win = ctk.CTkToplevel(self)
        self._sl_edge_win = win
        win.title("Stop-Loss-Edge-Analyse")
        win.geometry("760x560")
        win.configure(fg_color="#0d0d0f")
        try:
            win.transient(self)
            win.after(150, win.lift)
        except Exception:
            pass
        ctk.CTkLabel(win, text="  STOP-LOSS-EDGE-ANALYSE", font=("Arial", 14, "bold"),
                     text_color="#f6ad55", anchor="w").pack(fill="x", padx=10, pady=(10, 2))
        box = ctk.CTkTextbox(win, font=("Consolas", 11), fg_color="#0d0d0f",
                             text_color="#ddd", wrap="none")
        box.pack(fill="both", expand=True, padx=10, pady=8)
        box.insert("1.0", "Rechne... (laedt Kerzen, kann ein paar Sekunden dauern)")

        def _sl_current():
            # Stop-Loss aus der Config holen - korrekter Pfad ist config.risk
            for path in (("risk", "stop_loss_pct"), ("trading", "stop_loss_pct")):
                try:
                    grp = getattr(self.engine.config, path[0])
                    val = float(getattr(grp, path[1]))
                    return val / 100.0 if val > 1 else val
                except Exception:
                    continue
            return 0.032

        def worker():
            try:
                from features.stoploss_edge import run, format_report
                res = run()
                txt = format_report(res, current_stop=_sl_current())
            except Exception as e:
                import traceback
                txt = "Fehler bei der Analyse:\n" + str(e) + "\n\n" + traceback.format_exc()[:600]
            def show():
                try:
                    box.configure(state="normal")
                    box.delete("1.0", "end")
                    box.insert("1.0", txt)
                except Exception:
                    pass
            try:
                self.after(0, show)
            except Exception:
                pass

        import threading
        threading.Thread(target=worker, daemon=True).start()

    # [LOG-FARBEN 17.08.2026] Bis hierher war das Protokoll eine einzige
    # graue Wand - bei rund 12.000 Zeilen am Tag findet darin niemand die
    # drei, auf die es ankommt. Die Farbe beantwortet EINE Frage je Zeile:
    # Was sieht der Bot, was besitzt er, warum tat er nichts, und was ging
    # schief. Die Zuordnung steht im BOT-HANDBUCH, Teil 4.42.
    LOG_FARBEN = {
        "signal":   CLR_GREEN,    # Signal erkannt / Bestand
        "handel":   CLR_ACCENT,   # ausgefuehrter Kauf oder Verkauf
        "blockade": CLR_BLUE,     # bewusst nicht gehandelt
        "fehler":   CLR_RED,      # Fehler, Verlust, Notaus
        "hinweis":  CLR_ORANGE,   # Warnung, noch kein Fehler
        "normal":   "#8a8a92",    # alles Uebrige, bewusst gedaempft
    }

    # Reihenfolge ist Absicht: die erste passende Regel gewinnt.
    #
    # GEPRUEFT UND KORRIGIERT 17.08.2026: Der erste Entwurf hatte "BUY " und
    # "SELL " in der Handels-Gruppe. Damit wurde die Zeile
    #   "[SIGNAL] BTC/USDC: Score 7/10 -> BUY 146.92$"
    # golden statt gruen - obwohl gar nichts gekauft wurde, es war nur ein
    # Vorschlag. Dasselbe bei "BUY blockiert". Ein ausgefuehrter Handel
    # erkennt man ausschliesslich an [JOURNAL] oder [EXEC], nie am Wort BUY.
    # Deshalb steht "blockade" jetzt VOR "handel", und die Wortmarken sind
    # weg.
    _LOG_REGELN = (
        ("fehler",   ("FEHLER", "ERROR", "TRACEBACK", "EXCEPTION",
                      "KILL-SWITCH", "NOTAUS", "CRITICAL", "❌", "🛑")),
        ("blockade", ("REJECTED", "BLOCKIERT", "GESPERRT", "[REGIME]",
                      "[RISK]", "SCHATTEN", "NOTIZBUCH")),
        ("handel",   ("[JOURNAL]", "[EXEC]", "🛒", "✅")),
        ("signal",   ("[SIGNAL]", "[BALANCE]", "[MONITOR]", "[BRAIN]",
                      "[MTF]", "[META]", "[HEART]", "[SIZING]")),
        ("hinweis",  ("WARN", "⚠", "VERSTELLT", "ACHTUNG")),
    )

    def _log_art(self, msg):
        """Welche Farbe bekommt diese Zeile? Erste passende Regel gewinnt."""
        gross = msg.upper()
        for art, marker in self._LOG_REGELN:
            if any(m in gross for m in marker):
                return art
        return "normal"

    def _build_log_tab(self):
        self.log_text = ctk.CTkTextbox(self.tab_log, fg_color="#0d0d0f",
                                        font=("Consolas", 11), text_color="#ccc")
        self.log_text.pack(expand=True, fill="both", padx=10, pady=5)
        # Farbmarken einmalig anmelden. CTkTextbox kapselt ein tk.Text;
        # ohne dessen tag_config gibt es keine Zeilenfarben. Faellt der
        # Zugriff aus, laeuft alles wie vorher weiter - nur einfarbig.
        try:
            box = self.log_text._textbox
            for art, farbe in self.LOG_FARBEN.items():
                box.tag_config(art, foreground=farbe)
        except Exception:
            pass

    def _add_log(self, msg):
        ts = time.strftime('%H:%M:%S')
        try:
            self.log_text.configure(state="normal")
            zeile = f"[{ts}] {msg}\n"
            try:
                self.log_text._textbox.insert("end", zeile, self._log_art(msg))
            except Exception:
                self.log_text.insert("end", zeile)   # Rueckfall: ohne Farbe
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

    # ==========================================================
    # FOOTER – Start/Stop + Status
    # ==========================================================
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=CLR_CARD, corner_radius=0, height=50)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        left = ctk.CTkFrame(footer, fg_color="transparent")
        left.pack(side="left", padx=15, fill="y")

        self.status_lbl = ctk.CTkLabel(left, text="⏹ Gestoppt", font=("Arial", 11, "bold"),
                                        text_color="#888")
        self.status_lbl.pack(side="left", pady=12)

        self.uptime_lbl = ctk.CTkLabel(left, text="", font=("Arial", 10), text_color="#555")
        self.uptime_lbl.pack(side="left", padx=15, pady=12)

        right = ctk.CTkFrame(footer, fg_color="transparent")
        right.pack(side="right", padx=15, fill="y")

        self.start_btn = ctk.CTkButton(right, text="▶ STARTEN", font=("Arial", 13, "bold"),
                                        fg_color=CLR_GREEN, text_color="#000", hover_color="#00cc6a",
                                        width=140, height=36, command=self._toggle_bot)
        self.start_btn.pack(side="right", pady=8)

    def _toggle_bot(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.configure(text="⏹ STOPP", fg_color=CLR_RED, hover_color="#cc3344")
            self.status_lbl.configure(text="🟢 Läuft", text_color=CLR_GREEN)
            self._add_log("🚀 Trading Imperium V7 gestartet!")
            threading.Thread(target=self.engine.start, daemon=True).start()
        else:
            self.is_running = False
            self.start_btn.configure(text="▶ STARTEN", fg_color=CLR_GREEN, hover_color="#00cc6a")
            self.status_lbl.configure(text="⏹ Gestoppt", text_color="#888")
            self._add_log("⏹ Bot gestoppt")
            self.engine.stop()

    # ==========================================================
    # UPDATER – Aktualisiert UI periodisch
    # ==========================================================
    def _start_updater(self):
        # [CHARTFIX-MT] Initiale Charts: Tkinter nur aus dem Main-Thread anfassen.
        # self.after(ms) plant _update_all_charts im Main-Thread (~3s Delay,
        # ohne Worker-Thread) -> kein "main thread is not in main loop" mehr.
        self.after(3000, self._update_all_charts)

        # Preis-Ticker Thread (holt Preise aktiv)
        def _price_tick():
            tick_count = 0
            _client = None
            while True:
                try:
                    # Client sicherstellen (geteilter Client!)
                    if _client is None:
                        if self._shared_client:
                            _client = self._shared_client
                        else:
                            import ccxt as _ccxt
                            _client = _ccxt.binance({"enableRateLimit": True, "timeout": 10000})
                            self._shared_client = _client

                    try:
                        bal = self.engine.execution.get_balance()
                    except Exception:
                        bal = {'total': {}, 'free': {}}

                    loaded = 0
                    for coin in list(self.coin_labels.keys()):
                        try:
                            # Versuche USDC, Fallback auf USDT
                            try:
                                ticker = _client.fetch_ticker(coin)
                            except Exception:
                                alt = coin.replace("USDC", "USDT")
                                ticker = _client.fetch_ticker(alt)

                            price = ticker.get('last', 0)
                            pct = ticker.get('percentage', 0) or 0

                            if price > 0:
                                self.engine.data_agent.price_cache[coin] = price
                                loaded += 1

                                # Preis-History
                                if coin in self.price_history:
                                    self.price_history[coin].append(price)
                                    if len(self.price_history[coin]) > 60:
                                        self.price_history[coin] = self.price_history[coin][-60:]

                                if coin in self.coin_labels:
                                    labels = self.coin_labels[coin]
                                    self.after(0, lambda l=labels, p=price: l["price"].configure(text=f"{p:,.2f} $"))
                                    color = CLR_GREEN if pct >= 0 else CLR_RED
                                    self.after(0, lambda l=labels, pc=pct, c=color: l["change"].configure(
                                        text=f"24h: {pc:+.2f}%", text_color=c))
                                    asset = coin.split("/")[0]
                                    qty = bal.get('total', {}).get(asset, 0)
                                    # === DISPLAY FIX: RISK-ENGINE FALLBACK ===
                                    # Wenn Balance leer aber Position offen ist, nutze Position
                                    if qty <= 0:
                                        _pos = self.engine.risk_engine.open_positions.get(coin, {})
                                        if _pos.get("active") and _pos.get("qty", 0) > 0:
                                            qty = _pos.get("qty", 0)
                                    if qty > 0:
                                        val = qty * price
                                        # P&L% aus open_positions berechnen
                                        pos = self.engine.risk_engine.open_positions.get(coin, {})
                                        entry = pos.get("entry_price", 0)
                                        if entry > 0:
                                            pnl_pct = ((price / entry) - 1) * 100
                                            pnl_usd = (price - entry) * qty
                                            pnl_col = CLR_GREEN if pnl_pct >= 0 else CLR_RED
                                            self.after(0, lambda l=labels, q=qty, v=val:
                                                l["balance"].configure(
                                                    text=f"{q:.6f} ({v:.2f}$)", text_color=CLR_GREEN))
                                            self.after(0, lambda l=labels, pp=pnl_pct, pu=pnl_usd, pc=pnl_col:
                                                l["pnl"].configure(
                                                    text=f"P&L: {pp:+.1f}% ({pu:+.2f}$)", text_color=pc))
                                        else:
                                            self.after(0, lambda l=labels, q=qty, v=val: l["balance"].configure(
                                                text=f"{q:.6f} ({v:.2f}$)", text_color=CLR_GREEN))
                                            self.after(0, lambda l=labels: l["pnl"].configure(text=""))
                                    else:
                                        # Signal-Info: Zeige Indikator-Werte
                                        try:
                                            snap = self.engine.data_agent._last_snapshots.get(coin)
                                            pos = self.engine.risk_engine.open_positions.get(coin, {})
                                            mode = self.engine._coin_modes.get(coin, "SL") if hasattr(self.engine, '_coin_modes') else "SL"
                                            if pos.get("active"):
                                                mode_text = {"SL": "🛡️SL", "HOLD": "✋HOLD", "TP": "🎯TP"}.get(mode, "SL")
                                                self.after(0, lambda l=labels, m=mode_text: l["signal"].configure(
                                                    text=f"{m} aktiv", text_color=CLR_CYAN))
                                            elif snap and hasattr(snap, 'indicators'):
                                                rsi = snap.indicators.get("rsi", 50)
                                                adx = snap.indicators.get("adx", 20)
                                                self.after(0, lambda l=labels, r=rsi, a=adx: l["signal"].configure(
                                                    text=f"RSI:{r:.0f} ADX:{a:.0f}", text_color="#888"))
                                            else:
                                                self.after(0, lambda l=labels: l["signal"].configure(
                                                    text="Analysiere...", text_color="#555"))
                                        except Exception:
                                            self.after(0, lambda l=labels: l["signal"].configure(
                                                text="Bereit", text_color="#555"))
                                        self.after(0, lambda l=labels: l["pnl"].configure(text=""))
                            time.sleep(0.3)
                        except Exception:
                            pass

                    # Charts alle 10 Ticks aktualisieren
                    tick_count += 1
                    if tick_count % 10 == 0 and loaded > 0:
                        self.after(0, self._update_all_charts)

                    if tick_count == 1:
                        self._add_log(f"[TICKER] {loaded}/{len(self.coin_labels)} Coins geladen")

                except Exception as e:
                    if tick_count < 3:
                        self._add_log(f"[TICKER] Fehler: {e}")
                time.sleep(3)
        threading.Thread(target=_price_tick, daemon=True).start()

        # Stats-Updater Thread (auch History auto-refresh)
        def _stat_tick():
            hist_counter = 0
            while True:
                try:
                    self._update_stats()
                    self._update_agents()
                    # History alle 10 Sekunden (jede 2. Iteration) automatisch refreshen
                    hist_counter += 1
                    if hist_counter % 2 == 0:
                        try:
                            self._refresh_history()
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(5)
        threading.Thread(target=_stat_tick, daemon=True).start()

        # Logger-Callback für Live-Updates
        # [HAENGER LOG-WARTESCHLANGE 17.10.2026] Vorher rief jeder log.*()-Aufruf - aus JEDEM
        # Thread - self.after() auf. tkinter laesst den Thread dabei warten, bis der
        # Fenster-Thread den Aufruf abarbeitet, und core/logger.py ruft die Rueckrufe
        # VOR dem Schreiben in system.log. Am 16.10.2026 ab 09:08 UTC stand der
        # Fenster-Thread, und mit ihm standen Handelsablauf, Stopp-Ueberwachung und
        # auto_save 35 h lang (pruefstand/berichte/2026-10-17_v6_haenger.md).
        # Jetzt reiht der Rueckruf die Zeile nur ein und kehrt sofort zurueck; der
        # Fenster-Thread holt sie alle 250 ms selbst ab. Haengt das Fenster, haengt
        # nur noch das Fenster. Voller Puffer: nur die ANZEIGE verliert Zeilen.
        import queue as _log_q
        from core.logger import log
        self._log_warteschlange = _log_q.Queue(maxsize=2000)

        def _log_einreihen(entry):
            try:
                self._log_warteschlange.put_nowait(entry)
            except _log_q.Full:
                pass

        def _log_abholen():
            try:
                for _ in range(200):
                    e = self._log_warteschlange.get_nowait()
                    self._add_log(f"[{e['module']}] {e['msg']}")
            except _log_q.Empty:
                pass
            except Exception:
                pass
            try:
                self.after(250, _log_abholen)
            except Exception:
                pass

        log.add_callback(_log_einreihen)
        self.after(250, _log_abholen)

    def _update_stats(self):
        try:
            # Balance direkt vom Execution Engine holen (funktioniert immer)
            try:
                bal = self.engine.execution.get_balance()
                balance = bal.get("total", {})
            except Exception:
                balance = {}

            usdc = balance.get("USDC", 0) + balance.get("USDT", 0)
            btc = balance.get("BTC", 0)

            self.after(0, lambda u=usdc: self.stat_labels["usdc"].configure(text=f"{u:,.2f}"))

            # P&L (NUR Trade-P&L, NICHT BTC-Akkumulation!)
            try:
                stats = self.engine.journal.get_stats()
                # Nur SELL-Trades mit echtem PnL zaehlen
                pnl = sum((t.get("pnl") or 0) for t in self.engine.journal.get_all()
                         if t.get("type") in ("SELL", "sell") and isinstance(t.get("pnl"), (int, float)))
            except Exception:
                pnl = 0
            pnl_color = CLR_GREEN if pnl >= 0 else CLR_RED
            self.after(0, lambda p=pnl, c=pnl_color: self.stat_labels["pnl"].configure(
                text=f"{p:+.2f} $", text_color=c))

            # BTC (Akkumulator oder Balance)
            try:
                acc_btc = self.engine.btc_accumulator.total_btc
                if acc_btc > 0:
                    btc = acc_btc
            except Exception:
                pass
            self.after(0, lambda b=btc: self.stat_labels["btc"].configure(text=f"{b:.8f}"))

            # Strategie
            try:
                brain = self.engine.strategy_brain.get_status()
                strat_name = brain.get("name", "Multi-Signal")
            except Exception:
                strat_name = "–"
            self.after(0, lambda s=strat_name: self.stat_labels["strategy"].configure(text=s))

            # Zyklus
            try:
                cycle = self.engine.cycle_theory.get_status()
                cycle_text = f"{cycle.get('phase', '?')} | {cycle.get('mode', '?')}"
            except Exception:
                cycle_text = "–"
            self.after(0, lambda c=cycle_text: self.stat_labels["cycle"].configure(text=c))

            # Agents + Trades (BUY/SELL + offene Positionen)
            try:
                all_trades = self.engine.journal.get_all()
                buys = sum(1 for t in all_trades if t.get("type") in ("BUY", "buy"))
                sells = sum(1 for t in all_trades if t.get("type") in ("SELL", "sell"))
                open_pos = len([v for v in self.engine.risk_engine.open_positions.values() if v.get("active")])
                self.after(0, lambda b=buys, s=sells, op=open_pos:
                    self.stat_labels["agents"].configure(text=f"{b}B/{s}S | {op} offen"))
            except Exception:
                self.after(0, lambda: self.stat_labels["agents"].configure(text="–"))

            # Uptime
            if self.is_running:
                try:
                    uptime = self.engine.health.get_uptime()
                    self.after(0, lambda u=uptime: self.uptime_lbl.configure(text=f"Uptime: {u}"))
                except Exception:
                    pass

        except Exception as e:
            # Bei Fehler trotzdem weiter versuchen
            pass

    def _update_agents(self):
        if not self.is_running:
            for key, lbl in self.agent_labels.items():
                self.after(0, lambda l=lbl: l.configure(text="⏳ Bot nicht gestartet", text_color="#555"))
            return
        for key, lbl in self.agent_labels.items():
            try:
                text, color = "✅ Bereit", CLR_GREEN
                if key == "data":
                    cached = len(self.engine.data_agent.price_cache)
                    text = f"✅ {cached} Coins geladen"
                elif key == "signal":
                    strat = self.engine.signal_agent.current_strategy
                    text = f"✅ Strategie: {strat}"
                elif key == "risk":
                    opos = len([v for v in self.engine.risk_engine.open_positions.values() if v.get("active")])
                    text = f"✅ {opos} Positionen offen"
                elif key == "brain":
                    name = self.engine.strategy_brain.current_strategy or "?"
                    text = f"✅ {name}"
                elif key == "cycle":
                    phase = self.engine.cycle_theory.current_phase
                    text = f"✅ {phase}"
                    color = CLR_CYAN
                elif key == "execution":
                    mode = self.engine.config.trading.mode
                    text = f"✅ {mode.upper()}"
                elif key == "btc_acc":
                    btc = self.engine.btc_accumulator.total_btc
                    sp = "AN" if self.engine.btc_accumulator.sparplan_active else "AUS"
                    text = f"₿ {btc:.6f} | Sparplan: {sp}"
                    color = CLR_ORANGE
                elif key == "rl":
                    n = len(self.engine.rl_feedback.history)
                    text = f"✅ {n} Trades gelernt"
                elif key == "regime":
                    text = f"✅ {self.engine.regime_detector.current_regime}"
                    color = CLR_CYAN
                elif key == "adaptive":
                    wr = self.engine.adaptive_sizer.get_win_rate()
                    text = f"✅ WR: {wr:.0f}%"
                elif key == "arb":
                    n = len(self.engine.multi_exchange.exchanges)
                    text = f"✅ {n} Boersen"
                elif key == "smart":
                    n = len(self.engine.smart_entry.pending)
                    text = f"✅ {n} pending"
                self.after(0, lambda l=lbl, t=text, c=color: l.configure(text=t, text_color=c))
            except Exception:
                self.after(0, lambda l=lbl: l.configure(text="✅ Aktiv", text_color=CLR_GREEN))
