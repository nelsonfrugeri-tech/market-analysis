"""FastAPI router for AI-powered fund analysis endpoints.

Provides 3 endpoints:
- POST /api/v1/funds/{cnpj}/analysis -- Full LLM analysis
- GET  /api/v1/funds/{cnpj}/insights -- Historical insights
- POST /api/v1/analysis/batch        -- Batch analysis
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Query
from fastapi import Path as FastAPIPath

from market_analysis.api.analysis_models import (
    AnalysisType,
    BatchAnalysisItem,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    FundAnalysisResponse,
    FundInsightsResponse,
)
from market_analysis.api.analysis_service import get_analysis_service
from market_analysis.api.service import calculate_fund_performance

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/funds/{cnpj:path}/analysis",
    response_model=FundAnalysisResponse,
)
async def analyze_fund(
    cnpj: str = FastAPIPath(..., description="Fund CNPJ"),
    analysis_type: AnalysisType = Query(
        default=AnalysisType.COMPREHENSIVE,
        description="Type of analysis to perform",
    ),
    months: int = Query(
        default=3, ge=1, le=60, description="Months of data for analysis"
    ),
) -> FundAnalysisResponse:
    """Run AI-powered analysis on a fund using DeepSeek/Ollama.

    Falls back through: DeepSeek -> Qwen3:4b -> Anthropic -> Static analysis.
    """
    try:
        performance = await calculate_fund_performance(cnpj=cnpj, months=months)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching fund data: {e}",
        ) from e

    service = get_analysis_service()
    return await service.analyze_fund(performance, analysis_type)


@router.get(
    "/funds/{cnpj:path}/insights",
    response_model=FundInsightsResponse,
)
async def get_fund_insights(
    cnpj: str = FastAPIPath(..., description="Fund CNPJ"),
) -> FundInsightsResponse:
    """Get historical insights and latest analysis for a fund.

    Returns cached insights from previous analyses plus the latest one.
    """
    service = get_analysis_service()
    insights = service.get_insights(cnpj)

    # Try to get latest analysis if none exists
    latest: FundAnalysisResponse | None = None
    if not insights:
        try:
            performance = await calculate_fund_performance(cnpj=cnpj, months=3)
            latest = await service.analyze_fund(performance, AnalysisType.COMPREHENSIVE)
            insights = service.get_insights(cnpj)
        except (ValueError, Exception):
            pass  # No data available, return empty

    return FundInsightsResponse(
        cnpj=cnpj,
        fund_name="Nu Reserva Planejada",
        latest_analysis=latest,
        history=insights,
        total_analyses=len(insights),
    )


@router.post(
    "/analysis/batch",
    response_model=BatchAnalysisResponse,
)
async def batch_analysis(
    request: BatchAnalysisRequest,
) -> BatchAnalysisResponse:
    """Run analysis for multiple funds in batch."""
    t0 = time.monotonic()
    service = get_analysis_service()
    results: list[BatchAnalysisItem] = []
    succeeded = 0
    failed = 0

    for cnpj in request.cnpjs:
        try:
            performance = await calculate_fund_performance(cnpj=cnpj, months=3)
            analysis = await service.analyze_fund(performance, request.analysis_type)
            results.append(
                BatchAnalysisItem(cnpj=cnpj, status="success", analysis=analysis)
            )
            succeeded += 1
        except Exception as e:
            results.append(BatchAnalysisItem(cnpj=cnpj, status="error", error=str(e)))
            failed += 1

    elapsed = (time.monotonic() - t0) * 1000

    return BatchAnalysisResponse(
        total=len(request.cnpjs),
        succeeded=succeeded,
        failed=failed,
        results=results,
        total_latency_ms=round(elapsed, 1),
    )
