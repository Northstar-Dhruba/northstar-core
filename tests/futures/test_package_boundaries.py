"""Structural guarantees for the derivatives and futures packages.

These tests assert what the packages must never acquire: a clock, randomness, a
dependency on the legacy Generation-1 aggregates, market-listing identity, or a
dependency between derivative families. They inspect imports through the AST
rather than matching text, so prose in a docstring can neither cause a false
failure nor hide a real dependency.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import northstar_core.derivatives as derivatives
import northstar_core.futures as futures

_DERIVATIVES_ROOT = Path(derivatives.__file__).parent
_FUTURES_ROOT = Path(futures.__file__).parent


def _sources(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


_DERIVATIVES_FILES = _sources(_DERIVATIVES_ROOT)
_FUTURES_FILES = _sources(_FUTURES_ROOT)
_ALL_FILES = _DERIVATIVES_FILES + _FUTURES_FILES

# Modules that would make a contract irreproducible or provider-dependent.
_FORBIDDEN_MODULE_ROOTS = frozenset({"random", "uuid", "secrets", "os", "time", "requests"})

# Generation-1 packages this design deliberately does not build on.
_FORBIDDEN_MODULE_PREFIXES = (
    "northstar_core.orders",
    "northstar_core.trades",
    "northstar_core.portfolio",
    "northstar_core.domain.listing",
    "northstar_core.market_data",
)

# Generation-1 names, plus the listing identity derivatives must stay clear of.
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
    }
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _imported_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def test_both_packages_have_sources_to_inspect() -> None:
    """Guards every sweep below from passing vacuously."""
    assert len(_DERIVATIVES_FILES) >= 3
    assert len(_FUTURES_FILES) >= 4


@pytest.mark.parametrize("path", _ALL_FILES, ids=lambda path: path.name)
def test_no_randomness_or_provider_dependency_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert module.split(".")[0] not in _FORBIDDEN_MODULE_ROOTS, (
            f"{path.name} imports {module}; a contract must stay reproducible."
        )


@pytest.mark.parametrize("path", _ALL_FILES, ids=lambda path: path.name)
def test_no_legacy_package_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        for prefix in _FORBIDDEN_MODULE_PREFIXES:
            assert not module.startswith(prefix), f"{path.name} imports legacy {module}."


@pytest.mark.parametrize("path", _ALL_FILES, ids=lambda path: path.name)
def test_no_listing_or_legacy_name_is_imported(path: Path) -> None:
    """Derivative identity stays separate from market-listing identity."""
    forbidden = _imported_names(_parse(path)) & _FORBIDDEN_NAMES

    assert not forbidden, f"{path.name} imports {sorted(forbidden)}."


@pytest.mark.parametrize("path", _ALL_FILES, ids=lambda path: path.name)
def test_no_call_reads_a_clock(path: Path) -> None:
    """datetime is permitted for calendar validation, but never for the time now."""
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"now", "utcnow", "today", "monotonic", "time"}, (
                f"{path.name} calls {node.func.attr}()."
            )


@pytest.mark.parametrize("path", _DERIVATIVES_FILES, ids=lambda path: path.name)
def test_derivatives_depends_on_no_derivative_family(path: Path) -> None:
    """Options must never have to depend on Futures to reach a shared concept."""
    for module in _imported_modules(_parse(path)):
        assert not module.startswith("northstar_core.futures"), f"{path.name} imports {module}."
        assert not module.startswith("northstar_core.options"), f"{path.name} imports {module}."


@pytest.mark.parametrize("path", _DERIVATIVES_FILES, ids=lambda path: path.name)
def test_derivatives_depends_only_on_foundation(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        if not module.startswith("northstar_core"):
            continue
        assert module.startswith(("northstar_core.foundation", "northstar_core.derivatives")), (
            f"{path.name} imports {module}."
        )


@pytest.mark.parametrize("path", _FUTURES_FILES, ids=lambda path: path.name)
def test_futures_depends_only_on_foundation_and_derivatives(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        if not module.startswith("northstar_core"):
            continue
        assert module.startswith(
            (
                "northstar_core.foundation",
                "northstar_core.derivatives",
                "northstar_core.futures",
            )
        ), f"{path.name} imports {module}."


@pytest.mark.parametrize("path", _FUTURES_FILES, ids=lambda path: path.name)
def test_futures_never_imports_options(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert not module.startswith("northstar_core.options"), f"{path.name} imports {module}."


def test_the_derivatives_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(derivatives.__all__) == [
        "ExpirationDate",
        "InvalidExpirationDateError",
        "InvalidUnderlyingReferenceError",
        "UnderlyingReference",
    ]


def test_the_futures_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(futures.__all__) == [
        "FuturesContract",
        "FuturesProductReference",
        "FuturesProductSpecification",
        "InvalidFuturesContractError",
        "InvalidFuturesProductReferenceError",
        "InvalidFuturesProductSpecificationError",
    ]


def test_every_exported_name_is_importable() -> None:
    for package in (derivatives, futures):
        for name in package.__all__:
            assert getattr(package, name) is not None


def test_no_deferred_concept_is_exported_yet() -> None:
    exported = set(derivatives.__all__) | set(futures.__all__)

    for deferred in (
        "FuturesContractIdentity",
        "ContractMultiplier",
        "TickSize",
        "ContractMonth",
        "LastTradingDay",
        "SettlementInstant",
        "ContinuousFuturesContract",
        "ContractSize",
        "TickValue",
    ):
        assert deferred not in exported


def test_no_class_defines_a_deferred_concept() -> None:
    for path in _ALL_FILES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ClassDef):
                lowered = node.name.lower()
                for deferred in ("multiplier", "ticksize", "continuous", "rollover", "margin"):
                    assert deferred not in lowered, f"{path.name} defines {node.name}."
