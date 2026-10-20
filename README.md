# Trading Imperium – ein ehrlich dokumentierter Krypto-Bot (Papierhandel)

> **Kein Anlagerat. Nur Papierhandel. Dieser Bot ist nach Kosten bisher NICHT profitabel.**
> Wer ihn mit echtem Geld laufen lässt, tut das auf eigenes Risiko – Totalverlust ist möglich.

Trading Imperium ist ein selbst gebauter Handels-Bot für **BTC, ETH und SOL gegen USDC**, dazu ein
**Prüfstand**, der jeden Schritt des Bots misst, und ein **Strategie-Labor**. Das Projekt wird seit
Monaten öffentlich und ehrlich dokumentiert (TikTok: **@make.a.better_world**) – mit allen Fehlern.
Jetzt ist es Open Source, damit wir es **gemeinsam** zum Ziel bringen.

**Das Ziel:** nach allen Kosten profitabel – Marktwechsel nie verpassen – kein Problem bleibt unbemerkt.

---

## Ehrlicher Stand (Oktober 2026)

| Messung | Ergebnis |
|---|---|
| Bot v6, Epoche E7 (13.08.–13.10.2026), 136 Runden, 500 $ Papiergeld | vor Kosten **+75,51 $**, Gebühren **109,62 $**, nach Kosten **−34,11 $** |
| Markt im selben Zeitraum | BTC +31 %, ETH +33 %, SOL +42 % |
| Einstiege gegen Zufall (Prüf-Agent A4, Monatsmessung) | kein belegter Vorsprung – jeder 95-%-Bereich schließt die 0 ein |
| Seit dem Börsenwechsel zu Bitvavo USDC (14.10.) | Kosten je Runde 0,505 % → **0,150 %**, aber im Seitwärtsmarkt verliert der Bot schon **vor** Kosten |
| Papier-Wettkampf seit 15.10.2026 | Bot gegen zwei langsame Trendregeln und „BTC über der 200-Tage-Linie“ – Urteil frühestens Mitte Januar 2027 |
| In Arbeit | „Marktlage-Tor“: der Kurzfrist-Bot kauft nur noch, wenn die Marktlage *Aufwärts* ist |

Alle Zahlen sind Kassenrechnungen aus dem Handelsjournal und im Prüfstand nachvollziehbar
(`pruefstand/berichte`, `pruefstand/epochen`). Wir veröffentlichen sie, weil sie stimmen – nicht weil sie gut sind.

---

## Was drin ist

```
bot_v6/        Bot v6 – Hauptbot, kauft über Signal-Abstimmung, verkauft über Verlustbremse,
               Nullsicherung und Nachzieh-Stopp. Handbuch: bot_v6/BOT-HANDBUCH.md (über 7.000 Zeilen)
bot_v7/        Bot v7 – Weiterentwicklung mit Warte-Aufträgen und der Fraktal-Strategie (Zonen aus 1h + 4h)
pruefstand/    Der Prüfstand: misst die Bots, ändert sie nie selbst
  waechter/    7 Wächter (W1 Marktlage, W2 Bot gegen Markt, W3 Kosten, W4 Kasse, W5 Betrieb,
               W6 Kurs nach dem Verkauf, W7 Vorsprung) – laufen als Windows-Aufgaben
  .claude/agents/  11 KI-Prüfer (A1 Leitstand … A10 Advocatus Diaboli, A11 Chronist)
  labor/       Strategie-Labor: Rückrechnung seit 2017 und täglicher Papier-Wettkampf
  epochen/     Vorab-Registrierungen: jede Regeländerung mit Hypothese, Messgrößen, Erfolgskriterien
  patches/     Wie Änderungen eingespielt werden: Anker, Sicherung, Zeilenenden, Funktionstest
  berichte/    Prüfberichte, Lageberichte, Monatsmessung
  MASTERPROMPT_AGENTEN.md   Regeln des Prüfstands
```

Jeder Bot hat zwei Bücher: **BOT-HANDBUCH.md** (was der Bot tut und warum) und **ENTWICKLERHANDBUCH.md**
(Chronik jeder Änderung). Die Bots schreiben dort selbst mit.

---

## Schnellstart (Bot, Papierhandel, Windows)

1. Python 3.13 installieren (oder `bot_v6/EINRICHTUNG_0_PYTHON_313_HOLEN.bat`).
2. Pakete: `pip install -r bot_v6/requirements.txt` (oder `EINRICHTUNG_2_PAKETE_INSTALLIEREN.bat`).
3. Optional: `.env.example` nach `.env` kopieren (Telegram usw.). **Keine Börsen-Schlüssel nötig** –
   im Papiermodus liest der Bot nur öffentliche Kurse.
4. Start: `bot_v6/start_bot.bat` oder `python app.py` im Ordner `bot_v6`. Im Fenster auf **STARTEN** klicken.
5. `data_store/config.json` steht auf `"mode": "paper"`. **Lass das so.**

Der Bot legt seine Daten (Journal, Datenbanken, Logs) beim ersten Start in `data_store/` an – die sind
bewusst nicht im Repo.

**Prüfstand:** Die Skripte sind für Windows und Svens Ordner gebaut. Pfade stehen in
`pruefstand/instanzen.json` und in einigen Skriptköpfen (als `C:\Users\<BENUTZER>\Desktop\…`).
Die Pfade konfigurierbar zu machen, ist eine der ersten Aufgaben, bei denen Hilfe willkommen ist.

---

## Mitmachen – genau dafür ist das hier

Wir suchen Leute, die **Fehler finden, nachrechnen und Ideen sauber testen**. Gute erste Aufgaben:

- **Lauffähig machen:** Installation auf einem frischen Rechner nachstellen (Windows, Linux, macOS) und
  aufschreiben, was fehlt. Pfade im Prüfstand konfigurierbar machen.
- **Nachrechnen:** Unsere Zahlen mit eigenem Code prüfen (`pruefstand/skripte/runden_lib.py` als Einstieg).
- **Fehler finden:** Code lesen, Befunde mit Fundstelle als Issue melden.
- **Ideen testen:** Neue Regeln **nur als Messplan** vorschlagen (siehe CONTRIBUTING.md) – nicht als „bei mir lief es gut“.

Bitte zuerst **CONTRIBUTING.md** lesen. Die wichtigste Regel: **Keine Regeländerung ohne Vorab-Plan und Messung.**

---

## Haftungsausschluss

Dieses Projekt ist **keine Anlageberatung** und **kein Finanzprodukt**. Es läuft im **Papierhandel**
(simuliert, ohne echtes Geld). Vergangene Ergebnisse – ob echt oder zurückgerechnet – sagen nichts über die
Zukunft. Krypto-Handel kann zum Totalverlust führen. Die Software wird ohne jede Gewährleistung
bereitgestellt (siehe LICENSE).

## Lizenz

**GPL-3.0** – du darfst den Code nutzen, ändern und weitergeben. Veränderte Fassungen müssen ebenfalls unter
der GPL-3.0 offen bleiben. So bleibt es ein gemeinsames Projekt. Volltext: `LICENSE`.

Gebaut von Sven (Sam'sWorld, @make.a.better_world) zusammen mit Claude (Anthropic).

---

## English summary

Trading Imperium is a self-built crypto trading bot (BTC/ETH/SOL vs. USDC) with a measurement rig
(“Prüfstand”: 7 watchers, 11 AI review agents) and a strategy lab. **Paper trading only. Not profitable after
costs so far** (v6, 136 rounds: +75.51 $ gross, −109.62 $ fees, −34.11 $ net). Documentation is in German.
Contributions welcome – especially reproducing results, finding bugs and testing ideas with a pre-registered
measurement plan (see CONTRIBUTING.md). Not financial advice. License: GPL-3.0.
