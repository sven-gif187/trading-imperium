## 10.15 Nachzieh-Start aus dem wirksamen Abstand (A5-V1)

**Angelegt 14.10.2026**, Entscheidung Sven („V1 Start aus wirksamem Abstand“). Epoche v6 **E11_trailstart_wirksam** (19:55 UTC), v7 **L10_trailstart_wirksam** (19:56 UTC).

**Befund (Prüf-Agent A5).** Der Nachzieh-Abstand im Bot ist nicht der Config-Wert 1,0 %. Wirksam ist Config × Regime (`risk/regime_profiles.py`, EARLY_BEAR ×0,85) × Leiter-Stufe × Trend-Bonus (×1,3 bei TRENDING_UP). In E7 lösten 40 von 61 Nachzieh-Stopps bei 0,85 % aus, 9 bei 1,274 %. Der Start (`TRAIL_AB_PCT`, zuletzt 1,21) war aber für 1,0 % gerechnet. Im Aufwärtstrend endete deshalb jeder Ausstieg zwischen 1,21 % und 1,52 % Hoch nach Kosten im Minus.

**Änderung.** In `risk/exit_rules.py` gibt es die neue Funktion `trail_start_pct(abstand)`, und `effektiver_trail()` startet erst ab

```
Start = (1 + K/100) / (1 − Abstand/100) − 1  + 0,05      Abstand = wirksamer Abstand, K = K_BASIS_PCT (0,150)
```

| wirksamer Abstand | Start vorher | Start jetzt |
|---|---|---|
| 0,85 % (EARLY_BEAR) | 1,21 | 1,06 |
| 1,0 % | 1,21 | 1,21 |
| 1,3 % (TRENDING_UP) | 1,21 | 1,52 |

`TRAIL_AB_PCT` bleibt als Richtwert für 1,0 % stehen, Auswerte-Skripte lesen ihn. Wird `trail_ab_pct` ausdrücklich übergeben, gilt er wie bisher.

**Geprüft.** Ein Funktionstest mit 7 Fällen ist bestanden, und am Start ergibt sich bei jedem Abstand ein Ausstieg von +0,05 % netto. Skript: `pruefstand\patches\patch_v1_trailstart_wirksam.py`. Vorab-Registrierung: `pruefstand\epochen\E11_L10_trailstart_wirksam.md`. E10–E11 bzw. L9–L10 werden gemeinsam ausgewertet, weil sie dieselbe Kostenlatte haben.

**Was die Prüf-Agenten dazu sagen.** Die Ausstiegsregeln sind insgesamt **kein messbarer Gewinnhebel** (A5: alle Varianten ±10 $ in zwei Monaten). Die Änderung beseitigt einen garantierten Verlust, sie schafft keinen Vorsprung. Laut A4 haben die **Einstiege keinen belegten Vorsprung gegen Zufall**, das Brutto entspricht der Marktdrift. Berichte: `pruefstand\berichte\2026-10-14_ausstieg.md`, `2026-10-14_einstieg.md`.
