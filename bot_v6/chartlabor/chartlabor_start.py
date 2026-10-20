# -*- coding: utf-8 -*-
"""
chartlabor_start.py - oeffnet das Chartlabor im Browser
========================================================
WARUM EIN SERVER UND NICHT EINFACH DIE HTML-DATEI ANKLICKEN

Die Seite laedt ihre Kerzen aus daten/*.json nach. Oeffnet man die
HTML-Datei direkt per Doppelklick, laeuft sie unter file:// - und
Browser verbieten dort aus Sicherheitsgruenden das Nachladen von
Dateien. Die Seite bliebe leer, ohne verstaendliche Fehlermeldung.

Deshalb dieser winzige Server. Er liefert NUR diesen einen Ordner aus,
hoert nur auf 127.0.0.1 (also nur dieser Rechner, nicht das Netz) und
schreibt nichts.

    DER PORT IST BEWUSST NICHT 5050.

Auf 5050 sitzt der Bot. Zwei Programme auf demselben Port - genau das
war am 03.09.2026 die Ursache dafuer, dass fuenf Stunden lang zwei
getrennte Datenbestaende entstanden. Dieser Server prueft vorher, ob
sein Port frei ist, und weicht aus statt sich dazwischenzudraengen.

Beenden: dieses Fenster schliessen oder Strg+C.
"""
import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser

HIER = os.path.dirname(os.path.abspath(__file__))
PORT_WUNSCH = 8777
VERBOTEN = {5050}          # gehoert dem Bot, wird nie angefasst


def port_frei(p):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", p)) != 0


def _ist_unser_server(p):
    """Prueft, ob auf dem Port wirklich DAS CHARTLABOR sitzt.

    Nur "Port belegt" genuegt nicht - dort koennte irgendein anderes
    Programm horchen. Dann waere es falsch, den Browser dorthin zu
    schicken. Deshalb wird eine Seite abgerufen und hineingeschaut.
    """
    try:
        import urllib.request
        with urllib.request.urlopen(
                f"http://127.0.0.1:{p}/chartlabor.html", timeout=2) as r:
            return b"Chartlabor" in r.read(4000)
    except Exception:
        return False


def port_finden():
    for p in range(PORT_WUNSCH, PORT_WUNSCH + 40):
        if p in VERBOTEN:
            continue
        if port_frei(p):
            return p
    return None


# ===================================================================
# WARUM MEHRSPURIG (ThreadingHTTPServer) UND NICHT TCPServer
# -------------------------------------------------------------------
# [22.09.2026] socketserver.TCPServer bearbeitet EINE Verbindung nach
# der anderen. Wartende Verbindungen stehen in einer Schlange, die
# genau FUENF fasst (request_queue_size). Ist die voll, weist das
# Betriebssystem neue Verbindungen ab - der Browser zeigt dann nur ein
# ewiges Laderad, ohne Fehlermeldung.
#
# GEMESSEN an Svens laufendem Fenster: Prozess lebte (PID 7296, ein
# Thread), Port 8777 hatte 4x CloseWait und 1x Established, und jede
# neue Anfrage kam mit WinError 10061 zurueck ("Verbindung
# verweigert"). Der Chart war damit tot, ohne dass irgendwo etwas
# stand.
#
# Ein Browser oeffnet fuer eine Seite mehrere Verbindungen gleichzeitig
# (Seite, dann die Kursdatei), und liegengebliebene raeumt er erst
# spaeter ab. Fuenf sind schnell voll.
#
# ThreadingHTTPServer gibt jeder Verbindung einen eigenen Faden.
# daemon_threads=True sorgt dafuer, dass Strg+C das Fenster trotzdem
# sofort schliesst und keine Faeden haengenbleiben.
class MehrspurigerServer(socketserver.ThreadingTCPServer):
    daemon_threads = True          # Strg+C schliesst sofort
    allow_reuse_address = True     # Port nach einem Neustart gleich wieder frei


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HIER, **kw)

    def log_message(self, *a):
        pass                      # kein Geschnatter im Fenster


def main():
    daten = os.path.join(HIER, "daten")
    if not os.path.isdir(daten) or not os.listdir(daten):
        print()
        print("  Es liegen noch keine Kerzen bereit.")
        print("  Erst KURSVERLAUF_HOLEN.bat doppelklicken.")
        print()
        input("  Mit Eingabetaste schliessen ... ")
        return 1

    # Laeuft schon einer? Dann NICHT einen zweiten starten, sondern den
    # vorhandenen benutzen.
    #
    # WARUM DAS HIER STEHT: Am 03.09.2026 liefen zwei Boetse gleichzeitig,
    # weil jemand ein zweites Mal gestartet hat. Fuenf Stunden lang
    # entstanden zwei getrennte Datenbestaende. Hier geht es nur um
    # Kerzenbilder, nicht um Geld - aber zwei Server auf zwei Ports sind
    # zwei Adressen, und dann zeichnet man seine Linien in das eine
    # Fenster und sucht sie im anderen.
    seite = "lernpfad.html" if "--lernpfad" in sys.argv else "chartlabor.html"
    if not port_frei(PORT_WUNSCH) and _ist_unser_server(PORT_WUNSCH):
        adresse = f"http://127.0.0.1:{PORT_WUNSCH}/{seite}"
        print()
        print("  Es laeuft bereits ein Chartlabor auf Port "
              f"{PORT_WUNSCH} - es wird KEIN zweites gestartet.")
        print(f"  Geoeffnet wird: {adresse}")
        webbrowser.open(adresse)
        print()
        print("  Dieses Fenster kann zu.")
        return 0

    port = port_finden()
    if port is None:
        print("  Kein freier Port zwischen 8777 und 8816 gefunden.")
        input("  Mit Eingabetaste schliessen ... ")
        return 1

    # Beide Startdateien benutzen denselben Server, nur eine andere
    # Startseite (seite steht oben schon fest).
    adresse = f"http://127.0.0.1:{port}/{seite}"
    dateien = sorted(f for f in os.listdir(daten) if f.endswith(".json"))

    print("=" * 62)
    print("LERNPFAD" if seite == "lernpfad.html" else "CHARTLABOR")
    print("=" * 62)
    print(f"  Adresse : {adresse}")
    print(f"  Ordner  : {HIER}")
    print(f"  Daten   : {len(dateien)} Datei(en)")
    for d in dateien:
        mb = os.path.getsize(os.path.join(daten, d)) / 1048576
        print(f"            {d:24} {mb:5.1f} MB")
    print()
    print("  Der Browser oeffnet sich gleich.")
    print("  DIESES FENSTER OFFEN LASSEN - es haelt den Server.")
    print("  Beenden mit Strg+C oder Fenster schliessen.")
    print("=" * 62)

    threading.Timer(1.0, lambda: webbrowser.open(adresse)).start()

    try:
        with MehrspurigerServer(("127.0.0.1", port), Handler) as srv:
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
