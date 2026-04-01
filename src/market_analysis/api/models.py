"""
Pydantic models for API request/response schemas.

These models define the exact structure of API responses as agreed in the contract.
"""

from datetime import datetime
from datetime import date as date_type
from typing import Any, Dict, List, Optional

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
    return_pct: Optional[float] = Field(None, description="Return percentage")
    nav_start: Optional[float] = Field(None, description="NAV at start")
    nav_end: Optional[float] = Field(None, description="NAV at end")


class RiskMetrics(BaseModel):
    """Risk metrics."""
    volatility: Optional[float] = Field(None, description="Annualized volatility")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    var_95: Optional[float] = Field(None, description="Value at Risk 95%")


class EfficiencyMetrics(BaseModel):
    """Risk-adjusted efficiency metrics."""
    alpha: Optional[float] = Field(None, description="Alpha vs benchmark")
    beta: Optional[float] = Field(None, description="Beta sensitivity")


class BenchmarkComparison(BaseModel):
    """Benchmark comparison data."""
    cdi: Optional[float] = Field(None, description="CDI benchmark return")
    selic: Optional[float] = Field(None, description="SELIC benchmark return")
    ipca: Optional[float] = Field(None, description="IPCA benchmark return")


class MarketContext(BaseModel):
    """Market context information."""
    status: str = Field(..., description="Market status")
    last_updated: datetime = Field(..., description="Last update time")


class PerformanceResponse(BaseModel):
    """Complete performance metrics response."""
    fund: FundSummary
    period: PeriodInfo = Field(..., description="Analysis period info")
    performance: PerformanceMetrics = Field(..., description="Return metrics")
    risk: RiskMetrics = Field(..., description="Risk metrics")
    efficiency: EfficiencyMetrics = Field(..., description="Risk-adjusted metrics")
    benchmarks: BenchmarkComparison = Field(..., description="Benchmark comparisons")
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
    value: Optional[float] = Field(None, description="Current value (optional)")
    explanation: str = Field(..., description="User-friendly explanation")
    category: str = Field(..., description="Metric category (performance/risk/efficiency)")


class CollectionResponse(BaseModel):
    """Data collection trigger response."""
    status: str = Field(..., description="Collection status (success/error)")
    items_collected: int = Field(..., description="Number of data items collected")
    duration_secs: float = Field(..., description="Collection duration in seconds")
    timestamp: datetime = Field(..., description="Collection timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = Field(..., description="Health status (healthy/unhealthy)")
    timestamp: datetime = Field(..., description="Check timestamp")
    database_connected: bool = Field(..., description="Database connectivity status")
    last_collection: Optional[datetime] = Field(None, description="Last successful collection")
    error: Optional[str] = Field(None, description="Error details if unhealthy")