"""Settlement-currency value of one quote point for one futures contract.

A FuturesPointValue states how much settlement currency a 1.0 change in a
product's QuoteValue is worth for one contract:

    amount  =  settlement-currency units
               per 1.0 change in QuoteValue
               per one contract

An amount of 50 in USD means a 1.0 move in the quote, on one contract, is
worth 50 USD. This single rate is the only unit profit and loss needs: it
converts a quote difference -- in whatever convention the product is quoted,
index points, points of par or currency per barrel -- into currency, without
asserting anything about that convention or about a physical contract size.

It is not Money: Money is an amount of currency, whereas this is currency per
quote point per contract. It is not a tick value either, and carries no tick
size. It is a unit value, not a calculator: it performs no arithmetic, so no
result can depend on a caller's decimal context. Callers multiply under their
own explicit context and only then construct Money.

The amount is strictly positive. Quotes themselves may be positive, zero or
negative; the sign of a profit or loss comes from the quote movement and the
position's direction, never from the point value.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import Currency
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


class InvalidFuturesPointValueError(ValidationError):
    """Raised when a FuturesPointValue value is invalid."""


def _validate_amount(value: Decimal) -> Decimal:
    if value is None:
        raise InvalidFuturesPointValueError("FuturesPointValue amount cannot be None.")
    if not isinstance(value, Decimal):
        raise InvalidFuturesPointValueError("FuturesPointValue amount must be a Decimal.")
    amount = canonical_decimal(value, "FuturesPointValue amount", InvalidFuturesPointValueError)
    if amount <= 0:
        raise InvalidFuturesPointValueError("FuturesPointValue amount must be greater than zero.")
    return amount


def _validate_currency(value: Currency) -> Currency:
    if value is None:
        raise InvalidFuturesPointValueError("FuturesPointValue currency cannot be None.")
    if not isinstance(value, Currency):
        raise InvalidFuturesPointValueError("FuturesPointValue currency must be a Currency value.")
    return value


@dataclass(frozen=True, slots=True)
class FuturesPointValue:
    """Immutable settlement-currency amount per quote point per contract.

    Only a Decimal amount is accepted, stored in the context-independent
    canonical form every Core numeric value uses, so ``50``, ``50.0`` and
    ``50.000`` are one value. Point values are deliberately not ordered: two in
    different currencies have no order, and nothing needs to rank them.
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", _validate_amount(self.amount))
        object.__setattr__(self, "currency", _validate_currency(self.currency))

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}/point/contract"

    def __repr__(self) -> str:
        return f"FuturesPointValue(amount={self.amount!r}, currency={self.currency!r})"
