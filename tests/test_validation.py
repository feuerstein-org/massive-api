"""Test the three response-validation modes: raise, skip, and raw."""

import pytest
from conftest import MockApiFactory
from pydantic import ValidationError

from massive_api.api.reference import ReferenceApi

GOOD = {"ticker": "AAPL", "active": True, "name": "Apple Inc."}
BAD = {"name": "Missing ticker field"}  # required `ticker` and `active` are absent


@pytest.mark.asyncio
async def test_default_mode_skips_invalid_records(mock_api_factory: MockApiFactory) -> None:
    """Test that the default mode ("skip") drops invalid rows instead of raising."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, BAD])

    result = await api.get_all_tickers()

    assert [t.ticker for t in result] == ["AAPL"]


@pytest.mark.asyncio
async def test_raise_mode_raises_on_invalid_record(mock_api_factory: MockApiFactory) -> None:
    """Test that an explicit 'raise' override raises ValidationError on a bad row."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, BAD])

    with pytest.raises(ValidationError):
        await api.get_all_tickers(on_validation_error="raise")


@pytest.mark.asyncio
async def test_skip_returns_all_when_valid(mock_api_factory: MockApiFactory) -> None:
    """Test that skip mode returns everything (via the batch fast path) when all rows are valid."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, {"ticker": "MSFT", "active": True}])

    result = await api.get_all_tickers(on_validation_error="skip")

    assert [t.ticker for t in result] == ["AAPL", "MSFT"]


@pytest.mark.asyncio
async def test_raise_aggregates_all_bad_rows(mock_api_factory: MockApiFactory) -> None:
    """Test that raise mode reports every invalid row (by index), not just the first."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, BAD, {"name": "also bad"}])

    with pytest.raises(ValidationError) as exc_info:
        await api.get_all_tickers(on_validation_error="raise")

    # Both bad rows (indices 1 and 2) are reported in a single error.
    error_indices = {err["loc"][0] for err in exc_info.value.errors()}
    assert error_indices == {1, 2}


@pytest.mark.asyncio
async def test_config_default_raise_is_honored(mock_api_factory: MockApiFactory) -> None:
    """Test that a config-level default of 'raise' applies to un-overridden calls."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, BAD])
    api.config.on_validation_error = "raise"

    with pytest.raises(ValidationError):
        await api.get_all_tickers()


@pytest.mark.asyncio
async def test_per_call_override_beats_config_default(mock_api_factory: MockApiFactory) -> None:
    """Test that an explicit 'raise' override wins over a config default of 'skip'."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, BAD])
    api.config.on_validation_error = "skip"

    with pytest.raises(ValidationError):
        await api.get_all_tickers(on_validation_error="raise")


@pytest.mark.asyncio
async def test_raw_never_validates(mock_api_factory: MockApiFactory) -> None:
    """Test that the raw path returns untouched dicts and never raises."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[GOOD, BAD])

    result = await api.get_all_tickers_raw()

    assert result == [GOOD, BAD]
