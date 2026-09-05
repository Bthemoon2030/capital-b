"""Strategie-interface.

Contract, en dit is het belangrijkste deel van het hele project:

    on_bar(bar, history) krijgt de zojuist GESLOTEN bar plus alle bars
    daarvoor, en geeft een doelgewicht terug tussen 0.0 en 1.0.

De engine voert dat gewicht pas uit op de OPEN van de volgende bar. Je kunt
dus per constructie niet handelen op informatie die je op dat moment nog niet
had. Elke backtest die dat wel doet ziet er briljant uit en verliest geld.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.types import Bar


class Strategy(ABC):
    name: str = "unnamed"

    @abstractmethod
    def on_bar(self, bar: Bar, history: list[Bar]) -> float:
        """Doelgewicht in BTC na deze bar. 0.0 = volledig cash, 1.0 = volledig in."""

    @property
    def warmup(self) -> int:
        """Aantal bars dat de strategie nodig heeft voordat signalen tellen."""
        return 0

    def describe(self) -> str:
        return self.name


class BuyAndHold(Strategy):
    """De benchmark die je moet verslaan. Onderschat hem niet."""

    name = "buy-and-hold"

    def on_bar(self, bar: Bar, history: list[Bar]) -> float:
        return 1.0
