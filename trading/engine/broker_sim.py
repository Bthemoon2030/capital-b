"""Gesimuleerde broker: long-only, geen leverage, geen shorts.

Bewuste beperkingen voor een leerrekening. Leverage en shorts toevoegen kan
later, maar ze verbergen fouten in de strategie achter grotere getallen.
"""

from __future__ import annotations

from datetime import datetime

from .costs import CostModel
from .types import Fill


class SimulatedBroker:
    def __init__(
        self,
        starting_cash: float,
        costs: CostModel,
        min_trade_notional: float = 1.0,
        rebalance_threshold: float = 0.02,
    ) -> None:
        if starting_cash <= 0:
            raise ValueError("starting_cash moet positief zijn")
        self.cash = float(starting_cash)
        self.qty = 0.0
        self.costs = costs
        self.min_trade_notional = min_trade_notional
        self.rebalance_threshold = rebalance_threshold
        """Onder deze afwijking van het doelgewicht handelen we niet. Zonder
        deze band betaal je fees om van 60,0% naar 60,4% te gaan."""
        self.fills: list[Fill] = []

    def equity(self, price: float) -> float:
        return self.cash + self.qty * price

    def weight(self, price: float) -> float:
        eq = self.equity(price)
        return 0.0 if eq <= 0 else (self.qty * price) / eq

    def rebalance_to(self, ts: datetime, price: float, target_weight: float) -> Fill | None:
        """Breng de positie naar het doelgewicht tegen `price`.

        Retourneert de Fill, of None als er niet gehandeld is.
        """
        target_weight = max(0.0, min(1.0, target_weight))
        equity = self.equity(price)
        if equity <= 0:
            return None

        current_weight = self.weight(price)
        if abs(target_weight - current_weight) < self.rebalance_threshold:
            return None

        target_value = equity * target_weight
        delta_value = target_value - self.qty * price
        side = "buy" if delta_value > 0 else "sell"

        fill_price = self.costs.fill_price(price, side)

        if side == "buy":
            # Fee komt uit dezelfde pot, dus corrigeer om niet negatief te eindigen.
            budget = min(delta_value, self.cash)
            budget /= 1 + self.costs.fee_bps / 10_000.0
            qty = budget / fill_price
        else:
            qty = min(abs(delta_value) / fill_price, self.qty)

        notional = qty * fill_price
        if notional < self.min_trade_notional or qty <= 0:
            return None

        fee = self.costs.fee(notional)
        if side == "buy":
            if notional + fee > self.cash + 1e-9:
                return None
            self.cash -= notional + fee
            self.qty += qty
        else:
            self.cash += notional - fee
            self.qty -= qty
            if self.qty < 1e-12:
                self.qty = 0.0

        fill = Fill(
            ts=ts, side=side, qty=qty, price=fill_price, fee=fee, reference_price=price
        )
        self.fills.append(fill)
        return fill
