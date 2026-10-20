# -*- coding: utf-8 -*-
"""Warte-Auftraege (Limit-Orders) fuer den Papierpfad.

WOZU DAS HIER EXISTIERT
-----------------------
Der Bot kauft bisher ausschliesslich mit Sofort-Auftraegen (Market Order,
Fachbegriff "Taker"): er nimmt den Preis, der gerade da ist, und zahlt
0,25 % je Seite. Ein Warte-Auftrag (Limit Order, "Maker") legt ein Angebot
etwas unter den Markt und wartet, bis der Kurs dorthin kommt - dafuer nur
0,10 % je Seite, und der Einstieg liegt guenstiger.

Gemessen am 11.09.2026 an 382 echten Kaeufen des Bots (BTC/ETH/SOL,
15-Minuten-Kerzen vom 09.03. bis 08.09.2026):

    Abstand 0,10 %, gueltig 4 Kerzen   Vorteil +0,161 Prozentpunkte je Runde
    Vertrauensintervall                +0,077 bis +0,237, enthaelt die Null nicht

WAS DIE MESSUNG GEKOSTET HAT - und was sie NICHT verspricht
-----------------------------------------------------------
Die erste Fassung der Messung (warteauftrag_gegenauslese.py) rechnete an
ZUFAELLIGEN Zeitpunkten und wies die Trivial-Latte nicht aus. Beides wurde
am 11.09. nachgeholt, und beides aenderte das Ergebnis:

1. GEGENAUSLESE (adverse selection). Ein Warte-Auftrag unter dem Markt wird
   nur bedient, wenn der Kurs zu dir FAELLT. An den echten Kaufzeitpunkten
   des Bots gemessen: die Faelle, in denen er NICHT gefuellt haette, liefen
   vier Stunden spaeter im Schnitt +1,142 %, die gefuellten -0,106 %. Ein
   Unterschied von 1,248 Prozentpunkten. Der Bot verpasst also genau die
   guten Faelle. Der Vorteil ueberlebt das, aber er halbiert sich - von
   +0,20 auf +0,161 Prozentpunkte.

2. TRIVIAL-LATTE. Ein nicht ausgefuehrter Auftrag zaehlt in der Rechnung als
   0 %. Weil der Sofortkauf im Mittel NEGATIV ist, ist Nichthandeln fuer
   sich genommen schon ein Gewinn - ein Verfahren, das nie ausfuehrt,
   schlaegt den Bot. Zerlegt man den Vorteil in seine zwei Quellen, kommt
   bei dieser Einstellung nichts davon aus dem Nichthandeln (-0,055) und
   alles aus dem besseren Preis (+0,216). Bei 0,50 % Abstand waere es
   umgekehrt: dort sind +0,327 von +0,435 reiner Nichthandel-Schein.
   Deshalb steht der Abstand fest auf 0,10 % und nicht hoeher.

WARUM DIE AUSFUEHRUNGSQUOTE IM BETRIEB NIEDRIGER LIEGEN WIRD
------------------------------------------------------------
Die Messung sieht das TIEF jeder 15-Minuten-Kerze. Der Bot sieht nur, was
bei seiner Abfrage gerade auf dem Ticker steht - alle 12 Sekunden, also
rund 75 Blicke je Kerze. Ein Tief, das zwischen zwei Blicken liegt und
sofort wieder weg ist, entgeht ihm. Die gemessenen 73,3 % sind damit eine
OBERGRENZE, keine Vorhersage. Dasselbe steht in
docs/messungen_2026-07/BEFUNDE.md:406 ueber die Vorgaenger-Messung F1e:
"Die Fuellquote in F1e ist eine BERUEHRUNGSQUOTE ... nur die Obergrenze."

Was im Betrieb wirklich herauskommt, steht in `ausgefuehrt` und `verfallen`
und laesst sich nachher gegen die 73,3 % halten.

WARUM KEIN GELD RESERVIERT WIRD
-------------------------------
Der naheliegende Weg waere, den Betrag beim Anlegen aus der Papierkasse zu
nehmen und beim Verfall zurueckzugeben - so macht es eine echte Boerse.
Hier waere das gefaehrlich: die Papierkasse liegt in `bot_state.json`
(`paper_balances_backup`), diese Warteschlange in einer eigenen Datei. Zwei
Kassen, die bei jedem Absturz zwischen zwei Schreibvorgaengen auseinander-
laufen koennen - und eine verlorene Reservierung sieht man erst, wenn Geld
fehlt. Befund 51 und der Waechter-Alarm vom 05.08. kamen aus genau dieser
Art von Doppelbuchhaltung.

Stattdessen fuehrt die Warteschlange nur die ABSICHT. Ob das Geld reicht,
wird erst beim Fuellen geprueft - dort, wo es der Sofortkauf auch prueft
(`engine.py:_execute_paper`, "Balance: ..."). Reicht es nicht, wird der
Auftrag abgelehnt wie jeder andere auch. Die Obergrenze fuer offene
Positionen (max_open_positions) begrenzt ohnehin, wie viel gleichzeitig
unterwegs sein kann.

AENDERT NICHTS, SOLANGE DER SCHALTER AUS IST
--------------------------------------------
`data_store/config.json` -> `warteauftraege.aktiv`. Steht er auf false
(Vorgabe), wird diese Datei zwar geladen, aber nie gefragt.
"""
import io
import json
import os
import tempfile
import time

VORGABE = {
    # Aus bleibt aus, bis eine Epochengrenze gesetzt ist. Das Einschalten
    # ist eine Verhaltensaenderung und macht jeden Vorher-Nachher-Vergleich
    # ueber die Grenze hinweg ungueltig (config_epochs.json).
    "aktiv": False,
    # 0,10 % unter dem Marktpreis. Nicht hoeher - siehe Trivial-Latte oben.
    "abstand_pct": 0.10,
    # 4 Kerzen a 15 Minuten = 1 Stunde. Laenger heisst mehr Ausfuehrungen,
    # aber staerkere Gegenauslese; gemessen ist kuerzer netto besser:
    #   2 Kerzen +0,177 | 4 Kerzen +0,161 | 8 Kerzen +0,126 | 12 Kerzen +0,112
    # 4 statt 2, weil 2 am Rand des geprueften Bereichs liegt.
    "gueltig_kerzen": 4,
    "kerze_minuten": 15,
    # Nur der Papierpfad. Im Livebetrieb braucht ein Warte-Auftrag eine
    # echte Order an der Boerse, keine nachgespielte - das ist ein anderer
    # Bau und steht hier bewusst nicht drin.
    "nur_paper": True,
}


class Warteschlange:
    """Haelt die offenen Warte-Auftraege und raeumt nach Neustart auf."""

    def __init__(self, pfad=None, einstellungen=None, jetzt=None):
        self.pfad = pfad or os.path.join("data_store", "warteauftraege.json")
        self.einst = dict(VORGABE)
        if isinstance(einstellungen, dict):
            for k, v in einstellungen.items():
                if k in self.einst:
                    self.einst[k] = v
        self.auftraege = {}          # symbol -> Auftrag
        self.verlauf = {"angelegt": 0, "ausgefuehrt": 0, "verfallen": 0,
                        "verworfen": 0}
        self._laden(jetzt if jetzt is not None else time.time())

    # ------------------------------------------------------------------
    @property
    def aktiv(self):
        return bool(self.einst.get("aktiv"))

    def gueltig_sekunden(self):
        return (float(self.einst.get("gueltig_kerzen", 4))
                * float(self.einst.get("kerze_minuten", 15)) * 60.0)

    def limitpreis(self, marktpreis):
        return float(marktpreis) * (1.0 - float(self.einst["abstand_pct"]) / 100.0)

    # ------------------------------------------------------------------
    def anlegen(self, symbol, marktpreis, betrag_usd, angaben=None, jetzt=None):
        """Legt einen Warte-Auftrag an. Gibt den Auftrag zurueck, oder None.

        None heisst: fuer dieses Symbol wartet schon einer. Zwei Auftraege
        auf dieselbe Muenze waeren ein doppelter Einstieg - genau das
        verhindert die Idempotenz-Sperre beim Sofortkauf auch.
        """
        if marktpreis is None or float(marktpreis) <= 0:
            return None
        if symbol in self.auftraege:
            return None
        jetzt = time.time() if jetzt is None else jetzt
        auftrag = {
            "symbol": symbol,
            "limitpreis": round(self.limitpreis(marktpreis), 8),
            "marktpreis_bei_anlage": round(float(marktpreis), 8),
            "betrag_usd": round(float(betrag_usd), 4),
            "angelegt_ts": jetzt,
            "verfaellt_ts": jetzt + self.gueltig_sekunden(),
            "abstand_pct": float(self.einst["abstand_pct"]),
            "angaben": dict(angaben or {}),
        }
        self.auftraege[symbol] = auftrag
        self.verlauf["angelegt"] += 1
        self._speichern()
        return auftrag

    def pruefen(self, kurse, jetzt=None):
        """Ein Takt. Gibt (gefuellt, verfallen) als zwei Listen zurueck.

        `kurse` ist ein Dict symbol -> aktueller Preis. Fehlt ein Symbol,
        bleibt sein Auftrag unberuehrt - ein fehlender Kurs darf einen
        Auftrag weder fuellen noch verfallen lassen. (Befund 95: bei
        Netzausfall friert der Kurs ein; ein eingefrorener Kurs, der
        zufaellig unter dem Limit steht, wuerde sonst reihenweise fuellen.)
        """
        jetzt = time.time() if jetzt is None else jetzt
        gefuellt, verfallen = [], []
        for symbol in list(self.auftraege.keys()):
            a = self.auftraege[symbol]
            kurs = kurse.get(symbol) if isinstance(kurse, dict) else None
            if kurs is None or float(kurs) <= 0:
                # [14.09.2026] NOTVERFALL - ohne ihn bleibt der Auftrag EWIG.
                #
                # Die Regel darueber ist richtig: ein fehlender Kurs darf
                # einen Auftrag weder fuellen noch verfallen lassen
                # (Befund 95, eingefrorene Kurse). Sie hat aber eine Folge,
                # die beim Bauen nicht bedacht war: Kommt ein Symbol GAR
                # NICHT mehr - weil es aus der Muenzliste fiel, umbenannt
                # wurde oder nie eines war - wird sein Auftrag nie wieder
                # angesehen. Er bleibt fuer immer stehen.
                #
                # Und das ist nicht nur unordentlich: `anlegen()` lehnt
                # einen zweiten Auftrag auf dasselbe Symbol ab. Ein ewig
                # haengender Auftrag SPERRT die Muenze also dauerhaft vom
                # Handel aus.
                #
                # Aufgefallen am 14.09. durch einen eigenen Fehler:
                # befund68_test.py legte einen Auftrag auf "TEST/USDC" in
                # der ECHTEN Warteschlange an. Fuer dieses Symbol gibt es
                # keinen Kurs - er lag noch da, als der Test zum zweiten
                # Mal lief, und liess ihn durchfallen. Der Test hatte recht,
                # nur nicht ueber das, was er pruefen wollte.
                #
                # Der Notverfall greift erst beim DOPPELTEN der Frist.
                # Damit bleibt die Absicht von Befund 95 erhalten: ein
                # Netzausfall von einer Stunde laesst nichts verfallen,
                # denn die normale Frist ist ja auch eine Stunde. Erst wer
                # doppelt so lange keinen Kurs mehr sieht, ist wirklich weg.
                _frist = a.get("verfaellt_ts")
                if _frist is not None:
                    _spanne = self.gueltig_sekunden()
                    if jetzt >= float(_frist) + _spanne:
                        a["verfallen_ts"] = jetzt
                        a["verfallen_grund"] = (
                            "Notverfall: seit %.0f Minuten kein Kurs fuer %s"
                            % ((jetzt - float(_frist) + _spanne) / 60.0, symbol))
                        verfallen.append(a)
                        del self.auftraege[symbol]
                        self.verlauf["verfallen"] += 1
                continue
            if float(kurs) <= a["limitpreis"]:
                a["gefuellt_ts"] = jetzt
                a["gefuellt_kurs"] = float(kurs)
                gefuellt.append(a)
                del self.auftraege[symbol]
                self.verlauf["ausgefuehrt"] += 1
            elif jetzt >= a["verfaellt_ts"]:
                a["verfallen_ts"] = jetzt
                verfallen.append(a)
                del self.auftraege[symbol]
                self.verlauf["verfallen"] += 1
        if gefuellt or verfallen:
            self._speichern()
        return gefuellt, verfallen

    def erledigen(self, symbol, art):
        """Nimmt einen Auftrag heraus und zaehlt ihn RICHTIG.

        [17.09.2026] Fuer den Echtbetrieb gebraucht. Dort entscheidet die
        Boerse ueber Ausfuehrung und Verfall, nicht `pruefen()` - der
        Live-Takt muss den Auftrag also selbst herausnehmen.

        WARUM NICHT `abbrechen()`: Das zaehlt jeden Auftrag als
        **verworfen**, egal was mit ihm geschah. Ein ausgefuehrter
        Warte-Auftrag stuende damit in derselben Spalte wie einer, der
        wegen eines Notaus zurueckgezogen wurde. Genau diese Zahlen
        beantworten spaeter die Frage, ob sich Warte-Auftraege lohnen -
        eine falsch gefuellte Spalte macht die Messung wertlos, ohne
        dass es auffaellt.

        `art` ist "ausgefuehrt", "verfallen" oder "verworfen".
        """
        a = self.auftraege.pop(symbol, None)
        if a is None:
            return None
        if art not in self.verlauf:
            # Lieber eine sichtbare Unbekannte als eine still falsche
            # Spalte.
            art = "verworfen"
            a["zaehl_hinweis"] = "unbekannte Art, als verworfen gezaehlt"
        a["erledigt_als"] = art
        self.verlauf[art] += 1
        self._speichern()
        return a

    def abbrechen(self, symbol, grund=""):
        """Nimmt einen Auftrag zurueck. Fuer den Fall, dass die Muenze aus
        der Liste faellt oder ein Notaus greift."""
        a = self.auftraege.pop(symbol, None)
        if a is not None:
            a["verworfen_grund"] = grund
            self.verlauf["verworfen"] += 1
            self._speichern()
        return a

    def offene(self):
        return dict(self.auftraege)

    # ------------------------------------------------------------------
    def _laden(self, jetzt):
        """Liest den gespeicherten Stand und raeumt sofort auf.

        Das Aufraeumen beim Laden ist der Grund, warum diese Klasse
        ueberhaupt eine Datei hat. Ein Auftrag, der beim Absturz offen war,
        ist nach dem Neustart fast immer laengst verfallen - er darf nicht
        stillschweigend wieder scharf werden, nur weil der Bot neu startet.
        """
        if not os.path.exists(self.pfad):
            return
        try:
            with io.open(self.pfad, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            # Kaputte Datei: lieber ohne Auftraege starten als mit Muell.
            # Nicht stillschweigend - der Aufrufer sieht es an `verlauf`.
            self.verlauf["verworfen"] += 1
            return
        if not isinstance(d, dict):
            return
        self.verlauf.update({k: v for k, v in (d.get("verlauf") or {}).items()
                             if k in self.verlauf})
        for symbol, a in (d.get("auftraege") or {}).items():
            if not isinstance(a, dict) or "verfaellt_ts" not in a:
                continue
            if jetzt >= float(a["verfaellt_ts"]):
                self.verlauf["verfallen"] += 1      # beim Start verfallen
                continue
            self.auftraege[symbol] = a

    def _speichern(self):
        """Atomar: erst in eine Nebendatei, dann umbenennen.

        Ohne das kann ein Absturz mitten im Schreiben eine halbe JSON-Datei
        hinterlassen - und beim naechsten Start waeren alle Auftraege weg,
        ohne dass jemand es merkt.
        """
        ordner = os.path.dirname(os.path.abspath(self.pfad))
        try:
            if ordner and not os.path.isdir(ordner):
                os.makedirs(ordner)
            fd, tmp = tempfile.mkstemp(dir=ordner, prefix=".warteauftraege_",
                                       suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"auftraege": self.auftraege,
                           "verlauf": self.verlauf,
                           "einstellungen": self.einst,
                           "_geschrieben": time.time()},
                          f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.pfad)
            return True
        except Exception as fehler:
            # Kein stilles Scheitern. Der Fehler wird festgehalten, damit
            # `warteauftrag_test.py` und der Waechter ihn sehen; der naechste
            # Takt versucht es erneut. Ein Schreibfehler darf den Handel
            # nicht anhalten, aber er darf auch nicht unsichtbar bleiben.
            self.letzter_schreibfehler = str(fehler)[:200]
            return False


def einstellungen_lesen(configpfad=None):
    """Liest den Block `warteauftraege` aus data_store/config.json.

    Bewusst direkt aus der Datei und nicht ueber AppConfig: `_from_dict`
    laedt nur Bloecke, fuer die es ein Dataclass-Feld gibt, und dieses hier
    hat keines. `AppConfig.save()` erhaelt den Block trotzdem, seit Befund 31
    fremde Schluessel uebernimmt (config/settings.py:387-395) - er geht beim
    Speichern in der Einstellungsmaske also nicht verloren.
    """
    pfad = configpfad or os.path.join("data_store", "config.json")
    try:
        with io.open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        w = d.get("warteauftraege")
        return w if isinstance(w, dict) else {}
    except Exception:
        return {}
