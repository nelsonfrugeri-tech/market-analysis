"""
FastAPI application for Market Analysis v0.2.0

Provides REST API endpoints for fund performance data, metrics, and collection.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware

from .service import calculate_fund_performance, get_fund_metadata, get_fund_daily_data
from ..domain.models.fund import FundPerformance
from ..infrastructure.cvm_collector import NU_RESERVA_CNPJ, collect_multiple_months
from ..infrastructure.benchmarks import collect_all_benchmarks_sync
from .models import (
    FundSummary,
    PerformanceResponse,
    DailyDataResponse,
    MetricExplanation,
    CollectionResponse,
    HealthResponse
)


app = FastAPI(
    title="Market Analysis API",
    description="Investment fund analysis and metrics API",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Get API health status and last collection info."""
    try:
        # Simple health check - try to collect 1 month of data
        test_records = await get_fund_daily_data(NU_RESERVA_CNPJ, months=1)

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            database_connected=True,
            last_collection=datetime.now()  # Simplified for now
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            database_connected=False,
            last_collection=None,
            error=str(e)
        )


@app.get("/api/v1/funds", response_model=List[FundSummary])
async def list_funds() -> List[FundSummary]:
    """List all available funds."""
    try:
        funds_data = await get_fund_metadata()
        return [FundSummary(**fund) for fund in funds_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving funds: {str(e)}")


@app.get("/api/v1/funds/{cnpj:path}/performance", response_model=PerformanceResponse)
async def get_fund_performance(
    cnpj: str = Path(..., description="Fund CNPJ"),
    months: Optional[int] = Query(default=3, ge=1, le=60, description="Number of months for analysis"),
    start_date: Optional[date] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="End date (YYYY-MM-DD)")
) -> PerformanceResponse:
    """Get comprehensive fund performance metrics and benchmarks."""
    try:
        # Calculate performance using service layer
        performance = await calculate_fund_performance(
            cnpj=cnpj,
            months=months,
            start_date=start_date,
            end_date=end_date
        )

        return _convert_to_api_response(performance)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance: {str(e)}")


@app.get("/api/v1/funds/{cnpj:path}/daily", response_model=List[DailyDataResponse])
async def get_fund_daily_data_endpoint(
    cnpj: str = Path(..., description="Fund CNPJ"),
    from_date: Optional[date] = Query(default=None, alias="from", description="Start date"),
    to_date: Optional[date] = Query(default=None, alias="to", description="End date"),
    limit: int = Query(default=90, ge=1, le=365, description="Maximum number of records")
) -> List[DailyDataResponse]:
    """Get daily time series data for charts."""
    try:
        # For now, use months approximation (can be enhanced later)
        months = min(limit // 30, 12) or 3
        daily_records = await get_fund_daily_data(cnpj, months=months)

        # Limit results if needed
        if limit and len(daily_records) > limit:
            daily_records = daily_records[-limit:]

        return [
            DailyDataResponse(
                date=record.date,
                nav=record.nav,
                equity=record.equity,
                deposits=record.deposits,
                withdrawals=record.withdrawals,
                shareholders=record.shareholders,
                net_flow=record.deposits - record.withdrawals
            )
            for record in daily_records
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving daily data: {str(e)}")


@app.get("/api/v1/funds/{cnpj:path}/explanations", response_model=List[MetricExplanation])
async def get_metric_explanations(cnpj: str = Path(..., description="Fund CNPJ")) -> List[MetricExplanation]:
    """Get explanations for all metrics (for tooltips)."""
    # Static explanations for now - can be enhanced with LLM later
    explanations = [
        MetricExplanation(
            key="return_pct",
            name="Return (%)",
            value=None,
            explanation="Period return percentage shows how much the fund gained or lost over the selected timeframe",
            category="performance"
        ),
        MetricExplanation(
            key="volatility",
            name="Volatility",
            value=None,
            explanation="Measures how much the fund's returns vary from day to day. Higher volatility means more risk",
            category="risk"
        ),
        MetricExplanation(
            key="sharpe_ratio",
            name="Sharpe Ratio",
            value=None,
            explanation="Risk-adjusted return measure. Higher values indicate better return per unit of risk taken",
            category="efficiency"
        ),
        MetricExplanation(
            key="alpha",
            name="Alpha",
            value=None,
            explanation="Excess return above what's expected given the fund's risk level. Positive alpha indicates outperformance",
            category="efficiency"
        ),
        MetricExplanation(
            key="beta",
            name="Beta",
            value=None,
            explanation="Sensitivity to market movements. Beta > 1 means more volatile than market, < 1 means less volatile",
            category="efficiency"
        ),
        MetricExplanation(
            key="max_drawdown",
            name="Max Drawdown",
            value=None,
            explanation="Largest peak-to-trough loss during the period. Shows worst-case scenario for the investment",
            category="risk"
        ),
        MetricExplanation(
            key="var_95",
            name="VaR 95%",
            value=None,
            explanation="Value at Risk - potential loss that won't be exceeded 95% of the time under normal conditions",
            category="risk"
        )
    ]

    return explanations


@app.post("/api/v1/collect", response_model=CollectionResponse)
async def trigger_data_collection() -> CollectionResponse:
    """Trigger data collection (CVM + BCB data)."""
    start_time = datetime.now()

    try:
        # For now, collect 6 months of data
        import asyncio
        loop = asyncio.get_event_loop()

        records = await loop.run_in_executor(
            None,
            collect_multiple_months,
            NU_RESERVA_CNPJ,
            6
        )

        benchmarks = await loop.run_in_executor(
            None,
            collect_all_benchmarks_sync,
            records[0].date if records else None,
            records[-1].date if records else None
        )

        total_items = len(records) + 3  # CVM records + 3 benchmark series

        duration = (datetime.now() - start_time).total_seconds()

        return CollectionResponse(
            status="success",
            items_collected=total_items,
            duration_secs=duration,
            timestamp=datetime.now()
        )

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()

        return CollectionResponse(
            status="error",
            items_collected=0,
            duration_secs=duration,
            timestamp=datetime.now(),
            error=str(e)
        )


def _convert_to_api_response(performance: FundPerformance) -> PerformanceResponse:
    """Convert domain FundPerformance to API response model."""
    return PerformanceResponse(
        fund=FundSummary(
            cnpj=performance.fund_cnpj,
            name=performance.fund_name,
            short_name=performance.fund_name,
            fund_type="Renda Fixa",
            manager="Nu Asset Management",
            benchmark="CDI",
            status="active"
        ),
        period={
            "start": performance.period_start.strftime("%Y-%m-%d"),
            "end": performance.period_end.strftime("%Y-%m-%d"),
            "days": (performance.period_end - performance.period_start).days
        },
        performance={
            "return_pct": round(performance.return_pct, 4),
            "nav_start": round(performance.nav_start, 6),
            "nav_end": round(performance.nav_end, 6)
        },
        risk={
            "volatility": round(performance.volatility, 4),
            "sharpe_ratio": round(performance.sharpe_ratio, 4),
            "max_drawdown": round(performance.max_drawdown, 4),
            "var_95": round(performance.var_95, 4)
        },
        efficiency={
            "alpha": round(performance.alpha, 4),
            "beta": round(performance.beta, 4)
        },
        benchmarks={
            "cdi": {
                "accumulated": round(performance.benchmark_cdi, 4),
                "vs_fund": round(performance.vs_cdi, 0)  # basis points
            },
            "selic": {
                "accumulated": round(performance.benchmark_selic, 4),
                "vs_fund": round(performance.vs_selic, 0)
            },
            "ipca": {
                "accumulated": round(performance.benchmark_ipca, 4),
                "vs_fund": round(performance.vs_ipca, 0)
            },
            "cdb": {"estimated": round(performance.benchmark_cdi * 0.95, 4)},
            "poupanca": {"estimated": round(performance.benchmark_selic * 0.70, 4)}
        },
        market={
            "trend_30d": performance.trend_30d,
            "shareholders": performance.shareholders_current,
            "equity_millions": round(performance.equity_end / 1_000_000, 2)
        },
        updated_at=datetime.now()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("market_analysis.api.main:app", host="0.0.0.0", port=8000, reload=True)