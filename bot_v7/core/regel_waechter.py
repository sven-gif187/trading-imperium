# -*- coding: utf-8 -*-
"""
core/regel_waechter.py - passt auf den Drei-Stufen-Schalter auf
================================================================
WARUM ES DIESE DATEI GIBT

Am 12.08.2026 um 21:05 speicherte der Eigentuemer in der
Einstellungsmaske seine Telegram-Daten. Dabei verschwand aus
data_store/config.json der Block "regel_modi" - AppConfig.save() baute
die Datei komplett aus den bekannten Feldern neu auf, und was es nicht
kannte, fiel still heraus.

Folge: Der Drei-Stufen-Schalter faellt bei fehlender Angabe bewusst auf
ACTIVE zurueck (damit ein Vertipper nie eine SCHUETZENDE Regel
abschaltet). Damit war der Trend-Ausstieg wieder scharf - eine Regel, die
in 46 gemessenen Faellen zu 0 % im Plus lag und 36,08 $ gekostet hat.
Ausgeloest durch das Speichern einer voellig unbeteiligten Einstellung.

Die Ursache ist behoben (settings.py erhaelt jetzt fremde Bloecke). Aber:

    DAS PROBLEM WAR NICHT NUR DER FEHLER, SONDERN DASS ER STUMM WAR.

Aufgefallen ist er nur daran, dass eine Zeile im Protokoll FEHLTE
("[SCHALTER] NICHT scharf: ..."). Ein fehlender Eintrag ist das
schlechteste denkbare Alarmsignal - zwischen tausenden Logzeilen sieht
niemand, was nicht da ist.

Deshalb dieser Waechter. Er dreht das um: Statt zu schweigen, wenn alles
stimmt, und zu schweigen, wenn etwas fehlt, SCHREIT er bei jeder
unerwarteten Aenderung - mehrfach und auf Wegen, die man nicht uebersieht.

WIE ER ARBEITET

Beim ersten Lauf legt er eine Referenz an (regel_modi_soll.json): so
sollen die Schalter stehen. Danach vergleicht er bei jedem Lauf den
Ist-Zustand damit.

Weicht etwas ab, meldet er auf DREI Wegen:
  1. Ein mehrzeiliger Alarmblock als FEHLER ins Protokoll (nicht als
     INFO - der geht in der Masse unter)
  2. Ein Ticket in tickets.txt, das der Bot selbst ins
     ENTWICKLERHANDBUCH.md uebernimmt - ein dauerhafter Beleg, der auch
     nach Tagen noch auffindbar ist
  3. Eine Telegram-Nachricht, falls eingerichtet

Wer eine Schalterstellung ABSICHTLICH aendert, bestaetigt das einmal mit
    python regel_waechter_bestaetigen.py
Danach ist der neue Stand die Referenz und der Alarm verstummt.

GRUNDSATZ: Lieber ein Alarm zu viel als eine Regel, die heimlich wieder
scharf ist.
"""
import json
import os
import time

try:
    from config.settings import DATA_DIR
except Exception:                                   # Testbarkeit ohne Bot
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "data_store")

try:
    from core.logger import log
except Exception:
    class _L:
        def info(self, m, s): print(f"[{m}] {s}")
        def warn(self, m, s): print(f"[{m}] {s}")
        def error(self, m, s): print(f"[{m}] {s}")
    log = _L()

from core.regel_schalter import BEKANNTE_REGELN, ACTIVE

SOLL_DATEI = os.path.join(DATA_DIR, "regel_modi_soll.json")
CONFIG_DATEI = os.path.join(DATA_DIR, "config.json")

# Regeln, bei denen ACTIVE die GEFAEHRLICHE Richtung ist. Bei ihnen ist ein
# stiller Rueckfall auf ACTIVE schlimmer als bei den anderen, weil sie
# gemessen Geld gekostet haben.
RISKANT_WENN_AKTIV = {
    "trend_exit": "46 Faelle, 0 % im Plus, Summe -36,08 $ (Messung 10.08.)",
}


class RegelWaechter:
    """Vergleicht die Schalterstellungen mit der hinterlegten Referenz."""

    def __init__(self, schalter, telegram=None, tickets_datei=None):
        self.schalter = schalter
        self.telegram = telegram
        self.tickets_datei = tickets_datei or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tickets.txt")
        self.letzter_alarm = {}      # regel -> Zeitpunkt, gegen Dauerfeuer

    # ------------------------------------------------------------------
    def soll_lesen(self):
        try:
            if os.path.exists(SOLL_DATEI):
                with open(SOLL_DATEI, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                modi = daten.get("modi")
                if isinstance(modi, dict) and modi:
                    return modi
        except Exception as e:
            log.warn("REGEL-WAECHTER", f"Referenz nicht lesbar: {str(e)[:60]}")
        return None

    def soll_schreiben(self, modi, grund=""):
        try:
            os.makedirs(os.path.dirname(SOLL_DATEI), exist_ok=True)
            with open(SOLL_DATEI, "w", encoding="utf-8") as f:
                json.dump({
                    "_hinweis": "SOLL-Zustand der acht Regel-Schalter. Wird vom "
                                "Waechter mit der Konfiguration verglichen. "
                                "Aendern nur ueber regel_waechter_bestaetigen.py.",
                    "modi": modi,
                    "gesetzt_am": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "grund": grund,
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            log.warn("REGEL-WAECHTER", f"Referenz nicht schreibbar: {str(e)[:60]}")
            return False

    # ------------------------------------------------------------------
    def block_fehlt(self):
        """Steht der Block ueberhaupt noch in der config.json?"""
        try:
            with open(CONFIG_DATEI, "r", encoding="utf-8") as f:
                return "regel_modi" not in (json.load(f) or {})
        except Exception:
            return False          # Datei unlesbar -> nicht auch noch Alarm

    def pruefen(self):
        """Ein Durchlauf. Gibt die Liste der Abweichungen zurueck (leer = alles gut)."""
        try:
            self.schalter.neu_laden()
        except Exception:
            pass
        ist = dict(getattr(self.schalter, "modi", {}) or {})

        soll = self.soll_lesen()
        if soll is None:
            # Erster Lauf: heutigen Stand als Referenz festhalten.
            self.soll_schreiben(ist, "erstmalig beim Start des Waechters")
            log.info("REGEL-WAECHTER",
                     f"Referenz angelegt: {self._kurz(ist)}")
            return []

        abweichungen = []
        for regel in BEKANNTE_REGELN:
            s, i = soll.get(regel, ACTIVE), ist.get(regel, ACTIVE)
            if s != i:
                abweichungen.append((regel, s, i))

        if not abweichungen and not self.block_fehlt():
            return []

        self._alarm(abweichungen, soll, ist)
        return abweichungen

    # ------------------------------------------------------------------
    def _kurz(self, modi):
        aus = [f"{r}={m}" for r, m in sorted(modi.items()) if m != ACTIVE]
        return ", ".join(aus) if aus else "alle ACTIVE"

    def _alarm(self, abweichungen, soll, ist):
        fehlt = self.block_fehlt()

        zeilen = ["", "=" * 62,
                  "  ALARM: DIE REGEL-SCHALTER STEHEN ANDERS ALS HINTERLEGT",
                  "=" * 62]
        if fehlt:
            zeilen += [
                "  Der Block \"regel_modi\" fehlt in data_store/config.json.",
                "  Dann faellt JEDE Regel auf ACTIVE zurueck - auch die, die",
                "  bewusst stillgelegt wurden.",
                "",
            ]
        for regel, s, i in abweichungen:
            zeile = f"  {regel}: soll {s}  ->  IST {i}"
            if i == ACTIVE and regel in RISKANT_WENN_AKTIV:
                zeile += "   *** WIEDER SCHARF ***"
            zeilen.append(zeile)
            if i == ACTIVE and regel in RISKANT_WENN_AKTIV:
                zeilen.append(f"      Warum das zaehlt: {RISKANT_WENN_AKTIV[regel]}")
        zeilen += [
            "",
            "  Wenn das ABSICHT war:  python regel_waechter_bestaetigen.py",
            "  Sonst: regel_modi in data_store/config.json wiederherstellen",
            "  und den Bot neu starten.",
            "=" * 62, ""]
        text = "\n".join(zeilen)

        # 1) Ins Protokoll - als FEHLER, damit es sich abhebt
        for z in text.splitlines():
            log.error("REGEL-WAECHTER", z)

        # 2) Ticket schreiben - der dauerhafte Beleg, auch Tage spaeter noch
        #    auffindbar. Nur einmal je Regel und Stunde, sonst laeuft die
        #    Datei voll.
        jetzt = time.time()
        neue = [a for a in abweichungen
                if jetzt - self.letzter_alarm.get(a[0], 0) > 3600]
        if neue or (fehlt and jetzt - self.letzter_alarm.get("_block", 0) > 3600):
            self._ticket(abweichungen, fehlt)
            for regel, _, _ in abweichungen:
                self.letzter_alarm[regel] = jetzt
            if fehlt:
                self.letzter_alarm["_block"] = jetzt

        # 3) Telegram, falls eingerichtet
        try:
            if self.telegram is not None:
                kurz = ", ".join(f"{r}: {s}->{i}" for r, s, i in abweichungen)
                self.telegram.send(
                    "🚨 REGEL-SCHALTER VERSTELLT\n"
                    + ("Block regel_modi fehlt in der Konfiguration!\n" if fehlt else "")
                    + (kurz or "-")
                    + "\nBestaetigen mit regel_waechter_bestaetigen.py")
        except Exception:
            pass

    def _ticket(self, abweichungen, fehlt):
        try:
            teile = ["BUG: REGEL-SCHALTER VERSTELLT - automatisch gemeldet vom "
                     f"Waechter am {time.strftime('%d.%m.%Y %H:%M')}."]
            if fehlt:
                teile.append("Der Block regel_modi FEHLT in data_store/config.json - "
                             "damit faellt jede Regel auf ACTIVE zurueck.")
            for regel, s, i in abweichungen:
                stueck = f"{regel}: soll {s}, ist {i}."
                if i == ACTIVE and regel in RISKANT_WENN_AKTIV:
                    stueck += (f" ACHTUNG, diese Regel ist damit WIEDER SCHARF - "
                               f"{RISKANT_WENN_AKTIV[regel]}")
                teile.append(stueck)
            teile.append("War es Absicht, mit regel_waechter_bestaetigen.py "
                         "bestaetigen. Sonst config.json wiederherstellen und "
                         "neu starten.")
            with open(self.tickets_datei, "a", encoding="utf-8") as f:
                f.write("\n\n" + " ".join(teile) + "\n")
        except Exception as e:
            log.warn("REGEL-WAECHTER", f"Ticket nicht geschrieben: {str(e)[:60]}")

    # ------------------------------------------------------------------
    def status(self):
        soll = self.soll_lesen() or {}
        ist = dict(getattr(self.schalter, "modi", {}) or {})
        return {"soll": soll, "ist": ist,
                "block_fehlt": self.block_fehlt(),
                "abweichungen": [r for r in BEKANNTE_REGELN
                                 if soll.get(r, ACTIVE) != ist.get(r, ACTIVE)]}
