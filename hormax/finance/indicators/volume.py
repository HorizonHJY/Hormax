"""Volume indicators."""

from __future__ import annotations

import pandas as pd

from hormax.exceptions import StockDataError


def volume_profile(
    volume: pd.Series,
    *,
    period: int = 20,
) -> pd.DataFrame:
    """Raw volume with a moving average and a relative-to-average ratio.

    Args:
        volume: Traded volume indexed by date.
        period: Window for the volume moving average.

    Returns:
        DataFrame with ``volume``, ``vma`` and ``relative`` columns.
        ``relative`` is ``volume / vma`` — above 1 means today traded heavier
        than the recent norm, which is usually the thing you actually want to
        know, since raw volume is not comparable across tickers.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if volume.empty:
        raise StockDataError("volume_profile: empty volume series")

    vma = volume.rolling(window=period).mean()
    return pd.DataFrame(
        {
            "volume": volume,
            "vma": vma,
            # Guard against a zero average (a fully halted stretch) rather than
            # emitting inf into a chart.
            "relative": (volume / vma).where(vma > 0),
        }
    )
