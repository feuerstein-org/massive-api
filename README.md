# massive-api

An async Python client for the [Massive](https://massive.com/) financial-data REST API,
with smooth built-in rate limiting, cursor pagination, and pydantic validation. This is an
individual project and is not associated with or sponsored by Massive.

## Installation

```bash
pip install massive-py
```

## Quick Start

```python
import asyncio
from massive_api import MassiveApi

async def main():
    async with MassiveApi(api_key="YOUR_API_KEY") as api:
        # All tickers (paginated automatically, validated into models)
        tickers = await api.reference_api.get_all_tickers(market="stocks", active=True)
        print(len(tickers), "tickers")

        # Single ticker overview
        overview = await api.reference_api.get_ticker_overview("AAPL")
        print(overview.market_cap, overview.total_employees)

        # Corporate events (e.g. ticker changes)
        events = await api.reference_api.get_ticker_events("META")

        # Stock splits (paginated automatically)
        splits = await api.splits_api.get_splits(ticker="AAPL")

asyncio.run(main())
```

## Supported APIs

| Accessor | Method | Massive endpoint |
| --- | --- | --- |
| `reference_api` | `get_all_tickers(...)` | `GET /v3/reference/tickers` |
| `reference_api` | `get_ticker_overview(ticker, ...)` | `GET /v3/reference/tickers/{ticker}` |
| `reference_api` | `get_ticker_events(ticker_id, ...)` | `GET /vX/reference/tickers/{id}/events` |
| `splits_api` | `get_splits(...)` | `GET /stocks/v1/splits` |
| `dividends_api` | `get_dividends(...)` | `GET /stocks/v1/dividends` |

More endpoints are coming soon. Contributions are welcome - see [Contributing](#contributing).

## Rate limiting

A single in-memory token bucket enforces **`requests_per_period` requests every `period_seconds`** (default 100 per 1s) with smooth refill. Bucket capacity equals `requests_per_period`, so it tolerates a burst of up to one full period's allowance before settling to the steady rate. The bucket is shared across all endpoint instances that use the same API key. Every request - including each page of a paginated result - draws one token.
Configure it via `MassiveApiConfig`:

```python
from massive_api import MassiveApiConfig

config = MassiveApiConfig(
    api_key="YOUR_API_KEY",
    requests_per_period=100,      # requests allowed per period
    period_seconds=1,             # length of the period, in seconds
    rate_limit_max_sleep=60,      # raise MaxSleepExceededError beyond this wait
    max_retries=3,                # exponential backoff on HTTP 429
    # redis_connection=redis_conn,  # optional: distributed rate limiting via redis.asyncio
)
```

For the Massive **basic free tier** (5 requests/minute), set:

```python
config = MassiveApiConfig(api_key="YOUR_API_KEY", requests_per_period=5, period_seconds=60)
```

Requests that receive HTTP 429 are retried up to `max_retries` with exponential backoff
(1s, 2s, 4s, …), floored at the token-refill interval (`period_seconds /
requests_per_period`) so a slow tier waits at least long enough for the next token - e.g. on
the 5/minute free tier each retry waits ≥12s rather than earning another 429.

## Pagination

List endpoints (`get_all_tickers`, `get_splits`) follow Massive's `next_url` cursor
automatically. A single client-side control governs how much is fetched:

- **`max_results`** - a cap on the *total* records returned across all pages. Pagination
  stops as soon as the cap is reached, so `max_results=10` costs **one** request, not
  one-per-record. `None` (default) means "every matching record".

Each request always asks for the API's maximum page size (fewest requests), automatically
reduced to `max_results` when that is smaller so a small cap never over-fetches.

```python
await api.reference_api.get_all_tickers(max_results=10)      # 1 request, ≤10 rows
await api.reference_api.get_all_tickers(max_results=10_000)  # ~10 requests, ≤10k rows
await api.reference_api.get_all_tickers()                    # every row, page size = API max
```

## Concurrency

Use `gather_bounded` to fan out many requests (e.g. Ticker Overview across ~10k tickers)
while keeping the number of in-flight coroutines bounded so they saturate - but do not
overrun - the 100/s bucket:

```python
from massive_api import gather_bounded

symbols = [...]  # thousands of tickers
overviews = await gather_bounded(
    50,
    *(api.reference_api.get_ticker_overview(s) for s in symbols),
)
```

The `gather_bounded` function is just a small and lightweight wrapper, for real-world usage with things like exception handling etc. you most likely would want to manage the coroutines yourself.

See [Little's law](https://en.wikipedia.org/wiki/Little%27s_law) to calculate the amount of coroutines needed. At an average latency of 250ms 50 coroutines should be more than enough for 100 requests/s.

## Response validation

Each list endpoint offers three ways to handle response validation:

1. **validated (default)** - validate every record and raise `pydantic.ValidationError` on the first bad row. Returns `list[Model]`. This is the boundary default.
2. **skip** - validate per record, drop invalid rows (logging each), and return only the valid ones. Returns `list[Model]` (possibly shorter).
3. **raw** - no validation; return the untouched JSON dicts exactly as sent. Exposed as separate `*_raw()` methods returning `list[dict]`.

The default of (1) vs (2) is set on the config and can be overridden per call:

```python
config = MassiveApiConfig(api_key="...", on_validation_error="skip")  # default for all calls

# Per-call override
tickers = await api.reference_api.get_all_tickers(on_validation_error="raise")

# Raw path (returns list[dict], never raises):
raw = await api.reference_api.get_all_tickers_raw(market="stocks")
```

## Development

```bash
mise run install   # sync deps + install pre-commit hooks
mise run lint      # ruff check + format check
mise run test      # pyright + ruff + pytest with coverage
```

See [`example.py`](example.py) for a runnable end-to-end example.

## Contributing

Contributions are welcome! Additional endpoint coverage is on the roadmap, and pull
requests that add endpoints, fix bugs, or improve the docs are appreciated. Please run the
lint and test suite above before opening a pull request.
