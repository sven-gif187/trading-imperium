# PROJEKT-ENTSCHEIDUNGEN — was bewusst so ist, und warum

**Angelegt 19.08.2026.** Chronologisch vom ersten Chat aufwärts, aus den
20 Sitzungen seit dem 27.07.2026 zusammengetragen.

---

## Wozu diese Datei

Am 19.08. wollte ich `GEFUNDENE-PROBLEME.md` in die Forschungsdatenbank
übertragen — es sah nach einer Lücke aus. Sven stoppte mich: *„das haben
wir doch absichtlich so gemacht glaube ich?"* Er hatte recht. Die
Trennung war eine Entscheidung vom 13.08.

Seine Frage danach war die richtige: *„wo ist dein ganzes Wissen aus
unseren Gesprächen?"*

Es war da — in den Sitzungsprotokollen, durchsuchbar. Ich hatte nur nicht
gesucht. Diese Datei ist der Auszug daraus: **jede Stelle, an der etwas
bewusst so ist, wie es ist.**

> **Eine Entscheidung, die man nicht wiederfindet, wird beim nächsten Mal
> als Fehler „repariert".**

**Regel:** Was hier steht, ist eine **Entscheidung**, kein Vorschlag. Sie
wird nicht umgeworfen, sondern angesprochen. Wer sie ändern will, holt
vorher eine Freigabe.

---

## Juli 2026

### 27.07. — Übergabe an Claude Code
*Sitzung: „Bevor du irgendetwas tust: Lies UEBERGABE-CLAUDE-CODE.md"*

- **`brain_performance.json` wird bewusst NICHT genutzt.** Sie ist
  V4-Bootstrap-verseucht (`source: v4_bootstrap`, `v6_trades_added=0` bei
  ICHIMOKU). Gilt für Cockpit und Strategiewahl gleichermaßen. *Diese
  Entscheidung taucht in vier weiteren Sitzungen auf — sie hält.*

  > **Nachtrag 24.08.2026 — der Code setzt das für die Strategiewahl nicht
  > um.** Nachgemessen: `models/brain_persistence.py:36` lädt genau diese
  > Datei, `app.py:369-372` legt sie ins Strategie-Gehirn (Logzeile:
  > *„V4-Performance geladen: 19 Strategien, 683 Trades"*), und
  > `agents/strategy_brain.py:170` vergibt daraus bis zu **+2,0 Punkte**.
  > Fünf Strategien bekommen die volle Punktzahl für Handel, den V6 nie
  > geführt hat (ICHIMOKU 69 Trades im Gehirn, **0** im sauberen Zähler).
  >
  > **Folgenlos, aber nicht wirkungslos:** Die gewählte Strategie wird nur
  > als Etikett in den Kaufwunsch geschrieben
  > (`agents/signal_agent.py:182`), sie fließt in die Kauf-Punktzahl nicht
  > ein. Der V4-Anteil beträgt 105 von 683 Trades = 15 %.
  >
  > **Für das Cockpit gilt die Entscheidung unverändert** — dort ist sie
  > umgesetzt (`cockpit_server.py:14`). Ausführlich in `BOT-HANDBUCH.md`
  > Teil 5, Abschnitt 5.3.
- **Für die finale E7-Bewertung gilt `e7_auswertung.py`**, nicht andere
  Auswertungswege.
- **Eine Parameter-Wette wurde erkannt und verworfen.** Lektion für jede
  künftige Parameteränderung: **erst walk-forward prüfen**, dann ändern.
- Zwei Werte stehen auf 33.0 — **beides nicht anfassen**.
- Fehler in den Testprotokollen sind **absichtlich provozierte
  Fehlerfälle** (kaputte Ticker, unbrauchbare Balances), kein Defekt.

### 28.07. — Projektordner aufräumen
*Sitzung: „Projektordner aufräumen"*

- **`tickets.txt` nicht anfassen, solange eine Aufräumaktion läuft.** Das
  Einfügen löst einen Schreibvorgang aus, der mit dem Aufräumen kollidiert.

### 29.07. — Audit und Optimierung
*Sitzung: „Trading bot audit and optimization"*

- Bestätigung: **`brain_performance.json` bleibt ungenutzt** (V4-verseucht).

### 30.07. — Nachkauf-Schutz
*Sitzung: „Nachkauf-Schutz und Backtest-Diskrepanz"*

- **Altlasten der Trailing-Leiter bleiben absichtlich erhalten** — unter
  anderem, dass der Faktor aus dem *aktuellen* Gewinn kommt statt aus dem
  Höchststand. *Diese Entscheidung wurde am 29.07. mit der neuen Leiter
  aufgehoben (`risk/exit_rules.py`) — sie ist die einzige hier, die
  inzwischen überholt ist.*
- Ein Wächter lief unbemerkt in der Vorgabe „schatten" und hat nie
  eingegriffen — als Muster festgehalten: **Vorgabewerte prüfen, nicht
  annehmen.**

---

## August 2026

### 04.08. — Reibungskosten und Break-even
*Sitzung: „Quantitative Analyse: Reibungskosten und Break-even"*

- **Den Bot nicht stoppen und nicht anfassen.** Stattdessen am Ende einen
  Ticket-Block vorschlagen und selbst in `tickets.txt` eintragen.
- „Nach Angst kaufen und einen Monat halten" wurde mit zwei Jahren Daten
  geprüft; instabile Merkmale wurden verworfen.

### 05.08. — Stille Frühausstiege
*Sitzung: „Multi-Strategy Bug: Silent early exits"*

- **Die Indikator-Vorgaben im Signal-Agent bleiben unangetastet**
  (`rsi=50`, `adx=20`, `ema…`) — absichtlich nicht angefasst.
- **`trade_count` wird bewusst nicht zurückgesetzt**, weil er mit dem
  Journal korrespondiert.

### 06.08. — Tab-Audit
*Sitzung: „Trading Imperium V6 Tab Audit"*

- **Der Marker `[COCKPIT-KEEP]` schützt vor `cleanup.py`.** Was ihn trägt,
  wird nicht gelöscht.
- Erneut: `brain_performance.json` bleibt draußen.

### 10.08. — balanced-Modus und Masterprompt
*Sitzungen: „balanced-Modus", „Masterprompt"*

- **Die Deckelung auf freies Cash bleibt, wie sie ist** — bewusst nicht
  geändert.
- Hintergrundjobs: **echter `pythonw`-Pfad, keine ungeschützten
  `print()`-Blöcke, keine verworfene `stderr`.** Nach dem Anlegen prüfen,
  ob wirklich etwas passiert.

### 11.08. — RR-Gate-Forensik und Lernsystem
*Sitzungen: „RR-Gate Forensik", „Lernsystem fertigstellen", „Bot-Dateianalyse"*

- **Diese drei wirken bereits — nicht ohne Grund anfassen:**
  `models/meta_voting.py`, `app.py:2056` (fließt in den Score),
  `risk/regime_profiles.py`.
- **XGBoost bleibt vorerst unangetastet**, obwohl als KRITISCH und offen
  geführt — bewusste Zurückstellung.
- **Positions-Kennungen werden nachrüstend vergeben, nicht erzwingend.**
  Grund: Positionen entstehen an mehreren Stellen; ein Zwang dort hätte
  mehr kaputt gemacht als geheilt.

### 13.08. — V6-Audit
*Sitzung: „Trading Imperium V6 Audit"*

- **Die Forschungsdatenbank ist absichtlich abgekoppelt.**
  `docs/forschungsprogramm_2026-07/forschung.db` liest nichts aus
  `data_store/`, schreibt nichts dorthin, der laufende Bot wird nicht
  angebunden. Stand eingefroren 30.07. *(Grenze A7 in `DATENBANK.md:8-13`.
  Genau diese Entscheidung wollte ich am 19.08. „reparieren".)*
- **Die vier Cockpit-Reiter sind bewusst ein isoliertes Beobachtungsdeck.**
  Keine Handelsfunktion hineinbauen.

### 17.08. — Bestandsaufnahme
*Sitzung: „NAECHSTE-SESSION.md"*

- **`backtest/optimizer.py` ist absichtlich stillgelegt** (Handbuch 4.6).
- **Vier fertige Bausteine wurden verworfen**, weil sie schlechter waren
  als die einfachste Alternative (Handbuch 8.4). Daraus die Dauerregel:
  **nichts anschließen ohne Messung.**
- **„An vielen Tagen handelt der Bot bewusst nicht" ist ein gültiges
  Messergebnis, kein Fehlschlag.**

### 18.08. — Regel-Wächter und Bot-Start
*Sitzungen: „erstelle die neue bilderreihe", „Aufgaben vor BOZ-Start", „Kurzes Update"*

- **Absichtliche Regeländerungen bestätigt man einmal** mit
  `regel_waechter_bestaetigen.py`; danach schweigt der Wächter.
- Erneut bestätigt: `brain_performance.json` bleibt aus dem Cockpit
  heraus.

### 19.08. — Tiefen-Audit (diese Sitzung)
*Sitzung: „Trading Imperium V6 Deep Audit"*

- **Sprache: Alltagssprache mit dem Fachwort in Klammern** — entschieden
  gegen einen anderslautenden Auftrag im Chat (`CLAUDE.md` §2).
- **`forschung.db` bleibt eingefroren.** Der Versuch, sie zu füllen, wurde
  abgebrochen; das Werkzeug gelöscht, bevor es lief.
- **Take-Profit bleibt vorerst abgeschaltet** (`take_profit_pct = 0.0`) —
  bis geklärt ist, ob das Absicht war (`GEFUNDENE-PROBLEME.md` 46).
- **Die Trailing-Schwelle wird nicht voreilig hochgesetzt**, obwohl sie
  rechnerisch zu niedrig steht — erst die Positionsverläufe auswerten
  (Handbuch 4.64).

---

## Wie diese Datei gepflegt wird

**Sie wird nicht von Hand nachgetragen, sondern beim Finden ergänzt.**
Wer über eine Entscheidung stolpert, die hier fehlt, trägt sie mit Datum,
Sitzung und Begründung ein.

**Suchbefehle, mit denen sich Entscheidungen finden lassen:**

```
search_session_transcripts("absichtlich")
search_session_transcripts("bewusst nicht")
search_session_transcripts("nicht anfassen")
search_session_transcripts("verworfen")
search_session_transcripts("entschieden")
```

Und für die Dokumente:

```
python schon_bekannt.py <bezeichner>
```

**Pflicht vor jeder Arbeit:** `CLAUDE.md` Abschnitt 0.
