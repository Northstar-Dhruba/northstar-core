"""Contract tests for AssetAnalysis."""

import pytest

from northstar_core.domain.value_objects import ListingReference
from northstar_core.foundation.value_objects import ExchangeCode, PointInTime, Symbol
from northstar_core.strategy import AssetAnalysis, InvalidAssetAnalysisError

_INSTANT = PointInTime("2026-09-14T10:00:00Z")


def _reference() -> ListingReference:
    return ListingReference(Symbol("AAPL"), ExchangeCode("NASDAQ"))


def _analysis(listing_reference: object = None) -> AssetAnalysis:
    return AssetAnalysis(
        listing_reference if listing_reference is not None else _reference(),
        _INSTANT,
        ("strong bullish",),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_asset_analysis_preserves_listing_reference_and_signals() -> None:
    reference = _reference()
    analysis = _analysis(reference)

    assert analysis.listing_reference is reference
    assert analysis.point_in_time == _INSTANT
    assert analysis.summarized_signals == ("strong bullish",)


def test_asset_analysis_does_not_expose_a_listing_entity() -> None:
    analysis = _analysis()

    assert not hasattr(analysis, "listing")


# ---------------------------------------------------------------------------
# Listing reference validation
# ---------------------------------------------------------------------------


def test_asset_analysis_requires_a_listing_reference() -> None:
    with pytest.raises(InvalidAssetAnalysisError, match="cannot be None"):
        AssetAnalysis(None, _INSTANT, ("strong bullish",))


def test_asset_analysis_rejects_wrong_listing_reference_type() -> None:
    with pytest.raises(InvalidAssetAnalysisError, match="must be a ListingReference"):
        _analysis("AAPL@NASDAQ")


def test_asset_analysis_rejects_symbol_supplied_as_listing_reference() -> None:
    with pytest.raises(InvalidAssetAnalysisError, match="must be a ListingReference"):
        _analysis(Symbol("AAPL"))


# ---------------------------------------------------------------------------
# Preserved validation behaviour
# ---------------------------------------------------------------------------


def test_asset_analysis_rejects_invalid_point_in_time() -> None:
    with pytest.raises(InvalidAssetAnalysisError, match="point-in-time"):
        AssetAnalysis(_reference(), "2026-09-14T10:00:00Z", ("strong bullish",))


def test_asset_analysis_rejects_non_tuple_signals() -> None:
    with pytest.raises(InvalidAssetAnalysisError, match="must be a tuple"):
        AssetAnalysis(_reference(), _INSTANT, ["strong bullish"])


def test_asset_analysis_normalizes_signal_whitespace() -> None:
    analysis = AssetAnalysis(_reference(), _INSTANT, ("  strong bullish  ",))

    assert analysis.summarized_signals == ("strong bullish",)


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------


def test_str_renders_symbol_at_exchange_from_listing_reference() -> None:
    analysis = _analysis()

    assert str(analysis).startswith("AAPL@NASDAQ ")
    assert str(analysis) == f"AAPL@NASDAQ {_INSTANT} [strong bullish]"


def test_repr_exposes_listing_reference() -> None:
    representation = repr(_analysis())

    assert "AssetAnalysis" in representation
    assert "listing_reference=" in representation
    assert "ListingReference" in representation
    assert "listing=" not in representation


# ---------------------------------------------------------------------------
# Value semantics
# ---------------------------------------------------------------------------


def test_asset_analysis_is_immutable() -> None:
    analysis = _analysis()

    with pytest.raises(AttributeError):
        analysis.listing_reference = ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ"))


def test_equal_asset_analyses_compare_equal_and_hash_equal() -> None:
    left = _analysis()
    right = _analysis()

    assert left == right
    assert hash(left) == hash(right)


def test_asset_analyses_with_different_listing_references_do_not_compare_equal() -> None:
    left = _analysis()
    right = _analysis(ListingReference(Symbol("MSFT"), ExchangeCode("NASDAQ")))

    assert left != right
