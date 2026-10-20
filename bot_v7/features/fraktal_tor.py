# -*- coding: utf-8 -*-
"""Das Fraktal-Tor: Stufe 2 des neuen Handelswegs - der Anschluss an den Handel.

WOZU DIESE DATEI UEBERHAUPT GEBAUT WURDE
----------------------------------------
Am 14.09.2026 lief der Live-Bot zum ersten Mal und kaufte viermal BTC.
Der Grund stand woertlich im Log (data_store/system.log:248):

    BTC/USDC: Score 9/10 -> BUY | MACD positiv + EMA-Trend up
    + Starker Trend (ADX 35) + Ueber VWAP + Orderbook Kaufdruck
    + V4-EMA_TREND STARK

Fuenf Signale, alle Trendfolge. Kein Fibonacci, keine Fraktale, keine
Konfluenz. Die Pruefung ergab: `features/fraktal_konfluenz.py` wurde von
KEINEM Handelspfad importiert - nur von der eigenen Testdatei.

Das ist der entscheidende Punkt, und er ist kein Detail:

    Trendfolge kauft NACH dem Anstieg - "starker Trend, ueber VWAP,
    MACD positiv" heisst uebersetzt "er laeuft schon".
    Svens Verfahren kauft IM RUECKSETZER - im Golden Pocket, also
    nachdem der Kurs von einem Hoch zurueckgekommen ist.

Das sind gegensaetzliche Ansaetze. Der Bot tat das Gegenteil dessen, was
vorgegeben war. Sven am 14.09.: *"ich verstehe auch nicht warum er
bitcoin zu so einem hohen kurs kauft das kann doch nur schief gehen."*
Die Beobachtung war richtig, und die Ursache war diese fehlende Datei.

WARUM EIN TOR UND KEINE WEITEREN PUNKTE
---------------------------------------
Der naheliegende Einbau waere gewesen, Konfluenz als weitere Punkte in
den Score zu geben (`score += 2, "Golden Pocket"`). Das waere falsch
gewesen - und zwar auf eine Weise, die man erst spaet merkt:

Bei Schwelle 7 von 10 erreichen die Trendfolge-Signale die Schwelle
bereits allein. Am 14.09. kam Score 9 zustande OHNE jeden Fibonacci-
Beitrag. Zusaetzliche Punkte haetten daran nichts geaendert - der Bot
haette weiter oben gekauft, nur mit einer hoeheren Zahl daneben.

Ein Tor wirkt anders herum: Es kann einen Kauf VERHINDERN, den die
Punkte erlauben wuerden. Genau das ist gebraucht.

    Score sagt:   "die Lage ist guenstig"
    Tor sagt:     "aber der PREIS ist es nicht"

WAS DAS TOR NICHT TUT
---------------------
Es loest keinen Kauf aus. Ein Preis mitten im Golden Pocket, zu dem der
Score unter der Schwelle liegt, fuehrt zu keinem Handel. Das Tor kann
nur ablehnen, nie erlauben. Damit bleibt die gemessene Schwelle 7
(Befund 103, an 57 Verkaeufen) unangetastet und vergleichbar.

DER SCHALTER
------------
`config.trading.fraktal_tor_aktiv` - Vorgabe AUS. Ein Tor, das
Kaeufe verhindert, veraendert das Verhalten des Bots und braucht damit
nach CLAUDE.md Abschnitt 5 eine Epochengrenze. Der Schalter erlaubt
ausserdem den Schattenbetrieb: Bei `fraktal_tor_nur_messen = True`
schreibt das Tor seine Entscheidung ins Log, haelt aber nichts auf.
So entsteht die Messung, bevor das Verhalten sich aendert.
"""
import time

try:
    from core.logger import log
except Exception:                                      # pragma: no cover
    class _Log:
        def info(self, *a): pass
        def warn(self, *a): pass
        def error(self, *a): pass
    log = _Log()

from features.fraktal_konfluenz import (konfluenz, stufen_einer_welle,
                                        wellen_aus_fraktalen)


# ====================================================================
# Einstellungen
# ====================================================================
# Die Zeitrahmen der Konfluenz. Ein Rechtecksignal auf EINEM Zeitrahmen
# ist Zufall; erst wenn Stufen aus verschiedenen Zeitrahmen am selben
# Preis liegen, ist es eine Zone im Sinne des Verfahrens.
ZEITRAHMEN = ("1h", "4h", "1d")

# Wie viele Kerzen je Zeitrahmen. 200 reicht fuer die juengsten drei
# Wellen und haelt den Abruf klein.
KERZEN = 200

# Wie lange geholte Kerzen gelten duerfen, je Zeitrahmen (Sekunden).
# Der Bot prueft alle 12 s - Tageskerzen dabei jedes Mal neu zu laden
# waere sinnlos und wuerde ins Abruflimit der Boerse laufen.
FRISCHE = {"1h": 300, "4h": 1200, "1d": 3600}

# Wie nah der Preis an der Zonenmitte liegen muss, wenn die Zone selbst
# keine Breite hat (eine einzelne Stufe ist ein Punkt, kein Band).
# In Prozent - absolut waere die Regel bei BTC eine andere als bei SOL.
NAEHE_PCT = 0.35

# Mindestscore einer Zone, damit sie als Kaufzone zaehlt. Der Score aus
# `_zone_bauen` ist die Zahl UNABHAENGIGER Quellen plus je ein Punkt fuer
# Golden Pocket und fuer mehr als einen Zeitrahmen.
#
# 3 bedeutet damit im schwaechsten Fall: zwei unabhaengige Quellen und
# ein Golden Pocket - oder drei unabhaengige Quellen. Eine einzelne
# Fibonacci-Linie (Score 1) reicht nie.
MIN_ZONEN_SCORE = 3

# Wie weit ueber dem aktuellen Preis noch nach Zonen gesucht wird.
# Ohne diesen Puffer wuerde `nur_unter=preis` genau die Zone
# wegschneiden, in welcher der Preis GERADE steht.
PUFFER_PCT = 0.5

# ====================================================================
# Die zwei Regeln, die aus der Rueckmessung kamen (14.09.2026)
# ====================================================================
# Die erste Fassung des Tors haette DREI der vier Kaeufe vom 14.09.
# durchgelassen - gemessen mit fraktal_rueckblick.py. Der Grund war
# nicht die Konfluenz-Rechnung, die stimmte. Es waren zwei fehlende
# Bedingungen, und beide sind der Kern von Svens Verfahren:
#
# FEHLER 1 - Winzige Wellen zaehlten wie grosse.
# Auf dem 1h-Zeitrahmen fanden sich Wellen mit 0,63 % Spanne. Ihr
# Golden Pocket war 16 $ breit, bei 0,505 % Kosten also schmaler als
# die Gebuehren des Handels. Solche Stufen sind Rauschen mit einer
# Zahl daneben. Eine Welle muss gross genug sein, dass der Weg vom
# Einstieg zum Wellenhoch die Kosten ueberhaupt decken kann.
#
# 2,0 % ist rund das Vierfache der Kosten. Vom Golden Pocket
# (61,8 %-Ruecksetzer) bis zurueck zum Hoch sind das etwa 1,3 %
# Weg - schon knapp, aber messbar oberhalb der Kosten.
MIN_WELLE_PCT = 2.0

# FEHLER 2 - Flache Ruecksetzer galten als Kaufzone.
# Die Zone, die am 14.09. den Kauf erlaubt haette, lag bei 79.068 $ -
# gebildet aus 0,236er und 0,382er Stufen der grossen Tageswellen.
# Bei einem 23,6 %-Ruecksetzer steht der Kurs noch fast am Hoch.
# Genau das war der Vorwurf: "warum kauft er bitcoin zu so einem
# hohen kurs".
#
# Svens Verfahren zielt auf das Golden Pocket, also 61,8 bis 65 %.
# Die Kaufzone beginnt daher bei 0,5 und geht nach unten - flachere
# Stufen bilden keine Kaufzone. Sie bleiben in der Anzeige sichtbar,
# aber sie oeffnen das Tor nicht.
MIN_RUECKSETZER = 0.5

# FEHLER 3 - und der eigentliche. Abwaertswellen bildeten Kaufzonen.
#
# Auch mit den beiden Regeln oben haette das Tor drei der vier Kaeufe
# durchgelassen. Die Zone, die sie erlaubte, bestand aus diesen Stufen:
#
#   4h  Welle 76.047-79.890 abwaerts   Stufe 0,786  ->  79.068 $
#   4h  Welle 76.047-79.890 abwaerts   Stufe 0,866  ->  79.375 $
#   1d  Welle 76.888-81.479 aufwaerts  Stufe 0,500  ->  79.183 $
#   1d  Welle 76.264-82.300 aufwaerts  Stufe 0,500  ->  79.282 $
#
# Die ersten beiden sind Retracements einer ABWAERTSbewegung. Ein
# Ruecksetzer einer Abwaertsbewegung laeuft nach OBEN - so eine Linie
# ist ein WIDERSTAND, keine Unterstuetzung. Dort verkauft man, dort
# kauft man nicht.
#
# Rechnerisch war alles richtig: stufen_einer_welle() rechnet bei
# aufwaerts=False korrekt vom Tief nach oben. Der Fehler lag eine
# Ebene hoeher - im Tor, das beide Richtungen in denselben Topf warf.
#
# Die Folge war heimtueckisch, weil sie plausibel aussah: Die tiefen
# Ruecksetzer einer Abwaertswelle liegen KNAPP UNTER DEM LETZTEN HOCH.
# Das Tor meldete also eine starke Konfluenzzone aus vier Quellen und
# zwei Zeitrahmen - genau da, wo der Kurs am teuersten war.
#
# Svens Verfahren kauft im Ruecksetzer einer AUFWAERTSbewegung. Nur
# solche Wellen bilden hier eine Kaufzone.
NUR_AUFWAERTSWELLEN = True

# Wie viele Wellen je Zeitrahmen betrachtet werden - ROH, also vor den
# Filtern oben.
#
# Stand zuerst auf 3, wie in fraktal_konfluenz.py. Das war zu wenig,
# sobald der Richtungsfilter dazukam: An echten BTC-Daten gemessen
# (14.09.) blieben von 3 Wellen je Zeitrahmen ueber alle drei
# Zeitrahmen zusammen nur ZWEI brauchbare uebrig - zu wenig fuer eine
# Zone mit Score 3, und das Tor waere nie aufgegangen.
#
# Ein Tor, das immer zu ist, besteht jede Pruefung auf "lehnt ab" und
# ist trotzdem wertlos. Es handelt dann nicht weniger falsch, sondern
# gar nicht.
#
# Da etwa die Haelfte aller Wellen abwaerts laeuft, entsprechen 6 rohe
# Wellen ungefaehr den 3 aufwaerts gerichteten, die urspruenglich
# gemeint waren. Gemessen an denselben Daten: 1h 1, 4h 1, 1d 3 -
# zusammen 5 brauchbare Quellen.
WELLEN_JE_ZEITRAHMEN = 6


class FraktalTor:
    """Entscheidet, ob der aktuelle Preis ein Einstiegspreis ist.

    Liest nur. Kennt weder Orders noch Positionen noch Guthaben.
    """

    def __init__(self, data_agent, config=None):
        self.data_agent = data_agent
        self.config = config
        self._kerzen = {}          # (symbol, tf) -> (zeitpunkt, df)
        self._letzte = {}          # symbol -> letztes Urteil (fuer die Anzeige)
        self.stat_geprueft = 0
        self.stat_abgelehnt = 0
        # Werden in _kaufzonen je Pruefung neu gesetzt. Hier angelegt,
        # damit sie auch dann existieren, wenn pruefe() vorher abbricht
        # (z. B. Preis 0) und jemand die Zahlen liest.
        self._verworfen_klein = 0
        self._verworfen_abwaerts = 0
        self._wellen_gesamt = 0

    # ----------------------------------------------------------------
    def _hole_kerzen(self, symbol, tf):
        """Kerzen eines Zeitrahmens, mit Ablauf nach FRISCHE.

        Gibt None zurueck, wenn nichts zu holen ist. Bewusst KEIN
        try/except um den Rueckgabewert herum, das den Fehler
        verschluckt - ein fehlender Zeitrahmen muss sichtbar sein,
        sonst faellt das Tor still auf weniger Zeitrahmen zurueck und
        niemand merkt es (CLAUDE.md Abschnitt 7.4).
        """
        schluessel = (symbol, tf)
        jetzt = time.time()
        alt = self._kerzen.get(schluessel)
        if alt and (jetzt - alt[0]) < FRISCHE.get(tf, 300):
            return alt[1]

        snap = self.data_agent.fetch_snapshot(symbol, tf=tf, limit=KERZEN)
        df = getattr(snap, "_df", None) if snap is not None else None
        if df is None or len(df) < 20:
            # AUCH DEN FEHLSCHLAG MERKEN.
            #
            # Erster Entwurf speicherte nur Erfolge. Ein Zeitrahmen, der
            # dauerhaft nichts liefert (Boerse kennt ihn nicht, Symbol
            # falsch geschrieben), wurde dadurch bei JEDER Pruefung neu
            # abgefragt - und der Bot prueft alle 12 Sekunden. Im Test
            # sichtbar geworden: 13 Abrufe statt 3.
            #
            # Das waeren rund 7.200 vergebliche Abrufe am Tag je Coin
            # und Zeitrahmen, also der sichere Weg ins Abruflimit der
            # Boerse - mit der Folge, dass auch die EchtenAbrufe
            # gedrosselt werden.
            #
            # Kurze Sperre statt der vollen Frist: Ein voruebergehender
            # Ausfall soll sich nach einer Minute erholen duerfen, ohne
            # dass eine Tageskerze eine Stunde lang blockiert bleibt.
            self._kerzen[schluessel] = (jetzt - FRISCHE.get(tf, 300) + 60, None)
            log.warn("FRAKTAL", f"{symbol} {tf}: keine verwertbaren Kerzen "
                                f"({0 if df is None else len(df)}) - "
                                f"60 s gesperrt")
            return None

        self._kerzen[schluessel] = (jetzt, df)
        return df

    # ----------------------------------------------------------------
    def _kaufzonen(self, daten, preis):
        """Konfluenzzonen, die als KAUFZONE taugen.

        Unterschied zu `zonen_aus_zeitrahmen` aus fraktal_konfluenz.py:
        Dort werden alle Stufen aller Wellen verrechnet - richtig so,
        das ist die Anzeige- und Messfunktion, und sie darf nichts
        verschweigen.

        Hier wird gehandelt, und dafuer gelten zwei zusaetzliche
        Bedingungen (Begruendung oben bei MIN_WELLE_PCT und
        MIN_RUECKSETZER):

            1. Die Welle muss gross genug sein, dass der Weg zurueck
               zum Hoch die Handelskosten decken kann.
            2. Nur tiefe Ruecksetzer ab 0,5 bilden eine Kaufzone.
               Bei 0,236 steht der Kurs noch fast am Hoch.

        Beide Filter greifen VOR der Zonenbildung. Wuerden sie
        hinterher greifen, haetten die aussortierten Stufen den Score
        der Zone schon aufgeblaeht - und der Score soll die Zahl
        unabhaengiger Beobachtungen sein, nicht die Zahl gezeichneter
        Linien.
        """
        listen = []
        self._verworfen_klein = 0
        self._verworfen_abwaerts = 0
        self._wellen_gesamt = 0

        for tf, df in (daten or {}).items():
            if df is None or len(df) < 6:
                continue
            for w in wellen_aus_fraktalen(df, weite=2,
                                          hoechstens=WELLEN_JE_ZEITRAHMEN):
                self._wellen_gesamt += 1

                # Nur Ruecksetzer von Aufwaertsbewegungen. Bei einer
                # Abwaertswelle laeuft der Ruecksetzer nach oben - das
                # ist ein Widerstand, und er liegt knapp unter dem
                # letzten Hoch. Begruendung ausfuehrlich oben bei
                # NUR_AUFWAERTSWELLEN.
                if NUR_AUFWAERTSWELLEN and not w["aufwaerts"]:
                    self._verworfen_abwaerts += 1
                    continue

                spanne_pct = ((w["hoch"] - w["tief"]) / w["tief"] * 100.0
                              if w["tief"] else 0.0)
                if spanne_pct < MIN_WELLE_PCT:
                    self._verworfen_klein += 1
                    continue
                stufen = stufen_einer_welle(
                    w["hoch"], w["tief"], aufwaerts=w["aufwaerts"],
                    zeitrahmen=tf, welle_id=w["id"])

                # Die WELLE an jede Stufe haengen.
                #
                # Ohne das weiss die Zone spaeter nur, BEI WELCHEM PREIS
                # sie liegt - nicht, aus welcher Bewegung sie stammt. Der
                # Ausstieg braucht aber genau das: Seine Ziele sind
                # Verlaengerungen derselben Welle, in der gekauft wurde
                # (features/fraktal_ziele.py).
                #
                # Das Handbuch nennt das als offenen Punkt in 6.10:
                # "In Stufe 2 fehlt die Struktur-Pruefung. Das Swing-Tief
                # der Kaufzone ist an der Position nicht gespeichert."
                # Hier faengt die Kette an, die das schliesst.
                for s in stufen:
                    s["welle_hoch"] = w["hoch"]
                    s["welle_tief"] = w["tief"]
                    s["welle_spanne_pct"] = spanne_pct
                # Nur tiefe Ruecksetzer. Die Anker (0 und 1) fallen in
                # konfluenz() ohnehin raus, aber hier faellt auch alles
                # Flache weg.
                listen.append([s for s in stufen
                               if s["verhaeltnis"] >= MIN_RUECKSETZER])

        if not listen:
            return []

        zonen = konfluenz(listen,
                          nur_unter=preis * (1.0 + PUFFER_PCT / 100.0))
        return sorted(zonen, key=lambda z: (-z["score"], -z["mitte"]))

    # ----------------------------------------------------------------
    def pruefe(self, symbol, preis):
        """Darf zu diesem Preis gekauft werden?

        Rueckgabe: dict mit
            erlaubt    True/False
            grund      Klartext, geht so ins Log
            zone       die getroffene Zone (oder die naechste darunter)
            abstand    Abstand zur naechsten Zone in Prozent
        """
        self.stat_geprueft += 1

        if not preis or preis <= 0:
            return {"erlaubt": False, "grund": "kein Preis", "zone": None,
                    "abstand": None}

        daten = {}
        for tf in ZEITRAHMEN:
            df = self._hole_kerzen(symbol, tf)
            if df is not None:
                daten[tf] = df

        # Mit weniger als zwei Zeitrahmen gibt es keine Multi-Timeframe-
        # Konfluenz. Dann DARF das Tor nicht erlauben, aber es darf auch
        # nicht so tun, als haette es geprueft.
        if len(daten) < 2:
            self.stat_abgelehnt += 1
            return {"erlaubt": False,
                    "grund": f"nur {len(daten)} Zeitrahmen verfuegbar - "
                             f"Konfluenz nicht pruefbar",
                    "zone": None, "abstand": None}

        zonen = self._kaufzonen(daten, preis)

        tauglich = [z for z in zonen if z["score"] >= MIN_ZONEN_SCORE]
        if not tauglich:
            self.stat_abgelehnt += 1
            urteil = {"erlaubt": False,
                      "grund": f"keine Konfluenzzone mit Score >= "
                               f"{MIN_ZONEN_SCORE} unter {preis:,.2f} "
                               f"({self._wellen_gesamt} Wellen gesehen, "
                               f"{self._verworfen_abwaerts} abwaerts, "
                               f"{self._verworfen_klein} unter "
                               f"{MIN_WELLE_PCT}% Spanne)",
                      "zone": None, "abstand": None}
            self._letzte[symbol] = urteil
            return urteil

        # Treffer: Preis im Zonenband ODER nah genug an der Mitte.
        # Beides noetig - eine Zone aus einer einzigen Stufe hat
        # unten == oben == mitte und damit keine Breite.
        treffer = None
        for z in tauglich:
            if z["unten"] <= preis <= z["oben"]:
                treffer = z
                break
            if z["mitte"] > 0 and abs(preis - z["mitte"]) / z["mitte"] * 100.0 <= NAEHE_PCT:
                treffer = z
                break

        if treffer is None:
            naechste = max(tauglich, key=lambda z: z["mitte"])
            abstand = (preis - naechste["mitte"]) / naechste["mitte"] * 100.0
            self.stat_abgelehnt += 1
            urteil = {
                "erlaubt": False,
                "grund": f"Preis {preis:,.2f} liegt {abstand:+.2f}% neben der "
                         f"naechsten Zone ({naechste['mitte']:,.2f}, Score "
                         f"{naechste['score']}, {'+'.join(naechste['zeitrahmen'])})",
                "zone": naechste, "abstand": abstand}
            self._letzte[symbol] = urteil
            return urteil

        gp = " GOLDEN POCKET" if treffer["golden_pocket"] else ""

        # DIE TRAGENDE WELLE der Zone bestimmen.
        #
        # Eine Zone entsteht aus mehreren Stufen verschiedener Wellen.
        # Fuer die Ausstiegsziele zaehlt EINE davon - und zwar die
        # groesste: Sie gibt den weitesten Weg und damit das Ziel, das
        # die Handelskosten am ehesten deckt. Die kleineren Wellen
        # liegen innerhalb davon.
        #
        # `treffer["stufen"]` ist nach Gewicht sortiert (Golden Pocket
        # zuerst), aber Gewicht ist nicht Groesse. Deshalb hier
        # ausdruecklich nach Spanne, nicht auf die Sortierung verlassen.
        welle = None
        kandidaten = [s for s in treffer.get("stufen", [])
                      if s.get("welle_hoch") and s.get("welle_tief")]
        if kandidaten:
            beste = max(kandidaten, key=lambda s: s.get("welle_spanne_pct", 0))
            welle = {"hoch": beste["welle_hoch"], "tief": beste["welle_tief"],
                     "spanne_pct": beste.get("welle_spanne_pct", 0.0),
                     "zeitrahmen": beste.get("zeitrahmen", ""),
                     "verhaeltnis": beste.get("verhaeltnis")}

        urteil = {
            "erlaubt": True,
            "grund": f"Konfluenzzone {treffer['unten']:,.2f}-{treffer['oben']:,.2f}"
                     f" Score {treffer['score']} aus {treffer['quellen']} Quellen"
                     f" ({'+'.join(treffer['zeitrahmen'])}){gp}",
            "zone": treffer, "abstand": 0.0, "welle": welle}
        self._letzte[symbol] = urteil
        return urteil

    # ----------------------------------------------------------------
    def letztes_urteil(self, symbol):
        return self._letzte.get(symbol)

    def statistik(self):
        return {"geprueft": self.stat_geprueft,
                "abgelehnt": self.stat_abgelehnt,
                "durchgelassen": self.stat_geprueft - self.stat_abgelehnt}
