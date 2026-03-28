"""Quality validation tests for Phase 1 educational metrics system.

Validates:
- LLM explanation quality and comprehensibility
- Mathematical accuracy of metrics
- Performance benchmarks
- User experience criteria
"""

import pytest
import re
from datetime import date, timedelta
from typing import Dict, Any

from market_analysis.ai.explainer import MetricsExplainer
from market_analysis.application.performance import (
    calculate_sharpe_ratio,
    calculate_alpha_beta,
    calculate_var_95,
    calculate_volatility
)
from market_analysis.domain.models.fund import FundDailyRecord


class TestQualityValidation:
    """Quality validation tests for educational metrics system."""

    @pytest.fixture
    def stable_fund_data(self) -> list[FundDailyRecord]:
        """Create stable fund data for quality testing."""
        base_date = date(2024, 1, 1)
        records = []

        for i in range(60):  # 2 months of data
            record_date = base_date + timedelta(days=i)
            # Stable growth pattern
            nav = 1.0 + (i * 0.0005)  # 0.05% daily growth
            equity = 1000000 + (i * 500)

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=record_date,
                nav=nav,
                equity=equity,
                total_value=equity * 0.95,
                deposits=3000.0,
                withdrawals=1000.0,
                shareholders=150 + i
            ))

        return records

    @pytest.fixture
    def volatile_fund_data(self) -> list[FundDailyRecord]:
        """Create volatile fund data for testing edge cases."""
        import math

        base_date = date(2024, 1, 1)
        records = []

        for i in range(60):
            record_date = base_date + timedelta(days=i)
            # Volatile pattern with sine wave
            volatility_factor = math.sin(i * 0.3) * 0.02  # ±2% volatility
            nav = 1.0 + volatility_factor + (i * 0.0002)  # Small upward trend
            equity = 1000000 + (i * 200)

            records.append(FundDailyRecord(
                cnpj="43.121.002/0001-41",
                date=record_date,
                nav=nav,
                equity=equity,
                total_value=equity * 0.95,
                deposits=4000.0,
                withdrawals=2000.0,
                shareholders=120 + i
            ))

        return records

    def test_llm_explanation_quality(self, stable_fund_data):
        """Test quality of LLM-generated explanations."""
        explainer = MetricsExplainer()

        # Create performance context
        context = {
            'fund_return': 8.5,
            'cdi_return': 7.2,
            'volatility': 2.5,
            'period_start': date(2024, 1, 1),
            'period_end': date(2024, 3, 1)
        }

        # Test each metric explanation
        metrics_to_test = [
            ('sharpe_ratio', 1.25),
            ('alpha', 1.3),
            ('beta', 0.85),
            ('var_95', -2.1)
        ]

        for metric_name, value in metrics_to_test:
            explanation = explainer.explain_metric(metric_name, value, context)

            # Quality criteria
            self._validate_explanation_quality(explanation, metric_name, value)

    def _validate_explanation_quality(self, explanation: str, metric_name: str, value: float):
        """Validate quality criteria for explanations."""
        # Length criteria
        assert 50 <= len(explanation) <= 800, f"Explanation length {len(explanation)} not in range 50-800"

        # Portuguese language criteria
        portuguese_words = [
            'retorno', 'risco', 'fundo', 'investimento', 'valor', 'comparação',
            'indica', 'mostra', 'significa', 'representa', 'período'
        ]
        explanation_lower = explanation.lower()
        found_portuguese = sum(1 for word in portuguese_words if word in explanation_lower)
        assert found_portuguese >= 2, f"Not enough Portuguese financial terms found in: {explanation}"

        # Should mention the actual value
        value_mentioned = (
            str(value) in explanation or
            f"{value:.1f}" in explanation or
            f"{value:.2f}" in explanation
        )
        assert value_mentioned, f"Metric value {value} not mentioned in explanation: {explanation}"

        # Should avoid excessive jargon
        jargon_words = [
            'correlação', 'covariância', 'desvio padrão', 'distribuição normal',
            'regressão', 'econometria', 'hedge', 'derivativo'
        ]
        jargon_count = sum(1 for word in jargon_words if word in explanation_lower)
        assert jargon_count <= 2, f"Too much jargon in explanation: {explanation}"

        # Readability: should have reasonable sentence structure
        sentences = explanation.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        assert len(sentences) >= 1, "Explanation should have at least one complete sentence"

        # Each sentence should be reasonable length (not too long)
        for sentence in sentences:
            assert len(sentence) <= 200, f"Sentence too long ({len(sentence)} chars): {sentence}"

    def test_mathematical_accuracy(self, stable_fund_data, volatile_fund_data):
        """Test mathematical accuracy of metrics calculations."""

        # Test with stable data
        self._validate_metrics_accuracy(stable_fund_data, "stable")

        # Test with volatile data
        self._validate_metrics_accuracy(volatile_fund_data, "volatile")

    def _validate_metrics_accuracy(self, records: list[FundDailyRecord], data_type: str):
        """Validate mathematical accuracy for given data."""
        if not records or len(records) < 10:
            pytest.skip(f"Not enough data for {data_type} validation")

        # Test individual metric calculations
        fund_return = ((records[-1].nav / records[0].nav) - 1) * 100
        volatility = calculate_volatility(records)
        benchmark_return = 7.0  # Mock CDI

        # Sharpe Ratio validation
        sharpe = calculate_sharpe_ratio(fund_return, volatility, benchmark_return)
        if volatility > 0:
            expected_sharpe = (fund_return - benchmark_return) / volatility
            assert abs(sharpe - expected_sharpe) < 0.01, f"Sharpe calculation error for {data_type} data"

        # Alpha/Beta validation
        alpha, beta = calculate_alpha_beta(records, benchmark_return)
        assert 0.1 <= beta <= 3.0, f"Beta {beta} outside expected range for {data_type} data"
        assert -50 <= alpha <= 50, f"Alpha {alpha} outside reasonable range for {data_type} data"

        # VaR validation
        var_95 = calculate_var_95(records)
        if len(records) >= 30:
            assert var_95 <= 0, f"VaR should be negative or zero, got {var_95} for {data_type} data"
            assert var_95 >= -20, f"VaR {var_95} too extreme for {data_type} data"

        # Volatility validation
        assert volatility >= 0, f"Volatility should be non-negative, got {volatility} for {data_type} data"
        if data_type == "volatile":
            assert volatility > 0, f"Volatile data should have positive volatility, got {volatility}"

    def test_performance_benchmarks(self, stable_fund_data):
        """Test that system meets performance benchmarks."""
        import time

        explainer = MetricsExplainer()
        context = {'fund_return': 8.0, 'cdi_return': 7.0, 'volatility': 3.0}

        # Test single explanation performance
        start_time = time.time()
        explanation = explainer.explain_metric('sharpe_ratio', 1.1, context)
        single_time = time.time() - start_time

        assert single_time < 5.0, f"Single explanation took {single_time:.2f}s, expected < 5s"
        assert len(explanation) > 0, "Explanation should not be empty"

        # Test batch performance (all metrics)
        start_time = time.time()

        # Mock performance object
        class MockPerformance:
            return_pct = 8.5
            benchmark_cdi = 7.2
            volatility = 2.8
            period_start = date(2024, 1, 1)
            period_end = date(2024, 3, 1)
            sharpe_ratio = 1.15
            alpha = 1.2
            beta = 0.9
            var_95 = -1.8

        mock_perf = MockPerformance()
        explanations = explainer.explain_all_metrics(mock_perf)
        batch_time = time.time() - start_time

        assert batch_time < 10.0, f"Batch explanations took {batch_time:.2f}s, expected < 10s"
        assert len(explanations) == 4, "Should have 4 explanations"

    def test_user_comprehension_simulation(self, stable_fund_data):
        """Simulate user comprehension tests."""
        explainer = MetricsExplainer()

        # Test scenarios representing different user knowledge levels
        scenarios = [
            {
                'name': 'beginner_positive',
                'context': {'fund_return': 12.0, 'cdi_return': 8.0},
                'metric': 'sharpe_ratio',
                'value': 1.5,
                'expectations': ['bom', 'positivo', 'superior', 'melhor']
            },
            {
                'name': 'beginner_negative',
                'context': {'fund_return': 5.0, 'cdi_return': 8.0},
                'metric': 'alpha',
                'value': -2.0,
                'expectations': ['abaixo', 'negativo', 'pior', 'inferior']
            },
            {
                'name': 'intermediate_risk',
                'context': {'fund_return': 10.0, 'cdi_return': 8.0},
                'metric': 'var_95',
                'value': -3.5,
                'expectations': ['risco', 'perda', 'máxima', '95%']
            }
        ]

        for scenario in scenarios:
            explanation = explainer.explain_metric(
                scenario['metric'],
                scenario['value'],
                scenario['context']
            )

            # Check if explanation contains expected concepts
            explanation_lower = explanation.lower()
            found_expectations = sum(
                1 for exp in scenario['expectations']
                if exp in explanation_lower
            )

            # Should find at least some expected concepts
            assert found_expectations >= 1, (
                f"Scenario {scenario['name']}: Expected concepts {scenario['expectations']} "
                f"not found in explanation: {explanation}"
            )

    def test_edge_cases_handling(self):
        """Test handling of edge cases and boundary conditions."""
        explainer = MetricsExplainer()

        # Edge case scenarios
        edge_cases = [
            {'metric': 'sharpe_ratio', 'value': 0.0, 'context': {'fund_return': 7.0, 'cdi_return': 7.0}},
            {'metric': 'alpha', 'value': 0.0, 'context': {'fund_return': 8.0, 'cdi_return': 8.0}},
            {'metric': 'beta', 'value': 1.0, 'context': {'fund_return': 8.0, 'cdi_return': 7.0}},
            {'metric': 'var_95', 'value': 0.0, 'context': {'fund_return': 8.0, 'cdi_return': 7.0}},
            # Extreme values
            {'metric': 'sharpe_ratio', 'value': 3.0, 'context': {'fund_return': 15.0, 'cdi_return': 5.0}},
            {'metric': 'alpha', 'value': -10.0, 'context': {'fund_return': 2.0, 'cdi_return': 12.0}},
        ]

        for case in edge_cases:
            explanation = explainer.explain_metric(
                case['metric'],
                case['value'],
                case['context']
            )

            # Should handle edge cases gracefully
            assert len(explanation) > 10, f"Edge case explanation too short: {explanation}"
            assert not explanation.lower().startswith('error'), f"Error in explanation: {explanation}"

            # Should mention the value
            assert str(case['value']) in explanation, f"Value not mentioned in: {explanation}"

    def test_consistency_across_runs(self):
        """Test that explanations are consistent across multiple runs."""
        explainer = MetricsExplainer()

        # Test multiple runs of the same metric
        context = {'fund_return': 9.0, 'cdi_return': 7.5, 'volatility': 3.2}

        explanations = []
        for _ in range(3):  # Run 3 times
            explanation = explainer.explain_metric('sharpe_ratio', 1.2, context)
            explanations.append(explanation)

        # For fallback explanations, they should be exactly the same
        # For LLM explanations, they might vary slightly but should contain similar concepts
        if explainer.api_key is None:  # Fallback mode
            assert len(set(explanations)) == 1, "Fallback explanations should be identical"
        else:  # LLM mode
            # Should all mention the value
            for explanation in explanations:
                assert '1.2' in explanation or '1,2' in explanation
                assert len(explanation) > 20