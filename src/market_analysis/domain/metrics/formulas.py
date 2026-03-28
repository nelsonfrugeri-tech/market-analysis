"""Pure mathematical functions for financial metrics.

All functions operate on plain lists/floats. No domain types here.
This keeps calculations testable and decoupled from data models.
"""

from __future__ import annotations

import math
from typing import Optional


def annualized_return(cumulative_pct: float, trading_days: int) -> float:
    """Convert cumulative % return to annualized %.

    Args:
        cumulative_pct: Total return in % (e.g., 5.0 for 5%).
        trading_days: Number of trading days in the period.

    Returns:
        Annualized return in %.
    """
    if trading_days <= 0:
        return 0.0
    factor = 1 + cumulative_pct / 100
    if factor <= 0:
        return -100.0
    annualized = factor ** (252 / trading_days) - 1
    return round(annualized * 100, 4)


def daily_returns(navs: list[float]) -> list[float]:
    """Calculate daily returns from a NAV series.

    Args:
        navs: List of daily NAV values (must have len >= 2).

    Returns:
        List of daily returns in % (len = len(navs) - 1).
    """
    if len(navs) < 2:
        return []
    return [
        (navs[i] / navs[i - 1] - 1) * 100
        for i in range(1, len(navs))
        if navs[i - 1] > 0
    ]


def cumulative_return(nav_start: float, nav_end: float) -> float:
    """Simple cumulative return in %."""
    if nav_start <= 0:
        return 0.0
    return round((nav_end / nav_start - 1) * 100, 4)


def volatility_annualized(daily_rets: list[float]) -> float:
    """Annualized volatility from daily returns (%).

    Uses population std dev * sqrt(252).
    """
    if len(daily_rets) < 2:
        return 0.0
    mean = sum(daily_rets) / len(daily_rets)
    variance = sum((r - mean) ** 2 for r in daily_rets) / len(daily_rets)
    daily_std = math.sqrt(variance)
    return round(daily_std * math.sqrt(252), 4)


def downside_deviation(daily_rets: list[float], target: float = 0.0) -> float:
    """Downside deviation: std dev of returns below target.

    Args:
        daily_rets: Daily returns in %.
        target: Minimum acceptable return (default 0).

    Returns:
        Annualized downside deviation in %.
    """
    if len(daily_rets) < 2:
        return 0.0
    downside = [min(r - target, 0) ** 2 for r in daily_rets]
    dd = math.sqrt(sum(downside) / len(downside))
    return round(dd * math.sqrt(252), 4)


def sharpe_ratio(
    fund_return_pct: float,
    risk_free_pct: float,
    volatility_pct: float,
) -> float:
    """Sharpe Ratio = (Rp - Rf) / sigma_p."""
    if volatility_pct <= 0:
        return 0.0
    return round((fund_return_pct - risk_free_pct) / volatility_pct, 4)


def sortino_ratio(
    fund_return_pct: float,
    risk_free_pct: float,
    downside_dev_pct: float,
) -> float:
    """Sortino Ratio = (Rp - Rf) / downside_deviation."""
    if downside_dev_pct <= 0:
        return 0.0
    return round((fund_return_pct - risk_free_pct) / downside_dev_pct, 4)


def max_drawdown(navs: list[float]) -> float:
    """Maximum peak-to-trough drawdown in %.

    Returns a negative number (or 0 if no drawdown).
    """
    if len(navs) < 2:
        return 0.0
    peak = navs[0]
    mdd = 0.0
    for nav in navs:
        if nav > peak:
            peak = nav
        if peak > 0:
            dd = (nav / peak - 1) * 100
            if dd < mdd:
                mdd = dd
    return round(mdd, 4)


def var_parametric_95(daily_rets: list[float]) -> Optional[float]:
    """Parametric VaR at 95% confidence (monthly).

    Returns None if fewer than 60 observations.
    """
    if len(daily_rets) < 60:
        return None
    mean = sum(daily_rets) / len(daily_rets)
    variance = sum((r - mean) ** 2 for r in daily_rets) / len(daily_rets)
    std = math.sqrt(variance)
    # 1.645 = z-score for 95% one-tail
    daily_var = mean - 1.645 * std
    # Scale to monthly (21 trading days)
    monthly_var = daily_var * math.sqrt(21)
    return round(monthly_var, 4)


def beta_coefficient(
    fund_daily_rets: list[float],
    benchmark_daily_rets: list[float],
) -> Optional[float]:
    """Beta = Cov(Rp, Rm) / Var(Rm) via simple linear regression.

    Returns None if fewer than 30 paired observations.
    """
    n = min(len(fund_daily_rets), len(benchmark_daily_rets))
    if n < 30:
        return None

    fund = fund_daily_rets[:n]
    bench = benchmark_daily_rets[:n]

    mean_f = sum(fund) / n
    mean_b = sum(bench) / n

    cov = sum((fund[i] - mean_f) * (bench[i] - mean_b) for i in range(n)) / n
    var_b = sum((bench[i] - mean_b) ** 2 for i in range(n)) / n

    if var_b <= 1e-12:
        return None
    return round(cov / var_b, 4)


def alpha_jensen(
    fund_return_pct: float,
    risk_free_pct: float,
    market_return_pct: float,
    beta: float,
) -> float:
    """Jensen's Alpha = Rp - [Rf + Beta * (Rm - Rf)]."""
    expected = risk_free_pct + beta * (market_return_pct - risk_free_pct)
    return round(fund_return_pct - expected, 4)


def tracking_error(
    fund_daily_rets: list[float],
    benchmark_daily_rets: list[float],
) -> Optional[float]:
    """Tracking Error = annualized std dev of (Rp - Rm).

    Returns None if fewer than 30 paired observations.
    """
    n = min(len(fund_daily_rets), len(benchmark_daily_rets))
    if n < 30:
        return None

    excess = [fund_daily_rets[i] - benchmark_daily_rets[i] for i in range(n)]
    mean_e = sum(excess) / n
    variance = sum((e - mean_e) ** 2 for e in excess) / n
    daily_te = math.sqrt(variance)
    return round(daily_te * math.sqrt(252), 4)


def information_ratio(
    fund_return_pct: float,
    benchmark_return_pct: float,
    te: float,
) -> Optional[float]:
    """Information Ratio = (Rp - Rm) / Tracking Error."""
    if te is None or te <= 0:
        return None
    return round((fund_return_pct - benchmark_return_pct) / te, 4)


def pearson_correlation(
    xs: list[float],
    ys: list[float],
) -> Optional[float]:
    """Pearson correlation coefficient.

    Returns None if fewer than 30 paired observations.
    """
    n = min(len(xs), len(ys))
    if n < 30:
        return None

    mean_x = sum(xs[:n]) / n
    mean_y = sum(ys[:n]) / n

    cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / n
    var_x = sum((xs[i] - mean_x) ** 2 for i in range(n)) / n
    var_y = sum((ys[i] - mean_y) ** 2 for i in range(n)) / n

    denom = math.sqrt(var_x * var_y)
    if denom <= 1e-12:
        return None
    return round(cov / denom, 4)


def monthly_returns_from_daily(
    dates: list, navs: list[float]
) -> list[tuple[str, float]]:
    """Aggregate daily NAVs into monthly returns.

    Args:
        dates: List of date objects (aligned with navs).
        navs: Daily NAV values.

    Returns:
        List of (YYYY-MM, return_pct) tuples.
    """
    if len(dates) < 2 or len(dates) != len(navs):
        return []

    monthly: dict[str, list[float]] = {}
    for d, nav in zip(dates, navs):
        key = d.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = []
        monthly[key].append(nav)

    results = []
    for key in sorted(monthly):
        vals = monthly[key]
        if len(vals) >= 2 and vals[0] > 0:
            ret = (vals[-1] / vals[0] - 1) * 100
            results.append((key, round(ret, 4)))
    return results


def stability_index(
    positive_months_pct: float,
    sharpe: float,
    max_dd: float,
    vol: float,
) -> float:
    """Stability Index (0.0 to 1.0).

    Formula:
        0.30 * (positive_months_pct / 100)
      + 0.25 * min(1, sharpe / 2)
      + 0.25 * (1 - min(1, |max_dd| / 10))
      + 0.20 * (1 - min(1, vol / 15))
    """
    s1 = 0.30 * min(1.0, max(0.0, positive_months_pct / 100))
    s2 = 0.25 * min(1.0, max(0.0, sharpe / 2))
    s3 = 0.25 * (1 - min(1.0, abs(max_dd) / 10))
    s4 = 0.20 * (1 - min(1.0, vol / 15))
    return round(s1 + s2 + s3 + s4, 4)
