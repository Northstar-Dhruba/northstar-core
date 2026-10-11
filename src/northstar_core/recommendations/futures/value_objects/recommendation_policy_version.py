"""Version of the policy that produced one trade recommendation.

A trade recommendation is derived from a research decision by a generation
policy, and the same decision under a different policy is a different setup.
The version is opaque: Core neither defines nor interprets the policy, which
belongs to a later milestone.
"""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError


class InvalidRecommendationPolicyVersionError(ValidationError):
    """Raised when a RecommendationPolicyVersion value is invalid."""


def _normalize(version: str) -> str:
    if version is None:
        raise InvalidRecommendationPolicyVersionError("RecommendationPolicyVersion cannot be None.")
    if not isinstance(version, str):
        raise InvalidRecommendationPolicyVersionError(
            "RecommendationPolicyVersion must be a string."
        )

    normalized = version.strip()
    if not normalized:
        raise InvalidRecommendationPolicyVersionError(
            "RecommendationPolicyVersion cannot be empty."
        )

    return normalized


@dataclass(frozen=True, slots=True)
class RecommendationPolicyVersion:
    """Immutable opaque name and version of a recommendation-generation policy."""

    version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "version", _normalize(self.version))

    def __str__(self) -> str:
        return self.version

    def __repr__(self) -> str:
        return f"RecommendationPolicyVersion(version={self.version!r})"
