<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Entscheidungsvorlage · 15.10.2026

**Grundlage:** Einstiegs-Prüfung A4, Ausstiegs-Prüfung A5, Strategie-Labor (Stufe 4–6) und die unabhängige Gegenprüfung A10 (`berichte/2026-10-14_advocatus.md`). Dazu die ersten Läufe der Wächter W1–W7.
**Instanz:** Die Zahlen zum Bot gelten für **v6** (Epoche E7, 13.08.–13.10., 136 Runden). Die Laborzahlen sind Rückrechnungen. Beides bleibt getrennt.

---

## 1 · Das Ergebnis in fünf Sätzen

1. **Der heutige Bot kauft und verkauft nicht besser als der Zufall.** A4 findet beim Einstieg keinen Vorsprung, das „Können“ liegt bei −0,05 % je Runde [−0,55; +0,41]. Bei A5 ändern alle Ausstiegs-Stellschrauben das Ergebnis um höchstens ±10 $ in zwei Monaten. A10 hat alle 9 Kernzahlen mit eigenem Code nachgerechnet, und sie stimmen.
2. **Die Kosten fressen alles.** E7 brachte vor Kosten +75,51 $ und nach Kosten −34,11 $. Selbst mit Bitvavo-Kosten bleiben vom Plus nur gut 23 $ ehrlich übrig, alles aus dem August-Anstieg. Bei diesem Handelstempo kosten die Runden rund 39 % des Kapitals im Jahr. BTC halten brachte in der Rückrechnung 26 % im Jahr.
3. **Jede scheinbar bessere Variante gewinnt auf dieselbe Weise:** Sie handelt seltener und bleibt länger investiert, während der Markt steigt. Keine zeigt besseres Timing.
4. **Am ehesten wird das Projekt profitabel mit einer langsamen Trendregel**, die wenige Male im Monat handelt. In der Rückrechnung schafft das Trend-Ensemble K2 57 % im Jahr bei −36 % größtem Rückgang. Die einfache Regel „BTC halten, solange er über der 200-Tage-Linie liegt“ (M3) war aber seit 2022 genauso gut oder besser. Welche von beiden gewinnt, ist offen.
5. **Der Papier-Wettkampf (seit heute) entscheidet das nicht statistisch.** Selbst in der Rückrechnung schlug K2 die 200-Tage-Regel nur in jedem zweiten 3-Monats-Zeitraum. Nach 3 Monaten gibt es also eine Tendenz, keinen Beweis.

Konfidenz: [WAHRSCHEINLICH 75 %], dass der heutige Kurzfrist-Bot in Seitwärts- oder Abwärtsphasen auch bei Bitvavo-Kosten nach Kosten verliert. [VERMUTUNG 55 %], dass eine langsame Trendregel ihn über 12 Monate nach Kosten schlägt.

---

## 2 · Deine Entscheidungen

Jede Frage ist ein Entweder-oder. Darunter steht, was davon abhängt, und meine Empfehlung.

### E1 · Wohin geht die Hauptarbeit?
- **(a)** Den Kurzfrist-Bot weiter verbessern. *Folge:* Um einen Vorsprung zu belegen, bräuchte er rund 2.200 Runden, also etwa 32 Monate. Bis dahin arbeiten wir weitgehend im Blindflug.
- **(b)** Der Kurzfrist-Bot läuft auf Papier unverändert weiter, als Vergleich und Messobjekt. Die Hauptarbeit geht in die langsame Trendregel (Wettkampf B/C gegen die 200-Tage-Regel). *Folge:* Nach 3 Monaten (Mitte Januar) entscheidest du: umstellen, weiter beobachten oder abbrechen. Am Bot ändert sich bis dahin nur Kleinkram.

**Empfehlung: (b).** Alle vier Prüfungen zeigen in dieselbe Richtung. Echtgeld bleibt in beiden Fällen aus.

### E2 · Muss der Trend-Kandidat auch die einfache 200-Tage-Regel schlagen?
- **Ja:** B/C gelten im Wettkampf nur als besser, wenn sie den heutigen Bot **und** die 200-Tage-Regel schlagen. *Folge:* Das ist ehrlicher, denn die einfachere Regel gewinnt bei Gleichstand. Es wird aber öfter „unentschieden“ herauskommen.
- **Nein:** B/C müssen nur den heutigen Bot schlagen. *Folge:* Das ist leichter zu bestehen. Wir könnten dann aber eine komplizierte Regel wählen, obwohl die einfache gereicht hätte.

**Empfehlung: Ja.** Die 200-Tage-Regel wird so oder so jede Woche mitgerechnet.

### E3 · Was zählt im Wettkampf als „heutiger Bot“?
- **Jede Version von v6 ab heute:** Jede Änderung (Epoche) steht im Wochenbericht. *Folge:* Wir messen den Bot, so wie er sich entwickelt.
- **Nur die Version von heute (E11):** *Folge:* Die Messung ist sauberer, aber mit der nächsten Änderung am Bot endet der Vergleich.

**Empfehlung: jede Version** (so ist es vorläufig eingetragen). Ändern geht bis zum ersten Wochenbericht am Montag, 19.10.

### E4 · Soll der Marktlage-Wächter W1 ein „Halteband“ bekommen?
Gemeint ist: Ein erkannter Aufwärtstrend gilt erst dann als vorbei, wenn er deutlich nachlässt, nicht schon beim ersten Wackeln.
- **Ja:** Im Rückblick hätte W1 im August nicht mehr fünfmal hin und her gewechselt. W2 hätte schon am **24.08.** „Trend verpasst“ gemeldet, also einen Monat früher als ohne Band (23.09.).
- **Nein:** W1 bleibt bei den Startwerten.

**Empfehlung: Ja.** Am Bot ändert sich dadurch nichts, nur am Wächter.

### E5 · Sicherheitsabstand beim Absichern auf Null (Puffer 0,195 → 0,25 %)?
- **Ja:** Wenn der Bot eine Position „auf Null“ absichert, landet er im Mittel leicht im Plus statt leicht im Minus. W3 springt dann von Gelb auf Grün. *Folge:* Das ist eine kleine Bot-Änderung mit neuer Epoche (v6 E12, v7 L11). Die Wirkung liegt bei etwa +1 $ in zwei Monaten.
- **Nein:** Alles bleibt, W3 bleibt gelb.

**Empfehlung: Ja**, aber erst zusammen mit der nächsten Bot-Änderung, nicht als eigene Epoche. A10: trägt.

### E6 · Wie messen wir die Ausstiegs- und Halte-Ideen weiter?
Gemeint sind X1 (Stopp-Abstand 2 × typische Schwankung), 12 Stunden halten (mit Notstopp und einer Position je Münze) und das RSI-Verkaufssignal, jeweils getrennt nach Marktlage.
- **(a) Monatlich aus den vorhandenen Daten nachrechnen**, ohne Eingriff in den Bot. *Folge:* Das ist etwas ungenauer, aber ohne Risiko und ohne Epoche.
- **(b) Ein Schattenbuch im Bot:** Er schreibt mit, was diese Regeln getan hätten. *Folge:* Das ist genauer, braucht aber einen Eingriff in den Bot-Code. A10 vermutet außerdem, dass sich ein Rückkauf-Verbot dort nicht sauber abbilden lässt.

**Empfehlung: (a).** Bis zu einem Urteil braucht jede Idee ohnehin 570–780 Runden, das sind 9–12 Monate.

Nicht mehr zur Wahl steht nach A10: das Bündel X3 (sein Vorteil war ein Rechenartefakt) und das 12-Stunden-Halten mit der alten Erwartung +0,27 (realistisch ≤ +0,15).

---

## 3 · Was nur du selbst tun kannst

1. **Telegram einrichten.** Heute Nacht gab es zwei Vorfälle, die W5 sofort erkannt hat. Bei dir ist trotzdem nichts angekommen, weil Telegram fehlt. Dafür den Token kopieren und `Desktop\pruefstand\TELEGRAM_EINRICHTEN.bat` doppelklicken.
2. **Internet in der Nacht prüfen.** Von etwa 23:10 bis 10:40 hatte der Rechner kein Internet, obwohl er lief. Mögliche Ursachen: der WLAN-Adapter im Energiesparmodus (Geräte-Manager → Netzwerkadapter → Energieverwaltung) oder der Router nachts. Das sind Systemeinstellungen, die ich nicht ändern darf.
3. **Windows-Update-Neustart** nachts sperren (Nutzungszeit). Das ist weiter offen.
4. **Irgendwann eine neue Sitzung starten**, damit die Prüf-Agenten A1–A11 als eigene Agenten verfügbar sind. Das ist nicht eilig.

---

## 4 · Was ich seit gestern Abend erledigt habe (ohne deine Freigabe nötig)

- **A10 fertig** (Bericht oben). Die Korrekturen stehen als Nachtrag in den Berichten A4, A5 und Labor. Die Abschnitte „Debatte (A10)“ in E8, E10 und E11 sind als Selbstprüfung gekennzeichnet.
- **Wettkampf messbar gemacht** (S7-Nachtrag 1): Der heutige Bot hat jetzt eine tägliche Kontokurve, und alle Teilnehmer haben dieselben Kennzahlen. Für Kriterium 3 gibt es einen festen Zahlenbereich. Selbsttest 7/7. Tag 1: B und C −0,05 % (nur Kaufkosten), 67 % investiert.
- **W6 Nachlauf + W7 Vorsprung** laufen täglich um 02:50. W7 zeigt für v6, letzte 100 Runden: −0,44 % je Runde, Treffer 45 % bei nötigen 61 %. Seit der Bitvavo-Umstellung wurde noch keine Runde ganz neu begonnen und beendet, auch wegen des Internetausfalls. Das ist nicht entscheidbar.
- **Robuster Betrieb:** Fällt ein Nachtlauf aus, wiederholt er sich viermal alle 15 Minuten. W5 meldet jetzt fehlgeschlagene Aufgaben und Internetausfälle. W2 wartet auf W1.
- **Tickets** in v6 und v7 (6 Stück).

## 5 · Ampeln jetzt

| Wächter | Ampel | Warum |
|---|---|---|
| W1 Marktlage | grün | BTC seitwärts seit 9 Tagen |
| W2 Bot gegen Markt | grün | v6 14 Tage −6,7 % gegen den Korb −8,0 % |
| W3 Kosten | **gelb** | Sicherheitsabstand beim Puffer fehlt → E5 |
| W4 Kasse | **gelb** | Pflichtfelder bei Verkäufen fehlen (Befund 88, bekannt) |
| W5 Betrieb | grün | Internet wieder da, alle Aufgaben ok |
| W6 Nachlauf | grün | kein „zu früh raus“ |
| W7 Vorsprung | grün | seit Bitvavo zu wenig Runden für ein Urteil |

---

**Antwort genügt so:** „E1 b, E2 ja, E3 jede, E4 ja, E5 ja, E6 a“, oder abweichend.
