"""Dividends API endpoint."""

from datetime import datetime
from typing import Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi
from eodhd_py.utils import validate_normalize_symbol


class DividendsApi(BaseEodhdApi):
    """DividendsApi endpoint class."""

    @overload
    async def get_dividends(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_dividends(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, str | float]]: ...

    async def get_dividends(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: bool = True,
    ) -> list[dict[str, str | float]] | pd.DataFrame:
        """
        Get dividend data for a supplied symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL.US")
            from_date: Start date for data
            to_date: End date for data
            df_output: If True (default), return pandas DataFrame. If False, return list of dicts.

        Returns:
            Dividend data containing:
            - date: Ex-dividend date
            - declarationDate: Declaration date
            - recordDate: Record date
            - paymentDate: Payment date
            - period: Dividend period (e.g., "Quarterly")
            - value: Adjusted dividend value
            - unadjustedValue: Unadjusted dividend value
            - currency: Dividend currency (e.g., "USD")

        """
        params: dict[str, str] = {}

        symbol = validate_normalize_symbol(symbol)

        if from_date is not None:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            params["to"] = to_date.strftime("%Y-%m-%d")

        return await self._make_request(f"div/{symbol}", params=params, df_output=df_output)
