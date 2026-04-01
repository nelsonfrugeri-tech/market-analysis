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


class PerformanceResponse(BaseModel):
    """Complete performance metrics response."""
    fund: FundSummary
    period: Dict[str, Any] = Field(..., description="Analysis period info")
    performance: Dict[str, float] = Field(..., description="Return metrics")
    risk: Dict[str, float] = Field(..., description="Risk metrics")
    efficiency: Dict[str, float] = Field(..., description="Risk-adjusted metrics")
    benchmarks: Dict[str, Any] = Field(..., description="Benchmark comparisons")
    market: Dict[str, Any] = Field(..., description="Market context")
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