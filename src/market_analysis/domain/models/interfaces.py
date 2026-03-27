"""Abstract interfaces (Protocols) for the collection layer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from market_analysis.domain.models.collection import CollectionResult, ValidationResult


@runtime_checkable
class BaseCollector(Protocol):
    """Contract that every data collector must satisfy.

    Implementations are expected for BCB, Google News and CVM sources.
    Each collector is responsible for:
      1. Fetching raw data from its external source.
      2. Validating the fetched data.
      3. Returning a standardised ``CollectionResult``.
    """

    @property
    def source_name(self) -> str:
        """Unique identifier for this data source (e.g. 'bcb', 'news', 'cvm')."""
        ...

    async def collect(self) -> CollectionResult:
        """Execute the full collection cycle and return the result."""
        ...

    async def validate(self, raw_data: list[dict]) -> ValidationResult:
        """Validate a batch of raw records before persistence."""
        ...

    async def health_check(self) -> bool:
        """Return True if the external source is reachable."""
        ...
