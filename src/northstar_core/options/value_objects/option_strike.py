"""The strike of one option contract, as a fixed contract term.

A strike is the level at which the option's right is struck, expressed in the
quotation convention of the underlying. A NIFTY strike of 25000 is 25000 index
points; it is not 25000 rupees, and stamping a Currency onto it would assert
something false. Currency belongs to whatever later concept converts quotation
points into money, never to the strike.

Why this is not QuoteValue, Price or Money
------------------------------------------
A QuoteValue is an observed market quotation that changes from bar to bar and
may be negative. A strike is neither observed nor variable: it is set when the
contract is listed and is part of the contract's identity. Price is a
currency-bound valuation and Money is currency-bound financial state; a strike
is neither of those either.

Why a strike must be positive
-----------------------------
Strikes of the reference product are positive, and a zero strike would make a
call and a put on one expiry degenerate. Some venues have listed zero and
negative strikes on products whose quotations went negative; admitting them
would be a deliberate widening, which stays backward-compatible because every
strike valid today would remain valid.

Only a Decimal is accepted, so the caller -- not this value -- owns any
conversion from a provider's spelling. The stored form is the
context-independent canonical Decimal every Core numeric value uses, so
``25000``, ``25000.0`` and ``2.5E+4`` are one strike. The strike is ordered so
that contracts can be presented canonically, and it offers no arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


class InvalidOptionStrikeError(ValidationError):
    """Raised when an OptionStrike value is invalid."""


def _validate_value(value: Decimal) -> Decimal:
    if value is None:
        raise InvalidOptionStrikeError("OptionStrike cannot be None.")
    if not isinstance(value, Decimal):
        raise InvalidOptionStrikeError("OptionStrike must be a Decimal.")
    strike = canonical_decimal(value, "OptionStrike", InvalidOptionStrikeError)
    if strike <= 0:
        raise InvalidOptionStrikeError("OptionStrike must be greater than zero.")
    return strike


@dataclass(frozen=True, slots=True, order=True)
class OptionStrike:
    """Immutable strike of one option contract in the underlying's convention.

    Invariants:
        - The stored value is always a finite Decimal greater than zero.
        - The stored value is canonical, so numerically equal strikes compare
          and hash alike.
        - Canonicalization never rounds and never depends on the caller's
          decimal context.

    Examples:
        25000 (NIFTY index points)
        24950.5
    """

    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _validate_value(self.value))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"OptionStrike(value={self.value!r})"
