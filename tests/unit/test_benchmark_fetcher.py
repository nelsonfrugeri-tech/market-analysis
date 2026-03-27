"""Tests for the synchronous BCB benchmark fetcher."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from market_analysis.infrastructure.benchmark_fetcher import (
    BenchmarkFetchError,
    accumulate_daily_rates,
    accumulate_monthly_rates,
    collect_benchmarks,
)


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


class TestCollectBenchmarks:
    @patch("market_analysis.infrastructure.benchmark_fetcher._fetch_series")
    def test_returns_all_benchmarks(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{"data": "01/01/2026", "valor": "0.05"}]

        result = collect_benchmarks(date(2026, 1, 1), date(2026, 1, 31))

        assert "selic" in result
        assert "cdi" in result
        assert "ipca" in result
        assert all(isinstance(v, float) for v in result.values())

    @patch("market_analysis.infrastructure.benchmark_fetcher._fetch_series")
    def test_handles_api_failure_gracefully(self, mock_fetch: MagicMock) -> None:
        mock_fetch.side_effect = BenchmarkFetchError("API down")

        result = collect_benchmarks(date(2026, 1, 1), date(2026, 1, 31))

        assert result["selic"] == 0.0
        assert result["cdi"] == 0.0
        assert result["ipca"] == 0.0
