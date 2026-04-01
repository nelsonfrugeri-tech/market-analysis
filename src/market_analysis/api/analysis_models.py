"""Pydantic models for AI-powered fund analysis endpoints.

Defines request/response schemas for DeepSeek/Ollama LLM integration.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AnalysisType(StrEnum):
    """Types of LLM-powered analysis."""

    PERFORMANCE = "performance"
    RISK = "risk"
    RECOMMENDATION = "recommendation"
    COMPREHENSIVE = "comprehensive"


class ConfidenceLevel(StrEnum):
    """Confidence level of analysis output."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PerformanceAnalysis(BaseModel):
    """LLM-generated performance analysis."""

    summary: str = Field(..., description="Performance summary text")
    return_assessment: str = Field(
        ..., description="Assessment of returns vs benchmarks"
    )
    trend_outlook: str = Field(..., description="Short-term trend outlook")
    highlights: list[str] = Field(default_factory=list, description="Key highlights")


class RiskAnalysis(BaseModel):
    """LLM-generated risk analysis."""

    summary: str = Field(..., description="Risk summary text")
    risk_classification: str = Field(
        ..., description="Risk classification (conservative/moderate/aggressive)"
    )
    sharpe_assessment: str = Field(..., description="Sharpe ratio interpretation")
    drawdown_assessment: str = Field(..., description="Max drawdown interpretation")
    warnings: list[str] = Field(default_factory=list, description="Risk warnings")


class RecommendationAnalysis(BaseModel):
    """LLM-generated investment recommendation."""

    summary: str = Field(..., description="Recommendation summary")
    action: str = Field(..., description="Suggested action (hold/buy/reduce)")
    allocation_suggestion: str = Field(
        ..., description="Portfolio allocation suggestion"
    )
    considerations: list[str] = Field(
        default_factory=list, description="Important considerations"
    )


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis generation."""

    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used for generation")
    latency_ms: float = Field(..., description="Generation latency in ms")
    confidence: ConfidenceLevel = Field(
        ..., description="Confidence level of the analysis"
    )
    cached: bool = Field(default=False, description="Whether result was cached")
    fallback_used: bool = Field(
        default=False, description="Whether a fallback provider was used"
    )


class FundAnalysisResponse(BaseModel):
    """Complete fund analysis response from LLM."""

    cnpj: str = Field(..., description="Fund CNPJ")
    fund_name: str = Field(..., description="Fund name")
    analysis_type: AnalysisType = Field(..., description="Type of analysis performed")
    performance: PerformanceAnalysis | None = Field(
        None, description="Performance analysis"
    )
    risk: RiskAnalysis | None = Field(None, description="Risk analysis")
    recommendation: RecommendationAnalysis | None = Field(
        None, description="Recommendation analysis"
    )
    metadata: AnalysisMetadata = Field(..., description="Analysis generation metadata")
    generated_at: datetime = Field(..., description="Generation timestamp")


class InsightEntry(BaseModel):
    """A single historical insight entry."""

    analysis_type: AnalysisType
    summary: str
    provider: str
    confidence: ConfidenceLevel
    generated_at: datetime


class FundInsightsResponse(BaseModel):
    """Historical insights plus latest analysis for a fund."""

    cnpj: str = Field(..., description="Fund CNPJ")
    fund_name: str = Field(..., description="Fund name")
    latest_analysis: FundAnalysisResponse | None = Field(
        None, description="Most recent analysis"
    )
    history: list[InsightEntry] = Field(
        default_factory=list, description="Historical insights"
    )
    total_analyses: int = Field(
        default=0, description="Total number of analyses performed"
    )


class BatchAnalysisRequest(BaseModel):
    """Request for batch analysis of multiple funds."""

    cnpjs: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of fund CNPJs to analyze",
    )
    analysis_type: AnalysisType = Field(
        default=AnalysisType.COMPREHENSIVE,
        description="Type of analysis to perform",
    )


class BatchAnalysisItem(BaseModel):
    """Single item in a batch analysis response."""

    cnpj: str
    status: Literal["success", "error"] = "success"
    analysis: FundAnalysisResponse | None = None
    error: str | None = None


class BatchAnalysisResponse(BaseModel):
    """Batch analysis response."""

    total: int = Field(..., description="Total requested")
    succeeded: int = Field(..., description="Number of successful analyses")
    failed: int = Field(..., description="Number of failed analyses")
    results: list[BatchAnalysisItem] = Field(..., description="Individual results")
    total_latency_ms: float = Field(..., description="Total processing time in ms")
