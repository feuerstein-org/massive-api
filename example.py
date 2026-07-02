"""Sample EODHD API usage."""

import asyncio
import logging

from eodhd_py import EodhdApi, EodhdApiConfig

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main function to demonstrate EODHD API usage."""
    # Example 1
    async with EodhdApi() as api:
        data = await api.eod_historical_api.get_eod_data(order="d", symbol="MSFT", interval="d")
        logger.info("Retrieved EOD data: %s", len(data))

    # Example 2
    # Using custom configuration
    config = EodhdApiConfig(
        api_key="demo",
        max_retries=5,
        daily_max_sleep=1800,  # Wait max 30 minutes for daily limit
        minute_max_sleep=60,  # Wait max 60 seconds for minute limit
        # Note: setting the below is not recommended since the client auto-handles rate limits
        # daily_calls_rate_limit=50000,  # 50k requests per day
        # daily_remaining_limit=10000,  # 10k remaining requests
        # minute_requests_rate_limit=500,  # 500 requests per minute
        # minute_remaining_limit=100,  # 100 remaining requests
        # extra_limit=10,  # 10 extra non-refilling requests
    )
    async with EodhdApi(config=config) as api:
        eod_data = await api.eod_historical_api.get_eod_data(symbol="AAPL", interval="d")
        logger.info("EOD data retrieved: %s", len(eod_data))

        intraday_data = await api.intraday_historical_api.get_intraday_data(symbol="TSLA", interval="5m")
        logger.info("Intraday data retrieved: %s", len(intraday_data))

        dividends_data = await api.dividends_api.get_dividends(symbol="AAPL.US")
        logger.info("Dividends data retrieved: %s", len(dividends_data))

        splits_data = await api.splits_api.get_splits(symbol="AAPL.US")
        logger.info("Splits data retrieved: %s", len(splits_data))

        earnings_by_symbols = await api.earnings_api.get_earnings(symbols=["AAPL.US", "MCD.US"])
        logger.info("Earnings by symbols retrieved: %s", len(earnings_by_symbols))

        # Below API requests require a real API key

        # ipos_data = await api.ipos_api.get_ipos()
        # logging.info("IPOs data retrieved: %s", len(ipos_data))

        # exchanges_data = await api.exchanges_api.get_exchanges()
        # logging.info("Exchanges data retrieved: %s", len(exchanges_data))

        # exchange_symbols = await api.exchange_symbol_list_api.get_exchange_symbols(exchange_code="US")
        # logging.info("Exchange symbols retrieved: %s", len(exchange_symbols))

    logger.info("Done")


asyncio.run(main())
