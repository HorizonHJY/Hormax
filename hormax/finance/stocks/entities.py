"""Core domain entities for stock data management.

This module defines the fundamental data structures used throughout
the stock pack building process.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class Ticker:
    """Represents a stock ticker symbol.

    Attributes:
        symbol: The ticker symbol (e.g., 'AAPL', 'MSFT').
        market: Optional market identifier (e.g., 'NASDAQ', 'NYSE').
    """

    symbol: str
    market: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate ticker symbol."""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Ticker symbol cannot be empty")
        if len(self.symbol) > 10:
            raise ValueError("Ticker symbol cannot exceed 10 characters")


@dataclass(frozen=True)
class DateRange:
    """Represents a date range for data retrieval.

    Attributes:
        start: Start date (inclusive).
        end: End date (inclusive).
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        """Validate date range."""
        if self.start > self.end:
            raise ValueError(f"Start date {self.start} must be <= end date {self.end}")
        if self.end > date.today():
            raise ValueError(f"End date {self.end} cannot be in the future")

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}


@dataclass
class StockData:
    """Raw stock price data for a single ticker.

    Attributes:
        ticker: The ticker symbol.
        data: DataFrame with OHLCV data (Date index, columns: Open, High, Low, Close, Volume).
        retrieved_at: Timestamp when data was retrieved.
        source: Data source identifier (e.g., 'yfinance').
    """

    ticker: Ticker
    data: pd.DataFrame
    retrieved_at: datetime
    source: str = "yfinance"

    def __post_init__(self) -> None:
        """Validate stock data."""
        if self.data.empty:
            raise ValueError(f"StockData for {self.ticker.symbol} cannot be empty")

        required_columns = {"Open", "High", "Low", "Close", "Volume"}
        if not required_columns.issubset(self.data.columns):
            missing = required_columns - set(self.data.columns)
            raise ValueError(f"Missing required columns: {missing}")


@dataclass
class Returns:
    """Calculated returns for a stock.

    Attributes:
        ticker: The ticker symbol.
        daily_returns: Series of daily returns.
        cumulative_returns: Series of cumulative returns.
        total_return: Total return over the period.
        annualized_return: Annualized return.
        volatility: Annualized volatility (standard deviation).
    """

    ticker: Ticker
    daily_returns: pd.Series
    cumulative_returns: pd.Series
    total_return: float
    annualized_return: float
    volatility: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "ticker": self.ticker.symbol,
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
        }


@dataclass
class StockPack:
    """Complete stock data pack ready for export.

    Attributes:
        tickers: List of tickers included in the pack.
        date_range: Date range for the data.
        stock_data: Dictionary mapping ticker symbols to StockData.
        returns: Dictionary mapping ticker symbols to Returns.
        metadata: Additional metadata about the pack.
        created_at: Timestamp when pack was created.
    """

    tickers: List[Ticker]
    date_range: DateRange
    stock_data: Dict[str, StockData]
    returns: Dict[str, Returns]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate stock pack."""
        ticker_symbols = {t.symbol for t in self.tickers}

        if not ticker_symbols:
            raise ValueError("StockPack must contain at least one ticker")

        if set(self.stock_data.keys()) != ticker_symbols:
            raise ValueError("stock_data keys must match ticker symbols")

        if set(self.returns.keys()) != ticker_symbols:
            raise ValueError("returns keys must match ticker symbols")

    def get_ticker_count(self) -> int:
        """Get the number of tickers in the pack."""
        return len(self.tickers)

    def get_date_range_days(self) -> int:
        """Get the number of days in the date range."""
        return (self.date_range.end - self.date_range.start).days + 1
