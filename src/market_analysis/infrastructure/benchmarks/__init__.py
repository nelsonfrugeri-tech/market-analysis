"""Benchmark collection system for Brazilian financial markets.

Provides BCB SGS data collection (SELIC, CDI, IPCA) with derived
calculations for CDB and Poupanca rates. Tesouro Nacional deferred to Phase 2.
"""

from .bcb_client import BCBClient, BCBClientError
from .benchmark_calculator import (
    collect_all_benchmarks,
    collect_all_benchmarks_sync,
    accumulate_daily_rates,
    accumulate_monthly_rates,
    calculate_cdb_estimated,
    calculate_poupanca_estimated,
)
from .cache_manager import BenchmarkCacheManager
from .data_models import BenchmarkData, DailyBenchmarkRecord

__all__ = [
    "BCBClient",
    "BCBClientError",
    "BenchmarkCacheManager",
    "BenchmarkData",
    "DailyBenchmarkRecord",
    "accumulate_daily_rates",
    "accumulate_monthly_rates",
    "calculate_cdb_estimated",
    "calculate_poupanca_estimated",
    "collect_all_benchmarks",
    "collect_all_benchmarks_sync",
]
