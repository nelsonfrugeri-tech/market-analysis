"""Tests for pure mathematical formulas in domain/metrics/formulas.py.

Uses synthetic data with manually verifiable results.
"""

from __future__ import annotations

import math

import pytest

from market_analysis.domain.metrics.formulas import (
    annualized_return,
    alpha_jensen,
    beta_coefficient,
    cumulative_return,
    daily_returns,
    downside_deviation,
    information_ratio,
    max_drawdown,
    monthly_returns_from_daily,
    pearson_correlation,
    sharpe_ratio,
    sortino_ratio,
    stability_index,
    tracking_error,
    var_parametric_95,
    volatility_annualized,
)


# -- cumulative_return --

class TestCumulativeReturn:
    def test_positive_return(self) -> None:
        assert cumulative_return(100.0, 110.0) == 10.0

    def test_negative_return(self) -> None:
        assert cumulative_return(100.0, 90.0) == -10.0

    def test_zero_start(self) -> None:
        assert cumulative_return(0.0, 100.0) == 0.0

    def test_no_change(self) -> None:
        assert cumulative_return(100.0, 100.0) == 0.0


# -- daily_returns --

class TestDailyReturns:
    def test_simple_series(self) -> None:
        navs = [100.0, 101.0, 102.01]
        rets = daily_returns(navs)
        assert len(rets) == 2
        assert rets[0] == pytest.approx(1.0, abs=0.01)
        assert rets[1] == pytest.approx(1.0, abs=0.01)

    def test_too_short(self) -> None:
        assert daily_returns([100.0]) == []
        assert daily_returns([]) == []

    def test_handles_zero_nav(self) -> None:
        navs = [0.0, 100.0, 101.0]
        rets = daily_returns(navs)
        # First pair skipped (0 nav), second pair ok
        assert len(rets) == 1


# -- annualized_return --

class TestAnnualizedReturn:
    def test_one_year(self) -> None:
        # 10% over 252 days = 10% annualized
        result = annualized_return(10.0, 252)
        assert result == pytest.approx(10.0, abs=0.1)

    def test_half_year(self) -> None:
        # 5% over 126 days ~ 10.25% annualized
        result = annualized_return(5.0, 126)
        assert result > 10.0

    def test_zero_days(self) -> None:
        assert annualized_return(10.0, 0) == 0.0


# -- volatility --

class TestVolatility:
    def test_constant_returns(self) -> None:
        rets = [0.1] * 100
        assert volatility_annualized(rets) == 0.0

    def test_nonzero_vol(self) -> None:
        rets = [1.0, -1.0] * 50
        vol = volatility_annualized(rets)
        assert vol > 0

    def test_too_few(self) -> None:
        assert volatility_annualized([1.0]) == 0.0


# -- downside_deviation --

class TestDownsideDeviation:
    def test_all_positive(self) -> None:
        rets = [1.0, 2.0, 3.0] * 20
        dd = downside_deviation(rets, target=0.0)
        assert dd == 0.0

    def test_mixed(self) -> None:
        rets = [1.0, -1.0] * 50
        dd = downside_deviation(rets, target=0.0)
        assert dd > 0


# -- sharpe_ratio --

class TestSharpeRatio:
    def test_positive(self) -> None:
        assert sharpe_ratio(10.0, 5.0, 10.0) == 0.5

    def test_zero_vol(self) -> None:
        assert sharpe_ratio(10.0, 5.0, 0.0) == 0.0

    def test_negative(self) -> None:
        assert sharpe_ratio(3.0, 5.0, 10.0) == -0.2


# -- sortino_ratio --

class TestSortinoRatio:
    def test_positive(self) -> None:
        assert sortino_ratio(10.0, 5.0, 8.0) == 0.625

    def test_zero_dd(self) -> None:
        assert sortino_ratio(10.0, 5.0, 0.0) == 0.0


# -- max_drawdown --

class TestMaxDrawdown:
    def test_no_drawdown(self) -> None:
        navs = [100, 101, 102, 103]
        assert max_drawdown(navs) == 0.0

    def test_simple_drawdown(self) -> None:
        navs = [100, 110, 99, 105]
        mdd = max_drawdown(navs)
        # Peak 110, trough 99 -> -10%
        assert mdd == pytest.approx(-10.0, abs=0.1)

    def test_too_short(self) -> None:
        assert max_drawdown([100]) == 0.0


# -- var_parametric_95 --

class TestVaR95:
    def test_insufficient_data(self) -> None:
        assert var_parametric_95([0.1] * 59) is None

    def test_sufficient_data(self) -> None:
        # Constant returns -> VaR near 0
        rets = [0.1] * 100
        var = var_parametric_95(rets)
        assert var is not None
        # With 0 variance, VaR = mean * sqrt(21)
        expected = 0.1 * math.sqrt(21)
        assert var == pytest.approx(expected, abs=0.01)


# -- beta --

class TestBeta:
    def test_insufficient_data(self) -> None:
        assert beta_coefficient([1.0] * 29, [1.0] * 29) is None

    def test_perfect_correlation(self) -> None:
        fund = [float(i) for i in range(30)]
        bench = [float(i) * 0.5 for i in range(30)]
        b = beta_coefficient(fund, bench)
        assert b is not None
        assert b == pytest.approx(2.0, abs=0.01)

    def test_zero_variance_benchmark(self) -> None:
        fund = list(range(30))
        bench = [1.0] * 30
        assert beta_coefficient(fund, bench) is None


# -- alpha --

class TestAlphaJensen:
    def test_zero_beta(self) -> None:
        assert alpha_jensen(10.0, 5.0, 8.0, 0.0) == 5.0

    def test_beta_one(self) -> None:
        # Alpha = 10 - (5 + 1*(8-5)) = 10 - 8 = 2
        assert alpha_jensen(10.0, 5.0, 8.0, 1.0) == 2.0


# -- tracking_error --

class TestTrackingError:
    def test_insufficient(self) -> None:
        assert tracking_error([1.0] * 29, [1.0] * 29) is None

    def test_identical_series(self) -> None:
        series = [0.1] * 30
        te = tracking_error(series, series)
        assert te == 0.0

    def test_divergent_series(self) -> None:
        fund = [0.1] * 30
        bench = [0.2] * 30
        te = tracking_error(fund, bench)
        # Constant difference -> TE = 0 (no variation in excess)
        assert te == 0.0


# -- information_ratio --

class TestInformationRatio:
    def test_positive(self) -> None:
        assert information_ratio(10.0, 5.0, 2.5) == 2.0

    def test_zero_te(self) -> None:
        assert information_ratio(10.0, 5.0, 0.0) is None

    def test_none_te(self) -> None:
        assert information_ratio(10.0, 5.0, None) is None


# -- pearson_correlation --

class TestPearsonCorrelation:
    def test_insufficient(self) -> None:
        assert pearson_correlation([1.0] * 29, [1.0] * 29) is None

    def test_perfect_positive(self) -> None:
        xs = [float(i) for i in range(30)]
        ys = [float(i) * 2 for i in range(30)]
        corr = pearson_correlation(xs, ys)
        assert corr is not None
        assert corr == pytest.approx(1.0, abs=0.001)

    def test_perfect_negative(self) -> None:
        xs = [float(i) for i in range(30)]
        ys = [float(-i) for i in range(30)]
        corr = pearson_correlation(xs, ys)
        assert corr is not None
        assert corr == pytest.approx(-1.0, abs=0.001)


# -- monthly_returns_from_daily --

class TestMonthlyReturns:
    def test_single_month(self) -> None:
        from datetime import date
        dates = [date(2026, 1, d) for d in range(2, 22)]
        navs = [1.00 + i * 0.001 for i in range(20)]
        rets = monthly_returns_from_daily(dates, navs)
        assert len(rets) == 1
        assert rets[0][0] == "2026-01"

    def test_empty(self) -> None:
        assert monthly_returns_from_daily([], []) == []


# -- stability_index --

class TestStabilityIndex:
    def test_perfect_fund(self) -> None:
        si = stability_index(100.0, 2.0, 0.0, 0.0)
        assert si == pytest.approx(1.0, abs=0.001)

    def test_terrible_fund(self) -> None:
        si = stability_index(0.0, 0.0, -10.0, 15.0)
        assert si == pytest.approx(0.0, abs=0.001)

    def test_moderate(self) -> None:
        si = stability_index(70.0, 1.0, -3.0, 5.0)
        assert 0.4 < si < 0.9
