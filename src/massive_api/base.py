"""Base classes for MassiveApi and its endpoints."""

import asyncio
import functools
import logging
from collections.abc import AsyncIterator, Mapping
from typing import Any, Literal, Self, TypeVar, cast
from urllib.parse import parse_qs, urlsplit

import aiohttp
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from steindamm import AsyncTokenBucket

from massive_api.exceptions import HTTP_NOT_FOUND, HTTP_TOO_MANY_REQUESTS, MaxRetriesExceededError

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

# Refill the bucket in small increments for a smooth request rate.
# capacity tokens, refilling (rate * interval) tokens every `interval` seconds.
RATE_LIMIT_REFILL_INTERVAL = 0.1


@functools.cache
def _list_adapter(model: type[BaseModel]) -> TypeAdapter[list[Any]]:
    """Build (and cache) a TypeAdapter that validates a whole list of `model` instances."""
    return TypeAdapter(list[model])


class MassiveApiConfig(BaseModel):
    """
    Configuration class for MassiveApi and its endpoints.

    Additionally manages the shared aiohttp session and the rate limiter.

    Pass the config to multiple endpoint instances to share the session.
    The session will automatically close when all instances using it have exited.

    Rate limiting is a single token bucket allowing `requests_per_period` requests
    every `period_seconds` seconds (default 100 per 1s) with smooth refill. The bucket's
    capacity equals `requests_per_period`, this is also the start amount of tokens, allowing
    a burst at the beginning. For the Massive basic free tier, pass
    `requests_per_period=5, period_seconds=60`. The bucket is automatically
    shared between endpoint instances that use the same api key (even without sharing the
    config object). Override the sharing behaviour by passing a distinct `rate_limit_key`
    (max_length=8).

    The rate limiter uses a local (in-memory) implementation by default. For distributed
    rate limiting across processes, pass a `redis_connection`.

    If a request would need to wait longer than `rate_limit_max_sleep` seconds for a token,
    a steindamm.MaxSleepExceededError is raised.

    Retry behavior for 429 (Too Many Requests) responses is configured via `max_retries`
    (default 3). Retries use exponential backoff starting at 1 second. Set to 0 to disable.

    `on_validation_error` controls the default behavior of validated list methods:
    - "raise": raise pydantic.ValidationError on the first invalid record.
    - "skip" (default): drop invalid records (logging each) and return only the valid ones.
    Any validated list method may override this per-call.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    api_key: str = Field(min_length=1)
    max_retries: int = Field(default=3, ge=0)
    requests_per_period: float = Field(default=100.0, gt=0)
    period_seconds: float = Field(default=1.0, gt=0)
    rate_limit_max_sleep: float = Field(default=60.0, ge=0)
    redis_connection: Any = None  # Optional redis-py connection for distributed rate limiting
    rate_limit_key: str | None = Field(default=None, max_length=8)
    on_validation_error: Literal["raise", "skip"] = "skip"
    _session: aiohttp.ClientSession | None = None
    _session_ref_count: int = 0  # Track how many instances are using this session
    _rate_limiter: Any | None = None

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
    def rate_limiter(self) -> Any:
        """
        Lazily build the shared token bucket for this api key.

        Capacity is a full period's allowance (`requests_per_period`), refilled smoothly at
        the steady rate of `requests_per_period / period_seconds` tokens per second.
        """
        if self._rate_limiter is None:
            key = self.rate_limit_key or str(abs(hash(self.api_key)))[:8]
            tokens_per_second = self.requests_per_period / self.period_seconds
            self._rate_limiter = AsyncTokenBucket.create(
                connection=self.redis_connection,
                name=f"massive_{key}",
                capacity=self.requests_per_period,
                refill_frequency=RATE_LIMIT_REFILL_INTERVAL,
                refill_amount=tokens_per_second * RATE_LIMIT_REFILL_INTERVAL,
                max_sleep=self.rate_limit_max_sleep,
                expiry=120,
            )
        return self._rate_limiter


class BaseMassiveApi:
    """Base class for all MassiveApi endpoint classes."""

    def __init__(self, config: MassiveApiConfig | None = None, api_key: str = "") -> None:
        """Initialize with either a config or an api_key."""
        if not config and not api_key:
            msg = "Either config or api_key must be provided"
            raise ValueError(msg)
        self.config = config or MassiveApiConfig(api_key=api_key)
        self.session = self.config.session
        self.BASE_URL = "https://api.massive.com"

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context manager."""
        self.config.increment_session_ref()
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore # noqa: ANN002
        """Exit the asynchronous context manager and close session if no other instances are using it."""
        self.config.decrement_session_ref()
        # Only close session when no more references exist
        if self.config.should_close_session() and self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(
        self,
        endpoint: str,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Make a single GET request to the Massive API with rate limiting and 429 retries.

        Args:
            endpoint: The API endpoint path (e.g. "tickers")
            params: Optional query parameters.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            MaxRetriesExceededError: If 429 responses persist past max_retries.
            aiohttp.ClientResponseError: For any non-429 HTTP error response.
            steindamm.MaxSleepExceededError: If the rate-limit wait exceeds max_sleep.

        """
        url = f"{self.BASE_URL}/{endpoint.strip('/')}"
        request_params = dict(params or {})
        headers = {"Authorization": f"Bearer {self.config.api_key}"}

        for attempt in range(self.config.max_retries + 1):
            try:
                async with (
                    self.config.rate_limiter(),
                    self.session.request("GET", url, params=request_params, headers=headers) as response,
                ):
                    response.raise_for_status()
                    data: dict[str, Any] = await response.json()
                    return data
            except aiohttp.ClientResponseError as e:
                if e.status != HTTP_TOO_MANY_REQUESTS:
                    raise
                # Retry on 429 errors
                if attempt >= self.config.max_retries:
                    raise MaxRetriesExceededError(self.config.max_retries, e.status) from None
                await asyncio.sleep(self._retry_backoff(attempt))

        msg = "Unexpected end of retry loop"
        raise RuntimeError(msg)

    async def _make_request_optional(
        self,
        endpoint: str,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Like `_make_request`, but return None when the resource does not exist (HTTP 404).

        Every other error (401, 429-past-retries, 5xx, ...) propagates unchanged. Use this for
        single-resource lookups where "not found" is a routine, expected outcome rather than a
        failure. A 404 here means the resource is absent; a malformed 200 payload still surfaces
        downstream (e.g. as a pydantic.ValidationError), so None unambiguously signals "not found".
        """
        try:
            return await self._make_request(endpoint, params)
        except aiohttp.ClientResponseError as e:
            if e.status == HTTP_NOT_FOUND:
                return None
            raise

    def _retry_backoff(self, attempt: int) -> float:
        """
        Seconds to wait before retrying a 429.

        Works for both, high and low rate limits. At least 1 second backoff is guaranteed,
        for low rate limits we start at a higher number automatically.
        """
        inter_token_interval = self.config.period_seconds / self.config.requests_per_period
        return max(inter_token_interval, float(2**attempt))

    async def _paginate(
        self,
        endpoint: str,
        params: Mapping[str, str] | None = None,
        max_results: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Yield records across pages, following the cursor in `next_url`.

        Stops after `max_results` records (None means every record). Each fetched page
        consumes one token from the shared rate limiter, so pagination halts as soon as
        the cap is reached rather than draining the whole result set.
        """
        yielded = 0
        data = await self._make_request(endpoint, params)
        while True:
            results: list[dict[str, Any]] = data.get("results") or []
            for item in results:
                yield item
                yielded += 1
                if max_results is not None and yielded >= max_results:
                    return
            next_url: str | None = data.get("next_url")
            if not next_url:
                return
            cursor = parse_qs(urlsplit(next_url).query).get("cursor")
            if not cursor:
                logger.warning(
                    "Couldn't parse 'next_url' parameter in API response, "
                    "stopping pagination of this resource. next_url=%s",
                    next_url,
                )
                return
            data = await self._make_request(endpoint, {"cursor": cursor[0]})

    async def _get_all_pages(
        self,
        endpoint: str,
        params: Mapping[str, str] | None = None,
        *,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Collect records across pages into a list of raw dicts, capped at `max_results`."""
        return [item async for item in self._paginate(endpoint, params, max_results=max_results)]

    def _resolve_validation_mode(self, override: Literal["raise", "skip"] | None) -> Literal["raise", "skip"]:
        """Resolve the effective validation mode from a per-call override and the config default."""
        return override if override is not None else self.config.on_validation_error

    def _validate_records(
        self,
        records: list[dict[str, Any]],
        model: type[ModelT],
        mode: Literal["raise", "skip"],
    ) -> list[ModelT]:
        """
        Validate raw records into `model` instances, validating the whole list at once.

        With mode "raise", an invalid record raises pydantic.ValidationError aggregating every
        bad row (by index). With mode "skip", the fast batch path is tried first; only if it
        fails are records re-validated one-by-one to drop (and log) the invalid ones.
        """
        adapter = _list_adapter(model)
        if mode == "raise":
            return cast("list[ModelT]", adapter.validate_python(records))
        try:
            return cast("list[ModelT]", adapter.validate_python(records))
        except ValidationError:
            validated: list[ModelT] = []
            for record in records:
                try:
                    validated.append(model.model_validate(record))
                except ValidationError as e:
                    logger.warning("Dropping invalid %s record: %s", model.__name__, e)
            return validated
