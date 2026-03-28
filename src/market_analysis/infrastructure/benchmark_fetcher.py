"""DEPRECATED: Backward-compatible wrapper around the unified benchmarks module.

All new code should import from market_analysis.infrastructure.benchmarks.
This module is kept only so existing consumers (cli.py, performance.py, tests)
continue to work without changes until they are migrated.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TypeAlias

from market_analysis.infrastructure.benchmarks import (
    collect_all_benchmarks_sync,
    accumulate_daily_rates,
    accumulate_monthly_rates,
    BCBClientError,
)

logger = logging.getLogger(__name__)

BenchmarkRates: TypeAlias = dict[str, float]


class BenchmarkFetchError(BCBClientError):
    """Kept for backward compat. Use BCBClientError instead."""


def collect_benchmarks(
    start_date: date,
    end_date: date,
    timeout: int = 30,
) -> BenchmarkRates:
    """Collect accumulated benchmark rates for a period.

    DEPRECATED: Use collect_all_benchmarks_sync() for typed results,
    or collect_all_benchmarks() for async.
    """
    from market_analysis.infrastructure.benchmarks.bcb_client import BCBClient

    client = BCBClient(timeout=timeout)
    result = collect_all_benchmarks_sync(start_date, end_date, client=client)
    return result.to_legacy_dict()


__all__ = [
    "BenchmarkFetchError",
    "BenchmarkRates",
    "accumulate_daily_rates",
    "accumulate_monthly_rates",
    "collect_benchmarks",
]
