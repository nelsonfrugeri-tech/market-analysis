"""Pydantic v2 schemas for external data validation.

These schemas validate data at system boundaries (API responses,
RSS feeds, config files) before converting to domain models.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# BCB API response validation
# ---------------------------------------------------------------------------


class BcbApiRecord(BaseModel):
    """Single record from BCB SGS API response."""

    model_config = ConfigDict(strict=True)

    data: str = Field(description="Date string in dd/mm/yyyy format")
    valor: str = Field(description="Numeric value as string")

    @field_validator("data")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%d/%m/%Y")
        except ValueError as e:
            raise ValueError(f"Invalid date format: {v}") from e
        return v

    @field_validator("valor")
    @classmethod
    def validate_numeric(cls, v: str) -> str:
        try:
            Decimal(v)
        except Exception as e:
            raise ValueError(f"Non-numeric value: {v}") from e
        return v

    def to_date(self) -> date:
        """Convert the date string to a date object."""
        return datetime.strptime(self.data, "%d/%m/%Y").date()

    def to_decimal(self) -> Decimal:
        """Convert the value string to Decimal."""
        return Decimal(self.valor)


# ---------------------------------------------------------------------------
# News RSS validation
# ---------------------------------------------------------------------------


class NewsRssEntry(BaseModel):
    """Validated RSS feed entry from Google News."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=500)
    link: str = Field(min_length=1)
    published: datetime
    description: str = Field(default="", max_length=2000)
    source: str = Field(default="unknown", max_length=200)

    @field_validator("link")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {v}")
        return v


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


class SmtpConfig(BaseModel):
    """SMTP server configuration."""

    model_config = ConfigDict(str_strip_whitespace=True)

    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    username: str
    password: str
    use_tls: bool = True
    sender_email: str


class RecipientConfig(BaseModel):
    """Email recipient entry."""

    name: str = Field(min_length=1)
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid email: {v}")
        return v.lower()


class FundConfig(BaseModel):
    """Fund tracking configuration."""

    cnpj: str
    name: str
    fund_type: str
    manager: str

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj_format(cls, v: str) -> str:
        cleaned = re.sub(r"[./-]", "", v)
        if len(cleaned) != 14 or not cleaned.isdigit():
            raise ValueError(f"Invalid CNPJ: {v}")
        return v


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------


class RetryPolicy(BaseModel):
    """Configuration for retry behavior."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay_seconds: float = Field(default=1.0, ge=0.1)
    max_delay_seconds: float = Field(default=60.0, ge=1.0)
    exponential_base: float = Field(default=2.0, ge=1.5, le=4.0)
