# -*- coding: utf-8 -*-
"""
data/source_health.py - Gesundheit der externen Signalquellen  [E10-QUELLEN 29.07.2026]
=======================================================================================
WARUM ES DIESE DATEI GIBT

Im Log vom 29.07. steht:

    [REDDIT] r/CryptoCurrency: Status 403

Danach gibt reddit_sentiment.analyze_sentiment() zurueck:

    {"score": 0.5, "label": "NEUTRAL", "posts": 0, "details": "Keine Reddit-Daten"}

Diese 0.5 wanderte anschliessend ungebremst weiter:

    extra_score = cap*0.2 + fund*0.3 + whale*0.2 + reddit*0.3
    raw_scores  = {..., "reddit": reddit_score, ...}  -> EnsembleSignal

Eine tote Quelle hat also nicht etwa "nichts beigetragen", sondern mit
vollem Gewicht eine feste 0.5 beigesteuert. Das ist schlimmer als sie
wegzulassen: es zieht jedes echte Signal Richtung neutral. Bei Reddit
sind das 30 % des Zusatz-Scores und 5 % des Ensembles - dauerhaft
konstant, ohne dass es irgendwo auffiel, weil die Kette an jeder Stelle
mit `except Exception: pass` und `.get("score", 0.5)` abgesichert ist.

WIE ES JETZT LAEUFT

EnsembleSignal.calculate() normiert bereits ueber die Quellen, die im
uebergebenen Dict VORHANDEN sind (total_weight waechst nur fuer
gefundene Schluessel). Es genuegt also, tote Quellen gar nicht erst
einzutragen - dann verteilt sich ihr Gewicht automatisch auf die
lebenden. Genau das macht `gesunde_auswahl()`.

GRUNDSATZ: Nur was BEWIESEN tot ist, wird abgeschaltet. Eine Quelle
gilt als tot bei einer Ausnahme, bei einem "error"-Feld oder wenn sie
selbst meldet, keine Daten zu haben (z. B. posts == 0). Im Zweifel
bleibt sie an - lieber eine schwache Quelle dulden als eine gute
faelschlich stummschalten.
"""
import time

try:
    from core.logger import log
except Exception:                                   # Testbarkeit ohne Bot
    class _L:
        def info(self, m, s): print(f"[{m}] {s}")
        def warn(self, m, s): print(f"[{m}] {s}")
    log = _L()


class SourceHealth:
    """Merkt sich je Quelle, wann sie zuletzt echte Daten geliefert hat."""

    def __init__(self, max_alter_min=30):
        self.max_alter_min = float(max_alter_min)
        self._zustand = {}      # name -> {"ok": bool, "zeit": epoch, "detail": str}
        self._letzte_meldung = {}

    # ---------- Schreiben ----------
    def melde(self, name, ok, detail=""):
        vorher = self._zustand.get(name, {}).get("ok")
        self._zustand[name] = {"ok": bool(ok), "zeit": time.time(),
                               "detail": str(detail)[:80]}
        # Zustandswechsel einmal melden, nicht bei jedem Durchlauf spammen
        if vorher is not None and vorher != bool(ok):
            if ok:
                log.info("QUELLEN", f"{name}: liefert wieder Daten ({detail})")
            else:
                log.warn("QUELLEN", f"{name}: AUSGEFALLEN ({detail}) - "
                                    f"faellt aus der Gewichtung, statt neutral mitzuzaehlen")

    # ---------- Lesen ----------
    def ist_gesund(self, name):
        """Unbekannte Quellen gelten als gesund (nichts stummschalten, was nie gemeldet hat)."""
        z = self._zustand.get(name)
        if z is None:
            return True
        if not z.get("ok"):
            return False
        return (time.time() - z.get("zeit", 0)) <= self.max_alter_min * 60

    def hat_gemeldet(self, name):
        """Hat sich die Quelle seit dem Start ueberhaupt EINMAL gemeldet?

        [GEFUNDENE-PROBLEME #30, 12.08.2026] Absichtlich getrennt von
        ist_gesund(). Die beiden beantworten verschiedene Fragen, und beide
        Antworten sind an ihrer Stelle richtig:

          ist_gesund()   -> "darf die Quelle mitentscheiden?"
                            Unbekannt = ja. Im Zweifel dulden, sonst wuerde
                            eine Quelle direkt nach dem Start stummgeschaltet,
                            nur weil sie noch nicht dran war.

          hat_gemeldet() -> "ist das ein echter Messwert?"
                            Unbekannt = NEIN. Nach jedem Neustart ist der
                            Zustandsspeicher leer. Bis eine Quelle sich das
                            erste Mal meldet, steht im State noch ihr ALTER
                            Wert - und der als Messpunkt aufgezeichnet waere
                            eine Luege.

        Beobachtet am 12.08. in markt_historie:
            10:26 | ... | reddit 0.5    <- alter Wert, sah aus wie Messung
            10:43 | ... | reddit None   <- korrekt als Luecke
        Reddit ist seit dem 29.07. tot; die 0.5 stammte aus dem State.
        """
        return name in self._zustand

    def gesunde_auswahl(self, scores: dict) -> dict:
        """Filtert ein Score-Dict auf die lebenden Quellen.

        EnsembleSignal normiert ueber die vorhandenen Schluessel - was hier
        herausfaellt, verteilt sein Gewicht automatisch auf den Rest.
        """
        return {k: v for k, v in (scores or {}).items() if self.ist_gesund(k)}

    def gewichteter_wert(self, paare) -> float:
        """Gewichteter Mittelwert nur ueber gesunde Quellen.

        paare: [(name, wert, gewicht), ...]
        Faellt alles aus -> 0.5 (neutral), aber dann bewusst und sichtbar.
        """
        summe, gewicht = 0.0, 0.0
        for name, wert, g in paare:
            if not self.ist_gesund(name):
                continue
            try:
                summe += float(wert) * float(g)
                gewicht += float(g)
            except Exception:
                continue
        return (summe / gewicht) if gewicht > 0 else 0.5

    # ---------- Anzeige ----------
    def tote(self):
        return [n for n in self._zustand if not self.ist_gesund(n)]

    def status_zeile(self):
        lebend = [n for n in self._zustand if self.ist_gesund(n)]
        tot = self.tote()
        teile = [f"{len(lebend)}/{len(self._zustand)} Quellen aktiv"]
        if tot:
            teile.append("AUSGEFALLEN: " + ", ".join(
                f"{n} ({self._zustand[n].get('detail') or '?'})" for n in tot))
        return " | ".join(teile)

    def status(self):
        jetzt = time.time()
        return {n: {"ok": self.ist_gesund(n),
                    "alter_min": round((jetzt - z.get("zeit", jetzt)) / 60, 1),
                    "detail": z.get("detail", "")}
                for n, z in self._zustand.items()}
