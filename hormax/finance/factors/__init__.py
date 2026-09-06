"""Factor data and factor-exposure analysis."""

from hormax.finance.factors.exposure import (
    ExposureError,
    ExposureResult,
    FactorLoading,
    factor_exposure,
    rolling_factor_exposure,
)
from hormax.finance.factors.ken_french import FactorData, FactorDataError, load_factors

__all__ = [
    "FactorData",
    "FactorDataError",
    "load_factors",
    "ExposureError",
    "ExposureResult",
    "FactorLoading",
    "factor_exposure",
    "rolling_factor_exposure",
]
