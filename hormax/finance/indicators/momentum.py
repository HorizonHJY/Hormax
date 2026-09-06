"""Momentum indicators: MACD and RSI."""

from __future__ import annotations

import pandas as pd

from hormax.exceptions import StockDataError


def _validate(close: pd.Series, needed: int, name: str) -> None:
    if close.empty:
        raise StockDataError(f"{name}: empty price series")
    if len(close) < needed:
        raise StockDataError(
            f"{name}: needs at least {needed} observations for a meaningful "
            f"result, got {len(close)}"
        )


def macd(
    close: pd.Series,
    *,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    histogram_multiplier: float = 1.0,
) -> pd.DataFrame:
    """MACD — moving average convergence/divergence.

    Args:
        close: Closing prices indexed by date.
        fast: Fast EMA span.
        slow: Slow EMA span.
        signal: Span of the EMA applied to the MACD line (the signal/DEA line).
        histogram_multiplier: Scales the histogram. Charting platforms disagree
            here: TradingView and most US tooling plot ``dif - dea`` (1.0),
            while Chinese platforms such as 同花顺 and 通达信 plot twice that.
            The shape is identical, the scale is not, so pick the one matching
            whatever chart you compare against. Default follows TradingView.

    Returns:
        DataFrame with ``dif``, ``dea`` and ``histogram`` columns. The first
        ``slow + signal`` rows are influenced by EMA initialisation and should
        be treated as warm-up.
    """
    if not 0 < fast < slow:
        raise ValueError(f"fast ({fast}) must be positive and below slow ({slow})")
    if signal <= 0:
        raise ValueError(f"signal must be positive, got {signal}")

    _validate(close, slow + signal, "macd")

    dif = close.ewm(span=fast, adjust=False).mean() - close.ewm(
        span=slow, adjust=False
    ).mean()
    dea = dif.ewm(span=signal, adjust=False).mean()

    return pd.DataFrame(
        {
            "dif": dif,
            "dea": dea,
            "histogram": (dif - dea) * histogram_multiplier,
        }
    )


def rsi(
    close: pd.Series,
    *,
    period: int = 14,
    smoothing: str = "wilder",
) -> pd.DataFrame:
    """RSI — relative strength index.

    Args:
        close: Closing prices indexed by date.
        period: Look-back length.
        smoothing: ``"wilder"`` reproduces Wilder's original recursive average
            (equivalent to an EMA with ``alpha = 1/period``), which is what
            almost every charting platform draws. ``"sma"`` uses a plain rolling
            mean instead; it reacts faster and will not match those platforms.

    Returns:
        DataFrame with an ``rsi`` column in the 0-100 range. Wilder smoothing
        converges slowly, so allow several multiples of ``period`` as warm-up.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if smoothing not in ("wilder", "sma"):
        raise ValueError(f"unknown smoothing {smoothing!r}; use 'wilder' or 'sma'")

    _validate(close, period + 1, "rsi")

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    if smoothing == "wilder":
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    else:
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

    # A zero average loss means an unbroken run of up days: RSI is 100 by
    # definition. Dividing would give inf, so handle it explicitly rather than
    # letting a sentinel leak into the output.
    rs = avg_gain / avg_loss
    result = 100 - (100 / (1 + rs))
    result = result.where(avg_loss != 0, 100.0)
    result = result.where(avg_gain != 0, result.where(avg_loss == 0, 0.0))

    return pd.DataFrame({"rsi": result})
