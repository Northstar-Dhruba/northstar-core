"""Which market observations one trade recommendation may consume.

All three instants are completion instants of observations, compared only
through PointInTime.compare:

- ``eligible_from`` is the completion instant of the first trading session
  that began strictly after the recommendation was issued, inclusive. A daily
  bar that completes after issuance can still contain prices traded before it,
  so completing after issuance is not enough: only bars completing at or after
  ``eligible_from`` are evaluated.
- ``valid_through`` is the last observation the recommendation may consume,
  inclusive.
- ``contract_cutoff`` is the last observation of the contract itself. A
  contract's calendar expiry date is not assumed to be its last tradable
  session.

Core computes no session, calendar or expiry schedule. Every instant here is a
trusted, caller-supplied temporal contract, resolved by Application from the
authoritative trading-session calendar: a timestamp alone cannot prove that the
session it closes began after issuance. Core enforces only the order of the
instants it is given.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime


class InvalidRecommendationValidityError(ValidationError):
    """Raised when a RecommendationValidity value is invalid."""


def _validate_instant(value: PointInTime, field_name: str) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidRecommendationValidityError(
            f"RecommendationValidity {field_name} must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class RecommendationValidity:
    """Immutable eligible observation window, bounded by the contract cutoff.

    Invariants:
        - ``eligible_from`` is not later than ``valid_through``.
        - ``valid_through`` is not later than ``contract_cutoff``.
    """

    eligible_from: PointInTime
    valid_through: PointInTime
    contract_cutoff: PointInTime

    def __post_init__(self) -> None:
        eligible_from = _validate_instant(self.eligible_from, "eligible from")
        valid_through = _validate_instant(self.valid_through, "valid through")
        contract_cutoff = _validate_instant(self.contract_cutoff, "contract cutoff")
        if eligible_from.compare(valid_through) > 0:
            raise InvalidRecommendationValidityError(
                "RecommendationValidity eligible from cannot be later than valid through."
            )
        if valid_through.compare(contract_cutoff) > 0:
            raise InvalidRecommendationValidityError(
                "RecommendationValidity cannot extend beyond the contract cutoff."
            )
        object.__setattr__(self, "eligible_from", eligible_from)
        object.__setattr__(self, "valid_through", valid_through)
        object.__setattr__(self, "contract_cutoff", contract_cutoff)

    @property
    def ends_at_contract_cutoff(self) -> bool:
        """Return whether validity ends exactly at the contract cutoff."""
        return self.valid_through.compare(self.contract_cutoff) == 0

    def __str__(self) -> str:
        return (
            f"from {self.eligible_from} through {self.valid_through} "
            f"(contract cutoff {self.contract_cutoff})"
        )

    def __repr__(self) -> str:
        return (
            "RecommendationValidity("
            f"eligible_from={self.eligible_from!r}, "
            f"valid_through={self.valid_through!r}, "
            f"contract_cutoff={self.contract_cutoff!r}"
            ")"
        )
