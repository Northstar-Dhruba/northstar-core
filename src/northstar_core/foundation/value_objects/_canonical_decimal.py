"""Context-independent canonicalization shared by the numeric Value Objects.

This module is private. It is not exported from the value_objects package and
nothing outside Foundation's own numeric values should import it.

Why it exists
-------------
Money, Percentage, Price and Quantity each canonicalized with
``Decimal.normalize()``, which consults the ambient decimal context and rounds
to its precision. Under the default context a value with more than twenty-eight
significant digits was silently truncated on the way in, and under a reduced
context far sooner:

    Quantity(Decimal("1.2345678901234567890123456789012345678901234567890123"))
        with prec=6  -> 1.23457
        with prec=28 -> 1.234567890123456789012345679

The stored value therefore depended on whoever happened to hold the context at
construction time, so one input could become two unequal domain values. For
values that are recorded, replayed and compared across processes that is a
determinism defect rather than a rounding preference.

The approach
------------
Nothing here operates on the Decimal. ``normalize()`` is not used, and neither
is arithmetic, because both consult the context. The coefficient is edited
directly through ``as_tuple()``, and the result is rebuilt from text. Decimal
construction from a tuple or a string and plain ``"f"`` formatting are all
exact and context-free, so every supplied digit survives and the caller's
context and flags are left untouched.

The canonical form is unchanged from what ``normalize()`` plus ``format(..,
"f")`` produced for every value that fitted inside the ambient precision: plain
notation, no exponent, trailing zeros removed after the decimal point only.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from northstar_core.foundation.exceptions.validation import ValidationError


def _coerce(value: object, subject: str, error: type[ValidationError]) -> Decimal:
    """Accept the supported numeric spellings, or raise ``error``."""
    if value is None:
        raise error(f"{subject} cannot be None.")
    if isinstance(value, bool):
        raise error(f"{subject} must be a numeric value.")
    if isinstance(value, float):
        raise error(f"{subject} must not be a float.")
    if isinstance(value, Decimal):
        coerced = value
    elif isinstance(value, int):
        coerced = Decimal(value)
    elif isinstance(value, str):
        if not value.strip():
            raise error(f"{subject} cannot be empty.")
        try:
            coerced = Decimal(value.strip())
        except InvalidOperation as exc:
            raise error(f"{subject} must be a numeric value.") from exc
    else:
        raise error(f"{subject} must be a numeric value.")

    if not coerced.is_finite():
        raise error(f"{subject} must be finite.")
    return coerced


def _canonicalize(value: Decimal) -> Decimal:
    """Return the canonical spelling of a finite Decimal, digit for digit.

    Trailing zeros are removed after the decimal point only, so 1, 1.0, 1.000
    and 1E+0 reach one spelling while the integer 100 keeps its magnitude. The
    result is rendered in plain notation so that 1E+2 and 100 also agree.
    Negative zero is folded to zero, because a value equal to zero that prints
    as "-0" is the same number wearing two faces.
    """
    sign, digits, exponent = value.as_tuple()
    coefficient = list(digits)
    while exponent < 0 and coefficient and coefficient[-1] == 0:
        coefficient.pop()
        exponent += 1
    if not any(coefficient):
        sign, coefficient, exponent = 0, [0], 0
    return Decimal(format(Decimal((sign, tuple(coefficient), exponent)), "f"))


def canonical_decimal(value: object, subject: str, error: type[ValidationError]) -> Decimal:
    """Coerce ``value`` to a canonical finite Decimal without consulting the context.

    ``subject`` names the value in any raised message -- "Quantity", "Price
    amount" -- so each Value Object keeps the wording it already had, and
    ``error`` is the exception type that Value Object raises.
    """
    return _canonicalize(_coerce(value, subject, error))
