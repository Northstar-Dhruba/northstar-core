"""Structured reasoning that supports a Strategy-produced recommendation."""

from __future__ import annotations

from dataclasses import dataclass

from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.strategy.value_objects.recommendation import Recommendation


class InvalidExplanationReasonError(ValidationError):
    """Raised when an ExplanationReason value is invalid."""


class InvalidRecommendationExplanationError(ValidationError):
    """Raised when a RecommendationExplanation value is invalid."""


def _normalize_rationale(value: str) -> str:
    if value is None:
        raise InvalidExplanationReasonError("ExplanationReason rationale cannot be None.")
    if not isinstance(value, str):
        raise InvalidExplanationReasonError("ExplanationReason rationale must be a string.")

    normalized = value.strip()
    if not normalized:
        raise InvalidExplanationReasonError("ExplanationReason rationale cannot be empty.")
    return normalized


def _normalize_supporting_signals(value: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise InvalidExplanationReasonError("ExplanationReason supporting signals must be a tuple.")

    normalized_signals: list[str] = []
    for signal in value:
        if not isinstance(signal, str):
            raise InvalidExplanationReasonError(
                "ExplanationReason supporting signals must be strings."
            )
        normalized_signal = signal.strip()
        if not normalized_signal:
            raise InvalidExplanationReasonError(
                "ExplanationReason supporting signals cannot be empty."
            )
        normalized_signals.append(normalized_signal)

    return tuple(normalized_signals)


def _validate_recommendation(value: Recommendation) -> Recommendation:
    if value is None:
        raise InvalidRecommendationExplanationError(
            "RecommendationExplanation recommendation cannot be None."
        )
    if not isinstance(value, Recommendation):
        raise InvalidRecommendationExplanationError(
            "RecommendationExplanation recommendation must be a Recommendation value."
        )
    return value


def _validate_reasons(value: tuple[ExplanationReason, ...]) -> tuple[ExplanationReason, ...]:
    if value is None:
        raise InvalidRecommendationExplanationError(
            "RecommendationExplanation reasons cannot be None."
        )
    if not isinstance(value, tuple):
        raise InvalidRecommendationExplanationError(
            "RecommendationExplanation reasons must be a tuple."
        )
    if not value:
        raise InvalidRecommendationExplanationError(
            "RecommendationExplanation must contain at least one ExplanationReason."
        )
    if not all(isinstance(reason, ExplanationReason) for reason in value):
        raise InvalidRecommendationExplanationError(
            "RecommendationExplanation reasons must be ExplanationReason values."
        )
    return value


@dataclass(frozen=True, slots=True)
class ExplanationReason:
    """One rationale and its optional supporting signals."""

    rationale: str
    supporting_signals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rationale", _normalize_rationale(self.rationale))
        object.__setattr__(
            self,
            "supporting_signals",
            _normalize_supporting_signals(self.supporting_signals),
        )

    def __str__(self) -> str:
        return self.rationale

    def __repr__(self) -> str:
        return (
            "ExplanationReason("
            f"rationale={self.rationale!r}, "
            f"supporting_signals={self.supporting_signals!r}"
            ")"
        )


@dataclass(frozen=True, slots=True)
class RecommendationExplanation:
    """Structured reasoning that supports one existing Recommendation."""

    recommendation: Recommendation
    reasons: tuple[ExplanationReason, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "recommendation", _validate_recommendation(self.recommendation))
        object.__setattr__(self, "reasons", _validate_reasons(self.reasons))

    def __str__(self) -> str:
        return "; ".join(str(reason) for reason in self.reasons)

    def __repr__(self) -> str:
        return (
            "RecommendationExplanation("
            f"recommendation={self.recommendation!r}, "
            f"reasons={self.reasons!r}"
            ")"
        )
