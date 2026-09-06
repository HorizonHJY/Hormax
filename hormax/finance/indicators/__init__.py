"""Technical indicators.

Every function here is *parameterised*: the caller decides the conventions,
this package only supplies the arithmetic and a documented default. Where a
convention genuinely differs between markets or platforms — the MACD histogram
multiplier is the classic example — the difference is a parameter, never a
hardcoded choice, because a package that silently picks one is a package whose
numbers cannot be reconciled with anyone else's chart.

All functions take a price ``Series`` (or OHLCV ``DataFrame``) indexed by date
and return a ``DataFrame`` aligned to that index, with ``NaN`` in the warm-up
region rather than a fabricated value. Deciding what to *show* during warm-up
is the caller's job.
"""

from hormax.finance.indicators.momentum import macd, rsi
from hormax.finance.indicators.trend import moving_averages
from hormax.finance.indicators.volatility import bollinger_bands
from hormax.finance.indicators.volume import volume_profile

__all__ = [
    "macd",
    "rsi",
    "moving_averages",
    "bollinger_bands",
    "volume_profile",
]
