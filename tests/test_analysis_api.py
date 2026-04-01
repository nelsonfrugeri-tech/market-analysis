"""Tests for AI-powered fund analysis endpoints (v0.3.0).

Covers:
- POST /api/v1/funds/{cnpj}/analysis
- GET  /api/v1/funds/{cnpj}/insights
- POST /api/v1/analysis/batch
- AnalysisService fallback chain
- Static fallback generation
- LLM JSON parsing
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from market_analysis.ai.cache import ExplanationCache
from market_analysis.ai.clients.base import LLMClientError, LLMResponse
from market_analysis.api.analysis_models import (
    AnalysisType,
    ConfidenceLevel,
)
from market_analysis.api.analysis_service import (
    AnalysisService,
    _build_prompt,
    _build_static_performance,
    _build_static_recommendation,
    _build_static_risk,
    _parse_llm_json,
)
from market_analysis.api.main import app
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NU_RESERVA_CNPJ = "43.121.002/0001-41"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fresh_cache(tmp_path: Path) -> ExplanationCache:
    """Provide a fresh cache that doesn't interfere between tests."""
    return ExplanationCache(cache_dir=tmp_path / "test_cache")


@pytest.fixture
def sample_performance() -> FundPerformance:
    return FundPerformance(
        fund_cnpj=NU_RESERVA_CNPJ,
        fund_name="Nu Reserva Planejada",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 3, 31),
        nav_start=1.234567,
        nav_end=1.256789,
        return_pct=0.018,
        equity_start=500_000_000.0,
        equity_end=520_000_000.0,
        volatility=0.0123,
        shareholders_current=150_000,
        benchmark_selic=0.032,
        benchmark_cdi=0.031,
        benchmark_ipca=0.012,
        vs_selic=-14.0,
        vs_cdi=-13.0,
        vs_ipca=6.0,
        trend_30d="up",
        sharpe_ratio=1.45,
        alpha=0.002,
        beta=0.95,
        var_95=-0.003,
        max_drawdown=-0.005,
    )


@pytest.fixture
def sample_daily_records() -> list[FundDailyRecord]:
    return [
        FundDailyRecord(
            cnpj=NU_RESERVA_CNPJ,
            date=date(2025, 3, 28),
            nav=1.254321,
            equity=518_000_000.0,
            total_value=518_000_000.0,
            deposits=1_000_000.0,
            withdrawals=500_000.0,
            shareholders=149_500,
        ),
        FundDailyRecord(
            cnpj=NU_RESERVA_CNPJ,
            date=date(2025, 3, 31),
            nav=1.256789,
            equity=520_000_000.0,
            total_value=520_000_000.0,
            deposits=2_000_000.0,
            withdrawals=800_000.0,
            shareholders=150_000,
        ),
    ]


@pytest.fixture
def mock_llm_performance_response() -> LLMResponse:
    return LLMResponse(
        text=json.dumps(
            {
                "summary": "Fundo apresentou bom desempenho.",
                "return_assessment": "Retorno acima da media.",
                "trend_outlook": "Tendencia positiva.",
                "highlights": ["Sharpe alto", "Baixa volatilidade"],
            }
        ),
        model="deepseek-coder:6.7b",
        latency_ms=500.0,
        provider="ollama",
    )


@pytest.fixture
def mock_llm_risk_response() -> LLMResponse:
    return LLMResponse(
        text=json.dumps(
            {
                "summary": "Perfil de risco conservador.",
                "risk_classification": "conservative",
                "sharpe_assessment": "Sharpe excelente.",
                "drawdown_assessment": "Drawdown baixo.",
                "warnings": [],
            }
        ),
        model="deepseek-coder:6.7b",
        latency_ms=450.0,
        provider="ollama",
    )


@pytest.fixture
def mock_llm_recommendation_response() -> LLMResponse:
    return LLMResponse(
        text=json.dumps(
            {
                "summary": "Recomendacao de manter posicao.",
                "action": "hold",
                "allocation_suggestion": "Manter 10% do portfolio.",
                "considerations": ["Mercado estavel"],
            }
        ),
        model="deepseek-coder:6.7b",
        latency_ms=400.0,
        provider="ollama",
    )


# ---------------------------------------------------------------------------
# Unit tests: _parse_llm_json
# ---------------------------------------------------------------------------


class TestParseLlmJson:
    def test_parse_clean_json(self) -> None:
        text = '{"key": "value"}'
        assert _parse_llm_json(text) == {"key": "value"}

    def test_parse_json_with_code_fences(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert _parse_llm_json(text) == {"key": "value"}

    def test_parse_json_with_whitespace(self) -> None:
        text = '  \n  {"key": "value"}  \n  '
        assert _parse_llm_json(text) == {"key": "value"}

    def test_parse_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_json("not json at all")


# ---------------------------------------------------------------------------
# Unit tests: _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_performance_prompt_contains_fund_name(
        self, sample_performance: FundPerformance
    ) -> None:
        prompt = _build_prompt(AnalysisType.PERFORMANCE, sample_performance)
        assert "Nu Reserva Planejada" in prompt
        assert "return" in prompt.lower() or "Return" in prompt

    def test_risk_prompt_contains_volatility(
        self, sample_performance: FundPerformance
    ) -> None:
        prompt = _build_prompt(AnalysisType.RISK, sample_performance)
        assert "Volatility" in prompt or "volatility" in prompt.lower()

    def test_recommendation_prompt_contains_action(
        self, sample_performance: FundPerformance
    ) -> None:
        prompt = _build_prompt(AnalysisType.RECOMMENDATION, sample_performance)
        assert "recommendation" in prompt.lower() or "Recommendation" in prompt


# ---------------------------------------------------------------------------
# Unit tests: static fallbacks
# ---------------------------------------------------------------------------


class TestStaticFallbacks:
    def test_static_performance_positive_vs_cdi(
        self, sample_performance: FundPerformance
    ) -> None:
        # vs_cdi is -13 (below)
        result = _build_static_performance(sample_performance)
        assert "abaixo" in result.summary
        assert len(result.highlights) >= 1

    def test_static_risk_conservative(
        self, sample_performance: FundPerformance
    ) -> None:
        result = _build_static_risk(sample_performance)
        assert result.risk_classification == "conservative"

    def test_static_risk_aggressive(self, sample_performance: FundPerformance) -> None:
        perf = FundPerformance(
            fund_cnpj=NU_RESERVA_CNPJ,
            fund_name="Test",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            nav_start=1.0,
            nav_end=1.1,
            return_pct=0.1,
            equity_start=100.0,
            equity_end=110.0,
            volatility=0.15,
            shareholders_current=100,
            benchmark_selic=0.03,
            benchmark_cdi=0.03,
            benchmark_ipca=0.01,
            vs_selic=70.0,
            vs_cdi=70.0,
            vs_ipca=90.0,
            trend_30d="up",
            sharpe_ratio=0.5,
            alpha=0.01,
            beta=1.2,
            var_95=-0.02,
            max_drawdown=-0.08,
        )
        result = _build_static_risk(perf)
        assert result.risk_classification == "aggressive"

    def test_static_recommendation_buy(self) -> None:
        perf = FundPerformance(
            fund_cnpj=NU_RESERVA_CNPJ,
            fund_name="Test",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            nav_start=1.0,
            nav_end=1.1,
            return_pct=0.1,
            equity_start=100.0,
            equity_end=110.0,
            volatility=0.05,
            shareholders_current=100,
            benchmark_selic=0.03,
            benchmark_cdi=0.03,
            benchmark_ipca=0.01,
            vs_selic=70.0,
            vs_cdi=70.0,
            vs_ipca=90.0,
            trend_30d="up",
            sharpe_ratio=1.5,
            alpha=0.01,
            beta=1.0,
            var_95=-0.01,
            max_drawdown=-0.03,
        )
        result = _build_static_recommendation(perf)
        assert result.action == "buy"

    def test_static_recommendation_reduce(self) -> None:
        perf = FundPerformance(
            fund_cnpj=NU_RESERVA_CNPJ,
            fund_name="Test",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 3, 31),
            nav_start=1.0,
            nav_end=0.9,
            return_pct=-0.1,
            equity_start=100.0,
            equity_end=90.0,
            volatility=0.15,
            shareholders_current=100,
            benchmark_selic=0.03,
            benchmark_cdi=0.03,
            benchmark_ipca=0.01,
            vs_selic=-130.0,
            vs_cdi=-130.0,
            vs_ipca=-110.0,
            trend_30d="down",
            sharpe_ratio=-0.5,
            alpha=-0.02,
            beta=1.3,
            var_95=-0.05,
            max_drawdown=-0.15,
        )
        result = _build_static_recommendation(perf)
        assert result.action == "reduce"


# ---------------------------------------------------------------------------
# Unit tests: AnalysisService
# ---------------------------------------------------------------------------


class TestAnalysisService:
    @pytest.mark.asyncio
    async def test_analyze_fund_with_llm_success(
        self,
        sample_performance: FundPerformance,
        mock_llm_performance_response: LLMResponse,
        mock_llm_risk_response: LLMResponse,
        mock_llm_recommendation_response: LLMResponse,
        fresh_cache: ExplanationCache,
    ) -> None:
        """Service returns LLM-powered analysis when available."""
        mock_client = AsyncMock()
        mock_client.provider_name = "ollama"
        mock_client.generate = AsyncMock(
            side_effect=[
                mock_llm_performance_response,
                mock_llm_risk_response,
                mock_llm_recommendation_response,
            ]
        )

        service = AnalysisService(clients=[mock_client], cache=fresh_cache)
        result = await service.analyze_fund(
            sample_performance, AnalysisType.COMPREHENSIVE
        )

        assert result.cnpj == NU_RESERVA_CNPJ
        assert result.performance is not None
        assert result.risk is not None
        assert result.recommendation is not None
        assert result.metadata.provider == "ollama"
        assert result.metadata.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_analyze_fund_falls_back_to_static(
        self,
        sample_performance: FundPerformance,
        fresh_cache: ExplanationCache,
    ) -> None:
        """Service falls back to static when all LLMs fail."""
        mock_client = AsyncMock()
        mock_client.provider_name = "ollama"
        mock_client.generate = AsyncMock(
            side_effect=LLMClientError("Connection refused")
        )

        service = AnalysisService(clients=[mock_client], cache=fresh_cache)
        result = await service.analyze_fund(
            sample_performance, AnalysisType.PERFORMANCE
        )

        assert result.performance is not None
        assert result.metadata.provider == "static"
        assert result.metadata.confidence == ConfidenceLevel.LOW

    @pytest.mark.asyncio
    async def test_analyze_fund_fallback_chain(
        self,
        sample_performance: FundPerformance,
        mock_llm_performance_response: LLMResponse,
        fresh_cache: ExplanationCache,
    ) -> None:
        """First client fails, second succeeds."""
        failing_client = AsyncMock()
        failing_client.provider_name = "deepseek"
        failing_client.generate = AsyncMock(side_effect=LLMClientError("timeout"))

        working_client = AsyncMock()
        working_client.provider_name = "qwen"
        working_client.generate = AsyncMock(return_value=mock_llm_performance_response)

        service = AnalysisService(
            clients=[failing_client, working_client], cache=fresh_cache
        )
        result = await service.analyze_fund(
            sample_performance, AnalysisType.PERFORMANCE
        )

        assert result.performance is not None
        assert result.metadata.fallback_used is True
        assert result.metadata.confidence == ConfidenceLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_analyze_fund_single_type(
        self,
        sample_performance: FundPerformance,
        mock_llm_risk_response: LLMResponse,
        fresh_cache: ExplanationCache,
    ) -> None:
        """Single analysis type returns only that section."""
        mock_client = AsyncMock()
        mock_client.provider_name = "ollama"
        mock_client.generate = AsyncMock(return_value=mock_llm_risk_response)

        service = AnalysisService(clients=[mock_client], cache=fresh_cache)
        result = await service.analyze_fund(sample_performance, AnalysisType.RISK)

        assert result.risk is not None
        assert result.performance is None
        assert result.recommendation is None

    @pytest.mark.asyncio
    async def test_insights_stored(
        self,
        sample_performance: FundPerformance,
        fresh_cache: ExplanationCache,
    ) -> None:
        """Insights are accumulated in history."""
        mock_client = AsyncMock()
        mock_client.provider_name = "ollama"
        mock_client.generate = AsyncMock(side_effect=LLMClientError("fail"))

        service = AnalysisService(clients=[mock_client], cache=fresh_cache)
        await service.analyze_fund(sample_performance, AnalysisType.PERFORMANCE)
        await service.analyze_fund(sample_performance, AnalysisType.RISK)

        insights = service.get_insights(NU_RESERVA_CNPJ)
        assert len(insights) == 2

    @pytest.mark.asyncio
    async def test_llm_returns_invalid_json_falls_back(
        self,
        sample_performance: FundPerformance,
        fresh_cache: ExplanationCache,
    ) -> None:
        """If LLM returns invalid JSON, falls back to static."""
        mock_client = AsyncMock()
        mock_client.provider_name = "ollama"
        mock_client.generate = AsyncMock(
            return_value=LLMResponse(
                text="This is not valid JSON at all",
                model="test",
                latency_ms=100.0,
                provider="ollama",
            )
        )

        service = AnalysisService(clients=[mock_client], cache=fresh_cache)
        result = await service.analyze_fund(
            sample_performance, AnalysisType.PERFORMANCE
        )

        assert result.performance is not None
        assert result.metadata.provider == "static"


# ---------------------------------------------------------------------------
# Integration tests: API endpoints
# ---------------------------------------------------------------------------


class TestAnalysisEndpoint:
    """POST /api/v1/funds/{cnpj}/analysis tests."""

    def test_analysis_endpoint_returns_200(
        self,
        client: TestClient,
        sample_performance: FundPerformance,
    ) -> None:
        """Analysis endpoint returns 200 with static fallback."""
        from market_analysis.api import analysis_router as router_mod
        from market_analysis.api import analysis_service as svc_mod

        async def fake_calc(**kwargs: object) -> FundPerformance:
            return sample_performance

        original_calc = router_mod.calculate_fund_performance
        router_mod.calculate_fund_performance = fake_calc  # type: ignore[assignment]
        svc_mod._analysis_service = AnalysisService(
            clients=[],
            cache=ExplanationCache(cache_dir=Path(tempfile.mkdtemp())),
        )

        try:
            response = client.post(
                f"/api/v1/funds/{NU_RESERVA_CNPJ}/analysis",
                params={"analysis_type": "performance", "months": 3},
            )
            assert response.status_code == 200

            data = response.json()
            assert data["cnpj"] == NU_RESERVA_CNPJ
            assert data["analysis_type"] == "performance"
            assert data["performance"] is not None
            assert data["metadata"]["provider"] == "static"
        finally:
            router_mod.calculate_fund_performance = original_calc  # type: ignore[assignment]
            svc_mod._analysis_service = None

    def test_analysis_endpoint_invalid_cnpj(
        self,
        client: TestClient,
    ) -> None:
        """Invalid CNPJ returns 400."""
        from market_analysis.api import analysis_router as router_mod

        async def fake_calc(**kwargs: object) -> FundPerformance:
            raise ValueError("Only Nu Reserva CNPJ supported")

        original = router_mod.calculate_fund_performance
        router_mod.calculate_fund_performance = fake_calc  # type: ignore[assignment]
        try:
            response = client.post(
                "/api/v1/funds/00.000.000%2F0000-00/analysis",
                params={"months": 3},
            )
            assert response.status_code == 400
        finally:
            router_mod.calculate_fund_performance = original  # type: ignore[assignment]

    def test_analysis_endpoint_invalid_months(self, client: TestClient) -> None:
        """months=0 returns 422."""
        response = client.post(
            f"/api/v1/funds/{NU_RESERVA_CNPJ}/analysis",
            params={"months": 0},
        )
        assert response.status_code == 422


class TestInsightsEndpoint:
    """GET /api/v1/funds/{cnpj}/insights tests."""

    def test_insights_returns_200(
        self,
        client: TestClient,
        sample_performance: FundPerformance,
    ) -> None:
        """Insights endpoint returns 200."""
        from market_analysis.api import analysis_router as router_mod
        from market_analysis.api import analysis_service as svc_mod

        async def fake_calc(**kwargs: object) -> FundPerformance:
            return sample_performance

        original = router_mod.calculate_fund_performance
        router_mod.calculate_fund_performance = fake_calc  # type: ignore[assignment]
        svc_mod._analysis_service = AnalysisService(
            clients=[],
            cache=ExplanationCache(cache_dir=Path(tempfile.mkdtemp())),
        )
        try:
            response = client.get(f"/api/v1/funds/{NU_RESERVA_CNPJ}/insights")
            assert response.status_code == 200
            data = response.json()
            assert data["cnpj"] == NU_RESERVA_CNPJ
            assert "history" in data
            assert "total_analyses" in data
        finally:
            router_mod.calculate_fund_performance = original  # type: ignore[assignment]
            svc_mod._analysis_service = None

    def test_insights_no_data_returns_empty(
        self,
        client: TestClient,
    ) -> None:
        """Insights with unsupported CNPJ returns empty history."""
        from market_analysis.api import analysis_router as router_mod
        from market_analysis.api import analysis_service as svc_mod

        async def fake_calc(**kwargs: object) -> FundPerformance:
            raise ValueError("Unsupported CNPJ")

        original = router_mod.calculate_fund_performance
        router_mod.calculate_fund_performance = fake_calc  # type: ignore[assignment]
        svc_mod._analysis_service = AnalysisService(
            clients=[],
            cache=ExplanationCache(cache_dir=Path(tempfile.mkdtemp())),
        )
        try:
            response = client.get("/api/v1/funds/00.000.000%2F0000-00/insights")
            assert response.status_code == 200
            data = response.json()
            assert data["history"] == []
            assert data["total_analyses"] == 0
        finally:
            router_mod.calculate_fund_performance = original  # type: ignore[assignment]
            svc_mod._analysis_service = None


class TestBatchAnalysisEndpoint:
    """POST /api/v1/analysis/batch tests."""

    def test_batch_analysis_success(
        self,
        client: TestClient,
        sample_performance: FundPerformance,
    ) -> None:
        """Batch with valid CNPJs returns results."""
        from market_analysis.api import analysis_router as router_mod
        from market_analysis.api import analysis_service as svc_mod

        async def fake_calc(**kwargs: object) -> FundPerformance:
            return sample_performance

        original = router_mod.calculate_fund_performance
        router_mod.calculate_fund_performance = fake_calc  # type: ignore[assignment]
        svc_mod._analysis_service = AnalysisService(
            clients=[],
            cache=ExplanationCache(cache_dir=Path(tempfile.mkdtemp())),
        )
        try:
            response = client.post(
                "/api/v1/analysis/batch",
                json={
                    "cnpjs": [NU_RESERVA_CNPJ],
                    "analysis_type": "performance",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["succeeded"] == 1
            assert data["failed"] == 0
            assert len(data["results"]) == 1
            assert data["results"][0]["status"] == "success"
        finally:
            router_mod.calculate_fund_performance = original  # type: ignore[assignment]
            svc_mod._analysis_service = None

    def test_batch_analysis_mixed_results(
        self,
        client: TestClient,
    ) -> None:
        """Batch with invalid CNPJ returns error for that item."""
        from market_analysis.api import analysis_router as router_mod
        from market_analysis.api import analysis_service as svc_mod

        async def fake_calc(**kwargs: object) -> FundPerformance:
            raise ValueError("Unsupported CNPJ")

        original = router_mod.calculate_fund_performance
        router_mod.calculate_fund_performance = fake_calc  # type: ignore[assignment]
        svc_mod._analysis_service = AnalysisService(
            clients=[],
            cache=ExplanationCache(cache_dir=Path(tempfile.mkdtemp())),
        )
        try:
            response = client.post(
                "/api/v1/analysis/batch",
                json={
                    "cnpjs": ["00.000.000/0000-00"],
                    "analysis_type": "performance",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["failed"] == 1
            assert data["results"][0]["status"] == "error"
        finally:
            router_mod.calculate_fund_performance = original  # type: ignore[assignment]
            svc_mod._analysis_service = None

    def test_batch_analysis_empty_cnpjs(self, client: TestClient) -> None:
        """Empty CNPJs list returns 422."""
        response = client.post(
            "/api/v1/analysis/batch",
            json={"cnpjs": []},
        )
        assert response.status_code == 422

    def test_batch_analysis_too_many_cnpjs(self, client: TestClient) -> None:
        """More than 10 CNPJs returns 422."""
        response = client.post(
            "/api/v1/analysis/batch",
            json={"cnpjs": [f"cnpj-{i}" for i in range(11)]},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Regression: existing endpoints still work
# ---------------------------------------------------------------------------


class TestExistingEndpointsRegression:
    """Ensure v0.2.0 endpoints still work after adding analysis router."""

    def test_health_still_works(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_funds_list_still_works(self, client: TestClient) -> None:
        response = client.get("/api/v1/funds")
        assert response.status_code == 200

    def test_explanations_still_work(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/funds/{NU_RESERVA_CNPJ}/explanations")
        assert response.status_code == 200

    def test_openapi_version_updated(self, client: TestClient) -> None:
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["version"] == "0.3.0"
