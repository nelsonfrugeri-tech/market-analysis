"""Tests for the PDF report generator.

Covers both sync generate_pdf, generate_pdf_bytes, and AsyncPDFReportGenerator.
"""

from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.infrastructure.news_fetcher import NewsItem
from market_analysis.infrastructure.pdf_generator import (
    AsyncPDFReportGenerator,
    generate_pdf,
    generate_pdf_bytes,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(
    dt: date, nav: float, equity: float = 800_000_000.0
) -> FundDailyRecord:
    return FundDailyRecord(
        cnpj="43.121.002/0001-41",
        date=dt,
        nav=nav,
        equity=equity,
        total_value=equity,
        deposits=1_000_000.0,
        withdrawals=500_000.0,
        shareholders=50000,
    )


@pytest.fixture
def sample_performance() -> FundPerformance:
    records = [
        _make_record(
            date(2026, 1, d),
            nav=1.58 + d * 0.0001,
            equity=800_000_000 + d * 100_000,
        )
        for d in range(2, 22)
    ]
    return FundPerformance(
        fund_cnpj="43.121.002/0001-41",
        fund_name="Nu Reserva Planejada",
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 21),
        nav_start=1.5802,
        nav_end=1.5821,
        return_pct=0.1202,
        equity_start=800_200_000.0,
        equity_end=802_100_000.0,
        volatility=0.85,
        shareholders_current=50000,
        benchmark_selic=0.10,
        benchmark_cdi=0.09,
        benchmark_ipca=0.04,
        vs_selic=0.0202,
        vs_cdi=0.0302,
        vs_ipca=0.0802,
        trend_30d="up",
        sharpe_ratio=0.15,
        alpha=0.02,
        beta=0.95,
        var_95=-1.2,
        max_drawdown=-0.05,
        daily_records=records,
    )


@pytest.fixture
def sample_performance_no_records() -> FundPerformance:
    """Performance with no daily records (no charts)."""
    return FundPerformance(
        fund_cnpj="43.121.002/0001-41",
        fund_name="Nu Reserva Planejada",
        period_start=date(2026, 1, 2),
        period_end=date(2026, 1, 21),
        nav_start=1.5802,
        nav_end=1.5821,
        return_pct=0.1202,
        equity_start=800_200_000.0,
        equity_end=802_100_000.0,
        volatility=0.85,
        shareholders_current=50000,
        benchmark_selic=0.10,
        benchmark_cdi=0.09,
        benchmark_ipca=0.04,
        vs_selic=0.0202,
        vs_cdi=0.0302,
        vs_ipca=0.0802,
        trend_30d="flat",
        sharpe_ratio=0.0,
        alpha=0.0,
        beta=1.0,
        var_95=0.0,
        max_drawdown=0.0,
        daily_records=[],
    )


@pytest.fixture
def sample_news() -> list[NewsItem]:
    return [
        NewsItem(
            title="Nubank reports record quarterly results",
            link="https://example.com/1",
            pub_date=datetime(2026, 3, 25, 10, 0),
            source="Reuters",
        ),
        NewsItem(
            title="Nu Reserva Planejada attracts new investors",
            link="https://example.com/2",
            pub_date=datetime(2026, 3, 24, 14, 30),
            source="InfoMoney",
        ),
    ]


# ---------------------------------------------------------------------------
# generate_pdf (file-based)
# ---------------------------------------------------------------------------


class TestGeneratePdf:
    def test_generates_valid_pdf(
        self, sample_performance: FundPerformance, tmp_path: Path
    ) -> None:
        output = tmp_path / "test_report.pdf"
        result = generate_pdf(sample_performance, output_path=output)

        assert result.exists()
        assert result.suffix == ".pdf"
        assert result.stat().st_size > 0

        with open(result, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_generates_with_news(
        self,
        sample_performance: FundPerformance,
        sample_news: list[NewsItem],
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "test_report_news.pdf"
        result = generate_pdf(
            sample_performance, news=sample_news, output_path=output
        )

        assert result.exists()
        assert result.stat().st_size > 0

    def test_generates_without_records(
        self,
        sample_performance_no_records: FundPerformance,
        tmp_path: Path,
    ) -> None:
        """PDF should work even without daily records (no charts)."""
        output = tmp_path / "test_no_charts.pdf"
        result = generate_pdf(
            sample_performance_no_records, output_path=output
        )

        assert result.exists()
        with open(result, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_creates_parent_directories(
        self, sample_performance: FundPerformance, tmp_path: Path
    ) -> None:
        output = tmp_path / "deep" / "nested" / "report.pdf"
        result = generate_pdf(sample_performance, output_path=output)
        assert result.exists()

    def test_default_output_path(
        self,
        sample_performance: FundPerformance,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            result = generate_pdf(sample_performance)
            assert result.exists()
            assert "nu_reserva_report" in result.name


# ---------------------------------------------------------------------------
# generate_pdf_bytes
# ---------------------------------------------------------------------------


class TestGeneratePdfBytes:
    def test_returns_bytes(
        self, sample_performance: FundPerformance
    ) -> None:
        result = generate_pdf_bytes(sample_performance)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:5] == b"%PDF-"

    def test_with_news(
        self,
        sample_performance: FundPerformance,
        sample_news: list[NewsItem],
    ) -> None:
        result = generate_pdf_bytes(sample_performance, news=sample_news)
        assert result[:5] == b"%PDF-"

    def test_without_records(
        self, sample_performance_no_records: FundPerformance
    ) -> None:
        result = generate_pdf_bytes(sample_performance_no_records)
        assert result[:5] == b"%PDF-"

    def test_content_size_with_charts_larger(
        self,
        sample_performance: FundPerformance,
        sample_performance_no_records: FundPerformance,
    ) -> None:
        """PDF with charts should be significantly larger."""
        with_charts = generate_pdf_bytes(sample_performance)
        without_charts = generate_pdf_bytes(sample_performance_no_records)
        assert len(with_charts) > len(without_charts)


# ---------------------------------------------------------------------------
# AsyncPDFReportGenerator
# ---------------------------------------------------------------------------


class TestAsyncPDFReportGenerator:
    @pytest.mark.asyncio
    async def test_generate_returns_pdf_bytes(
        self, sample_performance: FundPerformance
    ) -> None:
        generator = AsyncPDFReportGenerator()
        result = await generator.generate(sample_performance)

        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_generate_with_news(
        self,
        sample_performance: FundPerformance,
        sample_news: list[NewsItem],
    ) -> None:
        generator = AsyncPDFReportGenerator()
        result = await generator.generate(
            sample_performance, news=sample_news
        )

        assert isinstance(result, bytes)
        assert len(result) > 0
