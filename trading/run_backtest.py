#!/usr/bin/env python3
"""Backtest-runner.

    python3 run_backtest.py --csv data/btc_1d.csv --timeframe 1d
    python3 run_backtest.py --synthetic          # zelftest, geen data nodig

Draait de gekozen strategie altijd naast buy-and-hold, want dat is de
benchmark die telt.
"""

from __future__ import annotations

import argparse
import sys

from data.csv_loader import load_csv
from data.synthetic import random_walk
from engine import metrics
from engine.backtest import run_backtest
from engine.costs import CostModel, ZERO_COST
from strategies.base import BuyAndHold
from strategies.sma_cross import SmaCross


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest een strategie op BTC-data")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", help="Pad naar OHLCV-CSV (bv. een TradingView-export)")
    source.add_argument("--synthetic", action="store_true", help="Gebruik synthetische data")

    parser.add_argument("--timeframe", default="1d", choices=["1h", "4h", "1d", "1w"])
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--fee-bps", type=float, default=25.0, help="Broker fee per kant")
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument(
        "--show-costless",
        action="store_true",
        help="Draai ook zonder kosten, om te zien hoeveel de kosten opeten",
    )
    args = parser.parse_args(argv)

    bars = random_walk() if args.synthetic else load_csv(args.csv)
    costs = CostModel(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)

    print(f"Bars: {len(bars)}  van {bars[0].ts.date()} tot {bars[-1].ts.date()}")
    print(f"Kosten: {costs.round_trip_bps():.0f} bps per volledige round trip\n")

    for strategy in (SmaCross(args.fast, args.slow), BuyAndHold()):
        result = run_backtest(bars, strategy, args.equity, costs)
        print(metrics.report(metrics.compute(result, args.timeframe), strategy.describe()))
        print()

    if args.show_costless:
        strategy = SmaCross(args.fast, args.slow)
        result = run_backtest(bars, strategy, args.equity, ZERO_COST)
        print(metrics.report(metrics.compute(result, args.timeframe), f"{strategy.name} ZONDER kosten"))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
