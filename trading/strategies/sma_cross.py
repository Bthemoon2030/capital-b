"""Referentie-implementatie: moving average crossover.

LET OP: dit is GEEN strategie-aanbeveling. Het is het simpelste ding dat de
pijplijn end-to-end aantoonbaar laat werken, zodat je er je eigen regels
naast kunt leggen en kunt vergelijken. MA-crossovers op BTC zijn breed
bekend en de edge is grotendeels weggearbitreerd; verwacht dat hij na kosten
verliest van buy-and-hold. Dat is precies wat een eerlijke backtest hoort te
laten zien.
"""

from __future__ import annotations

from engine.types import Bar
from strategies.base import Strategy


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


class SmaCross(Strategy):
    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        if fast >= slow:
            raise ValueError("fast window moet kleiner zijn dan slow window")
        self.fast = fast
        self.slow = slow
        self.name = f"sma-cross({fast}/{slow})"

    @property
    def warmup(self) -> int:
        return self.slow

    def on_bar(self, bar: Bar, history: list[Bar]) -> float:
        closes = [b.close for b in history]
        fast = sma(closes, self.fast)
        slow = sma(closes, self.slow)
        if fast is None or slow is None:
            return 0.0
        return 1.0 if fast > slow else 0.0
