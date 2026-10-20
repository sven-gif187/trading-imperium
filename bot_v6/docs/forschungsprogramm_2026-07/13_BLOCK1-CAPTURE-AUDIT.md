# Block 1 — Capture-Audit und Reparatur

**03.08.2026 · Ergebnis: Der Capture lief NICHT mehr. Drei Konstruktions-
fehler, alle behoben. Die erfassten Daten sind trotz Beschädigung
überwiegend brauchbar.**

Rohausgabe: `ausgaben/audit_capture_daten_out.txt`.
Reproduktion: `python audit_capture_daten.py` (~8 min, liest 190 MB).

---

## 1.1 Doppelstart — der Singleton hat versagt

**[BEFUND]** Es liefen zeitweise bis zu **19 Instanzen gleichzeitig**.
**[BELEG]** `capture.log`: 121× `CAPTURE START`, 229× `ABBRUCH`. Im
Heartbeat des 02.08. stehen **13.424 Zeilen**, wo bei 120 s Poll **720**
vorgesehen waren — Faktor 18,6. Mehrere Zeilen tragen gleichzeitig
`Zyklus 3`, `Zyklus 270`, `Zyklus 330`, `Zyklus 780` innerhalb weniger
Sekunden: verschiedene Instanzen mit eigenen Zählern.
**[URSACHE]** Der alte Schutz las eine PID-Datei, prüfte per `tasklist`
ob der Prozess lebt, und schrieb dann die eigene PID. Das ist ein
klassischer Check-Then-Act-Wettlauf: zwei gleichzeitig gestartete
Instanzen sehen beide „niemand da" und laufen beide los. Er griff in
zwei Dritteln der Fälle (229 Abbrüche) und versagte im letzten Drittel.
**[KONSEQUENZ]** Behoben durch eine **Betriebssystem-Sperre**
(`msvcrt.locking`, exklusiv, für die Prozesslaufzeit gehalten). Atomar,
und Windows gibt sie auch bei hartem Abschuss frei.
**[BELEGT DURCH TEST]** Zweite Instanz bei laufender erster:
`ABBRUCH: eine andere Instanz haelt die Sperre` — verifiziert 13:33:00Z.
**[KONFIDENZ]** SICHER · Risiko 2 | Aufwand 2 | Impact 9

**Zum Zeitpunkt der Prüfung lief gar keine Instanz mehr** — weder Capture
noch Bot. Kein `python.exe`, kein `pythonw.exe` im Prozessbaum.

## 1.2 Die Ausfallphasen — Ratenbegrenzung, selbst verursacht

**[BEFUND]** Ab dem 01.08. 16:21 Uhr UTC schlugen Zyklen mit
`ok=0 fehler=36` fehl, also **alle** Anfragen.
**[BELEG]** Erste Meldung `[2026-08-01T16:21:42Z] Zyklus 60: ok=0
fehler=36`; letzte erfolgreiche `[2026-08-03T08:37:46Z] Zyklus 1: ok=60
fehler=0`.
**[URSACHE]** Nicht Netzwerk, nicht die Börse. Die Ratenbegrenzung im
Code (max. 1 Request/s) gilt **pro Prozess**. Bei 19 Instanzen wurden
daraus 19 Requests/s — die API hat abgeriegelt.
**[GEGENPROBE]** Nach der Reparatur mit **einer** Instanz:
`ok=60 fehler=0, latenz_med=450ms` (13:31:43Z). Die API antwortet
einwandfrei; der Fehler lag ausschließlich bei uns.
**[KONFIDENZ]** SICHER · Risiko 1 | Aufwand 1 | Impact 7

## 1.2b Datenverlust durch gleichzeitiges gzip-Append

**[BEFUND]** **Alle 52 geprüften `.csv.gz` sind beschädigt.**
**[BELEG]** `zlib.error: Error -3 while decompressing data: invalid
block type` beim normalen Lesen. Mit einem rettenden Leser (sucht nach
jedem Fehler das nächste `1f8b`-Magic) wurden **22,2 MB aus 30,0 MB**
Rohdaten geborgen — rund **26 % der Bytes sind verloren**.
**[URSACHE]** Der alte Code öffnete für **jede einzelne Zeile** eine
gzip-Datei im Append-Modus. Jede Zeile wurde ein eigenes gzip-Mitglied.
Bei gleichzeitigen Schreibern verschränken sich diese Mitglieder zu
einem unlesbaren Strom. Derselbe Mechanismus erklärt auch die
Dateigröße: 100 MB am 02.08. statt der veranschlagten 50 MB.
**[KONSEQUENZ]** Behoben: es wird **unkomprimiert** geschrieben und erst
bei der Tagesrotation gepackt. Eine zerrissene Zeile kostet dann eine
Zeile, nicht die Datei.
**[KONFIDENZ]** SICHER · Risiko 3 | Aufwand 3 | Impact 8

## 1.2c Das aufpoppende Fenster

**[BEFUND]** Der Task rief `capture_start.bat` auf. Windows startet
dafür `cmd.exe` — **das** war das Fenster, das alle 10 Minuten aufging.
**[KONSEQUENZ]** Der Task ruft jetzt `pythonw.exe` **direkt** mit dem
Skript als Argument auf. `pythonw` hat keine Konsole. Verifiziert: der
laufende Prozess ist `pythonw.exe`, kein Fenster.
Die `.bat` bleibt liegen (Löschverbot), wird aber nicht mehr verwendet.
**[KONFIDENZ]** SICHER · Risiko 0 | Aufwand 1 | Impact 4

## 1.3 Selbstprüf-Befehl

Ein Befehl, CMD-tauglich, zeigt Prozess **und** Alter des letzten
Schreibvorgangs:

```
powershell -Command "$p=Get-Process pythonw -EA 0; $f=Get-ChildItem 'C:\Users\<BENUTZER>\Desktop\trading_imperium_v6(21)\docs\forschungsprogramm_2026-07\capture\2026-*' -Filter *.csv | Sort LastWriteTime -Desc | Select -First 1; Write-Host ('Prozess: ' + $(if($p){'LAEUFT (PID '+$p.Id+')'}else{'LAEUFT NICHT'})); Write-Host ('Letzter Schreibvorgang vor ' + [math]::Round(((Get-Date)-$f.LastWriteTime).TotalMinutes,1) + ' Minuten')"
```

Lesart: Prozess `LAEUFT` **und** letzter Schreibvorgang unter 5 Minuten
→ alles in Ordnung. Prozess läuft nicht → der Watchdog startet ihn
spätestens nach 15 Minuten selbst.

## 1.4 Überlebensfähigkeit — was belegt ist und was nicht

| Frage | Antwort | Beleg |
|---|---|---|
| Task-Trigger | alle **15 Minuten** (vorher 10) | `schtasks /Query /XML`: `<Interval>PT15M</Interval>` |
| Aufruf | `pythonw.exe <skript>` direkt, kein cmd, kein Fenster | Task-XML `<Command>`/`<Arguments>` |
| Doppelstart | OS-Sperre, getestet | Log 13:33:00Z |
| Sitzungsende | überlebt — der Task-Prozess hängt nicht an der Shell | Prozess läuft unter Task-Elternschaft |
| **Rechner-Neustart** | **NICHT GETESTET** | siehe unten |

**Zum Neustart: NICHT ENTSCHEIDBAR ohne Test.** Der Trigger ist
zeitbasiert (alle 15 Min), nicht ONLOGON — ONLOGON scheiterte an
fehlenden Adminrechten (`Zugriff verweigert`). Zeitbasierte Tasks laufen
nach dem Neustart weiter, **sobald der Benutzer angemeldet ist**; ohne
Anmeldung läuft er nicht, weil der Task im Benutzerkontext ohne
gespeichertes Kennwort registriert ist. Ein echter Neustart-Test würde
den Rechner herunterfahren und damit den Bot betreffen — das ist
untersagt, also **nicht simuliert und nicht behauptet**.

## 1.5 Ressourcen

| Größe | Wert |
|---|---|
| Erfasst 31.07.–03.08. | 190 MB in 4 Tagesordnern |
| 02.08. (voller Tag, 19 Instanzen) | 100,55 MB |
| Erwartung mit **einer** Instanz | ~5 MB/Tag gepackt [VERMUTUNG, aus 100 MB ÷ 18,6] |
| Freier Speicher | 126,4 GB (aus Heartbeat) |
| Grenze für Handlungsbedarf | Heartbeat warnt unter 10 GB |

Bei ~5 MB/Tag reicht der Platz rechnerisch über 60 Jahre. Der
Speicherbedarf ist **kein** limitierender Faktor.

## 1.6 Datenqualität — was trotz allem brauchbar ist

| Reihe | Wert |
|---|---|
| Ticker-Messpunkte gesamt (dedupliziert) | **25.055** (BTC) |
| Duplikate | **0,3 %** — und alle mit **identischem** `mid`, kein Widerspruch |
| Nullspreads / unplausible Werte | **0** |
| Lücken > 10 min | 4–8 je Tag, längste **166,8 min** |
| 03.08. Heartbeat | **unbrauchbar** — keine gültigen Zeitstempel |

**Wichtige Einschränkung:** Die 25.055 Punkte sind **keine 25.055
unabhängigen Beobachtungen**. Sie stammen aus ~2.880 realen Zeitfenstern,
die von bis zu 19 Instanzen mehrfach abgefragt wurden. Die effektive
Stichprobe ist um etwa Faktor 9–19 kleiner. Für Median-Schätzungen ist
das unkritisch, für Konfidenzintervalle **nicht** — daraus dürfen keine
Intervalle gerechnet werden.

## Offener Punkt für den Eigentümer

**Der Bot (`app.py`) läuft ebenfalls nicht mehr.** Beim letzten Check am
31.07. lief er als PID 7476. Heute ist kein `python.exe` im Prozessbaum.
Vermutlich wurde er mit demselben Fenster geschlossen. **Ich habe ihn
NICHT neu gestartet** — die harte Grenze lautet, den Bot nicht
anzufassen. Ob und wann er wieder laufen soll, ist deine Entscheidung.
