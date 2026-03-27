"""Domain models and interfaces for the market analysis system.

Re-exports from sub-modules for convenient imports::

    from market_analysis.domain.models import BcbDataPoint, CollectorType, ...
"""

from market_analysis.domain.models.core import (
    BcbDataPoint,
    BenchmarkComparison,
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorDetail,
    ErrorResult,
    FundMetadata,
    NewsItem,
    PerformanceReport,
    PeriodWindow,
    Recipient,
    SeriesCode,
    ValidationResult,
)
from market_analysis.domain.models.entities import (
    BCBRecord,
    CollectionMetadata,
    NewsRecord,
    SystemConfig,
)
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.domain.interfaces import BaseCollector

__all__ = [
    # Core domain models (authoritative)
    "BcbDataPoint",
    "BenchmarkComparison",
    "CollectionResult",
    "CollectionStatus",
    "CollectorType",
    "ErrorDetail",
    "ErrorResult",
    "FundMetadata",
    "NewsItem",
    "PerformanceReport",
    "PeriodWindow",
    "Recipient",
    "SeriesCode",
    "ValidationResult",
    # Fund models
    "FundDailyRecord",
    "FundPerformance",
    # Legacy entities (Pydantic-based)
    "BaseCollector",
    "BCBRecord",
    "CollectionMetadata",
    "NewsRecord",
    "SystemConfig",
]
