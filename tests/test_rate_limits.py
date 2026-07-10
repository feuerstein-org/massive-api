"""Test rate limiting, retry behavior, and authentication headers."""

from typing import Any

import aiohttp
import pytest
from aioresponses import aioresponses
from conftest import generate_random_api_key
from pytest_mock import MockerFixture
from steindamm import MaxSleepExceededError

from massive_api.base import BaseMassiveApi, MassiveApiConfig
from massive_api.exceptions import (
    AuthenticationError,
    MaxRetriesExceededError,
    NotFoundError,
    ServerError,
    TransportError,
)

TICKERS_URL = "https://api.massive.com/v3/reference/tickers"


def test_rate_limiter_defaults(test_config: MassiveApiConfig) -> None:
    """Test the shared bucket is a flat 100 requests/second with smooth refill."""
    limiter = test_config.rate_limiter
    assert limiter.capacity == 100.0
    assert limiter.refill_frequency == 0.1
    assert limiter.refill_amount == 10.0
    # The same bucket instance is reused on subsequent access.
    assert test_config.rate_limiter is limiter


def test_rate_limiter_free_tier() -> None:
    """Test the basic free tier (5 requests / 60s) maps to a valid sub-1/s bucket."""
    config = MassiveApiConfig(
        api_key=generate_random_api_key(),
        requests_per_period=5,
        period_seconds=60,
    )
    limiter = config.rate_limiter
    # Capacity is a full period's allowance, so a single request can always be served.
    assert limiter.capacity == 5.0
    assert limiter.refill_frequency == 0.1
    # Steady rate of 5/60 tokens per second, delivered in 0.1s increments.
    assert limiter.refill_amount == pytest.approx((5 / 60) * 0.1)


@pytest.mark.asyncio
async def test_free_tier_backoff_floored_at_refill_interval(mocker: MockerFixture) -> None:
    """Free-tier 429 backoff waits at least one 12s token-refill interval."""
    config = MassiveApiConfig(
        api_key=generate_random_api_key(),
        requests_per_period=5,
        period_seconds=60,
        max_retries=1,
    )
    session = aiohttp.ClientSession()

    try:
        config.session = session
        api = BaseMassiveApi(config=config)
        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            mock_http.get(TICKERS_URL, status=429)  # type: ignore
            mock_http.get(TICKERS_URL, payload={"results": []})  # type: ignore

            await api._make_request("v3/reference/tickers")

            # inter-token interval = 60/5 = 12s, dominating the 1s first exponential step.
            assert mock_sleep.call_args_list == [mocker.call(12.0)]
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_rate_limit_tokens_are_exhausted() -> None:
    """Test that requests fail with MaxSleepExceededError once the bucket is drained."""
    config = MassiveApiConfig(
        api_key=generate_random_api_key(),
        requests_per_period=2,
        rate_limit_max_sleep=0.01,
    )
    session = aiohttp.ClientSession()

    try:
        config.session = session
        api = BaseMassiveApi(config=config)

        with aioresponses() as mock_http:
            for i in range(3):
                mock_http.get(f"{TICKERS_URL}/T{i}", payload={"results": {}})  # type: ignore

            # Drain the two initial tokens.
            for i in range(2):
                await api._make_request(f"v3/reference/tickers/T{i}")

            # Third request would need to wait longer than max_sleep for a refill.
            with pytest.raises(MaxSleepExceededError):
                await api._make_request("v3/reference/tickers/T2")
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_bearer_auth_header_is_sent(test_config: MassiveApiConfig) -> None:
    """Test that the api key is passed as an Authorization: Bearer header."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        with aioresponses() as mock_http:
            mock_http.get(TICKERS_URL, payload={"results": []})  # type: ignore

            await api._make_request("v3/reference/tickers")

            requests_dict: dict[Any, Any] = mock_http.requests
            request = next(iter(requests_dict.values()))[0]
            assert request.kwargs["headers"]["Authorization"] == f"Bearer {test_config.api_key}"
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("max_retries", "num_429_responses", "success_after_retries", "expected_sleep_calls"),
    [
        (3, 3, True, [1, 2, 4]),  # Success after multiple retries with exponential backoff
        (2, 3, False, [1, 2]),  # Fails after max_retries exceeded
        (0, 1, False, []),  # Retry disabled with max_retries=0
    ],
)
async def test_429_retry_behavior(
    mocker: MockerFixture,
    test_config: MassiveApiConfig,
    max_retries: int,
    num_429_responses: int,
    success_after_retries: bool,
    expected_sleep_calls: list[int],
) -> None:
    """Test 429 error retry behavior with different max_retries configurations."""
    session = aiohttp.ClientSession()

    try:
        test_config.max_retries = max_retries
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        # Mock asyncio.sleep to avoid waiting during tests
        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            for _ in range(num_429_responses):
                mock_http.get(TICKERS_URL, status=429)  # type: ignore

            if success_after_retries:
                mock_http.get(TICKERS_URL, payload={"results": []})  # type: ignore
                result = await api._make_request("v3/reference/tickers")
                assert result == {"results": []}
            else:
                with pytest.raises(MaxRetriesExceededError) as exc_info:
                    await api._make_request("v3/reference/tickers")
                assert exc_info.value.retries == max_retries
                assert exc_info.value.status == 429

            assert mock_sleep.call_count == len(expected_sleep_calls)
            if expected_sleep_calls:
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls == expected_sleep_calls
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("max_retries", "num_5xx_responses", "success_after_retries", "expected_sleep_calls"),
    [
        (3, 3, True, [1, 2, 4]),  # Success after multiple retries with exponential backoff
        (2, 3, False, [1, 2]),  # Fails after max_retries exceeded
        (0, 1, False, []),  # Retry disabled with max_retries=0
    ],
)
async def test_5xx_retry_behavior(
    mocker: MockerFixture,
    test_config: MassiveApiConfig,
    max_retries: int,
    num_5xx_responses: int,
    success_after_retries: bool,
    expected_sleep_calls: list[int],
) -> None:
    """Transient 5xx responses are retried like 429s, but exhaustion raises ServerError."""
    session = aiohttp.ClientSession()

    try:
        test_config.max_retries = max_retries
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        # Mock asyncio.sleep to avoid waiting during tests
        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            for _ in range(num_5xx_responses):
                mock_http.get(TICKERS_URL, status=503)  # type: ignore

            if success_after_retries:
                mock_http.get(TICKERS_URL, payload={"results": []})  # type: ignore
                result = await api._make_request("v3/reference/tickers")
                assert result == {"results": []}
            else:
                with pytest.raises(ServerError) as exc_info:
                    await api._make_request("v3/reference/tickers")
                assert exc_info.value.status == 503
                assert isinstance(exc_info.value.__cause__, aiohttp.ClientResponseError)

            assert mock_sleep.call_count == len(expected_sleep_calls)
            if expected_sleep_calls:
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls == expected_sleep_calls
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "transport_exception",
    [
        TimeoutError(),
        aiohttp.ClientConnectionError("connection reset"),
        aiohttp.ServerDisconnectedError(),
    ],
)
async def test_transport_errors_retried(
    mocker: MockerFixture,
    test_config: MassiveApiConfig,
    transport_exception: Exception,
) -> None:
    """Timeouts and connection errors are retried; exhaustion raises TransportError."""
    session = aiohttp.ClientSession()

    try:
        test_config.max_retries = 2
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            # Fail once, then succeed: the caller sees only the successful response.
            mock_http.get(TICKERS_URL, exception=transport_exception)  # type: ignore
            mock_http.get(TICKERS_URL, payload={"results": []})  # type: ignore

            result = await api._make_request("v3/reference/tickers")
            assert result == {"results": []}
            assert mock_sleep.call_count == 1

            # Persistent failure exhausts max_retries and surfaces as TransportError.
            for _ in range(test_config.max_retries + 1):
                mock_http.get(TICKERS_URL, exception=transport_exception)  # type: ignore

            with pytest.raises(TransportError) as exc_info:
                await api._make_request("v3/reference/tickers")
            assert exc_info.value.__cause__ is transport_exception
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_lazy_session_uses_request_timeout() -> None:
    """The lazily created session applies `request_timeout` as the total timeout."""
    config = MassiveApiConfig(api_key=generate_random_api_key(), request_timeout=7.5)
    try:
        assert config.session.timeout.total == 7.5
    finally:
        await config.session.close()


@pytest.mark.asyncio
async def test_client_errors_not_retried(mocker: MockerFixture, test_config: MassiveApiConfig) -> None:
    """Test that non-transient errors (4xx other than 429) are not retried."""
    session = aiohttp.ClientSession()

    try:
        test_config.max_retries = 3
        test_config.session = session
        api = BaseMassiveApi(config=test_config)

        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            mock_http.get(TICKERS_URL, status=404)  # type: ignore

            with pytest.raises(NotFoundError) as exc_info:
                await api._make_request("v3/reference/tickers")

            assert exc_info.value.status == 404
            assert isinstance(exc_info.value.__cause__, aiohttp.ClientResponseError)
            assert mock_sleep.call_count == 0
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_exception"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (500, ServerError),
        (503, ServerError),
    ],
)
async def test_http_errors_wrapped_in_typed_exceptions(
    mocker: MockerFixture,
    test_config: MassiveApiConfig,
    status: int,
    expected_exception: type[Exception],
) -> None:
    """HTTP errors surface as typed MassiveApiHTTPError subclasses, not raw aiohttp errors."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session
        api = BaseMassiveApi(config=test_config)
        mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            # repeat=True keeps returning the same status, so 5xx cases also cover the
            # error type raised once retries are exhausted.
            mock_http.get(TICKERS_URL, status=status, repeat=True)  # type: ignore

            with pytest.raises(expected_exception) as exc_info:
                await api._make_request("v3/reference/tickers")

            assert exc_info.value.status == status  # type: ignore[attr-defined]
            assert isinstance(exc_info.value.__cause__, aiohttp.ClientResponseError)
    finally:
        await session.close()
