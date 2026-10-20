# -*- coding: utf-8 -*-
"""core/startsperre.py - verhindert, dass zwei Bots gleichzeitig laufen.

WOZU (Befund 93)
----------------
`app.py` erzeugte im `__main__`-Block sofort `TradingImperiumV6()`, ohne
nachzusehen, ob schon einer laeuft. Zwei Sicherungen, die man dafuer
haelt, greifen nicht:

  - Die Sperrdatei in `core/hintergrund.py` schuetzt nur die
    Hintergrundjobs, nicht den Bot selbst.
  - Die Portbelegung bremst nicht: mit `netstat` nachgemessen hoert der
    Bot-Prozess **keinen einzigen Port** ab. Damit laeuft auch die Regel
    in CLAUDE.md ins Leere, die verlangt, vor jedem Neustart zu pruefen,
    wer Port 5050 haelt - es haelt ihn niemand.

Am 01.09.2026 hing die Handelsschleife dadurch 37 Minuten.

DER GRUNDSATZ DIESER DATEI: IM ZWEIFEL STARTEN LASSEN
------------------------------------------------------
Ein Bot, der faelschlich nicht startet, ist schlimmer als zwei, die
kurz nebeneinander laufen - beim zweiten merkt man es, beim ersten
steht der Handel still, bis jemand hinsieht. Deshalb sperrt diese Datei
nur, wenn sie sich SICHER ist, und laesst in jedem anderen Fall laufen:

  Sperrdatei fehlt                    -> starten
  Sperrdatei unlesbar oder kaputt     -> starten
  Prozessnummer lebt nicht mehr       -> starten (das ist der Absturzfall)
  Prozess lebt, ist aber ein anderer  -> starten (Nummer neu vergeben)
  psutil fehlt                        -> starten, aber laut sagen warum
  Prozess lebt UND ist ein app.py     -> SPERREN

Der vorletzte Punkt ist der wichtigste: Ohne die Pruefung, ob die
eingetragene Nummer noch lebt, wuerde ein einziger Absturz den naechsten
Start dauerhaft aussperren. Genau davor warnt OFFEN.md Punkt 24.

NOTAUSGANG
----------
    python app.py --trotzdem-starten

Umgeht die Sperre. Gedacht fuer den Fall, dass sie sich doch einmal irrt -
dann soll niemand im Quelltext suchen muessen.

    python core/startsperre.py --pruefen    zeigt den Stand, sperrt nichts
"""
import io
import json
import os
import sys
import time

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPERRDATEI = os.path.join(HIER, "data_store", "bot_laeuft.json")


def _prozess_lebt(pid):
    """(lebt, ist_ein_bot, beschreibung).

    Gibt bei jeder Unsicherheit (False, False, grund) zurueck - der
    Aufrufer laesst dann starten.
    """
    try:
        import psutil
    except ImportError:
        return False, False, "psutil fehlt - kann nicht nachsehen"
    try:
        pr = psutil.Process(int(pid))
    except Exception:
        return False, False, "Prozess %s existiert nicht mehr" % pid
    try:
        if not pr.is_running():
            return False, False, "Prozess %s laeuft nicht mehr" % pid
        # Zombie zaehlt nicht als lebend
        if pr.status() == getattr(psutil, "STATUS_ZOMBIE", "zombie"):
            return False, False, "Prozess %s ist ein Zombie" % pid
        zeile = " ".join(pr.cmdline() or [])
        ist_bot = "app.py" in zeile and "python" in zeile.lower()
        return True, ist_bot, zeile[:120]
    except Exception as e:
        # Zugriff verweigert und aehnliches: NICHT sperren.
        return False, False, "Prozess %s nicht lesbar (%s)" % (pid, str(e)[:40])


def stand():
    """Was steht in der Sperrdatei, und lebt das noch?"""
    if not os.path.exists(SPERRDATEI):
        return {"da": False, "grund": "keine Sperrdatei"}
    try:
        with io.open(SPERRDATEI, encoding="utf-8") as f:
            d = json.load(f)
        pid = int(d.get("pid"))
    except Exception as e:
        return {"da": False, "grund": "Sperrdatei unlesbar (%s)" % str(e)[:40]}
    lebt, ist_bot, text = _prozess_lebt(pid)
    return {"da": True, "pid": pid, "lebt": lebt, "ist_bot": ist_bot,
            "text": text, "seit": d.get("gestartet"), "grund": ""}


def pruefen_und_eintragen(argumente=None):
    """Vor dem Start aufrufen. Gibt True zurueck, wenn gestartet werden darf.

    Traegt bei True die eigene Prozessnummer ein.
    """
    argumente = argumente if argumente is not None else sys.argv
    notausgang = "--trotzdem-starten" in argumente

    s = stand()
    if s["da"] and s.get("lebt") and s.get("ist_bot") and not notausgang:
        print("")
        print("!" * 70)
        print("!!  ES LAEUFT SCHON EIN BOT - dieser Start wird abgebrochen.")
        print("!" * 70)
        print("!!  Prozessnummer : %s" % s["pid"])
        print("!!  gestartet     : %s" % (s.get("seit") or "unbekannt"))
        print("!!  Kommandozeile : %s" % s.get("text", ""))
        print("!!")
        print("!!  WARUM DAS WICHTIG IST (Befund 93): Zwei Boetten schreiben")
        print("!!  in dieselben Dateien. Am 01.09.2026 hing die Handels-")
        print("!!  schleife dadurch 37 Minuten. Die Portbelegung bremst")
        print("!!  nicht - der Bot hoert auf keinem Port.")
        print("!!")
        print("!!  Wenn Sie sicher sind, dass der andere weg ist:")
        print("!!      python app.py --trotzdem-starten")
        print("!" * 70)
        print("")
        return False

    if s["da"] and s.get("lebt") and s.get("ist_bot") and notausgang:
        print("[STARTSPERRE] Es laeuft schon einer (PID %s) - --trotzdem-"
              "starten war gesetzt, also weiter." % s["pid"])
    elif s["da"] and not s.get("lebt"):
        # Der Absturzfall. Ohne diese Zeile bliebe die Sperre fuer immer.
        print("[STARTSPERRE] Alte Sperrdatei von PID %s: %s. Wird ersetzt."
              % (s.get("pid"), s.get("text", "")))
    elif s["da"] and s.get("lebt") and not s.get("ist_bot"):
        print("[STARTSPERRE] PID %s lebt, ist aber kein Bot (%s). "
              "Nummer neu vergeben - Sperre gilt nicht."
              % (s.get("pid"), s.get("text", "")[:60]))

    eintragen()
    return True


def eintragen():
    """Schreibt die eigene Prozessnummer in die Sperrdatei."""
    try:
        ordner = os.path.dirname(SPERRDATEI)
        if not os.path.isdir(ordner):
            os.makedirs(ordner)
        with io.open(SPERRDATEI, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(),
                       "gestartet": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "kommandozeile": " ".join(sys.argv)[:200]},
                      f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        # Kein stilles Scheitern - aber auch kein Grund, den Start zu
        # verhindern. Ohne Sperrdatei ist der Zustand wie vor Befund 93.
        print("[STARTSPERRE] Konnte die Sperrdatei nicht schreiben: %s"
              % str(e)[:80])
        return False


def freigeben():
    """Beim geordneten Beenden aufrufen. Fehlt der Aufruf (Absturz), faengt
    die Lebendpruefung beim naechsten Start den Fall ab."""
    try:
        if os.path.exists(SPERRDATEI):
            with io.open(SPERRDATEI, encoding="utf-8") as f:
                if int(json.load(f).get("pid")) != os.getpid():
                    return False        # nicht die eigene - stehen lassen
            os.remove(SPERRDATEI)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    s = stand()
    print("=" * 68)
    print("  STARTSPERRE - Stand (Befund 93)")
    print("=" * 68)
    print()
    print("  Sperrdatei: %s" % SPERRDATEI)
    if not s["da"]:
        print("  Zustand   : frei (%s)" % s["grund"])
        print()
        print("  Ein Start waere erlaubt.")
    else:
        print("  Eingetragen: PID %s, gestartet %s"
              % (s["pid"], s.get("seit") or "?"))
        print("  lebt       : %s" % s.get("lebt"))
        print("  ist ein Bot: %s" % s.get("ist_bot"))
        print("  Kommandozeile: %s" % s.get("text", ""))
        print()
        if s.get("lebt") and s.get("ist_bot"):
            print("  Ein zweiter Start wuerde ABGEBROCHEN.")
            print("  Notausgang: python app.py --trotzdem-starten")
        else:
            print("  Ein Start waere erlaubt - die Sperre greift nur bei")
            print("  einem lebenden Bot-Prozess.")
    print()
