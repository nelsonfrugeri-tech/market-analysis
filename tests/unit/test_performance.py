"""Tests for the performance calculation engine."""

import math
from datetime import date

import pytest

from market_analysis.application.performance import (
    calculate_return,
    calculate_volatility,
    compute_performance,
    determine_trend,
)
from market_analysis.domain.models.fund import FundDailyRecord


# -- Fixtures --


def _make_record(
    dt: date,
    nav: float = 1.0,
    equity: float = 1_000_000.0,
    **kwargs: float | int,
) -> FundDailyRecord:
    """Helper to create a FundDailyRecord with sensible defaults."""
    return FundDailyRecord(
        cnpj="43.121.002/0001-41",
        date=dt,
        nav=nav,
        equity=equity,
        total_value=kwargs.get("total_value", equity),
        deposits=kwargs.get("deposits", 0.0),
        withdrawals=kwargs.get("withdrawals", 0.0),
        shareholders=int(kwargs.get("shareholders", 1000)),
    )


@pytest.fixture
def sample_records() -> list[FundDailyRecord]:
    """Three days of records with known NAV values."""
    return [
        _make_record(date(2026, 1, 2), nav=1.000000),
        _make_record(date(2026, 1, 3), nav=1.001000),
        _make_record(date(2026, 1, 6), nav=1.002500),
    ]


@pytest.fixture
def flat_records() -> list[FundDailyRecord]:
    """Records with zero return."""
    return [
        _make_record(date(2026, 1, 2), nav=1.0),
        _make_record(date(2026, 1, 3), nav=1.0),
        _make_record(date(2026, 1, 6), nav=1.0),
    ]


# -- calculate_return --


class TestCalculateReturn:
    def test_positive_return(self) -> None:
        result = calculate_return(1.0, 1.05)
        assert result == pytest.approx(5.0)

    def test_negative_return(self) -> None:
        result = calculate_return(1.0, 0.95)
        assert result == pytest.approx(-5.0)

    def test_zero_return(self) -> None:
        result = calculate_return(1.0, 1.0)
        assert result == pytest.approx(0.0)

    def test_zero_start_nav(self) -> None:
        result = calculate_return(0.0, 1.0)
        assert result == 0.0

    def test_negative_start_nav(self) -> None:
        result = calculate_return(-1.0, 1.0)
        assert result == 0.0

    @pytest.mark.parametrize(
        "start,end,expected",
        [
            (100.0, 110.0, 10.0),
            (100.0, 90.0, -10.0),
            (1.5, 1.575, 5.0),
        ],
    )
    def test_various_returns(
        self, start: float, end: float, expected: float
    ) -> None:
        assert calculate_return(start, end) == pytest.approx(expected)


# -- calculate_volatility --


class TestCalculateVolatility:
    def test_empty_records(self) -> None:
        assert calculate_volatility([]) == 0.0

    def test_single_record(self) -> None:
        records = [_make_record(date(2026, 1, 2), nav=1.0)]
        assert calculate_volatility(records) == 0.0

    def test_flat_nav_zero_volatility(self, flat_records: list[FundDailyRecord]) -> None:
        vol = calculate_volatility(flat_records)
        assert vol == pytest.approx(0.0)

    def test_positive_volatility(self, sample_records: list[FundDailyRecord]) -> None:
        vol = calculate_volatility(sample_records)
        assert vol > 0.0

    def test_higher_dispersion_higher_volatility(self) -> None:
        low_vol = [
            _make_record(date(2026, 1, 2), nav=1.000),
            _make_record(date(2026, 1, 3), nav=1.001),
            _make_record(date(2026, 1, 6), nav=1.002),
        ]
        high_vol = [
            _make_record(date(2026, 1, 2), nav=1.000),
            _make_record(date(2026, 1, 3), nav=1.010),
            _make_record(date(2026, 1, 6), nav=0.990),
        ]
        assert calculate_volatility(high_vol) > calculate_volatility(low_vol)


# -- determine_trend --


class TestDetermineTrend:
    def test_upward_trend(self) -> None:
        records = [
            _make_record(date(2026, 1, d), nav=1.0 + d * 0.001)
            for d in range(2, 12)
        ]
        assert determine_trend(records) == "up"

    def test_downward_trend(self) -> None:
        records = [
            _make_record(date(2026, 1, d), nav=1.01 - d * 0.001)
            for d in range(2, 12)
        ]
        assert determine_trend(records) == "down"

    def test_flat_trend(self, flat_records: list[FundDailyRecord]) -> None:
        assert determine_trend(flat_records) == "flat"

    def test_single_record_flat(self) -> None:
        records = [_make_record(date(2026, 1, 2), nav=1.0)]
        assert determine_trend(records) == "flat"


# -- compute_performance --


class TestComputePerformance:
    def test_basic_computation(self, sample_records: list[FundDailyRecord]) -> None:
        benchmarks = {"selic": 0.05, "cdi": 0.04, "ipca": 0.03}
        perf = compute_performance(sample_records, benchmarks)

        assert perf.fund_cnpj == "43.121.002/0001-41"
        assert perf.period_start == date(2026, 1, 2)
        assert perf.period_end == date(2026, 1, 6)
        assert perf.return_pct == pytest.approx(0.25, abs=0.01)
        assert perf.vs_selic == pytest.approx(perf.return_pct - 0.05, abs=0.01)
        assert perf.vs_cdi == pytest.approx(perf.return_pct - 0.04, abs=0.01)

    def test_empty_records_raises(self) -> None:
        with pytest.raises(ValueError, match="empty records"):
            compute_performance([], {"selic": 0, "cdi": 0, "ipca": 0})

    def test_missing_benchmarks_default_zero(
        self, sample_records: list[FundDailyRecord]
    ) -> None:
        perf = compute_performance(sample_records, {})
        assert perf.benchmark_selic == 0.0
        assert perf.benchmark_cdi == 0.0
        assert perf.benchmark_ipca == 0.0

    def test_daily_records_included(
        self, sample_records: list[FundDailyRecord]
    ) -> None:
        perf = compute_performance(
            sample_records, {"selic": 0, "cdi": 0, "ipca": 0}
        )
        assert len(perf.daily_records) == 3
