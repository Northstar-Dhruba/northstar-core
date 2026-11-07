"""Structural guarantees for the equity recommendation package (ADR-020).

The package may build on Foundation, Domain and Strategy, and on nothing else:
never the Futures recommendation package, Derivatives, Futures, Paper Trading
or Broker Execution, never a clock, randomness, persistence or outer
repository. These tests inspect imports, calls and class names through the AST,
so prose in a docstring can neither cause a false failure nor hide a real
dependency.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import northstar_core.recommendations as recommendations
import northstar_core.recommendations.equity as equity

_EQUITY_ROOT = Path(equity.__file__).parent
_FUTURES_ROOT = Path(recommendations.__file__).parent / "futures"
_SOURCE_FILES = tuple(
    sorted(path for path in _EQUITY_ROOT.rglob("*.py") if "__pycache__" not in path.parts)
)

_ALLOWED_STANDARD = frozenset(
    {
        "__future__",
        "collections.abc",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "fractions",
        "math",
        "typing",
    }
)
_ALLOWED_CORE_PREFIXES = (
    "northstar_core.foundation",
    "northstar_core.domain",
    "northstar_core.strategy",
    "northstar_core.recommendations.equity",
)
_FORBIDDEN_CALLS = frozenset(
    {
        "now",
        "utcnow",
        "today",
        "monotonic",
        "time",
        "uuid1",
        "uuid4",
        "random",
        "getenv",
        "open",
        "print",
        "input",
        "float",
        "eval",
        "exec",
    }
)
_DEFERRED_FRAGMENTS = (
    "order",
    "fill",
    "execution",
    "position",
    "portfolio",
    "broker",
    "pnl",
    "profit",
    "margin",
    "leverage",
    "lifecycle",
    "store",
    "repository",
    "identity",
    "generator",
    "performance",
)

_APPROVED_SURFACE = sorted(
    [
        "EquityCostSide",
        "EquityEntryZone",
        "EquityIssuanceKind",
        "EquityPriceIncrement",
        "EquityRecommendationDefinition",
        "EquityRecommendationDirection",
        "EquityRecommendationLevels",
        "EquityRecommendationRejection",
        "EquityRecommendationRejectionReason",
        "EquityRecommendationTiming",
        "EquityResearchCandidateReference",
        "EquitySyntheticCostComponent",
        "EquitySyntheticCostSchedule",
        "EquitySyntheticGenerationPolicy",
        "EquitySyntheticRiskPolicy",
        "EquitySyntheticSizing",
        "EquitySyntheticVersion",
        "InvalidEquityPriceIncrementError",
        "InvalidEquityRecommendationDefinitionError",
        "InvalidEquityRecommendationLevelsError",
        "InvalidEquityRecommendationRejectionError",
        "InvalidEquityRecommendationTimingError",
        "InvalidEquityResearchCandidateReferenceError",
        "InvalidEquitySyntheticCostScheduleError",
        "InvalidEquitySyntheticGenerationPolicyError",
        "InvalidEquitySyntheticRiskPolicyError",
        "InvalidEquitySyntheticSizingError",
        "InvalidEquitySyntheticVersionError",
        "form_equity_recommendation",
    ]
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(tree: ast.Module) -> list[tuple[str, tuple[str, ...]]]:
    found: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, ()) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.append((node.module, tuple(alias.name for alias in node.names)))
    return found


def test_the_package_has_source_files_to_inspect() -> None:
    assert {path.name for path in _SOURCE_FILES} == {
        "__init__.py",
        "_exact.py",
        "cost_schedule.py",
        "definition.py",
        "formation.py",
        "levels.py",
        "rejection.py",
        "research_reference.py",
        "sizing.py",
        "synthetic_inputs.py",
        "timing.py",
    }


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_every_import_is_on_the_approved_list(path: Path) -> None:
    for module, names in _imports(_parse(path)):
        allowed = module in _ALLOWED_STANDARD or module.startswith(_ALLOWED_CORE_PREFIXES)
        assert allowed, f"{path.name} imports unapproved module {module}."
        if module == "datetime":
            assert names == ("date",), f"{path.name} may import only datetime.date."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_clock_randomness_float_or_io_call_is_made(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            assert name not in _FORBIDDEN_CALLS, f"{path.name} calls {name}()."
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float), f"{path.name} has a float literal."


def test_the_futures_and_equity_packages_never_import_each_other() -> None:
    for path in _SOURCE_FILES:
        for module, _ in _imports(_parse(path)):
            assert "recommendations.futures" not in module, path.name
    for path in _FUTURES_ROOT.rglob("*.py"):
        for module, _ in _imports(_parse(path)):
            assert "recommendations.equity" not in module, path.name


def test_importing_equity_loads_no_futures_recommendation_or_execution_context() -> None:
    probe = (
        "import sys; import northstar_core.recommendations.equity; "
        "print(sorted(n for n in sys.modules if n.startswith('northstar_core.')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    loaded = ast.literal_eval(result.stdout.strip())
    for prefix in (
        "northstar_core.recommendations.futures",
        "northstar_core.paper_trading",
        "northstar_core.broker_execution",
        "northstar_core.options",
    ):
        assert not any(name.startswith(prefix) for name in loaded), prefix


def test_no_class_or_export_names_a_deferred_concept() -> None:
    names = set(equity.__all__) | {
        node.name
        for path in _SOURCE_FILES
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.ClassDef)
    }
    for name in names:
        for fragment in _DEFERRED_FRAGMENTS:
            assert fragment not in name.lower(), f"{name} names deferred concept {fragment}."


def test_the_public_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(equity.__all__) == _APPROVED_SURFACE
    assert recommendations.__all__ == []
    for name in equity.__all__:
        module = getattr(equity, name).__module__
        assert module.startswith("northstar_core.recommendations.equity."), name


def test_the_package_exposes_no_persistence_use_case_or_service() -> None:
    for name in equity.__all__:
        assert not name.endswith(
            ("UseCase", "Repository", "Store", "Port", "Service", "Gateway", "Generator")
        )
