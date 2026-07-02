# EODHD-py

An async Python library for downloading financial data from [EODHD](https://eodhd.com/) with intelligent rate limiting. This is an individual project and is not associated with or sponsored by EODHD.

## Installation

```bash
pip install eodhd-py
```

## Quick Start

```python
import asyncio
from eodhd_py import EodhdApi

async def main():
    # Use demo API key (or set your own)
    async with EodhdApi(api_key="demo") as api:
        # Get end-of-day historical data
        df = await api.eod_historical_api.get_eod_data(symbol="AAPL", interval="d")
        print(f"Retrieved {len(df)} data points")

asyncio.run(main())
```

## Available APIs

By default, most API methods return pandas DataFrames. You can get dictionary output by passing `df_output=False` to any method. Some APIs like the User Api by default return a dictionary.
Existing EODHD APIs are being added gradually. Below are all the currently available options:

### EodHistoricalApi

Provides access to end-of-day historical data. [EODHD Documentation](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes)

```python
from datetime import datetime
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    # Returns a pandas DataFrame by default
    df = await api.eod_historical_api.get_eod_data(
        symbol="AAPL",                      # Stock symbol
        interval="d",                       # "d" (daily), "w" (weekly), "m" (monthly)
        order="a",                          # "a" (ascending), "d" (descending)
        from_date=datetime(2024, 1, 1),     # Optional start date
        to_date=datetime(2024, 12, 31),     # Optional end date
    )

    # Or get a dictionary by passing df_output=False
    data = await api.eod_historical_api.get_eod_data(
        symbol="AAPL",
        df_output=False,
    )
```

> **Note:** The EODHD API uses `period` instead of `interval`. For clarity, we use `interval`, which gets translated on the backend.

### IntradayHistoricalApi

Provides access to intraday historical data. [EODHD Documentation](https://eodhd.com/financial-apis/intraday-historical-data-api)

```python
from datetime import datetime
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    df = await api.intraday_historical_api.get_intraday_data(
        symbol="TSLA",                      # Stock symbol
        interval="5m",                      # "1m", "5m", or "1h"
        from_date=datetime(2024, 1, 1),     # Optional start date
        to_date=datetime(2024, 1, 31),      # Optional end date
        split_dt=False,                     # Split date and time into separate fields
    )
```

### UserApi

Provides access to user account information and API usage statistics. [EODHD Documentation](https://eodhd.com/financial-apis/user-api). Output is a dictonary instead of a dataframe.

```python
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    user_info = await api.user_api.get_user_info()
    print(f"Daily limit: {user_info['dailyRateLimit']}")
    print(f"Requests made: {user_info['apiRequests']}")
    print(f"Extra limit: {user_info['extraLimit']}")
```

### DividendsApi

Provides access to dividend data for stocks. [EODHD Documentation](https://eodhd.com/financial-apis/api-splits-dividends)

```python
from datetime import datetime
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    df = await api.dividends_api.get_dividends(
        symbol="AAPL.US",                   # Stock symbol with exchange
        from_date=datetime(2020, 1, 1),     # Optional start date
        to_date=datetime(2024, 12, 31),     # Optional end date
    )
```

### SplitsApi

Provides access to stock split data. [EODHD Documentation](https://eodhd.com/financial-apis/api-splits-dividends)

```python
from datetime import datetime
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    df = await api.splits_api.get_splits(
        symbol="AAPL.US",                   # Stock symbol with exchange
        from_date=datetime(1980, 1, 1),     # Optional start date
        to_date=datetime(2024, 12, 31),     # Optional end date
    )
```

### EarningsApi

Provides access to historical and upcoming earnings data. [EODHD Documentation](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits)

> Note: The API documentation mentions that passing the date parameters together with symbols doesn't work. This is incorrect, the API will work as expected when dates are provided.

```python
from datetime import datetime
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    # Query by date window (default: today + 7 days)
    df = await api.earnings_api.get_earnings(
        from_date=datetime(2024, 1, 1),     # Optional start date
        to_date=datetime(2024, 1, 31),      # Optional end date
    )

    # Query by symbols (default: today + 7 days)
    df = await api.earnings_api.get_earnings(
        symbols=["AAPL.US", "MSFT.US"],     # List of stock symbols
    )

    # Combine symbols with date filtering
    df = await api.earnings_api.get_earnings(
        symbols=["AAPL.US", "MSFT.US"],
        from_date=datetime(2024, 1, 1),
        to_date=datetime(2024, 12, 31),
    )
```

### IposApi

Provides access to historical and upcoming IPO data. [EODHD Documentation](https://eodhd.com/financial-apis/calendar-upcoming-earnings-ipos-and-splits)

```python
from datetime import datetime
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    # Query by date window (default: today + 7 days)
    df = await api.ipos_api.get_ipos(
        from_date=datetime(2024, 1, 1),     # Optional start date (uses filing_date)
        to_date=datetime(2024, 1, 31),      # Optional end date (uses filing_date)
    )
```

### ExchangesApi

Provides access to the list of supported exchanges. [EODHD Documentation](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours)

```python
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    # Get list of all supported exchanges
    df = await api.exchanges_api.get_exchanges()
```

> **Note:** The API returns not only stock exchanges but also other asset classes like Cryptocurrencies (CC), Forex (FOREX), Government Bonds (GBOND), and more.

### ExchangeSymbolListApi

Provides access to all tickers listed on a specific exchange. [EODHD Documentation](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours)

```python
from eodhd_py import EodhdApi

async with EodhdApi(api_key="your_api_key") as api:
    # Get all tickers on the US exchange
    df = await api.exchange_symbol_list_api.get_exchange_symbols(
        exchange_code="US",                 # Exchange code (e.g., "US", "LSE", "XETRA")
        delisted=False,                     # Set True to get delisted tickers only
        type="common_stock",                # Optional: "common_stock", "preferred_stock", "stock", "etf", "fund"
    )
```

> **Note:** For US stocks, use the unified exchange code 'US' which includes NYSE, NASDAQ, NYSE ARCA, and OTC markets. You can also use separate codes like 'NYSE', 'NASDAQ', 'BATS', WAR, etc.

### APIs pending implementation

Currently a lot of APIs haven't been implemented yet, below are the ones that were currently skipped:
 - Historical & Upcoming Dividends API (Note that the more detailed historical dividends API is already implemented)
 - Historical & Upcoming Splits API (Note that the more detailed historical splits API is already implemented)
 - Earnings Trends API

## Configuration Options

### **EodhdApiConfig**
The config class manages all configuration including sessions, rate limiters, and API limits. For rate limiting, the [Steindamm](https://github.com/feuerstein-org/steindamm) library is used.

Inside the config also lives the session. You can share it between different API classes to avoid opening multiple sessions, simply pass the same config class to different API instance to achieve that.

```python
from eodhd_py import EodhdApi, EodhdApiConfig

config = EodhdApiConfig(
    api_key="your_api_key",              # Required: Your EODHD API key, you can use "demo" for testing (default)
    max_retries=3,                       # Max retries for 429 responses
    daily_max_sleep=3600.0,              # Max wait time for daily limit (seconds)
    minute_max_sleep=120.0,              # Max wait time for minute limit (seconds)
    redis_connection=None,               # Optional Redis connection for distributed limiting
    rate_limit_key=None,                 # Optional unique key for rate limiter naming (max 8 chars)
)

async with EodhdApi(config=config) as api:
    data = await api.eod_historical_api.get_eod_data(symbol="AAPL")
```

**Note:** Rate limits are automatically shared between multiple endpoint instances for the same API key, even if the different endpoint instances use completely different configs! You can disable this by passing a unique `rate_limit_key` when creating the config (max_length=8). As a side-effect, this also means if you create different config classes that use the same API key, the limits should always be the same, otherwise they will conflict. In general, there should never be a case where you need to modify the rate limits since they are fetched from EODHD automatically.

The `max_sleep` values essentially specify how long the client will wait to make a request. A client will need to wait if the rate limits are currently exhausted. If the time that the client needs to wait exceeds the limit, a `steindamm.MaxSleepExceededError` is raised. If extra tokens are available in your EODHD subscription, a `steindamm.NoTokensAvailableError` is returned instead. The defaults can be modified as required, but keep in mind that setting the sleep too high will result in long-hanging clients.

### Error Handling

```python
from steindamm import MaxSleepExceededError, NoTokensAvailableError

try:
    async with EodhdApi(api_key="your_api_key") as api: # If no API key is provided "demo" is used
        data = await api.eod_historical_api.get_eod_data(symbol="AAPL")
except MaxSleepExceededError:
    print("Rate limit wait time exceeded configured maximum")
except NoTokensAvailableError:
    print("No API tokens available (extra limit exhausted)")
```

> **Note:**
> The library automatically fetches your API limits from the EODHD User API unless explicitly set. It is not recommended to override them, but it can be done if required:
> - `daily_calls_rate_limit` - Total daily API calls allowed
> - `daily_remaining_limit` - Remaining daily API calls
> - `extra_limit` - Additional non-refilling limit if available
> - `minute_requests_rate_limit` - Requests allowed per minute
> - `minute_remaining_limit` - Remaining minute requests

### Distributed Rate Limiting

Distributed rate limiting is also supported. This means you can download data from the API from multiple clients while not crossing the limits.

```python
from redis.asyncio import Redis  # or from redis.cluster import RedisCluster
from eodhd_py import EodhdApi, EodhdApiConfig

config = EodhdApiConfig(
    api_key="your_api_key",
    redis_connection=Redis.from_url("redis://localhost:6379"),  # Add Redis connection for distributed limiting
)

async with EodhdApi(config=config) as api:
    data = await api.eod_historical_api.get_eod_data(symbol="AAPL")
```

> **Important:** If the rate limits change (e.g., you buy more requests through the web UI), you need to restart the client or clear the Redis database. The reason is that the rate limit data is stored globally (or in Redis), and there's currently no support for clearing and updating those limits on the fly.

## Contributing

Contributions are very welcome. Here's how to get started:

- Clone the repo
- Install [mise en place](https://mise.jdx.dev/)
- Run `mise trust` to trust the `mise.toml` file
- Run `mise run install` to install dependencies
  If you prefer not to install mise, check the `mise.toml` file and
  run the commands manually, this would also require you to install [uv](https://docs.astral.sh/uv/getting-started/installation/) manually.
- Make your code changes, with tests
- Run tests with `mise run test` or `uv run pytest`
- Commit your changes and open a PR
