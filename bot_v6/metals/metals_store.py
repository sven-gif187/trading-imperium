#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  EDELMETALL-STORE  (Stufe 1: Persistenz + Datensammlung)
================================================================
Reine stdlib (json/os) - KEIN yfinance, KEIN Tkinter.
Damit vom Edelmetall-Tab nutzbar UND einzeln testbar.

Zwei Aufgaben:
  1) save_state/load_state: haelt den letzten Live-Stand fest,
     damit der Tab beim Neustart NICHT mehr neu wuerfelt.
  2) log_scan: haengt bei jedem Scan einen Zeitstempel-Eintrag
     in metals_data/scan_log.jsonl  (deine Sammelbasis fuers
     spaetere Lernen - eine Zeile pro Metall pro Scan).

Eigener Ordner: metals_data/  (getrennt vom Bot-data_store)
================================================================
"""
import os
import json
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "metals_data")
STATE_FILE = os.path.join(DATA_DIR, "metals_state.json")
SCAN_LOG = os.path.join(DATA_DIR, "scan_log.jsonl")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _strip(analyses):
    """Entfernt nicht-serialisierbare Felder (v.a. den DataFrame 'df')."""
    out = []
    for a in (analyses or []):
        try:
            out.append({k: v for k, v in a.items() if k != "df"})
        except Exception:
            pass
    return out


def save_state(analyses, gs_ratio, stats=None):
    """Speichert den letzten Live-Stand atomar (tmp + replace)."""
    try:
        _ensure_dir()
        payload = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "gs_ratio": gs_ratio,
            "analyses": _strip(analyses),
            "stats": stats,
        }
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
        return True
    except Exception:
        return False


def load_state():
    """Liest den letzten gespeicherten Stand (oder None bei leer/fehlt/kaputt)."""
    try:
        if not os.path.exists(STATE_FILE):
            return None
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        return json.loads(raw) if raw else None
    except Exception:
        return None


def log_scan(analyses, gs_ratio):
    """Eine Zeile pro Metall pro Scan in scan_log.jsonl anhaengen."""
    try:
        _ensure_dir()
        ts = datetime.now(timezone.utc).isoformat()
        with open(SCAN_LOG, "a", encoding="utf-8") as f:
            for a in (analyses or []):
                if not isinstance(a, dict) or a.get("error"):
                    continue
                rec = {
                    "ts": ts,
                    "name": a.get("name"),
                    "price": a.get("price"),
                    "score": a.get("score"),
                    "signal": a.get("signal"),
                    "trend": a.get("trend"),
                    "rsi": a.get("rsi"),
                    "gs_ratio": gs_ratio,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def scan_count():
    """Anzahl gesammelter Scan-Zeilen (kleine Hilfe fuer spaeter)."""
    try:
        if not os.path.exists(SCAN_LOG):
            return 0
        with open(SCAN_LOG, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0
