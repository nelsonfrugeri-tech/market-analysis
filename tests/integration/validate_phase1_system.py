#!/usr/bin/env python3
"""Phase 1 Educational Metrics System Validation Script.

Quick validation script to test all Phase 1 components:
- Enhanced benchmark collection (BCB + derived rates)
- Advanced metrics calculation (Sharpe, Alpha, Beta, VaR)
- LLM educational explanations (Claude API + fallback)
- Performance and quality validation

Usage: python validate_phase1_system.py [--verbose]
"""

import logging
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from market_analysis.ai.explainer import MetricsExplainer
from market_analysis.application.performance import compute_performance
from market_analysis.domain.models.fund import FundDailyRecord
from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [PHASE1-VALIDATOR] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_sample_data() -> list[FundDailyRecord]:
    """Create sample Nu Reserva Planejada data for testing."""
    logging.info("📊 Creating sample fund data...")

    base_date = date.today() - timedelta(days=60)
    records = []

    # Generate 60 days of realistic data
    base_nav = 1.0
    for i in range(60):
        current_date = base_date + timedelta(days=i)

        # Simulate slight upward trend with some volatility
        daily_change = 0.0005 + (0.002 if i % 10 == 0 else 0) - (0.001 if i % 15 == 0 else 0)
        base_nav += base_nav * daily_change

        record = FundDailyRecord(
            cnpj="43.121.002/0001-41",  # Nu Reserva Planejada
            date=current_date,
            nav=round(base_nav, 6),
            equity=850_000_000 + (i * 500_000),  # Growing fund
            total_value=850_000_000 + (i * 500_000),
            deposits=2_000_000 if i % 5 == 0 else 0,
            withdrawals=1_000_000 if i % 8 == 0 else 0,
            shareholders=8_500 + (i * 2)
        )
        records.append(record)

    logging.info(f"✅ Created {len(records)} days of sample data")
    logging.info(f"   Period: {records[0].date} to {records[-1].date}")
    logging.info(f"   NAV: {records[0].nav:.6f} → {records[-1].nav:.6f}")

    return records


def validate_benchmark_collection() -> bool:
    """Test benchmark collection system."""
    logging.info("🏛️ Validating benchmark collection...")

    try:
        start_time = time.time()

        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        logging.info(f"   Collecting benchmarks for {start_date} to {end_date}")
        benchmarks = collect_all_benchmarks_sync(start_date, end_date)

        collection_time = time.time() - start_time

        # Validate structure
        assert benchmarks is not None, "Benchmarks should not be None"
        assert hasattr(benchmarks, 'selic_accumulated'), "Should have SELIC data"
        assert hasattr(benchmarks, 'cdi_accumulated'), "Should have CDI data"
        assert hasattr(benchmarks, 'ipca_accumulated'), "Should have IPCA data"
        assert hasattr(benchmarks, 'cdb_estimated'), "Should have CDB estimate"
        assert hasattr(benchmarks, 'poupanca_estimated'), "Should have Poupança estimate"

        # Validate data quality
        assert benchmarks.data_completeness >= 0, "Data completeness should be valid"

        # Performance validation
        assert collection_time < 30, f"Collection took {collection_time:.2f}s, should be < 30s"

        logging.info("✅ Benchmark collection validation passed")
        logging.info(f"   Performance: {collection_time:.2f}s")
        logging.info(f"   Data quality: {benchmarks.data_completeness:.1%} complete")
        logging.info(f"   SELIC: {benchmarks.selic_accumulated:.3f}%")
        logging.info(f"   CDI: {benchmarks.cdi_accumulated:.3f}%")
        logging.info(f"   IPCA: {benchmarks.ipca_accumulated:.3f}%")
        logging.info(f"   CDB est.: {benchmarks.cdb_estimated:.3f}%")
        logging.info(f"   Poupança est.: {benchmarks.poupanca_estimated:.3f}%")

        return True

    except Exception as e:
        logging.error(f"❌ Benchmark collection failed: {e}")
        return False


def validate_advanced_metrics(sample_data: list[FundDailyRecord]) -> bool:
    """Test advanced metrics calculation."""
    logging.info("📊 Validating advanced metrics calculation...")

    try:
        # Get benchmarks
        start_date = sample_data[0].date
        end_date = sample_data[-1].date
        benchmarks = collect_all_benchmarks_sync(start_date, end_date)

        # Calculate performance
        start_time = time.time()
        performance = compute_performance(sample_data, benchmarks)
        calculation_time = time.time() - start_time

        # Validate core metrics
        assert performance is not None, "Performance should not be None"
        assert performance.fund_cnpj == "43.121.002/0001-41", "CNPJ should match"

        # Validate advanced metrics exist
        required_metrics = ['return_pct', 'volatility', 'sharpe_ratio', 'alpha', 'beta', 'var_95']
        for metric in required_metrics:
            assert hasattr(performance, metric), f"Should have {metric}"
            value = getattr(performance, metric)
            assert value is not None, f"{metric} should not be None"

        # Validate metric ranges (basic sanity checks)
        assert -100 <= performance.return_pct <= 200, f"Return {performance.return_pct} seems unrealistic"
        assert 0 <= performance.volatility <= 100, f"Volatility {performance.volatility} seems unrealistic"
        assert -10 <= performance.sharpe_ratio <= 10, f"Sharpe {performance.sharpe_ratio} seems unrealistic"
        assert 0 <= performance.beta <= 5, f"Beta {performance.beta} seems unrealistic"
        assert performance.var_95 <= 5, f"VaR {performance.var_95} should be negative or small positive"

        # Performance validation
        assert calculation_time < 2, f"Calculation took {calculation_time:.2f}s, should be < 2s"

        logging.info("✅ Advanced metrics validation passed")
        logging.info(f"   Performance: {calculation_time:.3f}s")
        logging.info(f"   Return: {performance.return_pct:.3f}%")
        logging.info(f"   Volatility: {performance.volatility:.3f}%")
        logging.info(f"   Sharpe: {performance.sharpe_ratio:.3f}")
        logging.info(f"   Alpha: {performance.alpha:.3f}%")
        logging.info(f"   Beta: {performance.beta:.3f}")
        logging.info(f"   VaR 95%: {performance.var_95:.3f}%")

        return True

    except Exception as e:
        logging.error(f"❌ Advanced metrics calculation failed: {e}")
        return False


def validate_llm_explanations(sample_data: list[FundDailyRecord]) -> bool:
    """Test LLM educational explanations."""
    logging.info("🧠 Validating LLM explanations...")

    try:
        # Get performance data
        start_date = sample_data[0].date
        end_date = sample_data[-1].date
        benchmarks = collect_all_benchmarks_sync(start_date, end_date)
        performance = compute_performance(sample_data, benchmarks)

        # Test explanations
        explainer = MetricsExplainer()

        start_time = time.time()
        explanations = explainer.explain_all_metrics(performance)
        explanation_time = time.time() - start_time

        # Validate structure
        assert explanations is not None, "Explanations should not be None"
        assert isinstance(explanations, dict), "Explanations should be a dict"

        expected_metrics = ['sharpe_ratio', 'alpha', 'beta', 'var_95']
        for metric in expected_metrics:
            assert metric in explanations, f"Should have explanation for {metric}"
            explanation = explanations[metric]
            assert explanation is not None, f"Explanation for {metric} should not be None"
            assert len(explanation) > 10, f"Explanation for {metric} too short"
            assert len(explanation) < 1000, f"Explanation for {metric} too long"

            # Basic Portuguese check
            portuguese_words = ['de ', 'do ', 'da ', 'em ', 'com ', 'que ', 'é ']
            has_portuguese = any(word in explanation.lower() for word in portuguese_words)
            assert has_portuguese, f"Explanation for {metric} should be in Portuguese"

        # Performance validation
        assert explanation_time < 15, f"Explanation took {explanation_time:.2f}s, should be < 15s"

        logging.info("✅ LLM explanations validation passed")
        logging.info(f"   Performance: {explanation_time:.2f}s")

        # Log sample explanations (first 100 chars)
        for metric, explanation in explanations.items():
            preview = explanation[:100] + "..." if len(explanation) > 100 else explanation
            logging.info(f"   {metric}: {preview}")

        return True

    except Exception as e:
        logging.error(f"❌ LLM explanations failed: {e}")
        return False


def validate_fallback_mechanisms() -> bool:
    """Test fallback mechanisms."""
    logging.info("🛡️ Validating fallback mechanisms...")

    try:
        # Test LLM fallback (force no API key to trigger fallback)
        # Use unittest.mock.patch.dict to safely manipulate env vars
        # This guarantees restoration even if an exception occurs
        import unittest.mock

        env_without_key = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with unittest.mock.patch.dict(os.environ, env_without_key, clear=True):
            explainer = MetricsExplainer()  # Will create with no API key

            explanation = explainer.explain_metric("sharpe_ratio", 1.5, {
                "fund_return": 12.5,
                "cdi_return": 10.2
            })

            assert explanation is not None, "Should provide fallback explanation"
            assert len(explanation) > 0, "Fallback explanation should not be empty"
            assert "Sharpe Ratio" in explanation, "Should mention the metric name"

        logging.info("✅ Fallback mechanisms validation passed")
        logging.info(f"   Fallback explanation: {explanation[:100]}...")

        return True

    except Exception as e:
        logging.error(f"❌ Fallback mechanisms failed: {e}")
        return False


def main() -> int:
    """Main validation runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 Educational Metrics System Validator")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("🚀 Phase 1 Educational Metrics System Validation")
    logger.info("=" * 60)

    # Create test data
    sample_data = create_sample_data()

    # Run all validations
    validations = [
        ("Benchmark Collection", validate_benchmark_collection),
        ("Advanced Metrics", lambda: validate_advanced_metrics(sample_data)),
        ("LLM Explanations", lambda: validate_llm_explanations(sample_data)),
        ("Fallback Mechanisms", validate_fallback_mechanisms),
    ]

    results = {}
    overall_start = time.time()

    for validation_name, validation_func in validations:
        logger.info(f"\n🔍 Running {validation_name} validation...")
        try:
            results[validation_name] = validation_func()
        except Exception as e:
            logger.error(f"❌ {validation_name} validation crashed: {e}")
            results[validation_name] = False

    overall_time = time.time() - overall_start

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 VALIDATION SUMMARY")
    logger.info("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for validation_name, passed_validation in results.items():
        status = "✅ PASS" if passed_validation else "❌ FAIL"
        logger.info(f"   {validation_name}: {status}")

    logger.info(f"\nOverall: {passed}/{total} validations passed")
    logger.info(f"Total time: {overall_time:.2f}s")

    if passed == total:
        logger.info("\n🎉 ALL VALIDATIONS PASSED!")
        logger.info("Phase 1 Educational Metrics System is ready for production.")
        return 0
    else:
        logger.info(f"\n⚠️  {total - passed} validations failed.")
        logger.info("Phase 1 system needs attention before production.")
        return 1


if __name__ == "__main__":
    sys.exit(main())