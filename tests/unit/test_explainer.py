"""Tests for the LLM integration service (Issue #60)."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from market_analysis.ai.cache import ExplanationCache
from market_analysis.ai.clients.base import LLMClient, LLMClientError, LLMResponse
from market_analysis.ai.context import MetricContext, build_context, fill_template, _fmt_brl
from market_analysis.ai.explainer import ExplanationResult, ExplainerStats, MetricsExplainer
from market_analysis.ai.templates.registry import TemplateRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeLLMClient(LLMClient):
    """Deterministic LLM client for testing."""

    def __init__(
        self,
        *,
        name: str = "fake",
        response_text: str = "Explicacao de teste.",
        should_fail: bool = False,
    ) -> None:
        self._name = name
        self._response_text = response_text
        self._should_fail = should_fail
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> LLMResponse:
        self.call_count += 1
        if self._should_fail:
            raise LLMClientError(f"{self._name} forced failure")
        return LLMResponse(
            text=self._response_text,
            model="fake-model",
            input_tokens=50,
            output_tokens=30,
            latency_ms=42.0,
            provider=self._name,
        )

    async def health_check(self) -> bool:
        return not self._should_fail


@pytest.fixture
def tmp_cache(tmp_path: Path) -> ExplanationCache:
    return ExplanationCache(cache_dir=tmp_path / "cache", ttl_hours=1)


@pytest.fixture
def registry() -> TemplateRegistry:
    return TemplateRegistry()


@pytest.fixture
def fake_client() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def failing_client() -> FakeLLMClient:
    return FakeLLMClient(name="failing", should_fail=True)


@pytest.fixture
def explainer(fake_client: FakeLLMClient, tmp_cache: ExplanationCache, registry: TemplateRegistry) -> MetricsExplainer:
    return MetricsExplainer(
        clients=[fake_client],
        registry=registry,
        cache=tmp_cache,
    )


# ---------------------------------------------------------------------------
# Context builder tests
# ---------------------------------------------------------------------------


class TestContextBuilder:
    def test_build_context_return_metric(self):
        ctx = build_context("cumulative_return", 12.5, period="12 meses")
        assert ctx.value == 12.5
        assert ctx.period == "12 meses"
        assert ctx.fund_name == "Nu Reserva Planejada"
        # R$ 10000 * 1.125 = 11250
        assert "11.250" in ctx.result

    def test_build_context_non_return_metric(self):
        ctx = build_context("sharpe_ratio", 1.25, period="12 meses")
        assert ctx.value == 1.25
        # Non-return metric should have result=0
        assert ctx.result == "0,00"

    def test_build_context_max_drawdown(self):
        ctx = build_context("max_drawdown", -2.3, investment_amount=10_000)
        # 10000 * (1 + (-2.3/100)) = 9770
        assert "9.770" in ctx.result

    def test_fill_template(self):
        ctx = MetricContext(
            value=1.25,
            fund_name="Test",
            period="12m",
            benchmark="CDI",
            bench_value=0.95,
            investment="10.000",
            result="10.125",
        )
        tpl = "Fundo {fund_name}: {value} vs {benchmark} ({bench_value})"
        result = fill_template(tpl, ctx)
        assert "Test" in result
        assert "1,25" in result
        assert "CDI" in result

    def test_fmt_brl_formats_correctly(self):
        assert _fmt_brl(10_000.0) == "10.000,00"
        assert _fmt_brl(0.0) == "0,00"
        assert _fmt_brl(1_234_567.89) == "1.234.567,89"


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------


class TestExplanationCache:
    def test_miss_returns_none(self, tmp_cache: ExplanationCache):
        assert tmp_cache.get("sharpe_ratio", 1.25, "12m") is None

    def test_put_and_get(self, tmp_cache: ExplanationCache):
        tmp_cache.put("sharpe_ratio", 1.25, "12m", "Texto cached")
        assert tmp_cache.get("sharpe_ratio", 1.25, "12m") == "Texto cached"

    def test_expired_entry_returns_none(self, tmp_path: Path):
        cache = ExplanationCache(cache_dir=tmp_path / "exp_cache", ttl_hours=0)
        cache.put("alpha", 0.5, "6m", "Old text")
        # TTL=0 means immediate expiration
        assert cache.get("alpha", 0.5, "6m") is None

    def test_clear(self, tmp_cache: ExplanationCache):
        tmp_cache.put("a", 1.0, "", "t1")
        tmp_cache.put("b", 2.0, "", "t2")
        count = tmp_cache.clear()
        assert count == 2
        assert tmp_cache.get("a", 1.0, "") is None

    def test_rounding_key_dedup(self, tmp_cache: ExplanationCache):
        tmp_cache.put("vol", 3.456, "12m", "same")
        # 3.459 rounds to 3.46 (different from 3.456 -> 3.46) — should match
        assert tmp_cache.get("vol", 3.459, "12m") == "same"
        # 3.5 rounds differently — should miss
        assert tmp_cache.get("vol", 3.5, "12m") is None


# ---------------------------------------------------------------------------
# LLM Client base tests
# ---------------------------------------------------------------------------


class TestFakeLLMClient:
    @pytest.mark.asyncio
    async def test_generate_returns_response(self, fake_client: FakeLLMClient):
        resp = await fake_client.generate("sys", "user")
        assert resp.text == "Explicacao de teste."
        assert resp.provider == "fake"
        assert fake_client.call_count == 1

    @pytest.mark.asyncio
    async def test_failing_client_raises(self, failing_client: FakeLLMClient):
        with pytest.raises(LLMClientError):
            await failing_client.generate("sys", "user")


# ---------------------------------------------------------------------------
# Explainer tests
# ---------------------------------------------------------------------------


class TestMetricsExplainer:
    @pytest.mark.asyncio
    async def test_explain_known_metric(self, explainer: MetricsExplainer, fake_client: FakeLLMClient):
        result = await explainer.explain_metric("sharpe_ratio", 1.25, period="12 meses")
        assert result.metric_name == "sharpe_ratio"
        assert result.display_name == "Indice Sharpe"
        assert result.category == "risk"
        assert result.text == "Explicacao de teste."
        assert result.provider == "fake"
        assert fake_client.call_count == 1

    @pytest.mark.asyncio
    async def test_explain_unknown_metric_returns_static(self, explainer: MetricsExplainer):
        result = await explainer.explain_metric("nonexistent_xyz", 42.0)
        assert result.provider == "static"
        assert "nonexistent_xyz" in result.text

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(
        self,
        tmp_cache: ExplanationCache,
        fake_client: FakeLLMClient,
        registry: TemplateRegistry,
    ):
        tmp_cache.put("sharpe_ratio", 1.25, "12m", "Cached explanation")
        exp = MetricsExplainer(clients=[fake_client], registry=registry, cache=tmp_cache)
        result = await exp.explain_metric("sharpe_ratio", 1.25, period="12m")
        assert result.cached is True
        assert result.provider == "cache"
        assert result.text == "Cached explanation"
        assert fake_client.call_count == 0

    @pytest.mark.asyncio
    async def test_fallback_chain(
        self,
        tmp_cache: ExplanationCache,
        registry: TemplateRegistry,
    ):
        failing = FakeLLMClient(name="primary", should_fail=True)
        backup = FakeLLMClient(name="backup", response_text="Backup response")
        exp = MetricsExplainer(clients=[failing, backup], registry=registry, cache=tmp_cache)

        result = await exp.explain_metric("sharpe_ratio", 1.0, period="12m")
        assert result.provider == "backup"
        assert result.text == "Backup response"
        assert failing.call_count == 1
        assert backup.call_count == 1

    @pytest.mark.asyncio
    async def test_all_clients_fail_uses_static(
        self,
        tmp_cache: ExplanationCache,
        registry: TemplateRegistry,
    ):
        f1 = FakeLLMClient(name="a", should_fail=True)
        f2 = FakeLLMClient(name="b", should_fail=True)
        exp = MetricsExplainer(clients=[f1, f2], registry=registry, cache=tmp_cache)

        result = await exp.explain_metric("sharpe_ratio", 1.0, period="12m")
        assert result.provider == "static"
        # Should use example_output from template
        assert len(result.text) > 10

    @pytest.mark.asyncio
    async def test_explain_all_returns_sorted_results(self, explainer: MetricsExplainer):
        metrics = {
            "sharpe_ratio": 1.25,
            "cumulative_return": 12.5,
            "stability_index": 0.85,
            "alpha": None,  # should be skipped
        }
        results, stats = await explainer.explain_all(metrics, period="12 meses")

        assert stats.total == 3
        assert stats.from_llm == 3
        assert len(results) == 3

        # Should be sorted: performance first, then risk, then consistency
        categories = [r.category for r in results]
        assert categories == ["performance", "risk", "consistency"]

    @pytest.mark.asyncio
    async def test_explain_all_stats(self, explainer: MetricsExplainer, tmp_cache: ExplanationCache):
        # Pre-cache one metric
        tmp_cache.put("volatility", 2.5, "6m", "Cached vol")

        metrics = {
            "volatility": 2.5,
            "sharpe_ratio": 1.0,
        }
        results, stats = await explainer.explain_all(metrics, period="6m")

        assert stats.total == 2
        assert stats.from_cache == 1
        assert stats.from_llm == 1

    def test_explain_all_sync(self, explainer: MetricsExplainer):
        metrics = {"sharpe_ratio": 1.25}
        results, stats = explainer.explain_all_sync(metrics, period="12m")
        assert len(results) == 1
        assert stats.total == 1


# ---------------------------------------------------------------------------
# Anthropic client unit test (mocked HTTP)
# ---------------------------------------------------------------------------


class TestAnthropicClient:
    @pytest.mark.asyncio
    async def test_generate_mocked(self):
        from unittest.mock import MagicMock
        from market_analysis.ai.clients.anthropic import AnthropicClient

        mock_response = {
            "content": [{"text": "Resposta Claude"}],
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }

        client = AnthropicClient(api_key="test-key")

        with patch("market_analysis.ai.clients.anthropic.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_resp.status_code = 200
            mock_ctx.post = AsyncMock(return_value=mock_resp)
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_ctx

            resp = await client.generate("system", "user")
            assert resp.text == "Resposta Claude"
            assert resp.provider == "anthropic"
            assert resp.input_tokens == 100

    @pytest.mark.asyncio
    async def test_no_api_key_raises(self):
        from market_analysis.ai.clients.anthropic import AnthropicClient

        client = AnthropicClient(api_key="")
        with pytest.raises(LLMClientError, match="ANTHROPIC_API_KEY"):
            await client.generate("sys", "user")

    @pytest.mark.asyncio
    async def test_health_check_no_key(self):
        from market_analysis.ai.clients.anthropic import AnthropicClient

        client = AnthropicClient(api_key="")
        assert await client.health_check() is False


# ---------------------------------------------------------------------------
# Ollama client unit test (mocked HTTP)
# ---------------------------------------------------------------------------


class TestOllamaClient:
    @pytest.mark.asyncio
    async def test_generate_mocked(self):
        from unittest.mock import MagicMock
        from market_analysis.ai.clients.ollama import OllamaClient

        mock_response = {
            "message": {"content": "Resposta local"},
            "model": "llama3.2",
        }

        client = OllamaClient()

        with patch("market_analysis.ai.clients.ollama.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status = MagicMock()
            mock_resp.status_code = 200
            mock_ctx.post = AsyncMock(return_value=mock_resp)
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_ctx

            resp = await client.generate("system", "user")
            assert resp.text == "Resposta local"
            assert resp.provider == "ollama"

    @pytest.mark.asyncio
    async def test_empty_response_raises(self):
        from unittest.mock import MagicMock
        from market_analysis.ai.clients.ollama import OllamaClient

        client = OllamaClient()

        with patch("market_analysis.ai.clients.ollama.httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"message": {"content": ""}}
            mock_resp.raise_for_status = MagicMock()
            mock_resp.status_code = 200
            mock_ctx.post = AsyncMock(return_value=mock_resp)
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_ctx

            with pytest.raises(LLMClientError, match="empty"):
                await client.generate("sys", "user")
