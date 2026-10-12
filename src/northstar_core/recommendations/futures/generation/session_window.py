"""The caller-resolved validity window one contract is asked to support.

A session window states, for one contract, the policy-required validity horizon
the Application resolved from the trading-session calendar:

- ``eligible_from`` -- completion instant of the first session that began
  strictly after issuance;
- ``valid_through`` -- the last observation the full positional horizon needs;
- ``contract_cutoff`` -- the contract's last observation.

Only ``eligible_from <= valid_through`` is required here. ``valid_through`` may
lie after the cutoff: that is a contract that cannot support the horizon, which
generation rejects (INSUFFICIENT_CONTRACT_LIFE, or CONTRACT_EXPIRED when even
``eligible_from`` is after the cutoff) rather than truncating the window.

Core computes no weekend, holiday, special session or last trading day, and
cannot verify these instants: they are trusted temporal contracts, as in F-2.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesContract
from northstar_core.recommendations.futures.value_objects import RecommendationValidity


class InvalidFuturesRecommendationSessionWindowError(ValidationError):
    """Raised when a FuturesRecommendationSessionWindow value is invalid."""


def _validate_instant(value: PointInTime, field_name: str) -> PointInTime:
    if not isinstance(value, PointInTime):
        raise InvalidFuturesRecommendationSessionWindowError(
            f"FuturesRecommendationSessionWindow {field_name} must be a PointInTime value."
        )
    return value


@dataclass(frozen=True, slots=True)
class FuturesRecommendationSessionWindow:
    """Immutable intended validity window and contract cutoff for one contract."""

    contract: FuturesContract
    eligible_from: PointInTime
    valid_through: PointInTime
    contract_cutoff: PointInTime

    def __post_init__(self) -> None:
        if not isinstance(self.contract, FuturesContract):
            raise InvalidFuturesRecommendationSessionWindowError(
                "FuturesRecommendationSessionWindow contract must be a FuturesContract value."
            )
        eligible_from = _validate_instant(self.eligible_from, "eligible from")
        valid_through = _validate_instant(self.valid_through, "valid through")
        _validate_instant(self.contract_cutoff, "contract cutoff")
        if eligible_from.compare(valid_through) > 0:
            raise InvalidFuturesRecommendationSessionWindowError(
                "FuturesRecommendationSessionWindow eligible from cannot be later than "
                "valid through."
            )

    @property
    def expires_before_eligibility(self) -> bool:
        """Return whether the contract's last observation precedes the first eligible one."""
        return self.eligible_from.compare(self.contract_cutoff) > 0

    @property
    def fits_contract(self) -> bool:
        """Return whether the full intended window ends no later than the contract cutoff."""
        return self.valid_through.compare(self.contract_cutoff) <= 0

    def to_validity(self) -> RecommendationValidity:
        """Return the F-2 validity for a window that fits its contract."""
        if not self.fits_contract:
            raise InvalidFuturesRecommendationSessionWindowError(
                "A FuturesRecommendationSessionWindow that outlives its contract has no validity."
            )
        return RecommendationValidity(self.eligible_from, self.valid_through, self.contract_cutoff)

    def __str__(self) -> str:
        return (
            f"{self.contract} from {self.eligible_from} through {self.valid_through} "
            f"(contract cutoff {self.contract_cutoff})"
        )

    def __repr__(self) -> str:
        return (
            "FuturesRecommendationSessionWindow("
            f"contract={self.contract!r}, "
            f"eligible_from={self.eligible_from!r}, "
            f"valid_through={self.valid_through!r}, "
            f"contract_cutoff={self.contract_cutoff!r}"
            ")"
        )
