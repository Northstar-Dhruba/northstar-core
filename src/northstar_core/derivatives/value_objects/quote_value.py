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

Quotations are comparable within one product and meaningless across products.
Nothing in this value can enforce that, because a value object only sees
itself; the bar that holds a quotation ties it to exactly one contract, which
is what makes an unqualified number safe for now.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidQuoteValueError(ValidationError):
    """Raised when a QuoteValue value is invalid."""


def _coerce(value: object) -> Decimal:
    if value is None:
        raise InvalidQuoteValueError("QuoteValue cannot be None.")
    if isinstance(value, bool):
        raise InvalidQuoteValueError("QuoteValue must be a numeric value.")
    if isinstance(value, float):
        raise InvalidQuoteValueError("QuoteValue must not be a float.")
    if isinstance(value, Decimal):
        coerced = value
    elif isinstance(value, int):
        coerced = Decimal(value)
    elif isinstance(value, str):
        if not value.strip():
            raise InvalidQuoteValueError("QuoteValue cannot be empty.")
        try:
            coerced = Decimal(value.strip())
        except InvalidOperation as exc:
            raise InvalidQuoteValueError("QuoteValue must be a numeric value.") from exc
    else:
        raise InvalidQuoteValueError("QuoteValue must be a numeric value.")
    if not coerced.is_finite():
        raise InvalidQuoteValueError("QuoteValue must be finite.")
    return coerced


def _canonicalize(value: Decimal) -> Decimal:
    """Return the canonical spelling of a finite Decimal, digit for digit.

    Decimal.normalize() is not used here, and neither is any arithmetic. Both
    consult the ambient decimal context and would round a quotation to whatever
    precision the caller happened to have set: under precision 6, normalize()
    turns a fifty-two digit quotation into six digits and the observation is
    gone. A market observation must read back exactly as it was recorded no
    matter who is holding the context.

    Instead the coefficient is edited directly. Trailing zeros after the
    decimal point are removed so that 1, 1.0, 1.000 and 1E+0 reach one
    spelling, the result is rendered in plain notation so that 1E+2 and 100
    also agree, and negative zero is folded to zero. Decimal construction from
    text and plain formatting are both exact, so every supplied digit
    survives.
    """
    sign, digits, exponent = value.as_tuple()
    coefficient = list(digits)
    while exponent < 0 and coefficient and coefficient[-1] == 0:
        coefficient.pop()
        exponent += 1
    if not any(coefficient):
        sign, coefficient, exponent = 0, [0], 0
    return Decimal(format(Decimal((sign, tuple(coefficient), exponent)), "f"))


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
        object.__setattr__(self, "value", _canonicalize(_coerce(self.value)))

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"QuoteValue(value={self.value!r})"
