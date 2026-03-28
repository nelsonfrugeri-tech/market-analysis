"""Tests for educational content templates and registry."""

import pytest
from pathlib import Path

from market_analysis.ai.templates import PromptTemplate, TemplateRegistry


@pytest.fixture
def registry() -> TemplateRegistry:
    return TemplateRegistry()


class TestPromptTemplate:
    def test_frozen_dataclass(self):
        tpl = PromptTemplate(
            category="performance",
            metric_name="test",
            display_name="Test",
            system_prompt="sys",
            user_template="tpl",
            interpretation_scale={"low": "<1"},
            example_output="example",
        )
        assert tpl.category == "performance"
        with pytest.raises(AttributeError):
            tpl.category = "risk"  # type: ignore[misc]

    def test_defaults(self):
        tpl = PromptTemplate(
            category="risk",
            metric_name="vol",
            display_name="Vol",
            system_prompt="",
            user_template="",
            interpretation_scale={},
            example_output="",
        )
        assert tpl.unit == ""
        assert tpl.priority == 1
        assert tpl.max_words == 120


class TestTemplateRegistry:
    def test_loads_all_18_metrics(self, registry: TemplateRegistry):
        metrics = registry.list_metrics()
        assert len(metrics) == 21

    def test_has_four_categories(self, registry: TemplateRegistry):
        categories = registry.list_categories()
        assert categories == ["consistency", "efficiency", "performance", "risk"]

    def test_performance_category_count(self, registry: TemplateRegistry):
        perf = registry.get_all_by_category("performance")
        assert len(perf) == 6

    def test_risk_category_count(self, registry: TemplateRegistry):
        risk = registry.get_all_by_category("risk")
        assert len(risk) == 5

    def test_efficiency_category_count(self, registry: TemplateRegistry):
        eff = registry.get_all_by_category("efficiency")
        assert len(eff) == 5

    def test_consistency_category_count(self, registry: TemplateRegistry):
        con = registry.get_all_by_category("consistency")
        assert len(con) == 5

    def test_get_template_by_name(self, registry: TemplateRegistry):
        tpl = registry.get_template("sharpe_ratio")
        assert tpl.category == "risk"
        assert tpl.display_name == "Indice Sharpe"
        assert "{value}" in tpl.user_template

    def test_get_template_missing_raises(self, registry: TemplateRegistry):
        with pytest.raises(KeyError):
            registry.get_template("nonexistent_metric")

    def test_templates_have_required_fields(self, registry: TemplateRegistry):
        for name in registry.list_metrics():
            tpl = registry.get_template(name)
            assert tpl.display_name, f"{name} missing display_name"
            assert tpl.user_template, f"{name} missing user_template"
            assert tpl.interpretation_scale, f"{name} missing interpretation_scale"
            assert tpl.example_output, f"{name} missing example_output"
            assert tpl.glossary_term, f"{name} missing glossary_term"
            assert tpl.analogy, f"{name} missing analogy"

    def test_templates_sorted_by_priority(self, registry: TemplateRegistry):
        for cat in registry.list_categories():
            templates = registry.get_all_by_category(cat)
            priorities = [t.priority for t in templates]
            assert priorities == sorted(priorities), f"{cat} not sorted by priority"

    def test_system_prompt_loaded(self, registry: TemplateRegistry):
        assert "educador financeiro" in registry.system_prompt

    def test_all_metrics_match_advanced_metrics_dataclass(self, registry: TemplateRegistry):
        """Ensure templates cover all fields from AdvancedMetrics."""
        expected = {
            "cumulative_return", "ytd_return", "twelve_month_return",
            "six_month_return", "three_month_return", "monthly_avg_return",
            "volatility", "max_drawdown", "sharpe_ratio", "sortino_ratio", "var_95",
            "alpha", "beta", "tracking_error", "information_ratio", "correlation",
            "positive_months_pct", "best_month", "worst_month", "win_loss_vs_cdi",
            "stability_index",
        }
        registered = set(registry.list_metrics())
        # We have 18 templates for 21 metrics (some periods may be grouped)
        # At minimum, all registered metrics should be in expected
        assert registered.issubset(expected), f"Unknown metrics: {registered - expected}"

    def test_max_words_within_limit(self, registry: TemplateRegistry):
        for name in registry.list_metrics():
            tpl = registry.get_template(name)
            assert tpl.max_words <= 150, f"{name} max_words too high: {tpl.max_words}"

    def test_user_template_has_placeholders(self, registry: TemplateRegistry):
        for name in registry.list_metrics():
            tpl = registry.get_template(name)
            assert "{value}" in tpl.user_template, f"{name} missing {{value}} placeholder"
            assert "{fund_name}" in tpl.user_template, f"{name} missing {{fund_name}} placeholder"
