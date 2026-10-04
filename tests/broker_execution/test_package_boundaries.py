"""Structural guarantees for the broker execution package.

These tests assert what the package must never acquire: a clock, randomness,
identifier generation, environment access, a broker or provider SDK, an outer
layer, or a dependency on the legacy Orders, Trades or Portfolio aggregates.
They also pin the direction of the one permitted dependency on paper trading:
broker execution reuses two shared paper-trading values, and paper trading
never depends on broker execution.

Imports are inspected through the AST rather than matching text, so prose in a
docstring can neither cause a false failure nor hide a real dependency.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

import northstar_core.broker_execution as broker_execution
import northstar_core.paper_trading as paper_trading

_PACKAGE_ROOT = Path(broker_execution.__file__).parent
_PAPER_ROOT = Path(paper_trading.__file__).parent


def _sources(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


_SOURCE_FILES = _sources(_PACKAGE_ROOT)
_PAPER_FILES = _sources(_PAPER_ROOT)

# Modules that would make a value irreproducible or read its environment.
_FORBIDDEN_MODULE_ROOTS = frozenset(
    {"datetime", "time", "random", "uuid", "secrets", "os", "calendar", "zoneinfo", "hashlib"}
)

# Outer layers, providers, brokers, transports and persistence.
_FORBIDDEN_OUTER_ROOTS = frozenset(
    {
        "northstar_application",
        "northstar_infrastructure",
        "northstar_api",
        "databento",
        "exchange_calendars",
        "sqlite3",
        "sqlalchemy",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "ssl",
        "websocket",
        "websockets",
        "ibapi",
        "ib_insync",
        "ib_async",
        "quickfix",
    }
)

# Generation-1 packages this design deliberately does not build on.
_FORBIDDEN_MODULE_PREFIXES = (
    "northstar_core.orders",
    "northstar_core.trades",
    "northstar_core.portfolio",
    "northstar_core.domain",
    "northstar_core.market_data",
)

# Generation-1 names that would reintroduce the obsolete identity model.
_FORBIDDEN_NAMES = frozenset(
    {
        "Listing",
        "ListingReference",
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

# The complete set of modules a broker execution value may import.
_ALLOWED_STANDARD_MODULES = frozenset({"__future__", "dataclasses", "enum"})
_ALLOWED_CORE_PREFIXES = (
    "northstar_core.broker_execution",
    "northstar_core.foundation",
    "northstar_core.derivatives",
    "northstar_core.futures",
    "northstar_core.strategy.value_objects.strategy_identity",
)

# The only paper-trading modules reused, and the only names taken from them.
_ALLOWED_PAPER_MODULES = frozenset(
    {
        "northstar_core.paper_trading.value_objects.order_side",
        "northstar_core.paper_trading.value_objects.futures_contract_count",
    }
)
_ALLOWED_PAPER_NAMES = frozenset({"OrderSide", "FuturesContractCount"})

# Concepts that belong to later stories, or must never exist here.
_DEFERRED_CLASS_FRAGMENTS = (
    "live",
    "paper",
    "simulat",
    "pnl",
    "profit",
    "margin",
    "commission",
    "fee",
    "symbol",
    "repository",
    "store",
    "journal",
    "attempt",
    "gateway",
    "port",
    "usecase",
    "service",
    "policy",
    "reconcil",
)


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


def test_the_package_has_source_files_to_inspect() -> None:
    """Guards the sweeps below from passing vacuously."""
    assert len(_SOURCE_FILES) == 13
    assert len(_PAPER_FILES) >= 10


# -- what broker execution may depend on ------------------------------------------


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_clock_randomness_or_environment_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert module.split(".")[0] not in _FORBIDDEN_MODULE_ROOTS, (
            f"{path.name} imports {module}; broker execution values must stay pure."
        )


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_call_reads_a_clock_or_generates_an_identity(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            assert name not in {
                "now",
                "utcnow",
                "today",
                "time",
                "monotonic",
                "uuid4",
                "uuid1",
                "getenv",
                "token_hex",
                "sha256",
            }, f"{path.name} calls {name}()."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_environment_is_read(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"environ", "getenv"}, f"{path.name} reads {node.attr}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_outer_layer_provider_or_broker_sdk_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        assert module.split(".")[0] not in _FORBIDDEN_OUTER_ROOTS, f"{path.name} imports {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_every_import_is_on_the_approved_list(path: Path) -> None:
    """An allowlist: any SDK, outer layer or new dependency fails by default."""
    for module in _imported_modules(_parse(path)):
        allowed = (
            module in _ALLOWED_STANDARD_MODULES
            or module in _ALLOWED_PAPER_MODULES
            or module.startswith(_ALLOWED_CORE_PREFIXES)
        )
        assert allowed, f"{path.name} imports unapproved module {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_only_the_shared_values_are_reused_from_paper_trading(path: Path) -> None:
    for module, names in _absolute_imports(_parse(path)):
        if module.startswith("northstar_core.paper_trading"):
            assert module in _ALLOWED_PAPER_MODULES, f"{path.name} imports {module}."
            assert set(names) <= _ALLOWED_PAPER_NAMES, f"{path.name} imports {names}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_legacy_package_is_imported(path: Path) -> None:
    for module in _imported_modules(_parse(path)):
        for prefix in _FORBIDDEN_MODULE_PREFIXES:
            assert not module.startswith(prefix), f"{path.name} imports legacy {module}."


@pytest.mark.parametrize("path", _SOURCE_FILES, ids=lambda path: path.name)
def test_no_legacy_name_is_imported(path: Path) -> None:
    forbidden = _imported_names(_parse(path)) & _FORBIDDEN_NAMES

    assert not forbidden, f"{path.name} imports legacy names {sorted(forbidden)}."


def test_the_package_defines_no_deferred_concept() -> None:
    for path in _SOURCE_FILES:
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ClassDef):
                lowered = node.name.lower()
                for fragment in _DEFERRED_CLASS_FRAGMENTS:
                    assert fragment not in lowered, f"{path.name} defines {node.name}."


# -- what must not depend on broker execution ----------------------------------------


@pytest.mark.parametrize("path", _PAPER_FILES, ids=lambda path: path.name)
def test_paper_trading_does_not_import_broker_execution(path: Path) -> None:
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        for module in modules:
            assert "broker_execution" not in module, f"{path.name} imports {module}."


def test_importing_paper_trading_does_not_load_broker_execution() -> None:
    """Checked in a fresh interpreter so this test module's own imports cannot mask it."""
    probe = (
        "import sys, northstar_core.paper_trading; "
        "print(any(name.startswith('northstar_core.broker_execution') for name in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "False"


# -- public surface -----------------------------------------------------------------


def test_the_public_surface_is_exactly_the_approved_vocabulary() -> None:
    assert sorted(broker_execution.__all__) == [
        "BrokerAccountReference",
        "BrokerEnvironment",
        "BrokerExecutionId",
        "BrokerOrderId",
        "BrokerOrderStatus",
        "ClientOrderIdentity",
        "FuturesBrokerExecution",
        "FuturesBrokerExecutionIntent",
        "FuturesBrokerOrder",
        "FuturesBrokerOrderObservation",
        "FuturesBrokerPosition",
        "InvalidBrokerAccountReferenceError",
        "InvalidBrokerExecutionIdError",
        "InvalidBrokerOrderIdError",
        "InvalidClientOrderIdentityError",
        "InvalidFuturesBrokerExecutionError",
        "InvalidFuturesBrokerExecutionIntentError",
        "InvalidFuturesBrokerOrderError",
        "InvalidFuturesBrokerOrderObservationError",
        "InvalidFuturesBrokerPositionError",
    ]


def test_the_value_objects_package_exports_the_same_surface() -> None:
    from northstar_core.broker_execution import value_objects

    assert sorted(value_objects.__all__) == sorted(broker_execution.__all__)


def test_every_exported_name_is_importable() -> None:
    for name in broker_execution.__all__:
        assert getattr(broker_execution, name) is not None


def test_every_exported_type_is_defined_in_this_package() -> None:
    """Nothing is a paper-trading type re-exported under a broker name."""
    for name in broker_execution.__all__:
        exported = getattr(broker_execution, name)
        assert exported.__module__.startswith("northstar_core.broker_execution"), name


def test_the_package_exposes_no_persistence_or_use_case() -> None:
    """Story 10.1 is Core values only: no ports, journals or orchestration."""
    for name in broker_execution.__all__:
        assert not name.endswith(
            ("UseCase", "Repository", "Store", "Port", "Service", "Gateway", "Policy")
        )


def test_paper_trading_public_surface_is_unchanged() -> None:
    """The broker package adds nothing to, and removes nothing from, paper trading."""
    assert not [name for name in paper_trading.__all__ if "Broker" in name]
    assert "FuturesExecutionIntent" in paper_trading.__all__
    assert "FuturesPaperFill" in paper_trading.__all__
