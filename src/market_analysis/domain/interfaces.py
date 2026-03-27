"""Domain interfaces (Protocols) for the fund analysis system.

These define the contracts that infrastructure implementations must satisfy.
Using Protocol (structural subtyping) so implementations don't need to
inherit from these -- they just need to match the shape.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, runtime_checkable

from market_analysis.domain.models import (
    BcbDataPoint,
    CollectionResult,
    CollectorType,
    ErrorResult,
    FundMetadata,
    NewsItem,
    PerformanceReport,
    Recipient,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Collector Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class BaseCollector(Protocol):
    """Interface that every data collector must satisfy.

    Collectors are responsible for:
    1. Fetching raw data from an external source
    2. Validating the raw data
    3. Returning a structured result or error

    Retry logic is NOT the collector's responsibility -- it belongs
    to the orchestration layer (application/scheduler).
    """

    @property
    def collector_type(self) -> CollectorType:
        """Identify which source this collector targets."""
        ...

    async def collect(
        self,
        start_date: date,
        end_date: date,
    ) -> CollectionResult | ErrorResult:
        """Execute the collection for the given date range.

        Must be idempotent: calling twice with the same range
        should produce the same result without side effects.
        """
        ...

    async def validate(
        self,
        items: list[BcbDataPoint] | list[NewsItem],
    ) -> ValidationResult:
        """Validate collected items before persistence."""
        ...

    async def health_check(self) -> bool:
        """Return True if the external source is reachable."""
        ...


# ---------------------------------------------------------------------------
# Repository Protocols
# ---------------------------------------------------------------------------


class BcbRepository(Protocol):
    """Persistence contract for BCB time-series data."""

    async def upsert_data_points(self, points: list[BcbDataPoint]) -> int:
        """Insert or update data points. Return count of affected rows."""
        ...

    async def get_series(
        self,
        series_code: str,
        start_date: date,
        end_date: date,
    ) -> list[BcbDataPoint]:
        """Retrieve data points for a series within a date range."""
        ...

    async def get_latest_date(self, series_code: str) -> date | None:
        """Return the most recent date stored for a series, or None."""
        ...


class NewsRepository(Protocol):
    """Persistence contract for news items."""

    async def insert_items(self, items: list[NewsItem]) -> int:
        """Insert news items, skipping duplicates. Return inserted count."""
        ...

    async def get_recent(
        self,
        since: datetime,
        limit: int = 50,
    ) -> list[NewsItem]:
        """Retrieve recent news items ordered by published_at desc."""
        ...


class FundRepository(Protocol):
    """Persistence contract for fund metadata."""

    async def get_by_cnpj(self, cnpj: str) -> FundMetadata | None:
        """Return fund metadata or None if not found."""
        ...

    async def upsert(self, fund: FundMetadata) -> None:
        """Insert or update fund metadata."""
        ...


class RecipientRepository(Protocol):
    """Persistence contract for email recipients."""

    async def get_active(self) -> list[Recipient]:
        """Return all active recipients."""
        ...


class CollectionMetadataRepository(Protocol):
    """Persistence contract for collection run tracking."""

    async def record_run(
        self,
        result: CollectionResult | ErrorResult,
    ) -> None:
        """Record the outcome of a collection run."""
        ...

    async def get_last_success(
        self,
        collector_type: CollectorType,
    ) -> datetime | None:
        """Return timestamp of last successful run, or None."""
        ...

    async def get_recent_errors(
        self,
        collector_type: CollectorType,
        limit: int = 10,
    ) -> list[ErrorResult]:
        """Return recent errors for diagnostics."""
        ...


# ---------------------------------------------------------------------------
# Service Protocols
# ---------------------------------------------------------------------------


class ReportGenerator(Protocol):
    """Generates PDF reports from performance data."""

    async def generate(self, report: PerformanceReport) -> bytes:
        """Return the PDF as bytes."""
        ...


class EmailSender(Protocol):
    """Sends email with attachments."""

    async def send(
        self,
        recipients: list[Recipient],
        subject: str,
        body: str,
        attachments: list[tuple[str, bytes]],
    ) -> None:
        """Send email. Raises on failure."""
        ...
