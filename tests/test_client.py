"""
Client wiring and this client's own rate-limit policy.

Retries, backoff, cursor pagination, validation modes and the typed exception hierarchy are
spitzeisen's and are tested in spitzeisen; duplicating them here would only mean two suites to
keep in step. What is left is what belongs to *this* client: that the accessors are wired up,
that a config turns Massive's documented tiers into the right bucket, and that the auth header
Massive expects actually goes out.
"""

import pytest
from conftest import generate_random_api_key
from spitzeisen import AsyncTransport, NoAsyncLimit, NoSyncLimit, SyncTransport
from spitzeisen.limits import REFILL_INTERVAL_SECONDS
from spitzeisen.testing import FakeRouter

from massive_api import (
    AggregatesApi,
    DividendsApi,
    MassiveApi,
    MassiveApiSync,
    ReferenceApi,
    massive_config,
)

TICKERS_PATH = "/v3/reference/tickers"
DEFAULT_RATE = 100.0
FREE_TIER_RATE = 5.0
FREE_TIER_PERIOD = 60.0


def test_api_key_alone_is_enough() -> None:
    """The common case: a key, and every default Massive documents."""
    api = MassiveApi(api_key=generate_random_api_key())

    assert api.config.base_url == "https://api.massive.com"
    assert api.config.requests_per_period == DEFAULT_RATE


def test_neither_config_nor_key_is_an_error() -> None:
    """Constructing without credentials fails immediately rather than at the first request."""
    with pytest.raises(ValueError, match="Neither a valid config nor a valid API key"):
        MassiveApi()


@pytest.mark.parametrize(
    ("accessor", "expected"),
    [
        ("reference_api", ReferenceApi),
        ("dividends_api", DividendsApi),
        ("aggregates_api", AggregatesApi),
    ],
)
def test_accessors_are_built_once_and_reused(accessor: str, expected: type) -> None:
    """Endpoint instances are lazy and shared, so they share a transport and a limiter."""
    api = MassiveApi(api_key=generate_random_api_key())

    first = getattr(api, accessor)

    assert isinstance(first, expected)
    assert getattr(api, accessor) is first


def test_reference_groups_three_endpoints() -> None:
    """The reference accessor composes what the generator emits as three separate layers."""
    api = MassiveApi(api_key=generate_random_api_key())

    methods = {name for name in dir(api.reference_api) if name.startswith("get_") and not name.endswith("_raw")}

    assert methods == {"get_all_tickers", "get_ticker_overview", "get_ticker_events"}


def test_default_tier_is_a_smooth_hundred_per_second() -> None:
    """
    Massive's standard tier, spread evenly rather than spent in a burst.

    Capacity is a full second's allowance, refilled in tenths so a hundred requests do not all
    leave at once.
    """
    config = massive_config(generate_random_api_key())

    assert config.requests_per_period == DEFAULT_RATE
    assert config.period_seconds == 1.0
    assert config.retry_backoff_floor == pytest.approx(1 / DEFAULT_RATE)


def test_free_tier_backoff_waits_for_a_token() -> None:
    """
    On five requests a minute, a one-second retry would just earn another 429.

    The floor is the interval between tokens, so a retry waits long enough to be served.
    """
    config = massive_config(
        generate_random_api_key(),
        requests_per_period=FREE_TIER_RATE,
        period_seconds=FREE_TIER_PERIOD,
    )

    assert config.retry_backoff_floor == pytest.approx(FREE_TIER_PERIOD / FREE_TIER_RATE)
    assert config.backoff(0) == pytest.approx(12.0)


def test_the_same_key_shares_a_bucket() -> None:
    """Two clients with one key must not each get a full allowance."""
    key = generate_random_api_key()

    assert massive_config(key).limiter_name == massive_config(key).limiter_name
    assert massive_config(key).limiter_name != massive_config(generate_random_api_key()).limiter_name


def test_a_rate_limit_key_opts_out_of_sharing() -> None:
    """Callers who want an independent allowance can say so."""
    key = generate_random_api_key()

    assert massive_config(key).limiter_name != massive_config(key, rate_limit_key="separate").limiter_name


def test_bucket_refills_smoothly() -> None:
    """The bucket spitzeisen builds from this config drips rather than dumps."""
    limiter = MassiveApi(api_key=generate_random_api_key()).reference_api._limiter

    assert limiter.capacity == DEFAULT_RATE
    assert limiter.refill_frequency == REFILL_INTERVAL_SECONDS
    assert limiter.refill_amount == pytest.approx(DEFAULT_RATE * REFILL_INTERVAL_SECONDS)


async def test_bearer_header_is_sent() -> None:
    """Massive authenticates with a bearer token; the request has to carry one."""
    key = generate_random_api_key()
    router = FakeRouter().add(TICKERS_PATH, json={"results": []})
    config = massive_config(key)
    config.transport = AsyncTransport(transport=router.mock_transport())
    config.limiter = NoAsyncLimit()

    async with MassiveApi(config) as api:
        await api.reference_api.get_all_tickers()

    assert router.requests[0].headers["authorization"] == f"Bearer {key}"


async def test_the_transport_closes_once_the_client_exits() -> None:
    """One shared transport, torn down when the last holder leaves."""
    router = FakeRouter().add(TICKERS_PATH, json={"results": []})
    config = massive_config(generate_random_api_key())
    config.transport = transport = AsyncTransport(transport=router.mock_transport())
    config.limiter = NoAsyncLimit()

    async with MassiveApi(config) as api:
        await api.reference_api.get_all_tickers()

    assert transport.client.is_closed


def test_the_blocking_client_exposes_the_same_surface() -> None:
    """Whatever the async client can do, the blocking one can too."""
    router = FakeRouter().add(TICKERS_PATH, json={"results": [{"ticker": "AAPL", "active": True}]})
    config = massive_config(generate_random_api_key())
    config.transport = SyncTransport(transport=router.mock_transport())
    config.limiter = NoSyncLimit()

    with MassiveApiSync(config) as api:
        tickers = api.reference_api.get_all_tickers()

    assert [ticker.ticker for ticker in tickers] == ["AAPL"]
