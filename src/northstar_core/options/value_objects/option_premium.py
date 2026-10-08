"""The observed market quotation of one option contract.

A premium is what an option contract traded or was quoted at, in premium
points. For NIFTY options a premium point is one index point per unit of the
underlying; converting premium points into settlement currency is the job of
OptionPointValue, so the premium itself carries no currency.

Why this is not QuoteValue, OptionStrike, Price or Money
--------------------------------------------------------
A QuoteValue is signed because futures quotations go negative. An option
premium cannot: the most a holder can be paid to take a contract is nothing.
The premium is therefore zero or greater, and zero is an ordinary value -- an
option that expires worthless is worth exactly that. It is a distinct type so
that an option premium can never be passed where an underlying or futures
quotation is expected, or the reverse.

A strike is a fixed contract term that forms part of identity; a premium is an
observation that changes from bar to bar. Price is a currency-bound valuation
and Money is currency-bound financial state; a premium is neither.

Only a Decimal is accepted, so the caller -- not this value -- owns any
conversion from a provider's spelling. The stored form is the
context-independent canonical Decimal every Core numeric value uses, so
``182.35`` and ``182.350`` are one premium and a negative zero is zero.
Premiums are ordered so that observations of one contract can be compared, and
they offer no arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


class InvalidOptionPremiumError(ValidationError):
    """Raised when an OptionPremium value is invalid."""


def _validate_value(value: Decimal) -> Decimal:
    if value is None:
        raise InvalidOptionPremiumError("OptionPremium cannot be None.")
    if not isinstance(value, Decimal):
        raise InvalidOptionPremiumError("OptionPremium must be a Decimal.")
    premium = canonical_decimal(value, "OptionPremium", InvalidOptionPremiumError)
    if premium < 0:
        raise InvalidOptionPremiumError("OptionPremium cannot be negative.")
    return premium


@dataclass(frozen=True, slots=True, order=True)
class OptionPremium:
    """Immutable observed premium of one option contract, in premium points.

    Invariants:
        - The stored value is always a finite Decimal of zero or greater.
        - The stored value is canonical, so numerically equal premiums compare
          and hash alike, and a negative zero is stored as zero.
        - Canonicalization never rounds and never depends on the caller's
          decimal context.

    Examples:
        182.35
        0
    """

    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_value(self.value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"OptionPremium(value={self.value!r})"
