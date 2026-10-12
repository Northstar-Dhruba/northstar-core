"""Structural guarantees for the futures trade recommendation package (ADR-017, ADR-018).

The package may build on Foundation, Derivatives, Futures and Strategy, and on
nothing else: never Paper Trading or Broker Execution, never a clock, randomness,
environment, provider, persistence or outer repository. Strategy, and every
other Core package, must never import it. These tests inspect imports and class
definitions through the AST rather than matching text, so prose in a docstring
can neither cause a false failure nor hide a real dependency.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import northstar_core
import northstar_core.recommendations as recommendations
import northstar_core.recommendations.futures as futures_recommendations
from northstar_core.recommendations.futures import generation, lifecycle, selection, value_objects

_CORE_ROOT = Path(northstar_core.__file__).parent
_PACKAGE_ROOT = Path(recommendations.__file__).parent
_SOURCE_FILES = tuple(
    sorted(path for path in _PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)
)
_OTHER_CORE_FILES = tuple(
    sorted(
        path
        for path in _CORE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts and _PACKAGE_ROOT not in path.parents
    )
)

_ALLOWED_CORE_PREFIXES = (
    "northstar_core.foundation",
    "northstar_core.derivatives",
    "northstar_core.futures",
    "northstar_core.strategy",
    "northstar_core.recommendations",
)

_ALLOWED_STANDARD_MODULES = frozenset({"__future__", "dataclasses", "enum", "functools"})

# Exact arithmetic for price levels (ADR-018); only generation may use it.
_GENERATION_STANDARD_MODULES = frozenset({"decimal", "fractions"})

# Research types that only candidate selection and generation may consume
# (ADR-017 permits Strategy types; generation maps BUY/SELL to LONG/SHORT under
# ADR-018; the trade setup and lifecycle stay free of research vocabulary).
_RESEARCH_NAMES = frozenset({"RecommendationAction", "FuturesRecommendation"})
_SELECTION_DIR = "selection"
_GENERATION_DIR = "generation"
_RESEARCH_CONSUMERS = frozenset({_SELECTION_DIR, _GENERATION_DIR})

_FORBIDDEN_CORE_PREFIXES = (
    "northstar_core.paper_trading",
    "northstar_core.broker_execution",
    "northstar_core.options",
    "northstar_core.market_data",
    "northstar_core.orders",
    "northstar_core.trades",
    "northstar_core.portfolio",
    "northstar_core.domain",
)

_FORBIDDEN_MODULE_ROOTS = frozenset(
    {
        "datetime",
        "time",
        "calendar",
        "zoneinfo",
        "random",
        "uuid",
        "hashlib",
        "secrets",
        "os",
        "json",
        "logging",
        "pathlib",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "sqlite3",
        "sqlalchemy",
        "databento",
        "upstox_client",
        "exchange_calendars",
        "pandas_market_calendars",
        "northstar_application",
        "northstar_infrastructure",
        "northstar_api",
    }
)

# Execution and research vocabularies the recommendation domain must not reuse.
_FORBIDDEN_NAMES = frozenset(
    {
        "OrderSide",
        "FuturesContractCount",
        "FuturesExecutionIntent",
        "FuturesPaperOrder",
        "FuturesPaperFill",
        "FuturesPosition",
        "FuturesPaperPortfolio",
        "RecommendationAction",
        "FuturesRecommendation",
        "Order",
        "Trade",
        "Portfolio",
        "Position",
        "Price",
        "Money",
    }
)

# Concepts outside F-2; none may appear as a class or export.
_DEFERRED_FRAGMENTS = (
    "orderside",
    "fill",
    "execution",
    "position",
    "portfolio",
    "broker",
    "pnl",
    "profit",
    "return",
    "margin",
    "quantity",
    "contractcount",
    "lotsize",
    "tick",
    "trailing",
    "notification",
    "alert",
    "publication",
    "repository",
    "store",
    "generator",
    "performance",
)

_VALUE_OBJECT_SURFACE = [
    "EntryZone",
    "FuturesResearchDecisionReference",
    "FuturesTradeRecommendation",
    "FuturesTradeRecommendationIdentity",
    "InvalidEntryZoneError",
    "InvalidFuturesResearchDecisionReferenceError",
    "InvalidFuturesTradeRecommendationError",
    "InvalidFuturesTradeRecommendationIdentityError",
    "InvalidPriceTargetError",
    "InvalidRecommendationPolicyVersionError",
    "InvalidRecommendationValidityError",
    "InvalidStopLossError",
    "PriceTarget",
    "RecommendationPolicyVersion",
    "RecommendationValidity",
    "StopLoss",
    "TradeDirection",
]

_LIFECYCLE_SURFACE = [
    "CoverageDeficiency",
    "FuturesTradeRecommendationEvent",
    "FuturesTradeRecommendationLifecycle",
    "IntrabarOrdering",
    "InvalidFuturesTradeRecommendationEventError",
    "InvalidFuturesTradeRecommendationExpiryError",
    "InvalidFuturesTradeRecommendationLifecycleError",
    "InvalidFuturesTradeRecommendationObservationError",
    "InvalidTimeExpiryEvidenceError",
    "ObservationCoverage",
    "RecommendationBoundary",
    "RecommendationEventKind",
    "RecommendationExpiryReason",
    "RecommendationStatus",
    "TimeExpiryEvidence",
]

_SELECTION_SURFACE = [
    "CandidateRejectionReason",
    "FuturesCandidateRejection",
    "FuturesCandidateSelection",
    "FuturesCandidateSelectionCriteria",
    "FuturesRecommendationCandidate",
    "FuturesResearchDecision",
    "InvalidFuturesCandidateRejectionError",
    "InvalidFuturesCandidateSelectionCriteriaError",
    "InvalidFuturesCandidateSelectionError",
    "InvalidFuturesRecommendationCandidateError",
    "InvalidFuturesResearchDecisionError",
]

_GENERATION_SURFACE = [
    "FuturesCandidateEvidence",
    "FuturesGenerationRejection",
    "FuturesRecommendationGeneration",
    "FuturesRecommendationGenerationPolicy",
    "FuturesRecommendationProposal",
    "FuturesRecommendationSessionWindow",
    "GenerationRejectionReason",
    "InvalidFuturesCandidateEvidenceError",
    "InvalidFuturesGenerationRejectionError",
    "InvalidFuturesRecommendationGenerationError",
    "InvalidFuturesRecommendationGenerationPolicyError",
    "InvalidFuturesRecommendationProposalError",
    "InvalidFuturesRecommendationSessionWindowError",
    "InvalidPriceMovementUnitError",
    "InvalidRewardToRiskError",
    "PriceMovementUnit",
    "RewardToRisk",
]

_APPROVED_SURFACE = sorted(
    _VALUE_OBJECT_SURFACE + _LIFECYCLE_SURFACE + _SELECTION_SURFACE + _GENERATION_SURFACE
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _absolute_imports(tree: ast.Module) -> list[tuple[str, tuple[str, ...]]]:
    imports: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, ()) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            imports.append((node.module, tuple(alias.name for alias in node.names)))
    return imports


def _imported_modules(tree: ast.Module) -> set[str]:
    return {module for module, _ in _absolute_imports(tree)}


def _imported_names(tree: ast.Module) -> set[str]:
    return {name for _, names in _absolute_imports(tree) for name in names}


def _subpackage(path: Path) -> str:
    """Return the futures sub-package a file belongs to, or "" for a package initializer."""
    parts = path.relative_to(_PACKAGE_ROOT).parts
    return parts[1] if len(parts) > 2 else ""


def _class_names() -> set[str]:
    return {
        node.name
        for path in _SOURCE_FILES
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.ClassDef)
    }


def test_the_package_has_source_files_to_inspect() -> None:
    """Guards every sweep below from passing vacuously."""
    assert {path.relative_to(_PACKAGE_ROOT).as_posix() for path in _SOURCE_FILES} == {
        "__init__.py",
        "futures/__init__.py",
        "futures/lifecycle/__init__.py",
        "futures/lifecycle/futures_trade_recommendation_lifecycle.py",
        "futures/lifecycle/recommendation_event.py",
        "futures/lifecycle/recommendation_status.py",
        "futures/lifecycle/time_expiry_evidence.py",
        "futures/value_objects/__init__.py",
        "futures/value_objects/entry_zone.py",
        "futures/value_objects/futures_trade_recommendation.py",
        "futures/value_objects/price_target.py",
        "futures/value_objects/recommendation_identity.py",
        "futures/value_objects/recommendation_policy_version.py",
        "futures/value_objects/recommendation_validity.py",
        "futures/value_objects/research_decision_reference.py",
        "futures/value_objects/stop_loss.py",
        "futures/value_objects/trade_direction.py",
        "futures/selection/__init__.py",
        "futures/selection/candidate_selection.py",
        "futures/selection/candidate_selection_criteria.py",
        "futures/selection/recommendation_candidate.py",
        "futures/selection/research_decision.py",
        "futures/generation/__init__.py",
        "futures/generation/_price_levels.py",
        "futures/generation/candidate_evidence.py",
        "futures/generation/generation_policy.py",
        "futures/generation/generation_rejection.py",
        "futures/generation/recommendation_generation.py",
        "futures/generation/recommendation_proposal.py",
        "futures/generation/reward_to_risk.py",
        "futures/generation/session_window.py",
    }
    assert len(_OTHER_CORE_FILES) > 100


# -- dependency direction -----------------------------------------------------------


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_every_import_is_on_the_approved_list(path: Path) -> None:
    standard = _ALLOWED_STANDARD_MODULES
    if _GENERATION_DIR in path.relative_to(_PACKAGE_ROOT).parts:
        standard = standard | _GENERATION_STANDARD_MODULES
    for module in _imported_modules(_parse(path)):
        allowed = module in standard or module.startswith(_ALLOWED_CORE_PREFIXES)
        assert allowed, f"{path.name} imports unapproved module {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_recommendations_never_import_execution_or_other_core_contexts(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        for prefix in _FORBIDDEN_CORE_PREFIXES:
            assert not module.startswith(prefix), f"{path.name} imports {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_clock_randomness_persistence_or_outer_layer_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert module.split(".")[0] not in _FORBIDDEN_MODULE_ROOTS, f"{path.name} imports {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_call_reads_a_clock_or_generates_an_identifier(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {
                "now",
                "utcnow",
                "today",
                "monotonic",
                "time",
                "uuid4",
                "uuid1",
                "random",
                "getenv",
                "open",
            }, f"{path.name} calls {node.func.attr}()."
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "print", "input", "id"}, (
                f"{path.name} calls {node.func.id}()."
            )


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_execution_or_research_action_name_is_imported(path: Path) -> None:
    forbidden = _imported_names(_parse(path)) & _FORBIDDEN_NAMES
    if _RESEARCH_CONSUMERS & set(path.relative_to(_PACKAGE_ROOT).parts):
        forbidden -= _RESEARCH_NAMES

    assert not forbidden, f"{path.name} imports {sorted(forbidden)}."


@pytest.mark.parametrize("path", _OTHER_CORE_FILES, ids=lambda path: path.name)
def test_no_other_core_package_imports_recommendations(path: Path) -> None:
    """Strategy in particular must never depend on Recommendations."""
    for module in _imported_modules(_parse(path)):
        assert not module.startswith("northstar_core.recommendations"), (
            f"{path.relative_to(_CORE_ROOT)} imports {module}."
        )


def _loaded_contexts(statement: str) -> list[str]:
    probe = (
        f"import sys; {statement}; "
        "print(sorted({name.split('.')[1] for name in sys.modules "
        "if name.startswith('northstar_core.')}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    return ast.literal_eval(result.stdout.strip())


def test_importing_recommendations_does_not_load_execution_contexts() -> None:
    """Checked in a fresh interpreter so this module's own imports cannot mask it."""
    loaded = _loaded_contexts("import northstar_core.recommendations.futures")

    assert "paper_trading" not in loaded
    assert "broker_execution" not in loaded
    assert "options" not in loaded
    assert {"foundation", "derivatives", "futures", "strategy", "recommendations"} <= set(loaded)


def test_importing_strategy_does_not_load_recommendations() -> None:
    assert "recommendations" not in _loaded_contexts("import northstar_core.strategy")


@pytest.mark.parametrize(
    "statement",
    [
        "import northstar_core.recommendations.futures.lifecycle",
        "import northstar_core.recommendations.futures.value_objects",
        "from northstar_core.recommendations.futures.lifecycle.recommendation_event "
        "import FuturesTradeRecommendationEvent",
        "import northstar_core.strategy; import northstar_core.recommendations.futures",
        "import northstar_core.recommendations.futures.generation",
        "from northstar_core.recommendations.futures.generation.recommendation_generation "
        "import FuturesRecommendationGeneration",
    ],
    ids=[
        "lifecycle-first",
        "value-objects-first",
        "deep-module-first",
        "strategy-first",
        "generation-first",
        "deep-generation-module-first",
    ],
)
def test_every_entry_point_imports_without_a_cycle(statement: str) -> None:
    assert "recommendations" in _loaded_contexts(statement)


# -- public surface -----------------------------------------------------------------


def test_the_parent_package_exports_nothing() -> None:
    assert recommendations.__all__ == []


def test_the_public_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(futures_recommendations.__all__) == _APPROVED_SURFACE


def test_the_value_objects_package_exports_its_part_of_the_surface() -> None:
    assert sorted(value_objects.__all__) == _VALUE_OBJECT_SURFACE


def test_the_lifecycle_package_exports_its_part_of_the_surface() -> None:
    assert sorted(lifecycle.__all__) == _LIFECYCLE_SURFACE


def test_the_selection_package_exports_its_part_of_the_surface() -> None:
    assert sorted(selection.__all__) == _SELECTION_SURFACE


def test_the_generation_package_exports_its_part_of_the_surface() -> None:
    assert sorted(generation.__all__) == _GENERATION_SURFACE


def test_only_selection_and_generation_consume_research_types() -> None:
    """The trade setup and lifecycle never see BUY/SELL/HOLD research vocabulary."""
    importers = {
        _subpackage(path)
        for path in _SOURCE_FILES
        if _imported_names(_parse(path)) & _RESEARCH_NAMES
    }

    assert importers == _RESEARCH_CONSUMERS


def test_only_generation_uses_decimal_or_rational_arithmetic() -> None:
    users = {
        _subpackage(path)
        for path in _SOURCE_FILES
        if _imported_modules(_parse(path)) & _GENERATION_STANDARD_MODULES
    }

    assert users == {_GENERATION_DIR}


def test_the_setup_lifecycle_and_selection_never_import_generation() -> None:
    """Generation builds on F-2 and F-3; neither depends on it."""
    for path in _SOURCE_FILES:
        if _subpackage(path) in {"value_objects", "lifecycle", "selection"}:
            for module in _imported_modules(_parse(path)):
                assert ".generation" not in module, f"{path.name} imports {module}."


def test_selection_never_assigns_a_trade_direction() -> None:
    """F-3 keeps the research action; LONG/SHORT mapping belongs to F-4 (ADR-017)."""
    for path in _SOURCE_FILES:
        if _SELECTION_DIR in path.relative_to(_PACKAGE_ROOT).parts:
            assert "TradeDirection" not in _imported_names(_parse(path)), path.name


def test_every_exported_name_is_importable_from_its_owner() -> None:
    for name in futures_recommendations.__all__:
        if name in _GENERATION_SURFACE:
            owner = generation
        elif name in _LIFECYCLE_SURFACE:
            owner = lifecycle
        elif name in _SELECTION_SURFACE:
            owner = selection
        else:
            owner = value_objects
        assert getattr(futures_recommendations, name) is getattr(owner, name)


def test_every_exported_type_is_defined_in_this_package() -> None:
    """Nothing is re-exported from Futures, Derivatives, Strategy or Foundation."""
    for name in futures_recommendations.__all__:
        module = getattr(futures_recommendations, name).__module__
        assert module.startswith("northstar_core.recommendations.futures.")


def test_the_package_exposes_no_persistence_use_case_or_service() -> None:
    for name in futures_recommendations.__all__:
        assert not name.endswith(
            ("UseCase", "Repository", "Store", "Port", "Service", "Gateway", "Generator")
        )


# -- deferred concepts --------------------------------------------------------------


def test_no_deferred_concept_is_exported_or_defined() -> None:
    for name in set(futures_recommendations.__all__) | _class_names():
        lowered = name.lower()
        for fragment in _DEFERRED_FRAGMENTS:
            assert fragment not in lowered, f"{name} names deferred concept {fragment}."


def test_the_classes_defined_are_exactly_the_approved_types() -> None:
    assert sorted(_class_names()) == _APPROVED_SURFACE
