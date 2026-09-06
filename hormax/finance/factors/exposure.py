"""Factor exposure: regress a return series on factor returns.

This is a **time-series** regression, not a cross-sectional one. It asks "what
was this portfolio actually exposed to", which needs only the portfolio's own
return history — so it stays meaningful for a portfolio of a dozen names, where
cross-sectional factor work would not.

    r_p - rf = alpha + sum_k beta_k * factor_k + epsilon

Daily returns are autocorrelated and heteroskedastic, so the ordinary standard
errors overstate significance. Newey-West (HAC) errors are the default here for
that reason; the lag length is a parameter because the right value depends on
how persistent the series is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
import statsmodels.api as sm

TRADING_DAYS_PER_YEAR = 252


class ExposureError(ValueError):
    """The regression could not be run on the given inputs."""


@dataclass(frozen=True)
class FactorLoading:
    """One factor's estimated coefficient."""

    factor: str
    beta: float
    t_stat: float
    p_value: float

    @property
    def significant(self) -> bool:
        """Whether the loading clears the conventional 5% threshold."""
        return self.p_value < 0.05


@dataclass(frozen=True)
class ExposureResult:
    """Outcome of one factor-exposure regression."""

    start: date
    end: date
    observations: int
    alpha_daily: float
    alpha_annualised: float
    alpha_t_stat: float
    alpha_p_value: float
    r_squared: float
    adj_r_squared: float
    loadings: list[FactorLoading]
    cov_type: str
    nw_lags: int | None

    @property
    def alpha_significant(self) -> bool:
        return self.alpha_p_value < 0.05

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "observations": self.observations,
            "alpha_daily": self.alpha_daily,
            "alpha_annualised": self.alpha_annualised,
            "alpha_t_stat": self.alpha_t_stat,
            "alpha_p_value": self.alpha_p_value,
            "alpha_significant": self.alpha_significant,
            "r_squared": self.r_squared,
            "adj_r_squared": self.adj_r_squared,
            "cov_type": self.cov_type,
            "nw_lags": self.nw_lags,
            "loadings": [
                {
                    "factor": l.factor,
                    "beta": l.beta,
                    "t_stat": l.t_stat,
                    "p_value": l.p_value,
                    "significant": l.significant,
                }
                for l in self.loadings
            ],
        }


def _default_lags(n: int) -> int:
    """Newey-West lag length by the usual rule of thumb, ``4*(n/100)^(2/9)``."""
    return max(1, int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0))))


def factor_exposure(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
    *,
    factor_columns: list[str] | None = None,
    rf_column: str = "rf",
    use_newey_west: bool = True,
    nw_lags: int | None = None,
    min_observations: int = 60,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> ExposureResult:
    """Regress excess portfolio returns on factor returns.

    Args:
        portfolio_returns: Daily **total** returns (not excess), indexed by date.
        factors: Daily factor returns indexed by date, including the risk-free
            column. Both must be decimals, not percent.
        factor_columns: Which columns to use as regressors. Defaults to every
            column except ``rf_column``.
        rf_column: Name of the risk-free column, subtracted from the portfolio
            return to form the dependent variable. Using a risk-free rate from
            a different source than the factors is a common way to get a
            slightly wrong alpha, so the default expects them to arrive together.
        use_newey_west: Use HAC standard errors. Turning this off gives
            ordinary OLS errors, which will look more significant than they are.
        nw_lags: HAC lag length. ``None`` picks ``4*(n/100)^(2/9)``.
        min_observations: Refuse to report a regression with fewer overlapping
            days than this — a six-factor fit on a handful of points is noise
            with a decimal point.
        trading_days: Used to annualise alpha.

    Returns:
        ExposureResult.

    Raises:
        ExposureError: If the inputs do not overlap enough to fit.
    """
    if portfolio_returns.empty:
        raise ExposureError("portfolio return series is empty")
    if rf_column not in factors.columns:
        raise ExposureError(
            f"factors has no {rf_column!r} column; got {list(factors.columns)}"
        )

    columns = factor_columns or [c for c in factors.columns if c != rf_column]
    missing = [c for c in columns if c not in factors.columns]
    if missing:
        raise ExposureError(f"factors is missing requested columns: {missing}")

    aligned = pd.concat(
        [portfolio_returns.rename("portfolio"), factors[[*columns, rf_column]]],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < min_observations:
        overlap = (
            f"{aligned.index[0].date()} → {aligned.index[-1].date()}"
            if len(aligned)
            else "none"
        )
        raise ExposureError(
            f"only {len(aligned)} overlapping observations (need {min_observations}); "
            f"overlap was {overlap}. Factor data lags the present by weeks, so a "
            f"window ending today will overlap less than you expect."
        )

    y = aligned["portfolio"] - aligned[rf_column]
    X = sm.add_constant(aligned[columns], has_constant="add")

    if use_newey_west:
        lags = _default_lags(len(aligned)) if nw_lags is None else nw_lags
        model = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        cov_type, used_lags = "HAC (Newey-West)", lags
    else:
        model = sm.OLS(y, X).fit()
        cov_type, used_lags = "nonrobust", None

    alpha = float(model.params["const"])
    loadings = [
        FactorLoading(
            factor=name,
            beta=float(model.params[name]),
            t_stat=float(model.tvalues[name]),
            p_value=float(model.pvalues[name]),
        )
        for name in columns
    ]

    return ExposureResult(
        start=aligned.index[0].date(),
        end=aligned.index[-1].date(),
        observations=len(aligned),
        alpha_daily=alpha,
        alpha_annualised=alpha * trading_days,
        alpha_t_stat=float(model.tvalues["const"]),
        alpha_p_value=float(model.pvalues["const"]),
        r_squared=float(model.rsquared),
        adj_r_squared=float(model.rsquared_adj),
        loadings=loadings,
        cov_type=cov_type,
        nw_lags=used_lags,
    )


def rolling_factor_exposure(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
    *,
    window: int = 252,
    step: int = 5,
    **kwargs,
) -> pd.DataFrame:
    """Run :func:`factor_exposure` over a rolling window.

    A single full-sample regression hides style drift: a portfolio that was a
    value bet last year and a momentum bet this year shows up as neither.

    Args:
        portfolio_returns: Daily total returns.
        factors: Daily factor returns including the risk-free column.
        window: Observations per regression.
        step: How many observations to advance between fits. Fitting every
            single day is mostly redundant — consecutive windows share all but
            one observation.
        **kwargs: Passed through to :func:`factor_exposure`.

    Returns:
        DataFrame indexed by each window's end date, with a column per beta
        plus ``alpha_annualised`` and ``r_squared``. Empty if the overlap is
        shorter than one window.
    """
    if window <= 0 or step <= 0:
        raise ValueError("window and step must be positive")

    kwargs.setdefault("min_observations", max(30, window // 4))

    aligned_index = portfolio_returns.dropna().index.intersection(factors.dropna().index)
    if len(aligned_index) < window:
        return pd.DataFrame()

    rows = []
    for end in range(window, len(aligned_index) + 1, step):
        window_index = aligned_index[end - window : end]
        try:
            result = factor_exposure(
                portfolio_returns.loc[window_index],
                factors.loc[window_index],
                **kwargs,
            )
        except ExposureError:
            continue

        row = {loading.factor: loading.beta for loading in result.loadings}
        row["alpha_annualised"] = result.alpha_annualised
        row["r_squared"] = result.r_squared
        rows.append((window_index[-1], row))

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([r for _, r in rows], index=[d for d, _ in rows])
