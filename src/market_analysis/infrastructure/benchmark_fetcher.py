"""Synchronous BCB benchmark rate fetcher for report generation.

Fetches SELIC, CDI, and IPCA rates from the BCB SGS API and computes
accumulated returns over a period. Used by the PDF report pipeline.

This is a lightweight, sync module for US-004 (report generation).
The full async BCB collector (bcb_collector.py) is part of US-001.

API docs: https://dadosabertos.bcb.gov.br/dataset/sgs
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import TypeAlias
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

# BCB series codes
SERIES_SELIC_DAILY = 11   # SELIC daily factor (%)
SERIES_SELIC_TARGET = 432 # SELIC annualized target rate (%)
SERIES_CDI_DAILY = 12     # CDI daily factor (%)
SERIES_CDI_ANNUAL = 4389  # CDI annualized rate (%)
SERIES_IPCA = 433         # IPCA monthly (%)

DEFAULT_TIMEOUT = 30

BenchmarkRates: TypeAlias = dict[str, float]


class BenchmarkFetchError(Exception):
    """Raised when BCB API fetch fails."""


def _fetch_series(
    code: int,
    start_date: date,
    end_date: date,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, str]]:
    """Fetch a BCB SGS series as JSON."""
    url = (
        f"{BCB_SGS_URL.format(code=code)}"
        f"?formato=json"
        f"&dataInicial={start_date.strftime('%d/%m/%Y')}"
        f"&dataFinal={end_date.strftime('%d/%m/%Y')}"
    )
    logger.info("Fetching BCB series %d: %s", code, url)

    req = Request(url, headers={"User-Agent": "MarketAnalysis/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            raise BenchmarkFetchError(f"Unexpected response for series {code}")
        logger.info("Got %d records for series %d", len(data), code)
        return data
    except BenchmarkFetchError:
        raise
    except Exception as exc:
        raise BenchmarkFetchError(
            f"Failed to fetch BCB series {code}: {exc}"
        ) from exc


def accumulate_daily_rates(records: list[dict[str, str]]) -> float:
    """Accumulate daily rates using compound interest.

    Each record has a daily rate in %. The accumulated return
    is: product((1 + rate/100)) - 1, converted back to %.
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


def collect_benchmarks(
    start_date: date,
    end_date: date,
    timeout: int = DEFAULT_TIMEOUT,
) -> BenchmarkRates:
    """Collect accumulated benchmark rates for a period.

    Args:
        start_date: Period start (inclusive).
        end_date: Period end (inclusive).
        timeout: HTTP timeout in seconds.

    Returns:
        Dict with keys 'selic', 'cdi', 'ipca' and accumulated % values.
    """
    results: BenchmarkRates = {}

    # SELIC (daily factor)
    try:
        selic_data = _fetch_series(SERIES_SELIC_DAILY, start_date, end_date, timeout)
        results["selic"] = accumulate_daily_rates(selic_data)
    except BenchmarkFetchError:
        logger.warning("Failed to collect SELIC daily data")
        results["selic"] = 0.0

    # SELIC annualized target rate
    try:
        selic_target = _fetch_series(SERIES_SELIC_TARGET, start_date, end_date, timeout)
        results["selic_annual"] = float(
            selic_target[-1]["valor"].replace(",", ".")
        ) if selic_target else 0.0
    except BenchmarkFetchError:
        logger.warning("Failed to collect SELIC target rate")
        results["selic_annual"] = 0.0

    # CDI (daily factor)
    try:
        cdi_data = _fetch_series(SERIES_CDI_DAILY, start_date, end_date, timeout)
        results["cdi"] = accumulate_daily_rates(cdi_data)
    except BenchmarkFetchError:
        logger.warning("Failed to collect CDI data")
        results["cdi"] = 0.0

    # IPCA (monthly)
    try:
        ipca_start = start_date.replace(day=1)
        ipca_data = _fetch_series(SERIES_IPCA, ipca_start, end_date, timeout)
        results["ipca"] = accumulate_monthly_rates(ipca_data)
    except BenchmarkFetchError:
        logger.warning("Failed to collect IPCA data")
        results["ipca"] = 0.0

    return results
