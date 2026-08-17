"""Configuration for MassiveApi and its endpoints."""

from typing import Any, Literal

from spitzeisen import BearerHeader, ClientConfig

BASE_URL = "https://api.massive.com"


def massive_config(
    api_key: str,
    *,
    requests_per_period: float = 100.0,
    period_seconds: float = 1.0,
    rate_limit_max_sleep: float = 60.0,
    max_retries: int = 3,
    request_timeout: float = 30.0,
    on_validation_error: Literal["raise", "skip"] = "skip",
    redis_connection: Any = None,
    rate_limit_key: str | None = None,
) -> ClientConfig:
    """
    Build the client configuration.

    A single token bucket allows `requests_per_period` requests every `period_seconds`
    (default 100 per second) with smooth refill. Capacity equals a full period's allowance, so
    a burst of up to one period is tolerated before the steady rate takes over. Every request,
    including each page of a paginated result, draws one token. For the basic free tier, pass
    `requests_per_period=5, period_seconds=60`.

    The bucket is shared between instances using the same API key, even when they do not share
    a config object. Pass a distinct `rate_limit_key` to opt out, or a `redis_connection` to
    share it across processes.

    Retries use exponential backoff, floored at the interval between tokens so that a slow
    tier waits long enough to earn one rather than collecting another 429.

    `on_validation_error` sets the default for validated list methods: "raise" propagates the
    first bad record, "skip" (the default) drops and logs them.
    """
    key = rate_limit_key or str(abs(hash(api_key)))[:8]
    return ClientConfig(
        base_url=BASE_URL,
        auth=BearerHeader(api_key),
        max_retries=max_retries,
        request_timeout=request_timeout,
        requests_per_period=requests_per_period,
        period_seconds=period_seconds,
        limiter_name=f"massive_{key}",
        limiter_max_sleep=rate_limit_max_sleep,
        redis_connection=redis_connection,
        on_validation_error=on_validation_error,
        # On a slow tier a one-second retry simply earns another 429, so wait at least long
        # enough for the next token.
        retry_backoff_floor=period_seconds / requests_per_period,
    )
