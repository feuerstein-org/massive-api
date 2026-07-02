"""Base classes for EodhdApi and its endpoints."""

import asyncio
from datetime import UTC, datetime
from typing import Any, Self

import aiohttp
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from steindamm import AsyncTokenBucket, MaxSleepExceededError

from eodhd_py.api.costs import get_endpoint_cost

HTTP_TOO_MANY_REQUESTS = 429


class EodhdApiConfig(BaseModel):
    """
    Configuration Class for EodhdApi and its endpoints.

    Additionally manages the session and rate limiters.

    Pass the config to multiple endpoint instances to share the session.
    The session will automatically close when all instances using it have exited.

    Rate limiters are automatically shared between multiple endpoint instances for the same api key,
    this also applies if you don't share the config object but use the same api key.
    You can override this by passing a different `rate_limit_key` when creating the config (max_length=8).

    The rate limiters use local (in-memory) implementation by default. For distributed rate
    limiting across processes, pass a Redis connection to the rate limiters.

    Rate limits are automatically fetched from the user API unless explicitly set.
    To familiarize yourself with the difference between limits and requests, see https://eodhd.com/financial-apis/api-limits.

    The API provides two types of daily limits:
    - dailyRateLimit: Regular daily limit that refills every 24 hours at midnight UTC
    - extraLimit: Additional non-refilling limit that can be used beyond the daily limit

    The daily limit is always consumed first. When the daily limit is exhausted, the extra limit
    is automatically used as a fallback. The extra limit does not refill unless the user adds
    more requests to their account on the API side.

    If you want to override the automatic fetching (not recommended), set daily_rate_limit(total calls for 24h),
    daily_remaining_limit(remaining calls for 24h), and extra_limit. Same applies for minute limits.
    The "remaining" limits (calls left) are not fetched automatically if you set the total limits manually.

    The maximum wait time for rate limiting can be configured via daily_max_sleep (default: 3600 seconds)
    and minute_max_sleep (default: 120 seconds). If a request would require waiting longer than these
    limits, a MaxSleepExceededError will be raised.
    If extra capacity is available, a NoTokensAvailableError will be raised instead.

    Retry behavior for 429 (Too Many Requests) responses can be configured via max_retries (default: 3).
    Retries use exponential backoff starting at 1 second. Set to 0 to disable retries.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    api_key: str = Field(pattern=r"^([A-Za-z0-9.]{16,32}|demo)$", default="demo")
    _session: aiohttp.ClientSession | None = None
    _session_ref_count: int = 0  # Track how many instances are using this session
    max_retries: int = Field(default=3, ge=0)  # Maximum number of retries for 429 responses
    daily_calls_rate_limit: int | None = None  # Auto-fetched from user API if None
    daily_remaining_limit: int | None = None  # Auto-fetched from user API if None
    minute_requests_rate_limit: int | None = None  # Auto-fetched from user API if None
    minute_remaining_limit: int | None = None  # Auto-fetched from user API if None
    extra_limit: int | None = None  # Auto-fetched from user API if None
    daily_max_sleep: float = 3600.0  # Maximum time to wait for daily rate limit (in seconds)
    minute_max_sleep: float = 120.0  # Maximum time to wait for minute rate limit (in seconds)
    redis_connection: Any = None  # Optional redis-py Redis connection for distributed rate limiting
    rate_limit_key: str | None = Field(default=None, max_length=8)  # Optional unique key for rate limiter
    _daily_rate_limiter: Any | None = None
    _extra_rate_limiter: Any | None = None
    _minute_rate_limiter: Any | None = None
    _user_limits_initialized: bool = False

    @property
    def session(self) -> aiohttp.ClientSession:
        """Lazily instantiate the aiohttp ClientSession when first accessed."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    @session.setter
    def session(self, value: aiohttp.ClientSession) -> None:
        """Allow setting a custom session if needed."""
        self._session = value

    def increment_session_ref(self) -> None:
        """Increment the session reference count."""
        self._session_ref_count += 1

    def decrement_session_ref(self) -> None:
        """Decrement the session reference count."""
        self._session_ref_count = max(0, self._session_ref_count - 1)

    def should_close_session(self) -> bool:
        """Check if the session should be closed (no more references)."""
        return self._session_ref_count == 0

    @property
    def daily_rate_limiter(self) -> Any:
        """Get the daily rate limiter instance."""
        if self._daily_rate_limiter is None:
            msg = "Rate limiters not initialized. Use async context manager or call initialize_rate_limiters()."
            raise RuntimeError(msg)
        return self._daily_rate_limiter

    @property
    def extra_rate_limiter(self) -> Any:
        """Get the extra rate limiter instance (non-refilling)."""
        if self._extra_rate_limiter is None:
            msg = "Rate limiters not initialized. Use async context manager or call initialize_rate_limiters()."
            raise RuntimeError(msg)
        return self._extra_rate_limiter

    def has_extra_rate_limiter(self) -> bool:
        """Check if extra rate limiter is available."""
        return self._extra_rate_limiter is not None

    @property
    def minute_rate_limiter(self) -> Any:
        """Get the minute rate limiter instance."""
        if self._minute_rate_limiter is None:
            msg = "Rate limiters not initialized. Use async context manager or call initialize_rate_limiters()."
            raise RuntimeError(msg)
        return self._minute_rate_limiter

    async def initialize_rate_limiters(self, base_url: str) -> None:
        """
        Fetch actual limits from user API and initialize rate limiters.

        Args:
            base_url: The base URL for the API
            force: If True, refetch limits even if already fetched (useful after 429 errors)

        """
        if self._user_limits_initialized:
            return

        self._user_limits_initialized = True

        # Default limits
        daily_limit = self.daily_calls_rate_limit if self.daily_calls_rate_limit is not None else 100000.0
        daily_remaining_limit = self.daily_remaining_limit if self.daily_remaining_limit is not None else daily_limit
        extra_limit = self.extra_limit if self.extra_limit is not None else 0.0
        minute_limit = self.minute_requests_rate_limit if self.minute_requests_rate_limit is not None else 1400.0
        minute_remaining_limit = (
            self.minute_remaining_limit if self.minute_remaining_limit is not None else minute_limit
        )

        # Try to fetch actual limits from user API if not explicitly set
        if self.daily_calls_rate_limit is None or self.minute_requests_rate_limit is None or self.extra_limit is None:
            try:
                # Make a simple EOD request first to populate user API values
                params = {"api_token": self.api_key, "fmt": "json"}
                eod_url = f"{base_url}/eod/AAPL"
                async with self.session.request("GET", eod_url, params=params) as eod_response:
                    eod_response.raise_for_status()
                    await eod_response.json()

                # Now fetch user info to get limits
                url = f"{base_url}/user"
                async with self.session.request("GET", url, params=params) as response:
                    response.raise_for_status()
                    user_info = await response.json()

                    # Update daily rate limit if not explicitly set
                    if self.daily_calls_rate_limit is None:
                        daily_limit = int(user_info.get("dailyRateLimit", 100000))
                        daily_remaining_limit = daily_limit - int(user_info.get("apiRequests", daily_limit))

                    # Update extra limit if not explicitly set
                    if self.extra_limit is None:
                        extra_limit = int(user_info.get("extraLimit", 0))

                    # Update minute rate limit if not explicitly set
                    if self.minute_requests_rate_limit is None:
                        minute_limit = int(response.headers.get("x-ratelimit-limit", 1400))
                        minute_remaining_limit = int(response.headers.get("x-ratelimit-remaining", minute_limit))
            except Exception as e:  # noqa: BLE001
                # TODO: Remove once logging is added
                print(f"Failed to fetch user limits: {e}. Using default or configured limits.")  # noqa: T201

        api_key_hash = self.rate_limit_key or str(abs(hash(self.api_key)))[:8]  # Short hash for unique naming

        # Daily limits reset at midnight GMT (UTC)
        # Use naive datetime for compatibility with steindamm
        now = datetime.now(UTC)
        last_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

        # Initialize rate limiters with fetched or default limits
        self._daily_rate_limiter = AsyncTokenBucket(
            connection=self.redis_connection,
            name=f"eodhd_daily_{api_key_hash}",
            capacity=daily_limit,
            refill_frequency=86400,  # 24 hours in seconds
            refill_amount=daily_limit,
            initial_tokens=daily_remaining_limit,  # Start with remaining capacity
            max_sleep=self.daily_max_sleep,  # Maximum time to wait for daily rate limit
            expiry=86400 * 2,
            window_start_time=last_midnight,
        )
        if extra_limit > 0:
            # Extra limit - non-refilling token bucket
            self._extra_rate_limiter = AsyncTokenBucket(
                connection=self.redis_connection,
                name=f"eodhd_extra_{api_key_hash}",
                capacity=extra_limit,
                refill_frequency=0,
                refill_amount=0,
                expiry=86400 * 2,
            )
        self._minute_rate_limiter = AsyncTokenBucket(
            connection=self.redis_connection,
            name=f"eodhd_minute_{api_key_hash}",
            capacity=minute_limit,
            refill_frequency=1,  # every second
            refill_amount=minute_limit / 60,
            initial_tokens=minute_remaining_limit,  # Start with remaining capacity
            max_sleep=self.minute_max_sleep,  # Maximum time to wait for minute rate limit
            expiry=120,
        )


class BaseEodhdApi:
    """Base class for all EodhdApi endpoint classes."""

    def __init__(self, config: EodhdApiConfig | None = None, api_key: str = "") -> None:
        """Initialize with either a config or an api_key."""
        if not config and not api_key:
            msg = "Either config or api_key must be provided"
            raise ValueError(msg)
        self.config = config or EodhdApiConfig(api_key=api_key)
        self.session = self.config.session
        self.BASE_URL = "https://eodhd.com/api"

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager."""
        # Increment reference count for session usage
        self.config.increment_session_ref()
        return self

    # TODO: handle exceptions
    async def __aexit__(self, *args) -> None:  # type: ignore # noqa: ANN002
        """Exit the asynchronous context manager and close session if no other instances are using it."""
        # Decrement reference count
        self.config.decrement_session_ref()
        # Only close session when no more references exist
        if self.config.should_close_session() and self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
        cost: float | None = None,
        df_output: bool = True,
    ) -> Any:
        """
        Make an HTTP request to the EODHD API with rate limiting and retry logic.

        Args:
            endpoint: The API endpoint path (e.g., "eod/AAPL")
            params: Optional dictionary of query parameters
            cost: The cost of this request in API tokens (default: auto-calculated based on endpoint)
            df_output: If True (default), return pandas DataFrame. If False, return dict.

        Returns:
            JSON response as a dictionary or pandas DataFrame (based on df_output setting)

        Raises:
            aiohttp.ClientError: If the HTTP request fails (including 429 after max retries)
            ValueError: If the response is not valid JSON
            steindamm.MaxSleepExceededError: If rate limit wait time exceeds max_sleep
            steindamm.NoTokensAvailableError: If both daily and extra limits are exhausted

        """
        # Ensure rate limiters are initialized (only on first call)
        await self.config.initialize_rate_limiters(self.BASE_URL)

        # Get API cost if not provided
        if cost is None:
            cost = get_endpoint_cost(endpoint)

        # Prepare parameters and URL
        request_params = (params or {}).copy()
        request_params["api_token"] = self.config.api_key
        request_params["fmt"] = "json"
        url = f"{self.BASE_URL}/{endpoint.strip('/')}"

        # Retry loop for handling 429 responses
        for attempt in range(self.config.max_retries + 1):
            try:
                try:
                    async with (
                        self.config.daily_rate_limiter(cost),
                        self.config.minute_rate_limiter(),
                        self.session.request("GET", url, params=request_params) as response,
                    ):
                        response.raise_for_status()
                        data = await response.json()
                        return pd.DataFrame(data) if df_output else data
                except MaxSleepExceededError as e:
                    # If daily limit is exhausted, try extra limit
                    if self.config.has_extra_rate_limiter() and "eodhd_daily_" in str(e):
                        async with (
                            self.config.extra_rate_limiter(cost),
                            self.config.minute_rate_limiter(),
                            self.session.request("GET", url, params=request_params) as response,
                        ):
                            response.raise_for_status()
                            data = await response.json()
                            return pd.DataFrame(data) if df_output else data
                    else:
                        raise

            except aiohttp.ClientResponseError as e:
                # Retry on 429 errors
                if e.status != HTTP_TOO_MANY_REQUESTS:
                    raise
                if attempt >= self.config.max_retries:
                    raise
                # Exponential backoff
                backoff_time = 2**attempt
                await asyncio.sleep(backoff_time)

        msg = "Unexpected end of retry loop"
        raise RuntimeError(msg)
