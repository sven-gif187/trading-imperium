# [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren
# -*- coding: utf-8 -*-
"""
Telegram fuer die Waechter (MASTERPROMPT_AGENTEN.md 6.1, Telegram-Regeln).

- Eigener Bot, NICHT der Bot von v6/v7. Token und Chat-ID in pruefstand/.env:
      TELEGRAM_WAECHTER_TOKEN=...
      TELEGRAM_WAECHTER_CHAT_ID=...
  Eingetragen wird beides mit TELEGRAM_EINRICHTEN.bat - nie von Hand abtippen.
- Der Token wird NIE ausgegeben, auch nicht in Fehlermeldungen (die URL enthaelt
  ihn, deshalb werden Ausnahmen ohne URL gemeldet).
- Gleiche Meldung (gleicher Schluessel) hoechstens alle 6 Stunden.
- Jeder Aufruf mit Zeitgrenze; ohne Netz gibt es False zurueck, keinen Absturz.

Nutzung:
    from telegram_meldung import sende
    sende("[WAECHTER][HOCH] W5 Bot v6 laeuft nicht", schluessel="W5-v6-aus")
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
ENV = HIER.parent / ".env"
GESENDET = HIER / "telegram_gesendet.json"
SPERRE_SEK = 6 * 3600
API = "https://api.telegram.org/bot{}/{}"


def lade_env(pfad: Path = ENV) -> dict:
    werte = {}
    if pfad.exists():
        for z in pfad.read_text(encoding="utf-8").splitlines():
            z = z.strip()
            if z and not z.startswith("#") and "=" in z:
                k, v = z.split("=", 1)
                werte[k.strip()] = v.strip().strip('"').strip("'")
    return werte


def schreibe_env(neu: dict, pfad: Path = ENV) -> None:
    """Setzt/ersetzt Schluessel, laesst alle anderen Zeilen stehen."""
    zeilen = pfad.read_text(encoding="utf-8").splitlines() if pfad.exists() else [
        "# [CLEANUP-KEEP] Pruefstand-Geheimnisse. NIE weitergeben, NIE in Berichte kopieren.",
        "# Eingetragen von TELEGRAM_EINRICHTEN.bat.",
    ]
    rest = dict(neu)
    for i, z in enumerate(zeilen):
        k = z.split("=", 1)[0].strip()
        if k in rest:
            zeilen[i] = f"{k}={rest.pop(k)}"
    zeilen += [f"{k}={v}" for k, v in rest.items()]
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def api(token: str, methode: str, daten: dict | None = None, timeout: int = 15) -> dict:
    url = API.format(token, methode)
    body = urllib.parse.urlencode(daten).encode() if daten else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:     # Antwort von Telegram, ohne URL weitergeben
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:                  # Netz weg: Text ohne URL/Token
        return {"ok": False, "description": type(e).__name__}


def _gesendet() -> dict:
    try:
        return json.loads(GESENDET.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sende(text: str, schluessel: str | None = None, env: dict | None = None) -> bool:
    env = env if env is not None else lade_env()
    token, chat = env.get("TELEGRAM_WAECHTER_TOKEN"), env.get("TELEGRAM_WAECHTER_CHAT_ID")
    if not token or not chat:
        return False
    if schluessel:
        log = _gesendet()
        if time.time() - log.get(schluessel, 0) < SPERRE_SEK:
            return False
    r = api(token, "sendMessage", {"chat_id": chat, "text": text[:4000],
                                    "disable_web_page_preview": "true"})
    if r.get("ok") and schluessel:
        log = _gesendet()
        log[schluessel] = time.time()
        GESENDET.write_text(json.dumps(log, indent=1), encoding="utf-8")
    return bool(r.get("ok"))
