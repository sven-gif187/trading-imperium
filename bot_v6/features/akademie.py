"""
TRADING-AKADEMIE  -  Trading Imperium V6
========================================
Dein persoenlicher Trading-Lehrgang vom Nullpunkt an.

Das Besondere: Die Akademie erklaert dir die Konzepte nicht abstrakt,
sondern anhand DEINER echten Trades aus trades_v5.json. Wenn ein Kapitel
ueber Stop-Loss spricht, zeigt es dir deinen echten ADA-Stop-Loss.

- Reine Lern-/Lesefunktion, KEIN Trading-Eingriff.
- Fortschritt wird in data_store/akademie_fortschritt.json gespeichert.

Standalone starten:
  python "C:\\Users\\<BENUTZER>\\Desktop\\trading_imperium_v6(21)\\features\\akademie.py"

Oder im Code:
  from features.akademie import Akademie
  Akademie().run_console()
"""
import os
import json
from collections import defaultdict


# ============================================================
#  LEHRPLAN  (4 Phasen, in kleinen Haeppchen)
#  Aufbau nach dem Profi-Standard: Fundament -> Aufbau ->
#  Fortgeschritten -> Verfeinerung. Jede Lektion: kurzer
#  Klartext-Text + optional ein echtes Trade-Beispiel + Quiz.
# ============================================================

CURRICULUM = [
    # ---------- PHASE 1: FUNDAMENT ----------
    {
        "phase": "Phase 1 - Fundament",
        "lessons": [
            {
                "id": "1.1",
                "titel": "Was Trading wirklich ist (und was nicht)",
                "text": (
                    "Trading ist KEIN Gluecksspiel und kein schnelles Geld. Es ist ein "
                    "Wahrscheinlichkeits-Spiel: Du suchst Situationen, in denen die Chancen "
                    "leicht zu deinen Gunsten stehen, und wiederholst das diszipliniert "
                    "hunderte Male. Kein einzelner Trade entscheidet - die Summe entscheidet.\n"
                    "Merksatz: Ein guter Trader verliert oft. Er sorgt nur dafuer, dass die "
                    "Gewinne groesser sind als die Verluste. Genau hier hat unser Bot gerade "
                    "seine groesste Schwaeche (dazu spaeter mehr in Phase 3)."
                ),
                "quiz": {
                    "frage": "Was entscheidet ueber Erfolg beim Trading?",
                    "optionen": [
                        "Ein einzelner perfekter Trade",
                        "Die Summe vieler Trades mit leichtem Vorteil",
                        "Glueck",
                    ],
                    "richtig": 1,
                    "erklaerung": (
                        "Genau. Einzelne Trades sind Rauschen. Der Vorteil zeigt sich erst "
                        "ueber viele Trades - deshalb sammelt unser Bot ueber Wochen Daten."
                    ),
                },
            },
            {
                "id": "1.2",
                "titel": "Long & Short, Bid & Ask, Spread",
                "text": (
                    "LONG = du kaufst, weil du auf steigende Preise setzt (das macht unser Bot). "
                    "SHORT = du verdienst an fallenden Preisen (macht unser Bot im Paper bisher nicht). "
                    "BID ist der hoechste Preis, den ein Kaeufer zahlt; ASK der niedrigste, den "
                    "ein Verkaeufer will. Die Luecke dazwischen ist der SPREAD - eine versteckte "
                    "Gebuehr, die du bei jedem Trade zahlst. Bei grossen Coins (BTC) ist der Spread "
                    "winzig, bei kleinen Memecoins riesig - ein Grund, warum wir mit Memecoins "
                    "vorsichtig sind."
                ),
                "quiz": {
                    "frage": "Was ist der Spread?",
                    "optionen": [
                        "Die Differenz zwischen Kauf- und Verkaufspreis",
                        "Die Boersengebuehr in Prozent",
                        "Der Gewinn eines Trades",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Richtig. Der Spread ist eine versteckte Kostenquelle - je illiquider "
                        "der Coin, desto teurer."
                    ),
                },
            },
            {
                "id": "1.3",
                "titel": "Was eine Kerze (Candlestick) dir verraet",
                "text": (
                    "Eine Kerze zeigt vier Preise in einem Zeitraum: Eroeffnung, Hoch, Tief, "
                    "Schluss. Gruener Koerper = Schluss ueber Eroeffnung (Kaeufer gewannen). "
                    "Roter Koerper = Verkaeufer gewannen. Die duennen 'Dochte' zeigen, wie weit "
                    "der Preis kurz ausschlug, bevor er zurueckkam. Lange Dochte nach unten bei "
                    "tiefem Preis = Kaeufer fangen an zuzugreifen (oft ein Boden-Signal - genau "
                    "das, was unsere 'Fear & Greed DCA'-Strategie ausnutzt)."
                ),
                "quiz": {
                    "frage": "Was bedeutet ein langer Docht nach unten?",
                    "optionen": [
                        "Der Preis ist tief gefallen und Kaeufer griffen zu",
                        "Niemand wollte kaufen",
                        "Die Boerse war geschlossen",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Korrekt - ein Hinweis auf Kaufdruck am Tief. Unser Bot misst genau "
                        "solche Signale (Orderbook-Kaufdruck)."
                    ),
                },
            },
        ],
    },
    # ---------- PHASE 2: AUFBAUWISSEN ----------
    {
        "phase": "Phase 2 - Aufbauwissen (Indikatoren)",
        "lessons": [
            {
                "id": "2.1",
                "titel": "RSI - der Ueberhitzungs-Messer",
                "text": (
                    "Der RSI (Relative Strength Index) laeuft von 0 bis 100. Unter 30 gilt ein "
                    "Coin als 'oversold' (ueberverkauft - koennte drehen), ueber 70 als "
                    "'overbought' (ueberkauft - koennte fallen). Unser Bot kauft gern bei "
                    "niedrigem RSI. ACHTUNG Anfaengerfalle: Ein niedriger RSI heisst NICHT "
                    "automatisch 'jetzt steigt es'. In einem starken Abwaertstrend kann der RSI "
                    "lange tief bleiben ('falling knife'). Deshalb kombiniert unser Bot RSI nie "
                    "allein, sondern mit mehreren Signalen (Score-System)."
                ),
                "quiz": {
                    "frage": "RSI 28 - was heisst das?",
                    "optionen": [
                        "Ueberverkauft, koennte drehen - aber kein Selbstlaeufer",
                        "Garantierter Anstieg",
                        "Sofort verkaufen",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Genau. Oversold = erhoehte Chance auf Drehung, mehr nicht. Deshalb "
                        "Score-System statt Einzelsignal."
                    ),
                },
            },
            {
                "id": "2.2",
                "titel": "Trend & ADX - die Staerke hinter der Bewegung",
                "text": (
                    "Ein Trend ist die Richtung, in die der Preis ueber Zeit laeuft (hoch, runter, "
                    "seitwaerts). Der ADX misst die STAERKE des Trends (nicht die Richtung): unter "
                    "20 = schwach/seitwaerts, ueber 25 = starker Trend. 'The trend is your friend' "
                    "- gegen einen starken Trend zu handeln ist teuer. Unser Bot liest den ADX in "
                    "seinen Signalen ('Starker Trend ADX 47')."
                ),
                "quiz": {
                    "frage": "Was misst der ADX?",
                    "optionen": [
                        "Die Staerke eines Trends",
                        "Die Richtung eines Trends",
                        "Den Gewinn",
                    ],
                    "richtig": 0,
                    "erklaerung": "Richtig - Staerke, nicht Richtung. Die Richtung kommt von anderen Indikatoren.",
                },
            },
            {
                "id": "2.3",
                "titel": "Marktphasen: Bullen-, Baeren- und Seitwaertsmarkt",
                "text": (
                    "BULLENMARKT = Preise steigen ueber laengere Zeit (Optimismus). "
                    "BAERENMARKT = Preise fallen ueber laengere Zeit (Angst). "
                    "SEITWAERTS = der Preis pendelt in einer Spanne. Jede Phase braucht eine andere "
                    "Strategie - im Seitwaerts kauft man Tiefs und verkauft Hochs, im Bullen laesst "
                    "man Gewinne laufen. Unser Bot erkennt das ueber den 'Regime-Detector' und die "
                    "'Zyklus-Phase' und merkt sich im PhaseMemory, was wann am besten lief."
                ),
                "quiz": {
                    "frage": "Dein Bot zeigt 'MID_BEAR + RANGING'. Was heisst das?",
                    "optionen": [
                        "Baerenmarkt-Zyklus, aktuell seitwaerts pendelnd",
                        "Starker Bullenmarkt",
                        "Die Boerse ist abgestuerzt",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Genau das siehst du gerade im Log. Deshalb waehlt der Bot 'Fear & Greed "
                        "DCA' - Tiefs einsammeln in der Angst."
                    ),
                },
            },
        ],
    },
    # ---------- PHASE 3: RISIKOMANAGEMENT (das Herzstueck) ----------
    {
        "phase": "Phase 3 - Risikomanagement (das Wichtigste!)",
        "lessons": [
            {
                "id": "3.1",
                "titel": "Stop-Loss - deine Notbremse",
                "text": (
                    "Ein Stop-Loss ist ein vorab festgelegter Punkt, an dem du einen Verlust-Trade "
                    "automatisch schliesst, damit aus einem kleinen Verlust kein grosser wird. "
                    "Klingt einfach, ist aber die wichtigste Faehigkeit ueberhaupt. Zu eng = du "
                    "wirst staendig durch normales Rauschen rausgeworfen. Zu weit = einzelne "
                    "Verluste werden riesig. Die Kunst ist, den Stop an die Schwankungsbreite des "
                    "Coins anzupassen - ein Memecoin braucht mehr Luft als BTC."
                ),
                "trade_beispiel": "stop_loss",
                "quiz": {
                    "frage": "Warum ist ein zu enger Stop-Loss gefaehrlich?",
                    "optionen": [
                        "Man wird durch normales Rauschen rausgeworfen, bevor der Trade laeuft",
                        "Er kostet extra Gebuehren",
                        "Er ist nie gefaehrlich",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Genau. Und ein zu WEITER Stop macht einzelne Verluste riesig - siehe "
                        "dein ADA-Trade oben. Die Balance ist alles."
                    ),
                },
            },
            {
                "id": "3.2",
                "titel": "Risk/Reward - das Verhaeltnis, das ueber alles entscheidet",
                "text": (
                    "Risk/Reward (R/R) vergleicht, wie viel du im Schnitt gewinnst gegen wie viel "
                    "du im Schnitt verlierst. R/R von 1.0 = Gewinne und Verluste gleich gross. "
                    "Unter 1.0 = deine Verluste sind groesser als deine Gewinne - dann MUSST du "
                    "eine sehr hohe Trefferquote haben, um trotzdem profitabel zu sein. Genau das "
                    "ist die aktuelle Lage unseres Bots: hohe Trefferquote, aber schlechtes R/R. "
                    "Das macht ihn fragil - faellt die Trefferquote, kippt er ins Minus."
                ),
                "trade_beispiel": "risk_reward",
                "quiz": {
                    "frage": "Dein Bot hat 89% Trefferquote, aber R/R 0.25. Ist das gut?",
                    "optionen": [
                        "Es funktioniert nur SOLANGE die Trefferquote extrem hoch bleibt - fragil",
                        "Perfekt, nichts zu verbessern",
                        "Egal, Hauptsache Trefferquote hoch",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Richtig erkannt. Das ist genau die Baustelle, die wir bei der Auswertung "
                        "angehen: Verluste kleiner machen, damit er nicht von der Trefferquote abhaengt."
                    ),
                },
            },
            {
                "id": "3.3",
                "titel": "Position Sizing - wie viel pro Trade?",
                "text": (
                    "Die Positionsgroesse bestimmt, wie viel Geld du in einen einzelnen Trade "
                    "steckst. Profi-Regel: Riskiere pro Trade nur einen kleinen, festen Prozentsatz "
                    "deines Kapitals (oft 1-2%). So ueberlebst du auch eine Pechstraehne. Anfaenger "
                    "machen den Fehler, 'all-in' zu gehen - ein einziger schlechter Trade kann dann "
                    "das Konto ruinieren. (Unser Bot hatte genau so einen Moment: einmal nahm das "
                    "DCA-Sizing fast das komplette Cash - das fixen wir noch.)"
                ),
                "quiz": {
                    "frage": "Wie viel Kapital riskieren Profis typisch pro Trade?",
                    "optionen": [
                        "1-2% des Kontos",
                        "50% des Kontos",
                        "Alles, fuer maximalen Gewinn",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Genau. Kleine feste Risiken pro Trade = du ueberlebst Pechstraehnen. "
                        "Das ist 'risikobasiertes Position-Sizing' auf unserer Roadmap."
                    ),
                },
            },
        ],
    },
    # ---------- PHASE 4: PSYCHOLOGIE & KONSISTENZ ----------
    {
        "phase": "Phase 4 - Psychologie & Konsistenz",
        "lessons": [
            {
                "id": "4.1",
                "titel": "Die zwei Feinde: Angst und Gier",
                "text": (
                    "Fast alle Trading-Verluste kommen aus zwei Emotionen: GIER (zu frueh rein, zu "
                    "gross, Gewinn nicht mitnehmen) und ANGST (Verlust nicht akzeptieren, Stop "
                    "wegnehmen, in der Hoffnung 'es kommt zurueck'). Der groesste Vorteil eines "
                    "Bots ist, dass er KEINE Emotionen hat - er folgt stur den Regeln. Deine "
                    "Aufgabe als Mensch ist, dem Bot nicht reinzufunken, wenn die Angst kommt. "
                    "Genau deshalb bauen wir einen Bot: um die Emotion aus der Gleichung zu nehmen."
                ),
                "quiz": {
                    "frage": "Was ist der groesste Vorteil eines Trading-Bots?",
                    "optionen": [
                        "Er handelt ohne Angst und Gier, stur nach Regeln",
                        "Er gewinnt immer",
                        "Er braucht keine Strategie",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Genau. Disziplin ohne Emotion ist sein Edge - vorausgesetzt, der Mensch "
                        "funkt nicht rein."
                    ),
                },
            },
            {
                "id": "4.2",
                "titel": "Das Trading-Journal - warum wir alles aufschreiben",
                "text": (
                    "Profis fuehren ueber JEDEN Trade Buch: Einstieg, Ausstieg, GRUND fuer den "
                    "Trade, und Ergebnis. Warum? Weil du nur aus dem lernst, was du ehrlich "
                    "festhaeltst. Genau das macht unser Bot automatisch: trades_v5.json ist dein "
                    "Journal, und der Sensei zieht Lektionen daraus. Du als Trader solltest dir "
                    "angewoehnen, bei jedem Trade zu fragen: 'Warum genau steige ich ein - und wo "
                    "liege ich falsch, wenn der Markt gegen mich laeuft?'"
                ),
                "quiz": {
                    "frage": "Was gehoert ins Trading-Journal?",
                    "optionen": [
                        "Einstieg, Ausstieg, Grund und Ergebnis jedes Trades",
                        "Nur die Gewinne",
                        "Nur das Datum",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Richtig - besonders der GRUND. Ohne ihn kannst du nicht lernen, ob deine "
                        "These stimmte oder du nur Glueck hattest."
                    ),
                },
            },
            {
                "id": "4.3",
                "titel": "Geduld & der Weg zur Konsistenz",
                "text": (
                    "Der letzte und schwerste Schritt: Konsistenz. Nicht der eine grosse Gewinn "
                    "zaehlt, sondern viele kleine, ueber Monate. Das bedeutet: nicht jeden Tag "
                    "handeln muessen, Verluste als Geschaeftskosten akzeptieren, und am Plan "
                    "festhalten auch wenn es mal nicht laeuft. Genau deshalb gehen wir mit unserem "
                    "Bot NICHT sofort live, sondern sammeln erst Wochen an Daten ueber "
                    "verschiedene Marktphasen. Geduld ist hier kein Zoegern - sie ist die Strategie."
                ),
                "quiz": {
                    "frage": "Warum gehen wir mit dem Bot nicht sofort live?",
                    "optionen": [
                        "Wir sammeln erst Daten ueber mehrere Marktphasen - Geduld ist die Strategie",
                        "Weil der Bot kaputt ist",
                        "Aus Angst",
                    ],
                    "richtig": 0,
                    "erklaerung": (
                        "Genau. Echte Reife zeigt sich erst, wenn der Bot Bulle, Baer UND Crash "
                        "gesehen hat. Bis dahin: messen, lernen, verbessern."
                    ),
                },
            },
        ],
    },
]


class Akademie:
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.root = project_root
        self.trades_path = os.path.join(self.root, "data_store", "trades_v5.json")
        self.progress_path = os.path.join(self.root, "data_store", "akademie_fortschritt.json")

    # ---------- Fortschritt ----------
    def _load_progress(self) -> dict:
        try:
            if os.path.exists(self.progress_path):
                with open(self.progress_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"erledigt": [], "quiz_richtig": 0, "quiz_gesamt": 0}

    def _save_progress(self, p: dict):
        try:
            tmp = self.progress_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(p, f, indent=2)
            os.replace(tmp, self.progress_path)
        except Exception:
            pass

    # ---------- Echte Trades als Lehrmaterial ----------
    def _load_trades(self) -> list:
        try:
            with open(self.trades_path, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else d.get("trades", [])
        except Exception:
            return []

    def real_example(self, kind: str) -> str:
        """Liefert ein echtes Trade-Beispiel passend zum Lektions-Thema."""
        trades = self._load_trades()
        sells = [t for t in trades if "SELL" in str(t.get("side", t.get("type", ""))).upper()]
        if not sells:
            return ""
        if kind == "stop_loss":
            sl = [t for t in sells if "STOP_LOSS" in str(t.get("strategy", t.get("active_strategy", ""))).upper()]
            if sl:
                worst = min(sl, key=lambda t: float(t.get("pnl") or 0))
                sym = worst.get("symbol", worst.get("coin", "?"))
                return (f"DEIN ECHTER TRADE: Ein STOP_LOSS bei {sym} hat "
                        f"{float(worst.get('pnl') or 0):+.2f}$ realisiert. Das war einer deiner "
                        f"groessten Einzelverluste - genau das Muster, das ein zu starrer "
                        f"Stop-Loss erzeugt.")
        if kind == "risk_reward":
            wins = [float(t.get("pnl") or 0) for t in sells if float(t.get("pnl") or 0) > 0]
            losses = [float(t.get("pnl") or 0) for t in sells if float(t.get("pnl") or 0) < 0]
            if wins and losses:
                aw = sum(wins) / len(wins)
                al = sum(losses) / len(losses)
                rr = abs(aw / al) if al else 0
                return (f"DEINE ECHTEN ZAHLEN: Schnitt-Gewinn {aw:+.2f}$, Schnitt-Verlust "
                        f"{al:+.2f}$ -> R/R {rr:.2f}. Bei {len(wins)} Gewinnern und "
                        f"{len(losses)} Verlierern haelt dich nur die hohe Trefferquote im Plus.")
        return ""

    # ---------- Konsolen-Lernmodus ----------
    def run_console(self):
        p = self._load_progress()
        print("\n" + "=" * 60)
        print("  TRADING-AKADEMIE  -  dein Weg vom Nullpunkt zum Trader")
        print("=" * 60)
        done = len(p["erledigt"])
        total = sum(len(ph["lessons"]) for ph in CURRICULUM)
        print(f"Fortschritt: {done}/{total} Lektionen | "
              f"Quiz: {p['quiz_richtig']}/{p['quiz_gesamt']} richtig\n")

        for phase in CURRICULUM:
            print("\n" + "-" * 60)
            print("  " + phase["phase"])
            print("-" * 60)
            for L in phase["lessons"]:
                mark = "[x]" if L["id"] in p["erledigt"] else "[ ]"
                print(f"  {mark} {L['id']}  {L['titel']}")

        print("\nLektion waehlen (z.B. 1.1), 'quiz 3.1' fuer Quiz, oder 'exit':")
        while True:
            try:
                cmd = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if cmd in ("exit", "quit", "q"):
                break
            quiz_mode = cmd.startswith("quiz ")
            lid = cmd.replace("quiz ", "").strip()
            lesson = self._find(lid)
            if not lesson:
                print("Lektion nicht gefunden. Format: 1.1 / 2.3 / quiz 3.1 / exit")
                continue
            if quiz_mode:
                self._run_quiz(lesson, p)
            else:
                self._show_lesson(lesson, p)
        self._save_progress(p)
        print("\nFortschritt gespeichert. Bis zum naechsten Mal, Schueler.")

    def _find(self, lid: str):
        for ph in CURRICULUM:
            for L in ph["lessons"]:
                if L["id"] == lid:
                    return L
        return None

    def _show_lesson(self, L, p):
        print("\n" + "=" * 60)
        print(f"  LEKTION {L['id']}: {L['titel']}")
        print("=" * 60)
        print(L["text"])
        if L.get("trade_beispiel"):
            ex = self.real_example(L["trade_beispiel"])
            if ex:
                print("\n>>> " + ex)
        print("\n(Tipp: 'quiz " + L["id"] + "' testet dein Wissen.)")
        if L["id"] not in p["erledigt"]:
            p["erledigt"].append(L["id"])
            self._save_progress(p)

    def _run_quiz(self, L, p):
        q = L.get("quiz")
        if not q:
            print("Kein Quiz fuer diese Lektion.")
            return
        print("\nQUIZ " + L["id"] + ": " + q["frage"])
        for i, opt in enumerate(q["optionen"]):
            print(f"  {i + 1}) {opt}")
        try:
            ans = int(input("Deine Antwort (Nummer): ").strip()) - 1
        except (ValueError, EOFError, KeyboardInterrupt):
            print("Abgebrochen.")
            return
        p["quiz_gesamt"] += 1
        if ans == q["richtig"]:
            p["quiz_richtig"] += 1
            print("\nRICHTIG! " + q["erklaerung"])
        else:
            print("\nNicht ganz. " + q["erklaerung"])
            print(f"(Richtige Antwort: {q['optionen'][q['richtig']]})")
        self._save_progress(p)


if __name__ == "__main__":
    Akademie().run_console()
