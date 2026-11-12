"""Equity recommendation lifecycle: states, events and pure transitions (EI-5B, ADR-024).

A pure, deterministic, equity-only model of one issued recommendation's
intraday lifecycle, evaluated from evidence the Application supplies:

- the eleven approved states, their outcome classes and the event kinds
  (EI5-D5); no ``INVALIDATED`` and no Futures state or ordering;
- the lifecycle window: levels, ``eligible_from``, the latest entry-bar opening,
  the entry window's end and the modeled exit boundary (EI5-D6, EI5-D7);
- evidence values: opaque snapshot and observation references, interval
  assessments in the EI-2A vocabulary, and explicit deficiencies;
- ``EquityRecommendationLifecycle``: a window and its events, whose state is
  the fold of the events, with ``advance`` over one observation and
  ``record_source_revision`` (EI5-D8).

Core does not issue recommendations, identify them, persist anything, read a
clock or evidence store, or infer an order, fill, execution price, exit price,
position or profit. Lifecycle facts are modeled level observations only. It
builds on Foundation and the equity levels; it never imports the Futures
recommendation package, the Application or Infrastructure.
"""

from northstar_core.recommendations.equity.lifecycle.event import (
    EquityLifecycleEvent,
    InvalidEquityLifecycleEventError,
)
from northstar_core.recommendations.equity.lifecycle.evidence import (
    EquityEvidenceDeficiency,
    EquityLifecycleEvidence,
    EquityLifecycleInterval,
    EquityLifecycleObservation,
    InvalidEquityLifecycleEvidenceError,
    InvalidEquityLifecycleObservationError,
)
from northstar_core.recommendations.equity.lifecycle.lifecycle import (
    EquityLifecycleAdvance,
    EquityLifecycleAdvanceStatus,
    EquityRecommendationLifecycle,
    InvalidEquityRecommendationLifecycleError,
)
from northstar_core.recommendations.equity.lifecycle.vocabulary import (
    EquityEvidenceDeficiencyKind,
    EquityIntrabarOrdering,
    EquityLifecycleCancellationReason,
    EquityLifecycleEventKind,
    EquityLifecycleIntervalOutcome,
    EquityLifecycleLevel,
    EquityLifecycleOutcomeClass,
    EquityLifecycleState,
    EquityRevisionMateriality,
)
from northstar_core.recommendations.equity.lifecycle.window import (
    EquityLifecycleWindow,
    InvalidEquityLifecycleWindowError,
)

__all__ = [
    "EquityEvidenceDeficiency",
    "EquityEvidenceDeficiencyKind",
    "EquityIntrabarOrdering",
    "EquityLifecycleAdvance",
    "EquityLifecycleAdvanceStatus",
    "EquityLifecycleCancellationReason",
    "EquityLifecycleEvent",
    "EquityLifecycleEventKind",
    "EquityLifecycleEvidence",
    "EquityLifecycleInterval",
    "EquityLifecycleIntervalOutcome",
    "EquityLifecycleLevel",
    "EquityLifecycleObservation",
    "EquityLifecycleOutcomeClass",
    "EquityLifecycleState",
    "EquityLifecycleWindow",
    "EquityRecommendationLifecycle",
    "EquityRevisionMateriality",
    "InvalidEquityLifecycleEventError",
    "InvalidEquityLifecycleEvidenceError",
    "InvalidEquityLifecycleObservationError",
    "InvalidEquityLifecycleWindowError",
    "InvalidEquityRecommendationLifecycleError",
]
