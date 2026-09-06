"""Trend indicators: simple and exponential moving averages."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from hormax.exceptions import StockDataError


def moving_averages(
    close: pd.Series,
    *,
    periods: Sequence[int] = (5, 20, 60),
    kind: str = "sma",
) -> pd.DataFrame:
    """A set of moving averages over the same price series.

    Args:
        close: Closing prices indexed by date.
        periods: Look-back lengths. One column per period.
        kind: ``"sma"`` for a simple rolling mean, ``"ema"`` for an
            exponentially weighted one. They cross at different points, so a
            strategy tuned on one will not behave the same on the other.

    Returns:
        DataFrame with a column per period, named ``ma{period}`` (or
        ``ema{period}``). Each column is NaN until its own window fills.
    """
    if not periods:
        raise ValueError("periods must not be empty")
    if any(p <= 0 for p in periods):
        raise ValueError(f"all periods must be positive, got {list(periods)}")
    if kind not in ("sma", "ema"):
        raise ValueError(f"unknown kind {kind!r}; use 'sma' or 'ema'")

    if close.empty:
        raise StockDataError("moving_averages: empty price series")

    prefix = "ma" if kind == "sma" else "ema"
    out = {}
    for period in periods:
        if kind == "sma":
            out[f"{prefix}{period}"] = close.rolling(window=period).mean()
        else:
            out[f"{prefix}{period}"] = close.ewm(span=period, adjust=False).mean()

    return pd.DataFrame(out)
