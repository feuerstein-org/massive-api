"""
Reference data API endpoints (tickers, ticker overview, ticker events).

Official documentation:
  https://massive.com/docs/rest/stocks/corporate-actions/ticker-events
  https://massive.com/docs/rest/stocks/tickers/all-tickers
  https://massive.com/docs/rest/stocks/tickers/ticker-overview
"""

import datetime as dt
from typing import Any, Literal

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from massive_api.base import BaseMassiveApi
from massive_api.params import Locale, Market, Order, TickerEventType, TickerSortField
from massive_api.utils import (
    build_query_params,
    coerce_choice,
    coerce_date,
    coerce_max_results,
    resolve_page_size,
)

TICKERS_ENDPOINT = "v3/reference/tickers"
TICKER_EVENTS_ENDPOINT = "vX/reference/tickers"
TICKERS_MAX_PAGE_SIZE = 1000


class Ticker(BaseModel):
    """A single ticker record from the All Tickers endpoint."""

    model_config = ConfigDict(extra="ignore")

    ticker: str
    active: bool
    name: str | None = None
    market: Market | None = None
    locale: Locale | None = None
    type: str | None = None
    primary_exchange: str | None = None
    currency_name: str | None = None
    currency_symbol: str | None = None
    base_currency_name: str | None = None
    base_currency_symbol: str | None = None
    cik: str | None = None
    composite_figi: str | None = None
    share_class_figi: str | None = None
    last_updated_utc: dt.datetime | None = None
    delisted_utc: dt.datetime | None = None


class TickerOverview(BaseModel):
    """Detailed company/ticker information from the Ticker Overview endpoint."""

    model_config = ConfigDict(extra="ignore")

    ticker: str
    name: str
    market: Market
    locale: Locale
    active: bool
    currency_name: str
    type: str | None = None
    primary_exchange: str | None = None
    cik: str | None = None
    composite_figi: str | None = None
    market_cap: float | None = None
    total_employees: int | None = None
    weighted_shares_outstanding: int | None = None
    share_class_shares_outstanding: int | None = None
    share_class_figi: str | None = None
    round_lot: int | None = None
    sic_code: str | None = None
    sic_description: str | None = None
    homepage_url: str | None = None
    description: str | None = None
    phone_number: str | None = None
    # Flattened from the nested `address` object in the response.
    address1: str | None = Field(default=None, validation_alias=AliasPath("address", "address1"))
    address2: str | None = Field(default=None, validation_alias=AliasPath("address", "address2"))
    city: str | None = Field(default=None, validation_alias=AliasPath("address", "city"))
    state: str | None = Field(default=None, validation_alias=AliasPath("address", "state"))
    postal_code: str | None = Field(default=None, validation_alias=AliasPath("address", "postal_code"))
    # Flattened from the nested `branding` object in the response.
    icon_url: str | None = Field(default=None, validation_alias=AliasPath("branding", "icon_url"))
    logo_url: str | None = Field(default=None, validation_alias=AliasPath("branding", "logo_url"))
    list_date: dt.date | None = None
    delisted_utc: dt.datetime | None = None
    last_updated_utc: dt.datetime | None = None
    ticker_root: str | None = None
    ticker_suffix: str | None = None


class TickerChange(BaseModel):
    """The new ticker recorded by a ticker_change event."""

    model_config = ConfigDict(extra="ignore")

    ticker: str


class TickerEvent(BaseModel):
    """A single corporate event (e.g. a ticker change) in a ticker's history."""

    model_config = ConfigDict(extra="ignore")

    type: str
    date: dt.date
    # Present for `ticker_change` events; absent for other event types.
    ticker_change: TickerChange | None = None


class TickerEvents(BaseModel):
    """History of corporate events for a ticker from the Ticker Events endpoint."""

    model_config = ConfigDict(extra="ignore")

    name: str
    events: list[TickerEvent]
    figi: str | None = None
    cik: str | None = None
    composite_figi: str | None = None


class ReferenceApi(BaseMassiveApi):
    """Reference data endpoints: All Tickers, Ticker Overview, and Ticker Events."""

    async def get_all_tickers_raw(  # noqa: PLR0913
        self,
        *,
        ticker: str | None = None,
        ticker_gt: str | None = None,
        ticker_gte: str | None = None,
        ticker_lt: str | None = None,
        ticker_lte: str | None = None,
        ticker_type: str | None = None,
        active: bool = True,
        market: Market | None = None,
        exchange: str | None = None,
        cusip: str | None = None,
        cik: str | None = None,
        date: str | dt.date | dt.datetime | None = None,
        search: str | None = None,
        max_results: int | None = None,
        sort: TickerSortField = "ticker",
        order: Order = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch tickers across pages as raw JSON dicts (no validation).

        Docs: https://massive.com/docs/rest/stocks/tickers/all-tickers

        See `get_all_tickers` for the meaning of each parameter.
        """
        max_results = coerce_max_results(max_results)
        params = build_query_params(
            {
                "ticker": ticker,
                "ticker.gt": ticker_gt,
                "ticker.gte": ticker_gte,
                "ticker.lt": ticker_lt,
                "ticker.lte": ticker_lte,
                "type": ticker_type,
                "market": coerce_choice(market, Market, "market"),
                "exchange": exchange,
                "cusip": cusip,
                "cik": cik,
                "active": active,
                "date": coerce_date(date, "date"),
                "search": search,
                "order": coerce_choice(order, Order, "order"),
                "limit": resolve_page_size(max_results, TICKERS_MAX_PAGE_SIZE),
                "sort": coerce_choice(sort, TickerSortField, "sort"),
            },
        )
        return await self._get_all_pages(TICKERS_ENDPOINT, params, max_results=max_results)

    async def get_all_tickers(  # noqa: PLR0913
        self,
        *,
        ticker: str | None = None,
        ticker_gt: str | None = None,
        ticker_gte: str | None = None,
        ticker_lt: str | None = None,
        ticker_lte: str | None = None,
        ticker_type: str | None = None,
        active: bool = True,
        market: Market | None = None,
        exchange: str | None = None,
        cusip: str | None = None,
        cik: str | None = None,
        date: str | dt.date | dt.datetime | None = None,
        search: str | None = None,
        max_results: int | None = None,
        sort: TickerSortField = "ticker",
        order: Order = "asc",
        on_validation_error: Literal["raise", "skip"] | None = None,
    ) -> list[Ticker]:
        """
        Get tickers (across pages, up to `max_results`), validated into `Ticker` models.

        Docs: https://massive.com/docs/rest/stocks/tickers/all-tickers

        Args:
            ticker: Exact ticker symbol to match.
            ticker_gt: Return tickers greater than this symbol (range scan).
            ticker_gte: Return tickers greater than or equal to this symbol.
            ticker_lt: Return tickers less than this symbol.
            ticker_lte: Return tickers less than or equal to this symbol.
            ticker_type: Filter by ticker type (e.g. "CS", "ETF") - by default all types.
            market: Filter by market. One of the `Market` values (e.g. "stocks") - by default all markets.
            exchange: Filter by primary exchange (ISO 10383 MIC code) - by default all exchanges.
            cusip: Filter by CUSIP (note: not returned in the response for legal reasons) - by default query all CUSIPs.
            cik: Filter by SEC Central Index Key (CIK) - by default query all CIKs.
            active: Whether to return active (True and default) or delisted (False) tickers.
            date: Point-in-time date for the ticker universe (ISO string or date/datetime) - by default latest date.
            search: Case-insensitive search over ticker and name.
            max_results: Maximum total records to return.
            sort: Field to sort by. One of the `TickerSortField` values. Defaults to "ticker".
            order: Sort direction, "asc" or "desc" (an `Order` value). Defaults to "asc".
            on_validation_error: Override the config default ("raise" or "skip") for this call.

        Returns:
            A list of `Ticker` models (at most `max_results`).

        Raises:
            ValueError: If `market`, `order`, `sort`, `date`, or `max_results` is invalid.

        """
        records = await self.get_all_tickers_raw(
            ticker=ticker,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            ticker_type=ticker_type,
            market=market,
            exchange=exchange,
            cusip=cusip,
            cik=cik,
            active=active,
            date=date,
            search=search,
            order=order,
            max_results=max_results,
            sort=sort,
        )
        mode = self._resolve_validation_mode(on_validation_error)
        return self._validate_records(records, Ticker, mode)

    async def get_ticker_overview_raw(
        self,
        ticker: str,
        *,
        date: str | dt.date | dt.datetime | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch the raw JSON `results` object for a single ticker (no validation).

        Returns None if the ticker does not exist (HTTP 404).

        Docs: https://massive.com/docs/rest/stocks/tickers/ticker-overview
        """
        params = build_query_params({"date": coerce_date(date, "date")})
        data = await self._make_request_optional(f"{TICKERS_ENDPOINT}/{ticker}", params)
        if data is None:
            return None
        return data.get("results") or {}

    async def get_ticker_overview(
        self,
        ticker: str,
        *,
        date: str | dt.date | dt.datetime | None = None,
    ) -> TickerOverview | None:
        """
        Get detailed information for a single ticker, validated into a `TickerOverview`.

        Docs: https://massive.com/docs/rest/stocks/tickers/ticker-overview

        Args:
            ticker: Case-sensitive ticker symbol (e.g. "AAPL").
            date: Optional point-in-time date (ISO string or date/datetime); defaults to latest.

        Returns:
            A validated `TickerOverview`, or None if the ticker does not exist (HTTP 404).
            Raises pydantic.ValidationError on an invalid payload.

        """
        raw = await self.get_ticker_overview_raw(ticker, date=date)
        if raw is None:
            return None
        return TickerOverview.model_validate(raw)

    async def get_ticker_events_raw(
        self,
        ticker_id: str,
        *,
        types: TickerEventType | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch the raw JSON `results` object of ticker events (no validation).

        Returns None if the ticker does not exist (HTTP 404).

        Docs: https://massive.com/docs/rest/stocks/corporate-actions/ticker-events
        """
        params = build_query_params({"types": coerce_choice(types, TickerEventType, "types")})
        data = await self._make_request_optional(f"{TICKER_EVENTS_ENDPOINT}/{ticker_id}/events", params)
        if data is None:
            return None
        return data.get("results") or {}

    async def get_ticker_events(
        self,
        ticker_id: str,
        *,
        types: TickerEventType | None = None,
    ) -> TickerEvents | None:
        """
        Get the corporate-event history for a ticker, validated into `TickerEvents`.

        Docs: https://massive.com/docs/rest/stocks/corporate-actions/ticker-events

        Args:
            ticker_id: A ticker symbol, CUSIP, or Composite FIGI.
            types: Event type to include. A `TickerEventType` value (e.g. "ticker_change").

        Returns:
            A validated `TickerEvents`, or None if the ticker does not exist (HTTP 404).
            Raises pydantic.ValidationError on an invalid payload.

        """
        raw = await self.get_ticker_events_raw(ticker_id, types=types)
        if raw is None:
            return None
        return TickerEvents.model_validate(raw)
