# -*- coding: utf-8 -*-
"""
chartlabor_py_bauen.py - baut die Einzeldatei CHARTLABOR.py auf den Desktop
===========================================================================
[07.09.2026, Wunsch von Sven: "erstell mir das bitte zusaetzlich als py
datei auf meinem desktop"]

WAS DAS IST

  Eine einzige Python-Datei, die das ganze Chartlabor enthaelt - die
  Chartseite und den Lernpfad stecken als Text darin. Sie laeuft auch
  dann noch, wenn der Projektordner verschoben oder geloescht wird.

WARUM SIE ERZEUGT WIRD UND NICHT VON HAND GESCHRIEBEN

  Zwei Kopien derselben Seite sind zwei Wahrheiten. Genau daran hat
  dieses Projekt schon zweimal verloren: das Messfenster-Datum stand in
  zwei Dateien (Befund 90), und die Python-Suche stand in fuenf
  (_python_finden.bat). Beide sind auseinandergelaufen, ohne dass es
  jemandem auffiel.

  Deshalb gilt hier:

      chartlabor/chartlabor.html  ist die Quelle.
      CHARTLABOR.py               ist ein Abzug davon.

  Wer die Seite aendert, aendert sie in der HTML-Datei und laesst
  danach dieses Skript laufen. Von Hand in der .py zu aendern ist
  verlorene Arbeit - der naechste Bau ueberschreibt es.

WAS DIE ERZEUGTE DATEI DAGEGEN TUT, WENN ES DOCH JEMAND VERGISST

  Sie merkt es selbst. Beim Start sucht sie die Vorlage und vergleicht
  die Pruefsumme. Weichen sie ab, sagt sie das laut UND zeigt die
  Vorlage statt ihrer eigenen, veralteten Kopie. So sieht man nie einen
  alten Chart, ohne es zu erfahren.

STARTEN:  python chartlabor_py_bauen.py
          (oder CHARTLABOR_NEU_BAUEN.bat doppelklicken)
"""
import base64
import hashlib
import io
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE_CHART = os.path.join(HIER, "chartlabor.html")
QUELLE_LERN = os.path.join(HIER, "lernpfad.html")


def desktop_finden():
    """Der Desktop dieses Benutzers.

    Bewusst nicht fest verdrahtet: der Benutzername enthaelt auf diesem
    Rechner ein Leerzeichen, und OneDrive hat den Desktop schon einmal
    verschoben. Erst die Registrierung fragen, dann der uebliche Ort.
    """
    if sys.platform == "win32":
        try:
            import winreg
            schluessel = (r"Software\Microsoft\Windows\CurrentVersion"
                          r"\Explorer\User Shell Folders")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, schluessel) as k:
                wert, _ = winreg.QueryValueEx(k, "Desktop")
            wert = os.path.expandvars(wert)
            if os.path.isdir(wert):
                return wert
        except Exception:
            pass
    heim = os.path.expanduser("~")
    for name in ("Desktop", "Schreibtisch"):
        p = os.path.join(heim, name)
        if os.path.isdir(p):
            return p
    return heim


def blob(daten, breite=76):
    """Bytes als base64, in Zeilen umgebrochen.

    WARUM BASE64 UND KEIN LANGER TEXT IN ANFUEHRUNGSZEICHEN: Die
    Chartseite enthaelt jede Sorte Anfuehrungszeichen, Schraegstriche
    und in JavaScript-Vorlagen ein \\n, das ein ECHTES \\n bleiben muss.
    In einen Python-Text eingebettet wuerde daraus stillschweigend ein
    Zeilenumbruch - die Seite waere kaputt, ohne Fehlermeldung. base64
    kann das nicht passieren; dafuer prueft die erzeugte Datei ihre
    Pruefsumme, damit ein Uebertragungsfehler auffaellt.
    """
    b = base64.b64encode(daten).decode("ascii")
    return "\n".join(b[i:i + breite] for i in range(0, len(b), breite))


VORLAGE = r'''# -*- coding: utf-8 -*-
r"""
CHARTLABOR.py - das ganze Chartlabor in einer Datei
===================================================
ERZEUGT AM @@GEBAUT@@ von chartlabor/chartlabor_py_bauen.py

    !!  DIESE DATEI NICHT VON HAND AENDERN  !!

    Die Quelle ist  @@QUELLE@@
    Wer hier etwas aendert, verliert es beim naechsten Bau.
    Nach jeder Aenderung an der HTML-Datei:
        python chartlabor_py_bauen.py

WAS SIE TUT

  Sie startet einen winzigen Server auf 127.0.0.1 (nur dieser Rechner)
  und oeffnet den Chart im Browser. Die Chartseite und der Lernpfad
  stecken als Text in dieser Datei; die Kerzen kommen aus dem Ordner
  daten/ des Projekts, der dafuer gesucht wird - 9 MB Kurse gehoeren
  nicht in eine Programmdatei.

DREI DINGE, DIE SIE ABSICHTLICH SO MACHT

  1. PORT 8777, NIEMALS 5050. Auf 5050 sitzt der Bot. Zwei Programme
     auf einem Port waren am 03.09.2026 die Ursache dafuer, dass fuenf
     Stunden lang zwei getrennte Datenbestaende entstanden.

  2. LAEUFT SCHON EIN CHARTLABOR AUF 8777, wird KEIN zweites
     gestartet - der Browser wird nur dorthin geschickt. Grund: die
     Zeichnungen liegen im Browser-Speicher, und der haengt an der
     Adresse. Zwei Adressen waeren zwei getrennte Zeichnungssaetze -
     man malt in das eine Fenster und sucht es im anderen.

  3. SIE PRUEFT SICH SELBST - BEI JEDEM ABRUF. Findet sie die Vorlage
     und weicht deren Pruefsumme ab, ist diese Datei veraltet. Dann
     sagt sie das laut und zeigt die VORLAGE statt ihrer eigenen
     Kopie. Ein F5 im Browser genuegt also, um eine Aenderung an der
     Vorlage zu sehen.

     [22.09.2026 nachgebessert] Vorher geschah das nur BEIM START. Wer
     die Vorlage aenderte, waehrend dieses Fenster lief, bekam weiter
     die alte Seite, ohne jeden Hinweis - nachgemessen: 2219 Zeilen
     ausgeliefert, 2322 lagen auf der Platte.

BEENDEN: dieses Fenster schliessen oder Strg+C.
PRUEFEN: python CHARTLABOR.py --selbsttest   (startet keinen Browser)
"""
import base64
import hashlib
import http.server
import os
import posixpath
import re
import socket
import socketserver
import sys
import threading
import webbrowser

HIER = os.path.dirname(os.path.abspath(__file__))

# Wo die Vorlage beim Bauen lag. Wird geprueft, nicht geglaubt.
VORLAGE_ORDNER = r"@@QUELLORDNER@@"
GEBAUT_AM = "@@GEBAUT@@"
SHA_CHART = "@@SHA_CHART@@"
SHA_LERN = "@@SHA_LERN@@"

PORT_WUNSCH = 8777
VERBOTEN = {5050}          # gehoert dem Bot, wird nie angefasst
PORT_PRUEF = 8900          # nur fuer --selbsttest, stoert nichts


# ===================================================================
# Die eingebauten Seiten
# ===================================================================
def _entpacken(text, sha_soll, name):
    roh = base64.b64decode("".join(text.split()))
    sha_ist = hashlib.sha256(roh).hexdigest()
    if sha_ist != sha_soll:
        raise SystemExit(
            f"  ABBRUCH: die eingebaute {name} ist beschaedigt.\n"
            f"  erwartet {sha_soll[:16]}..., vorhanden {sha_ist[:16]}...\n"
            f"  Neu bauen mit: python chartlabor_py_bauen.py")
    return roh


def seite_chart():
    return _entpacken(SEITE_CHART_B64, SHA_CHART, "Chartseite")


def seite_lern():
    return _entpacken(SEITE_LERN_B64, SHA_LERN, "Lernpfadseite")


# ===================================================================
# Vorlage und Kerzen suchen
# ===================================================================
def vorlagen_ordner():
    """Der chartlabor-Ordner des Projekts - oder None.

    Erst dort nachsehen, wo er beim Bauen lag. Ist er weg (Ordner
    verschoben, Rechner gewechselt), unter dem Desktop danach suchen.
    """
    kandidaten = [VORLAGE_ORDNER, os.path.join(HIER, "chartlabor"), HIER]
    heim = os.path.expanduser("~")
    for stamm in (os.path.join(heim, "Desktop"), heim):
        try:
            for eintrag in sorted(os.listdir(stamm)):
                if eintrag.lower().startswith("trading_imperium"):
                    kandidaten.append(os.path.join(stamm, eintrag, "chartlabor"))
        except OSError:
            pass
    for k in kandidaten:
        if k and os.path.isfile(os.path.join(k, "chartlabor.html")):
            return k
    return None


def daten_ordner():
    """Der Ordner mit den Kerzen - oder None."""
    ordner = vorlagen_ordner()
    kandidaten = [os.path.join(HIER, "daten")]
    if ordner:
        kandidaten.insert(0, os.path.join(ordner, "daten"))
    for k in kandidaten:
        if os.path.isdir(k) and any(f.endswith(".json") for f in os.listdir(k)):
            return k
    return None


_ORDNER_GEMERKT = None
_ZULETZT_GEMELDET = None


def seite_jetzt():
    """Die Chartseite, wie sie GERADE gilt. Rueckgabe: (Bytes, veraltet?)

    [22.09.2026] WARUM DAS BEI JEDEM ABRUF PASSIERT UND NICHT NUR BEIM
    START: Genau hier war eine Luecke. Die Seite wurde EINMAL beim
    Starten eingelesen; wer die Vorlage danach aenderte, waehrend
    dieses Programm lief, bekam weiter die alte Seite - lautlos. Am
    22.09. lieferte ein seit dem Vortag laufendes CHARTLABOR.py eine
    Seite mit 2219 Zeilen, waehrend auf der Platte 2322 lagen.

    Die Zusicherung von 07.09. ("sie merkt es selbst") galt also nur
    fuer den Augenblick des Startens. Eine Zusicherung mit einem
    unausgesprochenen "solange du nichts aenderst" ist keine.

    Das kostet einen Dateizugriff je Seitenabruf - etwa 90 KB, einmal
    pro F5. Das ist nichts gegen einen Chart, der still veraltet.
    """
    global _ORDNER_GEMERKT, _ZULETZT_GEMELDET
    ordner = _ORDNER_GEMERKT or vorlagen_ordner()
    if ordner:
        _ORDNER_GEMERKT = ordner
        try:
            with open(os.path.join(ordner, "chartlabor.html"), "rb") as f:
                roh = f.read()
            sha = hashlib.sha256(roh).hexdigest()
            if sha != SHA_CHART:
                # Nur beim WECHSEL etwas sagen, nicht bei jedem F5.
                if _ZULETZT_GEMELDET != sha:
                    _ZULETZT_GEMELDET = sha
                    print()
                    print("  [Hinweis] Die Vorlage hat sich geaendert - es wird")
                    print("            jetzt SIE gezeigt, nicht die eingebaute")
                    print("            Kopie. Neu bauen mit:")
                    print("                python chartlabor_py_bauen.py")
                    print()
                return roh, True
            _ZULETZT_GEMELDET = None
            return roh, False
        except OSError:
            pass
    return seite_chart(), False


def lernpfad_jetzt():
    """Dasselbe fuer die Lernpfadseite."""
    ordner = _ORDNER_GEMERKT or vorlagen_ordner()
    if ordner:
        try:
            with open(os.path.join(ordner, "lernpfad.html"), "rb") as f:
                return f.read()
        except OSError:
            pass
    return seite_lern()


def vorlagen_stand():
    """Vergleicht die eingebaute Kopie mit der Vorlage.

    Rueckgabe: ("gleich"|"abweichend"|"keine Vorlage", Ordner, Seitenbytes)
    Bei Abweichung kommen die Bytes DER VORLAGE zurueck - sie ist die
    Quelle, diese Datei nur ein Abzug.
    """
    ordner = vorlagen_ordner()
    if not ordner:
        return "keine Vorlage", None, seite_chart()
    try:
        with open(os.path.join(ordner, "chartlabor.html"), "rb") as f:
            roh = f.read()
    except OSError:
        return "keine Vorlage", None, seite_chart()
    if hashlib.sha256(roh).hexdigest() == SHA_CHART:
        return "gleich", ordner, seite_chart()
    return "abweichend", ordner, roh


# ===================================================================
# Server
# ===================================================================
SICHERER_NAME = re.compile(r"^[A-Za-z0-9_.\-]+\.json$")


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


def handler_bauen(chart_bytes, lern_bytes, daten, frisch=True):
    """frisch=False nimmt die uebergebenen Bytes fest - nur fuer den
    Selbsttest, der genau die eingebaute Kopie pruefen will."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass                      # kein Geschnatter im Fenster

        def _sende(self, roh, typ):
            self.send_response(200)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(roh)))
            # Nichts zwischenspeichern - sonst zeigt der Browser nach
            # einem Neubau weiter die alte Seite.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(roh)

        def _fehler(self, code, text):
            roh = text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(roh)))
            self.end_headers()
            self.wfile.write(roh)

        def do_GET(self):
            pfad = posixpath.normpath(self.path.split("?")[0])
            if pfad in ("/", "/index.html", "/chartlabor.html"):
                # Bei JEDEM Abruf nachsehen, ob die Vorlage neuer ist.
                # Ein F5 genuegt dann, um eine Aenderung zu sehen -
                # dieses Fenster muss nicht neu gestartet werden.
                roh = seite_jetzt()[0] if frisch else chart_bytes
                return self._sende(roh, "text/html; charset=utf-8")
            if pfad == "/lernpfad.html":
                roh = lernpfad_jetzt() if frisch else lern_bytes
                return self._sende(roh, "text/html; charset=utf-8")
            if pfad.startswith("/daten/"):
                name = pfad[len("/daten/"):]
                # Nur schlichte Dateinamen. Kein "..", keine Unterordner -
                # sonst kann eine Adresse aus dem Ordner herausklettern.
                if not SICHERER_NAME.match(name):
                    return self._fehler(400, "unzulaessiger Name")
                if not daten:
                    return self._fehler(
                        503, "Der Ordner mit den Kerzen wurde nicht gefunden.")
                voll = os.path.join(daten, name)
                if not os.path.isfile(voll):
                    return self._fehler(404, "Datei nicht da: " + name)
                try:
                    with open(voll, "rb") as f:
                        return self._sende(f.read(), "application/json")
                except OSError as e:
                    return self._fehler(500, str(e))
            return self._fehler(404, "gibt es hier nicht: " + pfad)

    return Handler


def port_frei(p):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", p)) != 0


def ist_unser_chartlabor(p):
    """Sitzt auf dem Port wirklich EIN CHARTLABOR?

    "Port belegt" genuegt nicht - dort koennte irgendein Programm
    horchen, und dann waere es falsch, den Browser hinzuschicken.
    """
    try:
        import urllib.request
        with urllib.request.urlopen(
                f"http://127.0.0.1:{p}/chartlabor.html", timeout=2) as r:
            return b"Chartlabor" in r.read(4000)
    except Exception:
        return False


def port_finden(ab=PORT_WUNSCH, bis=None):
    bis = bis if bis is not None else ab + 40
    for p in range(ab, bis):
        if p in VERBOTEN:
            continue
        if port_frei(p):
            return p
    return None


# ===================================================================
# Selbsttest - prueft, ohne etwas zu oeffnen
# ===================================================================
def selbsttest():
    import urllib.request
    print("=" * 66)
    print("SELBSTTEST CHARTLABOR.py")
    print("=" * 66)
    fehler = []

    # 1. Eingebaute Seiten - Pruefsumme UND Inhalt
    try:
        chart = seite_chart()
        lern = seite_lern()
        print(f"  [ok]  Chartseite  {len(chart):7d} Bytes, sha {SHA_CHART[:12]}")
        print(f"  [ok]  Lernpfad    {len(lern):7d} Bytes, sha {SHA_LERN[:12]}")
    except SystemExit as e:
        print(str(e))
        return 1

    # Nicht nur "ist da", sondern "ist das Richtige drin".
    marken = [b"<title>Chartlabor</title>", b"randhinweiseZeichnen",
              b"function merken", b"FUELLUNG", b"FIB_STUFEN"]
    fehlend = [m.decode() for m in marken if m not in chart]
    if fehlend:
        fehler.append("in der Chartseite fehlen: " + ", ".join(fehlend))
        print("  [!!]  Chartseite unvollstaendig:", ", ".join(fehlend))
    else:
        print(f"  [ok]  alle {len(marken)} Inhaltsmarken vorhanden")

    # 2. Vorlage
    stand, ordner, _ = vorlagen_stand()
    if stand == "gleich":
        print(f"  [ok]  Vorlage gefunden und identisch: {ordner}")
    elif stand == "abweichend":
        print(f"  [!!]  VERALTET - die Vorlage in {ordner} ist anders.")
        print("        Neu bauen: python chartlabor_py_bauen.py")
        fehler.append("eingebaute Kopie veraltet")
    else:
        print("  [--]  Keine Vorlage gefunden (laeuft trotzdem, eingebaute Kopie)")

    # 3. Kerzen
    daten = daten_ordner()
    if daten:
        dateien = sorted(f for f in os.listdir(daten) if f.endswith(".json"))
        gesamt = sum(os.path.getsize(os.path.join(daten, f)) for f in dateien)
        print(f"  [ok]  Kerzen: {len(dateien)} Dateien, "
              f"{gesamt / 1048576:.1f} MB in {daten}")
    else:
        print("  [!!]  Kein Ordner mit Kerzen gefunden")
        fehler.append("keine Kerzen")

    # 4. Wirklich ausliefern - auf einem eigenen Port, damit ein
    #    laufendes Chartlabor nicht gestoert wird.
    p = port_finden(PORT_PRUEF, PORT_PRUEF + 20)
    if p is None:
        print("  [!!]  kein freier Pruefport")
        fehler.append("kein Pruefport")
    else:
        # frisch=False: hier soll genau die eingebaute Kopie geprueft
        # werden, nicht die Vorlage - sonst prueft der Selbsttest etwas
        # anderes, als in dieser Datei steckt.
        srv = MehrspurigerServer(
            ("127.0.0.1", p), handler_bauen(chart, lern, daten, frisch=False))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{p}/chartlabor.html", timeout=3) as r:
                geliefert = r.read()
            if geliefert == chart:
                print(f"  [ok]  Auslieferung auf Port {p}: Byte fuer Byte gleich")
            else:
                print("  [!!]  Ausgelieferte Seite weicht ab")
                fehler.append("Auslieferung weicht ab")
            if daten and dateien:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{p}/daten/{dateien[0]}", timeout=5) as r:
                    kopf = r.read(200)
                if b'"kerzen"' in kopf or b'"symbol"' in kopf:
                    print(f"  [ok]  Kerzen ausgeliefert ({dateien[0]})")
                else:
                    print("  [!!]  Kerzendatei sieht falsch aus")
                    fehler.append("Kerzen falsch")
            # Gegenprobe: darf NICHT aus dem Ordner herausklettern
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{p}/daten/..%2f..%2fchartlabor.html",
                    timeout=3)
                print("  [!!]  Ausbruch aus dem Datenordner war moeglich")
                fehler.append("Pfadausbruch moeglich")
            except Exception:
                print("  [ok]  Ausbruch aus dem Datenordner wird abgewiesen")
        finally:
            srv.shutdown()
            srv.server_close()

    print("-" * 66)
    if fehler:
        print("  ERGEBNIS: " + str(len(fehler)) + " Beanstandung(en):")
        for f in fehler:
            print("            - " + f)
        return 1
    print("  ERGEBNIS: alles in Ordnung.")
    return 0


# ===================================================================
def main():
    if "--selbsttest" in sys.argv:
        return selbsttest()

    stand, ordner, chart = vorlagen_stand()
    print("=" * 66)
    print("CHARTLABOR - Einzeldatei")
    print("=" * 66)
    print(f"  Gebaut am : {GEBAUT_AM}")
    if stand == "abweichend":
        print()
        print("  !!  ACHTUNG: DIESE DATEI IST VERALTET.")
        print(f"      Die Vorlage in {ordner} ist neuer.")
        print("      Es wird deshalb DIE VORLAGE angezeigt, nicht die")
        print("      eingebaute Kopie. Ein F5 im Browser genuegt, um")
        print("      Aenderungen zu sehen - dieses Fenster muss nicht")
        print("      neu gestartet werden. Sauber wird es mit:")
        print("          python chartlabor_py_bauen.py")
        print()
    elif stand == "gleich":
        print(f"  Vorlage   : gefunden, identisch ({ordner})")
    else:
        print("  Vorlage   : nicht gefunden - eingebaute Kopie wird benutzt")

    daten = daten_ordner()
    if not daten:
        print()
        print("  Es wurden keine Kerzen gefunden (Ordner daten/).")
        print("  Der Chart bliebe leer. Erst KURSVERLAUF_HOLEN.bat im")
        print("  Projektordner doppelklicken - oder den Ordner daten/")
        print("  neben diese Datei legen.")
        print()
        input("  Mit Eingabetaste schliessen ... ")
        return 1
    dateien = sorted(f for f in os.listdir(daten) if f.endswith(".json"))
    print(f"  Kerzen    : {len(dateien)} Datei(en) aus {daten}")

    # Laeuft schon eines? Dann NICHT ein zweites aufmachen.
    if not port_frei(PORT_WUNSCH) and ist_unser_chartlabor(PORT_WUNSCH):
        adresse = f"http://127.0.0.1:{PORT_WUNSCH}/chartlabor.html"
        print()
        print(f"  Es laeuft bereits ein Chartlabor auf Port {PORT_WUNSCH}.")
        print("  Es wird KEIN zweites gestartet - sonst lieben die")
        print("  Zeichnungen auf zwei Adressen getrennt voneinander.")
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

    adresse = f"http://127.0.0.1:{port}/chartlabor.html"
    print(f"  Adresse   : {adresse}")
    if port != PORT_WUNSCH:
        print(f"  ACHTUNG: {PORT_WUNSCH} war belegt. Andere Adresse heisst")
        print("           eigener Zeichnungsspeicher - was du hier malst,")
        print("           steht nicht im Fenster von Port 8777.")
    print()
    print("  DIESES FENSTER OFFEN LASSEN - es haelt den Server.")
    print("  Beenden mit Strg+C oder Fenster schliessen.")
    print("=" * 66)

    threading.Timer(1.0, lambda: webbrowser.open(adresse)).start()
    try:
        with MehrspurigerServer(
                ("127.0.0.1", port),
                handler_bauen(chart, seite_lern(), daten)) as srv:
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Beendet.")
    return 0


# ===================================================================
# Die eingebauten Seiten, base64. Nicht von Hand anfassen.
# ===================================================================
SEITE_CHART_B64 = """\
@@CHART_B64@@"""

SEITE_LERN_B64 = """\
@@LERN_B64@@"""


if __name__ == "__main__":
    sys.exit(main())
'''


START_BAT = r'''@echo off
chcp 65001 > nul
REM ============================================================
REM  CHARTLABOR (Einzeldatei)  -  einfach doppelklicken
REM ============================================================
REM  Startet CHARTLABOR.py, die neben dieser Datei liegt.
REM
REM  WARUM ES DIESE .BAT GIBT: Auf diesem Rechner ist die Endung
REM  .py mit KEINEM Programm verknuepft (geprueft am 07.09.2026:
REM  "assoc .py" findet nichts). Ein Doppelklick auf die .py
REM  wuerde nur den "Womit oeffnen?"-Dialog zeigen.
REM
REM  Jeder Pfad steht in Anfuehrungszeichen: der Benutzername
REM  enthaelt ein Leerzeichen und der Projektordner Klammern.
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

REM Erst den Python-Finder des Projekts benutzen, wenn er da ist -
REM eine zweite Kopie dieser Suche waere eine zweite Wahrheit.
set "PY="
for %%D in ("%USERPROFILE%\Desktop\trading_imperium_v6*") do (
  if exist "%%~fD\_python_finden.bat" call "%%~fD\_python_finden.bat"
)
if not defined PY if exist "%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe" set "PY=%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe"
if not defined PY set "PY=python"

"%PY%" "%~dp0CHARTLABOR.py"
if errorlevel 1 pause
'''


def main():
    if not os.path.isfile(QUELLE_CHART):
        print("ABBRUCH: chartlabor.html nicht gefunden neben diesem Skript.")
        return 1
    if not os.path.isfile(QUELLE_LERN):
        print("ABBRUCH: lernpfad.html nicht gefunden neben diesem Skript.")
        return 1

    with open(QUELLE_CHART, "rb") as f:
        chart = f.read()
    with open(QUELLE_LERN, "rb") as f:
        lern = f.read()

    # Inhaltsprobe VOR dem Bauen. Eine Groessenpruefung wuerde eine
    # halb geschriebene Datei durchwinken.
    marken = [b"<title>Chartlabor</title>", b"randhinweiseZeichnen",
              b"function merken", b"FUELLUNG"]
    fehlend = [m.decode() for m in marken if m not in chart]
    if fehlend:
        print("ABBRUCH: chartlabor.html sieht unvollstaendig aus, es fehlen:")
        for m in fehlend:
            print("   " + m)
        return 1

    sha_chart = hashlib.sha256(chart).hexdigest()
    sha_lern = hashlib.sha256(lern).hexdigest()

    import datetime
    gebaut = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    text = (VORLAGE
            .replace("@@GEBAUT@@", gebaut)
            .replace("@@QUELLE@@", QUELLE_CHART)
            .replace("@@QUELLORDNER@@", HIER)
            .replace("@@SHA_CHART@@", sha_chart)
            .replace("@@SHA_LERN@@", sha_lern)
            .replace("@@CHART_B64@@", blob(chart))
            .replace("@@LERN_B64@@", blob(lern)))

    if "@@" in text:
        rest = [z for z in text.split("\n") if "@@" in z]
        print("ABBRUCH: eine Platzhalterstelle blieb stehen:")
        for z in rest[:5]:
            print("   " + z.strip()[:70])
        return 1

    # LAESST SICH DAS ERZEUGTE UEBERHAUPT UEBERSETZEN?
    #
    # [07.09.2026] Diese Pruefung gibt es, weil genau hier der erste
    # Bau kaputtging: der eingesetzte Pfad C:\Users\... stand im
    # Kommentarkopf, und \U ist fuer Python der Anfang einer
    # Escape-Sequenz. Die Datei wurde klaglos geschrieben und war
    # unbrauchbar. Ein Baumeister, der nicht nachsieht, ob sein
    # Ergebnis laeuft, meldet Erfolg fuer eine kaputte Datei.
    try:
        compile(text, "CHARTLABOR.py", "exec")
    except SyntaxError as e:
        print("ABBRUCH: die erzeugte Datei laesst sich nicht uebersetzen.")
        print(f"         Zeile {e.lineno}: {e.msg}")
        if e.text:
            print("         " + e.text.strip()[:70])
        return 1

    ziel_ordner = desktop_finden()
    ziel_py = os.path.join(ziel_ordner, "CHARTLABOR.py")
    ziel_bat = os.path.join(ziel_ordner, "CHARTLABOR.bat")

    with io.open(ziel_py, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    with io.open(ziel_bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(START_BAT)

    # Gegenprobe: zurueckLESEN und die eingebaute Seite wieder
    # herausholen. "Datei geschrieben" ist keine Bestaetigung, dass das
    # Richtige drinsteht.
    with io.open(ziel_py, encoding="utf-8") as f:
        zurueck = f.read()
    anfang = zurueck.index('SEITE_CHART_B64 = """\\\n') + len('SEITE_CHART_B64 = """\\\n')
    ende = zurueck.index('"""', anfang)
    heraus = base64.b64decode("".join(zurueck[anfang:ende].split()))
    if heraus != chart:
        print("ABBRUCH: die Gegenprobe stimmt nicht - die eingebaute Seite")
        print("         entspricht nicht der Vorlage. Datei nicht benutzen.")
        return 1

    print("=" * 66)
    print("CHARTLABOR.py gebaut")
    print("=" * 66)
    print(f"  Ziel      : {ziel_py}")
    print(f"  Dazu      : {ziel_bat}  (zum Doppelklicken)")
    print(f"  Chartseite: {len(chart):7d} Bytes  sha {sha_chart[:16]}")
    print(f"  Lernpfad  : {len(lern):7d} Bytes  sha {sha_lern[:16]}")
    print(f"  Datei     : {len(text.encode('utf-8')):7d} Bytes")
    print("  Gegenprobe: eingebaute Seite = Vorlage, Byte fuer Byte")
    print()
    print("  Pruefen mit:  python \"" + ziel_py + "\" --selbsttest")
    print("=" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())
