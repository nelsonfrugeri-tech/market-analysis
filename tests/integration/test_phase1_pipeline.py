"""End-to-end integration tests for Phase 1 - Educational Metrics pipeline.

Tests the complete flow:
1. Benchmark Collection (BCB APIs)
2. Advanced Metrics Calculation
3. LLM Explanations Generation (with fallback chain)
4. Integration with PDF Generator

Tests use sample Nu Reserva Planejada data and verify performance targets.
"""

import math
import time

import pytest
from datetime import date, timedelta

from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync
from market_analysis.infrastructure.benchmarks.data_models import BenchmarkData
from market_analysis.application.performance import compute_performance
from market_analysis.ai.explainer import MetricsExplainer, ExplanationResult
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance


def _make_benchmark(period_days: int = 30) -> BenchmarkData:
    """Create benchmark data scaled to the given period in days."""
    # Annualized rates (typical Brazilian market)
    selic_annual = 10.5
    cdi_annual = 10.2
    ipca_annual = 4.5

    # Scale to period (simple proportional, good enough for tests)
    factor = period_days / 365
    return BenchmarkData(
        date_range=(date(2024, 1, 1), date(2024, 1, 1) + timedelta(days=period_days)),
        selic_accumulated=round(selic_annual * factor, 4),
        cdi_accumulated=round(cdi_annual * factor, 4),
        ipca_accumulated=round(ipca_annual * factor, 4),
        selic_annual_rate=selic_annual,
        cdi_annual_rate=cdi_annual,
        cdb_estimated=round(9.7 * factor, 4),
        poupanca_estimated=round(6.0 * factor, 4),
        data_completeness=1.0,
        source_quality="complete",
    )


class TestPhase1Pipeline:
    """Integration tests for the complete Phase 1 metrics pipeline."""

    @pytest.fixture
    def sample_fund_data(self) -> list[FundDailyRecord]:
        """Create sample Nu Reserva Planejada fund data for testing."""
        base_date = date(2024, 1, 1)
        records = []

        for i in range(30):
            record_date = base_date + timedelta(days=i)
            nav = 1.0 + (i * 0.001)
            equity = 1000000 + (i * 1000)

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=record_date,
                nav=nav,
                equity=equity,
                total_value=equity * 0.95,
                deposits=5000.0,
                withdrawals=2000.0,
                shareholders=100 + i,
            ))

        return records

    def test_benchmark_collection_integration(self):
        """Test that benchmark collection works with real BCB APIs."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        benchmark_data = collect_all_benchmarks_sync(start_date, end_date)

        assert benchmark_data.date_range == (start_date, end_date)
        assert isinstance(benchmark_data.selic_accumulated, float)
        assert isinstance(benchmark_data.cdi_accumulated, float)
        assert isinstance(benchmark_data.ipca_accumulated, float)
        assert isinstance(benchmark_data.cdb_estimated, float)
        assert isinstance(benchmark_data.poupanca_estimated, float)

        # Reasonable values for ~1 month in Brazilian market
        assert 0.0 <= benchmark_data.selic_accumulated <= 5.0
        assert 0.0 <= benchmark_data.cdi_accumulated <= 5.0
        assert -2.0 <= benchmark_data.ipca_accumulated <= 5.0

        assert benchmark_data.cdb_estimated <= benchmark_data.cdi_accumulated
        assert benchmark_data.poupanca_estimated >= 0.0

    def test_advanced_metrics_calculation(self, sample_fund_data):
        """Test advanced metrics calculation with sample data."""
        benchmarks = _make_benchmark(period_days=30)

        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmarks,
            fund_name="Nu Reserva Planejada",
        )

        assert isinstance(performance, FundPerformance)
        assert performance.fund_cnpj == "43.121.002/0001-41"
        assert performance.fund_name == "Nu Reserva Planejada"
        assert performance.return_pct >= 0

        # Advanced metrics present and typed
        assert isinstance(performance.sharpe_ratio, float)
        assert isinstance(performance.alpha, float)
        assert isinstance(performance.beta, float)
        assert isinstance(performance.var_95, float)

        # Beta capped by implementation [0.1, 3.0]
        assert 0.1 <= performance.beta <= 3.0

    def test_llm_explanations_generation(self, sample_fund_data):
        """Test LLM explanation generation for metrics (uses fallback chain)."""
        benchmarks = _make_benchmark(period_days=30)
        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmarks,
        )

        explainer = MetricsExplainer()

        # Build metrics dict from performance
        metrics = {
            "sharpe_ratio": performance.sharpe_ratio,
            "alpha": performance.alpha,
            "beta": performance.beta,
            "var_95": performance.var_95,
        }

        results, stats = explainer.explain_all_sync(metrics, period="30 dias")

        # Should get results for all metrics
        assert len(results) == 4
        assert stats.total == 4

        for result in results:
            assert isinstance(result, ExplanationResult)
            assert len(result.text) > 0
            assert result.provider in ("anthropic", "ollama", "static", "cache")

    def test_full_pipeline_integration(self, sample_fund_data):
        """Test the complete pipeline from benchmarks to explanations."""
        benchmarks = _make_benchmark(period_days=30)

        # 1. Metrics
        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmarks,
            fund_name="Nu Reserva Planejada",
        )

        assert performance.fund_name == "Nu Reserva Planejada"
        assert performance.fund_cnpj == "43.121.002/0001-41"

        # Benchmark comparisons
        assert performance.vs_cdi == round(
            performance.return_pct - benchmarks.cdi_accumulated, 4
        )
        assert performance.vs_selic == round(
            performance.return_pct - benchmarks.selic_accumulated, 4
        )

        # Advanced metrics present
        assert performance.sharpe_ratio is not None
        assert performance.alpha is not None
        assert performance.beta is not None
        assert performance.var_95 is not None

        # 2. Explanations
        explainer = MetricsExplainer()
        metrics = {
            "sharpe_ratio": performance.sharpe_ratio,
            "alpha": performance.alpha,
            "beta": performance.beta,
            "var_95": performance.var_95,
        }
        results, stats = explainer.explain_all_sync(metrics, period="30 dias")

        assert len(results) == 4
        assert all(len(r.text) > 0 for r in results)

    @pytest.mark.performance
    def test_pipeline_performance_targets(self, sample_fund_data):
        """Test that pipeline meets performance targets."""
        start = time.time()

        benchmarks = _make_benchmark(period_days=30)
        performance = compute_performance(sample_fund_data, benchmarks)

        metrics = {
            "sharpe_ratio": performance.sharpe_ratio,
            "alpha": performance.alpha,
            "beta": performance.beta,
            "var_95": performance.var_95,
        }
        explainer = MetricsExplainer()
        results, stats = explainer.explain_all_sync(metrics, period="30 dias")

        elapsed = time.time() - start

        # Computation-only should be fast; LLM calls may add time but
        # static fallback (no API key) should be instant
        assert elapsed < 30.0, f"Pipeline took {elapsed:.2f}s, expected < 30s"
        assert len(results) == 4
        assert all(r.text for r in results)

    def test_error_handling_and_fallbacks(self):
        """Test that pipeline handles errors gracefully with fallbacks."""
        # Empty records -> ValueError
        empty_records: list[FundDailyRecord] = []
        benchmarks = _make_benchmark(period_days=30)

        with pytest.raises(ValueError, match="Cannot compute performance with empty records"):
            compute_performance(empty_records, benchmarks)

        # LLM fallback: explain_metric is async, test via explain_all_sync
        explainer = MetricsExplainer()
        metrics = {"sharpe_ratio": 1.25}
        results, stats = explainer.explain_all_sync(metrics, period="30 dias")

        assert len(results) == 1
        r = results[0]
        assert isinstance(r, ExplanationResult)
        assert len(r.text) > 0
        # Without API keys, should fall back to static
        assert r.provider in ("anthropic", "ollama", "static", "cache")

    def test_nu_reserva_planejada_specific_validation(self, sample_fund_data):
        """Test specific validation for Nu Reserva Planejada fund."""
        benchmarks = _make_benchmark(period_days=30)

        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmarks,
            fund_name="Nu Reserva Planejada",
        )

        assert performance.fund_cnpj == "43.121.002/0001-41"
        assert "Nu Reserva" in performance.fund_name

        # With synthetic linear data, volatility is near-zero so Sharpe
        # can be extreme. Just verify it's a valid float and the formula ran.
        assert isinstance(performance.sharpe_ratio, float)
        assert not math.isnan(performance.sharpe_ratio)
        assert not math.isinf(performance.sharpe_ratio)

        # Beta capped by implementation
        assert 0.1 <= performance.beta <= 3.0

        # VaR: for 30 data points, may return 0.0 (not enough for parametric)
        assert -20.0 <= performance.var_95 <= 2.0
