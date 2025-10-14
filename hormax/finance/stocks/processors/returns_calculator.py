"""Returns calculation for stock data.

This module provides functionality for calculating various return metrics
from stock price data.
"""

import numpy as np
import pandas as pd

from hormax.core.logging_setup import get_logger
from hormax.exceptions import StockDataError
from hormax.finance.stocks.entities import Returns, StockData, Ticker

logger = get_logger(__name__)


class ReturnsCalculator:
    """Calculator for stock returns and related metrics."""

    @staticmethod
    def calculate_returns(stock_data: StockData) -> Returns:
        """Calculate returns from stock price data.

        Args:
            stock_data: StockData containing price history.

        Returns:
            Returns object with daily, cumulative, and summary metrics.

        Raises:
            StockDataError: If returns cannot be calculated.
        """
        try:
            ticker = stock_data.ticker
            df = stock_data.data

            if df.empty or "Close" not in df.columns:
                raise StockDataError(
                    f"Cannot calculate returns for {ticker.symbol}: "
                    "missing or empty Close price data"
                )

            logger.info(f"Calculating returns for {ticker.symbol}")

            # Calculate daily returns (percentage change)
            daily_returns = df["Close"].pct_change()
            daily_returns = daily_returns.fillna(0.0)  # First day has NaN

            # Calculate cumulative returns
            cumulative_returns = (1 + daily_returns).cumprod() - 1

            # Calculate total return
            total_return = cumulative_returns.iloc[-1] if len(cumulative_returns) > 0 else 0.0

            # Calculate annualized return
            num_days = len(df)
            trading_days_per_year = 252

            if num_days > 0:
                years = num_days / trading_days_per_year
                annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
            else:
                annualized_return = 0.0

            # Calculate annualized volatility (standard deviation)
            if len(daily_returns) > 1:
                volatility = daily_returns.std() * np.sqrt(trading_days_per_year)
            else:
                volatility = 0.0

            returns = Returns(
                ticker=ticker,
                daily_returns=daily_returns,
                cumulative_returns=cumulative_returns,
                total_return=float(total_return),
                annualized_return=float(annualized_return),
                volatility=float(volatility),
            )

            logger.info(
                f"Calculated returns for {ticker.symbol}: "
                f"total={total_return:.2%}, annualized={annualized_return:.2%}, "
                f"volatility={volatility:.2%}"
            )

            return returns

        except StockDataError:
            raise
        except Exception as e:
            logger.error(f"Failed to calculate returns for {stock_data.ticker.symbol}: {e}")
            raise StockDataError(
                f"Failed to calculate returns for {stock_data.ticker.symbol}: {e}"
            ) from e

    @staticmethod
    def calculate_sharpe_ratio(returns: Returns, risk_free_rate: float = 0.02) -> float:
        """Calculate the Sharpe ratio for the returns.

        Args:
            returns: Returns object.
            risk_free_rate: Annual risk-free rate (default 2%).

        Returns:
            Sharpe ratio (annualized return - risk_free_rate) / volatility.
        """
        if returns.volatility == 0:
            return 0.0

        sharpe = (returns.annualized_return - risk_free_rate) / returns.volatility
        return float(sharpe)

    @staticmethod
    def calculate_max_drawdown(returns: Returns) -> float:
        """Calculate the maximum drawdown from cumulative returns.

        Args:
            returns: Returns object.

        Returns:
            Maximum drawdown as a decimal (e.g., -0.25 for 25% drawdown).
        """
        cumulative = returns.cumulative_returns + 1.0  # Convert to wealth index

        # Calculate running maximum
        running_max = cumulative.expanding().max()

        # Calculate drawdown at each point
        drawdown = (cumulative - running_max) / running_max

        # Return maximum drawdown (most negative value)
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
        return float(max_drawdown)
