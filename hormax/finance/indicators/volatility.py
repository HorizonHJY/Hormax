"""Volatility indicators: Bollinger bands."""

from __future__ import annotations

import pandas as pd

from hormax.exceptions import StockDataError


def bollinger_bands(
    close: pd.Series,
    *,
    period: int = 20,
    num_std: float = 2.0,
    ddof: int = 0,
) -> pd.DataFrame:
    """Bollinger bands around a simple moving average.

    Args:
        close: Closing prices indexed by date.
        period: Window for both the middle band and the standard deviation.
        num_std: How many standard deviations the outer bands sit from the mean.
        ddof: Delta degrees of freedom for the standard deviation. ``0`` is the
            population form used by TradingView and most charting platforms;
            pandas defaults to ``1`` (sample), which produces visibly wider
            bands on short windows. Left as a parameter because the "right"
            answer depends on which chart you are reconciling against.

    Returns:
        DataFrame with ``middle``, ``upper``, ``lower`` and ``bandwidth``
        columns. ``bandwidth`` is ``(upper - lower) / middle`` — a scale-free
        measure of how wide the bands currently are.
    """
    if period <= 1:
        raise ValueError(f"period must be greater than 1, got {period}")
    if num_std <= 0:
        raise ValueError(f"num_std must be positive, got {num_std}")

    if close.empty:
        raise StockDataError("bollinger_bands: empty price series")
    if len(close) < period:
        raise StockDataError(
            f"bollinger_bands: needs at least {period} observations, got {len(close)}"
        )

    middle = close.rolling(window=period).mean()
    deviation = close.rolling(window=period).std(ddof=ddof)

    upper = middle + num_std * deviation
    lower = middle - num_std * deviation

    return pd.DataFrame(
        {
            "middle": middle,
            "upper": upper,
            "lower": lower,
            "bandwidth": (upper - lower) / middle,
        }
    )
