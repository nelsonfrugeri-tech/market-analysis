"""Tests for the PDF report generator.

Covers both sync generate_pdf, generate_pdf_bytes, AsyncPDFReportGenerator,
and the Metrics Explained section (Issue #64).
"""

from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from market_analysis.ai.explainer import ExplanationResult
from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.infrastructure.news_fetcher import NewsItem
from market_analysis.infrastructure.pdf_generator import (
    AsyncPDFReportGenerator,
    _build_explained_metrics_section,
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


def _make_performance(*, with_records: bool = True) -> FundPerformance:
    records = (
        [
            _make_record(
                date(2026, 1, d),
                nav=1.58 + d * 0.0001,
                equity=800_000_000 + d * 100_000,
            )
            for d in range(2, 22)
        ]
        if with_records
        else []
    )
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
        trend_30d="up" if with_records else "flat",
        sharpe_ratio=0.15,
        alpha=0.02,
        beta=0.95,
        var_95=-1.2,
        max_drawdown=-0.05,
        daily_records=records,
    )


@pytest.fixture
def sample_performance() -> FundPerformance:
    return _make_performance(with_records=True)


@pytest.fixture
def sample_performance_no_records() -> FundPerformance:
    """Performance with no daily records (no charts)."""
    return _make_performance(with_records=False)


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


def _make_explanations() -> list[ExplanationResult]:
    """Create sample ExplanationResult objects for testing."""
    return [
        ExplanationResult(
            metric_name="cumulative_return",
            display_name="Retorno Acumulado",
            category="performance",
            text="O fundo rendeu 12,5% no periodo. Isso equivale a R$ 1.250 "
            "de lucro para cada R$ 10.000 investidos.",
            provider="anthropic",
            latency_ms=350.0,
        ),
        ExplanationResult(
            metric_name="volatility",
            display_name="Volatilidade",
            category="risk",
            text="A volatilidade de 0,8% indica que o fundo e bastante estavel.",
            provider="static",
        ),
        ExplanationResult(
            metric_name="sharpe_ratio",
            display_name="Indice Sharpe",
            category="risk",
            text="O Sharpe de 1,2 indica boa relacao risco-retorno.",
            provider="cache",
            cached=True,
        ),
        ExplanationResult(
            metric_name="alpha",
            display_name="Alpha",
            category="efficiency",
            text="O Alpha de 0,8% mostra que o gestor agrega valor.",
            provider="ollama",
            latency_ms=500.0,
        ),
        ExplanationResult(
            metric_name="positive_months_pct",
            display_name="Meses Positivos",
            category="consistency",
            text="O fundo teve retorno positivo em 95% dos meses.",
            provider="static",
        ),
    ]


@pytest.fixture
def sample_explanations() -> list[ExplanationResult]:
    return _make_explanations()


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


# ---------------------------------------------------------------------------
# Metrics Explained Section (Issue #64)
# ---------------------------------------------------------------------------


class TestMetricsExplainedSection:
    def test_pdf_with_explanations_is_larger(
        self,
        sample_performance: FundPerformance,
        sample_explanations: list[ExplanationResult],
    ) -> None:
        """PDF with explained metrics should be larger than without."""
        without = generate_pdf_bytes(sample_performance)
        with_exp = generate_pdf_bytes(
            sample_performance, metric_explanations=sample_explanations
        )
        assert len(with_exp) > len(without)

    def test_pdf_file_with_explanations(
        self,
        sample_performance: FundPerformance,
        sample_explanations: list[ExplanationResult],
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "test_explained.pdf"
        result = generate_pdf(
            sample_performance,
            metric_explanations=sample_explanations,
            output_path=output,
        )
        assert result.exists()
        assert result.stat().st_size > 0
        with open(result, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_backward_compat_without_explanations(
        self, sample_performance: FundPerformance
    ) -> None:
        """Existing calls without metric_explanations still work."""
        result = generate_pdf_bytes(sample_performance)
        assert result[:5] == b"%PDF-"

    def test_empty_explanations_list(
        self, sample_performance: FundPerformance
    ) -> None:
        """Empty list should produce same PDF as None."""
        without = generate_pdf_bytes(sample_performance, metric_explanations=None)
        with_empty = generate_pdf_bytes(sample_performance, metric_explanations=[])
        # Both should be valid PDFs of similar size
        assert abs(len(without) - len(with_empty)) < 100

    def test_build_section_returns_flowables(
        self, sample_explanations: list[ExplanationResult]
    ) -> None:
        from reportlab.lib.styles import getSampleStyleSheet

        styles = getSampleStyleSheet()
        elements = _build_explained_metrics_section(sample_explanations, styles)
        assert len(elements) > 0

    def test_single_category(self) -> None:
        """Section works with only one category."""
        explanations = [
            ExplanationResult(
                metric_name="volatility",
                display_name="Volatilidade",
                category="risk",
                text="Texto de teste sobre volatilidade.",
                provider="static",
            ),
        ]
        perf = _make_performance(with_records=False)
        result = generate_pdf_bytes(perf, metric_explanations=explanations)
        assert result[:5] == b"%PDF-"

    def test_all_four_categories(
        self, sample_explanations: list[ExplanationResult]
    ) -> None:
        """Section renders all four category banners."""
        from reportlab.lib.styles import getSampleStyleSheet

        styles = getSampleStyleSheet()
        elements = _build_explained_metrics_section(sample_explanations, styles)
        # 2 header elements + 4 categories * (banner + spacer) + 5 KeepTogether cards
        assert len(elements) >= 2 + 4 * 2 + 5

    @pytest.mark.asyncio
    async def test_async_generator_with_explanations(
        self,
        sample_performance: FundPerformance,
        sample_explanations: list[ExplanationResult],
    ) -> None:
        generator = AsyncPDFReportGenerator()
        result = await generator.generate(
            sample_performance, metric_explanations=sample_explanations
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"
