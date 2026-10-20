"""
Trading Imperium V5 – LLM Context Agent
Nutzt OpenAI GPT für: News-Zusammenfassung, Regime-Kontext,
Trade-Erklärungen, Portfolio-Konflikte erkennen, Journaling.
Ist KEIN eigenständiger Trader – ergänzt und kommentiert Signale.
"""
import os
import time
import json
import threading
from typing import Dict, Optional, List
from datetime import datetime, timezone
from core.events import DecisionIntent, MarketSnapshot, Side, CyclePhase
from core.logger import log


class NewsAnalyzer:
    """Holt und analysiert Crypto-News. Kostenlos, kein API-Key nötig."""

    BULLISH = ["rally","surge","bull","gain","jump","soar","high","rise","breakout",
               "buy","accumulate","etf","approval","adopt","pump","positive","growth"]
    BEARISH = ["crash","drop","bear","fall","dump","sell","fear","risk","ban","hack",
               "scam","fraud","loss","down","decline","warning","collapse","crisis","liquidat"]

    def __init__(self):
        self.headlines = []
        self.sentiment_score = 0.5  # 0=bearish, 1=bullish
        self.sentiment_label = "NEUTRAL"
        self.btc_sentiment = "neutral"
        self.bull_count = 0
        self.bear_count = 0
        self.last_fetch = 0

    def fetch(self) -> Dict:
        """Holt News und berechnet Sentiment. Kostenlos!"""
        import requests
        now = time.time()
        if now - self.last_fetch < 300:  # Max alle 5 Min
            return self.get_summary()

        self.last_fetch = now
        self.headlines = []
        self.bull_count = 0
        self.bear_count = 0

        # 1. News holen
        try:
            r = requests.get("https://cryptocurrency.cv/api/news?limit=15", timeout=8)
            if r.status_code == 200:
                data = r.json()
                articles = data if isinstance(data, list) else data.get("articles", data.get("items", []))
                for a in articles[:15]:
                    title = a.get("title", "") or a.get("headline", "")
                    if title:
                        self.headlines.append(title)
        except Exception:
            pass

        # 2. BTC Sentiment
        try:
            r = requests.get("https://cryptocurrency.cv/api/ai/sentiment?asset=BTC", timeout=8)
            if r.status_code == 200:
                data = r.json()
                self.btc_sentiment = data.get("label", "neutral").lower()
                btc_score = float(data.get("score", 0.5))
            else:
                btc_score = 0.5
        except Exception:
            btc_score = 0.5

        # 3. Lokale Keyword-Analyse
        for title in self.headlines:
            t = title.lower()
            is_bull = any(w in t for w in self.BULLISH)
            is_bear = any(w in t for w in self.BEARISH)
            if is_bull and not is_bear:
                self.bull_count += 1
            elif is_bear and not is_bull:
                self.bear_count += 1

        total = self.bull_count + self.bear_count
        local_score = (self.bull_count / total) if total > 0 else 0.5

        # 4. Kombiniert
        self.sentiment_score = round(btc_score * 0.6 + local_score * 0.4, 2) if btc_score != 0.5 else local_score

        if self.sentiment_score >= 0.7:
            self.sentiment_label = "BULLISH"
        elif self.sentiment_score >= 0.55:
            self.sentiment_label = "LEICHT BULLISH"
        elif self.sentiment_score <= 0.3:
            self.sentiment_label = "BEARISH"
        elif self.sentiment_score <= 0.45:
            self.sentiment_label = "LEICHT BEARISH"
        else:
            self.sentiment_label = "NEUTRAL"

        log.info("NEWS", f"{self.sentiment_label} (Score: {self.sentiment_score}) | "
                         f"Bull:{self.bull_count} Bear:{self.bear_count} | BTC: {self.btc_sentiment}")
        return self.get_summary()

    def get_summary(self) -> Dict:
        return {
            "label": self.sentiment_label,
            "score": self.sentiment_score,
            "btc": self.btc_sentiment,
            "bull": self.bull_count,
            "bear": self.bear_count,
            "headlines": self.headlines[:10],
        }


class LLMContextAgent:
    """LLM-Agent für Kontext, Erklärungen und Analyse. Nutzt OpenAI GPT."""

    def __init__(self, config):
        self.config = config
        # Defensive: getattr mit Fallback falls AIConfig diese Felder nicht hat
        ai_cfg = getattr(config, 'ai', None)
        if ai_cfg is not None:
            # API-Key aus .env laden falls noetig
            try:
                if hasattr(ai_cfg, 'load_from_env'):
                    ai_cfg.load_from_env()
            except Exception:
                pass
            self.api_key = getattr(ai_cfg, 'openai_key', '') or os.environ.get('OPENAI_API_KEY', '')
            self.model = getattr(ai_cfg, 'openai_model', 'gpt-4o-mini')
        else:
            # Fallback: Direkt aus .env
            self.api_key = os.environ.get('OPENAI_API_KEY', '')
            self.model = 'gpt-4o-mini'

        self.news = NewsAnalyzer()
        self.last_context = ""
        self.last_analysis_time = 0
        self.trade_explanations = []  # Letzte Erklärungen
        self.context_cache = {}

    def _call_llm(self, system_prompt: str, user_msg: str, max_tokens: int = 500) -> str:
        """Ruft die OpenAI API auf. Returns Antwort-Text."""
        if not self.api_key:
            return ""
        try:
            import requests
            r = requests.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "max_tokens": max_tokens, "temperature": 0.3,
                      "messages": [{"role": "system", "content": system_prompt},
                                   {"role": "user", "content": user_msg}]},
                timeout=15)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            else:
                log.warn("LLM", f"API Fehler: {r.status_code}")
                return ""
        except Exception as e:
            log.warn("LLM", f"API Fehler: {str(e)[:60]}")
            return ""

    def analyze_market_context(self, snapshots: List[MarketSnapshot],
                                cycle_phase: str = "", fear_greed: int = 50) -> str:
        """Erstellt eine komplette Markt-Kontext-Analyse."""
        now = time.time()
        if now - self.last_analysis_time < 300:  # Max alle 5 Min
            return self.last_context

        # News holen
        news = self.news.fetch()

        # Marktdaten zusammenfassen
        market_lines = []
        for snap in snapshots[:6]:
            ind = snap.indicators
            market_lines.append(f"{snap.symbol}: {snap.close:,.2f}$ | RSI:{ind.get('rsi', 50):.0f} "
                               f"ADX:{ind.get('adx', 20):.0f} | {snap.regime.value}")

        market_str = "\n".join(market_lines) if market_lines else "Keine Marktdaten"
        news_str = "\n".join(news.get("headlines", [])[:5]) if news.get("headlines") else "Keine News"

        system = (
            "Du bist ein Crypto-Marktanalyst. Deutsch, kurz (max 150 Wörter), anfängerfreundlich.\n"
            "Analysiere: Marktlage, News-Sentiment, Zyklusphase, Risiken und Chancen.\n"
            "Gib eine klare Empfehlung: KAUFEN / HALTEN / VORSICHT / NICHT KAUFEN.\n"
            "Begründe kurz warum."
        )

        user = (
            f"MARKTDATEN:\n{market_str}\n\n"
            f"NEWS-SENTIMENT: {news.get('label', 'NEUTRAL')} (Score: {news.get('score', 0.5)})\n"
            f"Headlines:\n{news_str}\n\n"
            f"ZYKLUSPHASE: {cycle_phase}\n"
            f"FEAR & GREED: {fear_greed}\n\n"
            f"Was ist deine Einschätzung?"
        )

        result = self._call_llm(system, user, max_tokens=300)
        if result:
            self.last_context = result
            self.last_analysis_time = now
            log.info("LLM", f"Markt-Analyse erstellt ({len(result)} Zeichen)")
        else:
            # Offline-Fallback
            self.last_context = self._offline_context(news, cycle_phase, fear_greed, snapshots)

        return self.last_context

    def explain_trade(self, intent: DecisionIntent, snapshot: MarketSnapshot = None) -> str:
        """Erklärt einen Trade-Vorschlag menschenlesbar."""
        if not self.api_key:
            return self._offline_explain(intent, snapshot)

        ind = snapshot.indicators if snapshot else {}
        system = (
            "Du bist ein Trading-Coach. Erkläre den Trade in 2-3 Sätzen auf Deutsch.\n"
            "Anfängerfreundlich: Was passiert, warum, und was kann schief gehen."
        )
        user = (
            f"Trade: {intent.side.value} {intent.symbol}\n"
            f"Betrag: {intent.amount_usd:.2f}$\n"
            f"Preis: {intent.entry_price:,.2f}$\n"
            f"Strategie: {intent.strategy_name}\n"
            f"Grund: {intent.entry_reason}\n"
            f"Score: {intent.score}/10 (Confidence: {intent.confidence:.0%})\n"
            f"RSI: {ind.get('rsi', '?')} | ADX: {ind.get('adx', '?')}\n"
            f"Stop-Loss: {intent.stop_loss:,.2f}$" if intent.stop_loss else ""
        )

        result = self._call_llm(system, user, max_tokens=150)
        if result:
            self.trade_explanations.append({
                "symbol": intent.symbol, "side": intent.side.value,
                "explanation": result, "time": datetime.now().isoformat()
            })
            if len(self.trade_explanations) > 50:
                self.trade_explanations = self.trade_explanations[-50:]
        return result or self._offline_explain(intent, snapshot)

    def check_portfolio_conflicts(self, positions: List[Dict], new_intent: DecisionIntent) -> str:
        """Prüft ob der neue Trade Portfolio-Konflikte erzeugt."""
        if not positions:
            return ""

        # Einfache Korrelations-Prüfung (ohne LLM)
        asset = new_intent.symbol.split("/")[0]
        l1_coins = {"BTC", "ETH", "SOL", "ADA", "AVAX", "DOT", "NEAR", "ATOM", "SUI", "APT"}
        defi_coins = {"UNI", "LINK", "OP", "ARB", "INJ"}
        meme_coins = {"DOGE", "RENDER"}

        active_assets = [p.get("coin", "") for p in positions]

        # Zu viele L1s?
        l1_count = sum(1 for a in active_assets if a in l1_coins)
        if asset in l1_coins and l1_count >= 3:
            return f"Warnung: Bereits {l1_count} L1-Coins offen. {asset} erhöht Korrelationsrisiko."

        # Zu viele DeFi?
        defi_count = sum(1 for a in active_assets if a in defi_coins)
        if asset in defi_coins and defi_count >= 2:
            return f"Warnung: Bereits {defi_count} DeFi-Coins. Sektor-Konzentration!"

        return ""

    def generate_daily_review(self, stats: Dict, trades: List[Dict]) -> str:
        """Generiert einen täglichen Trade-Review."""
        if not self.api_key:
            return self._offline_daily_review(stats)

        trades_str = ""
        for t in trades[-10:]:
            pnl = t.get("pnl", "")
            pnl_s = f" P&L:{pnl:+.2f}$" if isinstance(pnl, (int, float)) else ""
            trades_str += f"{t.get('type', '?')} {t.get('coin', '?').split('/')[0]} @ {t.get('price', 0):,.0f}${pnl_s}\n"

        system = (
            "Du bist ein Trading-Journal-Analyst. Deutsch, kurz.\n"
            "Bewerte den Handelstag: Was lief gut, was schlecht, was lernen wir daraus?\n"
            "Max 100 Wörter."
        )
        user = (
            f"TAGES-STATISTIK:\n"
            f"Trades: {stats.get('total_trades', 0)} | Wins: {stats.get('wins', 0)} | "
            f"Losses: {stats.get('losses', 0)}\n"
            f"Win-Rate: {stats.get('win_rate', 0):.1f}%\n"
            f"P&L: {stats.get('total_pnl', 0):+.2f}$\n\n"
            f"TRADES:\n{trades_str}"
        )

        return self._call_llm(system, user, max_tokens=200)

    def answer_chat(self, question: str, context: Dict) -> str:
        """Beantwortet eine Chat-Frage mit vollem Kontext."""
        if not self.api_key:
            return self._offline_chat(question, context)

        news = self.news.get_summary()
        system = (
            f"Du bist ein persönlicher KI-Trading-Assistent. Deutsch, freundlich, einfach.\n"
            f"KONTEXT:\n"
            f"Balance: {context.get('usdc', 0):.2f} USDC\n"
            f"BTC: {context.get('btc', 0):.8f}\n"
            f"P&L: {context.get('pnl', 0):+.2f}$\n"
            f"Strategie: {context.get('strategy', '?')}\n"
            f"Regime: {context.get('regime', '?')}\n"
            f"Zyklus: {context.get('phase', '?')}\n"
            f"F&G: {context.get('fg', 50)}\n"
            f"News: {news.get('label', 'NEUTRAL')} ({news.get('score', 0.5)})\n"
            f"Antworte kurz (max 150 Wörter)."
        )

        return self._call_llm(system, question, max_tokens=300)

    # ========= OFFLINE FALLBACKS =========
    def _offline_context(self, news, cycle_phase, fg, snapshots):
        lines = [f"Zyklusphase: {cycle_phase}", f"Fear & Greed: {fg}"]
        label = news.get("label", "NEUTRAL")
        lines.append(f"News-Sentiment: {label} (Score: {news.get('score', 0.5)})")

        if fg < 20:
            lines.append("Extreme Fear – historisch eine gute DCA-Kaufzone.")
        elif fg > 75:
            lines.append("Extreme Greed – Vorsicht, Korrektur wahrscheinlich.")

        if "BEAR" in cycle_phase:
            lines.append("Bärenmarkt: Nur BTC+ETH, kleine Positionen, DCA bevorzugen.")
        elif cycle_phase == "ACCUMULATION":
            lines.append("Akkumulationsphase: Smart Money kauft leise.")

        return "\n".join(lines)

    def _offline_explain(self, intent, snapshot):
        ind = snapshot.indicators if snapshot else {}
        rsi = ind.get("rsi", 50)
        side = "kauft" if intent.side == Side.BUY else "verkauft"
        return (f"Der Bot {side} {intent.symbol.split('/')[0]} für {intent.amount_usd:.2f}$. "
                f"Grund: {intent.entry_reason}. RSI: {rsi:.0f}. "
                f"Score: {intent.score}/10.")

    def _offline_chat(self, question, context):
        q = question.lower()
        if any(w in q for w in ["markt", "lage", "wie sieht"]):
            return self._offline_context(self.news.get_summary(), context.get("phase", "?"), context.get("fg", 50), [])
        elif any(w in q for w in ["btc", "bitcoin", "sparplan"]):
            return f"BTC: {context.get('btc', 0):.8f} | Wert: {context.get('btc', 0) * context.get('btc_price', 70000):.2f}$"
        elif any(w in q for w in ["news", "nachrichten"]):
            ns = self.news.get_summary()
            return f"News: {ns.get('label', '?')} (Score: {ns.get('score', 0.5)}) | Bull:{ns.get('bull', 0)} Bear:{ns.get('bear', 0)}"
        return "Frag mich nach: Marktlage, BTC, News, Strategien, Zyklus."

    def _offline_daily_review(self, stats):
        wr = stats.get("win_rate", 0)
        pnl = stats.get("total_pnl", 0)
        if wr > 60 and pnl > 0:
            return f"Guter Tag! Win-Rate {wr:.0f}%, P&L {pnl:+.2f}$. Weiter so."
        elif pnl < 0:
            return f"Schwieriger Tag. P&L {pnl:+.2f}$. Strategien prüfen, Risiko reduzieren."
        return f"Durchschnittlicher Tag. Win-Rate {wr:.0f}%, P&L {pnl:+.2f}$."

    def get_status(self) -> Dict:
        return {
            "api_active": bool(self.api_key),
            "model": self.model,
            "news": self.news.get_summary(),
            "last_context_len": len(self.last_context),
            "explanations": len(self.trade_explanations),
        }
