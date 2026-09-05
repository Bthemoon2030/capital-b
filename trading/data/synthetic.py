"""Synthetische prijsreeks voor zelftests.

Bestaat zodat de engine te verifieren is zonder marktdata en zonder
internet. Gebruik dit NOOIT om een strategie te beoordelen: een geometrische
random walk heeft geen van de eigenschappen die BTC interessant maken
(volatiliteitsclusters, fat tails, regimes).
"""

from __future__ import annotations

import math
import random
from datetime import timedelta

from engine.types import Bar, utc


def random_walk(
    n: int = 500,
    start_price: float = 50_000.0,
    drift: float = 0.0008,
    vol: float = 0.03,
    seed: int = 42,
) -> list[Bar]:
    rng = random.Random(seed)
    bars: list[Bar] = []
    ts = utc(2024, 1, 1)
    price = start_price

    for _ in range(n):
        shock = rng.gauss(drift, vol)
        close = max(price * math.exp(shock), 1.0)
        high = max(price, close) * (1 + abs(rng.gauss(0, vol / 4)))
        low = min(price, close) * (1 - abs(rng.gauss(0, vol / 4)))
        bars.append(
            Bar(ts=ts, open=price, high=high, low=low, close=close, volume=rng.uniform(10, 100))
        )
        price = close
        ts += timedelta(days=1)

    return bars
