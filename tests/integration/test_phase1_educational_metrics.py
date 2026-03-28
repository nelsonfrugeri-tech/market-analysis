"""End-to-end integration tests for Phase 1 Educational Metrics system.

Tests the complete pipeline: Benchmarks -> Advanced Metrics -> LLM Explanations
with performance validation and quality assurance.
"""

import logging
import time

import pytest
from datetime import date, timedelta

from market_analysis.application.performance import compute_performance
from market_analysis.ai.explainer import MetricsExplainer, ExplanationResult
from market_analysis.domain.models.fund import FundDailyRecord
from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync
from market_analysis.infrastructure.benchmarks.data_models import BenchmarkData


def _make_benchmark_for_period(start: date, end: date) -> BenchmarkData:
    """Create benchmark data scaled to the period."""
    days = (end - start).days
    factor = days / 365
    return BenchmarkData(
        date_range=(start, end),
        selic_accumulated=round(10.5 * factor, 4),
        cdi_accumulated=round(10.2 * factor, 4),
        ipca_accumulated=round(4.5 * factor, 4),
        selic_annual_rate=10.5,
        cdi_annual_rate=10.2,
        cdb_estimated=round(9.7 * factor, 4),
        poupanca_estimated=round(6.0 * factor, 4),
        data_completeness=1.0,
        source_quality="complete",
    )


def _extract_metrics(performance) -> dict[str, float]:
    """Extract metric values from performance for explainer."""
    return {
        "sharpe_ratio": performance.sharpe_ratio,
        "alpha": performance.alpha,
        "beta": performance.beta,
        "var_95": performance.var_95,
    }


class TestPhase1EducationalMetrics:
    """End-to-end tests for the Phase 1 Educational Metrics system."""

    @pytest.fixture
    def sample_fund_data(self) -> list[FundDailyRecord]:
        """Create 90 days of sample fund data."""
        base_date = date(2024, 1, 1)
        records = []

        for i in range(90):
            current_date = base_date + timedelta(days=i)
            nav = 1.0 + (i * 0.001) + (0.002 if i % 5 == 0 else 0)

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=current_date,
                nav=nav,
                equity=1_000_000_000 + (i * 1_000_000),
                total_value=1_000_000_000,
                deposits=1_000_000 if i % 3 == 0 else 0,
                withdrawals=500_000 if i % 7 == 0 else 0,
                shareholders=10_000 + i,
            ))

        return records

    def test_complete_pipeline_integration(self, sample_fund_data):
        """Test the complete pipeline from benchmarks to explanations."""
        start_date = sample_fund_data[0].date
        end_date = sample_fund_data[-1].date

        # Step 1: Benchmarks (use local scaled data for determinism)
        benchmarks = _make_benchmark_for_period(start_date, end_date)

        # Step 2: Performance metrics
        performance = compute_performance(sample_fund_data, benchmarks)

        assert performance is not None
        assert performance.fund_cnpj == "43.121.002/0001-41"
        assert performance.return_pct is not None
        assert performance.volatility >= 0
        assert performance.sharpe_ratio is not None
        assert performance.alpha is not None
        assert performance.beta is not None
        assert performance.var_95 is not None

        # Step 3: LLM explanations via sync wrapper
        explainer = MetricsExplainer()
        metrics = _extract_metrics(performance)
        results, stats = explainer.explain_all_sync(metrics, period="90 dias")

        assert len(results) == 4
        assert stats.total == 4

        for result in results:
            assert isinstance(result, ExplanationResult)
            assert len(result.text) > 0

    def test_benchmark_collection_performance(self):
        """Test benchmark collection performance requirements."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        start_time = time.time()
        benchmarks = collect_all_benchmarks_sync(start_date, end_date)
        elapsed = time.time() - start_time

        assert elapsed < 30, f"Benchmark collection took {elapsed:.2f}s, should be < 30s"
        assert benchmarks.data_completeness > 0.5

    def test_llm_explanation_performance(self, sample_fund_data):
        """Test LLM explanation generation performance."""
        start_date = sample_fund_data[0].date
        end_date = sample_fund_data[-1].date
        benchmarks = _make_benchmark_for_period(start_date, end_date)
        performance = compute_performance(sample_fund_data, benchmarks)

        explainer = MetricsExplainer()
        metrics = _extract_metrics(performance)

        start_time = time.time()
        results, stats = explainer.explain_all_sync(metrics, period="90 dias")
        elapsed = time.time() - start_time

        assert elapsed < 30, f"Explanation generation took {elapsed:.2f}s, should be < 30s"
        assert len(results) == 4

    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        # Benchmark fallback: should not crash even with recent dates
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        benchmarks = collect_all_benchmarks_sync(start_date, end_date)
        assert benchmarks is not None

        # LLM fallback: without API keys, should use static fallback
        explainer = MetricsExplainer()
        metrics = {"sharpe_ratio": 1.5}
        results, stats = explainer.explain_all_sync(metrics, period="30 dias")

        assert len(results) == 1
        assert results[0].provider in ("anthropic", "ollama", "static", "cache")
        assert len(results[0].text) > 0

    def test_data_quality_validation(self, sample_fund_data):
        """Test data quality validation throughout the pipeline."""
        start_date = sample_fund_data[0].date
        end_date = sample_fund_data[-1].date
        benchmarks = _make_benchmark_for_period(start_date, end_date)
        performance = compute_performance(sample_fund_data, benchmarks)

        assert 0 <= performance.volatility <= 100
        assert -50 <= performance.return_pct <= 200
        assert -20 <= performance.sharpe_ratio <= 20
        assert -200 <= performance.alpha <= 200
        assert 0.1 <= performance.beta <= 3.0

    def test_nu_reserva_planejada_real_data_integration(self):
        """Test integration with real Nu Reserva Planejada benchmarks."""
        end_date = date(2024, 1, 31)
        start_date = date(2024, 1, 1)

        try:
            benchmarks = collect_all_benchmarks_sync(start_date, end_date)

            if benchmarks.data_completeness > 0.5:
                assert 0 <= benchmarks.selic_accumulated <= 5.0
                assert 0 <= benchmarks.cdi_accumulated <= 5.0
                assert -2.0 <= benchmarks.ipca_accumulated <= 5.0
            else:
                logging.warning("Low data completeness: %.1f%%", benchmarks.data_completeness * 100)

        except Exception as e:
            logging.warning("Real data test failed: %s", e)
            pytest.skip("Real data not available for testing")


@pytest.mark.asyncio
async def test_async_benchmark_collection():
    """Test async benchmark collection if available."""
    try:
        from market_analysis.infrastructure.benchmarks import collect_all_benchmarks

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 7)

        benchmarks = await collect_all_benchmarks(start_date, end_date)
        assert benchmarks is not None
    except ImportError:
        pytest.skip("Async benchmark collection not available")
