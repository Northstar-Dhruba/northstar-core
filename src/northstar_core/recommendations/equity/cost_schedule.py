"""A versioned synthetic transaction-cost schedule (EI4-D4, ADR-020).

Indian cash-equity intraday costs have several components -- brokerage,
securities transaction tax, exchange transaction charges, SEBI fees, stamp duty
and GST -- whose real rates and bases change over time and are not approved
(EI0-D12). This schedule states **no real rate**. It holds explicit synthetic
components, each labelled and applied to one side of a hypothetical trade:

- ``proportional_rate``: a fraction of that side's notional;
- ``per_share``: an amount per share;
- ``per_order``: a flat amount per order, never spread as a per-share rate.

``slippage_rate_per_side`` is an explicit modeled adverse price movement, as a
fraction of notional, charged once on each side. It is a modelling assumption,
not a fee.

Each side's total is rounded **up** to ``rounding_increment``, so the modeled
cost is never understated. That is a synthetic convention of this schedule,
not an official fee-rounding rule.

Both sides must be stated explicitly: a schedule with no ENTRY or no EXIT
component is refused, so a missing cost is never read as zero. A zero rate is
allowed only when written down.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from fractions import Fraction
from typing import Any

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency, Price
from northstar_core.recommendations.equity._exact import (
    ceil_to,
    require_decimal,
    text,
    to_decimal,
)
from northstar_core.recommendations.equity.synthetic_inputs import EquitySyntheticVersion


class InvalidEquitySyntheticCostScheduleError(ValidationError):
    """Raised when a synthetic cost component or schedule is invalid, or misused."""


class EquityCostSide(StrEnum):
    """The side of a hypothetical round trip a cost applies to."""

    ENTRY = "ENTRY"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class EquitySyntheticCostComponent:
    """One labelled synthetic cost on one side of a hypothetical trade."""

    label: str
    side: EquityCostSide
    proportional_rate: Decimal
    per_share: Decimal
    per_order: Decimal

    def __post_init__(self) -> None:
        error = InvalidEquitySyntheticCostScheduleError
        if not isinstance(self.label, str) or not self.label or self.label != self.label.strip():
            raise error("A cost component label must be non-empty text without surrounding space.")
        if not isinstance(self.side, EquityCostSide):
            raise error("A cost component side must be an EquityCostSide.")
        for name in ("proportional_rate", "per_share", "per_order"):
            value = require_decimal(
                getattr(self, name), f"Cost component {name}", error, allow_zero=True
            )
            object.__setattr__(self, name, value)

    def document(self) -> dict[str, Any]:
        """Return the canonical content."""
        return {
            "label": self.label,
            "side": self.side.value,
            "proportional_rate": text(self.proportional_rate),
            "per_share": text(self.per_share),
            "per_order": text(self.per_order),
        }


@dataclass(frozen=True, slots=True)
class EquitySyntheticCostSchedule:
    """An explicit, versioned synthetic cost schedule in one currency."""

    version: EquitySyntheticVersion
    currency: Currency
    components: tuple[EquitySyntheticCostComponent, ...]
    slippage_rate_per_side: Decimal
    rounding_increment: Decimal

    def __post_init__(self) -> None:
        error = InvalidEquitySyntheticCostScheduleError
        if not isinstance(self.version, EquitySyntheticVersion):
            raise error("EquitySyntheticCostSchedule version must be an EquitySyntheticVersion.")
        if not isinstance(self.currency, Currency):
            raise error("EquitySyntheticCostSchedule currency must be a Currency.")
        if not isinstance(self.components, tuple) or not all(
            isinstance(c, EquitySyntheticCostComponent) for c in self.components
        ):
            raise error("EquitySyntheticCostSchedule components must be a tuple of components.")
        sides = {c.side for c in self.components}
        if sides != set(EquityCostSide):
            raise error("A cost schedule must state at least one ENTRY and one EXIT component.")
        keys = [(c.side, c.label) for c in self.components]
        if len(set(keys)) != len(keys):
            raise error("Cost component labels must be unique on each side.")
        object.__setattr__(
            self,
            "slippage_rate_per_side",
            require_decimal(
                self.slippage_rate_per_side, "Cost schedule slippage rate", error, allow_zero=True
            ),
        )
        object.__setattr__(
            self,
            "rounding_increment",
            require_decimal(
                self.rounding_increment,
                "Cost schedule rounding increment",
                error,
                allow_zero=False,
            ),
        )

    def cost(self, side: EquityCostSide, price: Price, quantity: int) -> Decimal:
        """Return the modeled cost of ``quantity`` shares at ``price`` on ``side``.

        Raises InvalidEquitySyntheticCostScheduleError for misuse, and ArithmeticError
        if the exact cost cannot be represented as a Decimal.
        """
        if not isinstance(side, EquityCostSide):
            raise InvalidEquitySyntheticCostScheduleError("side must be an EquityCostSide.")
        if not isinstance(price, Price) or price.currency != self.currency:
            raise InvalidEquitySyntheticCostScheduleError(
                f"price must be a Price in {self.currency}."
            )
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise InvalidEquitySyntheticCostScheduleError("quantity must be a whole number >= 1.")
        exact = to_decimal(side_cost(self, side, Fraction(price.amount), quantity))
        if exact is None:
            raise ArithmeticError("The modeled cost is not representable exactly.")
        return exact

    def document(self) -> dict[str, Any]:
        """Return the canonical content, components in their stated order."""
        return {
            "version": self.version.value,
            "currency": self.currency.value,
            "components": [c.document() for c in self.components],
            "slippage_rate_per_side": text(self.slippage_rate_per_side),
            "rounding_increment": text(self.rounding_increment),
        }


def side_terms(
    schedule: EquitySyntheticCostSchedule, side: EquityCostSide, price: Fraction
) -> tuple[Fraction, Fraction]:
    """Return one side's unrounded cost as ``(per-share slope, per-order amount)``.

    Before rounding, the side's cost of ``q`` shares at ``price`` is exactly
    ``slope * q + per_order``: proportional rates and slippage scale with the
    notional, per-share amounts with ``q``, and per-order amounts not at all.
    """
    slope = Fraction(schedule.slippage_rate_per_side) * price
    per_order = Fraction(0)
    for component in schedule.components:
        if component.side is side:
            slope += Fraction(component.proportional_rate) * price
            slope += Fraction(component.per_share)
            per_order += Fraction(component.per_order)
    return slope, per_order


def side_cost(
    schedule: EquitySyntheticCostSchedule, side: EquityCostSide, price: Fraction, quantity: int
) -> Fraction:
    """Return one side's exact modeled cost, rounded up to the schedule's increment.

    The cost is ``slope * quantity + per_order`` (``side_terms``), rounded up.
    It never decreases as ``quantity`` grows.
    """
    slope, per_order = side_terms(schedule, side, price)
    return ceil_to(slope * quantity + per_order, Fraction(schedule.rounding_increment))
