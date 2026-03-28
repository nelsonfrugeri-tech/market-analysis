"""Unified BCB SGS API client with async-first, sync fallback.

Replaces both bcb_collector.py (async) and benchmark_fetcher.py (sync).
Fetches raw daily series and returns structured data for the benchmark pipeline.

API docs: https://dadosabertos.bcb.gov.br/dataset/sgs
"""

from __future__ import annotations

import json
import logging
from datetime import date
from urllib.request import Request, urlopen

import httpx

from .cache_manager import BenchmarkCacheManager

logger = logging.getLogger(__name__)

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

# Canonical BCB SGS series codes
SERIES_SELIC_DAILY = 11    # Daily factor (%) — for accumulation
SERIES_CDI_DAILY = 12      # Daily factor (%) — for accumulation
SERIES_SELIC_TARGET = 432  # Annualized target rate (%)
SERIES_CDI_ANNUAL = 4389   # Annualized rate (%)
SERIES_IPCA = 433          # Monthly variation (%)

DEFAULT_TIMEOUT = 30


class BCBClientError(Exception):
    """Raised when BCB API interaction fails."""


class BCBClient:
    """Unified BCB SGS client: async-first with sync fallback.

    Usage:
        client = BCBClient()
        # Async (preferred)
        records = await client.fetch_series_async(11, start, end)
        # Sync fallback
        records = client.fetch_series_sync(11, start, end)
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        cache: BenchmarkCacheManager | None = None,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout
        self._cache = cache or BenchmarkCacheManager()
        self._external_client = httpx_client

    # ------------------------------------------------------------------
    # Async API
    # ------------------------------------------------------------------

    async def fetch_series_async(
        self,
        series_code: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, str]]:
        """Fetch a BCB SGS series asynchronously via httpx.

        Returns raw BCB-format records: [{"data": "dd/mm/yyyy", "valor": "X.XX"}, ...]
        Falls back to cache on failure.
        """
        url = self._build_url(series_code, start_date, end_date)
        logger.info("BCB async fetch series %d: %s -> %s", series_code, start_date, end_date)

        try:
            data = await self._do_async_get(url)
            self._cache.write(series_code, data)
            return data
        except Exception as exc:
            logger.warning(
                "Async fetch failed for series %d: %s -- trying cache",
                series_code, exc,
            )
            cached = self._cache.read(series_code, start_date, end_date)
            if cached:
                logger.info("Cache fallback: %d records for series %d", len(cached), series_code)
                return cached
            raise BCBClientError(f"No data for series {series_code}: {exc}") from exc

    async def _do_async_get(self, url: str) -> list[dict[str, str]]:
        if self._external_client is not None:
            resp = await self._external_client.get(url, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
        else:
            async with httpx.AsyncClient(
                headers={"User-Agent": "MarketAnalysis/1.0"},
                timeout=self._timeout,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

        if not isinstance(data, list):
            raise BCBClientError(f"Unexpected response format: {type(data)}")
        logger.info("Got %d records from BCB", len(data))
        return data

    # ------------------------------------------------------------------
    # Sync API (fallback for simple pipelines / CLI)
    # ------------------------------------------------------------------

    def fetch_series_sync(
        self,
        series_code: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, str]]:
        """Fetch a BCB SGS series synchronously via urllib.

        Returns raw BCB-format records. Falls back to cache on failure.
        """
        url = self._build_url(series_code, start_date, end_date)
        logger.info("BCB sync fetch series %d: %s -> %s", series_code, start_date, end_date)

        try:
            req = Request(url, headers={"User-Agent": "MarketAnalysis/1.0"})
            with urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, list):
                raise BCBClientError(f"Unexpected response format: {type(data)}")
            logger.info("Got %d records for series %d", len(data), series_code)
            self._cache.write(series_code, data)
            return data
        except BCBClientError:
            raise
        except Exception as exc:
            logger.warning(
                "Sync fetch failed for series %d: %s -- trying cache",
                series_code, exc,
            )
            cached = self._cache.read(series_code, start_date, end_date)
            if cached:
                logger.info("Cache fallback: %d records for series %d", len(cached), series_code)
                return cached
            raise BCBClientError(f"No data for series {series_code}: {exc}") from exc

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check if BCB API is reachable."""
        url = (
            BCB_SGS_URL.format(code=432)
            + "?formato=json&dataInicial=01/01/2024&dataFinal=02/01/2024"
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_url(series_code: int, start_date: date, end_date: date) -> str:
        return (
            f"{BCB_SGS_URL.format(code=series_code)}"
            f"?formato=json"
            f"&dataInicial={start_date.strftime('%d/%m/%Y')}"
            f"&dataFinal={end_date.strftime('%d/%m/%Y')}"
        )

    # ------------------------------------------------------------------
    # High-level data collection methods
    # ------------------------------------------------------------------

    def collect_core_rates(
        self,
        start_date: date,
        end_date: date
    ) -> dict[str, float]:
        """Collect and accumulate core BCB rates for the period.

        Returns:
            Dict with keys: 'selic', 'cdi', 'ipca', 'cdi_annual'
        """
        results = {}

        try:
            # SELIC daily accumulation
            selic_data = self.fetch_series_sync(SERIES_SELIC_DAILY, start_date, end_date)
            results['selic'] = self._accumulate_daily_rates(selic_data)
        except BCBClientError:
            logger.warning("Failed to fetch SELIC daily data")
            results['selic'] = 0.0

        try:
            # CDI daily accumulation
            cdi_data = self.fetch_series_sync(SERIES_CDI_DAILY, start_date, end_date)
            results['cdi'] = self._accumulate_daily_rates(cdi_data)
        except BCBClientError:
            logger.warning("Failed to fetch CDI daily data")
            results['cdi'] = 0.0

        try:
            # IPCA monthly accumulation
            ipca_start = start_date.replace(day=1)
            ipca_data = self.fetch_series_sync(SERIES_IPCA, ipca_start, end_date)
            results['ipca'] = self._accumulate_monthly_rates(ipca_data)
        except BCBClientError:
            logger.warning("Failed to fetch IPCA data")
            results['ipca'] = 0.0

        try:
            # CDI annual rate (latest value)
            cdi_annual_data = self.fetch_series_sync(SERIES_CDI_ANNUAL, start_date, end_date)
            if cdi_annual_data:
                results['cdi_annual'] = float(cdi_annual_data[-1]["valor"].replace(",", "."))
            else:
                results['cdi_annual'] = results['cdi']  # Fallback to accumulated
        except BCBClientError:
            logger.warning("Failed to fetch CDI annual rate")
            results['cdi_annual'] = results['cdi']

        return results

    def get_current_selic_target(self) -> float:
        """Get the current SELIC target rate.

        Returns:
            SELIC target rate (% per year).
        """
        try:
            from datetime import datetime
            today = datetime.now().date()
            # Fetch last 30 days to get current rate
            start_date = date(today.year, today.month, 1)

            target_data = self.fetch_series_sync(SERIES_SELIC_TARGET, start_date, today)
            if target_data:
                return float(target_data[-1]["valor"].replace(",", "."))
            else:
                logger.warning("No SELIC target data available")
                return 10.5  # Reasonable fallback
        except BCBClientError:
            logger.warning("Failed to fetch SELIC target rate")
            return 10.5  # Reasonable fallback

    @staticmethod
    def _accumulate_daily_rates(records: list[dict[str, str]]) -> float:
        """Accumulate daily rates using compound interest."""
        accumulated = 1.0
        for record in records:
            daily_rate = float(record["valor"].replace(",", "."))
            accumulated *= 1 + daily_rate / 100
        return (accumulated - 1) * 100

    @staticmethod
    def _accumulate_monthly_rates(records: list[dict[str, str]]) -> float:
        """Accumulate monthly rates using compound interest."""
        accumulated = 1.0
        for record in records:
            monthly_rate = float(record["valor"].replace(",", "."))
            accumulated *= 1 + monthly_rate / 100
        return (accumulated - 1) * 100
