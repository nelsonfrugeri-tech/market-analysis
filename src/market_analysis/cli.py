"""CLI entry point for the market analysis system.

Usage:
    python -m market_analysis.cli [--months N] [--output PATH] [--no-news]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from market_analysis.infrastructure.cvm_collector import (
    NU_RESERVA_CNPJ,
    collect_multiple_months,
)
from market_analysis.infrastructure.benchmarks import collect_all_benchmarks_sync
from market_analysis.infrastructure.news_fetcher import collect_news
from market_analysis.infrastructure.pdf_generator import generate_pdf
from market_analysis.application.performance import compute_performance


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for CLI execution."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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

        # Step 5: Generate PDF
        logger.info("Generating PDF report...")
        pdf_path = generate_pdf(
            performance=performance,
            news=news,
            output_path=args.output,
        )
        logger.info("Report generated: %s", pdf_path.resolve())

        print(f"\nReport generated successfully: {pdf_path.resolve()}")
        return 0

    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
