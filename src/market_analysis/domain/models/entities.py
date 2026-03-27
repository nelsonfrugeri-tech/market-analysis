"""Domain entities mapped to the SQLite schema."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BCBRecord(BaseModel):
    """A single BCB indicator data point (SELIC, CDI, IPCA)."""

    model_config = ConfigDict(frozen=True)

    date: date
    indicator: str
    value: float
    collected_at: datetime | None = None

    @field_validator("indicator")
    @classmethod
    def validate_indicator(cls, v: str) -> str:
        allowed = {"SELIC", "CDI", "IPCA"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"indicator must be one of {allowed}, got '{v}'")
        return upper


class NewsRecord(BaseModel):
    """A news article from Google News."""

    model_config = ConfigDict(frozen=True)

    title: str
    link: str
    pub_date: datetime
    description: str | None = None
    source: str
    collected_at: datetime | None = None

    @field_validator("link")
    @classmethod
    def validate_link(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"link must be a valid URL, got '{v}'")
        return v


class FundMetadata(BaseModel):
    """Metadata for an investment fund (CVM data)."""

    model_config = ConfigDict(frozen=True)

    cnpj: str
    name: str
    type: str | None = None
    manager: str | None = None
    admin_fee: float | None = None
    benchmark: str | None = None
    updated_at: datetime | None = None

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, v: str) -> str:
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) != 14:
            raise ValueError(f"CNPJ must have 14 digits, got {len(digits)}")
        return v


class SystemConfig(BaseModel):
    """A single key-value system configuration entry."""

    model_config = ConfigDict(frozen=True)

    key: str
    value: str
    description: str | None = None
    updated_at: datetime | None = None


class CollectionMetadata(BaseModel):
    """Tracks the execution state of a data collection source."""

    source: str
    last_run: datetime | None = None
    status: str = "pending"
    records_collected: int = 0
    error_count: int = 0
    last_error: str | None = None
    updated_at: datetime | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "running", "success", "error"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v


class PerformanceReport(BaseModel):
    """A generated performance report with optional PDF artifact."""

    model_config = ConfigDict(frozen=True)

    date: date
    report_data: dict[str, Any] = Field(default_factory=dict)
    pdf_path: str | None = None
    created_at: datetime | None = None
