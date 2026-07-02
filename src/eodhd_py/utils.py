"""General validation functions."""

from re import compile as re_compile


def validate_normalize_symbol(symbol: str) -> str:
    """Validate and format a stock symbol for EODHD API."""
    is_market = symbol.count(".") == 2  # noqa: PLR2004

    # Validate symbol
    regex = re_compile(r"^[A-z0-9-$\.+]{1,48}$")
    if not regex.match(symbol):
        msg = f"Symbol is invalid: {symbol}"
        raise ValueError(msg)

    # replace "." with "-" in markets
    if is_market:
        # The API sees everything after a dot as the exchange.
        # When symbol has 2 dots (e.g., "SYMBOL.MARKET.EXCHANGE"), replace first dot
        # with hyphen to ensure API correctly parses it as "SYMBOL-MARKET" with exchange "EXCHANGE"
        # instead of incorrectly treating "MARKET.EXCHANGE" as the exchange
        symbol = symbol.replace(".", "-", 1)
    return symbol


def validate_order(order: str) -> bool:
    """Validate order parameter."""
    if order not in ("a", "d"):
        msg = "Order must be 'a' (ascending) or 'd' (descending)"
        raise ValueError(msg)
    return True


def validate_interval(interval: str, data_type: str = "intraday") -> bool:
    """Validate interval parameter for EOD or intraday data."""
    if data_type == "eod":
        if interval not in ("d", "w", "m"):
            msg = "Interval must be 'd' (daily), 'w' (weekly), or 'm' (monthly)"
            raise ValueError(msg)
    elif data_type == "intraday":
        if interval not in ("1m", "5m", "1h"):
            msg = "Interval must be '1m', '5m', or '1h'"
            raise ValueError(msg)
    else:
        msg = f"Invalid data_type: {data_type}. Must be 'eod' or 'intraday'"
        raise ValueError(msg)
    return True
