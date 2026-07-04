"""Package allows for querying the Massive API using an async interface."""

from massive_api.api.reference import (
    ReferenceApi,
    Ticker,
    TickerChange,
    TickerEvent,
    TickerEvents,
    TickerOverview,
)
from massive_api.api.splits import Split, SplitsApi
from massive_api.base import BaseMassiveApi, MassiveApiConfig
from massive_api.client import MassiveApi
from massive_api.exceptions import MassiveApiError, MaxRetriesExceededError
from massive_api.params import (
    AdjustmentType,
    Locale,
    Market,
    Order,
    SplitSortField,
    TickerEventType,
    TickerSortField,
)
from massive_api.utils import build_query_params, gather_bounded

__all__ = (
    "AdjustmentType",
    "BaseMassiveApi",
    "Locale",
    "Market",
    "MassiveApi",
    "MassiveApiConfig",
    "MassiveApiError",
    "MaxRetriesExceededError",
    "Order",
    "ReferenceApi",
    "Split",
    "SplitSortField",
    "SplitsApi",
    "Ticker",
    "TickerChange",
    "TickerEvent",
    "TickerEventType",
    "TickerEvents",
    "TickerOverview",
    "TickerSortField",
    "build_query_params",
    "gather_bounded",
)
