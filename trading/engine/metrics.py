"""Prestatiematen.

Bewust inclusief de cijfers die het ongemakkelijk maken: kostendrag,
turnover, en de vergelijking met simpelweg kopen en niets doen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from engine.types import BacktestResult

BARS_PER_YEAR = {"1h": 24 * 365, "4h": 6 * 365, "1d": 365, "1w": 52}


@dataclass
class Metrics:
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    n_trades: int
    total_costs: float
    cost_drag: float  # kosten als % van startkapitaal
    time_in_market: float
    final_equity: float
    buy_hold_return: float

    def edge_vs_hold(self) -> float:
        return self.total_return - self.buy_hold_return


def _max_drawdown(curve: list[float]) -> float:
    peak, worst = curve[0], 0.0
    for value in curve:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def _sharpe(returns: list[float], bars_per_year: float) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return 0.0
    return (mean / sd) * math.sqrt(bars_per_year)


def compute(result: BacktestResult, timeframe: str = "1d") -> Metrics:
    curve = result.equity_curve
    if len(curve) < 2:
        raise ValueError("Te weinig datapunten voor metrics")

    bars_per_year = BARS_PER_YEAR.get(timeframe, 365)
    start, end = result.starting_equity, curve[-1]

    returns = [
        (curve[i] / curve[i - 1]) - 1 for i in range(1, len(curve)) if curve[i - 1] > 0
    ]
    years = len(curve) / bars_per_year
    cagr = ((end / start) ** (1 / years) - 1) if years > 0 and start > 0 else 0.0

    first_price = result.snapshots[0].price
    last_price = result.snapshots[-1].price
    buy_hold = (last_price / first_price) - 1

    in_market = sum(1 for s in result.snapshots if s.qty > 0) / len(result.snapshots)

    return Metrics(
        total_return=(end / start) - 1,
        cagr=cagr,
        max_drawdown=_max_drawdown(curve),
        sharpe=_sharpe(returns, bars_per_year),
        n_trades=len(result.fills),
        total_costs=result.total_costs,
        cost_drag=result.total_costs / start if start > 0 else 0.0,
        time_in_market=in_market,
        final_equity=end,
        buy_hold_return=buy_hold,
    )


def report(m: Metrics, label: str = "") -> str:
    verdict = "VERSLAAT hold" if m.edge_vs_hold() > 0 else "verliest van hold"
    return "\n".join(
        [
            f"--- {label} ---",
            f"  Eindkapitaal      EUR {m.final_equity:,.2f}",
            f"  Totaalrendement   {m.total_return:+.2%}",
            f"  CAGR              {m.cagr:+.2%}",
            f"  Max drawdown      {m.max_drawdown:.2%}",
            f"  Sharpe            {m.sharpe:.2f}",
            f"  Trades            {m.n_trades}",
            f"  Kosten betaald    EUR {m.total_costs:,.2f}  ({m.cost_drag:.2%} van inleg)",
            f"  Tijd in de markt  {m.time_in_market:.1%}",
            f"  Buy & hold        {m.buy_hold_return:+.2%}",
            f"  Verschil          {m.edge_vs_hold():+.2%}  <- {verdict}",
        ]
    )
