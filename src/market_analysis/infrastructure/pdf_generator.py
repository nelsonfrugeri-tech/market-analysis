"""PDF report generator using ReportLab and Matplotlib.

Generates a professional fund analysis report with:
- Header with report date and fund info
- Performance metrics table
- NAV evolution chart
- Equity evolution chart
- Benchmark comparison
- Metrics Explained educational section (optional, Issue #64)
- News section
"""

from __future__ import annotations

import io
import logging
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from market_analysis.domain.models.fund import FundDailyRecord, FundPerformance
from market_analysis.infrastructure.news_fetcher import NewsItem

logger = logging.getLogger(__name__)

# Colors
NUBANK_PURPLE = "#820AD1"
DARK_GRAY = "#333333"
LIGHT_GRAY = "#F5F5F5"
GREEN = "#27AE60"
RED = "#E74C3C"
BLUE = "#2980B9"
WARM_GRAY = "#7F8C8D"

# Category display metadata for the explained metrics section
_CATEGORY_LABELS: dict[str, tuple[str, str]] = {
    "performance": ("Desempenho", "#27AE60"),
    "risk": ("Risco", "#E74C3C"),
    "efficiency": ("Eficiencia", "#2980B9"),
    "consistency": ("Consistencia", "#F39C12"),
}


# ---------------------------------------------------------------------------
# Metrics Explained section builder (Issue #64)
# ---------------------------------------------------------------------------


def _build_explained_metrics_section(
    explanations: list[Any],
    styles: Any,
) -> list[Any]:
    """Build the 'Metrics Explained' educational section.

    Groups explanations by category and renders each as a visual card
    with display name, glossary term, and educational text.

    Args:
        explanations: List of ExplanationResult from MetricsExplainer.
        styles: ReportLab stylesheet (getSampleStyleSheet result).

    Returns:
        List of ReportLab flowable elements.
    """
    elements: list[Any] = []

    # Section header
    section_title = ParagraphStyle(
        "ExplainedTitle",
        parent=styles["Heading1"],
        fontSize=15,
        textColor=colors.HexColor(NUBANK_PURPLE),
        spaceBefore=24,
        spaceAfter=4,
    )
    section_intro = ParagraphStyle(
        "ExplainedIntro",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor(WARM_GRAY),
        leading=12,
        spaceAfter=12,
    )
    category_style = ParagraphStyle(
        "CategoryHeader",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.white,
        spaceBefore=12,
        spaceAfter=6,
    )
    metric_name_style = ParagraphStyle(
        "MetricName",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(DARK_GRAY),
        spaceBefore=4,
        spaceAfter=2,
    )
    glossary_style = ParagraphStyle(
        "GlossaryTerm",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor(WARM_GRAY),
        leading=10,
        spaceAfter=4,
    )
    explanation_style = ParagraphStyle(
        "ExplanationText",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor(DARK_GRAY),
        leading=13,
        spaceAfter=2,
    )
    analogy_style = ParagraphStyle(
        "AnalogyText",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor(BLUE),
        leading=11,
        leftIndent=12,
        spaceAfter=6,
    )
    provider_style = ParagraphStyle(
        "ProviderBadge",
        parent=styles["Normal"],
        fontSize=6,
        textColor=colors.HexColor("#AAAAAA"),
        alignment=2,  # right-aligned
    )

    elements.append(
        Paragraph("Metricas Explicadas — Guia do Investidor", section_title)
    )
    elements.append(
        Paragraph(
            "As metricas abaixo sao explicadas em linguagem simples para ajudar "
            "na compreensao do desempenho do fundo. Nenhuma informacao aqui "
            "constitui recomendacao de investimento.",
            section_intro,
        )
    )

    # Group by category (explanations should already be sorted by category)
    grouped: dict[str, list[Any]] = {}
    for exp in explanations:
        grouped.setdefault(exp.category, []).append(exp)

    # Render in canonical order
    for cat_key in ("performance", "risk", "efficiency", "consistency"):
        items = grouped.get(cat_key)
        if not items:
            continue

        cat_label, cat_color = _CATEGORY_LABELS.get(cat_key, (cat_key, DARK_GRAY))

        # Category banner
        cat_banner_data = [[Paragraph(cat_label, category_style)]]
        cat_banner = Table(cat_banner_data, colWidths=[16 * cm])
        cat_banner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(cat_color)),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(cat_banner)
        elements.append(Spacer(1, 4))

        for exp in items:
            card_elements: list[Any] = []

            # Metric display name
            card_elements.append(
                Paragraph(exp.display_name, metric_name_style)
            )

            # Glossary term (if available via template registry)
            glossary = getattr(exp, "glossary_term", "")
            if glossary:
                card_elements.append(Paragraph(glossary, glossary_style))

            # Main explanation text
            card_elements.append(Paragraph(exp.text, explanation_style))

            # Analogy (if available)
            analogy = getattr(exp, "analogy", "")
            if analogy:
                card_elements.append(
                    Paragraph(f"Analogia: {analogy}", analogy_style)
                )

            # Provider badge (discrete)
            provider_label = {
                "anthropic": "via Claude AI",
                "ollama": "via Ollama",
                "static": "texto padrao",
                "cache": "em cache",
            }.get(exp.provider, exp.provider)
            card_elements.append(Paragraph(provider_label, provider_style))

            # Separator
            card_elements.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#EEEEEE"),
                    spaceAfter=4,
                    spaceBefore=2,
                )
            )

            # KeepTogether prevents page break in the middle of a card
            elements.append(KeepTogether(card_elements))

    return elements


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------


def _create_nav_chart(records: list[FundDailyRecord]) -> bytes:
    """Create NAV evolution line chart, return PNG bytes."""
    dates = [r.date for r in records]
    navs = [r.nav for r in records]

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(dates, navs, color=NUBANK_PURPLE, linewidth=1.5)
    ax.fill_between(dates, navs, alpha=0.1, color=NUBANK_PURPLE)
    ax.set_title("NAV Evolution (Valor da Cota)", fontsize=10, fontweight="bold")
    ax.set_ylabel("R$", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _create_equity_chart(records: list[FundDailyRecord]) -> bytes:
    """Create equity (patrimonio liquido) evolution chart, return PNG bytes."""
    dates = [r.date for r in records]
    equity = [r.equity / 1_000_000 for r in records]  # in millions

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(dates, equity, color=NUBANK_PURPLE, alpha=0.7, width=0.8)
    ax.set_title("Net Equity Evolution (Patrimonio Liquido)", fontsize=10, fontweight="bold")
    ax.set_ylabel("R$ (millions)", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}M"))
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(True, alpha=0.3, axis="y")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _create_benchmark_chart(performance: FundPerformance) -> bytes:
    """Create horizontal bar chart comparing fund vs benchmarks."""
    labels = ["Fund Return", "SELIC", "CDI", "IPCA"]
    values = [
        performance.return_pct,
        performance.benchmark_selic,
        performance.benchmark_cdi,
        performance.benchmark_ipca,
    ]
    bar_colors = [NUBANK_PURPLE, "#3498DB", "#2ECC71", "#E67E22"]

    fig, ax = plt.subplots(figsize=(7, 2.5))
    bars = ax.barh(labels, values, color=bar_colors, height=0.5)

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}%",
            va="center",
            fontsize=8,
        )

    ax.set_title("Performance vs Benchmarks (Period)", fontsize=10, fontweight="bold")
    ax.set_xlabel("%", fontsize=8)
    ax.tick_params(axis="both", labelsize=8)
    ax.grid(True, alpha=0.3, axis="x")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trend_arrow(trend: str) -> str:
    """Return unicode arrow for trend direction."""
    if trend == "up":
        return "^ UP"
    elif trend == "down":
        return "v DOWN"
    return "- FLAT"


def _format_brl(value: float) -> str:
    """Format a number as BRL currency."""
    return f"R$ {value:,.2f}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_pdf(
    performance: FundPerformance,
    news: list[NewsItem] | None = None,
    output_path: str | Path | None = None,
    metric_explanations: list[Any] | None = None,
) -> Path:
    """Generate a PDF report for the fund analysis.

    Args:
        performance: Computed fund performance metrics.
        news: Optional list of news items to include.
        output_path: Path for the output PDF. Defaults to ./reports/report_YYYYMMDD.pdf.
        metric_explanations: Optional list of ExplanationResult from MetricsExplainer.
            When provided, adds an educational 'Metrics Explained' section.

    Returns:
        Path to the generated PDF file.
    """
    if output_path is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        output_path = reports_dir / f"nu_reserva_report_{date.today().isoformat()}.pdf"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Generating PDF report at %s", output_path)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor(NUBANK_PURPLE),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor(DARK_GRAY),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor(NUBANK_PURPLE),
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor(DARK_GRAY),
        leading=13,
    )
    news_title_style = ParagraphStyle(
        "NewsTitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor(DARK_GRAY),
        fontName="Helvetica-Bold",
        leading=12,
    )
    news_meta_style = ParagraphStyle(
        "NewsMeta",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.gray,
        leading=10,
    )

    elements: list[Any] = []

    # -- Header --
    elements.append(Paragraph("Fund Analysis Report", title_style))
    elements.append(
        Paragraph(
            f"{performance.fund_name} | CNPJ: {performance.fund_cnpj}",
            subtitle_style,
        )
    )
    elements.append(
        Paragraph(
            f"Period: {performance.period_start.strftime('%d/%m/%Y')} to "
            f"{performance.period_end.strftime('%d/%m/%Y')} | "
            f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            subtitle_style,
        )
    )

    # -- Key Metrics Table --
    elements.append(Paragraph("Key Metrics", section_style))

    metrics_data = [
        ["Metric", "Value"],
        ["Current NAV (Cota)", f"R$ {performance.nav_end:.6f}"],
        ["Net Equity", _format_brl(performance.equity_end)],
        ["Shareholders", f"{performance.shareholders_current:,}"],
        ["Period Return", f"{performance.return_pct:.4f}%"],
        ["Annualized Volatility", f"{performance.volatility:.4f}%"],
        ["30-Day Trend", _trend_arrow(performance.trend_30d)],
    ]

    metrics_table = Table(metrics_data, colWidths=[8 * cm, 8 * cm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NUBANK_PURPLE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(LIGHT_GRAY)]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(metrics_table)

    # -- Benchmark Comparison Table --
    elements.append(Paragraph("Benchmark Comparison", section_style))

    def _color_diff(val: float) -> str:
        if val > 0:
            return f'<font color="{GREEN}">+{val:.4f}%</font>'
        elif val < 0:
            return f'<font color="{RED}">{val:.4f}%</font>'
        return f"{val:.4f}%"

    bench_data = [
        ["Benchmark", "Benchmark Return", "Fund Return", "Difference"],
        [
            "SELIC",
            f"{performance.benchmark_selic:.4f}%",
            f"{performance.return_pct:.4f}%",
            _color_diff(performance.vs_selic),
        ],
        [
            "CDI",
            f"{performance.benchmark_cdi:.4f}%",
            f"{performance.return_pct:.4f}%",
            _color_diff(performance.vs_cdi),
        ],
        [
            "IPCA",
            f"{performance.benchmark_ipca:.4f}%",
            f"{performance.return_pct:.4f}%",
            _color_diff(performance.vs_ipca),
        ],
    ]

    # Convert difference cells to Paragraphs for HTML rendering
    for i in range(1, len(bench_data)):
        bench_data[i][3] = Paragraph(bench_data[i][3], body_style)

    bench_table = Table(bench_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    bench_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NUBANK_PURPLE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(LIGHT_GRAY)]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(bench_table)

    # -- Charts --
    records = performance.daily_records
    if records:
        # NAV chart
        elements.append(Paragraph("NAV Evolution", section_style))
        nav_png = _create_nav_chart(records)
        nav_img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        nav_img_path.write(nav_png)
        nav_img_path.flush()
        elements.append(Image(nav_img_path.name, width=16 * cm, height=7 * cm))

        # Equity chart
        elements.append(Paragraph("Net Equity Evolution", section_style))
        equity_png = _create_equity_chart(records)
        equity_img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        equity_img_path.write(equity_png)
        equity_img_path.flush()
        elements.append(Image(equity_img_path.name, width=16 * cm, height=7 * cm))

        # Benchmark comparison chart
        elements.append(Paragraph("Performance vs Benchmarks", section_style))
        bench_png = _create_benchmark_chart(performance)
        bench_img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        bench_img_path.write(bench_png)
        bench_img_path.flush()
        elements.append(Image(bench_img_path.name, width=16 * cm, height=6 * cm))

    # -- Metrics Explained Section (Issue #64) --
    if metric_explanations:
        explained_elements = _build_explained_metrics_section(
            metric_explanations, styles
        )
        elements.extend(explained_elements)

    # -- News Section --
    if news:
        elements.append(Paragraph("Recent News", section_style))
        for item in news[:8]:
            elements.append(
                Paragraph(f"&bull; {item.title}", news_title_style)
            )
            elements.append(
                Paragraph(
                    f"  {item.source} | {item.pub_date.strftime('%d/%m/%Y %H:%M')}",
                    news_meta_style,
                )
            )
            elements.append(Spacer(1, 4))

    # -- Footer note --
    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.gray,
        alignment=1,  # center
    )
    elements.append(
        Paragraph(
            "Data sources: CVM (fund data), BCB (benchmarks), Google News (news). "
            "This report is for informational purposes only.",
            footer_style,
        )
    )

    doc.build(elements)
    logger.info("PDF generated successfully: %s", output_path)
    return output_path


def generate_pdf_bytes(
    performance: FundPerformance,
    news: list[NewsItem] | None = None,
    metric_explanations: list[Any] | None = None,
) -> bytes:
    """Generate a PDF report and return it as raw bytes.

    This is useful for the ReportGenerator Protocol which expects bytes
    output (e.g., for email attachments or HTTP responses).

    Args:
        performance: Computed fund performance metrics.
        news: Optional list of news items to include.
        metric_explanations: Optional list of ExplanationResult from MetricsExplainer.

    Returns:
        PDF file content as bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    elements = _build_elements(performance, news, metric_explanations)
    doc.build(elements)
    return buf.getvalue()


def _build_elements(
    performance: FundPerformance,
    news: list[NewsItem] | None = None,
    metric_explanations: list[Any] | None = None,
) -> list[Any]:
    """Build the list of ReportLab flowable elements for the PDF.

    Extracted from generate_pdf so it can be reused by both
    file-based and bytes-based generation.
    """
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor(NUBANK_PURPLE),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor(DARK_GRAY),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor(NUBANK_PURPLE),
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor(DARK_GRAY),
        leading=13,
    )
    news_title_style = ParagraphStyle(
        "NewsTitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor(DARK_GRAY),
        fontName="Helvetica-Bold",
        leading=12,
    )
    news_meta_style = ParagraphStyle(
        "NewsMeta",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.gray,
        leading=10,
    )

    elements: list[Any] = []

    # -- Header --
    elements.append(Paragraph("Fund Analysis Report", title_style))
    elements.append(
        Paragraph(
            f"{performance.fund_name} | CNPJ: {performance.fund_cnpj}",
            subtitle_style,
        )
    )
    elements.append(
        Paragraph(
            f"Period: {performance.period_start.strftime('%d/%m/%Y')} to "
            f"{performance.period_end.strftime('%d/%m/%Y')} | "
            f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            subtitle_style,
        )
    )

    # -- Key Metrics Table --
    elements.append(Paragraph("Key Metrics", section_style))

    metrics_data = [
        ["Metric", "Value"],
        ["Current NAV (Cota)", f"R$ {performance.nav_end:.6f}"],
        ["Net Equity", _format_brl(performance.equity_end)],
        ["Shareholders", f"{performance.shareholders_current:,}"],
        ["Period Return", f"{performance.return_pct:.4f}%"],
        ["Annualized Volatility", f"{performance.volatility:.4f}%"],
        ["30-Day Trend", _trend_arrow(performance.trend_30d)],
    ]

    metrics_table = Table(metrics_data, colWidths=[8 * cm, 8 * cm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NUBANK_PURPLE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor(LIGHT_GRAY)],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(metrics_table)

    # -- Benchmark Comparison Table --
    elements.append(Paragraph("Benchmark Comparison", section_style))

    def _color_diff(val: float) -> str:
        if val > 0:
            return f'<font color="{GREEN}">+{val:.4f}%</font>'
        elif val < 0:
            return f'<font color="{RED}">{val:.4f}%</font>'
        return f"{val:.4f}%"

    bench_data: list[list[Any]] = [
        ["Benchmark", "Benchmark Return", "Fund Return", "Difference"],
        [
            "SELIC",
            f"{performance.benchmark_selic:.4f}%",
            f"{performance.return_pct:.4f}%",
            _color_diff(performance.vs_selic),
        ],
        [
            "CDI",
            f"{performance.benchmark_cdi:.4f}%",
            f"{performance.return_pct:.4f}%",
            _color_diff(performance.vs_cdi),
        ],
        [
            "IPCA",
            f"{performance.benchmark_ipca:.4f}%",
            f"{performance.return_pct:.4f}%",
            _color_diff(performance.vs_ipca),
        ],
    ]

    for i in range(1, len(bench_data)):
        bench_data[i][3] = Paragraph(str(bench_data[i][3]), body_style)

    bench_table = Table(bench_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    bench_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NUBANK_PURPLE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor(LIGHT_GRAY)],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(bench_table)

    # -- Charts --
    records = performance.daily_records
    if records:
        elements.append(Paragraph("NAV Evolution", section_style))
        nav_png = _create_nav_chart(records)
        nav_img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        nav_img_path.write(nav_png)
        nav_img_path.flush()
        elements.append(Image(nav_img_path.name, width=16 * cm, height=7 * cm))

        elements.append(Paragraph("Net Equity Evolution", section_style))
        equity_png = _create_equity_chart(records)
        equity_img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        equity_img_path.write(equity_png)
        equity_img_path.flush()
        elements.append(
            Image(equity_img_path.name, width=16 * cm, height=7 * cm)
        )

        elements.append(Paragraph("Performance vs Benchmarks", section_style))
        bench_png = _create_benchmark_chart(performance)
        bench_img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        bench_img_path.write(bench_png)
        bench_img_path.flush()
        elements.append(
            Image(bench_img_path.name, width=16 * cm, height=6 * cm)
        )

    # -- Metrics Explained Section (Issue #64) --
    if metric_explanations:
        explained_elements = _build_explained_metrics_section(
            metric_explanations, styles
        )
        elements.extend(explained_elements)

    # -- News Section --
    if news:
        elements.append(Paragraph("Recent News", section_style))
        for item in news[:8]:
            elements.append(
                Paragraph(f"&bull; {item.title}", news_title_style)
            )
            elements.append(
                Paragraph(
                    f"  {item.source} | {item.pub_date.strftime('%d/%m/%Y %H:%M')}",
                    news_meta_style,
                )
            )
            elements.append(Spacer(1, 4))

    # -- Footer note --
    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.gray,
        alignment=1,
    )
    elements.append(
        Paragraph(
            "Data sources: CVM (fund data), BCB (benchmarks), Google News (news). "
            "This report is for informational purposes only.",
            footer_style,
        )
    )

    return elements


class AsyncPDFReportGenerator:
    """Async PDF report generator satisfying the ReportGenerator Protocol.

    Wraps the sync generate_pdf_bytes function for use in async contexts.
    Accepts the domain PerformanceReport from domain/models.py.
    """

    async def generate(
        self,
        performance: FundPerformance,
        news: list[NewsItem] | None = None,
        metric_explanations: list[Any] | None = None,
    ) -> bytes:
        """Generate a PDF report and return as bytes.

        Args:
            performance: Fund performance metrics.
            news: Optional news items.
            metric_explanations: Optional list of ExplanationResult.

        Returns:
            PDF content as bytes.
        """
        return generate_pdf_bytes(performance, news, metric_explanations)
