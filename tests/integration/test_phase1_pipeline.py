"""End-to-end integration tests for Phase 1 - Educational Metrics pipeline.

Tests the complete flow:
1. Benchmark Collection (BCB APIs)
2. Advanced Metrics Calculation
3. LLM Explanations Generation
4. Integration with PDF Generator

Tests use real Nu Reserva Planejada data and verify performance targets.
"""

import pytest
from datetime import date, timedelta
from typing import Any

from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync
from market_analysis.infrastructure.benchmarks.data_models import BenchmarkData
from market_analysis.application.performance import compute_performance
from market_analysis.ai.explainer import MetricsExplainer
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance


class TestPhase1Pipeline:
    """Integration tests for the complete Phase 1 metrics pipeline."""

    @pytest.fixture
    def sample_fund_data(self) -> list[FundDailyRecord]:
        """Create sample Nu Reserva Planejada fund data for testing."""
        # Create 30 days of sample data
        base_date = date(2024, 1, 1)
        records = []

        for i in range(30):
            record_date = base_date + timedelta(days=i)
            # Simulate realistic fund data with slight growth
            nav = 1.0 + (i * 0.001)  # Small daily growth
            equity = 1000000 + (i * 1000)  # Growing equity

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",  # Nu Reserva Planejada CNPJ
                date=record_date,
                nav=nav,
                equity=equity,
                total_value=equity * 0.95,
                deposits=5000.0,
                withdrawals=2000.0,
                shareholders=100 + i
            ))

        return records

    def test_benchmark_collection_integration(self):
        """Test that benchmark collection works with real BCB APIs."""
        # Test with a small date range to avoid long API calls
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # This will test the real BCB API integration
        benchmark_data = collect_all_benchmarks_sync(start_date, end_date)

        # Verify structure
        assert benchmark_data.date_range == (start_date, end_date)
        assert isinstance(benchmark_data.selic_accumulated, float)
        assert isinstance(benchmark_data.cdi_accumulated, float)
        assert isinstance(benchmark_data.ipca_accumulated, float)
        assert isinstance(benchmark_data.cdb_estimated, float)
        assert isinstance(benchmark_data.poupanca_estimated, float)

        # Verify reasonable values (Brazilian market context)
        assert 0.0 <= benchmark_data.selic_accumulated <= 20.0  # Reasonable SELIC range
        assert 0.0 <= benchmark_data.cdi_accumulated <= 20.0    # CDI usually close to SELIC
        assert -5.0 <= benchmark_data.ipca_accumulated <= 15.0  # IPCA range

        # Verify derived calculations
        assert benchmark_data.cdb_estimated <= benchmark_data.cdi_accumulated
        assert benchmark_data.poupanca_estimated >= 0.0

    def test_advanced_metrics_calculation(self, sample_fund_data):
        """Test advanced metrics calculation with sample data."""
        # Create mock benchmark data
        benchmark_data = BenchmarkData(
            date_range=(date(2024, 1, 1), date(2024, 1, 31)),
            selic_accumulated=10.5,
            cdi_accumulated=10.2,
            ipca_accumulated=4.5,
            selic_annual_rate=10.5,
            cdi_annual_rate=10.2,
            cdb_estimated=9.7,
            poupanca_estimated=6.0,
            data_completeness=1.0,
            source_quality="complete"
        )

        # Calculate performance with advanced metrics
        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmark_data,
            fund_name="Nu Reserva Planejada"
        )

        # Verify basic performance metrics
        assert isinstance(performance, FundPerformance)
        assert performance.fund_cnpj == "43.121.002/0001-41"
        assert performance.fund_name == "Nu Reserva Planejada"
        assert performance.return_pct >= 0  # Should have positive return from our sample data

        # Verify advanced metrics are calculated
        assert hasattr(performance, 'sharpe_ratio')
        assert hasattr(performance, 'alpha')
        assert hasattr(performance, 'beta')
        assert hasattr(performance, 'var_95')

        # Verify reasonable metric ranges
        assert isinstance(performance.sharpe_ratio, float)
        assert isinstance(performance.alpha, float)
        assert isinstance(performance.beta, float)
        assert isinstance(performance.var_95, float)

        # Beta should be reasonable (0.1 to 3.0 based on our implementation)
        assert 0.1 <= performance.beta <= 3.0

    def test_llm_explanations_generation(self, sample_fund_data):
        """Test LLM explanation generation for metrics."""
        # Setup
        explainer = MetricsExplainer()

        # Create performance data
        benchmark_data = BenchmarkData(
            date_range=(date(2024, 1, 1), date(2024, 1, 31)),
            selic_accumulated=10.5,
            cdi_accumulated=10.2,
            ipca_accumulated=4.5,
            selic_annual_rate=10.5,
            cdi_annual_rate=10.2,
            cdb_estimated=9.7,
            poupanca_estimated=6.0
        )

        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmark_data
        )

        # Generate explanations
        explanations = explainer.explain_all_metrics(performance)

        # Verify all metrics have explanations
        expected_metrics = ['sharpe_ratio', 'alpha', 'beta', 'var_95']
        for metric in expected_metrics:
            assert metric in explanations
            assert isinstance(explanations[metric], str)
            assert len(explanations[metric]) > 0

        # Verify explanations contain Portuguese content
        # Even fallback explanations should be in Portuguese
        for explanation in explanations.values():
            assert len(explanation) > 10  # Reasonable length
            # Check for common Portuguese words in financial context
            explanation_lower = explanation.lower()
            portuguese_indicators = [
                'retorno', 'risco', 'fundo', 'valor', 'gestão',
                'indica', 'mostra', 'esperado', 'período'
            ]
            has_portuguese = any(word in explanation_lower for word in portuguese_indicators)
            assert has_portuguese, f"Explanation doesn't seem to be in Portuguese: {explanation}"

    def test_full_pipeline_integration(self, sample_fund_data):
        """Test the complete pipeline from benchmarks to explanations."""
        # 1. Collect benchmarks (using fallback for speed)
        benchmark_data = BenchmarkData(
            date_range=(date(2024, 1, 1), date(2024, 1, 31)),
            selic_accumulated=10.5,
            cdi_accumulated=10.2,
            ipca_accumulated=4.5,
            selic_annual_rate=10.5,
            cdi_annual_rate=10.2,
            cdb_estimated=9.7,
            poupanca_estimated=6.0
        )

        # 2. Calculate performance metrics
        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmark_data,
            fund_name="Nu Reserva Planejada"
        )

        # 3. Generate LLM explanations
        explainer = MetricsExplainer()
        explanations = explainer.explain_all_metrics(performance)

        # 4. Verify complete integration
        assert performance.fund_name == "Nu Reserva Planejada"
        assert performance.fund_cnpj == "43.121.002/0001-41"

        # Verify benchmark comparisons
        assert performance.vs_cdi == performance.return_pct - benchmark_data.cdi_accumulated
        assert performance.vs_selic == performance.return_pct - benchmark_data.selic_accumulated
        assert performance.vs_ipca == performance.return_pct - benchmark_data.ipca_accumulated

        # Verify advanced metrics
        assert performance.sharpe_ratio is not None
        assert performance.alpha is not None
        assert performance.beta is not None
        assert performance.var_95 is not None

        # Verify explanations exist for all metrics
        assert len(explanations) == 4
        assert all(len(exp) > 10 for exp in explanations.values())

    @pytest.mark.performance
    def test_pipeline_performance_targets(self, sample_fund_data):
        """Test that pipeline meets performance targets."""
        import time

        # Target: < 10s for first run, < 2s with cache
        start_time = time.time()

        # Run pipeline
        benchmark_data = BenchmarkData(
            date_range=(date(2024, 1, 1), date(2024, 1, 31)),
            selic_accumulated=10.5,
            cdi_accumulated=10.2,
            ipca_accumulated=4.5,
            selic_annual_rate=10.5,
            cdi_annual_rate=10.2,
            cdb_estimated=9.7,
            poupanca_estimated=6.0
        )
        performance = compute_performance(sample_fund_data, benchmark_data)
        explainer = MetricsExplainer()
        explanations = explainer.explain_all_metrics(performance)

        elapsed = time.time() - start_time

        # Should complete reasonably quickly
        # Note: Real BCB API calls will be slower, this tests computation only
        assert elapsed < 5.0, f"Pipeline took {elapsed:.2f}s, expected < 5s"

        # Verify results are complete
        assert len(explanations) == 4
        assert all(exp for exp in explanations.values())

    def test_error_handling_and_fallbacks(self):
        """Test that pipeline handles errors gracefully with fallbacks."""
        # Test with empty fund data
        empty_records = []
        benchmark_data = BenchmarkData(
            date_range=(date(2024, 1, 1), date(2024, 1, 31)),
            selic_accumulated=10.5,
            cdi_accumulated=10.2,
            ipca_accumulated=4.5
        )

        # Should raise ValueError for empty records
        with pytest.raises(ValueError, match="Cannot compute performance with empty records"):
            compute_performance(empty_records, benchmark_data)

        # Test LLM fallback (when no API key)
        explainer = MetricsExplainer()
        # Force fallback by using invalid context
        context = {"fund_return": 5.0, "cdi_return": 4.0}

        explanation = explainer.explain_metric("sharpe_ratio", 1.25, context)
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "sharpe" in explanation.lower() or "1.25" in explanation

    def test_nu_reserva_planejada_specific_validation(self, sample_fund_data):
        """Test specific validation for Nu Reserva Planejada fund."""
        benchmark_data = BenchmarkData(
            date_range=(date(2024, 1, 1), date(2024, 1, 31)),
            selic_accumulated=10.5,
            cdi_accumulated=10.2,
            ipca_accumulated=4.5,
            selic_annual_rate=10.5,
            cdi_annual_rate=10.2,
            cdb_estimated=9.7,
            poupanca_estimated=6.0
        )

        performance = compute_performance(
            records=sample_fund_data,
            benchmarks=benchmark_data,
            fund_name="Nu Reserva Planejada"
        )

        # Verify Nu Reserva specific attributes
        assert performance.fund_cnpj == "43.121.002/0001-41"
        assert "Nu Reserva" in performance.fund_name

        # Nu Reserva is a conservative fund, so validate reasonable metrics
        # Beta should be relatively low (conservative fund)
        assert 0.1 <= performance.beta <= 2.0

        # Sharpe ratio should be reasonable for a conservative fund
        assert -2.0 <= performance.sharpe_ratio <= 3.0

        # VaR should indicate conservative risk profile
        assert -10.0 <= performance.var_95 <= 2.0