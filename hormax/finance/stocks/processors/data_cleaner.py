"""Data cleaning and preprocessing for stock data.

This module provides functionality for cleaning stock price data,
handling missing values, and ensuring data quality.
"""

import pandas as pd

from hormax.core.logging_setup import get_logger
from hormax.exceptions import StockDataError
from hormax.finance.stocks.entities import StockData

logger = get_logger(__name__)


class DataCleaner:
    """Data cleaner for stock price data."""

    @staticmethod
    def clean_stock_data(stock_data: StockData, max_gap_days: int = 10) -> StockData:
        """Clean stock data by handling missing values and outliers.

        Args:
            stock_data: Raw stock data to clean.
            max_gap_days: Maximum allowed gap in trading days (default 10).

        Returns:
            Cleaned StockData with filled gaps and validated values.

        Raises:
            StockDataError: If data quality is too poor to clean.
        """
        ticker = stock_data.ticker
        df = stock_data.data.copy()

        logger.info(f"Cleaning data for {ticker.symbol}, initial rows: {len(df)}")

        # Check for completely empty data
        if df.empty:
            raise StockDataError(f"Cannot clean empty data for {ticker.symbol}")

        # Remove rows where all OHLC values are NaN
        df = df.dropna(subset=["Open", "High", "Low", "Close"], how="all")

        if df.empty:
            raise StockDataError(
                f"No valid data remaining for {ticker.symbol} after removing empty rows"
            )

        # Forward fill missing values (common for non-trading days)
        original_missing = df.isna().sum()
        df = df.fillna(method="ffill")

        # If there are still NaN values at the beginning, backfill
        df = df.fillna(method="bfill")

        filled_count = (original_missing - df.isna().sum()).sum()
        if filled_count > 0:
            logger.info(f"Filled {filled_count} missing values for {ticker.symbol}")

        # Check for remaining NaN values
        remaining_na = df.isna().sum().sum()
        if remaining_na > 0:
            logger.warning(
                f"Still have {remaining_na} NaN values for {ticker.symbol} after cleaning"
            )

        # Validate price relationships (High >= Low, Close between High and Low)
        invalid_rows = (
            (df["High"] < df["Low"])
            | (df["Close"] > df["High"])
            | (df["Close"] < df["Low"])
        )

        if invalid_rows.any():
            invalid_count = invalid_rows.sum()
            logger.warning(
                f"Found {invalid_count} rows with invalid price relationships "
                f"for {ticker.symbol}, fixing..."
            )

            # Fix by adjusting High/Low to accommodate Close
            df.loc[invalid_rows, "High"] = df.loc[invalid_rows, ["High", "Close"]].max(axis=1)
            df.loc[invalid_rows, "Low"] = df.loc[invalid_rows, ["Low", "Close"]].min(axis=1)

        # Check for negative prices (data error)
        negative_prices = (
            (df["Open"] < 0) | (df["High"] < 0) | (df["Low"] < 0) | (df["Close"] < 0)
        )

        if negative_prices.any():
            raise StockDataError(
                f"Found negative prices for {ticker.symbol} - data quality issue"
            )

        # Check for zero volume (possible data issue)
        zero_volume_count = (df["Volume"] == 0).sum()
        if zero_volume_count > 0:
            logger.warning(
                f"Found {zero_volume_count} days with zero volume for {ticker.symbol}"
            )

        # Check for large gaps in the date index
        if isinstance(df.index, pd.DatetimeIndex):
            date_diffs = df.index.to_series().diff()
            large_gaps = date_diffs > pd.Timedelta(days=max_gap_days)

            if large_gaps.any():
                gap_count = large_gaps.sum()
                logger.warning(
                    f"Found {gap_count} gaps > {max_gap_days} days for {ticker.symbol}"
                )

        logger.info(f"Cleaning complete for {ticker.symbol}, final rows: {len(df)}")

        return StockData(
            ticker=ticker,
            data=df,
            retrieved_at=stock_data.retrieved_at,
            source=stock_data.source,
        )

    @staticmethod
    def detect_outliers(stock_data: StockData, std_threshold: float = 5.0) -> pd.Series:
        """Detect outlier returns using standard deviation threshold.

        Args:
            stock_data: Stock data to analyze.
            std_threshold: Number of standard deviations for outlier threshold.

        Returns:
            Boolean Series indicating outlier days.
        """
        df = stock_data.data

        # Calculate daily returns
        returns = df["Close"].pct_change()

        # Calculate mean and std
        mean = returns.mean()
        std = returns.std()

        # Identify outliers
        outliers = (returns - mean).abs() > (std_threshold * std)

        outlier_count = outliers.sum()
        if outlier_count > 0:
            logger.info(
                f"Detected {outlier_count} outlier days for {stock_data.ticker.symbol} "
                f"(threshold={std_threshold} std)"
            )

        return outliers
