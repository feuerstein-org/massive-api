"""
Stock Splits API endpoint.

Official documentation: https://massive.com/docs/rest/stocks/corporate-actions/splits
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from massive_api.base import BaseMassiveApi
from massive_api.params import AdjustmentType, Order, SplitSortField
from massive_api.utils import (
    build_query_params,
    coerce_choice,
    coerce_choices,
    coerce_date,
    coerce_max_results,
    resolve_page_size,
)

SPLITS_ENDPOINT = "stocks/v1/splits"
SPLITS_MAX_PAGE_SIZE = 5000


class Split(BaseModel):
    """
    A single stock split record from the Splits endpoint.

    All fields are required and precisely typed to match the documented response:
    https://massive.com/docs/rest/stocks/corporate-actions/splits
    An invalid or missing field fails validation (see `on_validation_error`).
    """

    model_config = ConfigDict(extra="ignore")

    ticker: str
    # ISO "yyyy-mm-dd" in the payload; parsed into a real date.
    execution_date: date
    adjustment_type: AdjustmentType
    # Split ratio is `split_to`-for-`split_from` (e.g. 4-for-1 -> from=1, to=4).
    split_from: float
    split_to: float
    # Decimal factor used to adjust historical prices for this split (e.g. 0.017857).
    historical_adjustment_factor: float | None
    id: str | None


class SplitsApi(BaseMassiveApi):
    """Splits endpoint: historical stock split events with adjustment factors."""

    async def get_splits_raw(
        self,
        *,
        ticker: str | None = None,
        execution_date: str | date | datetime | None = None,
        execution_date_gt: str | date | datetime | None = None,
        execution_date_gte: str | date | datetime | None = None,
        execution_date_lt: str | date | datetime | None = None,
        execution_date_lte: str | date | datetime | None = None,
        adjustment_types: list[AdjustmentType] | None = None,
        order: Order | None = None,
        max_results: int | None = None,
        sort: SplitSortField | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch splits across pages as raw JSON dicts (no validation).

        Docs: https://massive.com/docs/rest/stocks/corporate-actions/splits

        See `get_splits` for the meaning of each parameter.
        """
        max_results = coerce_max_results(max_results)
        params = build_query_params(
            {
                "ticker": ticker,
                "execution_date": coerce_date(execution_date, "execution_date"),
                "execution_date.gt": coerce_date(execution_date_gt, "execution_date_gt"),
                "execution_date.gte": coerce_date(execution_date_gte, "execution_date_gte"),
                "execution_date.lt": coerce_date(execution_date_lt, "execution_date_lt"),
                "execution_date.lte": coerce_date(execution_date_lte, "execution_date_lte"),
                "adjustment_type.any_of": coerce_choices(
                    adjustment_types,
                    AdjustmentType,
                    "adjustment_types",
                ),
                # This endpoint has no `order` param: direction is a `.asc`/`.desc` suffix on `sort`.
                "sort": self._build_sort(sort, order),
                "limit": resolve_page_size(max_results, SPLITS_MAX_PAGE_SIZE),
            },
        )
        return await self._get_all_pages(SPLITS_ENDPOINT, params, max_results=max_results)

    @staticmethod
    def _build_sort(sort: SplitSortField | None, order: Order | None) -> str | None:
        """
        Combine `sort` field and `order` direction into the API's `sort=field.direction`.

        Both are validated. Returns None when no sort field is given (the API then applies
        its own default, `execution_date.desc`); `order` defaults to "asc" when a field is set.
        """
        sort_field = coerce_choice(sort, SplitSortField, "sort")
        direction = coerce_choice(order, Order, "order")
        if sort_field is None:
            return None
        return f"{sort_field}.{direction or 'asc'}"

    async def get_splits(
        self,
        *,
        ticker: str | None = None,
        execution_date: str | date | datetime | None = None,
        execution_date_gt: str | date | datetime | None = None,
        execution_date_gte: str | date | datetime | None = None,
        execution_date_lt: str | date | datetime | None = None,
        execution_date_lte: str | date | datetime | None = None,
        adjustment_types: list[AdjustmentType] | None = None,
        order: Order | None = None,
        max_results: int | None = None,
        sort: SplitSortField | None = None,
        on_validation_error: Literal["raise", "skip"] | None = None,
    ) -> list[Split]:
        """
        Get stock splits (across pages, up to `max_results`), validated into `Split` models.

        Docs: https://massive.com/docs/rest/stocks/corporate-actions/splits

        Args:
            ticker: Exact ticker symbol to match.
            execution_date: Exact split execution date (ISO string or date/datetime).
            execution_date_gt: Splits executed strictly after this date (ISO string or date/datetime).
            execution_date_gte: Splits executed on or after this date (ISO string or date/datetime).
            execution_date_lt: Splits executed strictly before this date (ISO string or date/datetime).
            execution_date_lte: Splits executed on or before this date (ISO string or date/datetime).
            adjustment_types: Filter by any of the given adjustment types. A list of
                `AdjustmentType` values ("forward_split", "reverse_split", "stock_dividend");
                pass a single-element list to match one type, e.g. ["forward_split"].
            order: Sort direction for `sort`, "asc" or "desc" (an `Order` value). Applies only
                when `sort` is set, and defaults to "asc". The endpoint has no standalone order
                param; this is folded into `sort` as a "field.direction" suffix.
            max_results: Maximum total records to return (None = no cap).
            sort: Field to sort by. One of the `SplitSortField` values (e.g. "execution_date").
            on_validation_error: Override the config default ("raise" or "skip") for this call.

        Returns:
            A list of `Split` models (at most `max_results`).

        Raises:
            ValueError: If `adjustment_types`, `order`, `sort`, an `execution_date*` filter,
                or `max_results` is invalid.

        """
        records = await self.get_splits_raw(
            ticker=ticker,
            execution_date=execution_date,
            execution_date_gt=execution_date_gt,
            execution_date_gte=execution_date_gte,
            execution_date_lt=execution_date_lt,
            execution_date_lte=execution_date_lte,
            adjustment_types=adjustment_types,
            order=order,
            max_results=max_results,
            sort=sort,
        )
        mode = self._resolve_validation_mode(on_validation_error)
        return self._validate_records(records, Split, mode)
