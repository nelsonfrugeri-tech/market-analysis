"""Performance calculation engine.

Computes fund returns, volatility, and benchmark comparisons
from raw daily records and benchmark rates.
"""

from __future__ import annotations

import math
from datetime import date

from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.infrastructure.benchmark_fetcher import BenchmarkRates


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


def compute_performance(
    records: list[FundDailyRecord],
    benchmarks: BenchmarkRates,
    fund_name: str = "Nu Reserva Planejada",
) -> FundPerformance:
    """Compute full performance metrics from daily records and benchmarks.

    Args:
        records: List of FundDailyRecord sorted by date ascending.
        benchmarks: Dict with 'selic', 'cdi', 'ipca' accumulated rates.
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

    selic_pct = benchmarks.get("selic", 0.0)
    cdi_pct = benchmarks.get("cdi", 0.0)
    ipca_pct = benchmarks.get("ipca", 0.0)

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
        daily_records=records,
    )
