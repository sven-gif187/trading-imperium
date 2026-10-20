# -*- coding: utf-8 -*-
"""
chartlabor_daten.py - holt den KOMPLETTEN Kursverlauf und legt ihn als JSON ab
==============================================================================
WARUM ES DIESE DATEI GIBT UND NICHT features/chart_data.py BENUTZT WIRD

Sven wollte am 06.09.2026 "den ganzen Chartverlauf von Bitcoin". Der
vorhandene Lader kann das nicht - und zwar aus einem Grund, den man nur
sieht, wenn man ihn liest (features/chart_data.py:87-90):

    if existing:
        start_ms = int(existing[-1]["open_time"]) + INTERVAL_MS[interval]
    else:
        start_ms = want_start

Liegt schon eine Cache-Datei da, wird NUR AB DER LETZTEN GESPEICHERTEN
KERZE VORWAERTS geholt - nie rueckwaerts. Der Cache versperrt damit jede
tiefere Historie: BTCUSDT_1d.csv enthielt 15 Zeilen, und eine Anfrage
ueber 4000 Tage lieferte trotzdem nur 37 Kerzen. Nicht weil Binance
nichts hergibt, sondern weil der Lader gar nicht erst zurueckfragt.

Diese Datei geht den anderen Weg: sie fragt vom gewuenschten Startpunkt
an vorwaerts, unabhaengig davon was schon da liegt, und schreibt in
einen EIGENEN Ordner. Der Zwischenspeicher des Bots wird nicht
angefasst - waehrend des Messfensters wird an data_store nichts
veraendert.

WAS ES TUT
----------
Holt OHLCV-Kerzen von Binance (oeffentlich, kein Schluessel noetig) und
legt sie unter chartlabor/daten/<SYMBOL>_<INTERVALL>.json ab. Reine
Datenbeschaffung, kein Handelseingriff.

BTCUSDT gibt es bei Binance seit dem 17.08.2017. Weiter zurueck reicht
diese Quelle nicht - wer die Jahre davor braucht, muss eine andere
Quelle dazunehmen. Das steht hier, damit niemand spaeter glaubt, die
Daten seien verlorengegangen.

AUFRUF
------
    python chartlabor_daten.py                 BTC in allen Zeitrahmen
    python chartlabor_daten.py BTCUSDT 1d      nur ein Zeitrahmen
    python chartlabor_daten.py --alle          alle Handels-Coins
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ZIEL = os.path.join(HIER, "daten")

BINANCE = "https://api.binance.com/api/v3/klines"
BINANCE_ALT = "https://data-api.binance.vision/api/v3/klines"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"

# ===================================================================
# WELCHE MAERKTE ES GIBT UND WOHER SIE KOMMEN
# -------------------------------------------------------------------
# [08.09.2026, Wunsch von Sven: "bau die charts noch fuer gold und
# silber dazu"]
#
# Binance ist eine KRYPTOBOERSE. Gold gibt es dort nur als Token
# (PAXGUSDT, Pax Gold) und erst ab 01.08.2020 - Silber ueberhaupt
# nicht. Deshalb kommen die Metalle von Yahoo Finance, und zwar BEIDE
# von dort: eine Quelle fuer Gold und Silber heisst, dass man die
# beiden gegeneinander halten kann.
#
# WAS DAS FUER ZAHLEN SIND: GC=F und SI=F sind die COMEX-TERMINKONTRAKTE
# (Futures) auf Gold und Silber, nicht der Kassapreis. Gegengerechnet am
# 08.09.2026 gegen den Binance-Token PAXG: die beiden weichen zwischen
# -1,31 % und +0,65 % voneinander ab. Das ist kein Fehler, sondern der
# Unterschied zwischen zwei verschiedenen Dingen - wer auf den Cent
# genau den Kassapreis braucht, braucht eine dritte Quelle.
#
# "pause_tage" sagt, wie lange der Markt geschlossen sein darf, ohne
# dass die Frischepruefung Alarm schlaegt. Krypto laeuft durch, die
# Metallboerse hat Wochenende.
MAERKTE = {
    "BTCUSDT": {"name": "BTC/USDT",  "quelle": "binance", "pause_tage": 0},
    "ETHUSDT": {"name": "ETH/USDT",  "quelle": "binance", "pause_tage": 0},
    "SOLUSDT": {"name": "SOL/USDT",  "quelle": "binance", "pause_tage": 0},
    "GOLD":    {"name": "Gold (COMEX)",   "quelle": "yahoo",
                "yahoo": "GC=F", "pause_tage": 4},
    "SILBER":  {"name": "Silber (COMEX)", "quelle": "yahoo",
                "yahoo": "SI=F", "pause_tage": 4},
}

# ===================================================================
# WIE LANG EIN ZEITRASTER DAUERN SOLL - die eine Tabelle
# -------------------------------------------------------------------
# Drei Stellen brauchen diese Zahlen: der Abruf bei Yahoo, das Tor vor
# dem Schreiben und die Uebersicht. Sie standen frueher an zwei Stellen
# mit ZWEI VERSCHIEDENEN Toleranzen - das ist genau die Sorte zweite
# Wahrheit, die irgendwann falsch ausgeht.
RASTER_SEKUNDEN = {
    "1M": 2_592_000, "1w": 604_800, "1d": 86_400, "4h": 14_400,
    "1h": 3_600, "15m": 900, "1m": 60, "1s": 1,
}

# Unsere Rasternamen -> die Namen, die Yahoo benutzt.
YAHOO_NAME = {"1M": "1mo", "1w": "1wk", "1d": "1d",
              "1h": "1h", "15m": "15m", "1m": "1m"}

# ===================================================================
# WIE WEIT ZURUECK BEI YAHOO GEFRAGT WIRD - und warum nicht weiter
# -------------------------------------------------------------------
# [21.09.2026, gemessen von Sven auf dem Laptop am 09.09., hier
# nachgeprueft]
#
# ZWEI GRUENDE, WARUM HIER NICHT "max" STEHT AUSSER BEIM MONAT:
#
# 1. YAHOO IGNORIERT BEI range=max DAS INTERVALL. Auf 1d, 1wk und 1mo
#    kommen jedes Mal dieselben rund 268 Monatsbalken zurueck - ohne
#    Fehlermeldung, ohne Hinweis. Wer das nicht misst, zieht einen
#    Fibonacci ueber zehn "Tage" und misst zehn Monate.
#
# 2. DIE ALTEN JAHRGAENGE SIND UNZUVERLAESSIG. Hier am 21.09.2026 im
#    vorhandenen Datenbestand nachgezaehlt (25y): GOLD_1d hatte 440
#    unstimmige Kerzen von 6272, SILBER_1d 243 von 6274 - Balken, deren
#    Schluss ueber dem Hoch oder unter dem Tief liegt. ALLE lagen
#    zwischen 2003 und 2011, die juengste am 14.11.2011. Ab 2012 ist
#    die Reihe sauber.
#
#    Dazu ein zweiter Beleg, dass die alten Jahre nicht bloss Luecken
#    haben, sondern wackeln: derselbe Tag (01.04.2003) kam auf zwei
#    Rechnern mit VERSCHIEDENEN Werten zurueck - einmal Tief 319,30 /
#    Schluss 339,10, einmal Tief 333,80 / Schluss 334,30.
#
# Deshalb zehn saubere Jahre statt zwanzig mit Loechern. Beim Monat
# geht es nicht anders, max ist dort die einzige Spanne, die die
# Geschichte hergibt - die wenigen unstimmigen Balken werden dort
# einzeln weggelassen und gezaehlt (siehe saeubern()).
YAHOO_SPANNE = {"1mo": "max", "1wk": "10y", "1d": "10y",
                "1h": "730d", "15m": "60d", "1m": "7d"}

# Bekannte Intervalle. Der Wert dient NUR noch zum Abschaetzen der
# Dateigroesse - weitergeblaettert wird ueber den Zeitstempel der
# letzten gelieferten Kerze (siehe laden()).
#
# [06.09.2026] Monatskerzen kamen dazu. Frueher sprang der Lader um
# genau ein Intervall weiter. Bei "1M" gibt es dieses eine Intervall
# nicht - Januar hat 31 Tage, Februar 28. Ein fester Sprung von 30
# Tagen haette mal eine Kerze uebersprungen, mal eine doppelt geholt.
# Deshalb wird jetzt ab "letzte Kerze + 1 ms" weitergefragt; doppelte
# fallen ohnehin beim Zusammenfuehren heraus.
INTERVAL_MS = {
    "1s": 1_000,
    "1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "12h": 43_200_000, "1d": 86_400_000, "3d": 259_200_000,
    "1w": 604_800_000, "1M": 2_592_000_000,
}

# Binance-Start fuer BTCUSDT. Frueher gibt es dort nichts.
HANDELSSTART_MS = 1_502_928_000_000   # 17.08.2017 00:00 UTC

# Welche Zeitrahmen standardmaessig geholt werden.
STANDARD = ["1M", "1w", "1d", "4h", "1h", "15m", "1m", "1s"]

# Wie weit zurueck je Zeitrahmen, in Tagen (Kommazahlen erlaubt).
#
# Die feinen Raster sind bewusst kurz gehalten - nicht aus Bequemlich-
# keit, sondern weil die Zahl sonst explodiert: Sekundenkerzen ueber
# die volle Historie waeren 285 Millionen Stueck. Zum Vergleich, was
# hier tatsaechlich geholt wird:
#     1s  ueber 12 Stunden  =    43.200 Kerzen
#     1m  ueber 30 Tage     =    43.200 Kerzen
#     15m ueber 120 Tage    =    11.520 Kerzen
# Das zeichnet ein Browser noch fluessig. Wer mehr braucht, setzt den
# Wert hier hoch und laesst KURSVERLAUF_HOLEN.bat neu laufen.
#
# [07.09.2026, Wunsch von Sven: "den chart bis zum anfang der zeit"]
# 4h, 1h und 15m gehen jetzt bis zum ersten Handelstag zurueck. Die
# Zahlen dahinter, damit niemand raten muss:
#     4h  ueber 9 Jahre =    19.850 Kerzen  (rund  1,7 MB)
#     1h  ueber 9 Jahre =    79.400 Kerzen  (rund  6,6 MB)
#     15m ueber 9 Jahre =   317.600 Kerzen  (rund   26 MB)
#     1m  ueber 9 Jahre = 4.760.000 Kerzen  (rund  390 MB)  <- geht nicht
#     1s  ueber 9 Jahre =   285 Mio  Kerzen                 <- erst recht
# Bei 1m ist deshalb bei 180 Tagen Schluss (rund 259.000 Kerzen, 21 MB),
# bei 1s bei einem halben Tag. Das ist keine Bequemlichkeit, sondern die
# Grenze dessen, was ein Browser noch als eine Datei einliest.
RUECKBLICK_TAGE = {
    "1M": 4000, "1w": 4000, "1d": 4000, "4h": 4000, "1h": 4000,
    "15m": 4000, "5m": 400, "1m": 180, "1s": 0.5,
}

# Sicherheitsnetz gegen Endlosschleifen - NICHT gegen Groesse.
#
# [07.09.2026] Vorher standen hier 400 Bloecke. Das reichte fuer 400.000
# Kerzen und war damit eine STILLE Groessenbremse: wer 1m ueber die volle
# Historie angefordert haette, haette 400.000 Kerzen aus dem Jahr 2017
# bekommen und keine einzige aktuelle - die Datei haette prall gefuellt
# ausgesehen und waere unbrauchbar gewesen. Das Limit ist jetzt so hoch,
# dass es nur noch eine echte Endlosschleife faengt, und die Vollstaendig-
# keit wird stattdessen am Ende geprueft (siehe frisch_genug).
BLOCK_GRENZE = 5000


def _hole(symbol, interval, start_ms, limit=1000):
    """Ein Block von hoechstens 1000 Kerzen ab start_ms."""
    pfad = f"?symbol={symbol}&interval={interval}&limit={limit}&startTime={start_ms}"
    letzter_fehler = None
    for host in (BINANCE, BINANCE_ALT):
        try:
            req = urllib.request.Request(
                host + pfad, headers={"User-Agent": "chartlabor/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            letzter_fehler = e
            continue
    raise RuntimeError(f"Binance nicht erreichbar: {letzter_fehler}")


def abstand(kerzen):
    """Der mittlere Abstand zweier Kerzen in Sekunden (Median).

    Median und nicht Durchschnitt: ein Wochenende oder eine Feiertags-
    luecke wuerde den Durchschnitt verziehen, den Median nicht.
    """
    if len(kerzen) < 3:
        return None
    d = sorted(kerzen[i+1]["t"] - kerzen[i]["t"] for i in range(len(kerzen)-1))
    return d[len(d)//2]


def raster_stimmt(kerzen, soll):
    """Halb bis doppelt ist erlaubt - ein Monat hat mal 28 und mal 31 Tage,
    und bei duennen Maerkten fehlen einzelne Stunden. Faktor 31 nicht."""
    ist = abstand(kerzen)
    return ist is None or (soll * 0.5 <= ist <= soll * 2.0)


def kerze_heil(k):
    """Sitzen Eroeffnung und Schluss zwischen Tief und Hoch?

    Klingt selbstverstaendlich, ist es bei Yahoo in alten Jahrgaengen
    aber nicht: dort gibt es Balken mit einem Schluss UEBER dem Hoch.
    """
    return (k["h"] >= k["l"]
            and k["l"] <= k["o"] <= k["h"]
            and k["l"] <= k["c"] <= k["h"])


def saeubern(kerzen):
    """Gibt (heile Kerzen, Anzahl weggeworfen) zurueck.

    WEGLASSEN UND NICHT ZURECHTBIEGEN. Ein Hoch auf den Schlusskurs
    hochzusetzen waere schnell gemacht und eine Luege im Chart: die
    Kerze saehe danach aus wie eine Messung, waere aber geraten.
    Eine fehlende Kerze sieht man, eine erfundene nicht.
    """
    heil = [k for k in kerzen if kerze_heil(k)]
    return heil, len(kerzen) - len(heil)


def _yahoo_holen(yahoo_symbol, spanne, raster):
    """Ein Abruf bei Yahoo. Rueckgabe: Liste von Kerzen im Chartformat.

    HIER STECKT DIE WICHTIGE PRUEFUNG: Yahoo vergroebert das Zeitraster
    stillschweigend, wenn die Spanne zu gross ist. Gemessen am
    08.09.2026: range=max mit interval=1d lieferte 268 Punkte fuer 26
    Jahre - also MONATSKERZEN mit dem Etikett "1d". Angefordert war
    eines, geliefert ein anderes, und keine Fehlermeldung.

    Das ist derselbe Fehlertyp wie die vertauschten Monats- und
    Minutendateien vom 06.09. Deshalb wird hier nicht der Anfrage und
    auch nicht dem Etikett geglaubt, sondern der ABSTAND ZWISCHEN DEN
    PUNKTEN gemessen.
    """
    url = f"{YAHOO}{yahoo_symbol}?range={spanne}&interval={raster}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 chartlabor/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))

    ergebnis = d.get("chart", {}).get("result")
    if not ergebnis:
        hinweis = d.get("chart", {}).get("error")
        raise RuntimeError(f"Yahoo lieferte nichts fuer {yahoo_symbol}: {hinweis}")
    res = ergebnis[0]
    ts = res.get("timestamp") or []
    q = (res.get("indicators", {}).get("quote") or [{}])[0]
    if not ts:
        raise RuntimeError(f"Yahoo lieferte keine Zeitstempel fuer {yahoo_symbol}")

    kerzen = []
    for i, t in enumerate(ts):
        o, h, l, c = (q.get("open") or [])[i:i+1], (q.get("high") or [])[i:i+1], \
                     (q.get("low") or [])[i:i+1], (q.get("close") or [])[i:i+1]
        v = (q.get("volume") or [])[i:i+1]
        if not (o and h and l and c) or None in (o[0], h[0], l[0], c[0]):
            continue                      # Luecke - kein Handel
        kerzen.append({"t": int(t), "o": float(o[0]), "h": float(h[0]),
                       "l": float(l[0]), "c": float(c[0]),
                       "v": float(v[0]) if v and v[0] is not None else 0.0})

    # Die Rasterpruefung - dieselbe Toleranz wie das Tor vor dem
    # Schreiben, damit nicht zwei verschiedene Massstaebe gelten.
    unser_name = {v: k for k, v in YAHOO_NAME.items()}[raster]
    soll = RASTER_SEKUNDEN[unser_name]
    if not raster_stimmt(kerzen, soll):
        raise RuntimeError(
            f"Yahoo hat ein anderes Zeitraster geliefert als bestellt: "
            f"angefordert {raster} (erwartet ~{soll} s), geliefert im "
            f"Schnitt {abstand(kerzen)} s. Falsch beschriftet - Abbruch.")
    return kerzen


# [21.09.2026] HIER STAND _zu_vier_stunden(), das aus Stundenkerzen
# Vier-Stunden-Kerzen zusammenrechnete, weil Yahoo kein 4h anbietet.
# Die Rechnung war richtig und von Hand gegengeprueft - trotzdem ist sie
# raus, Entscheidung von Sven:
#
#     "keine Kerzen aus anderen Rastern zusammenrechnen"
#
# Der Grund ist nicht die Rechnung, sondern die Herkunft. Eine
# zusammengerechnete Kerze sieht im Chart aus wie eine gelieferte, und
# niemand kann ihr ansehen, dass sie abgeleitet ist. Gold und Silber
# haben bei Yahoo kein 4-Stunden- und kein Sekundenraster - die Knoepfe
# bleiben dort grau, so wie rasterDa() in chartlabor.html es ohnehin
# vorsieht.


def laden_yahoo(symbol, interval, melden=print):
    """Kerzen fuer einen Yahoo-Markt (Gold, Silber)."""
    ysym = MAERKTE[symbol]["yahoo"]
    if interval not in YAHOO_NAME:
        raise ValueError(
            f"{symbol}: Zeitraster {interval} gibt es bei Yahoo nicht. "
            f"Vorhanden: {', '.join(YAHOO_NAME)}")
    yname = YAHOO_NAME[interval]
    return _yahoo_holen(ysym, YAHOO_SPANNE[yname], yname)


def laden(symbol="BTCUSDT", interval="1d", tage=None, melden=print):
    """Holt den Verlauf VOM ANFANG AN - unabhaengig davon, was schon da liegt."""
    # Metalle kommen von woanders her.
    if MAERKTE.get(symbol, {}).get("quelle") == "yahoo":
        return laden_yahoo(symbol, interval, melden)
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unbekanntes Intervall: {interval}")
    if tage is None:
        tage = RUECKBLICK_TAGE.get(interval, 400)

    jetzt_ms = int(time.time() * 1000)
    start = max(jetzt_ms - int(tage * 86_400_000), HANDELSSTART_MS)

    kerzen = []
    cur = start
    bloecke = 0
    while cur < jetzt_ms:
        block = _hole(symbol, interval, cur)
        bloecke += 1
        if not block:
            break
        for k in block:
            kerzen.append({
                "t": int(k[0]) // 1000,          # Sekunden, so will es der Chart
                "o": float(k[1]), "h": float(k[2]),
                "l": float(k[3]), "c": float(k[4]),
                "v": float(k[5]),
            })
        # Ab der letzten gelieferten Kerze + 1 ms weiterfragen. Bewusst
        # NICHT "+ ein Intervall": bei Monatskerzen gibt es kein festes
        # Intervall, ein Pauschalsprung wuerde Kerzen ueberspringen.
        naechster = int(block[-1][0]) + 1
        if naechster <= cur:      # kein Fortschritt -> sonst Endlosschleife
            break
        cur = naechster
        if len(block) < 1000:
            break
        if bloecke % 25 == 0:
            melden(f"    {symbol} {interval}: {len(kerzen)} Kerzen ...")
        time.sleep(0.2)          # hoeflich zu Binance
        if bloecke > BLOCK_GRENZE:
            melden(f"    ABBRUCH: {BLOCK_GRENZE} Bloecke erreicht - das ist "
                   f"das Netz gegen Endlosschleifen, die Daten sind "
                   f"UNVOLLSTAENDIG.")
            break

    # Doppelte entfernen (Blockgrenzen koennen ueberlappen) und sortieren
    nach_zeit = {k["t"]: k for k in kerzen}
    kerzen = [nach_zeit[t] for t in sorted(nach_zeit)]
    return kerzen


# Dateiname je Intervall.
#
# [06.09.2026] "1M" (Monat) und "1m" (Minute) unterscheiden sich bei
# Binance NUR durch Gross- und Kleinschreibung. Windows-Dateisysteme
# tun das nicht: BTCUSDT_1M.json und BTCUSDT_1m.json sind dieselbe
# Datei. Beim ersten Lauf hat der Minuten-Abruf die Monatskerzen
# stillschweigend ueberschrieben - aufgefallen nur, weil der Test die
# Anzahl UND das Startdatum geprueft hat: 43202 Kerzen ab 07.08.2026
# statt 109 Kerzen ab 2017. Eine reine Existenzpruefung haette nichts
# gemeldet, die Datei war ja da.
DATEI_NAME = {"1M": "1mon"}


def dateiname(interval):
    return DATEI_NAME.get(interval, interval)


def schreiben(symbol, interval, kerzen, verworfen=0):
    os.makedirs(ZIEL, exist_ok=True)
    p = os.path.join(ZIEL, f"{symbol}_{dateiname(interval)}.json")
    inhalt = {
        "symbol": symbol,
        "interval": interval,
        "anzahl": len(kerzen),
        # Wieviele unstimmige Balken beim Holen weggelassen wurden. Die
        # Zahl gehoert IN die Datei, nicht nur ins Fenster - sonst weiss
        # es morgen niemand mehr.
        "verworfen": verworfen,
        "geholt_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kerzen": kerzen,
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(inhalt, f, separators=(",", ":"))
    return p


def _zeit(sek):
    return datetime.fromtimestamp(sek, timezone.utc).strftime("%d.%m.%Y")


def frisch_genug(interval, kerzen, symbol="BTCUSDT"):
    """Reicht der geholte Verlauf bis (fast) jetzt? -> (ja/nein, Grund)

    WARUM DAS GEPRUEFT WIRD: Eine Datei mit 400.000 Kerzen sieht in
    jeder Uebersicht prima aus - auch dann, wenn die neueste davon aus
    dem Jahr 2018 stammt, weil der Lader vorher abgebrochen ist. Die
    ANZAHL sagt nichts darueber, ob das Richtige drinsteht. Genau
    dieser Unterschied hat am 06.09. die vertauschten Monats- und
    Minutenkerzen auffliegen lassen.
    """
    if not kerzen:
        return False, "keine Kerzen"
    alter_s = time.time() - kerzen[-1]["t"]
    # Fuenf Intervalle Spielraum, mindestens aber drei Minuten - in
    # duennen Sekunden gibt es nicht zu jeder Sekunde eine Kerze.
    #
    # Dazu die Marktpause: die Metallboerse hat Wochenende. Ohne diesen
    # Zuschlag haette der Holer am Montagmorgen jede Gold-Datei fuer
    # unvollstaendig erklaert - ein Fehlalarm, der die guten Daten
    # unbenutzt gelassen haette.
    pause = MAERKTE.get(symbol, {}).get("pause_tage", 0) * 86400
    erlaubt = max(5 * INTERVAL_MS[interval] / 1000, 180) + pause
    if alter_s <= erlaubt:
        return True, ""
    return False, (f"neueste Kerze vom {_zeit(kerzen[-1]['t'])}, das ist "
                   f"{_dauer(alter_s)} her - erlaubt waeren {_dauer(erlaubt)}")


def _dauer(sekunden):
    """Zeitspanne in einer Einheit, die man lesen kann.

    "0.0 Tage" ist keine Angabe, sondern eine verpasste Gelegenheit.
    """
    s = float(sekunden)
    if s < 90:
        return f"{s:.0f} Sekunden"
    if s < 5400:
        return f"{s / 60:.0f} Minuten"
    if s < 172800:
        return f"{s / 3600:.1f} Stunden"
    return f"{s / 86400:.1f} Tage"


def uebersicht_schreiben():
    """Schreibt daten/uebersicht.json - was tatsaechlich da ist.

    WARUM: Der Chart kann keinen Ordner auflisten. Ohne diese Datei
    muesste im HTML eine zweite Liste der Muenzen und Zeitraster
    stehen - und die waere schon beim naechsten Abruf falsch. Sie wird
    deshalb aus dem ERZEUGT, was wirklich im Ordner liegt, nicht aus
    dem, was geholt werden sollte.
    """
    if not os.path.isdir(ZIEL):
        return None
    rueck = {}
    for datei in sorted(os.listdir(ZIEL)):
        if not datei.endswith(".json") or datei == "uebersicht.json":
            continue
        if ".UNVOLLSTAENDIG." in datei:
            continue
        try:
            with open(os.path.join(ZIEL, datei), encoding="utf-8") as f:
                d = json.load(f)
            sym, tf, k = d["symbol"], d["interval"], d["kerzen"]
            if not k:
                continue
        except Exception:
            continue
        eintrag = rueck.setdefault(sym, {
            "name": MAERKTE.get(sym, {}).get("name", sym),
            "quelle": MAERKTE.get(sym, {}).get("quelle", "?"),
            "raster": {}})
        eintrag["raster"][tf] = {"anzahl": len(k), "von": k[0]["t"],
                                 "bis": k[-1]["t"],
                                 "verworfen": d.get("verworfen", 0)}
    p = os.path.join(ZIEL, "uebersicht.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "maerkte": rueck}, f, indent=1)
    return p


def pruefen():
    """Sieht jede Datei im Datenordner an: steckt das Raster drin, das
    ihr Name behauptet, und sind die Kerzen heil?

    Liest nur, schreibt nichts. Rueckgabe: 0 = alles in Ordnung.
    """
    print("=" * 64)
    print("CHARTLABOR - Datenordner pruefen")
    print("=" * 64)
    print(f"  {ZIEL}")
    print()
    if not os.path.isdir(ZIEL):
        print("  Es gibt noch keinen Datenordner.")
        return 1
    # Vom Dateinamen zurueck auf unser Raster - 1mon heisst bei uns 1M.
    zurueck = {v: k for k, v in DATEI_NAME.items()}
    beanstandet = 0
    for name in sorted(os.listdir(ZIEL)):
        if not name.endswith(".json") or name == "uebersicht.json":
            continue
        endung = name.rsplit("_", 1)[-1][:-5]
        tf = zurueck.get(endung, endung)
        soll = RASTER_SEKUNDEN.get(tf)
        if soll is None:
            print(f'  [--] {name:<26} unbekanntes Raster "{endung}"')
            continue
        try:
            with open(os.path.join(ZIEL, name), encoding="utf-8") as f:
                k = json.load(f)["kerzen"]
        except Exception as e:
            print(f"  [!!] {name:<26} nicht lesbar: {e}")
            beanstandet += 1
            continue
        if len(k) < 3:
            print(f"  [--] {name:<26} nur {len(k)} Kerzen")
            continue
        ist = abstand(k)
        kaputt = sum(1 for x in k if not kerze_heil(x))
        ok = raster_stimmt(k, soll) and kaputt == 0
        if not ok:
            beanstandet += 1
        print(f'  {"[ok]" if ok else "[!!]"} {name:<26} {len(k):>7} Kerzen  '
              f"Abstand {ist:>8}s  soll {soll:>8}s  kaputt {kaputt}")
    print()
    if beanstandet:
        print(f"  {beanstandet} Datei(en) beanstandet.")
        return 1
    print("  Alle Dateien in Ordnung.")
    return 0


def main():
    if "--pruefen" in sys.argv:
        return pruefen()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    alle = "--alle" in sys.argv

    symbole = ["BTCUSDT"]
    if alle:
        symbole = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    if args:
        symbole = [args[0].replace("/", "").upper()]
    rahmen = [args[1]] if len(args) > 1 else None

    print("=" * 64)
    print("CHARTLABOR - Kursverlauf holen")
    print("=" * 64)
    print(f"  Ziel: {ZIEL}")
    print()

    gesamt = 0
    fehler = []
    for sym in symbole:
        # Nicht jeder Markt hat jedes Zeitraster. Sekundenkerzen gibt es
        # bei Yahoo ueberhaupt nicht - der Knopf dafuer wird im Chart
        # ausgegraut, statt eine Datei zu suchen, die es nie geben wird.
        if rahmen is None:
            if MAERKTE.get(sym, {}).get("quelle") == "yahoo":
                # Kein 4h und kein 1s - die gibt es bei Yahoo nicht, und
                # zusammengerechnet wird nichts mehr (siehe oben).
                raster = ["1M", "1w", "1d", "1h", "15m", "1m"]
            else:
                raster = STANDARD
        else:
            raster = rahmen
        for tf in raster:
            try:
                k = laden(sym, tf)
                if not k:
                    fehler.append(f"{sym} {tf}: keine Kerzen")
                    print(f"  !! {sym:9} {tf:4}  keine Daten")
                    continue
                # Unvollstaendiges NIE ueber eine gute Datei schreiben.
                # Sonst tauscht ein abgebrochener Lauf brauchbare Kerzen
                # gegen kaputte, und niemand merkt es.
                ok, grund = frisch_genug(tf, k, sym)
                if not ok:
                    ersatz = os.path.join(
                        ZIEL, f"{sym}_{dateiname(tf)}.UNVOLLSTAENDIG.json")
                    with open(ersatz, "w", encoding="utf-8") as f:
                        json.dump({"symbol": sym, "interval": tf,
                                   "anzahl": len(k), "kerzen": k},
                                  f, separators=(",", ":"))
                    fehler.append(f"{sym} {tf}: unvollstaendig - {grund}")
                    print(f"  !! {sym:9} {tf:4}  UNVOLLSTAENDIG ({len(k)} Kerzen) "
                          f"- {grund}")
                    print(f"     Die vorhandene Datei bleibt unangetastet.")
                    print(f"     Das Geholte liegt in {os.path.basename(ersatz)}")
                    continue
                # ---- Unstimmige Balken raus, bevor irgendetwas geprueft
                #      oder geschrieben wird ----
                k, verworfen = saeubern(k)
                if not k:
                    fehler.append(f"{sym} {tf}: alle Kerzen unstimmig")
                    print(f"  !! {sym:9} {tf:4}  alle {verworfen} Kerzen unstimmig")
                    continue

                # ---- DAS TOR: enthaelt die Datei das Raster, das ihr
                #      Name behaupten wird? ----
                #
                # Auch fuer Binance, wo es bisher nie noetig war. Eine
                # Quelle, die still das Raster wechselt, faellt sonst nie
                # auf - und genau das ist bei Yahoo passiert.
                soll = RASTER_SEKUNDEN.get(tf)
                if soll and not raster_stimmt(k, soll):
                    grund2 = (f"Abstand {abstand(k)} s, erwartet ~{soll} s")
                    fehler.append(f"{sym} {tf}: falsches Raster - {grund2}")
                    print(f"  !! {sym:9} {tf:4}  FALSCHES RASTER - {grund2}")
                    print(f"     Nicht geschrieben. Die vorhandene Datei "
                          f"bleibt unangetastet.")
                    continue

                p = schreiben(sym, tf, k, verworfen)
                gesamt += len(k)
                mb = os.path.getsize(p) / 1048576
                nachsatz = (f"  [{verworfen} kaputte weggelassen]"
                            if verworfen else "")
                print(f"  OK {sym:9} {tf:4}  {len(k):>6} Kerzen  "
                      f"{_zeit(k[0]['t'])} bis {_zeit(k[-1]['t'])}  "
                      f"{mb:.1f} MB{nachsatz}")
            except Exception as e:
                fehler.append(f"{sym} {tf}: {type(e).__name__} {e}")
                print(f"  !! {sym:9} {tf:4}  FEHLER: {str(e)[:60]}")

    uebersicht_schreiben()
    print()
    print(f"  Zusammen {gesamt} Kerzen.")
    if fehler:
        print("  Nicht geklappt hat:")
        for f in fehler:
            print(f"    - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
