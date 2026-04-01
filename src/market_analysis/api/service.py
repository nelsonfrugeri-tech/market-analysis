"""
API service layer to integrate with existing application logic.

Provides high-level functions that coordinate data collection,
performance calculation, and response formatting for API endpoints.
"""

import asyncio
from datetime import date, timedelta
from typing import Optional

from ..application.performance import compute_performance
from ..domain.models.fund import FundPerformance
from ..infrastructure.cvm_collector import NU_RESERVA_CNPJ, collect_multiple_months
from ..infrastructure.benchmarks import collect_all_benchmarks_sync


async def calculate_fund_performance(
    cnpj: str,
    months: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> FundPerformance:
    """
    Calculate comprehensive fund performance metrics.

    This function uses the existing CLI logic to collect data and calculate performance.
    Runs sync functions in executor to maintain async interface.

    Args:
        cnpj: Fund CNPJ identifier (currently only supports Nu Reserva CNPJ)
        months: Number of months for analysis
        start_date: Custom start date (not fully implemented yet)
        end_date: Custom end date (not fully implemented yet)

    Returns:
        FundPerformance with complete metrics

    Raises:
        ValueError: If no data available or unsupported CNPJ
    """
    # For now, only support Nu Reserva CNPJ
    if cnpj != NU_RESERVA_CNPJ:
        raise ValueError(f"Only Nu Reserva CNPJ {NU_RESERVA_CNPJ} is currently supported")

    # Use months parameter, default to 3
    if not months:
        months = 3

    # Run sync collection functions in executor
    loop = asyncio.get_event_loop()

    # Collect fund data
    records = await loop.run_in_executor(
        None,
        collect_multiple_months,
        cnpj,
        months
    )

    if not records:
        raise ValueError(f"No fund data collected for CNPJ {cnpj} in the last {months} months")

    # Collect benchmark data for the same period
    benchmarks = await loop.run_in_executor(
        None,
        collect_all_benchmarks_sync,
        records[0].date,
        records[-1].date
    )

    # Calculate performance using existing application logic
    performance = compute_performance(
        records=records,
        benchmarks=benchmarks,
        fund_name="Nu Reserva Planejada"
    )

    return performance


async def get_fund_metadata():
    """Get list of available funds. Currently hardcoded to Nu Reserva."""
    return [{
        "cnpj": NU_RESERVA_CNPJ,
        "name": "Nu Reserva Planejada",
        "short_name": "Nu Reserva",
        "fund_type": "Renda Fixa",
        "manager": "Nu Asset Management",
        "benchmark": "CDI",
        "status": "active"
    }]


async def get_fund_daily_data(cnpj: str, months: int = 3):
    """Get daily data for charts. Currently uses CVM collector directly."""
    if cnpj != NU_RESERVA_CNPJ:
        raise ValueError(f"Only Nu Reserva CNPJ {NU_RESERVA_CNPJ} is currently supported")

    loop = asyncio.get_event_loop()
    records = await loop.run_in_executor(
        None,
        collect_multiple_months,
        cnpj,
        months
    )

    return records