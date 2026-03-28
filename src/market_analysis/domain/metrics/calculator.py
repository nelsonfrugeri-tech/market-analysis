"""Orchestrator: compute all advanced metrics from domain models.

Takes fund daily records + benchmark data and produces a single
AdvancedMetrics dataclass with every metric from Issue #57.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from market_analysis.domain.models.fund import FundDailyRecord
from market_analysis.infrastructure.benchmarks.data_models import BenchmarkData

from . import formulas as f

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AdvancedMetrics:
    """Complete set of advanced financial metrics."""

    # Performance
    cumulative_return: float
    ytd_return: float
    twelve_month_return: Optional[float]
    six_month_return: Optional[float]
    three_month_return: Optional[float]
    monthly_avg_return: float

    # Risk
    volatility: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    var_95: Optional[float]

    # Efficiency
    alpha: Optional[float]
    beta: Optional[float]
    tracking_error: Optional[float]
    information_ratio: Optional[float]
    correlation: Optional[float]

    # Consistency
    positive_months_pct: float
    best_month: float
    worst_month: float
    win_loss_vs_cdi: float
    stability_index: float

    # Comparisons (excess return vs benchmark)
    vs_cdi: float
    vs_selic: float
    vs_ipca: float
    vs_cdb: float
    vs_poupanca: float

    # Monthly breakdown
    monthly_returns: list[tuple[str, float]]


def _align_benchmark_daily_returns(
    fund_dates: list[date],
    benchmark: BenchmarkData,
) -> list[float]:
    """Build benchmark daily return series aligned with fund dates.

    The fund has records on business days. We match each fund date
    to the corresponding CDI daily factor from BenchmarkData.daily_records.
    """
    bm_by_date = {
        rec.date: rec.cdi_daily_factor or 0.0
        for rec in benchmark.daily_records
    }
    # Skip first date (returns need pairs)
    return [bm_by_date.get(d, 0.0) for d in fund_dates[1:]]


def _sub_period_return(
    records: list[FundDailyRecord],
    cutoff: date,
) -> Optional[float]:
    """Return for records from cutoff onwards. None if no data before cutoff."""
    filtered = [r for r in records if r.date >= cutoff]
    if len(filtered) < 2:
        return None
    return f.cumulative_return(filtered[0].nav, filtered[-1].nav)


def _monthly_cdi_returns(
    benchmark: BenchmarkData,
) -> dict[str, float]:
    """Compute monthly CDI returns from daily factors."""
    monthly: dict[str, list[float]] = {}
    for rec in benchmark.daily_records:
        key = rec.date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = []
        if rec.cdi_daily_factor is not None:
            monthly[key].append(rec.cdi_daily_factor)

    result = {}
    for key in sorted(monthly):
        factors = monthly[key]
        acc = 1.0
        for fac in factors:
            acc *= 1 + fac / 100
        result[key] = round((acc - 1) * 100, 4)
    return result


def compute_advanced_metrics(
    records: list[FundDailyRecord],
    benchmark: BenchmarkData,
    reference_date: Optional[date] = None,
) -> AdvancedMetrics:
    """Compute all advanced metrics from fund records and benchmark data.

    Args:
        records: Fund daily records sorted by date ascending.
        benchmark: BenchmarkData with daily_records populated.
        reference_date: Date for YTD calculation (defaults to last record date).

    Returns:
        AdvancedMetrics with all fields populated.

    Raises:
        ValueError: If records is empty.
    """
    if not records:
        raise ValueError("Cannot compute metrics from empty records")

    records = sorted(records, key=lambda r: r.date)
    navs = [r.nav for r in records]
    dates = [r.date for r in records]
    ref_date = reference_date or dates[-1]

    # -- Daily returns --
    fund_rets = f.daily_returns(navs)
    bm_rets = _align_benchmark_daily_returns(dates, benchmark)

    # Ensure same length
    n = min(len(fund_rets), len(bm_rets))
    fund_rets_aligned = fund_rets[:n]
    bm_rets_aligned = bm_rets[:n]

    # -- Performance --
    cum_return = f.cumulative_return(navs[0], navs[-1])

    # YTD: from Jan 1 of reference year
    ytd_cutoff = date(ref_date.year, 1, 1)
    ytd = _sub_period_return(records, ytd_cutoff)
    ytd_return = ytd if ytd is not None else cum_return

    # Sub-period returns
    from datetime import timedelta

    twelve_m = _sub_period_return(records, ref_date - timedelta(days=365))
    six_m = _sub_period_return(records, ref_date - timedelta(days=182))
    three_m = _sub_period_return(records, ref_date - timedelta(days=91))

    # Monthly returns
    monthly_rets = f.monthly_returns_from_daily(dates, navs)
    month_values = [m[1] for m in monthly_rets]
    monthly_avg = round(sum(month_values) / len(month_values), 4) if month_values else 0.0

    # -- Risk --
    vol = f.volatility_annualized(fund_rets)
    mdd = f.max_drawdown(navs)

    cdi_pct = benchmark.cdi_accumulated
    ann_return = f.annualized_return(cum_return, len(fund_rets))

    sharpe = f.sharpe_ratio(ann_return, cdi_pct, vol)
    dd = f.downside_deviation(fund_rets)
    sortino = f.sortino_ratio(ann_return, cdi_pct, dd)
    var_95 = f.var_parametric_95(fund_rets)

    # -- Efficiency --
    beta = f.beta_coefficient(fund_rets_aligned, bm_rets_aligned)

    if beta is not None:
        alpha = f.alpha_jensen(ann_return, cdi_pct, cdi_pct, beta)
    else:
        alpha = None

    te = f.tracking_error(fund_rets_aligned, bm_rets_aligned)
    ir = f.information_ratio(cum_return, cdi_pct, te) if te else None
    corr = f.pearson_correlation(fund_rets_aligned, bm_rets_aligned)

    # -- Consistency --
    positive_months = sum(1 for v in month_values if v > 0)
    pos_pct = round(positive_months / len(month_values) * 100, 2) if month_values else 0.0
    best_month = max(month_values) if month_values else 0.0
    worst_month = min(month_values) if month_values else 0.0

    # Win/loss vs CDI
    cdi_monthly = _monthly_cdi_returns(benchmark)
    wins = 0
    total_compared = 0
    for month_key, fund_ret in monthly_rets:
        if month_key in cdi_monthly:
            total_compared += 1
            if fund_ret >= cdi_monthly[month_key]:
                wins += 1
    win_loss = round(wins / total_compared * 100, 2) if total_compared > 0 else 0.0

    si = f.stability_index(pos_pct, sharpe, mdd, vol)

    # -- Comparisons --
    vs_cdi = round(cum_return - benchmark.cdi_accumulated, 4)
    vs_selic = round(cum_return - benchmark.selic_accumulated, 4)
    vs_ipca = round(cum_return - benchmark.ipca_accumulated, 4)
    vs_cdb = round(cum_return - benchmark.cdb_estimated, 4)
    vs_poupanca = round(cum_return - benchmark.poupanca_estimated, 4)

    return AdvancedMetrics(
        cumulative_return=cum_return,
        ytd_return=ytd_return,
        twelve_month_return=twelve_m,
        six_month_return=six_m,
        three_month_return=three_m,
        monthly_avg_return=monthly_avg,
        volatility=vol,
        max_drawdown=mdd,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        var_95=var_95,
        alpha=alpha,
        beta=beta,
        tracking_error=te,
        information_ratio=ir,
        correlation=corr,
        positive_months_pct=pos_pct,
        best_month=best_month,
        worst_month=worst_month,
        win_loss_vs_cdi=win_loss,
        stability_index=si,
        vs_cdi=vs_cdi,
        vs_selic=vs_selic,
        vs_ipca=vs_ipca,
        vs_cdb=vs_cdb,
        vs_poupanca=vs_poupanca,
        monthly_returns=monthly_rets,
    )
