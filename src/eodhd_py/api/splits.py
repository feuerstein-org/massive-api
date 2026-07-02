"""Splits API endpoint."""

from datetime import datetime
from typing import Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi
from eodhd_py.utils import validate_normalize_symbol


class SplitsApi(BaseEodhdApi):
    """SplitsApi endpoint class."""

    @overload
    async def get_splits(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_splits(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, str]]: ...

    async def get_splits(
        self,
        symbol: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        df_output: bool = True,
    ) -> list[dict[str, str]] | pd.DataFrame:
        """
        Get stock split data for a supplied symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL.US")
            from_date: Start date for data
            to_date: End date for data
            df_output: If True (default), return pandas DataFrame. If False, return list of dicts.

        Returns:
            Split data containing:
            - date: Date of the split (YYYY-MM-DD)
            - split: Split ratio (e.g., "2.000000/1.000000" for a 2-for-1 split)

        """
        params: dict[str, str] = {}

        symbol = validate_normalize_symbol(symbol)

        if from_date is not None:
            params["from"] = from_date.strftime("%Y-%m-%d")
        if to_date is not None:
            params["to"] = to_date.strftime("%Y-%m-%d")

        return await self._make_request(f"splits/{symbol}", params=params, df_output=df_output)
