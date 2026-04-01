"""
Pydantic models for API request/response schemas.

These models define the exact structure of API responses as agreed in the contract.
All fields are strongly typed -- no Dict[str, Any] allowed.
"""

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel, Field


class FundSummary(BaseModel):
    """Fund basic information for listings and metadata."""

    cnpj: str = Field(..., description="CNPJ identifier")
    name: str = Field(..., description="Full fund name")
    short_name: str = Field(..., description="Short display name")
    fund_type: str = Field(..., description="Type of fund (e.g., Renda Fixa)")
    manager: str = Field(..., description="Asset manager name")
    benchmark: str = Field(..., description="Primary benchmark (e.g., CDI)")
    status: str = Field(..., description="Fund status (active/inactive)")


class PeriodInfo(BaseModel):
    """Analysis period details."""

    start: date_type = Field(..., description="Start date")
    end: date_type = Field(..., description="End date")
    days: int = Field(..., description="Number of days analyzed")


class PerformanceMetrics(BaseModel):
    """Fund performance metrics."""

    return_pct: float = Field(..., description="Return percentage")
    nav_start: float = Field(..., description="NAV at start")
    nav_end: float = Field(..., description="NAV at end")


class RiskMetrics(BaseModel):
    """Risk metrics."""

    volatility: float = Field(..., description="Annualized volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    var_95: float = Field(..., description="Value at Risk 95%")


class EfficiencyMetrics(BaseModel):
    """Risk-adjusted efficiency metrics."""

    alpha: float = Field(..., description="Alpha vs benchmark")
    beta: float = Field(..., description="Beta sensitivity")


class BenchmarkDetail(BaseModel):
    """Single benchmark comparison detail."""

    accumulated: float = Field(..., description="Accumulated benchmark return")
    vs_fund: float = Field(..., description="Basis points vs fund return")


class BenchmarkEstimate(BaseModel):
    """Estimated benchmark value."""

    estimated: float = Field(..., description="Estimated benchmark return")


class BenchmarkComparison(BaseModel):
    """Full benchmark comparison data with typed sub-models."""

    cdi: BenchmarkDetail = Field(..., description="CDI benchmark comparison")
    selic: BenchmarkDetail = Field(..., description="SELIC benchmark comparison")
    ipca: BenchmarkDetail = Field(..., description="IPCA benchmark comparison")
    cdb: BenchmarkEstimate = Field(..., description="CDB estimated return")
    poupanca: BenchmarkEstimate = Field(
        ..., description="Poupanca estimated return"
    )


class MarketContext(BaseModel):
    """Market context information."""

    trend_30d: str = Field(..., description="30-day trend (up/down/flat)")
    shareholders: int = Field(..., description="Current number of shareholders")
    equity_millions: float = Field(
        ..., description="Fund equity in millions (BRL)"
    )


class PerformanceResponse(BaseModel):
    """Complete performance metrics response."""

    fund: FundSummary
    period: PeriodInfo = Field(..., description="Analysis period info")
    performance: PerformanceMetrics = Field(..., description="Return metrics")
    risk: RiskMetrics = Field(..., description="Risk metrics")
    efficiency: EfficiencyMetrics = Field(
        ..., description="Risk-adjusted metrics"
    )
    benchmarks: BenchmarkComparison = Field(
        ..., description="Benchmark comparisons"
    )
    market: MarketContext = Field(..., description="Market context")
    updated_at: datetime = Field(..., description="Response timestamp")


class DailyDataResponse(BaseModel):
    """Daily time series data point for charts."""

    date: date_type = Field(..., description="Trading date")
    nav: float = Field(..., description="Net Asset Value")
    equity: float = Field(..., description="Total fund equity")
    deposits: float = Field(..., description="Daily deposits")
    withdrawals: float = Field(..., description="Daily withdrawals")
    shareholders: int = Field(..., description="Number of shareholders")
    net_flow: float = Field(..., description="Net flow (deposits - withdrawals)")


class MetricExplanation(BaseModel):
    """Metric explanation for tooltips."""

    key: str = Field(..., description="Metric identifier")
    name: str = Field(..., description="Display name")
    value: float | None = Field(None, description="Current value (optional)")
    explanation: str = Field(..., description="User-friendly explanation")
    category: str = Field(
        ..., description="Metric category (performance/risk/efficiency)"
    )


class CollectionResponse(BaseModel):
    """Data collection trigger response."""

    status: str = Field(..., description="Collection status (success/error)")
    items_collected: int = Field(
        ..., description="Number of data items collected"
    )
    duration_secs: float = Field(
        ..., description="Collection duration in seconds"
    )
    timestamp: datetime = Field(..., description="Collection timestamp")
    error: str | None = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """API health check response."""

    status: str = Field(
        ..., description="Health status (healthy/unhealthy)"
    )
    timestamp: datetime = Field(..., description="Check timestamp")
    database_connected: bool = Field(
        ..., description="Database connectivity status"
    )
    last_collection: datetime | None = Field(
        None, description="Last successful collection"
    )
    error: str | None = Field(
        None, description="Error details if unhealthy"
    )
