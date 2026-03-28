"""Performance calculation engine.

Computes fund returns, volatility, and benchmark comparisons
from raw daily records and benchmark rates.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Dict, Any

from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.infrastructure.benchmarks import BenchmarkData


def calculate_return(nav_start: float, nav_end: float) -> float:
    """Calculate percentage return between two NAV values.

    Returns:
        Return as percentage (e.g. 2.5 means 2.5%).
    """
    if nav_start <= 0:
        return 0.0
    return ((nav_end / nav_start) - 1) * 100


def calculate_volatility(records: list[FundDailyRecord]) -> float:
    """Calculate annualized volatility from daily NAV records.

    Uses standard deviation of daily log returns, annualized
    with sqrt(252) factor.

    Returns:
        Annualized volatility as percentage.
    """
    if len(records) < 2:
        return 0.0

    daily_returns: list[float] = []
    for i in range(1, len(records)):
        if records[i - 1].nav > 0:
            log_return = math.log(records[i].nav / records[i - 1].nav)
            daily_returns.append(log_return)

    if not daily_returns:
        return 0.0

    n = len(daily_returns)
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1) if n > 1 else 0.0
    daily_std = math.sqrt(variance)

    annualized = daily_std * math.sqrt(252) * 100
    return round(annualized, 4)


def determine_trend(records: list[FundDailyRecord], window: int = 30) -> str:
    """Determine price trend over the last N records.

    Returns:
        "up", "down", or "flat".
    """
    recent = records[-window:] if len(records) >= window else records
    if len(recent) < 2:
        return "flat"

    ret = calculate_return(recent[0].nav, recent[-1].nav)
    if ret > 0.1:
        return "up"
    elif ret < -0.1:
        return "down"
    return "flat"


def calculate_sharpe_ratio(
    fund_return: float, fund_volatility: float, benchmark_return: float
) -> float:
    """Calculate Sharpe ratio using benchmark as risk-free rate.

    Args:
        fund_return: Fund annualized return (%)
        fund_volatility: Fund annualized volatility (%)
        benchmark_return: Benchmark return (%) - typically CDI

    Returns:
        Sharpe ratio (dimensionless).
    """
    if fund_volatility <= 0:
        return 0.0

    excess_return = fund_return - benchmark_return
    return round(excess_return / fund_volatility, 4)


def calculate_alpha_beta(records: list[FundDailyRecord], benchmark_return: float) -> tuple[float, float]:
    """Calculate Alpha and Beta vs benchmark.

    Alpha: Excess return above expected (Jensen's Alpha)
    Beta: Sensitivity to benchmark movements

    Args:
        records: Daily fund records
        benchmark_return: Benchmark accumulated return (%)

    Returns:
        Tuple of (alpha, beta) both as floats.
    """
    if len(records) < 10:  # Need minimum data
        return 0.0, 0.0

    # Calculate daily returns
    fund_returns = []
    for i in range(1, len(records)):
        if records[i - 1].nav > 0:
            daily_ret = (records[i].nav / records[i - 1].nav - 1) * 100
            fund_returns.append(daily_ret)

    if len(fund_returns) < 10:
        return 0.0, 0.0

    # Estimate daily benchmark return (assuming uniform distribution)
    daily_benchmark = (benchmark_return / len(fund_returns)) if len(fund_returns) > 0 else 0.0

    # Simple beta calculation: covariance(fund, benchmark) / variance(benchmark)
    # For constant benchmark, use correlation with market proxy
    fund_mean = sum(fund_returns) / len(fund_returns)

    # Simplified beta (sensitivity measure)
    fund_vol = sum((r - fund_mean) ** 2 for r in fund_returns) / len(fund_returns)
    beta = min(max(fund_vol / 0.01 if fund_vol > 0 else 1.0, 0.1), 3.0)  # Cap between 0.1 and 3.0

    # Alpha: excess return above expected
    fund_annual_return = ((1 + fund_mean/100) ** 252 - 1) * 100
    expected_return = daily_benchmark * 252
    alpha = fund_annual_return - expected_return

    return round(alpha, 4), round(beta, 4)


def calculate_var_95(records: list[FundDailyRecord]) -> float:
    """Calculate Value at Risk (VaR) at 95% confidence level.

    Args:
        records: Daily fund records

    Returns:
        VaR as percentage (negative value indicates loss).
    """
    if len(records) < 30:  # Need minimum 30 days
        return 0.0

    # Calculate daily returns
    daily_returns = []
    for i in range(1, len(records)):
        if records[i - 1].nav > 0:
            daily_ret = (records[i].nav / records[i - 1].nav - 1) * 100
            daily_returns.append(daily_ret)

    if len(daily_returns) < 30:
        return 0.0

    # Sort returns and find 5th percentile (95% VaR)
    daily_returns.sort()
    var_index = int(len(daily_returns) * 0.05)
    daily_var = daily_returns[var_index]

    # Annualize VaR (monthly approximation)
    monthly_var = daily_var * math.sqrt(21)  # 21 trading days per month

    return round(monthly_var, 4)


def calculate_max_drawdown(records: list[FundDailyRecord]) -> float:
    """Calculate maximum drawdown from peak to trough.

    Args:
        records: Daily fund records

    Returns:
        Maximum drawdown as negative percentage.
    """
    if len(records) < 2:
        return 0.0

    peak_nav = records[0].nav
    max_drawdown = 0.0

    for record in records:
        # Update peak if new high
        if record.nav > peak_nav:
            peak_nav = record.nav

        # Calculate drawdown from peak
        if peak_nav > 0:
            current_drawdown = ((record.nav / peak_nav) - 1) * 100
            if current_drawdown < max_drawdown:
                max_drawdown = current_drawdown

    return round(max_drawdown, 4)


def compute_performance(
    records: list[FundDailyRecord],
    benchmarks: BenchmarkData,
    fund_name: str = "Nu Reserva Planejada",
) -> FundPerformance:
    """Compute full performance metrics from daily records and benchmarks.

    Args:
        records: List of FundDailyRecord sorted by date ascending.
        benchmarks: BenchmarkData with accumulated rates and derived calculations.
        fund_name: Display name for the fund.

    Returns:
        FundPerformance with all metrics computed.

    Raises:
        ValueError: If records list is empty.
    """
    if not records:
        raise ValueError("Cannot compute performance with empty records")

    first = records[0]
    last = records[-1]

    fund_return = calculate_return(first.nav, last.nav)
    volatility = calculate_volatility(records)
    trend = determine_trend(records)

    selic_pct = benchmarks.selic_accumulated
    cdi_pct = benchmarks.cdi_accumulated
    ipca_pct = benchmarks.ipca_accumulated

    # Calculate advanced metrics
    sharpe = calculate_sharpe_ratio(fund_return, volatility, cdi_pct)
    alpha, beta = calculate_alpha_beta(records, cdi_pct)
    var_95 = calculate_var_95(records)
    max_dd = calculate_max_drawdown(records)

    return FundPerformance(
        fund_cnpj=first.cnpj,
        fund_name=fund_name,
        period_start=first.date,
        period_end=last.date,
        nav_start=first.nav,
        nav_end=last.nav,
        return_pct=round(fund_return, 4),
        equity_start=first.equity,
        equity_end=last.equity,
        volatility=volatility,
        shareholders_current=last.shareholders,
        benchmark_selic=round(selic_pct, 4),
        benchmark_cdi=round(cdi_pct, 4),
        benchmark_ipca=round(ipca_pct, 4),
        vs_selic=round(fund_return - selic_pct, 4),
        vs_cdi=round(fund_return - cdi_pct, 4),
        vs_ipca=round(fund_return - ipca_pct, 4),
        trend_30d=trend,

        # Advanced metrics
        sharpe_ratio=sharpe,
        alpha=alpha,
        beta=beta,
        var_95=var_95,
        max_drawdown=max_dd,

        daily_records=records,
    )


def extract_metrics_for_llm_explanation(performance: FundPerformance) -> Dict[str, Any]:
    """Extract key metrics in structured format for LLM educational explanations.

    This prepares data that Elliot's LLM integration will use to generate
    educational explanations in Portuguese.

    Args:
        performance: Computed FundPerformance object

    Returns:
        Dictionary with categorized metrics ready for LLM processing.
    """
    return {
        "performance_metrics": {
            "fund_name": performance.fund_name,
            "period": {
                "start": performance.period_start.strftime("%d/%m/%Y"),
                "end": performance.period_end.strftime("%d/%m/%Y"),
                "days": (performance.period_end - performance.period_start).days,
            },
            "return_pct": performance.return_pct,
            "nav_change": {
                "start": performance.nav_start,
                "end": performance.nav_end,
                "change_pct": performance.return_pct,
            },
        },
        "risk_metrics": {
            "volatility": performance.volatility,
            "sharpe_ratio": performance.sharpe_ratio,
            "max_drawdown": performance.max_drawdown,
            "var_95": performance.var_95,
        },
        "efficiency_metrics": {
            "alpha": performance.alpha,
            "beta": performance.beta,
        },
        "benchmark_comparison": {
            "vs_cdi": performance.vs_cdi,
            "vs_selic": performance.vs_selic,
            "vs_ipca": performance.vs_ipca,
            "benchmark_rates": {
                "cdi": performance.benchmark_cdi,
                "selic": performance.benchmark_selic,
                "ipca": performance.benchmark_ipca,
            },
        },
        "market_context": {
            "trend_30d": performance.trend_30d,
            "shareholders": performance.shareholders_current,
            "equity_millions": round(performance.equity_end / 1_000_000, 2),
        },
    }
