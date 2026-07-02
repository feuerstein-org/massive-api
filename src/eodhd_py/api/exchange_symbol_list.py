"""Exchange Symbol List API endpoint."""

from typing import Literal, overload

import pandas as pd

from eodhd_py.base import BaseEodhdApi


class ExchangeSymbolListApi(BaseEodhdApi):
    """ExchangeSymbolListApi endpoint class."""

    @overload
    async def get_exchange_symbols(
        self,
        exchange_code: str,
        delisted: bool = False,
        type: Literal["common_stock", "preferred_stock", "stock", "etf", "fund"] | None = None,
        df_output: Literal[True] = ...,
    ) -> pd.DataFrame: ...

    @overload
    async def get_exchange_symbols(
        self,
        exchange_code: str,
        delisted: bool = False,
        type: Literal["common_stock", "preferred_stock", "stock", "etf", "fund"] | None = None,
        df_output: Literal[False] = ...,
    ) -> list[dict[str, str]]: ...

    async def get_exchange_symbols(
        self,
        exchange_code: str,
        delisted: bool = False,
        type: Literal["common_stock", "preferred_stock", "stock", "etf", "fund"] | None = None,  # noqa: A002
        df_output: bool = True,
    ) -> list[dict[str, str]] | pd.DataFrame:
        """
        Get all tickers listed on a specific exchange.

        Args:
            exchange_code: Exchange code (e.g., "US", "LSE", "XETRA").
                          For US stocks, use 'US' for unified access to NYSE, NASDAQ, NYSE ARCA, and OTC markets.
                          Or use separate codes: 'NYSE', 'NASDAQ', 'BATS', 'OTCQB', 'PINK', etc.
            delisted: If True, returns delisted (inactive) tickers only. Default is False.
            type: Filter tickers by type. Supported values: "common_stock", "preferred_stock",
                  "stock", "etf", "fund". Default is None (all types).
            df_output: If True (default), return pandas DataFrame. If False, return list of dicts.

        Returns:
            List of tickers with the following fields:
            - Code: Ticker symbol
            - Name: Full company or instrument name
            - Country: Country of listing
            - Exchange: Exchange code
            - Currency: Trading currency
            - Type: Type of asset (e.g., "Common Stock", "ETF", "Fund")
            - Isin: International Securities Identification Number (if available)

        """
        params: dict[str, str] = {}

        if delisted:
            params["delisted"] = "1"
        if type is not None:
            params["type"] = type

        return await self._make_request(f"exchange-symbol-list/{exchange_code}", params=params, df_output=df_output)
