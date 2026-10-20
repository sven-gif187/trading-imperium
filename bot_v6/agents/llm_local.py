"""
Trading Imperium V6 – Lokales LLM via Ollama
Verbindet mit lokalem Ollama-Server fuer Trade-Erklaerungen auf Deutsch.
Fallback auf regelbasierte Erklaerungen wenn Ollama nicht laeuft.
"""
import time
import threading
from typing import Dict, Optional
from core.logger import log

try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False


class LocalLLMAgent:
    """Lokales LLM fuer Marktanalyse und Trade-Erklaerungen."""

    OLLAMA_URL = "http://localhost:11434"

    def __init__(self, model="mistral"):
        self.model = model
        self.available = False
        self.last_response = ""
        self._check_availability()

    def _check_availability(self):
        if not HAS_REQ:
            return
        try:
            r = requests.get(f"{self.OLLAMA_URL}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m.get("name", "") for m in r.json().get("models", [])]
                if any(self.model in m for m in models):
                    self.available = True
                    log.info("LLM", f"Ollama verbunden: {self.model}")
                else:
                    available = ", ".join(models[:5]) if models else "keine"
                    log.info("LLM", f"Ollama laeuft, aber '{self.model}' nicht installiert. Verfuegbar: {available}")
                    if models:
                        self.model = models[0].split(":")[0]
                        self.available = True
                        log.info("LLM", f"Nutze stattdessen: {self.model}")
        except Exception:
            log.info("LLM", "Ollama nicht erreichbar – nutze Fallback-Erklaerungen")

    def analyze_market(self, price, rsi, adx, fg, cycle, regime) -> str:
        if self.available:
            return self._ask_llm(
                f"Du bist ein Krypto-Trading-Analyst. Antworte auf Deutsch, maximal 3 Saetze. "
                f"BTC Preis: {price:,.0f}$, RSI: {rsi:.0f}, ADX: {adx:.0f}, "
                f"Fear&Greed: {fg}, Zyklus: {cycle}, Regime: {regime}. "
                f"Was ist deine Einschaetzung?")
        return self._fallback_analysis(price, rsi, adx, fg, cycle, regime)

    def explain_trade(self, coin, side, reason, score) -> str:
        if self.available:
            return self._ask_llm(
                f"Erklaere auf Deutsch in 2 Saetzen warum der Bot {side} {coin} macht. "
                f"Grund: {reason}. Signal-Score: {score}/10.")
        return f"{side} {coin}: {reason} (Score {score}/10)"

    def _ask_llm(self, prompt, max_tokens=150) -> str:
        try:
            r = requests.post(f"{self.OLLAMA_URL}/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "stream": False, "options": {"num_predict": max_tokens}},
                timeout=30)
            if r.status_code == 200:
                response = r.json().get("response", "").strip()
                self.last_response = response
                return response
        except Exception as e:
            log.warn("LLM", f"Ollama Fehler: {str(e)[:40]}")
        return self._fallback_analysis(0, 50, 20, 50, "?", "?")

    def _fallback_analysis(self, price, rsi, adx, fg, cycle, regime) -> str:
        parts = []
        if fg < 25: parts.append("Extreme Angst im Markt – gute Kaufgelegenheit")
        elif fg > 75: parts.append("Extreme Gier – Vorsicht vor Korrektur")
        if rsi < 30: parts.append("RSI ueberverkauft")
        elif rsi > 70: parts.append("RSI ueberkauft")
        if "BEAR" in str(cycle): parts.append("Baerenmarkt-Phase")
        elif "BULL" in str(cycle): parts.append("Bullenmarkt-Phase")
        if adx > 30: parts.append("Starker Trend aktiv")
        return ". ".join(parts) if parts else "Markt neutral, keine klaren Signale."

    def get_status(self):
        return {"available": self.available, "model": self.model,
                "ollama_url": self.OLLAMA_URL}
