"""Analysis service -- orchestrates LLM calls for fund analysis.

Uses a fallback chain: DeepSeek (Ollama) -> Qwen3:4b (Ollama) -> Anthropic -> Static.
Caches results via the existing ExplanationCache to avoid redundant LLM calls.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from market_analysis.ai.cache import ExplanationCache
from market_analysis.ai.clients.anthropic import AnthropicClient
from market_analysis.ai.clients.base import LLMClient, LLMClientError, LLMResponse
from market_analysis.ai.clients.ollama import OllamaClient
from market_analysis.api.analysis_models import (
    AnalysisMetadata,
    AnalysisType,
    ConfidenceLevel,
    FundAnalysisResponse,
    InsightEntry,
    PerformanceAnalysis,
    RecommendationAnalysis,
    RiskAnalysis,
)
from market_analysis.domain.models.fund import FundPerformance  # noqa: TCH001

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a senior Brazilian financial analyst specializing in investment funds. "
    "Respond in Portuguese (pt-BR). Be concise and precise. "
    "Always respond with valid JSON matching the requested schema. "
    "No markdown, no code fences, just raw JSON."
)

_PERFORMANCE_PROMPT_TEMPLATE = """\
Analyze the performance of fund "{fund_name}" (CNPJ: {cnpj}).

Data:
- Period return: {return_pct:.4%}
- NAV start: {nav_start:.6f}, NAV end: {nav_end:.6f}
- CDI accumulated: {benchmark_cdi:.4%}
- SELIC accumulated: {benchmark_selic:.4%}
- vs CDI: {vs_cdi:.0f} bps
- Volatility: {volatility:.4%}
- Sharpe ratio: {sharpe_ratio:.4f}

Respond with this exact JSON structure:
{{"summary": "...", "return_assessment": "...",\
 "trend_outlook": "...", "highlights": ["..."]}}
"""

_RISK_PROMPT_TEMPLATE = """\
Analyze the risk profile of fund "{fund_name}" (CNPJ: {cnpj}).

Data:
- Volatility: {volatility:.4%}
- Sharpe ratio: {sharpe_ratio:.4f}
- Max drawdown: {max_drawdown:.4%}
- VaR 95%: {var_95:.4%}
- Beta: {beta:.4f}
- Alpha: {alpha:.4f}

Respond with this exact JSON structure:
{{"summary": "...",\
 "risk_classification": "conservative|moderate|aggressive",\
 "sharpe_assessment": "...", "drawdown_assessment": "...",\
 "warnings": ["..."]}}
"""

_RECOMMENDATION_PROMPT_TEMPLATE = """\
Provide investment recommendation for fund "{fund_name}" (CNPJ: {cnpj}).

Data:
- Period return: {return_pct:.4%}
- vs CDI: {vs_cdi:.0f} bps
- Volatility: {volatility:.4%}
- Sharpe ratio: {sharpe_ratio:.4f}
- Max drawdown: {max_drawdown:.4%}
- Trend 30d: {trend_30d}
- Shareholders: {shareholders_current:,}

Respond with this exact JSON structure:
{{"summary": "...", "action": "hold|buy|reduce",\
 "allocation_suggestion": "...",\
 "considerations": ["..."]}}
"""


def _build_prompt(
    analysis_type: AnalysisType,
    performance: FundPerformance,
) -> str:
    """Build the user prompt from performance data and analysis type."""
    data = {
        "fund_name": performance.fund_name,
        "cnpj": performance.fund_cnpj,
        "return_pct": performance.return_pct,
        "nav_start": performance.nav_start,
        "nav_end": performance.nav_end,
        "benchmark_cdi": performance.benchmark_cdi,
        "benchmark_selic": performance.benchmark_selic,
        "vs_cdi": performance.vs_cdi,
        "volatility": performance.volatility,
        "sharpe_ratio": performance.sharpe_ratio,
        "max_drawdown": performance.max_drawdown,
        "var_95": performance.var_95,
        "alpha": performance.alpha,
        "beta": performance.beta,
        "trend_30d": performance.trend_30d,
        "shareholders_current": performance.shareholders_current,
    }

    templates = {
        AnalysisType.PERFORMANCE: _PERFORMANCE_PROMPT_TEMPLATE,
        AnalysisType.RISK: _RISK_PROMPT_TEMPLATE,
        AnalysisType.RECOMMENDATION: _RECOMMENDATION_PROMPT_TEMPLATE,
    }

    template = templates.get(analysis_type, _PERFORMANCE_PROMPT_TEMPLATE)
    return template.format(**data)


def _parse_llm_json(text: str) -> dict[str, Any]:
    """Parse LLM response text as JSON, stripping common artifacts."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)  # type: ignore[no-any-return]


def _build_static_performance(
    performance: FundPerformance,
) -> PerformanceAnalysis:
    """Build a static performance analysis when LLM is unavailable."""
    vs_cdi_str = "acima" if performance.vs_cdi > 0 else "abaixo"
    return PerformanceAnalysis(
        summary=(
            f"O fundo {performance.fund_name} apresentou retorno de "
            f"{performance.return_pct:.2%} no periodo, "
            f"ficando {abs(performance.vs_cdi):.0f} bps {vs_cdi_str} do CDI."
        ),
        return_assessment=(
            f"Retorno de {performance.return_pct:.2%} "
            f"vs CDI {performance.benchmark_cdi:.2%}."
        ),
        trend_outlook=f"Tendencia de 30 dias: {performance.trend_30d}.",
        highlights=[
            f"Sharpe ratio: {performance.sharpe_ratio:.2f}",
            f"Volatilidade: {performance.volatility:.2%}",
        ],
    )


def _build_static_risk(performance: FundPerformance) -> RiskAnalysis:
    """Build a static risk analysis when LLM is unavailable."""
    if performance.volatility < 0.02:
        risk_class = "conservative"
    elif performance.volatility < 0.10:
        risk_class = "moderate"
    else:
        risk_class = "aggressive"

    return RiskAnalysis(
        summary=(
            f"Volatilidade anualizada de {performance.volatility:.2%} "
            f"com drawdown maximo de {performance.max_drawdown:.2%}."
        ),
        risk_classification=risk_class,
        sharpe_assessment=f"Sharpe ratio de {performance.sharpe_ratio:.2f}.",
        drawdown_assessment=(f"Drawdown maximo de {performance.max_drawdown:.2%}."),
        warnings=[],
    )


def _build_static_recommendation(
    performance: FundPerformance,
) -> RecommendationAnalysis:
    """Build a static recommendation when LLM is unavailable."""
    action = "hold"
    if performance.vs_cdi > 0 and performance.sharpe_ratio > 1.0:
        action = "buy"
    elif performance.vs_cdi < -50:
        action = "reduce"

    return RecommendationAnalysis(
        summary=(
            f"Analise estatica baseada em metricas quantitativas do fundo "
            f"{performance.fund_name}."
        ),
        action=action,
        allocation_suggestion="Manter alocacao atual ate proxima revisao.",
        considerations=[
            "Analise gerada sem LLM - considerar consultar assessor.",
        ],
    )


class AnalysisService:
    """Orchestrates LLM-powered fund analysis with fallback chain.

    Fallback order: DeepSeek -> Qwen3:4b -> Anthropic -> Static.
    """

    def __init__(
        self,
        *,
        clients: list[LLMClient] | None = None,
        cache: ExplanationCache | None = None,
    ) -> None:
        self._cache = cache or ExplanationCache()
        self._clients: list[LLMClient] = (
            clients
            if clients is not None
            else [
                OllamaClient(model="deepseek-coder:6.7b"),
                OllamaClient(model="qwen3:4b"),
                AnthropicClient(),
            ]
        )
        # Track insights history in-memory (per-process lifetime)
        self._insights: dict[str, list[InsightEntry]] = {}

    async def analyze_fund(
        self,
        performance: FundPerformance,
        analysis_type: AnalysisType = AnalysisType.COMPREHENSIVE,
    ) -> FundAnalysisResponse:
        """Run LLM analysis for a fund.

        For COMPREHENSIVE, runs all three analysis types.
        Otherwise runs only the requested type.
        """
        t0 = time.monotonic()
        cnpj = performance.fund_cnpj
        fund_name = performance.fund_name

        if analysis_type == AnalysisType.COMPREHENSIVE:
            types_to_run = [
                AnalysisType.PERFORMANCE,
                AnalysisType.RISK,
                AnalysisType.RECOMMENDATION,
            ]
        else:
            types_to_run = [analysis_type]

        perf_analysis: PerformanceAnalysis | None = None
        risk_analysis: RiskAnalysis | None = None
        rec_analysis: RecommendationAnalysis | None = None

        provider = "static"
        model = "none"
        confidence = ConfidenceLevel.LOW
        cached = False
        fallback_used = False
        total_latency = 0.0

        for atype in types_to_run:
            result, meta = await self._run_single_analysis(atype, performance)
            total_latency += meta.get("latency_ms", 0.0)
            if meta.get("provider", "static") != "static":
                provider = meta["provider"]
                model = meta["model"]
                confidence = ConfidenceLevel.HIGH
            if meta.get("fallback_used", False):
                fallback_used = True
            if meta.get("cached", False):
                cached = True

            if atype == AnalysisType.PERFORMANCE:
                perf_analysis = result  # type: ignore[assignment]
            elif atype == AnalysisType.RISK:
                risk_analysis = result  # type: ignore[assignment]
            elif atype == AnalysisType.RECOMMENDATION:
                rec_analysis = result  # type: ignore[assignment]

        if provider == "static":
            confidence = ConfidenceLevel.LOW
        elif fallback_used:
            confidence = ConfidenceLevel.MEDIUM

        elapsed = (time.monotonic() - t0) * 1000

        response = FundAnalysisResponse(
            cnpj=cnpj,
            fund_name=fund_name,
            analysis_type=analysis_type,
            performance=perf_analysis,
            risk=risk_analysis,
            recommendation=rec_analysis,
            metadata=AnalysisMetadata(
                provider=provider,
                model=model,
                latency_ms=round(elapsed, 1),
                confidence=confidence,
                cached=cached,
                fallback_used=fallback_used,
            ),
            generated_at=datetime.now(),
        )

        # Store in insights history
        insight = InsightEntry(
            analysis_type=analysis_type,
            summary=(
                perf_analysis.summary
                if perf_analysis
                else (
                    risk_analysis.summary
                    if risk_analysis
                    else (rec_analysis.summary if rec_analysis else "No summary")
                )
            ),
            provider=provider,
            confidence=confidence,
            generated_at=response.generated_at,
        )
        self._insights.setdefault(cnpj, []).append(insight)

        return response

    def get_insights(self, cnpj: str) -> list[InsightEntry]:
        """Return historical insights for a fund."""
        return list(self._insights.get(cnpj, []))

    async def _run_single_analysis(
        self,
        analysis_type: AnalysisType,
        performance: FundPerformance,
    ) -> tuple[
        PerformanceAnalysis | RiskAnalysis | RecommendationAnalysis,
        dict[str, Any],
    ]:
        """Run a single analysis type through the LLM fallback chain."""
        prompt = _build_prompt(analysis_type, performance)
        cache_key = f"analysis:{performance.fund_cnpj}:{analysis_type.value}"

        # Check cache
        cached_text = self._cache.get(cache_key, 0.0, "")
        if cached_text is not None:
            try:
                parsed = _parse_llm_json(cached_text)
                result = self._parse_analysis_result(analysis_type, parsed, performance)
                return result, {
                    "provider": "cache",
                    "model": "cache",
                    "latency_ms": 0.0,
                    "cached": True,
                    "fallback_used": False,
                }
            except (json.JSONDecodeError, KeyError, ValueError):
                pass  # Cache corrupt, regenerate

        # Try LLM chain
        fallback_used = False
        for i, client in enumerate(self._clients):
            if i > 0:
                fallback_used = True
            try:
                resp: LLMResponse = await client.generate(
                    system_prompt=_SYSTEM_PROMPT,
                    user_prompt=prompt,
                    max_tokens=500,
                    temperature=0.3,
                )
                parsed = _parse_llm_json(resp.text)
                result = self._parse_analysis_result(analysis_type, parsed, performance)

                # Cache successful result
                self._cache.put(
                    cache_key,
                    0.0,
                    "",
                    resp.text,
                    provider=resp.provider,
                    model=resp.model,
                )

                return result, {
                    "provider": resp.provider,
                    "model": resp.model,
                    "latency_ms": resp.latency_ms,
                    "cached": False,
                    "fallback_used": fallback_used,
                }
            except (LLMClientError, json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning(
                    "LLM %s failed for %s analysis: %s",
                    client.provider_name,
                    analysis_type.value,
                    exc,
                )
                continue

        # Static fallback
        logger.info(
            "All LLM clients failed for %s, using static fallback",
            analysis_type.value,
        )
        result = self._build_static(analysis_type, performance)
        return result, {
            "provider": "static",
            "model": "none",
            "latency_ms": 0.0,
            "cached": False,
            "fallback_used": True,
        }

    def _parse_analysis_result(
        self,
        analysis_type: AnalysisType,
        data: dict[str, Any],
        performance: FundPerformance,
    ) -> PerformanceAnalysis | RiskAnalysis | RecommendationAnalysis:
        """Parse LLM JSON into the appropriate Pydantic model."""
        if analysis_type == AnalysisType.PERFORMANCE:
            return PerformanceAnalysis(**data)
        elif analysis_type == AnalysisType.RISK:
            return RiskAnalysis(**data)
        elif analysis_type == AnalysisType.RECOMMENDATION:
            return RecommendationAnalysis(**data)
        else:
            return _build_static_performance(performance)

    @staticmethod
    def _build_static(
        analysis_type: AnalysisType,
        performance: FundPerformance,
    ) -> PerformanceAnalysis | RiskAnalysis | RecommendationAnalysis:
        """Build static fallback for any analysis type."""
        if analysis_type == AnalysisType.PERFORMANCE:
            return _build_static_performance(performance)
        elif analysis_type == AnalysisType.RISK:
            return _build_static_risk(performance)
        elif analysis_type == AnalysisType.RECOMMENDATION:
            return _build_static_recommendation(performance)
        else:
            return _build_static_performance(performance)


# Module-level singleton for use by the router
_analysis_service: AnalysisService | None = None


def get_analysis_service() -> AnalysisService:
    """Get or create the module-level AnalysisService singleton."""
    global _analysis_service  # noqa: PLW0603
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service
