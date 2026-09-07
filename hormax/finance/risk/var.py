"""Value at Risk and Expected Shortfall.

Three estimators are provided on purpose. They rest on different assumptions,
so when they disagree the disagreement is the finding — a Monte Carlo VaR far
below the historical one usually means the simulated distribution is too thin
in the tail, not that the portfolio is safe.

Every VaR here is reported as a **positive loss magnitude**: "0.023" means a
2.3% loss, not a -2.3% return. Sign conventions are the most common source of
silently wrong risk numbers, so the direction is fixed once, here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from hormax.finance.risk.ewma import (
    DEFAULT_LAMBDA,
    RiskInputError,
    ewma_covariance,
    nearest_positive_semidefinite,
)

DEFAULT_SIMULATIONS = 50_000
DEFAULT_SEED = 20260906


@dataclass(frozen=True)
class VarResult:
    """VaR and ES at one confidence level, from one method."""

    method: str
    confidence: float
    horizon_days: int
    var: float                  # positive loss fraction
    expected_shortfall: float   # positive loss fraction, >= var
    distribution: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "confidence": self.confidence,
            "horizon_days": self.horizon_days,
            "var": self.var,
            "expected_shortfall": self.expected_shortfall,
            "distribution": self.distribution,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class BacktestResult:
    """How often reality exceeded the VaR estimate.

    A VaR nobody checked is decoration: it produces a number that looks like
    risk measurement without ever being wrong out loud.
    """

    confidence: float
    observations: int
    breaches: int
    expected_breaches: float
    breach_rate: float
    kupiec_statistic: float
    kupiec_p_value: float

    @property
    def calibrated(self) -> bool:
        """True when the breach count is consistent with the stated confidence."""
        return self.kupiec_p_value >= 0.05

    @property
    def verdict(self) -> str:
        if self.calibrated:
            return "校准合理"
        return "低估风险" if self.breach_rate > (1 - self.confidence) else "过于保守"

    def to_dict(self) -> dict:
        return {
            "confidence": self.confidence,
            "observations": self.observations,
            "breaches": self.breaches,
            "expected_breaches": self.expected_breaches,
            "breach_rate": self.breach_rate,
            "kupiec_statistic": self.kupiec_statistic,
            "kupiec_p_value": self.kupiec_p_value,
            "calibrated": self.calibrated,
            "verdict": self.verdict,
        }


def _check_confidence(confidence: float) -> None:
    if not 0.5 < confidence < 1:
        raise ValueError(f"confidence must be between 0.5 and 1, got {confidence}")


def _tail(losses: np.ndarray, confidence: float) -> tuple[float, float]:
    """VaR and ES from a sample of losses (positive = loss)."""
    var = float(np.quantile(losses, confidence))
    beyond = losses[losses >= var]
    es = float(beyond.mean()) if beyond.size else var
    return var, es


def historical_var(
    returns: pd.Series,
    *,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> VarResult:
    """Empirical quantile of realised returns.

    Assumes nothing about the shape of the distribution, which is its strength;
    it also cannot produce a loss larger than the worst one already observed,
    which is its weakness.
    """
    _check_confidence(confidence)
    series = returns.dropna()
    if len(series) < 30:
        raise RiskInputError(f"need at least 30 observations, got {len(series)}")

    losses = -series.to_numpy(dtype=float)
    var, es = _tail(losses, confidence)

    scale = np.sqrt(horizon_days)
    notes = []
    if horizon_days > 1:
        notes.append(
            f"{horizon_days} 日结果由 1 日按 √{horizon_days} 缩放，该缩放假设收益 iid，"
            "而波动率聚集会使其低估多日风险"
        )

    return VarResult(
        method="historical",
        confidence=confidence,
        horizon_days=horizon_days,
        var=var * scale,
        expected_shortfall=es * scale,
        notes=notes,
    )


def parametric_var(
    volatility: float,
    *,
    confidence: float = 0.95,
    horizon_days: int = 1,
    mean: float = 0.0,
) -> VarResult:
    """Closed-form normal VaR. Fast, and wrong in the tail by construction.

    Included as a reference point: the gap between this and a fat-tailed
    estimate is a direct read on how much the normal assumption is costing.
    """
    _check_confidence(confidence)
    if volatility < 0:
        raise ValueError("volatility cannot be negative")

    z = stats.norm.ppf(confidence)
    scale = np.sqrt(horizon_days)
    var = (z * volatility - mean) * scale
    # ES of a normal: sigma * phi(z) / (1 - confidence)
    es = (stats.norm.pdf(z) / (1 - confidence) * volatility - mean) * scale

    return VarResult(
        method="parametric",
        confidence=confidence,
        horizon_days=horizon_days,
        var=float(var),
        expected_shortfall=float(es),
        distribution="normal",
        notes=["正态假设低估尾部，仅作对照"],
    )


def estimate_t_dof(returns: pd.Series, *, floor: float = 2.5, cap: float = 30.0) -> float:
    """Student-t degrees of freedom implied by the sample kurtosis.

    For a t distribution, excess kurtosis is ``6 / (nu - 4)`` when ``nu > 4``.
    Inverting that is crude but robust and needs no optimiser. The result is
    clamped: below ~2.5 the variance stops existing, and above ~30 the t is
    indistinguishable from a normal so there is no point pretending otherwise.
    """
    series = returns.dropna()
    if len(series) < 30:
        raise RiskInputError(f"need at least 30 observations, got {len(series)}")

    excess = float(stats.kurtosis(series, fisher=True, bias=False))
    if excess <= 0:
        return cap
    return float(np.clip(4 + 6 / excess, floor, cap))


def monte_carlo_portfolio_var(
    returns: pd.DataFrame,
    weights: pd.Series,
    *,
    confidence: float = 0.95,
    horizon_days: int = 1,
    lam: float = DEFAULT_LAMBDA,
    distribution: str = "t",
    simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
) -> tuple[VarResult, dict]:
    """Monte Carlo portfolio VaR from an EWMA covariance matrix.

    Draws correlated asset returns, applies the portfolio weights, and reads the
    tail off the resulting distribution of portfolio outcomes. Correlation is
    what makes this a portfolio calculation rather than a pile of single-asset
    ones — simulating each position independently would quietly assume that
    everything you own never falls on the same day.

    Args:
        returns: Asset returns, one column per position.
        weights: Portfolio weights indexed by the same columns. Rescaled to sum
            to one if they do not already.
        confidence: e.g. 0.95.
        horizon_days: Simulated directly (not sqrt-scaled) by summing that many
            independent draws, which is still an iid assumption but at least
            keeps the fat tails.
        lam: EWMA decay for the covariance estimate.
        distribution: ``"t"`` (fat tails, degrees of freedom estimated from the
            data) or ``"normal"``.
        simulations: Number of paths.
        seed: Fixed so the same inputs give the same number. A risk figure that
            changes on every refresh cannot be discussed.

    Returns:
        ``(VarResult, diagnostics)``.
    """
    _check_confidence(confidence)
    if distribution not in ("t", "normal"):
        raise ValueError(f"distribution must be 't' or 'normal', got {distribution!r}")
    if horizon_days < 1:
        raise ValueError("horizon_days must be at least 1")

    frame = returns.dropna(how="any")
    aligned = weights.reindex(frame.columns).fillna(0.0).astype(float)
    total = aligned.sum()
    if total == 0:
        raise RiskInputError("portfolio weights sum to zero")
    aligned = aligned / total

    cov = ewma_covariance(frame, lam=lam)
    cov, repaired = nearest_positive_semidefinite(cov)

    notes: list[str] = []
    if repaired:
        notes.append(
            "EWMA 协方差矩阵存在负特征值（通常源于标的高度共线或样本偏短），"
            "已做最近半正定修正 —— 结果可用但应留意"
        )

    portfolio_returns = frame @ aligned
    dof = None
    rng = np.random.default_rng(seed)
    cov_values = cov.to_numpy(dtype=float)

    if distribution == "t":
        dof = estimate_t_dof(portfolio_returns)
        # Scale the covariance so the simulated t has the estimated covariance:
        # a standard t with nu dof has variance nu/(nu-2).
        scale_matrix = cov_values * (dof - 2) / dof
        chol = _safe_cholesky(scale_matrix)
        normals = rng.standard_normal((simulations * horizon_days, len(aligned)))
        chi = rng.chisquare(dof, size=(simulations * horizon_days, 1))
        draws = normals @ chol.T * np.sqrt(dof / chi)
    else:
        chol = _safe_cholesky(cov_values)
        draws = rng.standard_normal((simulations * horizon_days, len(aligned))) @ chol.T

    path_returns = (draws @ aligned.to_numpy()).reshape(simulations, horizon_days)
    horizon_returns = path_returns.sum(axis=1)      # log returns aggregate additively

    losses = -horizon_returns
    var, es = _tail(losses, confidence)

    if horizon_days > 1:
        notes.append(
            f"{horizon_days} 日为直接模拟（{horizon_days} 个独立日相加），"
            "未做 √T 缩放，但仍假设日间独立"
        )

    diagnostics = {
        "assets": list(frame.columns),
        "observations": int(len(frame)),
        "lambda": lam,
        "simulations": simulations,
        "dof": dof,
        "covariance_repaired": repaired,
        "portfolio_daily_vol": float(np.sqrt(aligned @ cov_values @ aligned)),
        "sample_kurtosis": float(stats.kurtosis(portfolio_returns, fisher=True, bias=False)),
        "sample_skew": float(stats.skew(portfolio_returns, bias=False)),
    }

    return (
        VarResult(
            method="monte_carlo",
            confidence=confidence,
            horizon_days=horizon_days,
            var=var,
            expected_shortfall=es,
            distribution=distribution,
            notes=notes,
        ),
        diagnostics,
    )


def _safe_cholesky(matrix: np.ndarray) -> np.ndarray:
    """Cholesky factor, falling back to an eigen decomposition if needed."""
    try:
        return np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError:
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        return eigenvectors @ np.diag(np.sqrt(np.clip(eigenvalues, 0.0, None)))


def kupiec_backtest(
    returns: pd.Series,
    var_series: pd.Series,
    *,
    confidence: float = 0.95,
) -> BacktestResult:
    """Kupiec proportion-of-failures test on a VaR series.

    Counts how often the realised loss exceeded that day's VaR and asks whether
    that count is plausible for the stated confidence. Both directions matter:
    too many breaches means the model understates risk, too few means it is
    tying up attention (or capital) on a danger that is not there.

    Args:
        returns: Realised returns, indexed by date.
        var_series: VaR as a **positive loss fraction** for the same dates.
        confidence: The level the VaR series claims.
    """
    _check_confidence(confidence)

    aligned = pd.concat(
        [returns.rename("r"), var_series.rename("var")], axis=1, join="inner"
    ).dropna()
    n = len(aligned)
    if n < 30:
        raise RiskInputError(f"need at least 30 aligned observations, got {n}")

    breaches = int((-aligned["r"] > aligned["var"]).sum())
    p = 1 - confidence
    rate = breaches / n

    # Kupiec POF likelihood ratio; chi-square with 1 dof under the null.
    if breaches == 0:
        lr = -2 * n * np.log(1 - p)
    elif breaches == n:
        lr = -2 * n * np.log(p)
    else:
        lr = -2 * (
            (n - breaches) * np.log(1 - p)
            + breaches * np.log(p)
            - (n - breaches) * np.log(1 - rate)
            - breaches * np.log(rate)
        )

    return BacktestResult(
        confidence=confidence,
        observations=n,
        breaches=breaches,
        expected_breaches=n * p,
        breach_rate=rate,
        kupiec_statistic=float(lr),
        kupiec_p_value=float(1 - stats.chi2.cdf(lr, df=1)),
    )
