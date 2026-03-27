"""Tests for the async BCB collector."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

if TYPE_CHECKING:
    from pathlib import Path

import httpx
import pytest

from market_analysis.domain.models import (
    BcbDataPoint,
    CollectionResult,
    CollectionStatus,
    CollectorType,
    ErrorResult,
    SeriesCode,
    ValidationResult,
)
from market_analysis.infrastructure.bcb_collector import BCBCollector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bcb_response(
    dates: list[str],
    values: list[str],
) -> list[dict[str, str]]:
    """Build a fake BCB API JSON response."""
    return [
        {"data": d, "valor": v}
        for d, v in zip(dates, values, strict=True)
    ]


SELIC_RESPONSE = _make_bcb_response(
    ["02/01/2026", "03/01/2026"],
    ["13.25", "13.25"],
)

CDI_RESPONSE = _make_bcb_response(
    ["02/01/2026", "03/01/2026"],
    ["0.04926", "0.04926"],
)

IPCA_RESPONSE = _make_bcb_response(
    ["01/01/2026"],
    ["0.52"],
)


@pytest.fixture
def tmp_cache(tmp_path: Path) -> Path:
    """Return a temporary cache directory."""
    return tmp_path / "bcb_cache"


def _mock_response(data: Any, status: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status,
        json=data,
        request=httpx.Request("GET", "https://fake"),
    )


# ---------------------------------------------------------------------------
# collector_type
# ---------------------------------------------------------------------------


class TestCollectorType:
    def test_returns_bcb(self) -> None:
        collector = BCBCollector()
        assert collector.collector_type == CollectorType.BCB


# ---------------------------------------------------------------------------
# collect - happy path
# ---------------------------------------------------------------------------


class TestCollectHappyPath:
    @pytest.mark.asyncio
    async def test_collects_all_series(self, tmp_cache: Path) -> None:
        """All three series return data -> SUCCESS with correct count."""
        responses = [
            _mock_response(SELIC_RESPONSE),
            _mock_response(CDI_RESPONSE),
            _mock_response(IPCA_RESPONSE),
        ]
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=responses)

        collector = BCBCollector(cache_dir=tmp_cache, client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.status == CollectionStatus.SUCCESS
        assert result.items_count == 5  # 2 SELIC + 2 CDI + 1 IPCA
        assert result.collector_type == CollectorType.BCB

    @pytest.mark.asyncio
    async def test_writes_cache(self, tmp_cache: Path) -> None:
        """Successful collection writes cache files."""
        responses = [
            _mock_response(SELIC_RESPONSE),
            _mock_response(CDI_RESPONSE),
            _mock_response(IPCA_RESPONSE),
        ]
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=responses)

        collector = BCBCollector(cache_dir=tmp_cache, client=client)
        await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert (tmp_cache / "432.json").exists()
        assert (tmp_cache / "4389.json").exists()
        assert (tmp_cache / "433.json").exists()


# ---------------------------------------------------------------------------
# collect - partial failure
# ---------------------------------------------------------------------------


class TestCollectPartialFailure:
    @pytest.mark.asyncio
    async def test_partial_when_one_series_fails(
        self, tmp_cache: Path
    ) -> None:
        """One series fails -> PARTIAL with remaining data."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=[
                _mock_response(SELIC_RESPONSE),
                httpx.HTTPStatusError(
                    "Server Error",
                    request=httpx.Request("GET", "https://fake"),
                    response=httpx.Response(500),
                ),
                _mock_response(IPCA_RESPONSE),
            ]
        )

        collector = BCBCollector(cache_dir=tmp_cache, client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.status == CollectionStatus.PARTIAL
        assert result.items_count == 3  # 2 SELIC + 1 IPCA


# ---------------------------------------------------------------------------
# collect - total failure
# ---------------------------------------------------------------------------


class TestCollectTotalFailure:
    @pytest.mark.asyncio
    async def test_error_when_all_series_fail(
        self, tmp_cache: Path
    ) -> None:
        """All series fail with no cache -> ErrorResult."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        collector = BCBCollector(cache_dir=tmp_cache, client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, ErrorResult)
        assert result.status == CollectionStatus.FAILURE
        assert result.error.code == "BCB_NO_DATA"
        assert result.error.retryable is True


# ---------------------------------------------------------------------------
# collect - cache fallback
# ---------------------------------------------------------------------------


class TestCacheFallback:
    @pytest.mark.asyncio
    async def test_uses_cache_on_failure(self, tmp_cache: Path) -> None:
        """When API fails but cache exists, use cached data."""
        tmp_cache.mkdir(parents=True)
        cache_data = [
            {"date": "2026-01-02", "value": "13.25"},
            {"date": "2026-01-03", "value": "13.25"},
        ]
        (tmp_cache / "432.json").write_text(json.dumps(cache_data))

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        collector = BCBCollector(cache_dir=tmp_cache, client=client)
        result = await collector.collect(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, CollectionResult)
        assert result.items_count == 2


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidate:
    @pytest.mark.asyncio
    async def test_valid_items(self) -> None:
        collector = BCBCollector()
        items = [
            BcbDataPoint(
                series_code=SeriesCode.SELIC,
                reference_date=date(2026, 1, 2),
                value=Decimal("13.25"),
            ),
            BcbDataPoint(
                series_code=SeriesCode.CDI,
                reference_date=date(2026, 1, 2),
                value=Decimal("0.04926"),
            ),
        ]
        result = await collector.validate(items)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.items_accepted == 2
        assert result.items_rejected == 0

    @pytest.mark.asyncio
    async def test_suspicious_value_warns(self) -> None:
        collector = BCBCollector()
        items = [
            BcbDataPoint(
                series_code=SeriesCode.SELIC,
                reference_date=date(2026, 1, 2),
                value=Decimal("10001"),
            ),
        ]
        result = await collector.validate(items)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "Suspicious" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        collector = BCBCollector()
        result = await collector.validate([])
        assert result.is_valid is True
        assert result.items_accepted == 0


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        resp = _mock_response([{"data": "01/01/2024", "valor": "11.75"}])
        client.get = AsyncMock(return_value=resp)

        collector = BCBCollector(client=client)
        assert await collector.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy(self) -> None:
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        collector = BCBCollector(client=client)
        assert await collector.health_check() is False


# ---------------------------------------------------------------------------
# _parse_records edge cases
# ---------------------------------------------------------------------------


class TestParseRecords:
    def test_skips_invalid_records(self) -> None:
        collector = BCBCollector()
        raw = [
            {"data": "02/01/2026", "valor": "13.25"},
            {"data": "invalid", "valor": "13.25"},
            {"data": "03/01/2026", "valor": "not_a_number"},
            {"data": "04/01/2026", "valor": "13.50"},
        ]
        points = collector._parse_records(SeriesCode.SELIC, raw)
        assert len(points) == 2
        assert points[0].reference_date == date(2026, 1, 2)
        assert points[1].reference_date == date(2026, 1, 4)
