#!/usr/bin/env python3
"""
================================================================
  TRADING IMPERIUM V6 - DEIN BOT-NAVIGATOR
================================================================
Scannt deinen V6-Ordner und erstellt eine interaktive HTML-Karte
mit Erklaerungen fuer jede Datei.

Verwendung: python bot_navigator.py
Oeffnet sich automatisch im Browser!
================================================================
"""
import os
import sys
import re
import json
import webbrowser
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# WISSEN: Was machen die Ordner und Datei-Typen?
# ============================================================
ORDNER_ERKLAERUNG = {
    "agents": {
        "icon": "🧠",
        "name": "AGENTS - Die Spezialisten",
        "desc": "Hier wohnen die Trading-Agenten. Jeder Agent ist ein Spezialist mit einem klaren Job: einer berechnet Signale, einer prueft Risiken, einer tradet Futures. Sie reden ueber den Event-Bus miteinander.",
        "color": "#3b82f6"
    },
    "core": {
        "icon": "⚙️",
        "name": "CORE - Das Fundament",
        "desc": "Das Herzstueck. Hier ist die Infrastruktur die alles zusammenhaelt: Event-Bus (wie reden die Module), State-Store (was wird gespeichert), Logger (was wird geloggt). Ohne Core laeuft nichts.",
        "color": "#ef4444"
    },
    "models": {
        "icon": "🤖",
        "name": "MODELS - Die KI-Modelle",
        "desc": "Hier liegen alle Machine-Learning-Modelle und KI-Bauteile: XGBoost, Reinforcement Learning, V4-Calibrator, Brain-Persistence. Die lernen aus Daten und sagen Preise voraus.",
        "color": "#8b5cf6"
    },
    "data": {
        "icon": "📊",
        "name": "DATA - Daten-Quellen",
        "desc": "Verbindet sich mit der Aussenwelt: Binance, Bybit, News-APIs, Reddit, Capitol Trades, Whale-Tracking. Diese Module sammeln rohe Daten die der Bot dann verarbeitet.",
        "color": "#10b981"
    },
    "execution": {
        "icon": "⚡",
        "name": "EXECUTION - Order-Ausfuehrung",
        "desc": "Wenn die KI 'KAUF!' sagt, macht's diese Schicht real: Order zur Boerse schicken, Bestaetigung abwarten, Slippage berechnen. Inkl. Circuit-Breaker (Schutz vor Pleite).",
        "color": "#f59e0b"
    },
    "risk": {
        "icon": "🛡️",
        "name": "RISK - Sicherheits-Engine",
        "desc": "Der Tuersteher. Prueft jeden Trade-Vorschlag: Zu hohes Risiko? Zu viele Positionen? Tagesverlust ueberschritten? Hat ein Veto-Recht und kann jeden Trade ablehnen.",
        "color": "#dc2626"
    },
    "config": {
        "icon": "🔧",
        "name": "CONFIG - Einstellungen",
        "desc": "Alle Knoepfe und Schalter: Wie viel pro Trade? Welche Coins? Stop-Loss bei 2% oder 3%? Hier liegen die Konfigurationen die du anpassen kannst ohne Code zu aendern.",
        "color": "#64748b"
    },
    "ui": {
        "icon": "🖥️",
        "name": "UI - Oberflaeche",
        "desc": "Die grafische Oberflaeche. Web-Dashboard, Charts, Live-Logs - alles was du auf dem Bildschirm siehst.",
        "color": "#ec4899"
    },
    "live": {
        "icon": "📡",
        "name": "LIVE - Live-Trading-Modus",
        "desc": "Spezielle Komponenten fuer Live-Trading: WebSocket-Verbindung, Live-Order-Tracking, Sicherheits-Mechanismen wenn echtes Geld im Spiel ist.",
        "color": "#06b6d4"
    },
    "backtest": {
        "icon": "⏪",
        "name": "BACKTEST - Strategie-Tests",
        "desc": "Spielt Strategien mit historischen Daten durch. So findest du raus ob eine Strategie haette gewonnen - bevor du echtes Geld riskierst.",
        "color": "#14b8a6"
    },
    "portfolio": {
        "icon": "💼",
        "name": "PORTFOLIO - Bestand-Verwaltung",
        "desc": "Was hast du wo? Wieviel BTC, ETH, SOL? Wie ist die Gewichtung? Soll rebalanced werden? Der Buchhalter deiner Coins.",
        "color": "#a855f7"
    },
    "features": {
        "icon": "✨",
        "name": "FEATURES - Zusatz-Funktionen",
        "desc": "Erweiterte Features: Telegram-Bot, Alarms, Notifications, Sparplaene und ander 'Nice-to-haves'.",
        "color": "#f97316"
    },
    "reports": {
        "icon": "📈",
        "name": "REPORTS - Berichte",
        "desc": "Generiert Performance-Berichte, Trade-Journale, taegliche Zusammenfassungen. Damit du checken kannst wie gut der Bot laeuft.",
        "color": "#84cc16"
    },
    "tests": {
        "icon": "🧪",
        "name": "TESTS - Selbstueberpruefung",
        "desc": "Automatische Tests die pruefen ob jedes Modul richtig funktioniert. Vor jedem Update sollten die laufen.",
        "color": "#71717a"
    },
    "scripts": {
        "icon": "📜",
        "name": "SCRIPTS - Hilfstools",
        "desc": "Einmalige Skripte: Migrations, Daten-Imports, Setup-Helfer. Werden manuell gestartet wenn man sie braucht.",
        "color": "#6b7280"
    },
    "docs": {
        "icon": "📖",
        "name": "DOCS - Dokumentation",
        "desc": "Anleitungen, Erklaerungen, Handbuch.",
        "color": "#8b5cf6"
    },
    "data_store": {
        "icon": "💾",
        "name": "DATA_STORE - Persistente Daten",
        "desc": "Hier speichert der Bot Daten die er ueber Neustarts hinweg behalten muss: Brain-Performance, offene Positionen, Trade-Journal, ML-Modelle.",
        "color": "#475569"
    },
    "v4_data": {
        "icon": "🏆",
        "name": "V4_DATA - V4-Lerngrundlage",
        "desc": "Die echten V4-Daten: 278 Trades, +1.597 EUR Profit. Diese Daten dienen als Startwissen fuer V6, damit V6 nicht bei Null anfaengt.",
        "color": "#eab308"
    },
}

# Bekannte Datei-Erklaerungen (Pattern -> Erklaerung)
DATEI_ERKLAERUNG = {

    # === WERKZEUGE, DIE DU SELBST STARTEST [20.08.2026] ===
    # Deckungsgleich mit BOT-HANDBUCH.md 4.86. Wer hier etwas aendert,
    # aendert es auch dort - zwei Listen, die auseinanderlaufen, sind
    # schlimmer als eine.

    # -- der Alltag --
    "status.py": "Bot-Uebersicht in einem Blick: laeuft er, Balance, offene Positionen, letzte Trades. Der schnellste Weg zu 'wie steht es gerade'.",
    "offen.py": "Zeigt die offenen Punkte aus OFFEN.md - kurz, ohne Scrollen. Mit --alle auch die Gruppen B, C und D.",
    "sammler_pruefen.py": "PRUEFT ALLE SAMMLER: laeuft er, schreibt er, gibt es Luecken, sind Pflichtfelder leer. Beantwortet die Frage, die prozess_frische.py NICHT beantwortet - ein Sammler, der laeuft, ist noch kein Sammler, der sammelt. Am einfachsten per Doppelklick: SAMMLER_PRUEFEN.bat",
    "prozess_frische.py": "Laeuft irgendwo noch alter Programmtext? Vergleicht die Startzeit jedes Prozesses mit der Aenderungszeit seiner Dateien. Beantwortet 'muss ich neu starten?'.",
    "stichtag.py": "Die Pruefung zum Ende des Messfensters (29.08.): reichen die Daten, wo stehen die Zielgroessen, ist der Code noch unveraendert, welche acht Entscheidungen stehen an.",
    "schon_bekannt.py": "Beantwortet in zwei Sekunden: steht dieser Befund schon in der Doku? Pflicht vor jedem neuen Fund - sonst wird derselbe Fehler zweimal gemeldet. Index bauen mit --index.",
    "sicherung.py": "Sichert das gesamte Projekt auf die zweite Festplatte. Der .env-Schluessel wird bewusst NICHT mitkopiert.",

    # -- ansehen --
    "cockpit_server.py": "DAS ANALYSE-DASHBOARD. Startet einen kleinen Webserver, danach im Browser http://localhost:8170 - Kennzahlen, Epochenvergleich, Freischaltungsstand, Ausstiegs-Nachlauf. Bindet nur auf 127.0.0.1, kein Zugriff aus dem Heimnetz. Beenden mit Strg+C. Nicht verwechseln mit Port 5070, das ist das Dashboard des laufenden Bots. [25.09.2026, Befund 111] In v7 sind es 5070 und 8170, weil der v6-Papier-Bot auf demselben Rechner 5050 und 8110 haelt. Beide Zahlen stehen in data_store/config.json unter dashboard.port und dashboard.cockpit_port.",
    "bot_navigator.py": "Erzeugt genau diese Karte hier (bot_uebersicht.html) - eine anklickbare Uebersicht ueber alle Ordner und Dateien des Projekts.",
    "handbuch_pdf.py": "Erzeugt BOT-HANDBUCH.pdf aus BOT-HANDBUCH.md. Nach jeder Handbuch-Aenderung aufrufen. Die PDF NIE von Hand aendern - sie wird erzeugt.",
    "zahlenbuch.py": "Erzeugt ZAHLENBUCH.pdf UND ZAHLENBUCH.md - alle gemessenen Kennzahlen mit Quellenangabe. Seit 20.08. schreibt ein normaler Lauf beide Fassungen, damit sie nicht auseinanderlaufen.",
    "datenexport.py": "Schreibt alle gemessenen Daten in eine Excel-Mappe (BOT-DATEN_*.xlsx) - zum Weiterrechnen ausserhalb des Bots.",
    "lage_erzeugen.py": "Schreibt LAGE.md neu: was laeuft gerade, welche Daten gibt es. NIE von Hand aendern.",
    "brain_view.py": "Zeigt, was das lernende Gehirn ueber die Strategien gespeichert hat. Achtung: die Zahlen enthalten V4-Bootstrap-Werte und sind kein reiner V6-Ertrag.",
    "epoch_report.py": "Vergleicht die Epochen: was hat sich seit welcher Verhaltensaenderung geaendert. Auswertungen duerfen nur INNERHALB einer Epoche verglichen werden.",
    "impact_report.py": "Impact-Journal: welche Aenderung was gebracht hat.",

    # -- die Auswertungen: die Belege hinter den Behauptungen --
    "regime_filter_messung.py": "Ist der Kauf-Blocker sein Geld wert? Rechnet fuer jede geblockte Kaufgelegenheit nach, wie der Kurs 4/12/24/48 h spaeter stand. Zaehlt seit dem 19.08. nur UNABHAENGIGE Faelle - der Bot prueft alle 12 Sekunden, aus 12 Tagen wurden sonst 53.806 'Faelle'.",
    "stoploss_analyse.py": "Wo genau entsteht der Verlust - und was wuerde helfen?",
    "drawdown_auswertung.py": "Wie tief ging es vom Hoechststand herunter? Die Schmerzgrenze, eine der zwei Kennzahlen, die den Live-Gang sperren. Filtert Messungen waehrend einer laufenden Verkaufsbuchung heraus (Befund 55).",
    "gesamtauswertung.py": "Alles Gemessene und Bestaetigte in einem Bericht.",
    "pnl_check.py": "Wann und wo ist das Minus entstanden?",
    "e7_auswertung.py": "Der grosse Report zur laufenden Epoche. Reine Leseoperation.",
    "e7_gegenprobe.py": "Dieselben Zahlen wie e7_auswertung.py, unabhaengig ein zweites Mal gerechnet. Stimmen beide ueberein, gilt der Wert.",
    "merkmale_auswertung.py": "Welche Indikatorwerte gingen steigenden Kursen voraus?",
    "schwelle_vergleich.py": "Hatte der lernende Waechter recht, als er den Filter strenger stellte?",
    "maker_schatten.py": "Lohnt der Wechsel von Sofort- auf Warteauftraege (Limit-Order)? Bei 0,25 % Taker je Seite die groesste einzelne Stellschraube.",
    "schatten_leiter_auswertung.py": "Vergleicht die Schatten-Ausstiegsregel mit der echten Ausstiegs-Leiter.",
    "gebuehren_gegenprobe.py": "Wird die Kaufgebuehr doppelt abgezogen? (Handbuch 4.50)",
    "telemetrie_frage.py": "Fragt die Telemetrie ab: warum hat der Bot gekauft - oder eben nicht?",
    "chartanalyse_backtest.py": "Trifft die Chartanalyse ueberhaupt? Fuellt die Tabelle chart_laeufe. Laeuft NICHT von selbst mit - das startest du von Hand.",
    "nachlauf_rueckwirkend.py": "Holt die Kurse nach einem Ausstieg rueckwirkend nach. Hat am 19.08. die 437 nie gemessenen Ausstiege zurueckgeholt (von 16 auf 453) und dabei Befund 60 gefunden: jeder dritte Live-Messwert stammte aus einer noch laufenden Kerze.",
    "schatten_regime_nachtragen.py": "Traegt den Marktzustand in alten Schatten-Zeilen nach - exakt aus dem gespeicherten ADX, nichts geschaetzt. War einmalig noetig (Befund 61).",
    "erledigtes_archivieren.py": "Nimmt Erledigtes aus den aktiven Listen heraus. Mit --offen-struktur prueft es, ob OFFEN.md noch alle vier Gruppen hat und Gruppe C sortiert ist.",

    # -- die Sammler, die dauerhaft laufen --
    "positionsverlauf.py": "SAMMLER: zeichnet alle 5 Minuten auf, WIE eine Position verlief - Kurs, Hoch, Tief, Rueckfall vom Hoch, ATR, RSI, ADX. Die Grundlage, um Ausstiegsregeln spaeter gegeneinander zu rechnen. Muss dauerhaft laufen; der Bot startet ihn seit 20.08. selbst mit.",
    "schatten_universum.py": "SAMMLER: rechnet stuendlich fuer 18 Muenzen dieselbe Punktzahl aus wie der Bot - HANDELT ABER NICHT. Beantwortet, welche Muenze ihre Reibungskosten ueberhaupt verdient.",
    "nachlauf.py": "SAMMLER (laeuft im Bot mit): misst nach jedem Ausstieg und jeder Blockade, wie der Kurs 1/4/24/48 h spaeter stand. War der Ausstieg zu frueh? War die Blockade richtig?",
    "job_zahlenbuch.py": "Morgenlauf: erzeugt das Zahlenbuch als PDF und schreibt LAGE.md neu.",
    "job_forschung_capture.py": "Starter fuer den Forschungs-Capture ohne Fenster. Laeuft dauerhaft und sammelt Rohdaten von den Boersen.",
    "schatten_starter.py": "Startet das Schatten-Universum, falls es nicht laeuft. Sonst tut es nichts.",

    # -- vor dem Live-Gang --
    "go_live_check.py": "Die Freigabe-Pruefung: sind alle Bedingungen fuer den Live-Betrieb erfuellt? Jetzt noch nicht dran - das Messfenster laeuft bis 29.08.",
    "preflight.py": "Ist der Bot technisch bereit - Schluessel, Verbindung, Konfiguration?",
    # Core
    "events.py": "Definiert die 3 zentralen Datenobjekte: MarketSnapshot (Was passiert am Markt?), DecisionIntent (Was will die KI tun?), ExecutionResult (Was ist wirklich passiert?). Auch alle Event-Typen wie SIGNAL, RISK_APPROVED etc.",
    "bus.py": "Der Event-Bus. Zentrales Kommunikationssystem - alle Module reden ueber ihn statt direkt miteinander. Macht das System modular: jedes Teil kann ausgetauscht werden.",
    "state_store.py": "Persistenter Speicher fuer alles was Neustarts ueberleben muss. Atomic Writes (Backup -> Temp -> Rename) verhindern korrupte Dateien. Plus TradeJournal fuer Trade-History.",
    "logger.py": "Strukturiertes Logging-System. Sortiert Log-Eintraege nach Modul, Schweregrad und Zeit. Was du im CMD-Fenster siehst kommt von hier.",
    "scheduler.py": "Plant zeitgesteuerte Aufgaben: alle 5 Minuten Markt scannen, jede Minute Positionen pruefen, taeglich Reports generieren.",
    "health.py": "System-Selbstdiagnose. Prueft ob alle Agenten leben, ob die Boerse erreichbar ist, ob Indikatoren-Berechnungen funktionieren. Der Doktor des Bots.",
    "auto_restart.py": "Wenn ein Agent abstuerzt: automatischer Neustart. Wenn der Bot komplett haengt: Notabschaltung. Sicherheitsnetz.",
    "exceptions.py": "Eigene Fehler-Typen wie RiskVetoError, KillSwitchError, CircuitBreakerOpenError. Damit der Bot weiss wie er auf welchen Fehler reagieren soll.",

    # Agents
    "signal_agent.py": "Der Signal-Generator. Liest Marktdaten, berechnet Indikatoren (RSI, MACD, EMA), und generiert Kauf/Verkauf-Vorschlaege mit Score 0-10.",
    "strategy_brain.py": "Das Gehirn. Waehlt aus 13 Strategien die passende fuer die aktuelle Marktlage. Nutzt Performance-Tracking um zu lernen welche Strategien wann funktionieren.",
    "context_agent.py": "Der Erklaerer. Nimmt einen Trade-Vorschlag und macht eine menschenlesbare Begruendung daraus ('Bot kauft BTC weil RSI niedrig + MACD bullisch').",
    "cycle_theory.py": "Bitcoin 4-Jahres-Zyklus-Analyse. Erkennt ob wir im Bullen- oder Baerenmarkt sind und passt Strategien entsprechend an.",
    "btc_accumulator.py": "Der BTC-Sparplan. Kauft regelmaessig BTC nach 1/3-Regel: 1/3 sofort, 1/3 bei Dip, 1/3 bei Crash. DCA Sparen.",
    "smart_entry.py": "Wartet auf bessere Einstiege. Statt sofort zu kaufen wenn Signal kommt, wartet er kurz auf einen Pullback fuer besseren Preis.",
    "llm_local.py": "Lokales Sprachmodell (z.B. Llama 7B/13B via Ollama). Fuer KI-Erklaerungen ohne externe API.",
    "grid_trader.py": "Grid-Trading-Strategie. Setzt mehrere Kauf/Verkauf-Levels und verdient an Volatilitaet.",
    "dca_advanced.py": "Dollar-Cost-Averaging Pro: kauft in fallenden Maerkten staerker nach.",
    "arbitrage_agent.py": "Sucht Preis-Unterschiede zwischen Boersen (z.B. Binance vs Bybit) und nutzt sie aus.",
    "v4_strategies.py": "Die 7 profitablen V4-Strategien als V6-Modul. DCA_FEAR_GREED, FIBONACCI_SUPPORT, ICHIMOKU etc. Ergebnis: +1.597 EUR in V4.",

    # Models
    "v4_calibrator.py": "Berechnet Strategie-Gewichte aus echter V4-Performance. DCA_FEAR_GREED bekommt 0.91, Verlierer wie STOCHRSI bekommen 0.0 (gesperrt).",
    "brain_persistence.py": "Speichert das Brain-Lernen ueber Neustarts. Damit der Bot nicht jedes Mal bei Null anfaengt.",
    "xgboost_model.py": "ML-Modell auf Basis von XGBoost. Lernt aus historischen Indikatoren ob ein Setup gewinnt oder verliert.",

    # Data
    "v4_importer.py": "Importiert V4-Trades und Equity-History ins V6-Format.",
    "ccxt_client.py": "Wrapper um die ccxt-Library. Damit kann der Bot mit ueber 100 Boersen sprechen ohne dass jede einzeln integriert werden muss.",
    "news_api.py": "Holt Crypto-News und macht Sentiment-Analyse.",
    "reddit_client.py": "Liest r/CryptoCurrency und Co. Crowd-Sentiment als Trade-Indikator.",

    # App
    "app.py": "Die Schaltzentrale. Startet alle Agenten, verbindet sie ueber den Event-Bus, startet das Dashboard. Das Hauptprogramm.",
    "main.py": "Alternative Einstiegsdatei.",
    "config.example.json": "Beispiel-Konfiguration. Kopier sie zu config.json und passe sie an.",
    ".env.example": "Beispiel fuer Umgebungs-Variablen (API-Keys etc).",
    "requirements.txt": "Alle Python-Pakete die der Bot braucht. Mit 'pip install -r requirements.txt' werden sie installiert.",
    "ANLEITUNG.md": "Anleitung wie man den Bot benutzt.",
    "HANDBUCH.md": "Ausfuehrliches Handbuch.",
    "LIVE_TRADING.md": "Spezielle Anleitung fuer Live-Trading-Modus.",
    "LIVE_TRADING_SETUP.md": "Setup-Schritte fuer Live-Trading.",

    # Bridge-Spezifisch
    "diagnose.py": "Mein Diagnose-Tool: prueft ob die V4-Bridge richtig installiert ist.",
    "repair.py": "Mein Repair-Tool: fixt fehlende Patches der V4-Bridge.",
    "install.py": "Mein V4-Bridge Installer.",
    "bot_navigator.py": "Dieses Tool hier - erstellt die Uebersicht.",
}


def get_file_size_human(path):
    """Liefert Dateigroesse in lesbarem Format."""
    try:
        size = os.path.getsize(path)
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f}KB"
        else:
            return f"{size/(1024*1024):.1f}MB"
    except Exception:
        return "?"


def count_lines(path):
    """Zaehlt Zeilen in einer Python-Datei."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def extract_docstring(path):
    """Extrahiert den ersten Docstring einer Python-Datei."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(2000)  # Nur die ersten 2KB
        # Triple-Quote Docstring suchen
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            doc = match.group(1).strip()
            # Erste 200 Zeichen
            return doc[:200] + ("..." if len(doc) > 200 else "")
        match = re.search(r"'''(.*?)'''", content, re.DOTALL)
        if match:
            doc = match.group(1).strip()
            return doc[:200] + ("..." if len(doc) > 200 else "")
    except Exception:
        pass
    return ""


def explain_file(filename):
    """Findet eine Erklaerung fuer eine Datei."""
    return DATEI_ERKLAERUNG.get(filename, "")


def explain_folder(folder_name):
    """Findet eine Erklaerung fuer einen Ordner."""
    return ORDNER_ERKLAERUNG.get(folder_name.lower(), {
        "icon": "📁",
        "name": folder_name.upper(),
        "desc": "Eigener Ordner.",
        "color": "#94a3b8"
    })


def scan_folder(folder_path, root):
    """Scannt einen Ordner rekursiv."""
    files = []
    folders = []
    if not os.path.isdir(folder_path):
        return files, folders

    try:
        for entry in sorted(os.listdir(folder_path)):
            if entry.startswith(".") and entry not in (".env.example",):
                continue
            if entry == "__pycache__" or entry.endswith(".pyc"):
                continue
            full = os.path.join(folder_path, entry)
            rel = os.path.relpath(full, root)
            if os.path.isdir(full):
                folders.append({
                    "name": entry,
                    "path": rel,
                })
            else:
                lines = count_lines(full) if entry.endswith(".py") else 0
                files.append({
                    "name": entry,
                    "path": rel,
                    "size": get_file_size_human(full),
                    "lines": lines,
                    "explanation": explain_file(entry),
                    "docstring": extract_docstring(full) if entry.endswith(".py") else "",
                })
    except PermissionError:
        pass
    return files, folders


def build_html(root_path, structure):
    """Baut die HTML-Uebersicht."""
    total_files = sum(len(s["files"]) for s in structure)
    total_lines = sum(f["lines"] for s in structure for f in s["files"])

    cards_html = ""
    for section in structure:
        info = section["info"]
        files_html = ""
        for f in section["files"]:
            badge = f'<span class="badge">{f["lines"]} Zeilen</span>' if f["lines"] > 0 else ""
            doc = ""
            if f["explanation"]:
                doc = f'<div class="file-explanation">{f["explanation"]}</div>'
            elif f["docstring"]:
                doc = f'<div class="file-docstring">{f["docstring"]}</div>'
            files_html += f"""
                <div class="file-item">
                    <div class="file-header">
                        <span class="file-name">📄 {f["name"]}</span>
                        <span class="file-meta">{f["size"]} {badge}</span>
                    </div>
                    {doc}
                </div>
            """
        if not section["files"]:
            files_html = '<div class="file-item empty">(leerer Ordner)</div>'

        cards_html += f"""
        <div class="folder-card" style="border-left-color: {info['color']};">
            <div class="folder-header" onclick="toggleFolder(this)">
                <div>
                    <span class="folder-icon">{info['icon']}</span>
                    <span class="folder-name">{info['name']}</span>
                    <span class="folder-path">/{section['name']}/</span>
                </div>
                <span class="folder-toggle">▼</span>
            </div>
            <div class="folder-desc">{info['desc']}</div>
            <div class="folder-content">
                <div class="folder-stats">{len(section['files'])} Dateien</div>
                {files_html}
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Trading Imperium V6 - Bot Navigator</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
        min-height: 100vh;
        padding: 20px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{
        font-size: 2.5em;
        margin-bottom: 10px;
        background: linear-gradient(90deg, #fbbf24, #f59e0b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .subtitle {{ color: #94a3b8; margin-bottom: 30px; font-size: 1.1em; }}
    .stats {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 15px;
        margin-bottom: 30px;
    }}
    .stat-card {{
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }}
    .stat-value {{
        font-size: 2em;
        font-weight: bold;
        color: #fbbf24;
    }}
    .stat-label {{ color: #94a3b8; font-size: 0.9em; margin-top: 5px; }}
    .folder-card {{
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #334155;
        border-left: 5px solid;
        border-radius: 8px;
        margin-bottom: 15px;
        overflow: hidden;
        transition: all 0.2s;
    }}
    .folder-card:hover {{
        background: rgba(30, 41, 59, 0.8);
        transform: translateX(2px);
    }}
    .folder-header {{
        padding: 18px 20px;
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        user-select: none;
    }}
    .folder-icon {{ font-size: 1.5em; margin-right: 10px; }}
    .folder-name {{ font-size: 1.2em; font-weight: bold; color: #fbbf24; }}
    .folder-path {{ color: #64748b; margin-left: 10px; font-family: monospace; font-size: 0.9em; }}
    .folder-toggle {{ color: #94a3b8; transition: transform 0.2s; }}
    .folder-card.collapsed .folder-toggle {{ transform: rotate(-90deg); }}
    .folder-card.collapsed .folder-content,
    .folder-card.collapsed .folder-desc {{ display: none; }}
    .folder-desc {{
        padding: 0 20px 15px;
        color: #cbd5e1;
        font-size: 0.95em;
        line-height: 1.5;
        border-bottom: 1px solid #334155;
    }}
    .folder-content {{ padding: 15px 20px; }}
    .folder-stats {{ color: #64748b; font-size: 0.85em; margin-bottom: 10px; }}
    .file-item {{
        background: rgba(15, 23, 42, 0.6);
        border-radius: 6px;
        padding: 12px 15px;
        margin-bottom: 8px;
        border-left: 3px solid #475569;
        transition: all 0.15s;
    }}
    .file-item:hover {{ border-left-color: #fbbf24; }}
    .file-item.empty {{ color: #64748b; font-style: italic; text-align: center; }}
    .file-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }}
    .file-name {{ font-family: 'Cascadia Code', 'Courier New', monospace; color: #e2e8f0; font-weight: 500; }}
    .file-meta {{ color: #64748b; font-size: 0.85em; }}
    .badge {{
        background: #1e293b;
        color: #94a3b8;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75em;
        margin-left: 5px;
    }}
    .file-explanation {{
        color: #cbd5e1;
        font-size: 0.9em;
        line-height: 1.5;
        margin-top: 5px;
    }}
    .file-docstring {{
        color: #94a3b8;
        font-size: 0.85em;
        line-height: 1.4;
        margin-top: 5px;
        font-style: italic;
        border-left: 2px solid #475569;
        padding-left: 10px;
    }}
    .legend {{
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }}
    .legend h2 {{ color: #fbbf24; margin-bottom: 15px; font-size: 1.2em; }}
    .legend p {{ color: #cbd5e1; line-height: 1.6; margin-bottom: 8px; }}
    .controls {{
        margin-bottom: 20px;
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }}
    .controls button {{
        background: #1e293b;
        color: #e2e8f0;
        border: 1px solid #475569;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9em;
    }}
    .controls button:hover {{ background: #334155; border-color: #fbbf24; }}
    .footer {{
        text-align: center;
        color: #64748b;
        font-size: 0.85em;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #334155;
    }}
</style>
</head>
<body>
    <div class="container">
        <h1>🤖 Trading Imperium V6 - Bot Navigator</h1>
        <p class="subtitle">Deine interaktive Karte des Bots. Klick auf einen Ordner um ein/auszuklappen.</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(structure)}</div>
                <div class="stat-label">Ordner</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_files}</div>
                <div class="stat-label">Dateien</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_lines:,}</div>
                <div class="stat-label">Code-Zeilen</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">⚡</div>
                <div class="stat-label">{datetime.now().strftime('%d.%m.%Y %H:%M')}</div>
            </div>
        </div>

        <div class="legend">
            <h2>📚 Wie liest man das?</h2>
            <p><strong>So funktioniert dein Bot:</strong> Daten kommen rein (📊 data) → werden analysiert (🧠 agents) → KI entscheidet (🤖 models) → Risk prueft (🛡️ risk) → Order geht raus (⚡ execution) → Ergebnis wird gespeichert (💾 data_store) → Brain lernt daraus.</p>
            <p><strong>Tipp:</strong> Die wichtigsten Ordner zum Verstehen sind <span style="color: #fbbf24;">core</span>, <span style="color: #fbbf24;">agents</span> und <span style="color: #fbbf24;">models</span>. Damit verstehst du 80% des Systems.</p>
        </div>

        <div class="controls">
            <button onclick="expandAll()">▼ Alle aufklappen</button>
            <button onclick="collapseAll()">▶ Alle einklappen</button>
        </div>

        {cards_html}

        <div class="footer">
            Generiert von bot_navigator.py - Trading Imperium V6 Übersicht<br>
            Pfad: {root_path}
        </div>
    </div>

<script>
function toggleFolder(el) {{
    el.parentElement.classList.toggle("collapsed");
}}
function expandAll() {{
    document.querySelectorAll(".folder-card").forEach(c => c.classList.remove("collapsed"));
}}
function collapseAll() {{
    document.querySelectorAll(".folder-card").forEach(c => c.classList.add("collapsed"));
}}
// Default: alle einklappen
collapseAll();
</script>
</body>
</html>"""
    return html


def main():
    root = SCRIPT_DIR
    print("=" * 60)
    print("  TRADING IMPERIUM V6 - BOT NAVIGATOR")
    print("=" * 60)
    print(f"  Scanne: {root}")
    print()

    structure = []

    # Top-Level Files
    top_files = []
    for entry in sorted(os.listdir(root)):
        if entry.startswith(".") and entry not in (".env.example",):
            continue
        full = os.path.join(root, entry)
        if os.path.isfile(full) and not entry.endswith(".pyc"):
            top_files.append({
                "name": entry,
                "path": entry,
                "size": get_file_size_human(full),
                "lines": count_lines(full) if entry.endswith(".py") else 0,
                "explanation": explain_file(entry),
                "docstring": extract_docstring(full) if entry.endswith(".py") else "",
            })
    if top_files:
        structure.append({
            "name": "ROOT",
            "info": {
                "icon": "🏠",
                "name": "ROOT - Hauptverzeichnis",
                "desc": "Die Top-Level-Dateien. Hier steht der Einstiegspunkt (app.py), die Konfiguration und Anleitungen.",
                "color": "#fbbf24"
            },
            "files": top_files,
        })

    # Ordner durchgehen
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        if not os.path.isdir(full):
            continue
        if entry.startswith(".") or entry == "__pycache__":
            continue
        files, _ = scan_folder(full, root)
        info = explain_folder(entry)
        structure.append({
            "name": entry,
            "info": info,
            "files": files,
        })
        print(f"  [OK] {entry}: {len(files)} Dateien")

    # HTML bauen
    html = build_html(root, structure)
    output = os.path.join(root, "bot_uebersicht.html")
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)

    total_files = sum(len(s["files"]) for s in structure)
    total_lines = sum(f["lines"] for s in structure for f in s["files"])
    print()
    print(f"  Gesamt: {len(structure)} Ordner, {total_files} Dateien, {total_lines:,} Zeilen Code")
    print()
    print(f"  HTML erstellt: {output}")
    # [20.08.2026] Mit --still nicht von selbst den Browser aufreissen -
    # sonst springt bei jedem Neuerzeugen ein Fenster auf, auch wenn man
    # die Karte nur aktualisieren wollte.
    if "--still" in sys.argv:
        print("  (--still: Browser wird nicht geoeffnet)")
        return
    print(f"  Oeffne automatisch im Browser...")
    try:
        webbrowser.open(f"file:///{output.replace(os.sep, '/')}")
    except Exception as e:
        print(f"  Konnte nicht oeffnen: {e}")
        print(f"  Bitte manuell oeffnen: {output}")
    print()
    print("  TIPP: Die HTML-Datei kannst du jederzeit wieder oeffnen!")


if __name__ == "__main__":
    main()
