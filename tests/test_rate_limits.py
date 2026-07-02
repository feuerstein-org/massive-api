"""Test rate limiting functionality"""

from typing import Any

import aiohttp
import pytest
from aioresponses import aioresponses
from pytest_mock import MockerFixture
from steindamm import MaxSleepExceededError, NoTokensAvailableError

from eodhd_py.base import BaseEodhdApi, EodhdApiConfig


@pytest.mark.asyncio
async def test_config_explicit_rate_limits() -> None:
    """Test that explicit rate limits in config are used without fetching from user API."""
    config = EodhdApiConfig(
        daily_calls_rate_limit=50000,
        daily_remaining_limit=4000,
        minute_requests_rate_limit=100,
        minute_remaining_limit=50,
        extra_limit=10,
    )

    api = BaseEodhdApi(config=config)

    # Initialize rate limiters
    await config.initialize_rate_limiters(api.BASE_URL)

    # Verify rate limiters are initialized with explicit values
    assert config.daily_rate_limiter.capacity == 50000.0
    assert config.daily_rate_limiter.initial_tokens == 4000.0
    assert config.minute_rate_limiter.capacity == 100.0
    assert config.minute_rate_limiter.initial_tokens == 50.0
    assert config.extra_rate_limiter.capacity == 10.0
    assert config.extra_rate_limiter.initial_tokens == 10.0

    assert config._user_limits_initialized is True


@pytest.mark.asyncio
async def test_rate_limit_tokens_are_exhausted(test_config: EodhdApiConfig) -> None:
    """Test that requests fail with MaxSleepExceededError when limits are exhausted."""
    session = aiohttp.ClientSession()

    try:
        # Set very low limits and max_sleep
        test_config.minute_requests_rate_limit = 5
        test_config.minute_remaining_limit = 5
        test_config.minute_max_sleep = 0.01
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        with aioresponses() as mock_http:
            # Mock successful responses for the first 5 requests
            for i in range(5):
                mock_http.get(  # type: ignore
                    f"https://eodhd.com/api/eod/TEST{i}?api_token={test_config.api_key}&fmt=json",
                    payload={"close": 100 + i},
                )

            # Make 5 requests to exhaust the minute limit
            for i in range(5):
                result = await api._make_request(f"eod/TEST{i}", cost=1.0, df_output=False)
                assert result == {"close": 100 + i}

            # Next request should fail with MaxSleepExceededError
            with pytest.raises(MaxSleepExceededError):
                await api._make_request("eod/TEST_FAIL", cost=1.0, df_output=False)

    finally:
        await session.close()


@pytest.mark.asyncio
async def test_fetch_limits_only_once() -> None:
    """Test that rate limits are only fetched once, even across multiple requests."""
    session = aiohttp.ClientSession()

    try:
        config = EodhdApiConfig()
        config.session = session

        api = BaseEodhdApi(config=config)

        with aioresponses() as mock_http:
            # The AAPL call is made to populate API stats before fetching user info
            mock_http.get(  # type: ignore
                "https://eodhd.com/api/eod/AAPL?api_token=demo&fmt=json",
                payload={"close": 100},
            )

            mock_http.get(  # type: ignore
                "https://eodhd.com/api/user?api_token=demo&fmt=json",
                payload={"dailyRateLimit": "100000", "apiRequests": "1000"},
                headers={"x-ratelimit-limit": "1400", "x-ratelimit-remaining": "100"},
            )

            for i in range(3):
                mock_http.get(  # type: ignore
                    f"https://eodhd.com/api/eod/TEST{i}?api_token=demo&fmt=json",
                    payload={"data": f"test{i}"},
                )

            for i in range(3):
                await api._make_request(f"eod/TEST{i}", df_output=False)

            # Verify _user_limits_initialized flag is True after requests
            assert config._user_limits_initialized is True

            # Verify user API was called exactly once
            requests_dict: dict[Any, Any] = mock_http.requests  # type: ignore
            user_api_call_count = sum(1 for key in requests_dict if "/user" in str(key[1]))
            assert user_api_call_count == 1

            # Verify rate limiters are initialized
            assert config._daily_rate_limiter is not None
            assert config._minute_rate_limiter is not None

            assert config._daily_rate_limiter.capacity == 100000
            assert config._daily_rate_limiter.initial_tokens == 99000  # 100000 - 1000 used
            assert config._minute_rate_limiter.capacity == 1400
            assert config._minute_rate_limiter.initial_tokens == 100

    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "explicit_daily",
        "explicit_minute",
        "explicit_extra",
        "expected_daily",
        "expected_minute",
        "expected_minute_initial",
        "expected_extra",
    ),
    [
        (75000, None, None, 75000, 2000, 1100, 1000),  # Daily explicit, others from API
        (None, 1500, None, 200000, 1500, 1500, 1000),  # Minute explicit, others from API
        (None, None, 500, 200000, 2000, 1100, 500),  # Extra explicit, others from API
    ],
)
async def test_config_partial_auto_fetch(
    explicit_daily: int | None,
    explicit_minute: int | None,
    explicit_extra: int | None,
    expected_daily: int,
    expected_minute: int,
    expected_minute_initial: int,
    expected_extra: int,
) -> None:
    """Test that only unset rate limits are fetched from user API."""
    session = aiohttp.ClientSession()

    try:
        # Set explicit limits based on test parameters
        config = EodhdApiConfig(
            api_key="demo",
            daily_calls_rate_limit=explicit_daily,
            minute_requests_rate_limit=explicit_minute,
            extra_limit=explicit_extra,
        )
        config.session = session

        api = BaseEodhdApi(config=config)

        # Mock the user API response
        with aioresponses() as mock_http:
            # The AAPL call is made to populate API stats before fetching user info
            mock_http.get(  # type: ignore
                "https://eodhd.com/api/eod/AAPL?api_token=demo&fmt=json",
                payload={"close": 100},
            )

            mock_http.get(  # type: ignore
                "https://eodhd.com/api/user?api_token=demo&fmt=json",
                payload={"dailyRateLimit": "200000", "apiRequests": "1000", "extraLimit": "1000"},
                headers={"x-ratelimit-limit": "2000", "x-ratelimit-remaining": "1100"},
            )

            # Initialize rate limiters
            await config.initialize_rate_limiters(api.BASE_URL)

            # Verify user API was called exactly once
            requests_dict: dict[Any, Any] = mock_http.requests  # type: ignore
            user_api_call_count = sum(1 for key in requests_dict if "/user" in str(key[1]))
            assert user_api_call_count == 1

            # Verify rate limiters are initialized
            assert config.daily_rate_limiter is not None
            assert config.minute_rate_limiter is not None
            assert config.extra_rate_limiter is not None

            # Verify limits match expected values (explicit or from API)
            assert config.daily_rate_limiter.capacity == expected_daily
            assert (
                config.daily_rate_limiter.initial_tokens == expected_daily if explicit_daily else 199000
            )  # 200000 - 1000
            assert config.minute_rate_limiter.capacity == expected_minute
            assert config.minute_rate_limiter.initial_tokens == expected_minute_initial
            assert config.extra_rate_limiter.capacity == expected_extra
            assert config.extra_rate_limiter.initial_tokens == expected_extra

    finally:
        await session.close()


@pytest.mark.asyncio
async def test_get_endpoint_cost_called(mocker: MockerFixture, test_config: EodhdApiConfig) -> None:
    """Test that get_endpoint_cost is called when making a request without explicit cost."""
    session = aiohttp.ClientSession()

    try:
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        # Mock get_endpoint_cost
        mock_get_cost = mocker.patch("eodhd_py.base.get_endpoint_cost", return_value=1.0)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                payload={"data": "test"},
            )

            await api._make_request("eod/AAPL", df_output=False)

            # Verify get_endpoint_cost was called with the endpoint
            mock_get_cost.assert_called_once_with("eod/AAPL")
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
    test_config: EodhdApiConfig,
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

        api = BaseEodhdApi(config=test_config)

        # Mock asyncio.sleep to avoid waiting during tests
        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            # Add 429 responses
            for _ in range(num_429_responses):
                mock_http.get(  # type: ignore
                    f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                    status=429,
                )

            # Add success response if expected
            if success_after_retries:
                mock_http.get(  # type: ignore
                    f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                    payload={"close": 100},
                )

                result = await api._make_request("eod/AAPL", df_output=False)
                assert result == {"close": 100}
            else:
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    await api._make_request("eod/AAPL", df_output=False)
                assert exc_info.value.status == 429

            # Verify sleep calls match expected exponential backoff
            assert mock_sleep.call_count == len(expected_sleep_calls)
            if expected_sleep_calls:
                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls == expected_sleep_calls
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_429_retry_refetches_rate_limits(mocker: MockerFixture, test_config: EodhdApiConfig) -> None:
    """Test that rate limits are refetched on 429 errors."""
    session = aiohttp.ClientSession()

    try:
        test_config.max_retries = 3
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        # Mock asyncio.sleep to avoid waiting during tests
        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            # First request returns 429
            mock_http.get(  # type: ignore
                f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                status=429,
            )

            # Mock the refetch calls with different limits
            mock_http.get(  # type: ignore
                f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                payload={"close": 100},
            )
            result = await api._make_request("eod/AAPL", df_output=False)

            assert result == {"close": 100}

            # Verify backoff sleep was called exactly once with 1 second
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_once_with(1)
    finally:
        await session.close()


@pytest.mark.asyncio
async def test_non_429_errors_not_retried(mocker: MockerFixture, test_config: EodhdApiConfig) -> None:
    """Test that non-429 errors are not retried."""
    session = aiohttp.ClientSession()

    try:
        test_config.max_retries = 3
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        # Mock asyncio.sleep to verify it's never called
        mock_sleep = mocker.patch("asyncio.sleep")

        with aioresponses() as mock_http:
            # Request returns 404
            mock_http.get(  # type: ignore
                f"https://eodhd.com/api/eod/INVALID?api_token={test_config.api_key}&fmt=json",
                status=404,
            )

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await api._make_request("eod/INVALID", df_output=False)

            assert exc_info.value.status == 404
            # Verify no retries occurred - sleep should not be called at all
            assert mock_sleep.call_count == 0
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extra_limit"),
    [(500), (0)],
)
async def test_extra_limiter_creation(extra_limit: int) -> None:
    """Test that extra rate limiter is created based on extra_limit value."""
    config = EodhdApiConfig(
        api_key="demo",
        daily_calls_rate_limit=1000,
        minute_requests_rate_limit=100,
        extra_limit=extra_limit,
    )

    api = BaseEodhdApi(config=config)
    await config.initialize_rate_limiters(api.BASE_URL)

    if extra_limit > 0:
        assert config._extra_rate_limiter is not None
        assert config._extra_rate_limiter.capacity == extra_limit
    else:
        assert config._extra_rate_limiter is None


@pytest.mark.asyncio
async def test_fallback_to_extra_limit_on_max_sleep_exceeded_success(test_config: EodhdApiConfig) -> None:
    """Test that requests fall back to extra limit when daily limit MaxSleepExceededError occurs and succeed."""
    session = aiohttp.ClientSession()

    try:
        test_config.daily_remaining_limit = 0
        test_config.extra_limit = 100
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                payload={"close": 150},
            )

            # Request should succeed by falling back to extra limit
            result = await api._make_request("eod/AAPL", cost=5.0, df_output=False)
            assert result == {"close": 150}

    finally:
        await session.close()


@pytest.mark.asyncio
async def test_fallback_to_extra_limit_raises_when_insufficient(test_config: EodhdApiConfig) -> None:
    """Test that NoTokensAvailableError is raised when extra limit is insufficient."""
    session = aiohttp.ClientSession()

    try:
        test_config.daily_remaining_limit = 0
        test_config.extra_limit = 5
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        with aioresponses() as mock_http:
            mock_http.get(  # type: ignore
                f"https://eodhd.com/api/eod/AAPL?api_token={test_config.api_key}&fmt=json",
                payload={"close": 150},
            )

            # First request should succeed using available extra limit
            await api._make_request("eod/AAPL", cost=1.0, df_output=False)
            # No extra limit available, should raise NoTokensAvailableError
            with pytest.raises(NoTokensAvailableError):
                await api._make_request("eod/AAPL", cost=5.0, df_output=False)

    finally:
        await session.close()


@pytest.mark.asyncio
async def test_max_sleep_exceeded_reraises_for_minute_limiter(test_config: EodhdApiConfig) -> None:
    """Test that MaxSleepExceededError from minute limiter is raised (no fallback to extra limit)."""
    session = aiohttp.ClientSession()

    try:
        test_config.minute_remaining_limit = 0
        test_config.minute_max_sleep = 0.01
        test_config.session = session

        api = BaseEodhdApi(config=test_config)

        # Request should raise MaxSleepExceededError (no fallback to extra limiter)
        with pytest.raises(MaxSleepExceededError):
            await api._make_request("eod/AAPL", cost=1.0, df_output=False)

    finally:
        await session.close()
