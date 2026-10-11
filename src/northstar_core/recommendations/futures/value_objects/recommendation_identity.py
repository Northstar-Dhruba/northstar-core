"""Opaque identity of one futures trade recommendation.

The identity is supplied by the caller. Core never generates, hashes or parses
it, and reads no clock or randomness to produce one. An Application service is
expected to derive it deterministically from at least the source research
decision and the recommendation policy version, so that regenerating the same
setup yields the same identity; that derivation is not defined here.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidFuturesTradeRecommendationIdentityError(ValidationError):
    """Raised when a FuturesTradeRecommendationIdentity value is invalid."""


def _normalize(identity: str) -> str:
    if identity is None:
        raise InvalidFuturesTradeRecommendationIdentityError(
            "FuturesTradeRecommendationIdentity cannot be None."
        )
    if not isinstance(identity, str):
        raise InvalidFuturesTradeRecommendationIdentityError(
            "FuturesTradeRecommendationIdentity must be a string."
        )

    normalized = identity.strip()
    if not normalized:
        raise InvalidFuturesTradeRecommendationIdentityError(
            "FuturesTradeRecommendationIdentity cannot be empty."
        )

    return normalized


@dataclass(frozen=True, slots=True)
class FuturesTradeRecommendationIdentity:
    """Immutable, caller-supplied opaque identity of one trade recommendation."""

    identity: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _normalize(self.identity))

    def __str__(self) -> str:
        return self.identity

    def __repr__(self) -> str:
        return f"FuturesTradeRecommendationIdentity(identity={self.identity!r})"
