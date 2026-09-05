"""Kerntypes voor de backtest- en paper-engine.

Bewust dependency-vrij (alleen stdlib): dit moet op elke machine draaien,
van een laptop tot een GitHub Actions runner, zonder installatiegedoe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Bar:
    """Eén OHLCV-candle."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        if self.ts.tzinfo is None:
            raise ValueError(f"Bar.ts moet timezone-aware zijn, kreeg {self.ts!r}")
        if not (self.low <= self.open <= self.high and self.low <= self.close <= self.high):
            raise ValueError(f"Inconsistente OHLC op {self.ts.isoformat()}: {self}")


@dataclass
class Fill:
    """Een uitgevoerde (deel)transactie, inclusief wat hij echt kostte."""

    ts: datetime
    side: str  # "buy" of "sell"
    qty: float
    price: float  # prijs na slippage
    fee: float
    reference_price: float  # prijs zonder slippage, voor kostenanalyse

    @property
    def notional(self) -> float:
        return self.qty * self.price

    @property
    def slippage_cost(self) -> float:
        return abs(self.price - self.reference_price) * self.qty

    @property
    def total_cost(self) -> float:
        return self.fee + self.slippage_cost


@dataclass
class Snapshot:
    """Portefeuillestand op het einde van een bar."""

    ts: datetime
    price: float
    cash: float
    qty: float
    equity: float
    target_weight: float

    @property
    def exposure(self) -> float:
        return 0.0 if self.equity <= 0 else (self.qty * self.price) / self.equity


@dataclass
class BacktestResult:
    snapshots: list[Snapshot] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    starting_equity: float = 0.0

    @property
    def equity_curve(self) -> list[float]:
        return [s.equity for s in self.snapshots]

    @property
    def total_costs(self) -> float:
        return sum(f.total_cost for f in self.fills)


def utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)
