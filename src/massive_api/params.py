"""Typed value sets for closed-set Massive API query parameters."""

from typing import Literal

Order = Literal["asc", "desc"]

Market = Literal["stocks", "crypto", "fx", "otc", "indices"]

Locale = Literal["us", "global"]

TickerSortField = Literal[
    "ticker",
    "name",
    "market",
    "locale",
    "primary_exchange",
    "type",
    "currency_name",
    "cik",
    "composite_figi",
    "share_class_figi",
    "last_updated_utc",
    "delisted_utc",
]

SplitSortField = Literal["ticker", "execution_date"]

AdjustmentType = Literal["forward_split", "reverse_split", "stock_dividend"]

TickerEventType = Literal["ticker_change"]
