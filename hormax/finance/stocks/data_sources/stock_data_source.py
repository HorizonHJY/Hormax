"""Stock data source implementation using yfinance.

This module provides the interface for fetching stock price data
from external data providers.
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
import yfinance as yf

from hormax.core.logging_setup import get_logger
from hormax.exceptions import StockDataError
from hormax.finance.stocks.entities import DateRange, StockData, Ticker

logger = get_logger(__name__)


class StockDataSource:
    """Data source for fetching stock price data using yfinance.

    Attributes:
        timeout: Request timeout in seconds.
    """

    def __init__(self, timeout: int = 30) -> None:
        """Initialize the stock data source.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout

    def fetch_price_history(
        self, ticker: Ticker, start_date: date, end_date: date
    ) -> StockData:
        """Fetch historical price data for a ticker.

        Args:
            ticker: The ticker to fetch data for.
            start_date: Start date (inclusive).
            end_date: End date (inclusive).

        Returns:
            StockData containing OHLCV data.

        Raises:
            StockDataError: If data cannot be fetched or is invalid.
        """
        try:
            logger.info(
                f"Fetching price history for {ticker.symbol} "
                f"from {start_date} to {end_date}"
            )

            # Download data using yfinance
            df = yf.download(
                ticker.symbol,
                start=start_date,
                end=end_date,
                progress=False,
                timeout=self.timeout,
            )

            if df.empty:
                raise StockDataError(
                    f"No data returned for {ticker.symbol} "
                    f"between {start_date} and {end_date}. "
                    "The ticker may be invalid or delisted."
                )

            # Ensure required columns exist
            required_columns = ["Open", "High", "Low", "Close", "Volume"]
            missing_columns = set(required_columns) - set(df.columns)

            if missing_columns:
                raise StockDataError(
                    f"Missing required columns for {ticker.symbol}: {missing_columns}"
                )

            # Select only required columns
            df = df[required_columns]

            # Create StockData object
            stock_data = StockData(
                ticker=ticker,
                data=df,
                retrieved_at=datetime.now(),
                source="yfinance",
            )

            logger.info(
                f"Successfully fetched {len(df)} days of data for {ticker.symbol}"
            )

            return stock_data

        except StockDataError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker.symbol}: {e}")
            raise StockDataError(
                f"Failed to fetch data for {ticker.symbol}: {e}"
            ) from e

    def validate_ticker(self, ticker: Ticker) -> bool:
        """Validate that a ticker exists and has available data.

        Args:
            ticker: The ticker to validate.

        Returns:
            True if the ticker is valid and has data available.
        """
        try:
            ticker_obj = yf.Ticker(ticker.symbol)
            info = ticker_obj.info

            # Check if we got valid info back
            if not info or "symbol" not in info:
                logger.warning(f"Ticker {ticker.symbol} may be invalid")
                return False

            return True

        except Exception as e:
            logger.warning(f"Failed to validate ticker {ticker.symbol}: {e}")
            return False
