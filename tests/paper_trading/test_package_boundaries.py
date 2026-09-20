"""Structural guarantees for the paper trading package.

These tests assert what the package must never acquire: a clock, a source of
randomness, a dependency on the legacy Orders, Trades or Portfolio reference
aggregates, or a Trade concept. They inspect the package's own imports through
the AST rather than matching text, so prose in a docstring can neither cause a
false failure nor hide a real dependency.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import northstar_core.paper_trading as paper_trading

_PACKAGE_ROOT = Path(paper_trading.__file__).parent
_SOURCE_FILES = tuple(
    sorted(path for path in _PACKAGE_ROOT.rglob("*.py") if "__pycache__" not in path.parts)
)

# Modules that would make a simulated execution irreproducible.
_FORBIDDEN_MODULE_ROOTS = frozenset(
    {"datetime", "time", "random", "uuid", "secrets", "os", "calendar", "zoneinfo"}
)

# Generation-1 packages this design deliberately does not build on.
_FORBIDDEN_MODULE_PREFIXES = (
    "northstar_core.orders",
    "northstar_core.trades",
    "northstar_core.portfolio",
    "northstar_core.domain.listing",
)

# Generation-1 names that would reintroduce the obsolete identity model.
_FORBIDDEN_NAMES = frozenset(
    {
        "Listing",
        "Instrument",
        "Exchange",
        "ParticipantIdentity",
        "ParticipantReference",
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


def test_the_package_has_source_files_to_inspect() -> None:
    """Guards the sweeps below from passing vacuously."""
    assert len(_SOURCE_FILES) >= 10


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_clock_or_randomness_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert module.split(".")[0] not in _FORBIDDEN_MODULE_ROOTS, (
            f"{path.name} imports {module}; paper trading must stay reproducible."
        )


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_legacy_package_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        for prefix in _FORBIDDEN_MODULE_PREFIXES:
            assert not module.startswith(prefix), f"{path.name} imports legacy {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_legacy_name_is_imported(path: Path) -> None:
    """ListingReference is permitted; the Listing entity it replaced is not."""
    forbidden = _imported_names(_parse(path)) & _FORBIDDEN_NAMES

    assert not forbidden, f"{path.name} imports legacy names {sorted(forbidden)}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_call_reads_a_clock(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"now", "utcnow", "today", "time", "monotonic"}, (
                f"{path.name} calls {node.func.attr}()."
            )


def test_the_package_defines_no_trade_concept() -> None:
    for path in _SOURCE_FILES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ClassDef):
                assert "Trade" not in node.name, f"{path.name} defines {node.name}."


def test_the_public_surface_exposes_no_trade_concept() -> None:
    assert not [name for name in paper_trading.__all__ if "Trade" in name]


def test_the_public_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(paper_trading.__all__) == [
        "ExecutionIntent",
        "InvalidExecutionIntentError",
        "InvalidPaperFillError",
        "InvalidPaperFillIdentityError",
        "InvalidPaperOrderError",
        "InvalidPaperOrderIdentityError",
        "InvalidPaperPortfolioIdentityError",
        "InvalidPositionError",
        "OrderSide",
        "PaperFill",
        "PaperFillIdentity",
        "PaperOrder",
        "PaperOrderIdentity",
        "PaperOrderStatus",
        "PaperPortfolioIdentity",
        "Position",
    ]


def test_every_exported_name_is_importable() -> None:
    for name in paper_trading.__all__:
        assert getattr(paper_trading, name) is not None


def test_the_package_exposes_no_persistence_or_use_case() -> None:
    """Story 8.2 is Core values only: no folding, no ports, no orchestration."""
    for name in paper_trading.__all__:
        assert not name.endswith(("UseCase", "Repository", "Store", "Port", "Service"))


def test_legacy_position_and_paper_position_remain_distinct_types() -> None:
    """The new Position must not be the legacy one re-exported."""
    from northstar_core.portfolio.position import Position as LegacyPosition

    assert paper_trading.Position is not LegacyPosition
    assert paper_trading.Position.__module__.startswith("northstar_core.paper_trading")
