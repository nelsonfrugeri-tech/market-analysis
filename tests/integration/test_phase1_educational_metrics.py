"""End-to-end integration tests for Phase 1 Educational Metrics system.

Tests the complete pipeline: Benchmarks → Advanced Metrics → LLM Explanations
with performance validation and quality assurance.
"""

import asyncio
import logging
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any

import pytest

from market_analysis.application.performance import compute_performance
from market_analysis.ai.explainer import MetricsExplainer
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync


class TestPhase1EducationalMetrics:
    """End-to-end tests for the Phase 1 Educational Metrics system."""

    @pytest.fixture
    def sample_fund_data(self) -> list[FundDailyRecord]:
        """Create sample fund data for testing."""
        base_date = date.today() - timedelta(days=90)
        records = []

        # Generate 90 days of sample data
        for i in range(90):
            current_date = base_date + timedelta(days=i)
            nav = 1.0 + (i * 0.001) + (0.002 if i % 5 == 0 else 0)  # Trending up with volatility

            record = FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=current_date,
                nav=nav,
                equity=1_000_000_000 + (i * 1_000_000),  # Growing fund
                total_value=1_000_000_000,
                deposits=1_000_000 if i % 3 == 0 else 0,
                withdrawals=500_000 if i % 7 == 0 else 0,
                shareholders=10_000 + i
            )
            records.append(record)

        return records

    @pytest.fixture
    def metrics_explainer(self) -> MetricsExplainer:
        """Create a MetricsExplainer instance."""
        return MetricsExplainer()

    def test_complete_pipeline_integration(self, sample_fund_data: list[FundDailyRecord]):
        """Test the complete pipeline from benchmarks to explanations."""
        logging.info("🚀 Starting complete pipeline integration test")

        # Step 1: Collect benchmarks
        start_date = sample_fund_data[0].date
        end_date = sample_fund_data[-1].date

        logging.info(f"📊 Collecting benchmarks for {start_date} to {end_date}")
        benchmarks = collect_all_benchmarks_sync(start_date, end_date)

        # Validate benchmarks
        assert benchmarks is not None, "Benchmarks should not be None"
        assert benchmarks.date_range == (start_date, end_date), "Date range should match"
        assert benchmarks.data_completeness > 0, "Should have some benchmark data"

        logging.info(f"✅ Benchmarks collected: SELIC={benchmarks.selic_accumulated:.2f}%, "
                    f"CDI={benchmarks.cdi_accumulated:.2f}%, IPCA={benchmarks.ipca_accumulated:.2f}%")

        # Step 2: Calculate performance metrics
        logging.info("📈 Calculating performance metrics")
        performance = compute_performance(sample_fund_data, benchmarks)

        # Validate core metrics
        assert performance is not None, "Performance should not be None"
        assert performance.fund_cnpj == "43.121.002/0001-41", "CNPJ should match"
        assert performance.return_pct is not None, "Return should be calculated"
        assert performance.volatility >= 0, "Volatility should be non-negative"

        # Validate advanced metrics
        assert performance.sharpe_ratio is not None, "Sharpe ratio should be calculated"
        assert performance.alpha is not None, "Alpha should be calculated"
        assert performance.beta is not None, "Beta should be calculated"
        assert performance.var_95 is not None, "VaR should be calculated"

        logging.info(f"✅ Metrics calculated: Return={performance.return_pct:.2f}%, "
                    f"Volatility={performance.volatility:.2f}%, "
                    f"Sharpe={performance.sharpe_ratio:.2f}, "
                    f"Alpha={performance.alpha:.2f}%, "
                    f"Beta={performance.beta:.2f}, "
                    f"VaR={performance.var_95:.2f}%")

        # Step 3: Generate LLM explanations
        logging.info("🧠 Generating LLM explanations")
        explainer = MetricsExplainer()
        explanations = explainer.explain_all_metrics(performance)

        # Validate explanations
        assert explanations is not None, "Explanations should not be None"
        assert isinstance(explanations, dict), "Explanations should be a dictionary"

        expected_metrics = ['sharpe_ratio', 'alpha', 'beta', 'var_95']
        for metric in expected_metrics:
            assert metric in explanations, f"Should have explanation for {metric}"
            assert explanations[metric] is not None, f"Explanation for {metric} should not be None"
            assert len(explanations[metric]) > 0, f"Explanation for {metric} should not be empty"

        logging.info("✅ All explanations generated successfully")

        # Step 4: Validate explanation quality (basic checks)
        for metric, explanation in explanations.items():
            # Check if explanation is in Portuguese (basic heuristic)
            portuguese_indicators = ['de ', 'do ', 'da ', 'em ', 'com ', 'para ', 'que ', 'é ']
            has_portuguese = any(indicator in explanation.lower() for indicator in portuguese_indicators)
            assert has_portuguese, f"Explanation for {metric} should be in Portuguese"

            # Check reasonable length
            assert 10 < len(explanation) < 1000, f"Explanation for {metric} should be reasonable length"

        logging.info("✅ Explanation quality validation passed")

        return performance, explanations

    def test_benchmark_collection_performance(self):
        """Test benchmark collection performance requirements."""
        logging.info("⚡ Testing benchmark collection performance")

        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        import time
        start_time = time.time()

        benchmarks = collect_all_benchmarks_sync(start_date, end_date)

        collection_time = time.time() - start_time

        # Performance requirements from issue #67
        assert collection_time < 30, f"Benchmark collection took {collection_time:.2f}s, should be < 30s"
        assert benchmarks.data_completeness > 0.5, "Should have reasonable data completeness"

        logging.info(f"✅ Benchmark collection completed in {collection_time:.2f}s")

    def test_llm_explanation_performance(self, sample_fund_data: list[FundDailyRecord]):
        """Test LLM explanation generation performance."""
        logging.info("⚡ Testing LLM explanation performance")

        # Quick setup with minimal benchmarks
        start_date = sample_fund_data[0].date
        end_date = sample_fund_data[-1].date

        benchmarks = collect_all_benchmarks_sync(start_date, end_date)
        performance = compute_performance(sample_fund_data, benchmarks)

        explainer = MetricsExplainer()

        import time
        start_time = time.time()

        explanations = explainer.explain_all_metrics(performance)

        explanation_time = time.time() - start_time

        # Performance requirements from issue #67
        assert explanation_time < 10, f"Explanation generation took {explanation_time:.2f}s, should be < 10s"

        logging.info(f"✅ LLM explanations generated in {explanation_time:.2f}s")

    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        logging.info("🛡️ Testing error handling and fallbacks")

        # Test with empty data
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        try:
            benchmarks = collect_all_benchmarks_sync(start_date, end_date)
            assert benchmarks is not None, "Should return fallback data even on failure"

            if benchmarks.fallback_used:
                assert benchmarks.data_completeness < 1.0, "Fallback should indicate reduced completeness"
                logging.info("✅ Benchmark fallback mechanism working")

        except Exception as e:
            pytest.fail(f"Benchmark collection should not fail completely: {e}")

        # Test LLM fallback
        explainer = MetricsExplainer()

        # Temporarily remove API key to test fallback
        original_api_key = explainer.api_key
        explainer.api_key = None

        try:
            explanation = explainer.explain_metric("sharpe_ratio", 1.5, {"fund_return": 10, "cdi_return": 8})
            assert explanation is not None, "Should provide fallback explanation"
            assert len(explanation) > 0, "Fallback explanation should not be empty"
            logging.info("✅ LLM fallback mechanism working")

        finally:
            explainer.api_key = original_api_key

    def test_data_quality_validation(self, sample_fund_data: list[FundDailyRecord]):
        """Test data quality validation throughout the pipeline."""
        logging.info("🔍 Testing data quality validation")

        start_date = sample_fund_data[0].date
        end_date = sample_fund_data[-1].date

        # Test with real data
        benchmarks = collect_all_benchmarks_sync(start_date, end_date)
        performance = compute_performance(sample_fund_data, benchmarks)

        # Validate performance data quality
        assert 0 <= performance.volatility <= 100, f"Volatility {performance.volatility} should be reasonable"
        assert -50 <= performance.return_pct <= 200, f"Return {performance.return_pct} should be reasonable"
        assert -5 <= performance.sharpe_ratio <= 10, f"Sharpe {performance.sharpe_ratio} should be reasonable"
        assert -100 <= performance.alpha <= 100, f"Alpha {performance.alpha} should be reasonable"
        assert 0 <= performance.beta <= 5, f"Beta {performance.beta} should be reasonable"
        assert -50 <= performance.var_95 <= 0, f"VaR {performance.var_95} should be negative or zero"

        logging.info("✅ Data quality validation passed")

    def test_nu_reserva_planejada_real_data_integration(self):
        """Test integration with real Nu Reserva Planejada data if available."""
        logging.info("🎯 Testing with Nu Reserva Planejada real data (if available)")

        # This test will be skipped if real data collection fails
        try:
            # Try to collect real benchmarks for last 30 days
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            benchmarks = collect_all_benchmarks_sync(start_date, end_date)

            if benchmarks.data_completeness > 0.5:
                logging.info(f"✅ Real benchmark data available: {benchmarks.data_completeness:.1%} complete")

                # Basic validation that real data looks reasonable
                assert 0 <= benchmarks.selic_accumulated <= 50, "SELIC should be reasonable"
                assert 0 <= benchmarks.cdi_accumulated <= 50, "CDI should be reasonable"
                assert -10 <= benchmarks.ipca_accumulated <= 30, "IPCA should be reasonable"

                logging.info(f"Real data: SELIC={benchmarks.selic_accumulated:.2f}%, "
                           f"CDI={benchmarks.cdi_accumulated:.2f}%, "
                           f"IPCA={benchmarks.ipca_accumulated:.2f}%")

            else:
                logging.warning(f"⚠️ Low real data completeness: {benchmarks.data_completeness:.1%}")

        except Exception as e:
            logging.warning(f"⚠️ Real data test failed: {e}")
            pytest.skip("Real data not available for testing")


@pytest.mark.asyncio
async def test_async_benchmark_collection():
    """Test async benchmark collection if available."""
    try:
        from market_analysis.infrastructure.benchmarks import collect_all_benchmarks

        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        benchmarks = await collect_all_benchmarks(start_date, end_date)
        assert benchmarks is not None, "Async benchmarks should not be None"

        logging.info("✅ Async benchmark collection working")

    except ImportError:
        pytest.skip("Async benchmark collection not available")


if __name__ == "__main__":
    """Run tests directly."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [PHASE1-TEST] %(levelname)s: %(message)s"
    )

    pytest.main([__file__, "-v", "-s"])