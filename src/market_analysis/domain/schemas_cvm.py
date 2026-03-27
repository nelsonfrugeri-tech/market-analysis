"""Pydantic v2 schemas for CVM data validation.

Validates raw CSV rows from CVM INF_DIARIO files before
converting to domain models.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CvmDailyRow(BaseModel):
    """Validated row from the CVM inf_diario CSV.

    Field names match CVM's CSV headers. Validation ensures types
    and ranges are correct before domain model creation.
    """

    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    CNPJ_FUNDO_CLASSE: str = Field(
        ..., description="Fund CNPJ (may also come as CNPJ_FUNDO)"
    )
    DT_COMPTC: str = Field(..., description="Reference date YYYY-MM-DD")
    VL_QUOTA: str = Field(..., description="NAV per share")
    VL_PATRIM_LIQ: str = Field(..., description="Net equity")
    VL_TOTAL: str = Field(..., description="Total value")
    CAPTC_DIA: str = Field(..., description="Daily deposits")
    RESG_DIA: str = Field(..., description="Daily withdrawals")
    NR_COTST: str = Field(..., description="Number of shareholders")

    @field_validator("DT_COMPTC")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {v}") from e
        return v

    @field_validator("VL_QUOTA", "VL_PATRIM_LIQ", "VL_TOTAL", "CAPTC_DIA", "RESG_DIA")
    @classmethod
    def validate_numeric(cls, v: str) -> str:
        cleaned = v.replace(",", ".")
        try:
            val = Decimal(cleaned)
        except InvalidOperation as e:
            raise ValueError(f"Non-numeric value: {v}") from e
        if val < 0:
            raise ValueError(f"Negative value not allowed: {v}")
        return v

    @field_validator("NR_COTST")
    @classmethod
    def validate_shareholders(cls, v: str) -> str:
        try:
            n = int(v)
        except ValueError as e:
            raise ValueError(f"Non-integer shareholders: {v}") from e
        if n < 0:
            raise ValueError(f"Negative shareholders: {v}")
        return v

    def to_date(self) -> date:
        """Convert DT_COMPTC to a date object."""
        return date.fromisoformat(self.DT_COMPTC)

    def to_nav(self) -> float:
        """Parse VL_QUOTA as float."""
        return float(self.VL_QUOTA.replace(",", "."))

    def to_equity(self) -> float:
        """Parse VL_PATRIM_LIQ as float."""
        return float(self.VL_PATRIM_LIQ.replace(",", "."))

    def to_total_value(self) -> float:
        """Parse VL_TOTAL as float."""
        return float(self.VL_TOTAL.replace(",", "."))

    def to_deposits(self) -> float:
        """Parse CAPTC_DIA as float."""
        return float(self.CAPTC_DIA.replace(",", "."))

    def to_withdrawals(self) -> float:
        """Parse RESG_DIA as float."""
        return float(self.RESG_DIA.replace(",", "."))

    def to_shareholders(self) -> int:
        """Parse NR_COTST as int."""
        return int(self.NR_COTST)
