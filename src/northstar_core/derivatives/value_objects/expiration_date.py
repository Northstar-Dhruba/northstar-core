"""Calendar date on which one derivative contract expires.

An expiration is a calendar date, not an instant. A contract expiring on 20
March 2026 does not expire at any particular moment that is meaningful without
the exchange's session calendar, so ExpirationDate carries no time of day and
no timezone: inventing either would produce a value that compares wrongly near
day boundaries while looking precise.

ExpirationDate deliberately does not convert to or from PointInTime. Relating
an expiry to a settlement instant requires session knowledge this value does
not have, and that relationship belongs to whatever later concept owns trading
sessions.

The value is also distinct from a last trading day, which is frequently earlier
than expiry. Those are different facts and are not collapsed here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from northstar_core.foundation.exceptions.validation import ValidationError

_EXPIRATION_DATE_PATTERN = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$")


class InvalidExpirationDateError(ValidationError):
    """Raised when an ExpirationDate value is invalid."""


def _normalize(value: str) -> str:
    """Return the canonical YYYY-MM-DD form of one real calendar date."""
    if value is None:
        raise InvalidExpirationDateError("ExpirationDate cannot be None.")
    if not isinstance(value, str):
        raise InvalidExpirationDateError("ExpirationDate must be a string.")

    normalized = value.strip()
    if not normalized:
        raise InvalidExpirationDateError("ExpirationDate cannot be empty.")

    match = _EXPIRATION_DATE_PATTERN.fullmatch(normalized)
    if match is None:
        raise InvalidExpirationDateError("ExpirationDate must be a YYYY-MM-DD calendar date.")

    try:
        calendar_date = date(
            int(match.group("year")), int(match.group("month")), int(match.group("day"))
        )
    except ValueError as exc:
        raise InvalidExpirationDateError("ExpirationDate must be a real calendar date.") from exc

    return calendar_date.isoformat()


@dataclass(frozen=True, slots=True, order=True)
class ExpirationDate:
    """Immutable calendar date on which one derivative contract expires.

    The stored value is always a real calendar date in canonical YYYY-MM-DD
    form, so lexicographic ordering is chronological ordering: fixed-width
    zero-padded components sort the same way the dates do. That is why this
    value can be ordered directly, unlike an instant whose optional fractional
    seconds make its text ordering unreliable.
    """

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _normalize(self.value))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ExpirationDate(value={self.value!r})"
