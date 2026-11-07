"""Modeled LONG price levels of an equity recommendation (EI0-D14, EI4-D3).

The entry zone, stop and target are **modeled** levels: hypothetical prices
derived from research values and synthetic parameters. None of them is a fill,
a historical execution or a guarantee that a broker can trade there, and
nothing here evaluates whether a bar touched them.

All levels are Foundation ``Price`` values in one currency. Comparisons are
exact Decimal comparisons, never binary floating point.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, Price
from northstar_core.recommendations.equity._exact import text


class InvalidEquityRecommendationLevelsError(ValidationError):
    """Raised when an entry zone or set of levels is invalid."""


class EquityRecommendationDirection(StrEnum):
    """The direction of an equity recommendation. V1 is LONG only (EI0-D3)."""

    LONG = "LONG"


def _require_price(value: object, name: str) -> Price:
    if not isinstance(value, Price):
        raise InvalidEquityRecommendationLevelsError(f"{name} must be a Price.")
    return value


@dataclass(frozen=True, slots=True)
class EquityEntryZone:
    """An inclusive, non-degenerate modeled entry-price zone.

    Invariants:
        - ``0 < low < high``: a zone has positive width. A single price is not
          a zone, and is refused rather than widened.
        - Both bounds share one currency.

    (Futures allows a single-price zone; the equity synthetic model does not.)
    """

    low: Price
    high: Price

    def __post_init__(self) -> None:
        low = _require_price(self.low, "EquityEntryZone low")
        high = _require_price(self.high, "EquityEntryZone high")
        if low.currency != high.currency:
            raise InvalidEquityRecommendationLevelsError(
                "EquityEntryZone bounds differ in currency."
            )
        if low.amount <= 0:
            raise InvalidEquityRecommendationLevelsError("EquityEntryZone low must be positive.")
        if low.amount > high.amount:
            raise InvalidEquityRecommendationLevelsError(
                "EquityEntryZone low must not exceed high: the zone is inverted."
            )
        if low.amount == high.amount:
            raise InvalidEquityRecommendationLevelsError(
                "EquityEntryZone low must be below high: the zone is collapsed."
            )

    @property
    def currency(self) -> Currency:
        """Return the zone's currency."""
        return self.low.currency

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {"low": text(self.low.amount), "high": text(self.high.amount)}


@dataclass(frozen=True, slots=True)
class EquityRecommendationLevels:
    """Modeled LONG levels: an entry zone, a stop below it and a target above it.

    Invariants:
        - ``0 < stop < entry_zone.low`` and ``target > entry_zone.high``.
        - Every level shares the entry zone's currency.

    ``worst_entry`` is the zone's high: the least favourable LONG entry, from
    which risk and reward are measured.
    """

    entry_zone: EquityEntryZone
    stop: Price
    target: Price

    def __post_init__(self) -> None:
        if not isinstance(self.entry_zone, EquityEntryZone):
            raise InvalidEquityRecommendationLevelsError(
                "EquityRecommendationLevels entry zone must be an EquityEntryZone."
            )
        stop = _require_price(self.stop, "EquityRecommendationLevels stop")
        target = _require_price(self.target, "EquityRecommendationLevels target")
        currency = self.entry_zone.currency
        if stop.currency != currency or target.currency != currency:
            raise InvalidEquityRecommendationLevelsError(
                "EquityRecommendationLevels must share one currency."
            )
        if not 0 < stop.amount < self.entry_zone.low.amount:
            raise InvalidEquityRecommendationLevelsError(
                "A LONG stop must be positive and strictly below the whole entry zone."
            )
        if target.amount <= self.entry_zone.high.amount:
            raise InvalidEquityRecommendationLevelsError(
                "A LONG target must be strictly above the worst entry."
            )

    @property
    def currency(self) -> Currency:
        """Return the levels' currency."""
        return self.entry_zone.currency

    @property
    def worst_entry(self) -> Price:
        """Return the least favourable LONG entry: the zone's high."""
        return self.entry_zone.high

    @property
    def risk_per_share(self) -> Decimal:
        """Return the gross modeled loss per share from the worst entry to the stop."""
        return self.worst_entry.amount - self.stop.amount

    @property
    def reward_per_share(self) -> Decimal:
        """Return the gross modeled reward per share from the worst entry to the target."""
        return self.target.amount - self.worst_entry.amount

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "currency": self.currency.value,
            "entry_zone": self.entry_zone.document(),
            "stop": text(self.stop.amount),
            "target": text(self.target.amount),
        }
