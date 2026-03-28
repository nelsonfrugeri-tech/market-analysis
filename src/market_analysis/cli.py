"""CLI entry point for the market analysis system.

Usage:
    python -m market_analysis.cli [--months N] [--output PATH] [--no-news] [--email ADDR] [--no-explain]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from market_analysis.infrastructure.cvm_collector import (
    NU_RESERVA_CNPJ,
    collect_multiple_months,
)
from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync
from market_analysis.infrastructure.news_fetcher import collect_news
from market_analysis.infrastructure.pdf_generator import generate_pdf
from market_analysis.application.performance import (
    compute_performance,
    extract_metrics_for_llm_explanation,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI execution."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _build_metrics_dict_for_explainer(
    performance: "FundPerformance",  # noqa: F821
) -> dict[str, float | None]:
    """Extract flat metric dict suitable for MetricsExplainer.explain_all.

    Maps metric names to their float values. These names must match
    the templates registered in TemplateRegistry.
    """
    return {
        "return_pct": performance.return_pct,
        "volatility": performance.volatility,
        "sharpe_ratio": performance.sharpe_ratio,
        "alpha": performance.alpha,
        "beta": performance.beta,
        "var_95": performance.var_95,
        "max_drawdown": performance.max_drawdown,
        "vs_cdi": performance.vs_cdi,
        "vs_selic": performance.vs_selic,
        "vs_ipca": performance.vs_ipca,
    }


def _run_explainer(
    performance: "FundPerformance",  # noqa: F821
    logger: logging.Logger,
) -> list | None:
    """Run MetricsExplainer (DeepSeek via Ollama as primary) and return results.

    Returns None if the explainer fails entirely (non-fatal).
    """
    try:
        from market_analysis.ai.explainer import MetricsExplainer
    except ImportError as exc:
        logger.warning("AI explainer not available: %s", exc)
        return None

    metrics = _build_metrics_dict_for_explainer(performance)
    days = (performance.period_end - performance.period_start).days
    period = f"ultimos {days} dias"

    benchmarks = {
        "cdi": performance.benchmark_cdi,
        "selic": performance.benchmark_selic,
        "ipca": performance.benchmark_ipca,
    }

    logger.info("Generating metric explanations via DeepSeek/Ollama...")
    try:
        explainer = MetricsExplainer()
        results, stats = explainer.explain_all_sync(
            metrics,
            period=period,
            benchmarks=benchmarks,
        )
        logger.info(
            "Explanations: %d total (%d LLM, %d cache, %d static)",
            stats.total,
            stats.from_llm,
            stats.from_cache,
            stats.from_static,
        )
        return results
    except Exception as exc:
        logger.warning("Metric explanation failed (non-fatal): %s", exc)
        return None


def _send_email(
    pdf_path: Path,
    recipients: list[str],
    fund_name: str,
    logger: logging.Logger,
) -> None:
    """Send the generated PDF report via email.

    Requires MA_SMTP_* environment variables to be configured.
    """
    from market_analysis.application.config import AppSettings
    from market_analysis.infrastructure.email_sender import (
        SmtpSettings,
        send_email_with_attachment,
    )

    settings = AppSettings()

    if not settings.smtp_host:
        logger.error(
            "SMTP not configured. Set MA_SMTP_HOST, MA_SMTP_SENDER_EMAIL, etc."
        )
        return

    smtp = SmtpSettings(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        sender_email=settings.smtp_sender_email,
    )

    pdf_bytes = pdf_path.read_bytes()
    today = date.today().isoformat()
    subject = f"Relatorio {fund_name} - {today}"
    body = (
        f"Segue em anexo o relatorio de analise do fundo {fund_name}.\n\n"
        f"Data de geracao: {today}\n"
        "Este relatorio e apenas informativo e nao constitui recomendacao de investimento."
    )

    try:
        send_email_with_attachment(
            settings=smtp,
            recipients=recipients,
            subject=subject,
            body=body,
            attachment_name=pdf_path.name,
            attachment_data=pdf_bytes,
        )
        logger.info("Email sent to: %s", ", ".join(recipients))
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        prog="market-analysis",
        description="Generate fund analysis report for Nu Reserva Planejada",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Number of months to analyze (default: 3)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output PDF path (default: reports/nu_reserva_report_YYYY-MM-DD.pdf)",
    )
    parser.add_argument(
        "--no-news",
        action="store_true",
        help="Skip news collection",
    )
    parser.add_argument(
        "--no-explain",
        action="store_true",
        help="Skip DeepSeek metric explanations",
    )
    parser.add_argument(
        "--email",
        type=str,
        nargs="+",
        default=None,
        help="Email address(es) to send the report to",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args(argv)
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Step 1: Collect CVM fund data
        logger.info(
            "Collecting CVM data for %d months (CNPJ: %s)...",
            args.months,
            NU_RESERVA_CNPJ,
        )
        records = collect_multiple_months(
            cnpj=NU_RESERVA_CNPJ,
            num_months=args.months,
        )

        if not records:
            logger.error("No fund data collected from CVM. Cannot generate report.")
            return 1

        logger.info(
            "Collected %d daily records (%s to %s)",
            len(records),
            records[0].date,
            records[-1].date,
        )

        # Step 2: Collect benchmark rates
        logger.info("Collecting benchmark rates from BCB...")
        benchmarks = collect_all_benchmarks_sync(
            start_date=records[0].date,
            end_date=records[-1].date,
        )
        logger.info(
            "Benchmarks: SELIC=%.4f%%, CDI=%.4f%%, IPCA=%.4f%%, CDB=%.4f%%, Poupanca=%.4f%%",
            benchmarks.selic_accumulated,
            benchmarks.cdi_accumulated,
            benchmarks.ipca_accumulated,
            benchmarks.cdb_estimated,
            benchmarks.poupanca_estimated,
        )

        # Step 3: Compute performance
        logger.info("Computing performance metrics...")
        performance = compute_performance(records, benchmarks)
        logger.info(
            "Fund return: %.4f%%, vs SELIC: %.4f%%, vs CDI: %.4f%%",
            performance.return_pct,
            performance.vs_selic,
            performance.vs_cdi,
        )

        # Step 4: Collect news (optional)
        news = None
        if not args.no_news:
            logger.info("Collecting news...")
            try:
                news = collect_news()
                logger.info("Collected %d news items", len(news))
            except Exception as exc:
                logger.warning("News collection failed (non-fatal): %s", exc)

        # Step 5: Generate metric explanations via DeepSeek/Ollama (optional)
        metric_explanations = None
        if not args.no_explain:
            metric_explanations = _run_explainer(performance, logger)

        # Step 6: Generate PDF
        logger.info("Generating PDF report...")
        pdf_path = generate_pdf(
            performance=performance,
            news=news,
            output_path=args.output,
            metric_explanations=metric_explanations,
        )
        logger.info("Report generated: %s", pdf_path.resolve())

        # Step 7: Send email (optional)
        if args.email:
            _send_email(pdf_path, args.email, performance.fund_name, logger)

        print(f"\nReport generated successfully: {pdf_path.resolve()}")
        return 0

    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
