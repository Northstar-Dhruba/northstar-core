"""Structural guarantees for the options package.

These tests assert what the package must never acquire: a dependency on the
Futures family or on any other Core context above the shared derivatives layer,
a clock, randomness, a provider or outer layer, the legacy Generation-1
aggregates, market-listing identity, or a concept deferred to a later
milestone. They inspect imports and class definitions through the AST rather
than matching text, so prose in a docstring can neither cause a false failure
nor hide a real dependency.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import northstar_core.options as options
from northstar_core.options import value_objects

_OPTIONS_ROOT = Path(options.__file__).parent
_SOURCE_FILES = tuple(
    sorted(path for path in _OPTIONS_ROOT.rglob("*.py") if "__pycache__" not in path.parts)
)

# The only Core packages an option value may build on.
_ALLOWED_CORE_PREFIXES = (
    "northstar_core.foundation",
    "northstar_core.derivatives",
    "northstar_core.options",
)

# The only standard-library modules an option value may import.
_ALLOWED_STANDARD_MODULES = frozenset({"__future__", "dataclasses", "decimal", "enum"})

# Sibling and higher Core contexts that options must never reach into.
_FORBIDDEN_CORE_PREFIXES = (
    "northstar_core.futures",
    "northstar_core.paper_trading",
    "northstar_core.broker_execution",
    "northstar_core.strategy",
    "northstar_core.market_data",
    "northstar_core.orders",
    "northstar_core.trades",
    "northstar_core.portfolio",
    "northstar_core.domain",
)

# Clocks, randomness, environment, providers, persistence and outer layers.
_FORBIDDEN_MODULE_ROOTS = frozenset(
    {
        "datetime",
        "time",
        "calendar",
        "zoneinfo",
        "random",
        "uuid",
        "secrets",
        "os",
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

# Generation-1 names, plus the listing identity derivatives stay clear of.
_FORBIDDEN_NAMES = frozenset(
    {
        "ListingReference",
        "Listing",
        "Instrument",
        "Exchange",
        "ParticipantReference",
        "ParticipantIdentity",
        "Order",
        "OrderIdentity",
        "OrderStatus",
        "Trade",
        "TradeIdentity",
        "Portfolio",
        "PortfolioIdentity",
        "Price",
        "Money",
        "Quantity",
    }
)

# Concepts deferred to later milestones; none may appear as a class or export.
_DEFERRED_FRAGMENTS = (
    "greek",
    "delta",
    "gamma",
    "theta",
    "vega",
    "impliedvolatility",
    "volatility",
    "margin",
    "exercise",
    "assignment",
    "leg",
    "spread",
    "lotsize",
    "multiplier",
    "pnl",
    "profit",
    "premium",
    "pointvalue",
    "economics",
    "contractcount",
    "settlement",
    "chain",
    "position",
    "fill",
    "broker",
    "provider",
    "instrumentkey",
    "tradingsymbol",
    "derivativecontract",
)

_APPROVED_SURFACE = [
    "InvalidOptionContractError",
    "InvalidOptionProductReferenceError",
    "InvalidOptionProductSpecificationError",
    "InvalidOptionStrikeError",
    "OptionContract",
    "OptionProductReference",
    "OptionProductSpecification",
    "OptionRight",
    "OptionStrike",
]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _absolute_imports(tree: ast.Module) -> list[tuple[str, tuple[str, ...]]]:
    """Return (module, imported names) for every absolute import."""
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


def _class_names() -> set[str]:
    return {
        node.name
        for path in _SOURCE_FILES
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.ClassDef)
    }


def test_the_package_has_source_files_to_inspect() -> None:
    """Guards every sweep below from passing vacuously."""
    assert {path.name for path in _SOURCE_FILES} == {
        "__init__.py",
        "option_contract.py",
        "option_product_reference.py",
        "option_product_specification.py",
        "option_right.py",
        "option_strike.py",
    }
    assert len(_SOURCE_FILES) == 7


# -- dependency direction -----------------------------------------------------------


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_every_import_is_on_the_approved_list(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        allowed = module in _ALLOWED_STANDARD_MODULES or module.startswith(_ALLOWED_CORE_PREFIXES)
        assert allowed, f"{path.name} imports unapproved module {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_options_never_imports_futures_or_a_higher_core_context(path: Path) -> None:
    """Options and Futures are siblings; neither may depend on the other."""
    for module in _imported_modules(_parse(path)):
        for prefix in _FORBIDDEN_CORE_PREFIXES:
            assert not module.startswith(prefix), f"{path.name} imports {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_clock_randomness_provider_or_outer_layer_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert module.split(".")[0] not in _FORBIDDEN_MODULE_ROOTS, (
            f"{path.name} imports {module}; an option contract must stay reproducible."
        )


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_call_reads_a_clock(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"now", "utcnow", "today", "monotonic", "time"}, (
                f"{path.name} calls {node.func.attr}()."
            )


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_listing_legacy_or_equity_economics_name_is_imported(path: Path) -> None:
    """Derivative identity stays separate from listing identity and equity values."""
    forbidden = _imported_names(_parse(path)) & _FORBIDDEN_NAMES

    assert not forbidden, f"{path.name} imports {sorted(forbidden)}."


def test_importing_options_does_not_load_futures() -> None:
    """Checked in a fresh interpreter so this test module's own imports cannot mask it."""
    probe = (
        "import sys, northstar_core.options; "
        "print(sorted({name.split('.')[1] for name in sys.modules "
        "if name.startswith('northstar_core.')}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "['derivatives', 'foundation', 'options']"


# -- public surface -----------------------------------------------------------------


def test_the_public_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(options.__all__) == _APPROVED_SURFACE


def test_the_value_objects_package_exports_the_same_surface() -> None:
    assert sorted(value_objects.__all__) == _APPROVED_SURFACE


def test_every_exported_name_is_importable() -> None:
    for name in options.__all__:
        assert getattr(options, name) is getattr(value_objects, name)


def test_every_exported_type_is_defined_in_this_package() -> None:
    """Nothing is re-exported from Futures, Derivatives or Foundation."""
    for name in options.__all__:
        assert getattr(options, name).__module__.startswith("northstar_core.options.")


def test_the_package_exposes_no_persistence_use_case_or_policy() -> None:
    for name in options.__all__:
        assert not name.endswith(
            ("UseCase", "Repository", "Store", "Port", "Service", "Gateway", "Policy")
        )


# -- deferred concepts --------------------------------------------------------------


def test_no_deferred_concept_is_exported() -> None:
    for name in options.__all__:
        lowered = name.lower()
        for fragment in _DEFERRED_FRAGMENTS:
            assert fragment not in lowered, f"{name} exports deferred concept {fragment}."


def test_no_class_defines_a_deferred_concept() -> None:
    for name in _class_names():
        lowered = name.lower()
        for fragment in _DEFERRED_FRAGMENTS:
            assert fragment not in lowered, f"{name} defines deferred concept {fragment}."


def test_the_classes_defined_are_exactly_the_approved_types() -> None:
    assert sorted(_class_names()) == _APPROVED_SURFACE
