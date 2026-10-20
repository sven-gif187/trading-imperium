# -*- coding: utf-8 -*-
r"""
chartlabor_teilen_bauen.py - baut die Fassung zum Weitergeben
=============================================================
[08.09.2026, Wunsch von Sven: "kannst du mir einen link erstellen wo ich
einem freund das werkzeug geben kann"]

WAS DAS IST

  Eine EINZIGE HTML-Datei, in der die Kerzen mit drinstehen. Sie
  braucht keinen Server, keine Dateien daneben und kein Python - sie
  laeuft ueberall, wo ein Browser ist. Aus ihr wird der Link.

WARUM DIE DATEN HINEIN MUESSEN

  Eine Seite, die auf claude.ai veroeffentlicht wird, darf nichts
  nachladen - keine JSON-Datei, keinen fremden Server, gar nichts. Das
  ist eine Sicherheitsregel dort und nicht verhandelbar. Also muessen
  die Kerzen mit in die Datei.

WAS DESHALB FEHLT

  15-Minuten-, Minuten- und Sekundenkerzen. BTC allein hat davon
  620.000 Stueck und 48 MB - das passt nicht in eine Seite und waere
  auch nicht zumutbar zu laden. Drin sind Monat, Woche, Tag, 4 Std und
  1 Std fuer alle drei Maerkte.

  Die Preise sind auf Cent gerundet. Yahoo liefert Fliesskomma-
  Rauschen (4444.2998046875 statt 4444.30); groesster Unterschied durch
  die Rundung: 0,0002 USD. Das spart 1,8 MB und verliert nichts, was
  je gemessen wurde.

WAS DIE FASSUNG NICHT KANN

  Sie ist eine MOMENTAUFNAHME. Der Freund sieht die Kurse bis zum
  Bautag und danach nie wieder neue - dafuer muesste sie neu gebaut und
  neu veroeffentlicht werden. Das steht auch in der Seite selbst, damit
  es niemand fuer einen Fehler haelt.

WOHER SIE KOMMT

  Aus chartlabor.html - wie CHARTLABOR.py auch. Eine Quelle, zwei
  Abzuege. Von Hand wird in der Teilfassung nichts geaendert.

STARTEN:  python chartlabor_teilen_bauen.py
"""
import io
import json
import os
import sys
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
QUELLE = os.path.join(HIER, "chartlabor.html")
DATEN = os.path.join(HIER, "daten")
ZIELORDNER = os.path.join(HIER, "teilen")
ZIEL = os.path.join(ZIELORDNER, "chartlabor_geteilt.html")
# Dieselbe Seite, aber mit Dokumentkopf - zum Verschicken und
# Doppelklicken, ohne Anmeldung und ohne Server.
ZIEL_EINZELN = os.path.join(ZIELORDNER, "CHARTLABOR_ZUM_VERSCHICKEN.html")

# Was mitkommt. 15m/1m/1s bleiben absichtlich draussen - siehe oben.
RASTER = ["1mon", "1w", "1d", "4h", "1h"]
MAERKTE = ["BTCUSDT", "GOLD", "SILBER"]


def kompakt(kerzen):
    """Kerzen als Zahlenreihen statt als Objekte, Preise auf Cent.

    [t,o,h,l,c,v] statt {"t":...,"o":...}. Spart rund 40 Prozent, weil
    die sechs Feldnamen nicht 300.000-mal wiederholt werden.
    """
    return [[k["t"], round(k["o"], 2), round(k["h"], 2), round(k["l"], 2),
             round(k["c"], 2), round(k["v"], 2)] for k in kerzen]


def main():
    if not os.path.isfile(QUELLE):
        print("ABBRUCH: chartlabor.html nicht gefunden.")
        return 1
    with io.open(QUELLE, encoding="utf-8", newline="") as f:
        seite = f.read()

    uebersicht_pfad = os.path.join(DATEN, "uebersicht.json")
    if not os.path.isfile(uebersicht_pfad):
        print("ABBRUCH: daten/uebersicht.json fehlt - erst KURSVERLAUF_HOLEN.bat.")
        return 1
    with io.open(uebersicht_pfad, encoding="utf-8") as f:
        uebersicht = json.load(f)["maerkte"]

    # ---- Daten einsammeln ----
    roh, maerkte, fehlend = {}, {}, []
    for sym in MAERKTE:
        if sym not in uebersicht:
            fehlend.append(sym)
            continue
        eintrag = {"name": uebersicht[sym]["name"],
                   "quelle": uebersicht[sym]["quelle"], "raster": {}}
        for datei_tf in RASTER:
            pfad = os.path.join(DATEN, f"{sym}_{datei_tf}.json")
            if not os.path.isfile(pfad):
                continue
            with io.open(pfad, encoding="utf-8") as f:
                d = json.load(f)
            k = d["kerzen"]
            if not k:
                continue
            roh[f"{sym}_{datei_tf}"] = kompakt(k)
            eintrag["raster"][d["interval"]] = {
                "anzahl": len(k), "von": k[0]["t"], "bis": k[-1]["t"]}
        if eintrag["raster"]:
            maerkte[sym] = eintrag
    if fehlend:
        print("  Hinweis: keine Daten fuer", ", ".join(fehlend))
    if not maerkte:
        print("ABBRUCH: keine Daten zum Einbauen gefunden.")
        return 1

    stand = datetime.now().strftime("%d.%m.%Y")
    eingebaut = ("const EINGEBAUT = "
                 + json.dumps({"stand": stand, "maerkte": maerkte, "roh": roh},
                              separators=(",", ":"))
                 + ";\n")

    fehler = []

    def ersetze(anker, neu, name):
        nonlocal seite
        n = seite.count(anker)
        if n != 1:
            fehler.append(f"{name}: Anker {n}x (erwartet 1x)")
            return
        seite = seite.replace(anker, neu, 1)

    # ---- 1. Kopf weg: das Artifact liefert doctype, head und body ----
    ersetze('<!doctype html>\n<meta charset="utf-8">\n<title>Chartlabor</title>\n',
            '<title>Chartlabor</title>\n',
            "Kopfzeilen entfernen")

    # ---- 2. Lernpfad-Knopf raus, Hinweis rein ----
    ersetze('''  <div class="gruppe">
    <button onclick="location.href='lernpfad.html'">📘 Lernpfad</button>
  </div>''',
            '''  <div class="gruppe">
    <span class="titel" id="standhinweis"></span>
  </div>''',
            "Lernpfad ersetzen")

    # ---- 3. Kerzen aus der Datei statt vom Server ----
    ersetze('''    const datei = (rahmen === "1M") ? "1mon" : rahmen;
    const antwort = await fetch(`daten/${symbol}_${datei}.json`);
    if(!antwort.ok) throw new Error(antwort.status + " " + antwort.statusText);
    const d = await antwort.json();
    kerzen = d.kerzen;''',
            '''    // TEILFASSUNG: die Kerzen stehen in dieser Datei, es wird nichts
    // nachgeladen. Ausgepackt wird erst beim ersten Gebrauch - sonst
    // haette der Browser beim Start alle Maerkte gleichzeitig im Kopf.
    const datei = (rahmen === "1M") ? "1mon" : rahmen;
    const schluessel = symbol + "_" + datei;
    if(!EINGEBAUT.fertig[schluessel]){
      const r = EINGEBAUT.roh[schluessel];
      if(!r) throw new Error("in dieser Fassung nicht enthalten");
      EINGEBAUT.fertig[schluessel] = r.map(a=>({t:a[0], o:a[1], h:a[2],
                                                l:a[3], c:a[4], v:a[5]}));
    }
    kerzen = EINGEBAUT.fertig[schluessel];''',
            "Kerzen einbauen")

    # ---- 4. Uebersicht aus der Datei statt vom Server ----
    ersetze('''  try{
    const antwort = await fetch("daten/uebersicht.json");
    if(!antwort.ok) throw new Error(antwort.status);
    const d = await antwort.json();
    if(d && d.maerkte && Object.keys(d.maerkte).length) uebersicht = d.maerkte;
  }catch(e){
    uebersicht = null;               // kein Beinbruch, nur weniger Auswahl
  }''',
            '''  uebersicht = EINGEBAUT.maerkte;      // TEILFASSUNG: steht in der Datei
  const hinweis = document.getElementById("standhinweis");
  if(hinweis) hinweis.textContent = "Stand " + EINGEBAUT.stand;''',
            "Uebersicht einbauen")

    # ---- 5. Der eingebaute Datenblock, ganz oben im Skript ----
    ersetze('''<script>
"use strict";''',
            '<script>\n"use strict";\n' + eingebaut
            + 'EINGEBAUT.fertig = {};\n',
            "Datenblock einsetzen")

    # ---- 6. Ein Wort zur Herkunft, in die Hinweiszeile ----
    ersetze('''  <div id="meldung" hidden></div>''',
            '''  <div id="meldung" hidden></div>
  <div id="teilhinweis" style="position:absolute;top:8px;right:12px;
       max-width:320px;background:rgba(13,17,23,.9);border:1px solid #30363d;
       border-radius:6px;padding:6px 9px;font-size:11px;color:#8b949e;
       z-index:3;cursor:pointer" title="Wegklicken"
       onclick="this.remove()">
    <b style="color:#e6edf3">Chartlabor – Fassung zum Weitergeben</b><br>
    Kurse stecken in dieser Seite (Momentaufnahme, keine Aktualisierung).
    Enthalten: Monat, Woche, Tag, 4 Std, 1 Std für BTC, Gold und Silber.
    Zeichnungen bleiben in deinem Browser.
  </div>''',
            "Hinweiskasten")

    if fehler:
        print("ABBRUCH - nichts geschrieben:")
        for f in fehler:
            print("   " + f)
        return 1

    # ---- 6b. Speichern ueber die Artifact-Faehigkeit ----
    #
    # WARUM DAS SEIN MUSS: Im Artifact-Viewer sind gewoehnliche
    # Downloads gesperrt. Ein <a download> tut dort NICHTS - und zwar
    # lautlos. Der Knopf haette "gesichert" gemeldet und nichts getan;
    # genau die Sorte Erfolgsmeldung, die keine ist.
    ersetze('''function sichern(){''', '''async function sichern(){''',
            "sichern wird async")

    ersetze('''  const name = `chartlabor_zeichnungen_${symbol}_${zeitstempel()}.json`;
  const blob = new Blob([JSON.stringify(paket, null, 2)], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 10000);
  melde(`Gesichert: ${zeichnungen.length} Zeichnung(en), `
      + `${belegtePlaetze} von ${PLAETZE.length} Plätzen.\\n${name}\\n`
      + `Sie liegt im Download-Ordner.`, "ok");''',
            '''  const name = `chartlabor_zeichnungen_${symbol}_${zeitstempel()}.json`;
  const inhalt = JSON.stringify(paket, null, 2);
  const zusammen = `${zeichnungen.length} Zeichnung(en), `
                 + `${belegtePlaetze} von ${PLAETZE.length} Plätzen`;

  // Diese Fassung laeuft auf einer veroeffentlichten Seite. Dort sind
  // gewoehnliche Downloads gesperrt - ein <a download> tut lautlos
  // nichts. Deshalb erst den Weg ueber die Speicher-Faehigkeit
  // versuchen, die den Betrachter fragt; wird die Datei dagegen
  // oertlich geoeffnet, gibt es sie nicht und der alte Weg greift.
  const speicher = (window.claude && window.claude.use)
      ? await window.claude.use("downloads") : null;
  if(speicher){
    try{
      await speicher.save({filename: name, data: inhalt});
      melde(`Gesichert: ${zusammen}.\\n${name}`, "ok");
    }catch(e){
      // Kein stilles Scheitern: auch ein Abbruch wird gesagt.
      melde(e && e.code === "declined"
        ? "Abgebrochen — es wurde nichts gespeichert."
        : `Speichern ging nicht: ${(e && e.message) || e}`, "fehler");
    }
    return;
  }
  const blob = new Blob([inhalt], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 10000);
  melde(`Gesichert: ${zusammen}.\\n${name}\\nSie liegt im Download-Ordner.`, "ok");''',
            "Speichern ueber Faehigkeit")

    # ---- 6c. Der Altershinweis bekommt einen Rat, der hier passt ----
    #
    # Die Quelle rät, KURSVERLAUF_HOLEN.bat zu doppelklicken. Wer diese
    # Fassung bekommt, hat weder die .bat noch den Ordner - ein Rat, den
    # man nicht befolgen kann, ist schlimmer als keiner.
    ersetze(
        'const ALTER_RAT = "Zum Nachholen: KURSVERLAUF_HOLEN.bat im '
        'Chartlabor-Ordner doppelklicken.";',
        'const ALTER_RAT = "Diese Fassung ist eine Momentaufnahme - '
        'neue Kurse kommen hier nicht nach.";',
        "Altersrat fuer die Teilfassung")

    # ---- 7. Kein Name im Quelltext ----
    #
    # Die Kommentare erklaeren, WARUM etwas so ist - das ist der Wert des
    # Codes und bleibt drin. Der Name des Auftraggebers gehoert aber
    # nicht auf eine Seite, die weitergegeben wird. Wer den Quelltext
    # oeffnet, soll die Begruendung lesen, nicht wissen, von wem der
    # Wunsch kam.
    for alt, neu in [("Wunsch von Sven:", "Wunsch:"),
                     ("Wunsch von Sven", "auf Wunsch"),
                     ("von Sven", "auf Wunsch"),
                     ("Sven", "der Anwender")]:
        seite = seite.replace(alt, neu)
    if "Sven" in seite:
        stelle = seite.index("Sven")
        print("ABBRUCH: es steht noch ein Name im Quelltext:")
        print("   ..." + seite[max(0, stelle-70):stelle+70].replace("\n", " ") + "...")
        return 1

    # ---- Gegenproben, bevor irgendetwas geschrieben wird ----
    if "fetch(" in seite:
        stelle = seite[max(0, seite.index("fetch(")-80):seite.index("fetch(")+80]
        print("ABBRUCH: es wird noch etwas nachgeladen - das kann eine")
        print("         veroeffentlichte Seite nicht. Stelle:")
        print("   ..." + stelle.replace("\n", " ") + "...")
        return 1
    for pflicht in ["<title>Chartlabor</title>", "randhinweiseZeichnen",
                    "function merken", "EINGEBAUT.roh", "FIB_ZONEN"]:
        if pflicht not in seite:
            print(f"ABBRUCH: '{pflicht}' fehlt in der erzeugten Seite.")
            return 1
    if "<!doctype" in seite.lower():
        print("ABBRUCH: der Dokumentkopf ist noch drin - das Artifact setzt ihn selbst.")
        return 1

    os.makedirs(ZIELORDNER, exist_ok=True)
    with io.open(ZIEL, "w", encoding="utf-8", newline="\n") as f:
        f.write(seite)

    # ---- Zweite Fassung: zum Verschicken, ohne Anmeldung ----
    #
    # WARUM ZWEI DATEIEN: Die Fassung fuers Veroeffentlichen hat KEINEN
    # Dokumentkopf - den setzt die Artifact-Seite selbst. Genau diese
    # Datei per Doppelklick zu oeffnen ginge schief: ohne <!doctype>
    # schaltet der Browser in den Kompatibilitaetsmodus (die Aufteilung
    # oben/unten bricht zusammen), und ohne Angabe der Zeichenkodierung
    # wuerden aus den Umlauten Fragezeichen. Also bekommt die
    # Verschickfassung beides.
    einzeln = ('<!doctype html>\n<meta charset="utf-8">\n'
               '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
               + seite)
    with io.open(ZIEL_EINZELN, "w", encoding="utf-8", newline="\n") as f:
        f.write(einzeln)

    groesse = os.path.getsize(ZIEL)
    print("=" * 66)
    print("TEILFASSUNG GEBAUT")
    print("=" * 66)
    print(f"  Fuer den Link : {ZIEL}")
    print(f"  Zum Verschicken: {ZIEL_EINZELN}")
    print(f"  Groesse : {groesse/1048576:.2f} MB  (Grenze fuer ein Artifact: 16 MB)")
    print(f"  Stand   : {stand}")
    for sym, m in maerkte.items():
        raster = " ".join(f"{tf}({m['raster'][tf]['anzahl']})"
                          for tf in ["1M", "1w", "1d", "4h", "1h"]
                          if tf in m["raster"])
        print(f"  {sym:9} {m['name']:16} {raster}")
    if groesse > 15 * 1048576:
        print()
        print("  ACHTUNG: knapp an der 16-MB-Grenze. Ein Zeitraster weglassen.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
