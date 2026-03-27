"""BCB async collector for benchmark rates (SELIC, CDI, IPCA).

Implements the BaseCollector protocol defined in domain/interfaces.py.
Uses httpx for async HTTP and the BCB SGS REST API directly.

API docs: https://dadosabertos.bcb.gov.br/dataset/sgs
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from market_analysis.domain.models import (
    BcbDataPoint,
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorDetail,
    ErrorResult,
    SeriesCode,
    ValidationResult,
)
from market_analysis.domain.schemas import BcbApiRecord

logger = logging.getLogger(__name__)

BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

# Series codes mapped for convenience
SERIES_MAP: dict[SeriesCode, int] = {
    SeriesCode.SELIC: 432,
    SeriesCode.CDI: 4389,
    SeriesCode.IPCA: 433,
}

DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_DIR = Path(".cache/bcb")


class BCBCollector:
    """Async collector for BCB time-series data.

    Satisfies the BaseCollector protocol:
      - collector_type -> CollectorType.BCB
      - collect(start_date, end_date) -> CollectionResult | ErrorResult
      - validate(items) -> ValidationResult
      - health_check() -> bool
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        cache_dir: Path | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._external_client = client
        self._last_collected: list[BcbDataPoint] = []

    @property
    def last_collected(self) -> list[BcbDataPoint]:
        """Items from the most recent collect() call, for persistence."""
        return list(self._last_collected)

    @property
    def collector_type(self) -> CollectorType:
        return CollectorType.BCB

    async def collect(
        self,
        start_date: date,
        end_date: date,
    ) -> CollectionResult | ErrorResult:
        """Fetch SELIC, CDI and IPCA series for the given date range."""
        started_at = datetime.now(UTC)
        self._last_collected = []
        all_points: list[BcbDataPoint] = []
        errors: list[str] = []

        for series_code, api_code in SERIES_MAP.items():
            try:
                raw_records = await self._fetch_series(
                    api_code, start_date, end_date
                )
                points = self._parse_records(series_code, raw_records)
                all_points.extend(points)
            except Exception as exc:
                msg = f"Failed to fetch {series_code.name}: {exc}"
                logger.warning(msg)
                errors.append(msg)

                # Try cache fallback
                cached = self._read_cache(series_code, start_date, end_date)
                if cached:
                    logger.info(
                        "Using %d cached records for %s",
                        len(cached),
                        series_code.name,
                    )
                    all_points.extend(cached)

        finished_at = datetime.now(UTC)
        duration = (finished_at - started_at).total_seconds()

        if not all_points:
            return ErrorResult(
                collector_type=CollectorType.BCB,
                attempted_at=finished_at,
                error=ErrorDetail(
                    code="BCB_NO_DATA",
                    message=f"No data collected: {'; '.join(errors)}",
                    retryable=True,
                ),
                attempts=1,
                status=CollectionStatus.FAILURE,
            )

        # Store for retrieval and write cache
        self._last_collected = all_points
        self._write_cache(all_points)

        status = (
            CollectionStatus.SUCCESS if not errors else CollectionStatus.PARTIAL
        )
        return CollectionResult(
            collector_type=CollectorType.BCB,
            collected_at=finished_at,
            items_count=len(all_points),
            duration_seconds=duration,
            status=status,
        )

    async def validate(
        self,
        items: list[BcbDataPoint],  # type: ignore[override]
    ) -> ValidationResult:
        """Validate BCB data points."""
        errors: list[str] = []
        warnings: list[str] = []
        accepted = 0
        rejected = 0

        for item in items:
            try:
                if item.series_code not in SeriesCode:
                    errors.append(
                        f"Unknown series code: {item.series_code}"
                    )
                    rejected += 1
                    continue

                if item.value < Decimal("-100") or item.value > Decimal("10000"):
                    warnings.append(
                        f"Suspicious value {item.value} for "
                        f"{item.series_code} on {item.reference_date}"
                    )

                accepted += 1
            except Exception as exc:
                errors.append(f"Validation error: {exc}")
                rejected += 1

        return ValidationResult(
            is_valid=rejected == 0,
            errors=errors,
            warnings=warnings,
            items_accepted=accepted,
            items_rejected=rejected,
        )

    async def health_check(self) -> bool:
        """Check if BCB API is reachable."""
        url = (
            BCB_SGS_URL.format(code=432)
            + "?formato=json&dataInicial=01/01/2024&dataFinal=02/01/2024"
        )
        try:
            async with self._get_client() as client:
                resp = await client.get(url, timeout=10)
                return resp.status_code == 200
        except Exception:
            return False

    # -----------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        """Return an httpx client, reusing external one if provided."""
        if self._external_client is not None:
            # Wrap in a no-op context manager for consistency
            return _NoCloseClient(self._external_client)
        return httpx.AsyncClient(
            headers={"User-Agent": "MarketAnalysis/1.0"},
            timeout=self._timeout,
        )

    async def _fetch_series(
        self,
        code: int,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, str]]:
        """Fetch a single BCB SGS series as raw JSON records."""
        url = (
            f"{BCB_SGS_URL.format(code=code)}"
            f"?formato=json"
            f"&dataInicial={start_date.strftime('%d/%m/%Y')}"
            f"&dataFinal={end_date.strftime('%d/%m/%Y')}"
        )
        logger.info("Fetching BCB series %d: %s -> %s", code, start_date, end_date)

        async with self._get_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            raise ValueError(f"Unexpected response format for series {code}")

        logger.info("Got %d records for series %d", len(data), code)
        return data

    def _parse_records(
        self,
        series_code: SeriesCode,
        raw_records: list[dict[str, str]],
    ) -> list[BcbDataPoint]:
        """Parse and validate raw BCB API records into domain objects."""
        points: list[BcbDataPoint] = []
        for raw in raw_records:
            try:
                record = BcbApiRecord(
                    data=raw.get("data", ""),
                    valor=raw.get("valor", ""),
                )
                points.append(
                    BcbDataPoint(
                        series_code=series_code,
                        reference_date=record.to_date(),
                        value=record.to_decimal(),
                    )
                )
            except Exception as exc:
                logger.debug(
                    "Skipping invalid BCB record %s: %s", raw, exc
                )
        return points

    def _cache_path(self, series_code: SeriesCode) -> Path:
        """Return the cache file path for a series."""
        return self._cache_dir / f"{series_code.value}.json"

    def _write_cache(self, points: list[BcbDataPoint]) -> None:
        """Write data points to local cache files grouped by series."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            by_series: dict[SeriesCode, list[dict[str, str]]] = {}
            for p in points:
                by_series.setdefault(p.series_code, []).append(
                    {
                        "date": p.reference_date.isoformat(),
                        "value": str(p.value),
                    }
                )
            for series_code, records in by_series.items():
                path = self._cache_path(series_code)
                # Merge with existing cache
                existing: list[dict[str, str]] = []
                if path.exists():
                    existing = json.loads(path.read_text())
                existing_dates = {r["date"] for r in existing}
                for r in records:
                    if r["date"] not in existing_dates:
                        existing.append(r)
                path.write_text(json.dumps(existing, indent=2))
        except Exception as exc:
            logger.warning("Failed to write BCB cache: %s", exc)

    def _read_cache(
        self,
        series_code: SeriesCode,
        start_date: date,
        end_date: date,
    ) -> list[BcbDataPoint]:
        """Read cached data points for a series within date range."""
        path = self._cache_path(series_code)
        if not path.exists():
            return []
        try:
            records = json.loads(path.read_text())
            points: list[BcbDataPoint] = []
            for r in records:
                ref_date = date.fromisoformat(r["date"])
                if start_date <= ref_date <= end_date:
                    points.append(
                        BcbDataPoint(
                            series_code=series_code,
                            reference_date=ref_date,
                            value=Decimal(r["value"]),
                        )
                    )
            return points
        except Exception as exc:
            logger.warning("Failed to read BCB cache for %s: %s", series_code, exc)
            return []


class _NoCloseClient:
    """Wraps an externally-owned httpx.AsyncClient to prevent closing it."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *args: Any) -> None:
        pass  # Do not close the external client
