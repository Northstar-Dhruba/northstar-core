"""A signed market quotation in the quotation convention of its product.

A quotation is a number in whatever convention its product is quoted in, and
that convention is not always money. ES trades in index points, ZB in points of
par, CL in US dollars per barrel and GC in US dollars per troy ounce. Only the
last two are currency amounts per unit; the first two are not currency amounts
at all, and stamping a Currency onto them would assert something false.

This value therefore carries a bare Decimal and makes no currency, unit, tick
or multiplier claim. Currency and quotation unit are constant per product, so
they belong on a product specification once a consumer needs them -- notional
value, tick-aligned validation or profit and loss -- rather than being repeated
on every quotation of every bar, where four copies could disagree.

Why this is not Price
---------------------
Beyond the unit question, Price forbids negative amounts, and quotations go
negative: WTI crude settled at -37.63 on 20 April 2020. A Price-based quotation
could not record that session at all. A quotation is signed here for that
reason, not as a convenience.

Canonicalization is the shared context-independent Foundation routine, so a
quotation never depends on the decimal context its caller happened to hold.

Quotations are comparable within one product and meaningless across products.
Nothing in this value can enforce that, because a value object only sees
itself; the bar that holds a quotation ties it to exactly one contract, which
is what makes an unqualified number safe for now.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects._canonical_decimal import (
    canonical_decimal,
)


class InvalidQuoteValueError(ValidationError):
    """Raised when a QuoteValue value is invalid."""


@dataclass(frozen=True, slots=True, order=True)
class QuoteValue:
    """Immutable signed quotation in its product's own convention.

    Invariants:
        - The stored value is always finite.
        - The stored value is canonical, so numerically equal quotations
          compare and hash alike.
        - Canonicalization never rounds and never depends on the caller's
          decimal context.
        - Positive, zero and negative quotations are all valid.

    Examples:
        5432.25 (ES index points)
        118.5 (ZB points of par)
        -37.63 (CL US dollars per barrel, 20 April 2020)
    """

    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", canonical_decimal(self.value, "QuoteValue", InvalidQuoteValueError)
        )

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"QuoteValue(value={self.value!r})"
