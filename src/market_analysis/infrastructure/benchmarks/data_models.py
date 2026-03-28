"""Data models for the benchmark collection system.

These are the output types consumed by the performance engine and PDF generator.
Tesouro Nacional data is deferred to Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass(frozen=True, slots=True)
class DailyBenchmarkRecord:
    """A single day's benchmark observation from BCB SGS."""

    date: date
    selic_daily_factor: Optional[float] = None  # series 11 (%)
    cdi_daily_factor: Optional[float] = None    # series 12 (%)
    ipca_monthly: Optional[float] = None        # series 433 (%)
    selic_target_rate: Optional[float] = None    # series 432 (% annual)
    cdi_annual_rate: Optional[float] = None      # series 4389 (% annual)


@dataclass
class BenchmarkData:
    """Comprehensive benchmark results for a date range.

    This is the primary output consumed by performance.py and the PDF pipeline.
    Fields mirror the old BenchmarkRates dict but are typed and include
    derived calculations + raw daily series for advanced metrics (#57).
    """

    # Period
    date_range: tuple[date, date]

    # Accumulated returns over period (%)
    selic_accumulated: float = 0.0
    cdi_accumulated: float = 0.0
    ipca_accumulated: float = 0.0

    # Latest annualized reference rates (%)
    selic_annual_rate: float = 0.0
    cdi_annual_rate: float = 0.0

    # Derived benchmarks (%)
    cdb_estimated: float = 0.0
    poupanca_estimated: float = 0.0

    # Raw daily time series (for #57 advanced metrics)
    daily_records: list[DailyBenchmarkRecord] = field(default_factory=list)

    # Data quality
    data_completeness: float = 1.0  # 0.0 to 1.0
    missing_days: int = 0
    fallback_used: bool = False
    source_quality: str = "complete"  # "complete", "partial", "fallback"

    def to_legacy_dict(self) -> dict[str, float]:
        """Convert to the old BenchmarkRates dict format for backward compat.

        Keys: selic, cdi, ipca, selic_annual, cdb, poupanca
        """
        return {
            "selic": self.selic_accumulated,
            "cdi": self.cdi_accumulated,
            "ipca": self.ipca_accumulated,
            "selic_annual": self.selic_annual_rate,
            "cdb": self.cdb_estimated,
            "poupanca": self.poupanca_estimated,
        }
