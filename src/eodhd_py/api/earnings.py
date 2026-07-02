"""Earnings API endpoint."""

from datetime import datetime
from typing import Any, Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi
from eodhd_py.utils import validate_normalize_symbol


class EarningsApi(BaseEodhdApi):
    """EarningsApi endpoint class for historical and upcoming earnings data."""

    @overload
    async def get_earnings(
        self,
        symbols: list[str] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_earnings(
        self,
        symbols: list[str] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, Any]]: ...

    async def get_earnings(
        self,
        symbols: list[str] | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: bool = True,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """
        Get historical and upcoming earnings data.

        Can be queried by symbols, date window, or both. Without dates, default window is "today + 7 days".

        Args:
            symbols: List of stock symbols (e.g., ["AAPL.US", "MSFT.US"]).
            from_date: Start date for data (default: today).
            to_date: End date for data (default: today + 7 days).
            df_output: If True (default), return pandas DataFrame. If False, return list of dicts.

        Returns:
            Earnings data containing:
            - code: Ticker in EODHD format
            - report_date: Date when the company reported/announced results
            - date: Fiscal period end date the result refers to
            - before_after_market: Report timing (e.g., "BeforeMarket", "AfterMarket") or null
            - currency: Reporting currency for EPS
            - actual: Reported EPS
            - estimate: Consensus EPS estimate (or null)
            - difference: actual - estimate (or null)
            - percent: Surprise in percent (or null)

        """
        params: dict[str, str] = {}

        if symbols is not None:
            # Validate and normalize each symbol
            normalized_symbols = [validate_normalize_symbol(s) for s in symbols]
            params["symbols"] = ",".join(normalized_symbols)

        if from_date is not None:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            params["to"] = to_date.strftime("%Y-%m-%d")

        response: dict[str, Any] = await self._make_request("calendar/earnings", params=params, df_output=False)

        # The API returns a wrapper object with an "earnings" array
        earnings_data: list[dict[str, Any]] = response.get("earnings", [])

        if df_output:
            return pd.DataFrame(earnings_data)
        return earnings_data
