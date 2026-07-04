"""Test cursor-based pagination in the base client."""

import logging

import aiohttp
import pytest
from aioresponses import aioresponses
from conftest import generate_random_api_key
from steindamm import MaxSleepExceededError

from massive_api.base import BaseMassiveApi, MassiveApiConfig

TICKERS_URL = "https://api.massive.com/v3/reference/tickers"


@pytest.mark.asyncio
async def test_cursor_pagination_follows_next_url(test_config: MassiveApiConfig) -> None:
    """Test that _get_all_pages follows next_url across pages and concatenates results."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                TICKERS_URL,
                payload={"results": [{"ticker": "A"}, {"ticker": "B"}], "next_url": f"{TICKERS_URL}?cursor=page2"},
            )
            mock_http.get(  # type: ignore
                f"{TICKERS_URL}?cursor=page2",
                payload={"results": [{"ticker": "C"}], "next_url": None},
            )

            records = await api._get_all_pages("v3/reference/tickers", {})

            assert [r["ticker"] for r in records] == ["A", "B", "C"]
            assert len(mock_http.requests) == 2
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_max_results_stops_pagination_early(test_config: MassiveApiConfig) -> None:
    """Test that max_results halts pagination without fetching further pages."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                TICKERS_URL,
                payload={"results": [{"ticker": "A"}, {"ticker": "B"}], "next_url": f"{TICKERS_URL}?cursor=page2"},
            )
            # No second page

            records = await api._get_all_pages("v3/reference/tickers", {}, max_results=1)

            assert [r["ticker"] for r in records] == ["A"]
            assert len(mock_http.requests) == 1
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_max_results_larger_than_available_returns_all(test_config: MassiveApiConfig) -> None:
    """Test that a max_results cap above the total simply returns everything."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                TICKERS_URL,
                payload={"results": [{"ticker": "A"}, {"ticker": "B"}], "next_url": None},
            )

            records = await api._get_all_pages("v3/reference/tickers", {}, max_results=100)

            assert [r["ticker"] for r in records] == ["A", "B"]
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_pagination_stops_on_unparseable_next_url(
    test_config: MassiveApiConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that a next_url without a `cursor` param halts pagination with a warning."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        with aioresponses() as mock_http:
            # next_url is present but carries no `cursor` query param -> cannot paginate.
            mock_http.get(  # type: ignore
                TICKERS_URL,
                payload={"results": [{"ticker": "A"}], "next_url": f"{TICKERS_URL}?foo=bar"},
            )

            with caplog.at_level(logging.WARNING, logger="massive_api.base"):
                records = await api._get_all_pages("v3/reference/tickers", {})

            # Only the first page is returned; the malformed next_url is not fetched.
            assert [r["ticker"] for r in records] == ["A"]
            assert len(mock_http.requests) == 1
            assert "Couldn't parse 'next_url'" in caplog.text
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_each_page_draws_a_token() -> None:
    """Test that every page consumes a token from the shared rate limiter."""
    config = MassiveApiConfig(
        api_key=generate_random_api_key(),
        requests_per_period=1,
        rate_limit_max_sleep=0.01,
    )
    session = aiohttp.ClientSession()

    try:
        config.session = session
        api = BaseMassiveApi(config=config)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                TICKERS_URL,
                payload={"results": [{"ticker": "A"}], "next_url": f"{TICKERS_URL}?cursor=page2"},
            )
            mock_http.get(  # type: ignore
                f"{TICKERS_URL}?cursor=page2",
                payload={"results": [{"ticker": "B"}], "next_url": None},
            )

            # First page drains the single token; fetching the second page needs another
            # token, which would exceed max_sleep -> MaxSleepExceededError.
            with pytest.raises(MaxSleepExceededError):
                await api._get_all_pages("v3/reference/tickers", {})
    finally:
        await session.close()
