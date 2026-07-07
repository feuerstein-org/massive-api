"""
Dividends API endpoint.

Official documentation: https://massive.com/docs/rest/stocks/corporate-actions/dividends
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from massive_api.base import BaseMassiveApi
from massive_api.params import DistributionType, DividendFrequency, DividendSortField, Order
from massive_api.utils import (
    build_query_params,
    coerce_choice,
    coerce_choices,
    coerce_date,
    coerce_max_results,
    coerce_sort,
    resolve_page_size,
)

DIVIDENDS_ENDPOINT = "stocks/v1/dividends"
DIVIDENDS_MAX_PAGE_SIZE = 5000


class Dividend(BaseModel):
    """
    A single cash dividend record from the Dividends endpoint.
    """

    model_config = ConfigDict(extra="ignore")

    ticker: str
    # ISO "yyyy-mm-dd" in the payload; parsed into a real date.
    ex_dividend_date: date
    # Original dividend amount per share in `currency`.
    cash_amount: float
    distribution_type: DistributionType
    # Expected payouts per year; 0 means non-recurring/irregular.
    frequency: int | None = None
    currency: str | None = None
    declaration_date: date | None = None
    record_date: date | None = None
    pay_date: date | None = None
    # `cash_amount` restated on a current share basis (adjusted for later splits).
    split_adjusted_cash_amount: float | None = None
    # Cumulative factor used to offset dividend effects on historical prices.
    historical_adjustment_factor: float | None = None
    id: str | None = None


class DividendsApi(BaseMassiveApi):
    """Dividends endpoint: historical cash dividend distributions with adjustment factors."""

    async def get_dividends_raw(  # noqa: PLR0913
        self,
        *,
        ticker: str | None = None,
        tickers: list[str] | None = None,
        ticker_gt: str | None = None,
        ticker_gte: str | None = None,
        ticker_lt: str | None = None,
        ticker_lte: str | None = None,
        ex_dividend_date: str | date | datetime | None = None,
        ex_dividend_date_gt: str | date | datetime | None = None,
        ex_dividend_date_gte: str | date | datetime | None = None,
        ex_dividend_date_lt: str | date | datetime | None = None,
        ex_dividend_date_lte: str | date | datetime | None = None,
        frequency: DividendFrequency | None = None,
        frequency_gt: int | None = None,
        frequency_gte: int | None = None,
        frequency_lt: int | None = None,
        frequency_lte: int | None = None,
        distribution_types: list[DistributionType] | None = None,
        max_results: int | None = None,
        sort: DividendSortField = "ticker",
        order: Order = "asc",
    ) -> list[dict[str, Any]]:
        """
        Fetch dividends across pages as raw JSON dicts (no validation).

        Docs: https://massive.com/docs/rest/stocks/corporate-actions/dividends

        See `get_dividends` for the meaning of each parameter.
        """
        max_results = coerce_max_results(max_results)
        params = build_query_params(
            {
                "ticker": ticker,
                "ticker.any_of": ",".join(tickers) if tickers else None,
                "ticker.gt": ticker_gt,
                "ticker.gte": ticker_gte,
                "ticker.lt": ticker_lt,
                "ticker.lte": ticker_lte,
                "ex_dividend_date": coerce_date(ex_dividend_date, "ex_dividend_date"),
                "ex_dividend_date.gt": coerce_date(ex_dividend_date_gt, "ex_dividend_date_gt"),
                "ex_dividend_date.gte": coerce_date(ex_dividend_date_gte, "ex_dividend_date_gte"),
                "ex_dividend_date.lt": coerce_date(ex_dividend_date_lt, "ex_dividend_date_lt"),
                "ex_dividend_date.lte": coerce_date(ex_dividend_date_lte, "ex_dividend_date_lte"),
                "frequency": coerce_choice(frequency, DividendFrequency, "frequency"),
                "frequency.gt": frequency_gt,
                "frequency.gte": frequency_gte,
                "frequency.lt": frequency_lt,
                "frequency.lte": frequency_lte,
                "distribution_type.any_of": coerce_choices(
                    distribution_types,
                    DistributionType,
                    "distribution_types",
                ),
                # This endpoint has no `order` param: direction is a `.asc`/`.desc` suffix on `sort`.
                "sort": coerce_sort(sort, order, DividendSortField),
                "limit": resolve_page_size(max_results, DIVIDENDS_MAX_PAGE_SIZE),
            },
        )
        return await self._get_all_pages(DIVIDENDS_ENDPOINT, params, max_results=max_results)

    async def get_dividends(  # noqa: PLR0913
        self,
        *,
        ticker: str | None = None,
        tickers: list[str] | None = None,
        ticker_gt: str | None = None,
        ticker_gte: str | None = None,
        ticker_lt: str | None = None,
        ticker_lte: str | None = None,
        ex_dividend_date: str | date | datetime | None = None,
        ex_dividend_date_gt: str | date | datetime | None = None,
        ex_dividend_date_gte: str | date | datetime | None = None,
        ex_dividend_date_lt: str | date | datetime | None = None,
        ex_dividend_date_lte: str | date | datetime | None = None,
        frequency: DividendFrequency | None = None,
        frequency_gt: int | None = None,
        frequency_gte: int | None = None,
        frequency_lt: int | None = None,
        frequency_lte: int | None = None,
        distribution_types: list[DistributionType] | None = None,
        max_results: int | None = None,
        sort: DividendSortField = "ticker",
        order: Order = "asc",
        on_validation_error: Literal["raise", "skip"] | None = None,
    ) -> list[Dividend]:
        """
        Get cash dividends (across pages, up to `max_results`), validated into `Dividend` models.

        Docs: https://massive.com/docs/rest/stocks/corporate-actions/dividends

        Args:
            ticker: Exact ticker symbol to match.
            tickers: Match any of the given ticker symbols (the API's `ticker.any_of`).
            ticker_gt: Return tickers greater than this symbol (range scan).
            ticker_gte: Return tickers greater than or equal to this symbol.
            ticker_lt: Return tickers less than this symbol.
            ticker_lte: Return tickers less than or equal to this symbol.
            ex_dividend_date: Exact ex-dividend date (ISO string or date/datetime).
            ex_dividend_date_gt: Ex-dividend date strictly after this date.
            ex_dividend_date_gte: Ex-dividend date on or after this date.
            ex_dividend_date_lt: Ex-dividend date strictly before this date.
            ex_dividend_date_lte: Ex-dividend date on or before this date.
            frequency: Exact payout cadence. One of the `DividendFrequency` values
                (0 = non-recurring, 1 = annual, 4 = quarterly, 12 = monthly, ...).
            frequency_gt: Payouts per year strictly greater than this value.
            frequency_gte: Payouts per year greater than or equal to this value.
            frequency_lt: Payouts per year strictly less than this value.
            frequency_lte: Payouts per year less than or equal to this value.
            distribution_types: Filter by any of the given distribution types. A list of
                `DistributionType` values ("recurring", "special", "supplemental",
                "irregular", "unknown"); pass a single-element list to match one type.
            max_results: Maximum total records to return (None = no cap).
            sort: Field to sort by. One of the `DividendSortField` values (e.g. "ex_dividend_date").
            order: Sort direction for `sort`, "asc" or "desc" (an `Order` value). Requires
                `sort` to be set, defaults to "asc".
            on_validation_error: Override the config default ("raise" or "skip") for this call.

        Returns:
            A list of `Dividend` models (at most `max_results`).

        Raises:
            ValueError: If `distribution_types`, `frequency`, `order`, `sort`, an
                `ex_dividend_date*` filter, or `max_results` is invalid, or if `order`
                is given without `sort`.

        """
        records = await self.get_dividends_raw(
            ticker=ticker,
            tickers=tickers,
            ticker_gt=ticker_gt,
            ticker_gte=ticker_gte,
            ticker_lt=ticker_lt,
            ticker_lte=ticker_lte,
            ex_dividend_date=ex_dividend_date,
            ex_dividend_date_gt=ex_dividend_date_gt,
            ex_dividend_date_gte=ex_dividend_date_gte,
            ex_dividend_date_lt=ex_dividend_date_lt,
            ex_dividend_date_lte=ex_dividend_date_lte,
            frequency=frequency,
            frequency_gt=frequency_gt,
            frequency_gte=frequency_gte,
            frequency_lt=frequency_lt,
            frequency_lte=frequency_lte,
            distribution_types=distribution_types,
            order=order,
            max_results=max_results,
            sort=sort,
        )
        mode = self._resolve_validation_mode(on_validation_error)
        return self._validate_records(records, Dividend, mode)
