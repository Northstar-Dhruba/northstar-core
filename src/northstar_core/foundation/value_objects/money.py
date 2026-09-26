"""Financial money value object.

Money represents monetary value within a financial context.

Unlike Price, which represents a quoted or observed monetary value expressed in
a specific Currency, Money represents financial state such as balances,
liabilities, obligations, reserves, and financial responsibility. Negative
monetary values are valid because Money models financial state, not quoted
market value. Money remains distinct from Quantity, measurement, exchange rates,
and currency conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import (
    CurrencyMismatchError,
    InvalidMoneyError,
)
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)
from northstar_core.foundation.value_objects.currency import Currency


def _normalize_amount(value: object) -> Decimal:
    return canonical_decimal(value, "Money amount", InvalidMoneyError)


def _validate_amount(value: Decimal) -> None:
    """Validate Money business invariants."""
    return


def _require_matching_currency(left: Currency, right: Currency) -> None:
    if left != right:
        raise CurrencyMismatchError("Money currencies do not match.")


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable representation of monetary value within a financial context.

    Purpose:
        Preserve a monetary value expressed in a specific currency in a broader
        financial setting such as balances, obligations, reserves, or
        financial responsibility.

    Invariants:
        - The stored amount is always valid.
        - The stored currency is always a valid Currency instance.
        - The stored amount may be positive, zero, or negative.
        - Cross-currency operations are rejected.

    Examples:
        100 USD
        0 EUR
        -50 GBP
    """

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        normalized_amount = _normalize_amount(self.amount)
        _validate_amount(normalized_amount)

        if self.currency is None:
            raise InvalidMoneyError("Money currency cannot be None.")
        if not isinstance(self.currency, Currency):
            raise InvalidMoneyError("Money currency must be a Currency value.")

        object.__setattr__(self, "amount", normalized_amount)
        object.__setattr__(self, "currency", self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            return False
        return self.amount == other.amount

    def __add__(self, other: object) -> Money:
        if isinstance(other, Money):
            _require_matching_currency(self.currency, other.currency)
            return Money(self.amount + other.amount, self.currency)
        return NotImplemented

    def __sub__(self, other: object) -> Money:
        if isinstance(other, Money):
            _require_matching_currency(self.currency, other.currency)
            return Money(self.amount - other.amount, self.currency)
        return NotImplemented

    def __mul__(self, other: object) -> Money:
        if isinstance(other, Decimal):
            return Money(self.amount * other, self.currency)
        if isinstance(other, int):
            return Money(self.amount * Decimal(other), self.currency)
        return NotImplemented

    def __truediv__(self, other: object) -> Money:
        if isinstance(other, Decimal):
            if other == 0:
                raise InvalidMoneyError("Money cannot be divided by zero.")
            return Money(self.amount / other, self.currency)
        if isinstance(other, int):
            if other == 0:
                raise InvalidMoneyError("Money cannot be divided by zero.")
            return Money(self.amount / Decimal(other), self.currency)
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount < other.amount

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount <= other.amount

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount > other.amount

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        _require_matching_currency(self.currency, other.currency)
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"{self.amount} {self.currency.value}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount!r}, currency={self.currency!r})"
