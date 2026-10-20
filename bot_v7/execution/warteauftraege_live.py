# -*- coding: utf-8 -*-
"""Warte-Auftraege (Limit-Orders) im ECHTBETRIEB - die fehlende Haelfte.

WOZU
----
`execution/warteauftraege.py` spielt Warte-Auftraege im Papierpfad nach
und steht dort ausdruecklich unter:

    "Nur der Papierpfad. Im Livebetrieb braucht ein Warte-Auftrag eine
     echte Order an der Boerse, keine nachgespielte - das ist ein
     anderer Bau und steht hier bewusst nicht drin."   (Zeile 96-99)

Das ist dieser andere Bau.

DER UNTERSCHIED ZUM PAPIERPFAD - und warum er das Ergebnis VERBESSERT
---------------------------------------------------------------------
Im Papierpfad prueft der BOT alle 12 Sekunden, ob der Kurs sein Limit
erreicht hat. Deshalb steht in warteauftraege.py, die gemessenen 73,3 %
Ausfuehrungsquote seien eine Obergrenze: ein Tief zwischen zwei Blicken
entgeht ihm.

Im Echtbetrieb haelt die BOERSE den Auftrag im Orderbuch und sieht jeden
einzelnen Handel. Der Grund fuer die Obergrenze entfaellt also - hier
wird die Beruehrungsquote tatsaechlich erreicht, nicht nur angenaehert.

WAS IM ECHTBETRIEB DAZUKOMMT - die drei Gefahren
-------------------------------------------------
1. TEILAUSFUEHRUNG. Eine Limit-Order kann zur Haelfte bedient werden.
   Der Papierpfad kennt nur ganz oder gar nicht. Wer das uebersieht,
   bucht eine Menge, die er nicht besitzt - und der Stop-Loss kann
   spaeter nicht verkaufen. Genau dieser Fehler stand am 15.09. schon
   einmal im Register (0,0042 gebucht gegen 0,0041895 vorhanden).

2. DAS WETTRENNEN BEIM ZURUECKNEHMEN. Zwischen "ich sehe, sie ist noch
   offen" und "nimm sie zurueck" liegen Millisekunden, in denen sie
   ausgefuehrt werden kann. Die Boerse meldet dann einen Fehler - und
   der Bot haelt eine Position, von der er nichts weiss. Deshalb wird
   nach JEDEM Ruecknahmeversuch nachgesehen, was wirklich passiert ist,
   statt der Fehlermeldung zu glauben.

3. GEBUNDENES GELD. Solange der Auftrag offen ist, haelt die Boerse den
   Betrag fest. Der Bot haelt ihn dagegen fuer verfuegbar und koennte
   ihn ein zweites Mal verplanen. Deshalb meldet `offene_summe_usd()`,
   wieviel gerade gebunden ist.

WAS HIER BEWUSST NICHT DRIN IST
-------------------------------
Kein Verkauf ueber Warte-Auftraege. Ein Stop-Loss, der als Limit-Order
im Orderbuch liegt, wird bei einem schnellen Rutsch NICHT bedient - der
Kurs springt darueber hinweg. Die Notbremse bleibt ein Sofort-Auftrag.
Gemessen ist ohnehin nur der Kauf (K_WARTE_PCT = Maker beim Kauf, Taker
beim Verkauf).

Reine Baustein-Datei: sie stellt, fragt und nimmt zurueck. Sie bucht
nichts und entscheidet nichts.
"""
import time

from core.logger import log

# Wie oft hoechstens nachgefragt wird, wenn die Boerse zickt.
_VERSUCHE = ((1, 0.0), (2, 1.0), (3, 2.5))


def _zahl(wert, ersatz=0.0):
    try:
        if wert is None:
            return ersatz
        return float(wert)
    except (TypeError, ValueError):
        return ersatz


def stellen(exchange, symbol, menge, limitpreis, kennung=""):
    """Legt einen Warte-Auftrag ins Orderbuch der Boerse.

    Rueckgabe: (order_id, fehler). Genau eines von beiden ist gesetzt.

    Der Parametername fuer die eigene Kennung ist boersenabhaengig -
    dieselbe Falle wie in engine.py:771. Bybit liest `orderLinkId`,
    Binance `newClientOrderId`. Wer den falschen sendet, bekommt keinen
    Fehler, sondern eine Order ohne Wiedererkennung.
    """
    params = {}
    if kennung:
        boerse = str(getattr(exchange, "id", "")).lower()
        k = str(kennung)[:36]              # Bybit: hoechstens 36 Zeichen
        if "bybit" in boerse:
            params["orderLinkId"] = k
        elif "binance" in boerse:
            params["newClientOrderId"] = k
        else:
            params["clientOrderId"] = k

    try:
        order = exchange.create_order(symbol, "limit", "buy",
                                      menge, limitpreis, params)
    except Exception as e:
        return "", f"{type(e).__name__}: {str(e)[:150]}"

    oid = str((order or {}).get("id") or "")
    if not oid:
        # Kein Fehler, aber auch keine Kennung: dann ist der Auftrag
        # moeglicherweise trotzdem im Buch. Das ist der gefaehrlichere
        # Fall, deshalb wird er als Fehler gemeldet, damit der Aufrufer
        # nachsieht statt weiterzumachen.
        return "", "Boerse lieferte keine Order-ID zurueck"
    log.info("WARTE-LIVE",
             f"{symbol}: Warte-Auftrag gestellt, Limit {limitpreis:.8f}, "
             f"Menge {menge:.8f}, ID {oid}")
    return oid, ""


def status(exchange, order_id, symbol):
    """Was ist aus dem Auftrag geworden?

    Rueckgabe: dict mit
        zustand   "offen" | "gefuellt" | "teilweise" | "weg" | "unklar"
        menge     tatsaechlich ausgefuehrte Menge
        preis     Durchschnittspreis der Ausfuehrung
        gebuehr   bezahlte Gebuehr, falls die Boerse sie nennt
        waehrung  in welcher Muenze die Gebuehr abging

    "unklar" heisst: die Boerse war nicht erreichbar. Das ist NICHT
    dasselbe wie "weg" - wer beides gleich behandelt, verliert
    irgendwann eine Position aus den Augen.
    """
    letzte = ""
    for _versuch, pause in _VERSUCHE:
        if pause:
            time.sleep(pause)
        try:
            o = exchange.fetch_order(order_id, symbol) or {}
        except Exception as e:
            letzte = f"{type(e).__name__}: {str(e)[:120]}"
            continue

        roh = str(o.get("status") or "").lower()
        gefuellt = _zahl(o.get("filled"))
        offen = _zahl(o.get("remaining"))
        gebuehr = (o.get("fee") or {})
        ergebnis = {
            "menge": gefuellt,
            "preis": _zahl(o.get("average") or o.get("price")),
            "gebuehr": _zahl(gebuehr.get("cost")),
            "waehrung": str(gebuehr.get("currency") or ""),
            "roh": roh,
        }
        if roh in ("closed", "filled") and gefuellt > 0:
            ergebnis["zustand"] = "gefuellt"
        elif roh in ("canceled", "cancelled", "expired", "rejected"):
            # Storniert, aber vorher teilweise bedient - der haeufigste
            # Weg, wie eine unbemerkte Teilmenge entsteht.
            ergebnis["zustand"] = "teilweise" if gefuellt > 0 else "weg"
        elif gefuellt > 0 and offen > 0:
            ergebnis["zustand"] = "teilweise"
        elif roh == "open" or offen > 0:
            ergebnis["zustand"] = "offen"
        else:
            ergebnis["zustand"] = "unklar"
        return ergebnis

    log.warn("WARTE-LIVE",
             f"{symbol}: Status von {order_id} nicht abfragbar ({letzte}) - "
             f"Auftrag gilt als UNKLAR, nicht als weg")
    return {"zustand": "unklar", "menge": 0.0, "preis": 0.0,
            "gebuehr": 0.0, "waehrung": "", "roh": ""}


def zuruecknehmen(exchange, order_id, symbol):
    """Nimmt den Auftrag zurueck - und sieht nach, was wirklich geschah.

    DAS WETTRENNEN
    --------------
    Zwischen der Entscheidung "zuruecknehmen" und dem Eintreffen des
    Befehls an der Boerse koennen Millisekunden liegen, in denen der
    Auftrag ausgefuehrt wird. Die Boerse meldet dann einen Fehler
    ("order not found", "already filled"). Wer daraus schliesst, es sei
    nichts passiert, haelt eine Position, von der er nichts weiss - und
    ohne Stop-Loss.

    Deshalb wird nach jedem Versuch der STATUS abgefragt, egal ob der
    Befehl gelang oder nicht. Der Status entscheidet, nicht die
    Fehlermeldung.
    """
    fehler = ""
    try:
        exchange.cancel_order(order_id, symbol)
    except Exception as e:
        fehler = f"{type(e).__name__}: {str(e)[:120]}"

    nachher = status(exchange, order_id, symbol)

    if nachher["zustand"] == "gefuellt":
        log.warn("WARTE-LIVE",
                 f"{symbol}: Ruecknahme kam zu spaet - der Auftrag wurde "
                 f"ausgefuehrt ({nachher['menge']:.8f} zu "
                 f"{nachher['preis']:.8f}). Die Position wird gebucht.")
    elif nachher["zustand"] == "teilweise":
        log.warn("WARTE-LIVE",
                 f"{symbol}: Ruecknahme traf einen teilweise bedienten "
                 f"Auftrag - {nachher['menge']:.8f} wurden gekauft und "
                 f"werden gebucht.")
    elif nachher["zustand"] == "unklar":
        log.error("WARTE-LIVE",
                  f"{symbol}: Auftrag {order_id} nach Ruecknahmeversuch "
                  f"NICHT einsehbar ({fehler or 'kein Fehler gemeldet'}). "
                  f"Er wird NICHT als erledigt verbucht - beim naechsten "
                  f"Takt wird erneut nachgesehen.")
    else:
        log.info("WARTE-LIVE",
                 f"{symbol}: Warte-Auftrag {order_id} zurueckgenommen, "
                 f"nichts ausgefuehrt")
    return nachher


def offene_summe_usd(auftraege):
    """Wieviel Geld haelt die Boerse gerade fest?

    Der Bot fuehrt seinen freien Betrag selbst; ein offener Warte-Auftrag
    bindet Geld, das dort noch als verfuegbar steht. Ohne diese Zahl
    koennte derselbe Betrag ein zweites Mal verplant werden.
    """
    summe = 0.0
    for a in (auftraege or []):
        summe += _zahl(a.get("betrag_usd"))
    return summe
