"""Backtest-loop.

Volgorde per bar, en die volgorde is het hele punt:

    1. bar i sluit
    2. strategie ziet bar i en alles ervoor -> doelgewicht
    3. dat gewicht wordt uitgevoerd op de OPEN van bar i+1
    4. waardering aan het einde van bar i+1

Geen enkele beslissing gebruikt dus informatie uit de bar waarin hij wordt
uitgevoerd. Dat kost wat rendement op papier en is de reden dat het cijfer
iets betekent.
"""

from __future__ import annotations

from engine.broker_sim import SimulatedBroker
from engine.costs import CostModel
from engine.types import Bar, BacktestResult, Snapshot
from strategies.base import Strategy


def run_backtest(
    bars: list[Bar],
    strategy: Strategy,
    starting_equity: float = 1000.0,
    costs: CostModel | None = None,
    rebalance_threshold: float = 0.02,
) -> BacktestResult:
    if len(bars) < 2:
        raise ValueError("Minstens 2 bars nodig voor een backtest")

    costs = costs or CostModel()
    broker = SimulatedBroker(
        starting_cash=starting_equity,
        costs=costs,
        rebalance_threshold=rebalance_threshold,
    )
    result = BacktestResult(starting_equity=starting_equity)

    pending_target = 0.0
    history: list[Bar] = []

    for i, bar in enumerate(bars):
        # Uitvoeren op de open van deze bar, op basis van het signaal van gisteren.
        if i > 0:
            broker.rebalance_to(bar.ts, bar.open, pending_target)

        history.append(bar)

        # Signaal voor de volgende bar, pas nadat deze bar gesloten is.
        if len(history) > strategy.warmup:
            pending_target = strategy.on_bar(bar, history)
        else:
            pending_target = 0.0

        result.snapshots.append(
            Snapshot(
                ts=bar.ts,
                price=bar.close,
                cash=broker.cash,
                qty=broker.qty,
                equity=broker.equity(bar.close),
                target_weight=pending_target,
            )
        )

    result.fills = broker.fills
    return result
