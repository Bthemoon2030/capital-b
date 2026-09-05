#!/usr/bin/env python3
"""Zelftest zonder data en zonder netwerk: klopt de engine zelf?

    python3 selftest.py
"""

from __future__ import annotations

import sys

from data.synthetic import random_walk
from engine import metrics
from engine.backtest import run_backtest
from engine.costs import CostModel, ZERO_COST
from strategies.base import BuyAndHold, Strategy
from strategies.sma_cross import SmaCross

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        failures.append(name)


class AlwaysFlip(Strategy):
    """Draait elke bar om: maximale turnover, om kosten zichtbaar te maken."""

    name = "always-flip"

    def __init__(self) -> None:
        self.state = 0.0

    def on_bar(self, bar, history):
        self.state = 1.0 - self.state
        return self.state


def main() -> int:
    bars = random_walk(n=400)
    print(f"Synthetische reeks: {len(bars)} bars\n")

    print("1. Buy-and-hold volgt de prijs (minus eenmalige instapkosten)")
    hold = run_backtest(bars, BuyAndHold(), 1000.0, ZERO_COST)
    m = metrics.compute(hold)
    check("rendement ~= prijsverandering", abs(m.total_return - m.buy_hold_return) < 0.02,
          f"({m.total_return:.4f} vs {m.buy_hold_return:.4f})")
    check("precies 1 trade", m.n_trades == 1, f"(kreeg {m.n_trades})")

    print("\n2. Kosten verlagen het rendement, nooit andersom")
    cheap = metrics.compute(run_backtest(bars, SmaCross(), 1000.0, ZERO_COST))
    pricey = metrics.compute(run_backtest(bars, SmaCross(), 1000.0, CostModel(50, 10)))
    check("duur < gratis", pricey.total_return < cheap.total_return,
          f"({pricey.total_return:.4f} vs {cheap.total_return:.4f})")

    print("\n3. Hoge turnover wordt zwaar afgestraft")
    flip = metrics.compute(run_backtest(bars, AlwaysFlip(), 1000.0, CostModel(25, 5)))
    check("kostendrag > 50% bij dagelijks omdraaien", flip.cost_drag > 0.5,
          f"(kreeg {flip.cost_drag:.2%})")

    print("\n4. Geen lookahead: kapitaal kan niet uit het niets komen")
    check("eindkapitaal >= 0", flip.final_equity >= 0, f"({flip.final_equity:.2f})")
    check("geen negatieve cash", all(s.cash >= -1e-6 for s in
          run_backtest(bars, SmaCross(), 1000.0, CostModel()).snapshots))

    print("\n5. Gewichten blijven binnen 0..1 (long-only, geen leverage)")
    snaps = run_backtest(bars, SmaCross(), 1000.0, CostModel()).snapshots
    check("exposure <= 1.0", all(s.exposure <= 1.0 + 1e-6 for s in snaps))
    check("exposure >= 0.0", all(s.exposure >= -1e-9 for s in snaps))

    print()
    if failures:
        print(f"{len(failures)} test(s) GEFAALD: {failures}")
        return 1
    print("Alle zelftests geslaagd.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
