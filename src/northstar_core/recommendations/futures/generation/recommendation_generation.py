"""Deterministic generation of trade-setup proposals from one candidate selection.

``FuturesRecommendationGeneration.generate(...)`` turns the candidates of one
F-3 selection into validated FuturesRecommendationProposals and records why
every other candidate produced none (ADR-018). It is pure: it reads no clock,
generates no identifier, performs no I/O and mutates nothing.

The evaluation sequence is fixed:

1. Validate every input. Malformed or contradictory input raises
   InvalidFuturesRecommendationGenerationError; it is never relabelled as a
   rejected trade. Identical repeats of evidence, windows or lifecycles are one
   value.
2. Per candidate: the approved strategy, a supplied window, and a contract that
   can support the full window -- never truncated.
3. Per product, over the eligible candidates: contradictory BUY and SELL
   research rejects the whole group; SELL with SHORT disabled is rejected;
   otherwise the nearest expiration is selected and the others are rejected.
   Contracts of one product differ by expiry and each has at most one eligible
   candidate, so the nearest is unique. Nearest is a deterministic rule, not a
   liquidity claim, and there is no fallback to another expiry.
4. On the selected candidate: open-recommendation contradiction and
   duplication, evidence, price levels and worst-entry reward-to-risk.

One open recommendation per product (ADR-018, P-1): across every expiry of a
futures product, at most one non-terminal recommendation may exist. A selected
candidate is therefore checked against every supplied non-terminal lifecycle of
its product -- compared by FuturesProductReference equality, never by contract
or display text -- and rejected CONTRADICTS_OPEN_RECOMMENDATION if any of them
has the other direction, otherwise DUPLICATE_OPEN_RECOMMENDATION if any has the
same direction. The check is set-based, so the order of the supplied lifecycles
cannot change it. Terminal lifecycles, by ``is_terminal``, are validated and
then ignored: they block nothing.

A supplied state that already breaks exclusivity -- several non-terminal
recommendations on one product -- is not repaired. It fails closed: holding
both directions, it contradicts any new candidate on the product; holding one
direction several times, it duplicates a same-direction candidate and
contradicts the other. Each such product is listed in ``exclusivity_breaches``
for Application reconciliation. Core cannot know about an open recommendation
the caller did not supply; completeness of that view is an Application duty.

Research action BUY maps to LONG and SELL to SHORT; the research action itself
is never altered. Every candidate ends as exactly one proposal or one
rejection, and the result does not depend on input order: proposals and
rejections are each sorted by product, expiration, timeframe, strategy and
decision instant, as F-3 sorts.

A stored generation validates its own structure but cannot recompute itself,
because it does not hold the evidence, windows and open recommendations it was
generated from. It does enforce what its own parts imply: no proposal is for a
product listed in ``exclusivity_breaches``, since generation rejects every
candidate of such a product. That says nothing about whether the supplied open
recommendations were complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, Inexact, Rounded
from fractions import Fraction
from functools import cmp_to_key

from northstar_core.derivatives import QuoteValue
from northstar_core.foundation.exceptions.validation import ValidationError
from northstar_core.foundation.value_objects import PointInTime
from northstar_core.futures import FuturesContract, FuturesProductReference
from northstar_core.recommendations.futures.generation._price_levels import (
    entry_bounds,
    fixed_point,
    stop_and_target,
    to_decimal,
    total_absolute_change,
    worst_entry_reward_and_risk,
)
from northstar_core.recommendations.futures.generation.candidate_evidence import (
    FuturesCandidateEvidence,
)
from northstar_core.recommendations.futures.generation.generation_policy import (
    FuturesRecommendationGenerationPolicy,
)
from northstar_core.recommendations.futures.generation.generation_rejection import (
    FuturesGenerationRejection,
    GenerationRejectionReason,
)
from northstar_core.recommendations.futures.generation.recommendation_proposal import (
    FuturesRecommendationProposal,
)
from northstar_core.recommendations.futures.generation.reward_to_risk import (
    PriceMovementUnit,
    RewardToRisk,
)
from northstar_core.recommendations.futures.generation.session_window import (
    FuturesRecommendationSessionWindow,
)
from northstar_core.recommendations.futures.lifecycle import FuturesTradeRecommendationLifecycle
from northstar_core.recommendations.futures.selection import (
    FuturesCandidateSelection,
    FuturesRecommendationCandidate,
)
from northstar_core.recommendations.futures.value_objects import (
    EntryZone,
    FuturesResearchDecisionReference,
    FuturesTradeRecommendationIdentity,
    PriceTarget,
    StopLoss,
    TradeDirection,
)
from northstar_core.strategy import ExplanationReason, RecommendationAction

Reason = GenerationRejectionReason

# The approved, versioned research-action-to-direction mapping (ADR-018, F4-D1).
# HOLD never reaches generation: F-3 rejects it.
_DIRECTIONS: dict[RecommendationAction, TradeDirection] = {
    RecommendationAction("BUY"): TradeDirection.LONG,
    RecommendationAction("SELL"): TradeDirection.SHORT,
}
_SELL = RecommendationAction("SELL")


class InvalidFuturesRecommendationGenerationError(ValidationError):
    """Raised when generation input is invalid or a stored generation is malformed."""


# -- ordering ---------------------------------------------------------------------------


def _compare_sources(
    first: FuturesResearchDecisionReference, second: FuturesResearchDecisionReference
) -> int:
    first_key = (
        first.contract.product,
        first.contract.expiration_date,
        first.timeframe.value,
        first.strategy_identity.identity,
    )
    second_key = (
        second.contract.product,
        second.contract.expiration_date,
        second.timeframe.value,
        second.strategy_identity.identity,
    )
    if first_key != second_key:
        return -1 if first_key < second_key else 1
    return first.decision_instant.compare(second.decision_instant)


_SOURCE_ORDER = cmp_to_key(_compare_sources)


def _ordered(sources: list[FuturesResearchDecisionReference]) -> bool:
    return all(
        _compare_sources(earlier, later) < 0
        for earlier, later in zip(sources, sources[1:], strict=False)
    )


# -- input validation -------------------------------------------------------------------


def _require_tuple_of(value: object, expected: type, field_name: str) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, expected) for item in value):
        raise InvalidFuturesRecommendationGenerationError(
            f"FuturesRecommendationGeneration {field_name} must be a tuple of "
            f"{expected.__name__} values."
        )


def _index_evidence(
    evidence: tuple[FuturesCandidateEvidence, ...],
    sources: set[FuturesResearchDecisionReference],
) -> dict[FuturesResearchDecisionReference, FuturesCandidateEvidence]:
    by_source: dict[FuturesResearchDecisionReference, FuturesCandidateEvidence] = {}
    for item in evidence:
        if item.source not in sources:
            raise InvalidFuturesRecommendationGenerationError(
                f"Evidence for {item.source} does not belong to a candidate of the selection."
            )
        known = by_source.setdefault(item.source, item)
        if known != item:
            raise InvalidFuturesRecommendationGenerationError(
                f"Two different evidence values were supplied for {item.source}."
            )
    return by_source


def _index_windows(
    windows: tuple[FuturesRecommendationSessionWindow, ...],
    contracts: set[FuturesContract],
    issued_at: PointInTime,
) -> dict[FuturesContract, FuturesRecommendationSessionWindow]:
    by_contract: dict[FuturesContract, FuturesRecommendationSessionWindow] = {}
    for window in windows:
        if window.contract not in contracts:
            raise InvalidFuturesRecommendationGenerationError(
                f"The session window for {window.contract} does not belong to a candidate contract."
            )
        if issued_at.compare(window.eligible_from) >= 0:
            raise InvalidFuturesRecommendationGenerationError(
                f"The session window for {window.contract} must become eligible strictly after "
                f"issuance at {issued_at}."
            )
        known = by_contract.setdefault(window.contract, window)
        if known != window:
            raise InvalidFuturesRecommendationGenerationError(
                f"Two different session windows were supplied for {window.contract}."
            )
    return by_contract


def _open_by_product(
    lifecycles: tuple[FuturesTradeRecommendationLifecycle, ...], issued_at: PointInTime
) -> dict[FuturesProductReference, tuple[FuturesTradeRecommendationLifecycle, ...]]:
    """Validate every supplied lifecycle, then group the non-terminal ones by product.

    Terminal lifecycles are validated like the others -- issuance and identity --
    and then excluded: a finished recommendation blocks nothing.
    """
    by_identity: dict[FuturesTradeRecommendationIdentity, FuturesTradeRecommendationLifecycle] = {}
    for lifecycle in lifecycles:
        recommendation = lifecycle.recommendation
        if recommendation.issued_at.compare(issued_at) > 0:
            raise InvalidFuturesRecommendationGenerationError(
                f"Open recommendation {recommendation.identity} was issued after {issued_at}."
            )
        known = by_identity.setdefault(recommendation.identity, lifecycle)
        if known != lifecycle:
            raise InvalidFuturesRecommendationGenerationError(
                f"Two different lifecycles share recommendation identity {recommendation.identity}."
            )
    by_product: dict[FuturesProductReference, list[FuturesTradeRecommendationLifecycle]] = {}
    for lifecycle in by_identity.values():
        if not lifecycle.is_terminal:
            by_product.setdefault(lifecycle.recommendation.contract.product, []).append(lifecycle)
    return {product: tuple(group) for product, group in by_product.items()}


# -- per-candidate decisions ------------------------------------------------------------


def _candidate_rejection(
    policy: FuturesRecommendationGenerationPolicy,
    candidate: FuturesRecommendationCandidate,
    windows: dict[FuturesContract, FuturesRecommendationSessionWindow],
) -> GenerationRejectionReason | None:
    if candidate.strategy_identity not in policy.approved_strategies:
        return Reason.STRATEGY_NOT_APPROVED
    window = windows.get(candidate.contract)
    if window is None:
        return Reason.MISSING_SESSION_WINDOW
    if window.expires_before_eligibility:
        return Reason.CONTRACT_EXPIRED
    if not window.fits_contract:
        return Reason.INSUFFICIENT_CONTRACT_LIFE
    return None


def _open_rejection(
    direction: TradeDirection,
    open_on_product: tuple[FuturesTradeRecommendationLifecycle, ...],
) -> GenerationRejectionReason | None:
    """Apply one-open-recommendation-per-product to a candidate of that product."""
    directions = {lifecycle.recommendation.direction for lifecycle in open_on_product}
    if directions - {direction}:
        return Reason.CONTRADICTS_OPEN_RECOMMENDATION
    if direction in directions:
        return Reason.DUPLICATE_OPEN_RECOMMENDATION
    return None


def _thesis(
    candidate: FuturesRecommendationCandidate,
    direction: TradeDirection,
    policy: FuturesRecommendationGenerationPolicy,
    reference: QuoteValue,
    unit: PriceMovementUnit,
    worst_entry: Decimal,
    reward_to_risk: RewardToRisk,
) -> tuple[ExplanationReason, ...]:
    source = candidate.source
    return (
        ExplanationReason(
            f"Research {candidate.research_action} by {source.strategy_identity} on "
            f"{source.contract} decided at {source.decision_instant}",
            candidate.decision.assessment.asset_analysis.summarized_signals,
        ),
        ExplanationReason(
            f"{direction} setup under policy {policy.version}",
            (
                f"reference close {fixed_point(reference.value)}",
                f"mean absolute close-to-close change {unit}",
                f"worst entry {fixed_point(worst_entry)}",
                f"reward {fixed_point(reward_to_risk.reward)} against risk "
                f"{fixed_point(reward_to_risk.risk)}",
            ),
        ),
    )


def _generate_one(
    policy: FuturesRecommendationGenerationPolicy,
    candidate: FuturesRecommendationCandidate,
    window: FuturesRecommendationSessionWindow,
    evidence: FuturesCandidateEvidence | None,
    open_on_product: tuple[FuturesTradeRecommendationLifecycle, ...],
    issued_at: PointInTime,
) -> FuturesRecommendationProposal | GenerationRejectionReason:
    direction = _DIRECTIONS[candidate.research_action]
    open_reason = _open_rejection(direction, open_on_product)
    if open_reason is not None:
        return open_reason
    if evidence is None:
        return Reason.MISSING_MARKET_EVIDENCE

    context = evidence.context
    closes = tuple(close.value for close in context.recent_closes)
    total = total_absolute_change(closes, policy.lookback_changes)
    if total is None:
        return Reason.INSUFFICIENT_HISTORY
    if total == 0:
        return Reason.ZERO_PRICE_MOVEMENT_UNIT

    unit = Fraction(total) / policy.lookback_changes
    reference = context.latest_quote
    low, high = entry_bounds(reference.value, unit, policy.entry_multiplier, policy.price_increment)
    if low > high:
        return Reason.DEGENERATE_ENTRY_ZONE
    stop, target = stop_and_target(
        direction,
        low,
        high,
        unit,
        policy.stop_multiplier,
        policy.target_multiplier,
        policy.price_increment,
    )
    entry_low, entry_high = to_decimal(low), to_decimal(high)
    stop_price, target_price = to_decimal(stop), to_decimal(target)
    worst, reward, risk = worst_entry_reward_and_risk(
        direction, entry_low, entry_high, stop_price, target_price
    )
    if reward <= 0 or risk <= 0:
        return Reason.INVALID_PRICE_ORDER
    reward_to_risk = RewardToRisk(reward, risk)
    if not reward_to_risk.meets(policy.min_reward_to_risk):
        return Reason.INSUFFICIENT_REWARD_TO_RISK

    movement_unit = PriceMovementUnit(total, policy.lookback_changes)
    return FuturesRecommendationProposal(
        contract=candidate.contract,
        direction=direction,
        entry=EntryZone(QuoteValue(entry_low), QuoteValue(entry_high)),
        stop=StopLoss(QuoteValue(stop_price)),
        target=PriceTarget(QuoteValue(target_price)),
        validity=window.to_validity(),
        source=candidate.source,
        policy_version=policy.version,
        issued_at=issued_at,
        thesis=_thesis(
            candidate, direction, policy, reference, movement_unit, worst, reward_to_risk
        ),
        reference_price=reference,
        movement_unit=movement_unit,
        reward_to_risk=reward_to_risk,
    )


# -- the generation -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FuturesRecommendationGeneration:
    """Immutable result of generation: policy, issuance, proposals and rejections."""

    policy: FuturesRecommendationGenerationPolicy
    issued_at: PointInTime
    proposals: tuple[FuturesRecommendationProposal, ...]
    rejections: tuple[FuturesGenerationRejection, ...]
    exclusivity_breaches: tuple[FuturesProductReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.policy, FuturesRecommendationGenerationPolicy):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration policy must be a "
                "FuturesRecommendationGenerationPolicy value."
            )
        if not isinstance(self.issued_at, PointInTime):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration issued at must be a PointInTime value."
            )
        _require_tuple_of(self.proposals, FuturesRecommendationProposal, "proposals")
        _require_tuple_of(self.rejections, FuturesGenerationRejection, "rejections")
        _require_tuple_of(
            self.exclusivity_breaches, FuturesProductReference, "exclusivity breaches"
        )
        if list(self.exclusivity_breaches) != sorted(set(self.exclusivity_breaches)):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration exclusivity breaches must be distinct and sorted."
            )

        breached = set(self.exclusivity_breaches)
        for proposal in self.proposals:
            if proposal.contract.product in breached:
                raise InvalidFuturesRecommendationGenerationError(
                    f"Proposal for {proposal.source} is on {proposal.contract.product}, whose "
                    "supplied open recommendations already break exclusivity."
                )
            if (
                proposal.policy_version != self.policy.version
                or proposal.issued_at.compare(self.issued_at) != 0
                or proposal.strategy_identity != self.policy.strategy
            ):
                raise InvalidFuturesRecommendationGenerationError(
                    f"Proposal for {proposal.source} was not generated under this policy "
                    "and issuance."
                )

        proposal_sources = [proposal.source for proposal in self.proposals]
        rejection_sources = [rejection.source for rejection in self.rejections]
        if len(set(proposal_sources + rejection_sources)) != len(
            proposal_sources + rejection_sources
        ):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration disposes of a candidate more than once."
            )
        if not _ordered(proposal_sources) or not _ordered(rejection_sources):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration proposals and rejections must be in "
                "canonical order."
            )

    @classmethod
    def generate(
        cls,
        policy: FuturesRecommendationGenerationPolicy,
        selection: FuturesCandidateSelection,
        evidence: tuple[FuturesCandidateEvidence, ...],
        windows: tuple[FuturesRecommendationSessionWindow, ...],
        open_recommendations: tuple[FuturesTradeRecommendationLifecycle, ...],
        issued_at: PointInTime,
    ) -> FuturesRecommendationGeneration:
        """Return the deterministic proposals and rejections for one selection."""
        if not isinstance(policy, FuturesRecommendationGenerationPolicy):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration policy must be a "
                "FuturesRecommendationGenerationPolicy value."
            )
        if not isinstance(selection, FuturesCandidateSelection):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration selection must be a "
                "FuturesCandidateSelection value."
            )
        _require_tuple_of(evidence, FuturesCandidateEvidence, "evidence")
        _require_tuple_of(windows, FuturesRecommendationSessionWindow, "windows")
        _require_tuple_of(
            open_recommendations, FuturesTradeRecommendationLifecycle, "open recommendations"
        )
        if not isinstance(issued_at, PointInTime):
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration issued at must be a PointInTime value."
            )
        if issued_at.compare(selection.criteria.session_close) < 0:
            raise InvalidFuturesRecommendationGenerationError(
                "FuturesRecommendationGeneration cannot be issued before the selection session "
                f"closes at {selection.criteria.session_close}."
            )

        candidates = selection.candidates
        evidence_by_source = _index_evidence(
            evidence, {candidate.source for candidate in candidates}
        )
        windows_by_contract = _index_windows(
            windows, {candidate.contract for candidate in candidates}, issued_at
        )
        open_by_product = _open_by_product(open_recommendations, issued_at)

        proposals: list[FuturesRecommendationProposal] = []
        rejections: list[FuturesGenerationRejection] = []

        def reject(candidate: FuturesRecommendationCandidate, reason: Reason) -> None:
            rejections.append(FuturesGenerationRejection(candidate, reason))

        eligible: dict[FuturesProductReference, list[FuturesRecommendationCandidate]] = {}
        for candidate in candidates:
            reason = _candidate_rejection(policy, candidate, windows_by_contract)
            if reason is None:
                eligible.setdefault(candidate.contract.product, []).append(candidate)
            else:
                reject(candidate, reason)

        for group in eligible.values():
            actions = {candidate.research_action for candidate in group}
            if len(actions) > 1:
                for candidate in group:
                    reject(candidate, Reason.CONTRADICTORY_PRODUCT_DIRECTION)
                continue
            if actions == {_SELL} and not policy.short_enabled:
                for candidate in group:
                    reject(candidate, Reason.SHORT_NOT_ENABLED)
                continue

            nearest = min(group, key=lambda candidate: candidate.contract.expiration_date)
            for candidate in group:
                if candidate is not nearest:
                    reject(candidate, Reason.NOT_NEAREST_ELIGIBLE_CONTRACT)

            try:
                outcome = _generate_one(
                    policy,
                    nearest,
                    windows_by_contract[nearest.contract],
                    evidence_by_source.get(nearest.source),
                    open_by_product.get(nearest.contract.product, ()),
                    issued_at,
                )
            except (Inexact, Rounded) as exc:
                raise InvalidFuturesRecommendationGenerationError(
                    f"A level generated for {nearest.source} cannot be represented exactly."
                ) from exc
            if isinstance(outcome, FuturesRecommendationProposal):
                proposals.append(outcome)
            else:
                reject(nearest, outcome)

        return cls(
            policy=policy,
            issued_at=issued_at,
            proposals=tuple(sorted(proposals, key=lambda item: _SOURCE_ORDER(item.source))),
            rejections=tuple(sorted(rejections, key=lambda item: _SOURCE_ORDER(item.source))),
            exclusivity_breaches=tuple(
                sorted(product for product, group in open_by_product.items() if len(group) > 1)
            ),
        )

    def __str__(self) -> str:
        return (
            f"{len(self.proposals)} proposal(s), {len(self.rejections)} rejection(s) "
            f"under {self.policy.version} issued {self.issued_at}"
        )

    def __repr__(self) -> str:
        return (
            "FuturesRecommendationGeneration("
            f"policy={self.policy!r}, "
            f"issued_at={self.issued_at!r}, "
            f"proposals={self.proposals!r}, "
            f"rejections={self.rejections!r}, "
            f"exclusivity_breaches={self.exclusivity_breaches!r}"
            ")"
        )
