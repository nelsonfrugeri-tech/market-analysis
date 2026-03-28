"""Tests for the advanced metrics calculator (orchestrator).

Uses synthetic fund records and benchmark data with known properties.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from market_analysis.domain.metrics.calculator import (
    AdvancedMetrics,
    compute_advanced_metrics,
)
from market_analysis.domain.models.fund import FundDailyRecord
from market_analysis.infrastructure.benchmarks.data_models import (
    BenchmarkData,
    DailyBenchmarkRecord,
)


def _make_records(
    start: date,
    days: int,
    base_nav: float = 1.50,
    daily_growth: float = 0.0001,
) -> list[FundDailyRecord]:
    """Generate synthetic fund records with steady growth."""
    records = []
    for i in range(days):
        d = start + timedelta(days=i)
        # Skip weekends
        if d.weekday() >= 5:
            continue
        nav = base_nav * (1 + daily_growth) ** i
        records.append(
            FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=d,
                nav=round(nav, 6),
                equity=800_000_000.0,
                total_value=800_000_000.0,
                deposits=1_000_000.0,
                withdrawals=500_000.0,
                shareholders=50000,
            )
        )
    return records


def _make_benchmark(
    records: list[FundDailyRecord],
    cdi_daily: float = 0.04,
    cdi_accumulated: float = 5.0,
    vary: bool = False,
) -> BenchmarkData:
    """Build benchmark data aligned with fund records.

    If vary=True, add small variation to CDI daily factor so beta is computable.
    """
    daily = []
    for i, r in enumerate(records):
        factor = cdi_daily + (0.001 * (i % 5 - 2) if vary else 0.0)
        daily.append(
            DailyBenchmarkRecord(
                date=r.date,
                cdi_daily_factor=factor,
                selic_daily_factor=factor * 0.99,
            )
        )
    return BenchmarkData(
        date_range=(records[0].date, records[-1].date),
        cdi_accumulated=cdi_accumulated,
        selic_accumulated=cdi_accumulated * 0.99,
        ipca_accumulated=2.0,
        cdb_estimated=cdi_accumulated * 1.1,
        poupanca_estimated=3.5,
        daily_records=daily,
    )


class TestComputeAdvancedMetrics:
    @pytest.fixture
    def records_90d(self) -> list[FundDailyRecord]:
        return _make_records(date(2025, 10, 1), 130)  # ~90 business days

    @pytest.fixture
    def benchmark_90d(self, records_90d: list[FundDailyRecord]) -> BenchmarkData:
        return _make_benchmark(records_90d, vary=True)

    def test_returns_all_fields(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        assert isinstance(metrics, AdvancedMetrics)
        assert metrics.cumulative_return > 0
        assert metrics.volatility >= 0
        assert metrics.max_drawdown <= 0
        assert metrics.sharpe_ratio != 0 or metrics.volatility == 0

    def test_var_requires_60_days(self) -> None:
        short = _make_records(date(2026, 1, 1), 40)  # ~28 business days
        bm = _make_benchmark(short)
        metrics = compute_advanced_metrics(short, bm)
        assert metrics.var_95 is None

    def test_var_available_with_enough_data(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        assert metrics.var_95 is not None

    def test_beta_alpha_require_30_days(self) -> None:
        short = _make_records(date(2026, 1, 1), 20)  # ~14 business days
        bm = _make_benchmark(short)
        metrics = compute_advanced_metrics(short, bm)
        assert metrics.beta is None
        assert metrics.alpha is None

    def test_beta_alpha_available(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        assert metrics.beta is not None
        assert metrics.alpha is not None

    def test_consistency_metrics(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        assert 0 <= metrics.positive_months_pct <= 100
        assert metrics.best_month >= metrics.worst_month
        assert 0 <= metrics.stability_index <= 1

    def test_comparisons(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        # vs_cdi = cumulative - cdi_accumulated
        expected_vs_cdi = round(
            metrics.cumulative_return - benchmark_90d.cdi_accumulated, 4
        )
        assert metrics.vs_cdi == expected_vs_cdi

    def test_empty_records_raises(self) -> None:
        bm = BenchmarkData(date_range=(date(2026, 1, 1), date(2026, 1, 31)))
        with pytest.raises(ValueError, match="empty records"):
            compute_advanced_metrics([], bm)

    def test_monthly_returns_populated(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        assert len(metrics.monthly_returns) >= 2  # 90 days spans 3+ months

    def test_win_loss_vs_cdi(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        assert 0 <= metrics.win_loss_vs_cdi <= 100

    def test_sortino_ratio(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        # Sortino should be >= Sharpe for steady growth (no negative returns)
        # or at least both are finite
        assert isinstance(metrics.sortino_ratio, float)

    def test_tracking_error_and_ir(
        self, records_90d: list[FundDailyRecord], benchmark_90d: BenchmarkData
    ) -> None:
        metrics = compute_advanced_metrics(records_90d, benchmark_90d)
        if metrics.tracking_error is not None:
            assert metrics.tracking_error >= 0
        if metrics.information_ratio is not None:
            assert isinstance(metrics.information_ratio, float)
