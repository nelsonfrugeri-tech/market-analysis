"""Benchmark collection orchestrator and derived-rate calculator.

Coordinates BCBClient to fetch all required series, accumulates daily
factors into period returns, and computes derived benchmarks (CDB, Poupanca).

This is the single entry point for the benchmark pipeline.
"""

from __future__ import annotations

import logging
from datetime import date

from .bcb_client import (
    BCBClient,
    BCBClientError,
    SERIES_CDI_ANNUAL,
    SERIES_CDI_DAILY,
    SERIES_IPCA,
    SERIES_SELIC_DAILY,
    SERIES_SELIC_TARGET,
)
from .data_models import BenchmarkData, DailyBenchmarkRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Accumulation helpers
# ---------------------------------------------------------------------------


def accumulate_daily_rates(records: list[dict[str, str]]) -> float:
    """Accumulate daily factors using compound interest.

    Each record has a daily rate in %. Accumulated return =
    product(1 + rate/100) - 1, converted back to %.
    """
    accumulated = 1.0
    for record in records:
        daily_rate = float(record["valor"].replace(",", "."))
        accumulated *= 1 + daily_rate / 100
    return (accumulated - 1) * 100


def accumulate_monthly_rates(records: list[dict[str, str]]) -> float:
    """Accumulate monthly rates (IPCA) using compound interest."""
    accumulated = 1.0
    for record in records:
        monthly_rate = float(record["valor"].replace(",", "."))
        accumulated *= 1 + monthly_rate / 100
    return (accumulated - 1) * 100


def _latest_rate(records: list[dict[str, str]]) -> float:
    """Extract the last value from a series of records."""
    if not records:
        return 0.0
    return float(records[-1]["valor"].replace(",", "."))


# ---------------------------------------------------------------------------
# Derived calculations
# ---------------------------------------------------------------------------


def calculate_cdb_estimated(cdi_accumulated: float) -> float:
    """Estimate average CDB return as 95% of CDI.

    This is a conservative proxy; real CDB rates vary by institution.
    """
    return cdi_accumulated * 0.95


def calculate_poupanca_estimated(
    selic_annual_rate: float,
    selic_accumulated: float,
) -> float:
    """Estimate poupanca return based on SELIC rule.

    Rule (Lei 12.703/2012):
    - If SELIC > 8.5%: poupanca = 0.5% per month + TR (TR ~ 0 in Phase 1)
    - If SELIC <= 8.5%: poupanca = 70% of SELIC
    """
    if selic_annual_rate > 8.5:
        # 0.5% per month, compound for the period proportional to SELIC days
        # Simplified: use the accumulated SELIC period and apply ratio
        # Monthly 0.5% annualized ~ 6.17%. Ratio to SELIC accumulated:
        annual_poupanca = (1.005 ** 12 - 1) * 100  # ~6.17%
        if selic_accumulated > 0:
            # Scale proportionally to the period
            # selic_accumulated is already for the period, so ratio it
            selic_annual_equivalent = ((1 + selic_accumulated / 100) ** (252 / max(_estimate_business_days(selic_accumulated), 1)) - 1) * 100
            if selic_annual_equivalent > 0:
                return selic_accumulated * (annual_poupanca / selic_annual_equivalent)
        return 0.0
    else:
        return selic_accumulated * 0.70


def _estimate_business_days(accumulated_pct: float) -> int:
    """Rough estimate of business days from accumulated SELIC %.

    Used only for poupanca approximation. Not critical precision.
    """
    # Typical daily SELIC ~ 0.04-0.05%. Use 0.045 as midpoint.
    if accumulated_pct <= 0:
        return 1
    daily_avg = 0.045
    # accumulated ~ (1 + daily/100)^n - 1 => n ~ accumulated / daily (linear approx)
    return max(int(accumulated_pct / daily_avg), 1)


# ---------------------------------------------------------------------------
# Build daily records from raw data
# ---------------------------------------------------------------------------


def _build_daily_records(
    selic_daily: list[dict[str, str]],
    cdi_daily: list[dict[str, str]],
    ipca_monthly: list[dict[str, str]],
    selic_target: list[dict[str, str]],
    cdi_annual: list[dict[str, str]],
) -> list[DailyBenchmarkRecord]:
    """Build a list of DailyBenchmarkRecord from raw series data.

    Merges all series by date. Not all series have data for every day
    (e.g., IPCA is monthly), so fields may be None.
    """
    from datetime import datetime

    # Index all data by date
    by_date: dict[date, dict[str, float]] = {}

    def _index(records: list[dict[str, str]], field: str) -> None:
        for r in records:
            try:
                d = datetime.strptime(r["data"], "%d/%m/%Y").date()
                val = float(r["valor"].replace(",", "."))
                by_date.setdefault(d, {})[field] = val
            except (ValueError, KeyError):
                continue

    _index(selic_daily, "selic_daily_factor")
    _index(cdi_daily, "cdi_daily_factor")
    _index(ipca_monthly, "ipca_monthly")
    _index(selic_target, "selic_target_rate")
    _index(cdi_annual, "cdi_annual_rate")

    result = []
    for d in sorted(by_date.keys()):
        fields = by_date[d]
        result.append(DailyBenchmarkRecord(
            date=d,
            selic_daily_factor=fields.get("selic_daily_factor"),
            cdi_daily_factor=fields.get("cdi_daily_factor"),
            ipca_monthly=fields.get("ipca_monthly"),
            selic_target_rate=fields.get("selic_target_rate"),
            cdi_annual_rate=fields.get("cdi_annual_rate"),
        ))
    return result


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


async def collect_all_benchmarks(
    start_date: date,
    end_date: date,
    client: BCBClient | None = None,
) -> BenchmarkData:
    """Collect all benchmark data for a period (async).

    This is the primary async entry point. Fetches all 5 BCB series,
    computes accumulations and derived rates, returns BenchmarkData.
    """
    bcb = client or BCBClient()
    errors: list[str] = []

    async def _safe_fetch(code: int) -> list[dict[str, str]]:
        try:
            return await bcb.fetch_series_async(code, start_date, end_date)
        except BCBClientError as exc:
            errors.append(str(exc))
            return []

    # Fetch all series
    selic_daily = await _safe_fetch(SERIES_SELIC_DAILY)
    cdi_daily = await _safe_fetch(SERIES_CDI_DAILY)
    ipca_data = await _safe_fetch(SERIES_IPCA)
    selic_target = await _safe_fetch(SERIES_SELIC_TARGET)
    cdi_annual = await _safe_fetch(SERIES_CDI_ANNUAL)

    return _assemble_result(
        start_date, end_date,
        selic_daily, cdi_daily, ipca_data, selic_target, cdi_annual,
        errors,
    )


def collect_all_benchmarks_sync(
    start_date: date,
    end_date: date,
    client: BCBClient | None = None,
) -> BenchmarkData:
    """Collect all benchmark data for a period (sync fallback).

    Used by CLI and simple pipelines that don't run an event loop.
    """
    bcb = client or BCBClient()
    errors: list[str] = []

    def _safe_fetch(code: int) -> list[dict[str, str]]:
        try:
            return bcb.fetch_series_sync(code, start_date, end_date)
        except BCBClientError as exc:
            errors.append(str(exc))
            return []

    selic_daily = _safe_fetch(SERIES_SELIC_DAILY)
    cdi_daily = _safe_fetch(SERIES_CDI_DAILY)
    ipca_data = _safe_fetch(SERIES_IPCA)
    selic_target = _safe_fetch(SERIES_SELIC_TARGET)
    cdi_annual = _safe_fetch(SERIES_CDI_ANNUAL)

    return _assemble_result(
        start_date, end_date,
        selic_daily, cdi_daily, ipca_data, selic_target, cdi_annual,
        errors,
    )


def _assemble_result(
    start_date: date,
    end_date: date,
    selic_daily: list[dict[str, str]],
    cdi_daily: list[dict[str, str]],
    ipca_data: list[dict[str, str]],
    selic_target: list[dict[str, str]],
    cdi_annual: list[dict[str, str]],
    errors: list[str],
) -> BenchmarkData:
    """Assemble BenchmarkData from raw series."""
    # Accumulate
    selic_acc = accumulate_daily_rates(selic_daily) if selic_daily else 0.0
    cdi_acc = accumulate_daily_rates(cdi_daily) if cdi_daily else 0.0
    ipca_acc = accumulate_monthly_rates(ipca_data) if ipca_data else 0.0

    # Reference rates (latest)
    selic_annual = _latest_rate(selic_target)
    cdi_annual_rate = _latest_rate(cdi_annual)

    # Derived
    cdb_est = calculate_cdb_estimated(cdi_acc)
    poupanca_est = calculate_poupanca_estimated(selic_annual, selic_acc)

    # Daily records
    daily = _build_daily_records(selic_daily, cdi_daily, ipca_data, selic_target, cdi_annual)

    # Quality
    total_series = 5
    failed = len(errors)
    completeness = (total_series - failed) / total_series

    quality = "complete"
    if failed > 0:
        quality = "partial" if failed < total_series else "fallback"

    if errors:
        for e in errors:
            logger.warning("Benchmark collection issue: %s", e)

    return BenchmarkData(
        date_range=(start_date, end_date),
        selic_accumulated=round(selic_acc, 6),
        cdi_accumulated=round(cdi_acc, 6),
        ipca_accumulated=round(ipca_acc, 6),
        selic_annual_rate=round(selic_annual, 4),
        cdi_annual_rate=round(cdi_annual_rate, 4),
        cdb_estimated=round(cdb_est, 6),
        poupanca_estimated=round(poupanca_est, 6),
        daily_records=daily,
        data_completeness=round(completeness, 2),
        missing_days=0,  # TODO: compute from business day calendar
        fallback_used=bool(errors),
        source_quality=quality,
    )
