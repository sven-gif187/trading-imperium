"""
Sensei-Mode - Der Trading-Lehrer von Trading Imperium V6

Zwei Faehigkeiten:
A) ERKLAERER: Uebersetzt Signal-Begruendungen in Klartext-Deutsch
   (liest die [SIGNAL]-Zeilen aus data_store/system.log)
B) TRAINER: Analysiert abgeschlossene Trades aus trades_v5.json
   und erzeugt Tages-Lektionen mit konkreten Verbesserungsideen.

Greift NIRGENDS in die Trading-Logik ein - liest nur Dateien.
Lektionen werden zusaetzlich in SENSEI_LEKTIONEN.md gespeichert.
"""
import os
import re
import json
from datetime import datetime
from collections import defaultdict

try:
    from core.logger import log
except Exception:
    class _Log:
        def info(self, *a, **kw): pass
        def warn(self, *a, **kw): pass
    log = _Log()


# ============================================================
# LEXIKON: Indikator -> Klartext-Erklaerung
# ============================================================
LEXIKON = {
    "RSI": ("Relative Strength Index (0-100). Misst, wie stark zuletzt gekauft/verkauft "
            "wurde. Unter 30 = ueberverkauft (oft folgt Erholung), ueber 70 = ueberkauft."),
    "MACD": ("Moving Average Convergence Divergence. Vergleicht kurzen und langen "
             "Durchschnitt. 'Bullish cross' = kurzfristiger Schwung dreht nach oben."),
    "ADX": ("Average Directional Index. Misst die STAERKE eines Trends (nicht die "
            "Richtung). Ueber 25 = echter Trend, unter 20 = Seitwaertsgeschiebe."),
    "EXTREME FEAR": ("Fear & Greed Index unter 25. Die Masse panikt - historisch sind "
                     "das oft die besten Kaufzonen ('Be greedy when others are fearful')."),
    "Orderbook": ("Kaufdruck im Orderbuch: Es liegen mehr/groessere Kauforders als "
                  "Verkaufsorders im Buch - kurzfristig druecken Kaeufer den Preis."),
    "Divergenz": ("Bullische RSI-Divergenz: Preis macht ein tieferes Tief, RSI aber ein "
                  "hoeheres Tief. Der Abwaertsdruck laesst nach - klassisches Umkehrsignal."),
    "VWAP": ("Volume Weighted Average Price - volumengewichteter Durchschnittspreis. "
             "Preis darueber = Kaeufer haben die Kontrolle."),
    "Volume-Spike": ("Handelsvolumen deutlich ueber Normal (z.B. 2x). Grosse Marktteilnehmer "
                     "werden aktiv - Bewegungen mit Volumen sind glaubwuerdiger."),
    "Grid": ("Grid-Bot: kauft automatisch an vorberechneten Preis-Leveln innerhalb eines "
             "Bandes (Bollinger) und verkauft hoeher - verdient an Seitwaertsbewegung."),
    "Score": ("Signal-Score 0-10: Wie viele Kaufargumente zusammenkommen. Je hoeher, "
              "desto mehr Indikatoren zeigen in dieselbe Richtung."),
}

# Muster in den Begruendungs-Strings -> (Lexikon-Key, Klartext-Satz)
_REASON_PATTERNS = [
    (r"RSI stark oversold \((\d+)\)", "RSI",
     "RSI bei {0} - STARK ueberverkauft. Der Abverkauf ist ueberzogen, "
     "die Chance auf eine Gegenbewegung ist statistisch erhoeht."),
    (r"RSI oversold \((\d+)\)", "RSI",
     "RSI bei {0} - ueberverkauft. Es wurde zuletzt viel verkauft, "
     "oft folgt darauf eine Erholung."),
    (r"RSI niedrig \((\d+)\)", "RSI",
     "RSI bei {0} - niedrig, aber noch nicht extrem. Leichtes Kaufargument."),
    (r"MACD bullish cross", "MACD",
     "MACD kreuzt nach oben - der kurzfristige Schwung dreht gerade ins Positive."),
    (r"MACD positiv", "MACD",
     "MACD steht im Plus - der kurzfristige Schwung ist bereits aufwaerts gerichtet."),
    (r"EMA-Trend up", "MACD",
     "Die gleitenden Durchschnitte (EMA) zeigen nach oben - "
     "der uebergeordnete Kurztrend ist aufwaerts."),
    (r"Starker Trend \(ADX (\d+)\)", "ADX",
     "ADX bei {0} - hier laeuft ein echter Trend, keine Zufallsbewegung."),
    (r"EXTREME FEAR \((\d+)\)", "EXTREME FEAR",
     "Fear & Greed bei {0} - die Masse ist in Panik. Genau dann sind "
     "Preise historisch am guenstigsten."),
    (r"Orderbook Kaufdruck \(\+([\d.]+)\)", "Orderbook",
     "Im Orderbuch liegt Kaufdruck (+{0}) - kurzfristig schieben Kaeufer den Preis."),
    (r"Bullische RSI-Divergenz", "Divergenz",
     "Bullische Divergenz: Preis faellt noch, aber der RSI steigt schon - "
     "der Verkaufsdruck laesst unter der Oberflaeche nach. Starkes Umkehrsignal."),
    (r"Volume-Spike \(([\d.]+)x\)", "Volume-Spike",
     "Volumen {0}-fach ueber Normal - grosse Adressen handeln mit, "
     "das Signal hat Substanz."),
    (r"Ueber VWAP", "VWAP",
     "Preis ueber dem volumengewichteten Durchschnitt - die Kaeufer fuehren."),
]


class Sensei:
    """Trading-Lehrer: erklaert Signale und erzeugt Lektionen aus Trade-Daten."""

    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root = project_root
        self.log_path = os.path.join(self.root, "data_store", "system.log")
        self.trades_path = os.path.join(self.root, "data_store", "trades_v5.json")
        self.lektionen_path = os.path.join(self.root, "SENSEI_LEKTIONEN.md")
        self.lessons_json_path = os.path.join(self.root, "data_store",
                                              "sensei_lessons.json")

    # ========================================================
    # A) ERKLAERER
    # ========================================================
    def explain_reason_string(self, reason: str) -> list:
        """Zerlegt 'RSI oversold (34) + ADX...' in Klartext-Saetze."""
        out = []
        for pattern, _key, template in _REASON_PATTERNS:
            m = re.search(pattern, reason)
            if m:
                out.append(template.format(*m.groups()))
        if not out:
            out.append("Begruendung: " + reason)
        return out

    def explain_last_signals(self, max_signals: int = 3) -> str:
        """Liest die letzten [SIGNAL]-Zeilen aus system.log und erklaert sie."""
        try:
            if not os.path.exists(self.log_path):
                return "Kein system.log gefunden - Bot schon mal gestartet?"
            # Nur Datei-Ende lesen (Log kann gross sein)
            size = os.path.getsize(self.log_path)
            with open(self.log_path, "rb") as f:
                f.seek(max(0, size - 200_000))
                tail = f.read().decode("utf-8", errors="replace")

            sig_re = re.compile(
                r"\[SIGNAL\]\s+(\S+):\s+Score\s+(\d+)/10\s+\((\d+)%\)\s+->\s+"
                r"(BUY|SELL)\s+([\d.]+)\$\s+\|\s+(.+)")
            found = sig_re.findall(tail)
            if not found:
                return "Keine [SIGNAL]-Zeilen im Log gefunden."

            # Pro Coin nur das letzte Signal, dann die juengsten nehmen
            latest = {}
            for sym, score, pct, side, amt, reason in found:
                latest[sym] = (sym, int(score), side, float(amt), reason.strip())
            picks = list(latest.values())[-max_signals:]

            lines = []
            for sym, score, side, amt, reason in picks:
                lines.append(f"=== {sym}: {side} {amt:.2f}$ (Score {score}/10) ===")
                if score >= 7:
                    lines.append("Einordnung: STARKES Signal - viele Argumente zeigen "
                                 "in dieselbe Richtung.")
                elif score >= 5:
                    lines.append("Einordnung: solides Signal - mehrere Argumente, "
                                 "aber kein Selbstlaeufer.")
                else:
                    lines.append("Einordnung: SCHWACHES Signal - wenige Argumente. "
                                 "Solche Trades haben statistisch die niedrigste Trefferquote.")
                for satz in self.explain_reason_string(reason):
                    lines.append("  -> " + satz)
                lines.append("")
            return "\n".join(lines).strip()
        except Exception as e:
            return "Erklaerungs-Fehler: " + str(e)[:120]

    def explain_term(self, term: str) -> str:
        """Lexikon-Nachschlag fuer einen Begriff."""
        t = term.strip().upper()
        for key, text in LEXIKON.items():
            if key.upper() in t or t in key.upper():
                return key + ": " + text
        return "Begriff nicht im Lexikon. Vorhanden: " + ", ".join(LEXIKON.keys())

    # ========================================================
    # B) TRAINER
    # ========================================================
    @staticmethod
    def _get(trade: dict, *keys, default=None):
        """Robuster Feldzugriff (Feldnamen koennen variieren)."""
        for k in keys:
            if k in trade and trade[k] is not None:
                return trade[k]
        return default

    def _load_trades(self) -> list:
        if not os.path.exists(self.trades_path):
            return []
        try:
            with open(self.trades_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("trades", [])
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def daily_lesson(self, write_md: bool = True) -> str:
        """Analysiert trades_v5.json und erzeugt eine Lektion.

        write_md=False: nur JSON-Datenbank aktualisieren (fuer Auto-Lauf),
        kein neuer Eintrag in SENSEI_LEKTIONEN.md."""
        trades = self._load_trades()
        closed = []
        for t in trades:
            if not isinstance(t, dict):
                continue
            pnl = self._get(t, "pnl", "profit", "realized_pnl", "pnl_usd")
            if pnl is None:
                continue
            try:
                pnl = float(pnl)
            except (TypeError, ValueError):
                continue
            closed.append({
                "symbol": self._get(t, "symbol", "pair", "coin", default="?"),
                "pnl": pnl,
                "strategy": self._get(t, "active_strategy", "strategy", default="?"),
                "score": self._get(t, "signal_score", "score"),
                "regime": self._get(t, "market_regime", "regime", default="?"),
                "fg": self._get(t, "fear_greed_at_entry", "fear_greed"),
            })

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not closed:
            return (f"SENSEI-LEKTION ({ts})\n"
                    "Noch keine abgeschlossenen Trades im Journal - der Testlauf "
                    "sammelt gerade Daten. Geduld ist die erste Lektion des Traders: "
                    "Wer dem System Zeit gibt, bekommt belastbare Zahlen statt Bauchgefuehl.")

        wins = [t for t in closed if t["pnl"] > 0]
        losses = [t for t in closed if t["pnl"] <= 0]
        win_rate = len(wins) / len(closed) * 100
        total = sum(t["pnl"] for t in closed)
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
        rr = abs(avg_win / avg_loss) if avg_loss else 0

        # [FIX 05.08.2026] Mindeststichprobe, bevor aus Kennzahlen eine
        # Handlungsempfehlung wird.
        # BEFUND: Die Lektion unten ("Dein Risk/Reward traegt - du darfst
        # mehr Trades verlieren als gewinnen") loeste bei rr>=1.5 und
        # win_rate>=40 aus - das kann bei ZWEI abgeschlossenen Trades
        # passieren, einem Gewinn und einem Verlust. Eine Win-Rate aus zwei
        # Trades ist keine Kennzahl, sondern eine Zufallszahl mit
        # Nachkommastelle.
        # SCHWELLEN aus der eigenen Messreihe (docs/messungen_2026-07):
        # bei n=30 ist das 95-%-Konfidenzintervall einer Trefferquote rund
        # +/-18 Prozentpunkte breit, bei n=20.129 waren es +/-4. Unter 30
        # Trades laesst sich eine Quote nicht von Rauschen unterscheiden;
        # unter 10 ist sie reine Anekdote.
        MIN_ANEKDOTE = 10       # darunter: keine Kennzahl ausweisen
        MIN_BELASTBAR = 30      # darunter: keine Handlungsempfehlung
        n = len(closed)

        if n < MIN_ANEKDOTE:
            hinweis = (f"ACHTUNG: nur {n} abgeschlossene Trades. Die Quoten "
                       f"unten sind NICHT belastbar - bei so kleiner "
                       f"Stichprobe entscheidet der Zufall, nicht die "
                       f"Strategie. Keine Lektion, keine Empfehlung.")
        elif n < MIN_BELASTBAR:
            hinweis = (f"VORBEHALT: {n} abgeschlossene Trades. Das 95-%-"
                       f"Intervall einer Win-Rate ist hier noch rund "
                       f"+/-20 Prozentpunkte breit. Richtung moeglich, "
                       f"Groesse nicht.")
        else:
            hinweis = f"Stichprobe: {n} abgeschlossene Trades."

        lines = [f"SENSEI-LEKTION ({ts})",
                 hinweis,
                 f"Abgeschlossene Trades: {n} | Win-Rate: {win_rate:.0f}% | "
                 f"P&L gesamt: {total:+.2f}$",
                 f"Schnitt-Gewinn: {avg_win:+.2f}$ | Schnitt-Verlust: {avg_loss:+.2f}$ | "
                 f"Risk/Reward: {rr:.2f}", ""]

        # Unterhalb der Anekdoten-Schwelle werden die Lektionen uebersprungen,
        # aber Speichern und DB-Eintrag laufen weiter wie sonst - sonst
        # entstuende eine Luecke in der Historie.
        _lektionen_erlaubt = n >= MIN_ANEKDOTE
        if not _lektionen_erlaubt:
            lines.append("Sobald mindestens 30 Trades abgeschlossen sind, "
                         "werden hier wieder Lektionen abgeleitet. Bis dahin "
                         "waere jede Empfehlung geraten.")

        # Lektion 1: Win-Rate vs Risk/Reward
        if _lektionen_erlaubt and rr >= 1.5 and win_rate >= 40:
            lines.append("LEKTION: Dein Risk/Reward traegt - Gewinne sind im Schnitt "
                         f"{rr:.1f}x groesser als Verluste. Bei dieser Quote darfst du "
                         "sogar mehr Trades verlieren als gewinnen und bist trotzdem profitabel.")
        elif _lektionen_erlaubt and rr < 1.0 and closed:
            lines.append("LEKTION: Deine Verluste sind im Schnitt GROESSER als deine "
                         "Gewinne. Das frisst jede Win-Rate auf. Pruefen: Werden Gewinne "
                         "zu frueh mitgenommen (Trailing zu eng?) oder Verluste zu lange "
                         "gehalten?")

        # Lektion 2: Score-Auswertung
        scored = [t for t in closed if t["score"] is not None]
        if len(scored) >= 5:
            low = [t for t in scored if float(t["score"]) <= 4]
            high = [t for t in scored if float(t["score"]) >= 7]
            # [FIX 05.08.2026] Auch die Untergruppen brauchen eine
            # Mindeststichprobe. Vorher genuegte EIN Trade in der Gruppe:
            # im Lauf vom 05.08. stand hier "Trades mit Score >=7: 4 Stueck,
            # Win-Rate 100%" - vier Trades als Kennzahl, mit
            # Handlungsempfehlung daneben. Die Untergruppen sind zwangslaeufig
            # kleiner als die Gesamtstichprobe, deshalb eine eigene Schwelle.
            MIN_GRUPPE = 20
            if low:
                lwr = sum(1 for t in low if t["pnl"] > 0) / len(low) * 100
                if len(low) < MIN_GRUPPE:
                    lines.append(f"SCORE-CHECK: Trades mit Score <=4: "
                                 f"{len(low)} Stueck - zu wenige fuer eine "
                                 f"belastbare Quote (Richtwert {MIN_GRUPPE}). "
                                 f"Roh: {lwr:.0f}%, keine Ableitung.")
                else:
                    lines.append(f"SCORE-CHECK: Trades mit Score <=4: {len(low)} Stueck, "
                                 f"Win-Rate {lwr:.0f}%. " +
                                 ("Schwache Signale verlieren ueberdurchschnittlich - "
                                  "Mindest-Score anheben waere eine Ueberlegung."
                                  if lwr < win_rate else
                                  "Halten sich ueberraschend gut."))
            if high:
                hwr = sum(1 for t in high if t["pnl"] > 0) / len(high) * 100
                if len(high) < MIN_GRUPPE:
                    lines.append(f"SCORE-CHECK: Trades mit Score >=7: "
                                 f"{len(high)} Stueck - zu wenige fuer eine "
                                 f"belastbare Quote (Richtwert {MIN_GRUPPE}). "
                                 f"Roh: {hwr:.0f}%, keine Ableitung.")
                else:
                    lines.append(f"SCORE-CHECK: Trades mit Score >=7: {len(high)} Stueck, "
                                 f"Win-Rate {hwr:.0f}%.")

        # Lektion 3: Strategie-Ranking
        by_strat = defaultdict(list)
        for t in closed:
            by_strat[t["strategy"]].append(t["pnl"])
        ranking = sorted(by_strat.items(), key=lambda kv: -sum(kv[1]))
        if len(ranking) >= 2:
            best_s, best_p = ranking[0][0], sum(ranking[0][1])
            worst_s, worst_p = ranking[-1][0], sum(ranking[-1][1])
            lines.append(f"STRATEGIEN: Beste: {best_s} ({best_p:+.2f}$) | "
                         f"Schwaechste: {worst_s} ({worst_p:+.2f}$).")

        # Lektion 4: bester/schlechtester Trade
        best = max(closed, key=lambda t: t["pnl"])
        worst = min(closed, key=lambda t: t["pnl"])
        lines.append(f"EXTREME: Bester Trade {best['symbol']} {best['pnl']:+.2f}$ | "
                     f"Schlechtester {worst['symbol']} {worst['pnl']:+.2f}$.")

        text = "\n".join(lines)
        if write_md:
            self._save_lesson(text)

        # === SENSEI-DB: strukturierte Kennzahlen fuer die Auswertung ===
        by_strat_pnl = {k: round(sum(v), 2) for k, v in by_strat.items()}
        # Coin-Edge-Vorbereitung: Kennzahlen PRO COIN (Vorbild Freqtrade Edge)
        by_symbol = defaultdict(list)
        for t in closed:
            by_symbol[t["symbol"]].append(t["pnl"])
        by_symbol_stats = {}
        for sym, pnls in by_symbol.items():
            sym_wins = [p for p in pnls if p > 0]
            by_symbol_stats[sym] = {
                "trades": len(pnls),
                "win_rate": round(len(sym_wins) / len(pnls) * 100, 1),
                "pnl": round(sum(pnls), 2),
            }
        low_scored = [t for t in scored if float(t["score"]) <= 4]
        high_scored = [t for t in scored if float(t["score"]) >= 7]
        metrics = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "closed_trades": len(closed),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "risk_reward": round(rr, 2),
            "by_strategy_pnl": by_strat_pnl,
            "by_symbol": by_symbol_stats,
            "low_score_trades": len(low_scored),
            "low_score_winrate": round(sum(1 for t in low_scored if t["pnl"] > 0)
                                       / len(low_scored) * 100, 1) if low_scored else None,
            "high_score_trades": len(high_scored),
            "high_score_winrate": round(sum(1 for t in high_scored if t["pnl"] > 0)
                                        / len(high_scored) * 100, 1) if high_scored else None,
            "best_trade": {"symbol": best["symbol"], "pnl": round(best["pnl"], 2)},
            "worst_trade": {"symbol": worst["symbol"], "pnl": round(worst["pnl"], 2)},
        }
        self._save_lesson_json(metrics)
        return text

    def _save_lesson_json(self, metrics: dict):
        """Haelt pro Datum genau einen Eintrag (letzter Stand des Tages)."""
        try:
            data = []
            if os.path.exists(self.lessons_json_path):
                try:
                    with open(self.lessons_json_path, "r", encoding="utf-8") as f:
                        _raw = f.read().strip()
                    data = json.loads(_raw) if _raw else []
                except Exception as _e:
                    log.warn("SENSEI", "Lektions-DB leer/kaputt - starte neu ("
                             + str(_e)[:50] + ")")
                    data = []
            if not isinstance(data, list):
                data = []
            data = [e for e in data if e.get("date") != metrics["date"]]
            data.append(metrics)
            tmp = self.lessons_json_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.lessons_json_path)
            log.info("SENSEI", "Lektions-DB aktualisiert ("
                     + str(len(data)) + " Tage)")
        except Exception as e:
            log.warn("SENSEI", "Lektions-DB-Fehler: " + str(e)[:80])

    def _save_lesson(self, text: str):
        try:
            with open(self.lektionen_path, "a", encoding="utf-8") as f:
                f.write("\n---\n\n" + text + "\n")
            log.info("SENSEI", "Lektion gespeichert: SENSEI_LEKTIONEN.md")
        except Exception as e:
            log.warn("SENSEI", "Speichern fehlgeschlagen: " + str(e)[:80])
