"""
Trading Imperium V5 – Fee Calculator
Realistische Gebuehren pro Exchange. Beruecksichtigt Maker/Taker und VIP-Level.
"""
from typing import Dict

# Gebuehren-Tabellen (Standard-Level, ohne Rabatte)
#
# [KORREKTUR 11.08.2026] bybit stand hier auf taker 0,10 % - falsch fuer den
# EU-Spot-Markt, auf dem gehandelt werden soll. Der Eigentuemer hat die
# offizielle Bybit-EU-Gebuehrenseite selbst geprueft (Help-Center "Bybit Spot
# Fees Explained", Stand 08.03.2026): Maker 0,10 % / Taker 0,25 % je Seite.
# Quelle und Kostenmodell:
# docs/forschungsprogramm_2026-07/02_EXPERIMENT-REGISTER_v1.1.md
#
# NIE aus ccxt uebernehmen: ccxt.bybit().fees['trading'] meldet
# maker 0,01 % / taker 0,075 % - fuer EU-Spot schlicht falsch. Eine zu
# guenstige Gebuehrenannahme laesst jede Auswertung besser aussehen als die
# Wirklichkeit, und zwar still.
EXCHANGE_FEES = {
    "binance":    {"maker": 0.10, "taker": 0.10, "bnb_discount": 0.075},
    "coinbase":   {"maker": 0.40, "taker": 0.60},
    "kraken":     {"maker": 0.16, "taker": 0.26},
    # [EINHEITSGEBUEHR 05.10.2026] Bybit EU seit 05.10.2026 11:00 UTC Einheitsgebuehr
    # 0,25 % fuer VIP 0, kein Maker-Rabatt (Trading-Fee-Structure, geprueft 14.10.2026).
    "bybit":      {"maker": 0.25, "taker": 0.25},   # EU-Spot, geprueft
    # [KOSTENLATTE BITVAVO 14.10.2026] Bitvavo USDC-Maerkte, Kategorie B: 0,05 % Maker und Taker
    # (bitvavo.com/en/fees, geprueft 14.10.2026). Zielboerse seit Entscheidung Sven 14.10.
    "bitvavo_usdc": {"maker": 0.05, "taker": 0.05},
    "okx":        {"maker": 0.08, "taker": 0.10},
}


class FeeCalculator:
    """Berechnet realistische Trading-Gebuehren."""

    def __init__(self, exchange="binance", custom_fee_pct=None):
        self.exchange = exchange
        self.fees = EXCHANGE_FEES.get(exchange, EXCHANGE_FEES["binance"])
        self.custom_fee = custom_fee_pct
        self.total_fees_paid = 0.0

    def calculate(self, amount_usd, order_type="taker"):
        """Berechnet Gebuehr fuer einen Trade."""
        if self.custom_fee is not None:
            fee_pct = self.custom_fee
        else:
            fee_pct = self.fees.get(order_type, self.fees.get("taker", 0.1))
        fee = amount_usd * (fee_pct / 100)
        self.total_fees_paid += fee
        return round(fee, 4)

    def calculate_roundtrip(self, amount_usd):
        """Gebuehren fuer Kauf + Verkauf zusammen."""
        buy_fee = self.calculate(amount_usd, "taker")
        sell_fee = self.calculate(amount_usd, "taker")
        return round(buy_fee + sell_fee, 4)

    def breakeven_pct(self):
        """Wie viel % muss ein Trade mindestens machen um Fees zu decken?"""
        fee = self.fees.get("taker", 0.1)
        return round(fee * 2, 3)  # Kauf + Verkauf

    def get_status(self):
        return {"exchange": self.exchange, "fees": self.fees,
                "total_paid": round(self.total_fees_paid, 2),
                "breakeven": self.breakeven_pct()}
