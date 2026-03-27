"""Domain models for the fund analysis system.

These are pure data structures with no external dependencies.
They represent the core business concepts and serve as contracts
between all layers of the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SeriesCode(StrEnum):
    """BCB time-series codes."""

    SELIC = "432"
    CDI = "4389"
    IPCA = "433"


class CollectionStatus(StrEnum):
    """Outcome of a single collection run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"


class CollectorType(StrEnum):
    """Identifies the data source a collector targets."""

    BCB = "bcb"
    NEWS = "news"
    CVM = "cvm"


class PeriodWindow(StrEnum):
    """Standard analysis windows."""

    D30 = "30d"
    D90 = "90d"
    D180 = "180d"
    D365 = "365d"


# ---------------------------------------------------------------------------
# Value Objects (immutable, no identity)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BcbDataPoint:
    """A single BCB time-series observation."""

    series_code: SeriesCode
    reference_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A single RSS news entry."""

    title: str
    link: str
    published_at: datetime
    description: str
    source: str


@dataclass(frozen=True, slots=True)
class FundMetadata:
    """Static metadata for a tracked fund."""

    cnpj: str
    name: str
    fund_type: str
    manager: str


@dataclass(frozen=True, slots=True)
class Recipient:
    """An email recipient."""

    name: str
    email: str
    active: bool = True


# ---------------------------------------------------------------------------
# Result Types (collection pipeline outputs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """Successful collection result carrying collected items."""

    collector_type: CollectorType
    collected_at: datetime
    items_count: int
    duration_seconds: float
    status: CollectionStatus = CollectionStatus.SUCCESS


@dataclass(frozen=True, slots=True)
class ErrorDetail:
    """Structured error information for diagnostics."""

    code: str
    message: str
    context: dict[str, str] = field(default_factory=dict)
    retryable: bool = True


@dataclass(frozen=True, slots=True)
class ErrorResult:
    """Failed collection result."""

    collector_type: CollectorType
    attempted_at: datetime
    error: ErrorDetail
    attempts: int
    status: CollectionStatus = CollectionStatus.FAILURE


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of validating collected data before persistence."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    items_accepted: int = 0
    items_rejected: int = 0


# ---------------------------------------------------------------------------
# Report Structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """Fund performance vs a single benchmark over a window."""

    benchmark_name: str
    period: PeriodWindow
    fund_return_pct: Decimal
    benchmark_return_pct: Decimal
    spread_pct: Decimal  # fund - benchmark


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    """All data needed to render the PDF report."""

    fund: FundMetadata
    generated_at: datetime
    report_date: date
    comparisons: list[BenchmarkComparison]
    recent_news: list[NewsItem]
    data_quality_notes: list[str] = field(default_factory=list)
