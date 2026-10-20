## 10.16 Puffer K + 0,10 und Kauf-Felder am Verkauf (E12 / L11)

**Angelegt 15.10.2026.** Grundlage ist Svens Entscheidung E5: „Puffer 0,25 mit der nächsten Bot-Änderung“. Die Aufzeichnungs-Änderung (Befund 88) fällt unter F8. Epoche v6 **E12_puffer_pflichtfelder**, v7 **L11_puffer_pflichtfelder**, beide ab 09:35:57 UTC.

**Änderung 1, verhaltensändernd: Puffer der Nullsicherung 0,195 → 0,25 %.** In `risk/exit_rules.py` steigt `BREAKEVEN_MARGE_PCT` von 0,045 auf 0,10. Der Puffer ist K + Marge = 0,150 + 0,10.
- **Warum:** Eine Nullsicherung löst im Mittel 0,072 % unter ihrer Linie aus (p90 0,17 %), weil der Bot alle 30 s prüft und der Kurs dazwischen weiterläuft. Mit 0,045 Marge endete sie deshalb im Mittel bei −0,027 % netto. Mit 0,10 sind es etwa +0,028 %.
- **Wirkung:** klein, rund +1 $ in zwei Monaten (Prüf-Agent A5, Vorschlag V2). Die Gegenprüfung A10 sagt: „trägt“.
- Wächter W3 zeigt die Invariante I1 jetzt grün.

**Änderung 2, nur Aufzeichnung: Kauf-Felder am Verkauf (Befund 88).** Diese Felder stehen am Kauf, fehlten aber am Verkauf: `stop_initial`, `trailing_stop_pct`, `decision_id`, `signal_score`, `signal_reasons` und `active_strategy`. Bei wiederhergestellten Positionen fehlten außerdem `entry_score` und `entry_strategie`. Jetzt ergänzt `app.py` `_journal_add()` die fehlenden Felder eines Verkaufs aus dem **ersten Kauf der laufenden Runde**, also aus den Käufen derselben Münze seit ihrem letzten Verkauf. Durch `_journal_add()` laufen alle Schreibwege.
- Vorhandene Werte bleiben unangetastet.
- Die Herkunft steht im neuen Feld `felder_aus_kauf` (Kauf-`_id`, Kaufzeit, Zahl der Käufe).
- Findet sich kein Kauf, zum Beispiel beim zweiten Teil eines Teilverkaufs, bleibt das Feld leer. Es wird nichts erfunden.
- Ein Fehler dabei blockiert nie einen Trade, es gibt nur eine Warnung im Log.
- Wächter W4 prüft die Pflichtfelder ab dieser Epoche.

**Geprüft:**
- Funktionstest: Puffer = 0,25, dazu 7 Fälle für die Feld-Übernahme. Abgedeckt sind: erbt alle Felder, vorhandene Werte bleiben, nach einem Verkauf wird nichts erfunden, andere Münze, zwei Käufe, Fehler wirft nicht, Kauf unberührt.
- Zeilenenden byte-genau erhalten: v6 `app.py` CRLF, `exit_rules.py` LF; v7 umgekehrt.
- Beide Bots wurden mit `bot_anhalten.py` gestoppt (Zustand unverändert, v7 mit 1 offener BTC-Position) und um 09:36 UTC per Autostart wieder gestartet.

Skript: `pruefstand\patches\patch_e12_puffer_pflichtfelder.py`. Vorab-Registrierung: `pruefstand\epochen\E12_L11_puffer_pflichtfelder.md`. Sicherungen: `*.bak_e12_puffer_pflichtfelder_*` neben den Dateien.

**Einordnung.** Diese Änderung beseitigt einen kleinen sicheren Verlust und eine Datenlücke. Einen Vorsprung schafft sie nicht. Laut Svens Entscheidung E1 vom 15.10. läuft der Kurzfrist-Bot auf Papier als Vergleich weiter. Die Hauptarbeit gilt der langsamen Trendregel im Papier-Wettkampf (`pruefstand\epochen\S7_papier_wettkampf.md`).
