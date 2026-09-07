"""Exponentially weighted volatility and covariance (RiskMetrics style).

An equally weighted sample variance treats a crash from two years ago exactly
like yesterday's move. EWMA does not: weights decay geometrically, so the
estimate reacts to the current regime while still remembering enough history to
be stable.

    sigma_t^2 = lambda * sigma_{t-1}^2 + (1 - lambda) * r_{t-1}^2

``lambda`` is the only knob and it is genuinely a choice, not a fact: smaller
reacts faster and is noisier, larger is smoother and slower to notice a regime
change. J.P. Morgan's RiskMetrics settled on 0.94 for daily data and 0.97 for
monthly, which is why those numbers are everywhere — they are a convention, not
a derivation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_LAMBDA = 0.94


class RiskInputError(ValueError):
    """Inputs are unusable for a risk estimate."""


def effective_window(lam: float, *, residual: float = 0.001) -> int:
    """How many observations carry all but ``residual`` of the total weight.

    EWMA weights decay but never reach zero, so in practice you truncate. This
    reports where truncation stops mattering: with lambda=0.94 and a 0.1%
    residual that is about 112 observations.
    """
    _validate_lambda(lam)
    return int(np.ceil(np.log(residual) / np.log(lam)))


def half_life(lam: float) -> float:
    """Observations until a weight halves. The intuitive read on ``lambda``."""
    _validate_lambda(lam)
    return float(np.log(0.5) / np.log(lam))


def _validate_lambda(lam: float) -> None:
    if not 0 < lam < 1:
        raise ValueError(f"lambda must be strictly between 0 and 1, got {lam}")


def _weights(n: int, lam: float) -> np.ndarray:
    """Normalised EWMA weights, newest observation last."""
    ages = np.arange(n - 1, -1, -1)          # oldest ... newest
    raw = (1 - lam) * lam**ages
    return raw / raw.sum()


def ewma_volatility(
    returns: pd.Series,
    *,
    lam: float = DEFAULT_LAMBDA,
    annualise: bool = False,
    periods_per_year: int = 252,
    min_observations: int = 30,
) -> float:
    """Current EWMA volatility (standard deviation) of a return series.

    Args:
        returns: Periodic returns. Log returns are the usual choice when the
            result feeds a simulation, since they aggregate additively.
        lam: Decay factor.
        annualise: Scale by ``sqrt(periods_per_year)``. Note this assumes
            returns are iid, which is exactly what volatility clustering says
            they are not — so an annualised daily vol is an approximation, not
            a forecast of a year's dispersion.
        periods_per_year: Used only when annualising.
        min_observations: Refuse below this; an EWMA on a handful of points is
            dominated by whatever happened most recently.
    """
    _validate_lambda(lam)
    series = returns.dropna()
    if len(series) < min_observations:
        raise RiskInputError(
            f"need at least {min_observations} observations, got {len(series)}"
        )

    window = min(len(series), effective_window(lam))
    recent = series.iloc[-window:].to_numpy(dtype=float)

    # Deviations from zero, not from the mean: over daily horizons the mean is
    # tiny relative to the noise, and estimating it adds error without adding
    # information. RiskMetrics makes the same choice.
    variance = float(np.dot(_weights(window, lam), recent**2))
    vol = float(np.sqrt(variance))
    return vol * np.sqrt(periods_per_year) if annualise else vol


def ewma_covariance(
    returns: pd.DataFrame,
    *,
    lam: float = DEFAULT_LAMBDA,
    min_observations: int = 30,
) -> pd.DataFrame:
    """Current EWMA covariance matrix across several return series.

    Portfolio risk is not the sum of its parts: two positions that fall together
    are far more dangerous than their individual volatilities suggest, and two
    that offset each other are far less. That information lives entirely in the
    off-diagonal terms, which is why a portfolio VaR needs this rather than a
    vector of standalone volatilities.

    Returns:
        Symmetric DataFrame indexed and columned by the input's columns.

    Raises:
        RiskInputError: If there are too few overlapping observations.
    """
    _validate_lambda(lam)
    frame = returns.dropna(how="any")
    if len(frame) < min_observations:
        raise RiskInputError(
            f"need at least {min_observations} overlapping observations, got {len(frame)}"
        )
    if frame.shape[1] == 0:
        raise RiskInputError("no columns to estimate covariance over")

    window = min(len(frame), effective_window(lam))
    recent = frame.iloc[-window:].to_numpy(dtype=float)
    weights = _weights(window, lam)

    weighted = recent * weights[:, None]
    cov = weighted.T @ recent

    cov = (cov + cov.T) / 2      # kill floating-point asymmetry
    return pd.DataFrame(cov, index=frame.columns, columns=frame.columns)


def nearest_positive_semidefinite(matrix: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Clip negative eigenvalues to zero.

    A covariance matrix must be positive semidefinite to be simulated from, but
    floating-point error (or a near-collinear pair of assets) can produce a tiny
    negative eigenvalue. Silently "fixing" that would hide a genuinely
    degenerate portfolio, so this reports whether it had to intervene.

    Returns:
        ``(matrix, was_adjusted)``.
    """
    values = matrix.to_numpy(dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(values)

    if (eigenvalues >= -1e-12).all():
        return matrix, False

    clipped = np.clip(eigenvalues, 0.0, None)
    repaired = eigenvectors @ np.diag(clipped) @ eigenvectors.T
    repaired = (repaired + repaired.T) / 2
    return pd.DataFrame(repaired, index=matrix.index, columns=matrix.columns), True
