"""Tests for the unified benchmark collection system.

Covers: BCBClient, benchmark_calculator, cache_manager, data_models.
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from market_analysis.infrastructure.benchmarks import (
    BCBClient,
    BCBClientError,
    BenchmarkCacheManager,
    BenchmarkData,
    DailyBenchmarkRecord,
    accumulate_daily_rates,
    accumulate_monthly_rates,
    calculate_cdb_estimated,
    calculate_poupanca_estimated,
    collect_all_benchmarks,
    collect_all_benchmarks_sync,
)


# ---------------------------------------------------------------------------
# accumulate_daily_rates
# ---------------------------------------------------------------------------


class TestAccumulateDailyRates:
    def test_single_rate(self) -> None:
        records = [{"data": "01/01/2026", "valor": "0.05"}]
        result = accumulate_daily_rates(records)
        assert result == pytest.approx(0.05)

    def test_compound_accumulation(self) -> None:
        records = [
            {"data": "01/01/2026", "valor": "0.05"},
            {"data": "02/01/2026", "valor": "0.05"},
        ]
        expected = ((1.0005 * 1.0005) - 1) * 100
        result = accumulate_daily_rates(records)
        assert result == pytest.approx(expected)

    def test_empty_records(self) -> None:
        result = accumulate_daily_rates([])
        assert result == pytest.approx(0.0)

    def test_comma_decimal_separator(self) -> None:
        records = [{"data": "01/01/2026", "valor": "0,05"}]
        result = accumulate_daily_rates(records)
        assert result == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# accumulate_monthly_rates
# ---------------------------------------------------------------------------


class TestAccumulateMonthlyRates:
    def test_single_month(self) -> None:
        records = [{"data": "01/01/2026", "valor": "0.50"}]
        result = accumulate_monthly_rates(records)
        assert result == pytest.approx(0.50)

    def test_two_months(self) -> None:
        records = [
            {"data": "01/01/2026", "valor": "0.50"},
            {"data": "01/02/2026", "valor": "0.40"},
        ]
        expected = ((1.005 * 1.004) - 1) * 100
        result = accumulate_monthly_rates(records)
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Derived calculations
# ---------------------------------------------------------------------------


class TestDerivedCalculations:
    def test_cdb_estimated(self) -> None:
        assert calculate_cdb_estimated(10.0) == pytest.approx(9.5)

    def test_cdb_estimated_zero(self) -> None:
        assert calculate_cdb_estimated(0.0) == pytest.approx(0.0)

    def test_poupanca_selic_high(self) -> None:
        # SELIC > 8.5% -> fixed 0.5%/month rule
        result = calculate_poupanca_estimated(13.75, 5.0)
        # Should be less than SELIC accumulated
        assert result > 0
        assert result < 5.0

    def test_poupanca_selic_low(self) -> None:
        # SELIC <= 8.5% -> 70% of SELIC
        result = calculate_poupanca_estimated(6.0, 3.0)
        assert result == pytest.approx(2.1)

    def test_poupanca_zero_selic(self) -> None:
        result = calculate_poupanca_estimated(0.0, 0.0)
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# BenchmarkCacheManager
# ---------------------------------------------------------------------------


class TestBenchmarkCacheManager:
    def test_write_and_read(self, tmp_path: Path) -> None:
        cache = BenchmarkCacheManager(cache_dir=tmp_path)
        records = [
            {"data": "02/01/2026", "valor": "0.05"},
            {"data": "03/01/2026", "valor": "0.04"},
        ]
        cache.write(11, records)

        result = cache.read(11, date(2026, 1, 1), date(2026, 1, 5))
        assert len(result) == 2
        assert result[0]["valor"] == "0.05"

    def test_read_filters_by_date(self, tmp_path: Path) -> None:
        cache = BenchmarkCacheManager(cache_dir=tmp_path)
        records = [
            {"data": "02/01/2026", "valor": "0.05"},
            {"data": "15/01/2026", "valor": "0.04"},
        ]
        cache.write(11, records)

        result = cache.read(11, date(2026, 1, 1), date(2026, 1, 10))
        assert len(result) == 1

    def test_read_empty_cache(self, tmp_path: Path) -> None:
        cache = BenchmarkCacheManager(cache_dir=tmp_path)
        result = cache.read(99, date(2026, 1, 1), date(2026, 1, 31))
        assert result == []

    def test_write_merges_with_existing(self, tmp_path: Path) -> None:
        cache = BenchmarkCacheManager(cache_dir=tmp_path)
        cache.write(11, [{"data": "02/01/2026", "valor": "0.05"}])
        cache.write(11, [{"data": "03/01/2026", "valor": "0.04"}])

        result = cache.read(11, date(2026, 1, 1), date(2026, 1, 31))
        assert len(result) == 2


# ---------------------------------------------------------------------------
# BenchmarkData
# ---------------------------------------------------------------------------


class TestBenchmarkData:
    def test_to_legacy_dict(self) -> None:
        data = BenchmarkData(
            date_range=(date(2026, 1, 1), date(2026, 3, 31)),
            selic_accumulated=3.5,
            cdi_accumulated=3.4,
            ipca_accumulated=1.2,
            selic_annual_rate=13.75,
            cdi_annual_rate=13.65,
            cdb_estimated=3.23,
            poupanca_estimated=2.1,
        )
        legacy = data.to_legacy_dict()
        assert legacy["selic"] == 3.5
        assert legacy["cdi"] == 3.4
        assert legacy["ipca"] == 1.2
        assert "cdb" in legacy
        assert "poupanca" in legacy


# ---------------------------------------------------------------------------
# collect_all_benchmarks_sync (integration-style with mocked HTTP)
# ---------------------------------------------------------------------------


class TestCollectAllBenchmarksSync:
    @patch.object(BCBClient, "fetch_series_sync")
    def test_collects_all_series(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{"data": "02/01/2026", "valor": "0.05"}]

        result = collect_all_benchmarks_sync(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, BenchmarkData)
        assert result.selic_accumulated > 0
        assert result.cdi_accumulated > 0
        assert result.cdb_estimated > 0
        assert result.poupanca_estimated >= 0
        assert result.data_completeness == 1.0
        assert len(result.daily_records) > 0

    @patch.object(BCBClient, "fetch_series_sync")
    def test_handles_partial_failure(self, mock_fetch: MagicMock) -> None:
        def side_effect(code: int, start: date, end: date) -> list:
            if code == 11:
                raise BCBClientError("API down")
            return [{"data": "02/01/2026", "valor": "0.05"}]

        mock_fetch.side_effect = side_effect

        result = collect_all_benchmarks_sync(date(2026, 1, 1), date(2026, 1, 31))

        assert result.source_quality == "partial"
        assert result.fallback_used is True
        assert result.selic_accumulated == 0.0
        assert result.cdi_accumulated > 0

    @patch.object(BCBClient, "fetch_series_sync")
    def test_handles_total_failure(self, mock_fetch: MagicMock) -> None:
        mock_fetch.side_effect = BCBClientError("API down")

        result = collect_all_benchmarks_sync(date(2026, 1, 1), date(2026, 1, 31))

        assert result.source_quality == "fallback"
        assert result.data_completeness == 0.0
        assert result.selic_accumulated == 0.0
        assert result.cdi_accumulated == 0.0


# ---------------------------------------------------------------------------
# collect_all_benchmarks (async)
# ---------------------------------------------------------------------------


class TestCollectAllBenchmarksAsync:
    @pytest.mark.asyncio
    async def test_collects_all_series(self) -> None:
        mock_client = MagicMock(spec=BCBClient)
        mock_client.fetch_series_async = AsyncMock(
            return_value=[{"data": "02/01/2026", "valor": "0.05"}]
        )

        result = await collect_all_benchmarks(
            date(2026, 1, 1), date(2026, 1, 31), client=mock_client
        )

        assert isinstance(result, BenchmarkData)
        assert result.selic_accumulated > 0
        assert result.cdi_accumulated > 0
        assert result.data_completeness == 1.0

    @pytest.mark.asyncio
    async def test_handles_failure(self) -> None:
        mock_client = MagicMock(spec=BCBClient)
        mock_client.fetch_series_async = AsyncMock(
            side_effect=BCBClientError("fail")
        )

        result = await collect_all_benchmarks(
            date(2026, 1, 1), date(2026, 1, 31), client=mock_client
        )

        assert result.source_quality == "fallback"
        assert result.data_completeness == 0.0


# ---------------------------------------------------------------------------
# Backward compat: old benchmark_fetcher still works
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    @patch.object(BCBClient, "fetch_series_sync")
    def test_old_collect_benchmarks(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{"data": "02/01/2026", "valor": "0.05"}]

        from market_analysis.infrastructure.benchmark_fetcher import collect_benchmarks
        result = collect_benchmarks(date(2026, 1, 1), date(2026, 1, 31))

        assert isinstance(result, dict)
        assert "selic" in result
        assert "cdi" in result
        assert "ipca" in result
