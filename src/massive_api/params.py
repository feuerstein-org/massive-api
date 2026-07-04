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

DividendSortField = Literal["ticker", "ex_dividend_date", "frequency", "distribution_type"]

AdjustmentType = Literal["forward_split", "reverse_split", "stock_dividend"]

DistributionType = Literal["recurring", "special", "supplemental", "irregular", "unknown"]

# Documented payout cadences: 0 = non-recurring/irregular, 1 = annual, 2 = semi-annual,
# 3 = trimester, 4 = quarterly, 12 = monthly, 24 = bi-monthly, 52 = weekly, 104 = bi-weekly,
# 365 = daily.
DividendFrequency = Literal[0, 1, 2, 3, 4, 12, 24, 52, 104, 365]

TickerEventType = Literal["ticker_change"]
