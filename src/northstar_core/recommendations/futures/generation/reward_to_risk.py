"""Exact price-movement and reward-to-risk evidence carried by a proposal.

PriceMovementUnit records U, the mean absolute close-to-close change, as the
exact total of the absolute changes and the number of changes. U itself is the
quotient; it is kept as its exact parts because the quotient need not
terminate. It is not average true range and not realized volatility.

RewardToRisk records the exact reward and risk measured from the worst entry
inside the aligned entry zone. Comparison with a minimum is exact
cross-multiplication. The ratio is a geometric property of the levels -- not a
probability of success, an expected return or a forecast -- and no transaction
cost or slippage is included.

``value`` and ``ratio`` are display quotients rounded to twenty-eight
significant digits (round-half-even); nothing is decided from them. String
forms are fixed-point -- 0.0000001, never 1E-7 -- and are text, not the
canonical numeric values. ``str(PriceMovementUnit)`` says "(rounded to 28
significant digits)" whenever the displayed U is not exactly the quotient.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.recommendations.futures.generation._price_levels import (
    display_quotient,
    fixed_point,
    is_exact_quotient,
    meets_minimum,
)


class InvalidPriceMovementUnitError(ValidationError):
    """Raised when a PriceMovementUnit value is invalid."""


class InvalidRewardToRiskError(ValidationError):
    """Raised when a RewardToRisk value is invalid."""


def _require_positive_decimal(
    value: Decimal, subject: str, error: type[ValidationError]
) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise error(f"{subject} must be a finite Decimal.")
    if value <= 0:
        raise error(f"{subject} must be greater than zero.")
    return value


@dataclass(frozen=True, slots=True)
class PriceMovementUnit:
    """Immutable mean absolute close-to-close change, held as its exact parts."""

    total_absolute_change: Decimal
    changes: int

    def __post_init__(self) -> None:
        _require_positive_decimal(
            self.total_absolute_change,
            "PriceMovementUnit total absolute change",
            InvalidPriceMovementUnitError,
        )
        if isinstance(self.changes, bool) or not isinstance(self.changes, int):
            raise InvalidPriceMovementUnitError("PriceMovementUnit changes must be an integer.")
        if self.changes < 1:
            raise InvalidPriceMovementUnitError("PriceMovementUnit changes must be positive.")

    @property
    def value(self) -> Decimal:
        """Return U for display, rounded to twenty-eight significant digits."""
        return display_quotient(self.total_absolute_change, Decimal(self.changes))

    def __str__(self) -> str:
        """Return U in fixed point, marked when the display is not the exact quotient."""
        value = self.value
        text = fixed_point(value)
        if not is_exact_quotient(value, self.total_absolute_change, Decimal(self.changes)):
            text = f"{text} (rounded to 28 significant digits)"
        return f"{text} over {self.changes} changes"

    def __repr__(self) -> str:
        return (
            "PriceMovementUnit("
            f"total_absolute_change={self.total_absolute_change!r}, "
            f"changes={self.changes!r}"
            ")"
        )


@dataclass(frozen=True, slots=True)
class RewardToRisk:
    """Immutable exact worst-entry reward and risk of one setup."""

    reward: Decimal
    risk: Decimal

    def __post_init__(self) -> None:
        _require_positive_decimal(self.reward, "RewardToRisk reward", InvalidRewardToRiskError)
        _require_positive_decimal(self.risk, "RewardToRisk risk", InvalidRewardToRiskError)

    @property
    def ratio(self) -> Decimal:
        """Return reward / risk for display, rounded to twenty-eight significant digits."""
        return display_quotient(self.reward, self.risk)

    def meets(self, minimum: Decimal) -> bool:
        """Return whether ``reward >= minimum * risk``, compared exactly."""
        if not isinstance(minimum, Decimal) or not minimum.is_finite():
            raise InvalidRewardToRiskError("RewardToRisk minimum must be a finite Decimal.")
        return meets_minimum(self.reward, self.risk, minimum)

    def __str__(self) -> str:
        return f"{fixed_point(self.reward)}:{fixed_point(self.risk)}"

    def __repr__(self) -> str:
        return f"RewardToRisk(reward={self.reward!r}, risk={self.risk!r})"
