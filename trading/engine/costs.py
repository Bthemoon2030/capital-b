"""Kostenmodel.

Dit is het onderdeel dat de meeste "winnende" strategieen sloopt. Op een
account van EUR 1000 zijn fees en spread geen detail maar de hoofdrolspeler:
een strategie die 2x per week de hele positie omdraait betaalt bij 25 bps
per kant ruim 50% van het kapitaal per jaar aan kosten.

Defaults staan op Alpaca crypto taker-tarief (0,25% voor het laagste
volumeniveau). Controleer je eigen tarief voordat je conclusies trekt.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    fee_bps: float = 25.0
    """Broker fee per kant, in basispunten. Alpaca crypto taker = 25 bps."""

    slippage_bps: float = 5.0
    """Verwacht verschil tussen de prijs die je ziet en de prijs die je krijgt."""

    min_fee: float = 0.0
    """Minimum fee per order. Alpaca crypto kent die niet; aandelenbrokers wel."""

    def fill_price(self, reference_price: float, side: str) -> float:
        """Slippage werkt altijd tegen je: kopen duurder, verkopen goedkoper."""
        drift = reference_price * self.slippage_bps / 10_000.0
        if side == "buy":
            return reference_price + drift
        if side == "sell":
            return reference_price - drift
        raise ValueError(f"Onbekende side: {side!r}")

    def fee(self, notional: float) -> float:
        return max(abs(notional) * self.fee_bps / 10_000.0, self.min_fee)

    def round_trip_bps(self) -> float:
        """Wat een volledige heen-en-weer-trade kost, in bps. Je edge moet
        hier ruim overheen komen voordat er iets overblijft."""
        return 2 * (self.fee_bps + self.slippage_bps)


ZERO_COST = CostModel(fee_bps=0.0, slippage_bps=0.0)
"""Alleen voor tests: laat zien hoeveel van je rendement puur kosten was."""
