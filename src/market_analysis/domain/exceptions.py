"""Domain exception hierarchy.

All exceptions inherit from MarketAnalysisError so callers can
catch the base class at system boundaries.
"""

from __future__ import annotations


class MarketAnalysisError(Exception):
    """Base exception for all domain errors."""


# --- Collection errors ---


class CollectionError(MarketAnalysisError):
    """Base for errors during data collection."""


class SourceUnavailableError(CollectionError):
    """External data source is unreachable or returning errors."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"{source} unavailable: {reason}")
        self.source = source
        self.reason = reason


class DataValidationError(CollectionError):
    """Collected data failed validation rules."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__(f"Validation failed: {'; '.join(errors)}")
        self.errors = errors


class RetryExhaustedError(CollectionError):
    """All retry attempts have been exhausted."""

    def __init__(self, collector: str, attempts: int) -> None:
        super().__init__(f"{collector}: all {attempts} attempts exhausted")
        self.collector = collector
        self.attempts = attempts


# --- Persistence errors ---


class PersistenceError(MarketAnalysisError):
    """Error during database operations."""


# --- Report errors ---


class ReportGenerationError(MarketAnalysisError):
    """Error generating the PDF report."""


class EmailDeliveryError(MarketAnalysisError):
    """Error sending email."""
