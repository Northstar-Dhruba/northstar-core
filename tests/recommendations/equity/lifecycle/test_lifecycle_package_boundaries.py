"""EI-5B architecture guarantees for the equity lifecycle package (ADR-024, ADR-020).

The lifecycle is pure Core: it imports only Foundation and the equity
recommendation package, never the Futures recommendation package, a Futures,
Options, Paper Trading or Broker Execution context, the Application or
Infrastructure. It reads no clock and exposes no store, service, identity or
execution concept. These tests inspect the AST, so prose can neither cause a
false failure nor hide a dependency.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import northstar_core.recommendations.equity as equity
import northstar_core.recommendations.equity.lifecycle as lifecycle

_ROOT = Path(lifecycle.__file__).parent
_SOURCES = tuple(sorted(p for p in _ROOT.rglob("*.py") if "__pycache__" not in p.parts))

_ALLOWED_STANDARD = frozenset({"__future__", "dataclasses", "enum"})
_ALLOWED_CORE = (
    "northstar_core.foundation",
    "northstar_core.recommendations.equity.levels",
    "northstar_core.recommendations.equity.lifecycle",
)
_FORBIDDEN_CALLS = frozenset(
    {"now", "utcnow", "today", "monotonic", "time", "perf_counter", "sleep", "uuid1", "uuid4",
     "random", "getenv", "open", "print", "input", "float", "eval", "exec"}
)  # fmt: skip
_FORBIDDEN_NAME_FRAGMENTS = (
    "fill",
    "execution",
    "position",
    "portfolio",
    "broker",
    "pnl",
    "profit",
    "store",
    "repository",
    "identity",
    "issuance",
    "invalidat",
    "repair",
    "recovery",
    "usecase",
    "service",
    "port",
    "gateway",
    "scheduler",
    "monitor",
)

_APPROVED_SURFACE = sorted(
    [
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
)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _modules(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.append(node.module)
    return found


def test_the_package_has_exactly_its_source_files() -> None:
    assert {p.name for p in _SOURCES} == {
        "__init__.py",
        "event.py",
        "evidence.py",
        "lifecycle.py",
        "vocabulary.py",
        "window.py",
    }


def test_ar01_every_import_is_foundation_equity_levels_or_the_lifecycle_itself() -> None:
    for path in _SOURCES:
        for module in _modules(_tree(path)):
            allowed = module in _ALLOWED_STANDARD or module.startswith(_ALLOWED_CORE)
            assert allowed, f"{path.name} imports {module}."


def test_ar02_no_clock_randomness_float_or_io_call_is_made() -> None:
    for path in _SOURCES:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                assert name not in _FORBIDDEN_CALLS, f"{path.name} calls {name}()."
            if isinstance(node, ast.Constant):
                assert not isinstance(node.value, float), f"{path.name} has a float literal."


def test_importing_the_lifecycle_loads_no_other_context_or_outer_repository() -> None:
    probe = (
        "import sys; import northstar_core.recommendations.equity.lifecycle; "
        "print(sorted(n for n in sys.modules if n.startswith(('northstar', 'sqlite3'))))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    loaded = ast.literal_eval(result.stdout.strip())
    # The Futures market-data value objects are already loaded, transitively, by
    # the existing equity package root (EI-4B); the lifecycle adds no such import
    # (see the AST import check above). The Futures recommendation package is forbidden.
    for prefix in (
        "northstar_core.recommendations.futures",
        "northstar_core.options",
        "northstar_core.paper_trading",
        "northstar_core.broker_execution",
        "northstar_core.orders",
        "northstar_application",
        "northstar_infrastructure",
        "sqlite3",
    ):
        assert not any(name.startswith(prefix) for name in loaded), prefix


def test_the_public_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(lifecycle.__all__) == _APPROVED_SURFACE
    for name in lifecycle.__all__:
        module = getattr(lifecycle, name).__module__
        assert module.startswith("northstar_core.recommendations.equity.lifecycle."), name


def test_the_equity_root_surface_is_unchanged_by_the_lifecycle() -> None:
    assert not set(lifecycle.__all__) & set(equity.__all__)


def test_no_class_or_export_names_an_execution_store_identity_or_invalidation_concept() -> None:
    names = set(lifecycle.__all__) | {
        node.name
        for path in _SOURCES
        for node in ast.walk(_tree(path))
        if isinstance(node, ast.ClassDef)
    }
    for name in names:
        lowered = name.lower()
        for fragment in _FORBIDDEN_NAME_FRAGMENTS:
            assert fragment not in lowered, f"{name} names {fragment}."


def test_no_lifecycle_value_has_a_price_fill_or_order_field_beyond_bar_evidence() -> None:
    priced = {"low", "high"}  # only an interval assessment carries its candle's range
    for name in lifecycle.__all__:
        value = getattr(lifecycle, name)
        if not hasattr(value, "__dataclass_fields__"):
            continue
        for field in fields(value):
            lowered = field.name.lower()
            if name == "EquityLifecycleInterval" and lowered in priced:
                continue
            for word in ("price", "fill", "quantity", "order_", "broker", "pnl", "profit"):
                assert word not in lowered, f"{name}.{field.name}"
            assert lowered not in priced, f"{name}.{field.name}"
