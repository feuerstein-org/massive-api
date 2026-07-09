"""Test Reference API (all-tickers, ticker-overview, ticker-events)."""

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import Mock

import aiohttp
import pytest
from conftest import MockApiFactory, with_defaults
from pydantic import ValidationError

from massive_api.api.reference import ReferenceApi, Ticker, TickerEvents, TickerOverview
from massive_api.exceptions import MassiveApiHTTPError, http_error_from_response


def _response_error(status: int) -> MassiveApiHTTPError:
    """Build the typed MassiveApiHTTPError that `_make_request` raises for the given HTTP status."""
    raw = aiohttp.ClientResponseError(request_info=Mock(), history=(), status=status)
    return http_error_from_response(raw)


# The SDK always sends these unless the call overrides them.
DEFAULT_PARAMS = {"active": "true", "order": "asc", "sort": "ticker", "limit": "1000"}

SAMPLE_TICKER = {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "market": "stocks",
    "locale": "us",
    "primary_exchange": "XNAS",
    "type": "CS",
    "active": True,
    "currency_name": "usd",
    "cik": "0000320193",
    "composite_figi": "BBG000B9XRY4",
    "share_class_figi": "BBG001S5N8V8",
    "last_updated_utc": "2024-01-01T00:00:00Z",
}

SAMPLE_OVERVIEW = {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "market": "stocks",
    "locale": "us",
    "type": "CS",
    "active": True,
    "primary_exchange": "XNAS",
    "cik": "0000320193",
    "composite_figi": "BBG000B9XRY4",
    "currency_name": "usd",
    "market_cap": 3.0e12,
    "total_employees": 161000,
    "weighted_shares_outstanding": 15000000000,
    "share_class_shares_outstanding": 15000000000,
    "sic_code": "3571",
    "homepage_url": "https://www.apple.com",
    "description": "Apple designs consumer electronics.",
    "address": {"address1": "One Apple Park Way", "city": "Cupertino", "state": "CA", "postal_code": "95014"},
    "round_lot": 100,
    "list_date": "1980-12-12",
}

SAMPLE_EVENTS = {
    "name": "Meta Platforms, Inc.",
    "cik": "0001326801",
    "composite_figi": "BBG000MM2P62",
    "events": [
        {"type": "ticker_change", "date": "2022-06-09", "ticker_change": {"ticker": "META"}},
    ],
}


# --------------------------------------------------------------------------- #
# All Tickers (list endpoint)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_params"),
    [
        ({}, {}),  # Test default params
        ({"market": "stocks", "active": True}, {"market": "stocks"}),
        (
            {"ticker": "AAPL", "ticker_type": "CS", "date": "2024-01-01", "max_results": 500},
            {"ticker": "AAPL", "type": "CS", "date": "2024-01-01", "limit": "500"},
        ),
        (
            {"active": False, "order": "desc", "sort": "name"},
            {"active": "false", "order": "desc", "sort": "name"},
        ),
        # max_results shrinks the page size so the single page is not over-fetched.
        ({"max_results": 10}, {"limit": "10"}),
        # ...but never above the API maximum.
        ({"max_results": 10000}, {"limit": "1000"}),
        # Range operators and identifier filters map to their dotted query params.
        (
            {"ticker_gte": "A", "ticker_lte": "B", "cusip": "037833100", "cik": "0000320193"},
            {"ticker.gte": "A", "ticker.lte": "B", "cusip": "037833100", "cik": "0000320193"},
        ),
        ({"ticker_gt": "A", "ticker_lt": "Z"}, {"ticker.gt": "A", "ticker.lt": "Z"}),
    ],
)
async def test_all_tickers_parameters(
    mock_api_factory: MockApiFactory,
    kwargs: dict[str, Any],
    expected_params: dict[str, str],
) -> None:
    """get_all_tickers builds the correct endpoint, params, and results cap."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_pages=[SAMPLE_TICKER])

    result = await api.get_all_tickers(**kwargs)

    mocks.get_all_pages.assert_called_once_with(
        "v3/reference/tickers",
        with_defaults(expected_params, DEFAULT_PARAMS),
        max_results=kwargs.get("max_results"),
    )
    assert len(result) == 1
    assert isinstance(result[0], Ticker)


@pytest.mark.asyncio
async def test_all_tickers_raw_returns_untouched_records(mock_api_factory: MockApiFactory) -> None:
    """get_all_tickers_raw returns the untouched page dicts (no model conversion)."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_pages=[SAMPLE_TICKER])

    result = await api.get_all_tickers_raw(market="stocks")

    mocks.get_all_pages.assert_called_once_with(
        "v3/reference/tickers",
        with_defaults({"market": "stocks"}, DEFAULT_PARAMS),
        max_results=None,
    )
    assert result == [SAMPLE_TICKER]


@pytest.mark.asyncio
async def test_all_tickers_parses_typed_fields(mock_api_factory: MockApiFactory) -> None:
    """A valid ticker parses into precise types (market/locale enums, datetime)."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[SAMPLE_TICKER])

    ticker = (await api.get_all_tickers())[0]

    assert ticker.ticker == "AAPL"
    assert ticker.market == "stocks"
    assert ticker.locale == "us"
    assert ticker.active is True
    assert ticker.last_updated_utc == datetime(2024, 1, 1, tzinfo=UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_record",
    [
        {**SAMPLE_TICKER, "market": "planets"},  # not a Market value
        {**SAMPLE_TICKER, "last_updated_utc": "not-a-timestamp"},  # unparseable datetime
        {k: v for k, v in SAMPLE_TICKER.items() if k != "ticker"},  # missing required ticker
        {k: v for k, v in SAMPLE_TICKER.items() if k != "active"},  # missing required active
    ],
)
async def test_all_tickers_rejects_invalid_records(
    mock_api_factory: MockApiFactory,
    bad_record: dict[str, Any],
) -> None:
    """The hardened Ticker model raises on an invalid/missing field under 'raise' mode."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_pages=[bad_record])

    with pytest.raises(ValidationError):
        await api.get_all_tickers(on_validation_error="raise")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_params",
    [
        {"order": "dec"},  # not an Order ("asc"/"desc")
        {"market": "planets"},  # not a Market value
        {"sort": "volume"},  # not a TickerSortField
        {"date": "not-a-date"},  # unparseable date
        {"date": "2024-13-01"},  # out-of-range month
        {"max_results": 0},  # must be a positive integer
        {"max_results": -5},  # must be a positive integer
    ],
)
async def test_all_tickers_rejects_invalid_parameters(
    mock_api_factory: MockApiFactory,
    bad_params: dict[str, Any],
) -> None:
    """An invalid query parameter raises before any request is made."""
    api, _ = mock_api_factory.create(ReferenceApi)

    with pytest.raises(ValueError):  # noqa: PT011
        await api.get_all_tickers(**bad_params, on_validation_error="raise")


# --------------------------------------------------------------------------- #
# Ticker Overview (single-record endpoint)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_params"),
    [
        ({}, {}),
        ({"date": "2024-01-01"}, {"date": "2024-01-01"}),
    ],
)
async def test_ticker_overview_parameters(
    mock_api_factory: MockApiFactory,
    kwargs: dict[str, Any],
    expected_params: dict[str, str],
) -> None:
    """get_ticker_overview requests the right URL with the right params."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_OVERVIEW)

    result = await api.get_ticker_overview("AAPL", **kwargs)

    mocks.request_json.assert_called_once_with("v3/reference/tickers/AAPL", expected_params)
    assert isinstance(result, TickerOverview)


@pytest.mark.asyncio
async def test_ticker_overview_raw_returns_untouched_records(mock_api_factory: MockApiFactory) -> None:
    """get_ticker_overview_raw returns the untouched `results` dict (no model conversion)."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_OVERVIEW)

    result = await api.get_ticker_overview_raw("AAPL")

    assert result == SAMPLE_OVERVIEW


@pytest.mark.asyncio
async def test_ticker_overview_returns_none_on_404(mock_api_factory: MockApiFactory) -> None:
    """A 404 (unknown ticker) yields None rather than raising, for both the raw and typed methods."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_OVERVIEW)
    mocks.request_json.side_effect = _response_error(404)

    assert await api.get_ticker_overview_raw("NOPE") is None
    assert await api.get_ticker_overview("NOPE") is None


@pytest.mark.asyncio
async def test_ticker_overview_propagates_non_404_errors(mock_api_factory: MockApiFactory) -> None:
    """Non-404 HTTP errors (e.g. 401, 500) still propagate rather than becoming None."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_OVERVIEW)
    mocks.request_json.side_effect = _response_error(500)

    with pytest.raises(MassiveApiHTTPError):
        await api.get_ticker_overview("AAPL")


@pytest.mark.asyncio
async def test_ticker_overview_parses_typed_fields(mock_api_factory: MockApiFactory) -> None:
    """A valid overview parses into precise types and flattens the nested address."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_OVERVIEW)

    result = await api.get_ticker_overview("AAPL")

    assert result is not None
    assert result.market == "stocks"
    assert result.locale == "us"
    assert result.market_cap == 3.0e12
    assert result.total_employees == 161000
    assert result.list_date == date(1980, 12, 12)
    # Flattened from the nested `address` object.
    assert result.city == "Cupertino"
    assert result.postal_code == "95014"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_record",
    [
        {**SAMPLE_OVERVIEW, "market": "planets"},  # not a Market value
        {**SAMPLE_OVERVIEW, "list_date": "not-a-date"},  # unparseable date
        {k: v for k, v in SAMPLE_OVERVIEW.items() if k != "market"},  # missing required market
        {k: v for k, v in SAMPLE_OVERVIEW.items() if k != "name"},  # missing required name
        {k: v for k, v in SAMPLE_OVERVIEW.items() if k != "currency_name"},  # missing required currency_name
    ],
)
async def test_ticker_overview_rejects_invalid_records(
    mock_api_factory: MockApiFactory,
    bad_record: dict[str, Any],
) -> None:
    """The hardened TickerOverview model raises on an invalid/missing field."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=bad_record)

    with pytest.raises(ValidationError):
        await api.get_ticker_overview("AAPL")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_params",
    [
        {"date": "not-a-date"},  # unparseable date
        {"date": "2024-13-01"},  # out-of-range month
    ],
)
async def test_ticker_overview_rejects_invalid_parameters(
    mock_api_factory: MockApiFactory,
    bad_params: dict[str, Any],
) -> None:
    """An invalid query parameter raises before any request is made."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_OVERVIEW)

    with pytest.raises(ValueError):  # noqa: PT011
        await api.get_ticker_overview("AAPL", **bad_params)


# --------------------------------------------------------------------------- #
# Ticker Events (single-record endpoint)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected_params"),
    [
        ({}, {}),
        ({"types": "ticker_change"}, {"types": "ticker_change"}),
    ],
)
async def test_ticker_events_parameters(
    mock_api_factory: MockApiFactory,
    kwargs: dict[str, Any],
    expected_params: dict[str, str],
) -> None:
    """get_ticker_events requests the right URL with the right params."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_EVENTS)

    result = await api.get_ticker_events("META", **kwargs)

    mocks.request_json.assert_called_once_with("vX/reference/tickers/META/events", expected_params)
    assert isinstance(result, TickerEvents)


@pytest.mark.asyncio
async def test_ticker_events_raw_returns_untouched_records(mock_api_factory: MockApiFactory) -> None:
    """get_ticker_events_raw returns the untouched `results` dict (no model conversion)."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_EVENTS)

    result = await api.get_ticker_events_raw("META")

    assert result == SAMPLE_EVENTS


@pytest.mark.asyncio
async def test_ticker_events_returns_none_on_404(mock_api_factory: MockApiFactory) -> None:
    """A 404 (unknown ticker) yields None rather than raising, for both the raw and typed methods."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_EVENTS)
    mocks.request_json.side_effect = _response_error(404)

    assert await api.get_ticker_events_raw("NOPE") is None
    assert await api.get_ticker_events("NOPE") is None


@pytest.mark.asyncio
async def test_ticker_events_propagates_non_404_errors(mock_api_factory: MockApiFactory) -> None:
    """Non-404 HTTP errors (e.g. 401, 500) still propagate rather than becoming None."""
    api, mocks = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_EVENTS)
    mocks.request_json.side_effect = _response_error(500)

    with pytest.raises(MassiveApiHTTPError):
        await api.get_ticker_events("META")


@pytest.mark.asyncio
async def test_ticker_events_parses_typed_fields(mock_api_factory: MockApiFactory) -> None:
    """A valid response parses nested events into precise types (date, nested ticker_change)."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_EVENTS)

    result = await api.get_ticker_events("META")

    assert result is not None
    assert result.name == "Meta Platforms, Inc."
    assert len(result.events) == 1
    event = result.events[0]
    assert event.type == "ticker_change"
    assert event.date == date(2022, 6, 9)
    assert event.ticker_change is not None
    assert event.ticker_change.ticker == "META"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_record",
    [
        {**SAMPLE_EVENTS, "events": [{"type": "ticker_change", "date": "not-a-date"}]},  # unparseable event date
        {**SAMPLE_EVENTS, "events": [{"type": "ticker_change"}]},  # event missing required date
        {k: v for k, v in SAMPLE_EVENTS.items() if k != "name"},  # missing required name
        {k: v for k, v in SAMPLE_EVENTS.items() if k != "events"},  # missing required events
    ],
)
async def test_ticker_events_rejects_invalid_records(
    mock_api_factory: MockApiFactory,
    bad_record: dict[str, Any],
) -> None:
    """The hardened TickerEvents model raises on an invalid/missing field."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=bad_record)

    with pytest.raises(ValidationError):
        await api.get_ticker_events("META")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_params",
    [
        {"types": "merger"},  # not a TickerEventType value
    ],
)
async def test_ticker_events_rejects_invalid_parameters(
    mock_api_factory: MockApiFactory,
    bad_params: dict[str, Any],
) -> None:
    """An invalid query parameter raises before any request is made."""
    api, _ = mock_api_factory.create(ReferenceApi, mock_results=SAMPLE_EVENTS)

    with pytest.raises(ValueError):  # noqa: PT011
        await api.get_ticker_events("META", **bad_params)
