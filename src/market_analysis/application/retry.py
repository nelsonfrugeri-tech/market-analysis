"""Retry logic with exponential backoff.

This is the single place where retry policy is implemented.
Collectors do NOT retry internally -- the orchestrator wraps
them with this utility.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from typing import TypeVar

from market_analysis.domain.interfaces import BaseCollector
from market_analysis.domain.models import (
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorDetail,
    ErrorResult,
)
from market_analysis.domain.schemas import RetryPolicy

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def collect_with_retry(
    collector: BaseCollector,
    start_date: date,
    end_date: date,
    policy: RetryPolicy | None = None,
) -> CollectionResult | ErrorResult:
    """Execute a collector with retry logic.

    Returns CollectionResult on success or ErrorResult after
    all attempts are exhausted.
    """
    if policy is None:
        policy = RetryPolicy()

    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = await collector.collect(start_date, end_date)

            if isinstance(result, CollectionResult):
                if attempt > 1:
                    logger.info(
                        "Collection succeeded on attempt %d/%d for %s",
                        attempt,
                        policy.max_attempts,
                        collector.collector_type,
                    )
                return result

            # Collector returned ErrorResult but may be retryable
            if isinstance(result, ErrorResult) and result.error.retryable:
                last_error = Exception(result.error.message)
                if attempt < policy.max_attempts:
                    delay = _calculate_delay(attempt, policy)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt,
                        policy.max_attempts,
                        collector.collector_type,
                        result.error.message,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

            # Non-retryable error or final attempt
            return result

        except Exception as exc:
            last_error = exc
            if attempt < policy.max_attempts:
                delay = _calculate_delay(attempt, policy)
                logger.warning(
                    "Attempt %d/%d raised %s for %s. Retrying in %.1fs",
                    attempt,
                    policy.max_attempts,
                    type(exc).__name__,
                    collector.collector_type,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "All %d attempts exhausted for %s: %s",
                    policy.max_attempts,
                    collector.collector_type,
                    exc,
                )

    # All attempts exhausted
    return ErrorResult(
        collector_type=collector.collector_type,
        attempted_at=datetime.now(timezone.utc),
        error=ErrorDetail(
            code="RETRY_EXHAUSTED",
            message=str(last_error) if last_error else "Unknown error",
            retryable=False,
        ),
        attempts=policy.max_attempts,
        status=CollectionStatus.FAILURE,
    )


def _calculate_delay(attempt: int, policy: RetryPolicy) -> float:
    """Exponential backoff with cap."""
    delay = policy.base_delay_seconds * (policy.exponential_base ** (attempt - 1))
    return min(delay, policy.max_delay_seconds)
