"""Sample Massive API usage."""

import asyncio
import logging

from massive_api import MassiveApi, MassiveApiConfig, gather_bounded

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Demonstrate Massive API usage."""
    # Example 1: default config (flat 100 requests/second rate limiting).
    async with MassiveApi(api_key="demo") as api:
        # Closed-set params are typed Literals: a type checker flags a wrong string here.
        # max_results caps total records (here: at most 50, fetched in one efficient request).
        tickers = await api.reference_api.get_all_tickers(
            market="stocks",
            active=True,
            order="asc",
            sort="ticker",
            max_results=50,
        )
        logger.info("Retrieved %s tickers", len(tickers))

        overview = await api.reference_api.get_ticker_overview("AAPL")
        logger.info("AAPL market cap: %s", overview.market_cap)

        events = await api.reference_api.get_ticker_events("META")
        logger.info("META events: %s", len(events.events))

        splits = await api.splits_api.get_splits(ticker="AAPL")
        logger.info("Retrieved %s splits", len(splits))

    # Example 2: custom config + bounded-concurrency fan-out over many tickers.
    config = MassiveApiConfig(
        api_key="demo",
        max_retries=5,
        # Drop invalid rows instead of raising (per-call override also available).
        on_validation_error="skip",
        # Optional: pass a redis.asyncio connection for distributed rate limiting.
        # redis_connection=redis_conn,
    )
    async with MassiveApi(config=config) as api:
        symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
        # Saturate the 100/s bucket without spawning unbounded coroutines.
        overviews = await gather_bounded(
            50,
            *(api.reference_api.get_ticker_overview(symbol) for symbol in symbols),
        )
        for overview in overviews:
            logger.info("%s: %s employees", overview.ticker, overview.total_employees)

        # Raw path: untouched JSON dicts, no validation.
        raw_splits = await api.splits_api.get_splits_raw(ticker="AAPL")
        logger.info("Raw splits payload: %s rows", len(raw_splits))

    logger.info("Done")


asyncio.run(main())
