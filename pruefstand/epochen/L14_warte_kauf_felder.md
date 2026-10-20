<!-- [CLEANUP-KEEP] Pruefstand-Datei, nicht archivieren -->
# Vorab-Registrierung · v7 Epoche L14 (Nummer vorläufig) · „Warte-Kauf trägt die Kauf-Felder“ (Befund 88, Rest)

Registriert: 17.10.2026 ~22:50 Berlin, **vor dem Einspielen. Vorbereitet, NICHT eingespielt.** Gilt **nur für v7**. v6 hat keine Warte-Aufträge, sein Verkauf seit E12 ist vollständig.
Grundlage: F8 (Kleinkram selbstständig), wie Änderung 2 in `E12_L11_puffer_pflichtfelder.md`. Die Änderung betrifft nur die Aufzeichnung und **begründet allein keine Epochengrenze**. Sie wird mit der **nächsten v7-Bot-Änderung** eingespielt (Leitstand: Kleinkram bündeln, damit die Messung nicht ständig neu beginnt). Steht dann eine andere Nummer an, wird diese Datei umbenannt.

## Befund und Ursache

W4 `pflichtfelder` GELB: Bei allen 4 v7-Verkäufen seit L11 fehlen `stop_initial` und `trailing_stop_pct` (Journal `_id` 36 MANUAL_SELL, 38 TRAILING_STOP, 40 STOP_LOSS, 42 TRAILING_STOP), obwohl `felder_aus_kauf` und `decision_id` gesetzt sind.

- **[SICHER 97 %] Der L11-Block in `app.py` `_journal_add()` (:1476-1517) arbeitet richtig.** Er ist Zeichen für Zeichen derselbe wie in v6, findet den Kauf (`felder_aus_kauf` gesetzt) und erbt nur, was am Kauf steht. **Am Kauf steht in v7 aber nichts:** Alle 22 Käufe im v7-Journal (seit 26.09.) haben `stop_initial = None`, `trailing_stop_pct = None`, `tp1 = None`, `agent_id = ""` und `risk_reason = ""`. In v6 haben alle 70 Käufe seit 01.09. die Felder (seit dem Fix vom 05.08. schrittweise), z. B. `_id` 1269 mit `stop_initial` 2369,68 und `trailing_stop_pct` 1,0.
- **[SICHER 95 %] Ursache: Der bediente Warte-Auftrag baut den Kauf neu auf.** Seit `warteauftraege.aktiv = true` (12.09., Epoche E9-Freigabe) läuft jeder v7-Kauf als Warte-Auftrag: `warteauftraege.json` zählt `ausgefuehrt` 22, das sind alle 22 Journal-Käufe. Die 5 Käufe seit L11 stehen im Log sekundengenau als `Warte-Auftrag … BEDIENT` (`system.log.1`, 15.10. 08:29:56 / 16:18:27, 16.10. 11:59:04 / 17:25:43, 17.10. 05:35:28). Fundstellen in `execution/engine.py`:
  - Beim Anlegen wird nur `strategy_id`, `score`, `confidence` und `entry_reason` gemerkt, im Papierpfad `_execute_paper` (:428-433) und im Live-Pfad `_warteauftrag_live_anlegen` (:1096-1106).
  - Beim Bedienen wird ein **neuer** `DecisionIntent` gebaut, nur mit diesen vier Angaben, im Papierpfad `warteauftraege_pruefen` (:1271-1279) und im Live-Pfad `_warteauftraege_live_takt` (:1201-1212). `stop_loss`, `trailing_stop_pct`, `take_profit`, `agent_id`, `risk_reason` und `_evaluation_id` bleiben auf den Vorgaben `None` bzw. `""`.
  - `app.py` `_buche_ergebnis` (:1849/1851) schreibt `"stop_initial": intent.stop_loss` und `"trailing_stop_pct": intent.trailing_stop_pct`, also `None`.
  - Der Signal-Agent setzt beide Werte (`agents/signal_agent.py:253-254`). Die Telemetrie sieht sie bei der Entscheidung noch (`evaluations.stop_loss` gefüllt).
- **Warum v6 anders ist [SICHER 97 %]:** v6 hat keine Warteschlange (kein `warteauftraege` im Code). Der Kauf läuft sofort mit dem Original-Intent durch `_execute_approved_trade`.
- **Zweite Folge derselben Ursache [SICHER 90 %]:** Auch `_evaluation_id` geht verloren. Deshalb verknüpft `_buche_ergebnis` (:2167-2185) die Entscheidung nicht mit der Position, und zwar **still**, weil der Zweig nur bei vorhandener Kennung warnt. Belegt in `telemetrie.db`: v7 hat seit 13.10. keine APPROVED-BUY-Zeile mit `position_id`, v6 hat sie bei allen 7. Ohne diese Verknüpfung gibt es in v7 kein R-Vielfaches aus der Telemetrie.

## Änderung

| # | Datei | Art | vorher → nachher |
|---|---|---|---|
| 1 | `execution/engine.py` (CRLF), 2 Helfer vor `class ExecutionEngine` | nur Aufzeichnung | `_warte_merkangaben(intent)`: `stop_loss`, `take_profit`, `trailing_stop_pct` (als Zahl), `agent_id`, `model_version`, `risk_reason` (als Text), `evaluation_id`. Nur einfache Typen, weil die Datei JSON ist. Wirft nie, ein unbrauchbarer Wert wird weggelassen. `_warte_merkangaben_zurueck(intent, ang)` setzt die Werte am neu gebauten Kauf zurück. |
| 2 | dieselbe Datei, Anlegen (Papier :433, Live :1106) | nur Aufzeichnung | `angaben` bekommen zusätzlich `**_warte_merkangaben(intent)` |
| 3 | dieselbe Datei, Bedienen (Live :1212, Papier :1279) | nur Aufzeichnung | nach dem Bau des neuen Intents `_warte_merkangaben_zurueck(intent, ang)` |

Skript: `pruefstand/patches/patch_l14_warte_kauf_felder.py v7 --pruefen|--selbsttest|--anwenden`. Marke `BEFUND 88 WARTEKAUF 17.10.2026`, 5 Anker, Werkzeug `_patchwerkzeug.py`. v6 wird abgelehnt (Code 2).

**Warum das den Handel nicht ändert [SICHER 92 %]:** Die übertragenen Felder liest weder die Ausführung (`execution/engine.py`, `warteauftraege.py`) noch der Ausstieg (`risk/`, `runtime/`) noch Telegram (`on_buy`). Sie landen nur im Journal-Eintrag (`app.py:1846-1854`) und, über `_evaluation_id`, in `telemetrie.db` (`UPDATE evaluations SET position_id`). Der Funktionstest vergleicht Preis, Menge, Gebühr, Schlupf, Kasse, Bestand, Betrag und Order-Kennung zwischen einer alten und einer gepatchten Kopie: identisch.

**Bewusst NICHT im Patch:**
- `decision_id` am Kauf bleibt die Kennung des neu gebauten Intents. Sie steckt in der `client_order_id` der Order-Historie, sie umzustellen würde die Order-Buchung berühren. Sie passt deshalb weiter nicht zur `decision_id` in `telemetrie.db` (Nebenbefund, klein). Die Brücke Entscheidung → Position läuft nach dem Patch über `position_id`.
- Die 4 alten Verkäufe und der offene ETH-Kauf vom 17.10. 05:35 (`_id` 43) werden nicht nachgetragen. Das Journal wird nicht von Hand geändert.

## Prüfung vor dem Einspielen (17.10.2026, 22:42 Berlin)

- `--pruefen`: **BEREIT**, 5 × `execution/engine.py (CRLF)`.
- `--selbsttest`: **BESTANDEN.** Werkzeug: Marke da, Zeilenenden gleich (CRLF), übersetzbar, zweiter Lauf idempotent, Original unberührt. Funktionstest mit der echten `ExecutionEngine` auf zwei Kopien (alt/gepatcht) im Temp-Ordner. `DATA_DIR` und `TI_LOG_FILE` zeigen in die Kopie, das prüft der Treiber vor dem ersten Schritt. 12/12 OK:
  1. Reproduktion: Ohne Fix verliert der bediente Kauf Stop und Nachzieh-Abstand.
  2. Papier: Der bediente Kauf trägt `stop_loss` 97,85, `trailing_stop_pct` 1,21, `agent_id`, `risk_reason` und die Kennung.
  3. Warteschlangen-Datei: einfache JSON-Werte, `take_profit = None` wird nicht geschrieben.
  4. Die bisherigen vier Angaben sind unverändert.
  5. Handel gleich (Papier).
  6. Ein Alt-Auftrag aus der Datei von vor dem Fix wird normal bedient, die Felder bleiben leer wie bisher.
  7. Kauf ohne Stop: Es wird nichts erfunden.
  8. Unbrauchbare Werte (Text statt Zahl, Objekt): Der Auftrag wird trotzdem angelegt, die Datei bleibt lesbar.
  9. Live: Beim Anlegen werden Stop und Kennung neben `live_order_id` gemerkt.
  10. Live: Der bediente Kauf trägt die Felder.
  11. Live: Handel gleich.
  12. Die Kopien sind richtig, alt ungepatcht und neu gepatcht.
- Bot-Ordner danach geprüft: SHA-256 von `execution/engine.py`, `app.py`, `order_history.json`, `idempotency_keys.json` und `warteauftraege.json` unverändert, keine neue Sicherungsdatei.
- Nicht abgedeckt: Die Strecke vom bedienten Kauf durch `_buche_ergebnis` bis zum Verkauf ist nicht als Ganzes durchgespielt. Sie besteht aus zwei getesteten Teilen: dieser Test (der Intent trägt die Felder) und der L11-Funktionstest (der Verkauf erbt vom Kauf). `_buche_ergebnis` schreibt die Felder unverändert aus dem Intent (:1849/1851). [WAHRSCHEINLICH 90 %], dass die Strecke im Betrieb ohne weitere Lücke durchläuft. Die Messgröße L14b prüft das beim ersten echten Verkauf.

## Messgrößen und Erfolgskriterien (vorab festgelegt)

| # | Messgröße | Erfolg | Entscheidbar ab |
|---|---|---|---|
| L14a | v7-Käufe nach dem Start mit `stop_initial` und `trailing_stop_pct` (Journal) | 100 % der Käufe, deren Warte-Auftrag nach dem Start angelegt wurde | erster Kauf |
| L14b | W4 `pflichtfelder` für Verkäufe, deren Kauf (`felder_aus_kauf.kauf_zeit`) nach dem Start liegt | vollständig (≥ 95 %, wie E12c) | erster solcher Verkauf |
| L14c | APPROVED-BUY-Zeile in `telemetrie.db`, die einen bedienten Kauf ausgelöst hat, mit `position_id` | 1 Zeile mit `position_id` je bedientem Kauf (heute 0) | erster Kauf |
| L14d | Regression Handel: Füllpreis = Limitpreis, Maker-Gebühr, `warteauftraege.json` `angelegt`/`ausgefuehrt`/`verfallen` zählen weiter, W4 `orders`/`plausibel`/`gebucht_vs_kasse` grün | unverändert | 24 h nach dem Start |

## W4 beim Einspielen anpassen (Prüfstand, nicht Bot)

W4 zählt heute alle v7-Verkäufe ab `PFLICHT_AB["v7"] = 2026-10-15T09:35:57` (`waechter/w4_kasse.py:50`). Die 4 alten Verkäufe sind nicht nachtragbar, so bliebe W4 für v7 **für immer GELB**. Dasselbe gilt für den ersten Verkauf nach dem Start, wenn sein Kauf noch vor dem Start lag, z. B. ETH `_id` 43. Beim Einspielen deshalb:
- `PFLICHT_AB["v7"]` auf den L14-Start setzen.
- Für v7 nur Verkäufe prüfen, deren `felder_aus_kauf.kauf_zeit` ≥ Start ist. Ältere als „Altkauf vor L14 (nicht nachtragbar)“ nur zählen, wie heute die Verkäufe ohne Kauf in der Runde.
- Mit Selbsttest-Fall (Altkauf → Hinweis, Neukauf ohne Feld → GELB). Vorher die Wächter-Sitzung fragen, ob sie `w4_kasse.py` gerade bearbeitet.

## Einspiel-Ablauf (mit der nächsten v7-Bot-Änderung)

1. `autostart\bot_anhalten.py` für v7. Es setzt die Sperre `.BEWUSST_AUS`, damit `TI-Bots-Neustart` nicht dazwischenstartet.
2. `patch_l14_warte_kauf_felder.py v7 --pruefen` (BEREIT), dann `--anwenden`, danach `--pruefen` („bereits angewendet“).
3. `config_epochs.json` byte-genau fortschreiben (Zeilenenden prüfen): `id` `L14_warte_kauf_felder` (oder die dann gültige Nummer), `changes` `["warte_kauf_felder"]`. Gibt es eine verhaltensändernde Begleitänderung, steht dieser Punkt in deren Eintrag unter `changes`.
4. BOT-HANDBUCH Abschnitt 10.19 (vorläufig), Ticket in `tickets.txt`, BOT-HANDBUCH.pdf neu.
5. W4 anpassen (Abschnitt oben).
6. Start nur mit `schtasks /run /tn TI-Bots-Autostart`, nicht mit `bots_starten.py` aus der Sitzung, sonst beendet ein App-Update den Bot.
7. Abschnitt „Start“ in dieser Datei nachtragen, `sitzung_stand.md`.

## Abbruch / Rücknahme

- Sofort zurücknehmen (`execution/engine.py.bak_befund_88_wartekauf_17_10_2026_*`), wenn nach dem Start APPROVED-BUY-Zeilen kommen, aber `warteauftraege.json` `angelegt` nicht mehr steigt. Ebenso bei Log-Zeilen `Warte-Auftrag … nicht ausfuehrbar`, `Warte-Auftraege: Takt fehlgeschlagen` oder `… nicht gebucht`, oder wenn W4 `orders`/`plausibel` ROT wird.
- Ein Schreibfehler der Warteschlange (`_speichern` fängt ihn ab) bei neuen Feldern: prüfen. Erwartet ist er nicht, weil nur `float`/`str` geschrieben wird (Fall 8).

## Debatte

*Selbst geschrieben, keine unabhängige A10-Prüfung. Vor dem Einspielen kann A10 sie gegenlesen.*

- **Dafür:** Eine Ursache, eine Stelle. Sie schließt den Rest von Befund 88 in v7 und nebenbei die stille Lücke Entscheidung → Position in der Telemetrie. Sie berührt den Handel nicht, das ist geprüft. Alte Aufträge laufen unverändert weiter.
- **Dagegen:** `stop_initial` ist der Stop zur **Entscheidung**, gerechnet vom Marktpreis (`signal_agent.py:253`). Der Warte-Kauf füllt 0,10 % darunter (Limit). Die Risikostrecke Einstieg − Stop ist am Kauf also um 0,10 Prozentpunkte kürzer als `stop_loss_pct`. In v6 ist es ähnlich, nur umgekehrt (Füllung mit Schlupf über dem Signalpreis). Wer daraus ein R-Vielfaches rechnet, muss das wissen. Ein umgerechneter Stop wäre aber eine erfundene Zahl, die der Bot nie geplant hat.
- **Dagegen:** Mehr als die zwei W4-Felder (dazu `take_profit`, `agent_id`, `model_version`, `risk_reason`, Kennung). Es ist aber dieselbe Lücke an derselben Stelle. Sie einzeln zu schließen hieße, später noch einmal einzuspielen.

## Start

- **Eingespielt 19.10.2026** auf Svens Auftrag („Ja, spiel jetzt beide Patches ein …“), zusammen mit der Log-Warteschlange gegen Hänger (`epochen/E15_L14_log_warteschlange.md`). Eingespielt um **2026-10-19 21:00 UTC**, ohne neue Epoche. **Berichtigt 19.10. ~23:15:** Die Einträge `E15_log_warteschlange` / `L14_warte_kauf_felder` in `config_epochs.json` habe ich um 21:01 UTC angelegt und um ~21:10 UTC wieder zurückgenommen (Original aus der Sicherung, atomar; die Fassung mit Eintrag liegt als `config_epochs.json.mit_<id>_zurueckgenommen` daneben). Grund: Svens Entscheidung H1 sagt „keine Handels-Epoche“, und die Bots werten `config_epochs.json` selbst als Messgrenze aus (TERMINAL-Tab, Zahlenbuch, Vollständigkeit, Wochenbericht A). **Laufende Epoche bleibt v6 E14 / v7 L13.**
- `--anwenden` 21:00:28 UTC, Sicherung `execution/engine.py.bak_befund_88_wartekauf_17_10_2026_20261019_230028`, `execution/engine.py` CRLF 1582/1582, Marke 5×, danach `--pruefen` „bereits angewendet“. Selbsttest direkt vorher erneut bestanden (12/12).
- Handbuch 10.19, Tickets, PDF neu. Start über `TI-Bots-Autostart` 21:02 UTC, Port 5070 offen 21:03:50 UTC.
- W4 angepasst wie oben verlangt: `PFLICHT_AB["v7"]` = `KAUF_AB["v7"]` = 2026-10-19T21:00:50 (Einspielzeit). Verkäufe mit Kauf vor L14 zählen nur als Hinweis, fehlt die Kaufzeit, wird normal geprüft. Selbsttest 3 neue Fälle bestanden.
- Offen: L14a/L14c beim ersten Kauf, L14b beim ersten Verkauf eines Kaufs nach dem Start, L14d nach 24 h. Die offene BTC-Position ist ein Altkauf, ihr Verkauf bleibt ohne Felder.
