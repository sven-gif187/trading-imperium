"""
Trading Imperium V5 – XGBoost Signal Model
Einfaches ML-Modell das aus historischen OHLCV-Daten ein Kauf/Verkauf-Signal lernt.
Nutzt scikit-learn GradientBoosting (XGBoost-aehnlich, keine extra Library noetig).
"""
import numpy as np
import pandas as pd
import os
import json
import time
import pickle
from typing import Dict, Tuple, Optional
from config.settings import DATA_DIR
from core.logger import log

MODEL_DIR = os.path.join(DATA_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)


class XGBoostSignalModel:
    """ML-Modell fuer Kauf/Verkauf-Signale basierend auf OHLCV + Indikatoren."""

    FEATURES = [
        "RSI", "ADX", "MACD", "MACD_hist", "ATR",
        "volume_ratio", "close_to_ema20", "volatility", "high_low_range",
        "returns", "StochRSI", "TSI",
        # Zusaetzliche Features
        "rsi_slope",        # RSI Steigung (Momentum des Momentums)
        "price_vs_bb",      # Preis relativ zu Bollinger Baendern
        "volume_trend",     # Volumen-Trend (steigend/fallend)
    ]

    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.version = "xgb_v0"
        self.feature_importance = {}
        self.training_stats = {}
        # [GEFUNDENE-PROBLEME #4] Die Merkmale, auf die dieses Modell
        # TATSAECHLICH trainiert wurde. FEATURES oben ist nur die Wunschliste -
        # beim Training faellt heraus, was im DataFrame fehlt (StochRSI/TSI).
        # predict() muss dieselbe Liste in derselben Reihenfolge benutzen,
        # sonst passt die Spaltenzahl nicht und der Aufruf scheitert still.
        self.trained_features = []
        self._merkmal_warnung_gezeigt = False

    def prepare_features(self, df) -> pd.DataFrame:
        """Berechnet alle Features aus einem OHLCV DataFrame."""
        d = df.copy()

        # Basis-Features (sollten schon vorhanden sein)
        if "RSI" not in d.columns:
            import pandas_ta as ta
            d["RSI"] = ta.rsi(d["Close"], length=14)

        # Zusaetzliche Features
        d["returns"] = d["Close"].pct_change()
        d["volatility"] = d["returns"].rolling(14).std()
        d["volume_sma"] = d["Volume"].rolling(20).mean()
        d["volume_ratio"] = d["Volume"] / (d["volume_sma"] + 1e-10)
        d["high_low_range"] = (d["High"] - d["Low"]) / (d["Close"] + 1e-10)

        ema20 = d["Close"].rolling(20).mean()
        d["close_to_ema20"] = (d["Close"] - ema20) / (ema20 + 1e-10)

        # RSI Slope (Steigung der letzten 5 RSI-Werte)
        if "RSI" in d.columns:
            d["rsi_slope"] = d["RSI"].diff(5)
        else:
            d["rsi_slope"] = 0

        # Preis vs Bollinger Baender
        bb_mid = d["Close"].rolling(20).mean()
        bb_std = d["Close"].rolling(20).std()
        d["price_vs_bb"] = (d["Close"] - bb_mid) / (bb_std + 1e-10)

        # Volume Trend
        d["volume_trend"] = d["Volume"].rolling(5).mean() / (d["Volume"].rolling(20).mean() + 1e-10)

        return d

    def predict(self, df_or_row) -> Tuple[float, str]:
        """
        Gibt (score, reason) zurueck.
        Score: 0.0-1.0 (0=stark sell, 0.5=neutral, 1=stark buy)
        """
        if not self.is_trained or self.model is None:
            return self._predict_fallback(df_or_row)

        # [GEFUNDENE-PROBLEME #4] Ohne bekannte Trainings-Merkmalsliste NICHT
        # raten: frueher wurden hier stur alle 15 FEATURES gebaut, waehrend die
        # gespeicherten Modelle nur 13 kennen. Der Aufruf scheiterte dadurch bei
        # JEDEM Takt und fiel still in den RSI/ADX-Notbehelf zurueck - der sah
        # von aussen aus wie eine ML-Vorhersage, war aber keine.
        merkmale = self.trained_features or []
        if not merkmale:
            if not self._merkmal_warnung_gezeigt:
                self._merkmal_warnung_gezeigt = True
                log.warn("XGB", "Merkmalsliste des Modells unbekannt - "
                                "Notbehelf statt ML-Vorhersage")
            return self._predict_fallback(df_or_row)

        try:
            if isinstance(df_or_row, pd.DataFrame):
                row = df_or_row.iloc[-1]
            else:
                row = df_or_row

            features = []
            for f in merkmale:
                val = row.get(f, 0) if isinstance(row, dict) else getattr(row, f, row.get(f, 0) if hasattr(row, 'get') else 0)
                features.append(0 if pd.isna(val) else float(val))

            X = np.array(features).reshape(1, -1)

            # Skalieren wenn Scaler vorhanden
            if self.scaler:
                X = self.scaler.transform(X)

            proba = self.model.predict_proba(X)[0]
            score = float(proba[1])  # Wahrscheinlichkeit fuer "BUY"

            # Top 3 wichtigste Features fuer Erklaerung
            top_features = sorted(self.feature_importance.items(),
                                  key=lambda x: x[1], reverse=True)[:3]
            reason = f"XGB: {score:.2f} | Top: {', '.join(f[0] for f in top_features)}"

            return score, reason

        except Exception as e:
            log.warn("XGB", f"Predict: {e}")
            return self._predict_fallback(df_or_row)

    def _predict_fallback(self, row) -> Tuple[float, str]:
        """Regelbasierter Fallback."""
        try:
            if isinstance(row, pd.DataFrame):
                row = row.iloc[-1]
            rsi = float(row.get("RSI", 50))
            adx = float(row.get("ADX", 20))
            score = 0.5
            if rsi < 35: score += 0.15
            if rsi > 70: score -= 0.15
            if adx > 25: score += 0.05
            return min(max(score, 0), 1), "Fallback (kein ML-Modell)"
        except Exception:
            return 0.5, "Fallback"

    # [GEFUNDENE-PROBLEME #18] EINE Definition, was "Gewinn" heisst.
    #
    # Vorher stand die Schwelle an zwei Stellen: auto_retrain.py:51 rechnete
    # mit 1 %, xgboost_model ueberschrieb sie still mit 0,5 %. Es galt immer
    # die zweite - und das war die FALSCHE.
    #
    # WARUM 0,5 % NICHT GEHT (nachgerechnet 12.08.2026): Eine Handelsrunde
    # kostet auf Bybit EU 0,60 % (Szenario K-BASIS: 2x0,25 % Taker +
    # 2x0,05 % Slippage, siehe docs/forschungsprogramm_2026-07/). Ein Ziel von
    # 0,5 % liegt DARUNTER. Selbst ein perfekt getroffenes Signal haette also
    # 0,50 % - 0,60 % = -0,10 % ergeben. Das ist kein Modellproblem, sondern
    # die falsche Frage: kein Training macht ein Ziel profitabel, das unter
    # den Kosten liegt.
    #
    # WARUM 1,0 %: liegt mit 0,4 Prozentpunkten Abstand ueber K-BASIS, also
    # traegt ein Treffer die Kosten auch bei etwas Pech. Es ist zugleich
    # genau der Wert, den auto_retrain.py von Anfang an hatte, bevor er
    # ueberschrieben wurde.
    #
    # WAS DAS NICHT LOEST: Bei 1,0 % steigt der Preis nur in 8,5 % der Faelle
    # so weit. Im Zukunftstest bleiben damit rund 22 positive Faelle - viel
    # zu wenig, um die Guete des Modells zu beurteilen. Die Frage "hilft die
    # KI?" ist mit 3 Muenzen x 500 Kerzen NICHT ENTSCHEIDBAR. Deshalb bleibt
    # das Modell im Notizbuch-Modus (Teil 4.8), bis mehr Daten da sind.
    #
    # Sinkt die Zielboerse je auf Limit-Orders (K-MAKER 0,26 %), darf diese
    # Zahl wieder sinken - vorher NICHT.
    LABEL_SCHWELLE = 0.010      # Preis muss in 5 Kerzen um >1,0 % steigen

    def train(self, df, min_samples=200, test_size=0.2, label_schwelle=None,
              speichern=True):
        """Trainiert das XGBoost-Modell.

        Akzeptiert einen DataFrame mit OHLCV-Spalten. Enthaelt er eine Spalte
        "coin" mit mehreren Muenzen, werden Merkmale und Label JE MUENZE
        gerechnet (sonst laufen die Fensterrechnungen ueber die Grenzen).
        Eine Zeitspalte ("ts"/"timestamp"/"Datetime"/"Date") schaltet den
        zeitlichen Holdout frei - ohne sie wird bei mehreren Muenzen
        abgebrochen, weil ein Zeilen-Schnitt dort nur die letzte Muenze
        abtrennen wuerde.

        Returns: True bei Erfolg, False bei Fehler.
        """
        label_schwelle = (self.LABEL_SCHWELLE if label_schwelle is None
                          else float(label_schwelle))
        # FIX BUG 4: Sichere None/Length-Checks (kein 'if df:' das numpy crasht)
        # Wichtig: NIEMALS 'if X' oder 'if df' direkt - das crasht bei numpy!
        if df is None:
            log.warn("XGB", "train() mit None aufgerufen")
            return False

        # Pruefe ob es numpy array ist (auto_retrain alter Bug)
        if isinstance(df, np.ndarray):
            log.warn("XGB", "train() bekam numpy-Array statt DataFrame - bitte DataFrame uebergeben!")
            return False

        # Pruefe Laenge sicher (DataFrame oder Liste)
        try:
            data_len = len(df)
        except TypeError:
            log.warn("XGB", f"train() Input hat keine Laenge: {type(df).__name__}")
            return False

        if data_len < min_samples:
            log.warn("XGB", f"Zu wenig Daten ({data_len}/{min_samples})")
            return False

        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import train_test_split

            # [GEFUNDENE-PROBLEME #18, 12.08.2026] Merkmale und Label JE MUENZE
            # berechnen, nicht ueber den ganzen Stapel.
            #
            # WAS VORHER PASSIERTE: auto_retrain.py klebt fuenf Muenzen mit
            # pd.concat(ignore_index=True) zu EINER Tabelle zusammen. Danach
            # liefen hier rolling(14)/rolling(20)/pct_change()/diff(5) und das
            # Label mit shift(-5) ueber die Muenz-Grenzen hinweg: die letzten
            # BTC-Zeilen wurden mit den ersten ETH-Zeilen verrechnet. Das Label
            # sagte an der Naht "BTC steigt", gemeint war der ETH-Kurs.
            #
            # Gibt es eine Spalte "coin", wird jede Muenze fuer sich gerechnet
            # und erst danach gestapelt. Fehlt sie (Einzel-Muenze), bleibt es
            # beim alten Weg - dann ist er ja richtig.
            df = df.copy()
            if "coin" in df.columns and df["coin"].nunique() > 1:
                teile = []
                for muenze, block in df.groupby("coin", sort=False):
                    block = self.prepare_features(block.copy())
                    block["future_return"] = block["Close"].shift(-5) / block["Close"] - 1
                    block["label"] = (block["future_return"] > label_schwelle).astype(int)
                    teile.append(block)
                df = pd.concat(teile, ignore_index=True)
                log.info("XGB", f"Merkmale je Muenze berechnet "
                                f"({len(teile)} Muenzen, keine Grenzverletzung)")
            else:
                df = self.prepare_features(df)
                df["future_return"] = df["Close"].shift(-5) / df["Close"] - 1
                df["label"] = (df["future_return"] > label_schwelle).astype(int)
            df = df.dropna()

            # Feature-Matrix
            available_features = [f for f in self.FEATURES if f in df.columns]

            # FIX: Sichere Pruefung auf Liste (nicht numpy)
            if len(available_features) < 3:
                log.warn("XGB", f"Zu wenig Features: {len(available_features)} (min 3)")
                return False

            X = df[available_features].fillna(0).values
            y = df["label"].values

            # FIX: Sichere numpy-Pruefung mit explizitem .size oder len()
            if X.size == 0 or len(X) < min_samples:
                log.warn("XGB", f"Nach Cleanup nur {len(X)} Samples")
                return False

            # Pruefe Label-Balance (beide Klassen muessen da sein!)
            unique_labels = np.unique(y)
            if len(unique_labels) < 2:
                log.warn("XGB", f"Nur eine Klasse in Labels: {unique_labels} - kein Training moeglich")
                return False

            # [GEFUNDENE-PROBLEME #18] ZEITLICHER Holdout statt Zeilen-Schnitt.
            #
            # WAS VORHER PASSIERTE: train_test_split(shuffle=False) nimmt die
            # letzten 20 % der ZEILEN. Bei gestapelten Muenzen sind das nicht
            # die spaetesten Kerzen, sondern schlicht die LETZTE MUENZE. Der
            # Bot testete also "gelernt auf BTC+ETH+SOL+ADA, geprueft auf DOT" -
            # und nannte das Ergebnis "Test-Genauigkeit". Ein Modell, das die
            # Zukunft vorhersagen soll, wurde nie gegen die Zukunft geprueft.
            #
            # Jetzt: Schnitt an einem ZEITPUNKT. Alles davor lernt, alles
            # danach prueft - ueber alle Muenzen gleichzeitig. Das ist die
            # Frage, die zaehlt: taugt das Modell fuer Kerzen, die es noch nie
            # gesehen hat?
            zeit_spalte = next((s for s in ("ts", "timestamp", "Datetime", "Date")
                                if s in df.columns), None)
            if zeit_spalte is not None:
                zeiten = pd.to_datetime(df[zeit_spalte], errors="coerce", utc=True)
                if zeiten.notna().all():
                    grenze = zeiten.quantile(1.0 - test_size)
                    ist_test = (zeiten > grenze).values
                    if ist_test.sum() >= 20 and (~ist_test).sum() >= min_samples // 2:
                        X_train, X_test = X[~ist_test], X[ist_test]
                        y_train, y_test = y[~ist_test], y[ist_test]
                        self._holdout_art = f"zeitlich ab {grenze:%Y-%m-%d %H:%M}"
                    else:
                        zeit_spalte = None      # zu duenn -> Rueckfall unten
                else:
                    zeit_spalte = None

            if zeit_spalte is None:
                # Rueckfall: nur zulaessig, wenn EINE Muenze vorliegt - dann
                # sind die Zeilen chronologisch und der Schnitt ist echt.
                mehrere = "coin" in df.columns and df["coin"].nunique() > 1
                if mehrere:
                    log.warn("XGB", "Kein Zeitstempel bei mehreren Muenzen - "
                                    "ein Zeilen-Schnitt wuerde nur die letzte "
                                    "Muenze abtrennen. Training abgebrochen.")
                    return False
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, shuffle=False)
                self._holdout_art = "zeilenweise (eine Muenze, chronologisch)"

            # Skalierung
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Training
            self.model = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                min_samples_split=10,
                random_state=42,
            )
            self.model.fit(X_train_scaled, y_train)

            # [GEFUNDENE-PROBLEME #18] Ehrliche Bewertung statt nackter
            # Trefferquote.
            #
            # WARUM DAS NOETIG IST: Gemeldet wurde bisher nur "test_acc".
            # Am 05.08. stand dort 71,4 % - klingt gut. Nur waren 22,6 % der
            # Faelle positiv, also haette "immer nein sagen" 77,4 % erreicht.
            # Das Modell war SCHLECHTER als die einfachste denkbare Regel, und
            # die Zahl allein verriet das nicht. Deshalb steht die Trivial-Latte
            # ab jetzt IMMER daneben.
            train_acc = self.model.score(X_train_scaled, y_train)
            test_acc = self.model.score(X_test_scaled, y_test)

            anteil_positiv = float(y_test.mean()) if len(y_test) else 0.0
            trivial_acc = max(anteil_positiv, 1.0 - anteil_positiv)
            schlaegt_trivial = bool(test_acc > trivial_acc)

            praez = ausbeute = f1 = auc = None
            try:
                from sklearn.metrics import (precision_score, recall_score,
                                             f1_score, roc_auc_score)
                y_pred = self.model.predict(X_test_scaled)
                praez = float(precision_score(y_test, y_pred, zero_division=0))
                ausbeute = float(recall_score(y_test, y_pred, zero_division=0))
                f1 = float(f1_score(y_test, y_pred, zero_division=0))
                if len(np.unique(y_test)) > 1:
                    # AUC ist der ehrlichste Einzelwert: er misst, ob das Modell
                    # gute von schlechten Zeitpunkten TRENNT, unabhaengig von
                    # der Schwelle. 0,5 = Muenzwurf.
                    auc = float(roc_auc_score(
                        y_test, self.model.predict_proba(X_test_scaled)[:, 1]))
            except Exception as e:
                log.warn("XGB", f"Zusatz-Kennzahlen: {str(e)[:60]}")

            # Feature Importance
            self.feature_importance = {
                available_features[i]: round(float(imp), 4)
                for i, imp in enumerate(self.model.feature_importances_)
            }

            self.trained_features = list(available_features)
            self.is_trained = True
            self.version = f"xgb_{int(time.time()) % 100000}"
            self.training_stats = {
                "version": self.version,
                "samples": len(X),
                "features": len(available_features),
                "train_acc": round(train_acc, 3),
                "test_acc": round(test_acc, 3),
                # [GEFUNDENE-PROBLEME #18] Die Zahlen, die das Urteil tragen
                "trivial_acc": round(trivial_acc, 3),
                "schlaegt_trivial": schlaegt_trivial,
                "auc": round(auc, 3) if auc is not None else None,
                "precision": round(praez, 3) if praez is not None else None,
                "recall": round(ausbeute, 3) if ausbeute is not None else None,
                "f1": round(f1, 3) if f1 is not None else None,
                "holdout": getattr(self, "_holdout_art", "?"),
                "label_schwelle": label_schwelle,
                "label_balance": f"{y.mean():.1%} positiv",
                "time": time.strftime("%Y-%m-%d %H:%M"),
            }

            # Ergebnis so ins Log, dass man es nicht falsch lesen KANN.
            urteil = ("schlaegt die Trivial-Latte" if schlaegt_trivial
                      else "SCHLECHTER als 'immer nein sagen'")
            log.info("XGB", f"Trainiert ({len(X)} Zeilen, "
                            f"{len(available_features)} Merkmale, "
                            f"Holdout {self.training_stats['holdout']})")
            log.info("XGB", f"  Test {test_acc:.1%} gegen Trivial-Latte "
                            f"{trivial_acc:.1%} -> {urteil}")
            if auc is not None:
                auc_text = ("besser als Muenzwurf" if auc > 0.55 else
                            "praktisch Muenzwurf" if auc >= 0.45 else
                            "SCHLECHTER als Muenzwurf")
                log.info("XGB", f"  AUC {auc:.3f} ({auc_text}), "
                                f"Train {train_acc:.1%}")
            if train_acc - test_acc > 0.15:
                log.warn("XGB", f"  Auswendig gelernt: Train {train_acc:.1%} "
                                f"gegen Test {test_acc:.1%} - "
                                f"{train_acc - test_acc:.1%} Abstand")

            # Speichern - mit speichern=False fuer Tests.
            #
            # [12.08.2026] Diese Bremse fehlte und hat sofort zugeschlagen:
            # Beim Pruefen des neuen Trainingspfads legte jeder Testlauf ein
            # echtes Modell in data_store/models/ ab. Da load() das NEUESTE
            # nimmt, haette der Bot beim naechsten Start ein Modell geladen,
            # das auf erfundenen Zufallsdaten trainiert wurde. Aufgeraeumt,
            # aber besser: gar nicht erst entstehen lassen.
            if speichern:
                self._save()
            else:
                log.info("XGB", "Testlauf - Modell NICHT gespeichert")
            return True

        except ImportError:
            log.warn("XGB", "scikit-learn fehlt: pip install scikit-learn")
            return False
        except Exception as e:
            log.error("XGB", f"Training: {e}")
            return False

    def _save(self):
        try:
            path = os.path.join(MODEL_DIR, f"xgboost_{self.version}.pkl")
            with open(path, "wb") as f:
                # [GEFUNDENE-PROBLEME #4] trained_features statt FEATURES:
                # gespeichert werden muss, worauf wirklich trainiert wurde.
                pickle.dump({"model": self.model, "scaler": self.scaler,
                            "features": self.trained_features,
                            "importance": self.feature_importance}, f)
            meta = os.path.join(MODEL_DIR, "xgboost_meta.json")
            with open(meta, "w") as f:
                json.dump(self.training_stats, f, indent=2)
        except Exception as e:
            log.warn("XGB", f"Speichern: {e}")

    def load(self, version=None):
        """Laedt ein gespeichertes Modell."""
        try:
            if version:
                path = os.path.join(MODEL_DIR, f"xgboost_{version}.pkl")
            else:
                # [GEFUNDENE-PROBLEME #4] Neuestes finden - nach Datum, NICHT
                # nach Namen. sorted(files)[-1] sortierte alphabetisch: "94240"
                # steht hinter "65358", also wurde das Modell vom 12. Mai
                # geladen, waehrend das vom 5. August unbenutzt danebenlag.
                files = [f for f in os.listdir(MODEL_DIR) if f.startswith("xgboost_") and f.endswith(".pkl")]
                if not files:
                    return False
                path = max((os.path.join(MODEL_DIR, f) for f in files),
                           key=os.path.getmtime)
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.model = data["model"]
            self.scaler = data.get("scaler")
            self.feature_importance = data.get("importance", {})

            # [GEFUNDENE-PROBLEME #4] Merkmalsliste zurueckholen und gegen das
            # Modell pruefen. Aeltere Dateien haben hier faelschlich die volle
            # FEATURES-Wunschliste gespeichert (15) statt der trainierten (13) -
            # in dem Fall die Reihenfolge aus der Wichtigkeits-Tabelle nehmen,
            # die beim Training aus genau diesen Spalten gebaut wurde.
            erwartet = getattr(self.model, "n_features_in_", None)
            merkmale = list(data.get("features") or [])
            if erwartet and len(merkmale) != erwartet:
                aus_importance = list(self.feature_importance.keys())
                merkmale = aus_importance if len(aus_importance) == erwartet else []
            self.trained_features = merkmale

            # [GEFUNDENE-PROBLEME #4] Version aus dem Dateinamen uebernehmen.
            # Vorher blieb sie nach dem Laden auf "xgb_v0" stehen - jede
            # Protokollzeile und die Dashboard-Anzeige nannten damit eine
            # Version, die es nicht gab.
            dateiname = os.path.basename(path)
            if dateiname.startswith("xgboost_") and dateiname.endswith(".pkl"):
                self.version = dateiname[len("xgboost_"):-len(".pkl")]

            self.is_trained = True
            if not merkmale:
                log.warn("XGB", f"Modell geladen, aber Merkmalsliste passt "
                                f"nicht ({erwartet} erwartet) - keine "
                                f"Vorhersage moeglich: {os.path.basename(path)}")
            else:
                log.info("XGB", f"Modell geladen: {os.path.basename(path)} "
                                f"({len(merkmale)} Merkmale)")
            return True
        except Exception as e:
            log.warn("XGB", f"Laden: {e}")
            return False

    def get_status(self):
        return {
            "trained": self.is_trained,
            "version": self.version,
            "stats": self.training_stats,
            "top_features": dict(sorted(self.feature_importance.items(),
                                       key=lambda x: x[1], reverse=True)[:5]),
        }
