"""Result types for the collection pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class CollectionStatus(StrEnum):
    """Possible outcomes of a collection run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of validating a batch of collected records.

    Separates valid records from those that failed validation,
    keeping the error detail for each rejected item.
    """

    valid_records: list[Any] = field(default_factory=list)
    invalid_records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.invalid_records) == 0

    @property
    def total(self) -> int:
        return len(self.valid_records) + len(self.invalid_records)

    @property
    def valid_count(self) -> int:
        return len(self.valid_records)


@dataclass(frozen=True, slots=True)
class ErrorResult:
    """Structured representation of a collection error."""

    source: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """Standardised outcome returned by every collector.

    Encapsulates the collected data, validation outcome, timing
    information and any errors that occurred during the run.
    """

    source: str
    status: CollectionStatus
    records: list[Any] = field(default_factory=list)
    errors: list[ErrorResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def is_success(self) -> bool:
        return self.status == CollectionStatus.SUCCESS

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()
