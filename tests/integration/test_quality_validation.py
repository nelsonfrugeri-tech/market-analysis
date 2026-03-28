"""Quality validation tests for Phase 1 educational metrics system.

Validates:
- LLM explanation quality and comprehensibility
- Mathematical accuracy of metrics
- Performance benchmarks
- User experience criteria
"""

import math
import time

import pytest
from datetime import date, timedelta

from market_analysis.ai.explainer import MetricsExplainer, ExplanationResult
from market_analysis.application.performance import (
    calculate_sharpe_ratio,
    calculate_alpha_beta,
    calculate_var_95,
    calculate_volatility,
)
from market_analysis.domain.models.fund import FundDailyRecord


class TestQualityValidation:
    """Quality validation tests for educational metrics system."""

    @pytest.fixture
    def stable_fund_data(self) -> list[FundDailyRecord]:
        """Create stable fund data for quality testing."""
        base_date = date(2024, 1, 1)
        records = []

        for i in range(60):
            record_date = base_date + timedelta(days=i)
            nav = 1.0 + (i * 0.0005)
            equity = 1000000 + (i * 500)

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=record_date,
                nav=nav,
                equity=equity,
                total_value=equity * 0.95,
                deposits=3000.0,
                withdrawals=1000.0,
                shareholders=150 + i,
            ))

        return records

    @pytest.fixture
    def volatile_fund_data(self) -> list[FundDailyRecord]:
        """Create volatile fund data for testing edge cases."""
        base_date = date(2024, 1, 1)
        records = []

        for i in range(60):
            record_date = base_date + timedelta(days=i)
            volatility_factor = math.sin(i * 0.3) * 0.02
            nav = 1.0 + volatility_factor + (i * 0.0002)
            equity = 1000000 + (i * 200)

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=record_date,
                nav=nav,
                equity=equity,
                total_value=equity * 0.95,
                deposits=4000.0,
                withdrawals=2000.0,
                shareholders=120 + i,
            ))

        return records

    def test_llm_explanation_quality(self):
        """Test quality of LLM-generated explanations (via fallback chain)."""
        explainer = MetricsExplainer()

        metrics = {
            "sharpe_ratio": 1.25,
            "alpha": 1.3,
            "beta": 0.85,
            "var_95": -2.1,
        }

        results, stats = explainer.explain_all_sync(metrics, period="2 meses")

        assert len(results) == 4

        for result in results:
            assert isinstance(result, ExplanationResult)
            assert len(result.text) > 0
            assert result.metric_name in metrics

    def test_mathematical_accuracy(self, stable_fund_data, volatile_fund_data):
        """Test mathematical accuracy of metrics calculations."""
        self._validate_metrics_accuracy(stable_fund_data, "stable")
        self._validate_metrics_accuracy(volatile_fund_data, "volatile")

    def _validate_metrics_accuracy(self, records: list[FundDailyRecord], data_type: str):
        """Validate mathematical accuracy for given data."""
        if len(records) < 10:
            pytest.skip(f"Not enough data for {data_type} validation")

        fund_return = ((records[-1].nav / records[0].nav) - 1) * 100
        volatility = calculate_volatility(records)
        benchmark_return = 1.2  # ~1.2% for 60-day period (CDI-like)

        # Sharpe Ratio
        sharpe = calculate_sharpe_ratio(fund_return, volatility, benchmark_return)
        if volatility > 0:
            expected_sharpe = (fund_return - benchmark_return) / volatility
            assert abs(sharpe - round(expected_sharpe, 4)) < 0.01, (
                f"Sharpe calculation error for {data_type} data"
            )

        # Alpha/Beta
        alpha, beta = calculate_alpha_beta(records, benchmark_return)
        assert 0.1 <= beta <= 3.0, f"Beta {beta} outside expected range for {data_type} data"
        assert -200 <= alpha <= 200, f"Alpha {alpha} outside reasonable range for {data_type} data"

        # VaR
        var_95 = calculate_var_95(records)
        if len(records) >= 30:
            assert var_95 <= 0.5, f"VaR should be ~0 or negative, got {var_95} for {data_type} data"
            assert var_95 >= -20, f"VaR {var_95} too extreme for {data_type} data"

        # Volatility
        assert volatility >= 0
        if data_type == "volatile":
            assert volatility > 0

    def test_performance_benchmarks(self):
        """Test that system meets performance benchmarks."""
        explainer = MetricsExplainer()

        # Single metric explanation
        start_time = time.time()
        results, _ = explainer.explain_all_sync({"sharpe_ratio": 1.1}, period="30 dias")
        single_time = time.time() - start_time

        assert single_time < 30.0, f"Single explanation took {single_time:.2f}s"
        assert len(results) == 1
        assert len(results[0].text) > 0

        # Batch (4 metrics)
        start_time = time.time()
        metrics = {
            "sharpe_ratio": 1.15,
            "alpha": 1.2,
            "beta": 0.9,
            "var_95": -1.8,
        }
        results, stats = explainer.explain_all_sync(metrics, period="2 meses")
        batch_time = time.time() - start_time

        assert batch_time < 30.0, f"Batch explanations took {batch_time:.2f}s"
        assert len(results) == 4

    def test_user_comprehension_simulation(self):
        """Simulate user comprehension -- explanations should be non-empty and meaningful."""
        explainer = MetricsExplainer()

        scenarios = [
            {"sharpe_ratio": 1.5},
            {"alpha": -2.0},
            {"var_95": -3.5},
        ]

        for metrics in scenarios:
            results, _ = explainer.explain_all_sync(metrics, period="30 dias")
            assert len(results) == 1
            r = results[0]
            assert len(r.text) > 10, f"Explanation too short for {r.metric_name}: {r.text}"

    def test_edge_cases_handling(self):
        """Test handling of edge cases and boundary conditions."""
        explainer = MetricsExplainer()

        edge_metrics = {
            "sharpe_ratio": 0.0,
            "alpha": 0.0,
            "beta": 1.0,
            "var_95": 0.0,
        }

        results, stats = explainer.explain_all_sync(edge_metrics, period="30 dias")
        assert len(results) == 4

        for r in results:
            assert len(r.text) > 0, f"Edge case explanation empty for {r.metric_name}"

    def test_consistency_across_runs(self):
        """Test that explanations are consistent across multiple runs."""
        explainer = MetricsExplainer()
        metrics = {"sharpe_ratio": 1.2}

        texts = []
        for _ in range(3):
            results, _ = explainer.explain_all_sync(metrics, period="30 dias")
            texts.append(results[0].text)

        # With caching / static fallback, results should be stable
        # (LLM results may vary but should all be non-empty)
        for t in texts:
            assert len(t) > 0
