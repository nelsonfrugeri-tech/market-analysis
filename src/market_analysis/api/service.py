"""
API service layer to integrate with existing application logic.

Provides high-level functions that coordinate data collection,
performance calculation, and response formatting for API endpoints.
"""

import asyncio
from datetime import date

from ..application.performance import compute_performance
from ..domain.models.fund import FundDailyRecord, FundPerformance
from ..infrastructure.benchmarks import collect_all_benchmarks_sync
from ..infrastructure.cvm_collector import NU_RESERVA_CNPJ, collect_multiple_months


async def calculate_fund_performance(
    cnpj: str,
    months: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> FundPerformance:
    """Calculate comprehensive fund performance metrics.

    Runs sync collection functions via ``asyncio.to_thread`` to keep the
    async interface non-blocking.

    Args:
        cnpj: Fund CNPJ identifier (currently only supports Nu Reserva).
        months: Number of months for analysis.
        start_date: Custom start date (not fully implemented yet).
        end_date: Custom end date (not fully implemented yet).

    Returns:
        FundPerformance with complete metrics.

    Raises:
        ValueError: If no data available or unsupported CNPJ.
    """
    if cnpj != NU_RESERVA_CNPJ:
        raise ValueError(
            f"Only Nu Reserva CNPJ {NU_RESERVA_CNPJ} is currently supported"
        )

    if not months:
        months = 3

    records: list[FundDailyRecord] = await asyncio.to_thread(
        collect_multiple_months,
        cnpj,
        months,
    )

    if not records:
        raise ValueError(
            f"No fund data collected for CNPJ {cnpj} "
            f"in the last {months} months"
        )

    benchmarks = await asyncio.to_thread(
        collect_all_benchmarks_sync,
        records[0].date,
        records[-1].date,
    )

    performance = compute_performance(
        records=records,
        benchmarks=benchmarks,
        fund_name="Nu Reserva Planejada",
    )

    return performance


async def get_fund_metadata() -> list[dict[str, str]]:
    """Get list of available funds. Currently hardcoded to Nu Reserva."""
    return [
        {
            "cnpj": NU_RESERVA_CNPJ,
            "name": "Nu Reserva Planejada",
            "short_name": "Nu Reserva",
            "fund_type": "Renda Fixa",
            "manager": "Nu Asset Management",
            "benchmark": "CDI",
            "status": "active",
        }
    ]


async def get_fund_daily_data(
    cnpj: str, months: int = 3
) -> list[FundDailyRecord]:
    """Get daily data for charts. Uses CVM collector directly."""
    if cnpj != NU_RESERVA_CNPJ:
        raise ValueError(
            f"Only Nu Reserva CNPJ {NU_RESERVA_CNPJ} is currently supported"
        )

    records: list[FundDailyRecord] = await asyncio.to_thread(
        collect_multiple_months,
        cnpj,
        months,
    )

    return records
