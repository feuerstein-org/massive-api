"""
API endpoint cost mapping for rate limiting.

This module defines the cost (in API tokens) for different EODHD API endpoints.
Different endpoints consume different amounts of API quota.
"""

import functools
from typing import Final

# Cost mapping for different endpoint patterns
# Based on EODHD API documentation, different endpoints have different daily API costs
ENDPOINT_COSTS: Final[dict[str, int]] = {
    # User API
    "user": 0,
    # EOD Historical Data
    "eod": 1,
    # Intraday Historical Data
    "intraday": 5,
    # Dividends Data
    "div": 1,
    # Splits Data
    "splits": 1,
    # Calendar Data (Earnings, IPOs, etc.)
    "calendar": 1,
    # Exchanges Data
    "exchanges": 1,
    # Exchange Symbol List
    "exchange-symbol-list": 1,
}


@functools.lru_cache(maxsize=128)
def get_endpoint_cost(endpoint: str) -> int:
    """
    Get the API cost for a given endpoint.

    Args:
        endpoint: The API endpoint path (e.g., "eod/AAPL", "intraday/TSLA", "user")

    Returns:
        The cost in API tokens for this endpoint

    """
    # Strip leading/trailing slashes and extract the base endpoint
    endpoint_clean = endpoint.strip("/")
    endpoint_base = endpoint_clean.split("/")[0].lower()

    # Return the cost for this endpoint, or default if not found
    return ENDPOINT_COSTS.get(endpoint_base, 1)  # Default to 1 for unknown endpoints
