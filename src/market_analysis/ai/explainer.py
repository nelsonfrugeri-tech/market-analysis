"""MetricsExplainer — orchestrates LLM calls to explain financial metrics.

Fallback chain: Claude -> Ollama -> Static (template-based, no LLM).
Uses TemplateRegistry for prompts, ExplanationCache for persistence.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from market_analysis.ai.cache import ExplanationCache
from market_analysis.ai.clients.base import LLMClient, LLMClientError, LLMResponse
from market_analysis.ai.clients.anthropic import AnthropicClient
from market_analysis.ai.clients.ollama import OllamaClient
from market_analysis.ai.context import MetricContext, build_context, fill_template
from market_analysis.ai.templates.models import PromptTemplate
from market_analysis.ai.templates.registry import TemplateRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExplanationResult:
    """Single metric explanation with metadata."""

    metric_name: str
    display_name: str
    category: str
    text: str
    provider: str  # "anthropic", "ollama", "static", "cache"
    cached: bool = False
    latency_ms: float = 0.0


@dataclass
class ExplainerStats:
    """Aggregated stats for a batch explain run."""

    total: int = 0
    from_cache: int = 0
    from_llm: int = 0
    from_static: int = 0
    total_tokens: int = 0
    total_latency_ms: float = 0.0


class MetricsExplainer:
    """Orchestrator for generating educational metric explanations.

    Usage::

        explainer = MetricsExplainer()
        results = await explainer.explain_all(metrics_dict, period="12 meses")

    Or synchronously::

        results = explainer.explain_all_sync(metrics_dict, period="12 meses")
    """

    def __init__(
        self,
        *,
        clients: list[LLMClient] | None = None,
        registry: TemplateRegistry | None = None,
        cache: ExplanationCache | None = None,
        fund_name: str = "Nu Reserva Planejada",
        benchmark_name: str = "CDI",
    ) -> None:
        self._registry = registry or TemplateRegistry()
        self._cache = cache or ExplanationCache()
        self._fund_name = fund_name
        self._benchmark_name = benchmark_name

        # Default fallback chain: Anthropic -> Ollama
        self._clients: list[LLMClient] = clients or [
            OllamaClient(),
            AnthropicClient(),
        ]

    async def explain_metric(
        self,
        metric_name: str,
        value: float,
        *,
        period: str = "",
        benchmark_value: float = 0.0,
    ) -> ExplanationResult:
        """Generate explanation for a single metric.

        Tries cache first, then LLM chain, then static fallback.
        """
        # 1. Try cache
        cached_text = self._cache.get(metric_name, value, period)
        if cached_text is not None:
            tpl = self._get_template(metric_name)
            return ExplanationResult(
                metric_name=metric_name,
                display_name=tpl.display_name if tpl else metric_name,
                category=tpl.category if tpl else "",
                text=cached_text,
                provider="cache",
                cached=True,
            )

        # 2. Build prompt from template
        tpl = self._get_template(metric_name)
        if tpl is None:
            return self._static_result(metric_name, value)

        ctx = build_context(
            metric_name,
            value,
            fund_name=self._fund_name,
            period=period,
            benchmark_name=self._benchmark_name,
            benchmark_value=benchmark_value,
        )
        user_prompt = fill_template(tpl.user_template, ctx)
        system_prompt = tpl.system_prompt.replace("{max_words}", str(tpl.max_words))

        # 3. Try LLM chain
        for client in self._clients:
            try:
                resp = await client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=tpl.max_words * 6,  # Portuguese ~3-4 tok/word + DeepSeek exceeds word limits
                    temperature=0.3,
                )
                # Cache the result
                self._cache.put(
                    metric_name,
                    value,
                    period,
                    resp.text,
                    provider=resp.provider,
                    model=resp.model,
                )
                return ExplanationResult(
                    metric_name=metric_name,
                    display_name=tpl.display_name,
                    category=tpl.category,
                    text=resp.text,
                    provider=resp.provider,
                    latency_ms=resp.latency_ms,
                )
            except LLMClientError as exc:
                logger.warning(
                    "LLM %s failed for %s: %s",
                    client.provider_name,
                    metric_name,
                    exc,
                )
                continue

        # 4. Static fallback
        logger.info("All LLM clients failed for %s, using static fallback", metric_name)
        return self._static_from_template(tpl, ctx)

    async def explain_all(
        self,
        metrics: dict[str, float | None],
        *,
        period: str = "",
        benchmarks: dict[str, float] | None = None,
    ) -> tuple[list[ExplanationResult], ExplainerStats]:
        """Generate explanations for all metrics in a dict.

        Args:
            metrics: metric_name -> value mapping. None values are skipped.
            period: Human-readable period string (e.g. "ultimos 12 meses").
            benchmarks: Optional benchmark values for comparison.

        Returns:
            Tuple of (results list sorted by category+priority, stats).
        """
        benchmarks = benchmarks or {}
        default_bench = benchmarks.get("cdi", 0.0)
        stats = ExplainerStats()
        results: list[ExplanationResult] = []

        for name, val in metrics.items():
            if val is None:
                continue
            stats.total += 1
            bench_val = benchmarks.get(name, default_bench)

            result = await self.explain_metric(
                name,
                val,
                period=period,
                benchmark_value=bench_val,
            )
            results.append(result)

            if result.cached:
                stats.from_cache += 1
            elif result.provider == "static":
                stats.from_static += 1
            else:
                stats.from_llm += 1
                stats.total_latency_ms += result.latency_ms

        # Sort by category order, then priority within category
        category_order = {"performance": 0, "risk": 1, "efficiency": 2, "consistency": 3}
        results.sort(key=lambda r: (category_order.get(r.category, 99), r.display_name))
        return results, stats

    def explain_all_sync(
        self,
        metrics: dict[str, float | None],
        *,
        period: str = "",
        benchmarks: dict[str, float] | None = None,
    ) -> tuple[list[ExplanationResult], ExplainerStats]:
        """Synchronous wrapper for explain_all. For use in PDF pipeline."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already inside an event loop — run in thread to avoid deadlock
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.explain_all(metrics, period=period, benchmarks=benchmarks),
                )
                return future.result(timeout=120)
        else:
            return asyncio.run(
                self.explain_all(metrics, period=period, benchmarks=benchmarks)
            )

    def _get_template(self, metric_name: str) -> Optional[PromptTemplate]:
        try:
            return self._registry.get_template(metric_name)
        except KeyError:
            return None

    def _static_result(self, metric_name: str, value: float) -> ExplanationResult:
        """Minimal fallback when no template exists."""
        return ExplanationResult(
            metric_name=metric_name,
            display_name=metric_name,
            category="",
            text=f"{metric_name}: {value}",
            provider="static",
        )

    def _static_from_template(
        self, tpl: PromptTemplate, ctx: MetricContext
    ) -> ExplanationResult:
        """Build a static explanation from template fields (no LLM)."""
        text = tpl.example_output.strip()
        if not text:
            text = f"{tpl.display_name}: {ctx.value}"

        return ExplanationResult(
            metric_name=tpl.metric_name,
            display_name=tpl.display_name,
            category=tpl.category,
            text=text,
            provider="static",
        )
