"""
FastAPI application for Market Analysis v0.2.0

Provides REST API endpoints for fund performance data, metrics, and collection.
"""

import asyncio
import sqlite3
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi import Path as FastAPIPath
from fastapi.middleware.cors import CORSMiddleware

from ..domain.models.fund import FundPerformance
from ..infrastructure.benchmarks import collect_all_benchmarks_sync
from ..infrastructure.cvm_collector import NU_RESERVA_CNPJ, collect_multiple_months
from .models import (
    BenchmarkComparison,
    BenchmarkDetail,
    BenchmarkEstimate,
    CollectionResponse,
    DailyDataResponse,
    EfficiencyMetrics,
    FundSummary,
    HealthResponse,
    MarketContext,
    MetricExplanation,
    PerformanceMetrics,
    PerformanceResponse,
    PeriodInfo,
    RiskMetrics,
)
from .service import (
    calculate_fund_performance,
    get_fund_daily_data,
    get_fund_metadata,
)

app = FastAPI(
    title="Market Analysis API",
    description="Investment fund analysis and metrics API",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database path for lightweight health check
_DB_PATH = Path("data/market_analysis.db")


# ---------------------------------------------------------------------------
# Metric explanations -- covers all metrics from AdvancedMetrics + basics
# ---------------------------------------------------------------------------
METRIC_EXPLANATIONS: list[MetricExplanation] = [
    # Performance
    MetricExplanation(
        key="return_pct",
        name="Return (%)",
        value=None,
        explanation=(
            "Period return percentage shows how much the fund gained or "
            "lost over the selected timeframe"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="cumulative_return",
        name="Cumulative Return",
        value=None,
        explanation=(
            "Total accumulated return since the beginning of the analysis "
            "period, compounding daily returns"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="ytd_return",
        name="YTD Return",
        value=None,
        explanation=(
            "Year-to-date return measures fund performance from January 1st "
            "of the current year to the latest available date"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="twelve_month_return",
        name="12-Month Return",
        value=None,
        explanation=(
            "Rolling 12-month return shows the fund's performance over the "
            "last full year, useful for annualized comparisons"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="six_month_return",
        name="6-Month Return",
        value=None,
        explanation=(
            "Rolling 6-month return captures medium-term fund performance "
            "trends"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="three_month_return",
        name="3-Month Return",
        value=None,
        explanation=(
            "Rolling 3-month return reflects recent short-term performance "
            "of the fund"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="monthly_avg_return",
        name="Monthly Average Return",
        value=None,
        explanation=(
            "Average monthly return across all months in the analysis "
            "period, giving a sense of typical monthly gains"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="nav_start",
        name="NAV (Start)",
        value=None,
        explanation=(
            "Net Asset Value at the beginning of the analysis period. "
            "NAV represents the per-share value of the fund"
        ),
        category="performance",
    ),
    MetricExplanation(
        key="nav_end",
        name="NAV (End)",
        value=None,
        explanation=(
            "Net Asset Value at the end of the analysis period. Comparing "
            "start and end NAV shows the absolute price change"
        ),
        category="performance",
    ),
    # Risk
    MetricExplanation(
        key="volatility",
        name="Volatility",
        value=None,
        explanation=(
            "Annualized standard deviation of daily returns. Measures how "
            "much the fund's returns vary day to day. Higher volatility "
            "means more risk"
        ),
        category="risk",
    ),
    MetricExplanation(
        key="sharpe_ratio",
        name="Sharpe Ratio",
        value=None,
        explanation=(
            "Risk-adjusted return measure (return minus risk-free rate, "
            "divided by volatility). Higher values indicate better return "
            "per unit of risk taken"
        ),
        category="risk",
    ),
    MetricExplanation(
        key="sortino_ratio",
        name="Sortino Ratio",
        value=None,
        explanation=(
            "Similar to Sharpe but only penalizes downside volatility. "
            "Better for funds with asymmetric return distributions, as "
            "it ignores upside volatility"
        ),
        category="risk",
    ),
    MetricExplanation(
        key="max_drawdown",
        name="Max Drawdown",
        value=None,
        explanation=(
            "Largest peak-to-trough loss during the period. Shows the "
            "worst-case scenario an investor would have experienced"
        ),
        category="risk",
    ),
    MetricExplanation(
        key="var_95",
        name="VaR 95%",
        value=None,
        explanation=(
            "Value at Risk at 95% confidence. The potential daily loss "
            "that won't be exceeded 95% of the time under normal market "
            "conditions"
        ),
        category="risk",
    ),
    # Efficiency
    MetricExplanation(
        key="alpha",
        name="Alpha",
        value=None,
        explanation=(
            "Excess return above what's expected given the fund's risk "
            "level (CAPM). Positive alpha indicates outperformance "
            "relative to the benchmark"
        ),
        category="efficiency",
    ),
    MetricExplanation(
        key="beta",
        name="Beta",
        value=None,
        explanation=(
            "Sensitivity to market (CDI) movements. Beta > 1 means more "
            "volatile than the market, < 1 means less volatile"
        ),
        category="efficiency",
    ),
    MetricExplanation(
        key="tracking_error",
        name="Tracking Error",
        value=None,
        explanation=(
            "Standard deviation of the difference between fund and "
            "benchmark returns. Lower tracking error means the fund "
            "more closely follows its benchmark"
        ),
        category="efficiency",
    ),
    MetricExplanation(
        key="information_ratio",
        name="Information Ratio",
        value=None,
        explanation=(
            "Alpha divided by tracking error. Measures the consistency "
            "of excess returns relative to the benchmark. Higher is better"
        ),
        category="efficiency",
    ),
    MetricExplanation(
        key="correlation",
        name="Correlation",
        value=None,
        explanation=(
            "Statistical correlation between fund and benchmark daily "
            "returns. Values near 1 mean the fund moves closely with "
            "the benchmark; near 0 means independent"
        ),
        category="efficiency",
    ),
    # Consistency
    MetricExplanation(
        key="positive_months_pct",
        name="Positive Months (%)",
        value=None,
        explanation=(
            "Percentage of months with positive returns. Higher values "
            "indicate more consistent gains over time"
        ),
        category="consistency",
    ),
    MetricExplanation(
        key="best_month",
        name="Best Month",
        value=None,
        explanation=(
            "Highest monthly return in the analysis period. Shows the "
            "upside potential of the fund"
        ),
        category="consistency",
    ),
    MetricExplanation(
        key="worst_month",
        name="Worst Month",
        value=None,
        explanation=(
            "Lowest monthly return in the analysis period. Shows the "
            "downside risk in a single month"
        ),
        category="consistency",
    ),
    MetricExplanation(
        key="win_loss_vs_cdi",
        name="Win/Loss vs CDI",
        value=None,
        explanation=(
            "Ratio of months where the fund beat CDI versus months "
            "where it underperformed. Above 1.0 means the fund beats "
            "CDI more often than not"
        ),
        category="consistency",
    ),
    MetricExplanation(
        key="stability_index",
        name="Stability Index",
        value=None,
        explanation=(
            "Composite score measuring return consistency. Higher values "
            "indicate more stable and predictable fund performance"
        ),
        category="consistency",
    ),
    # Benchmark comparisons
    MetricExplanation(
        key="vs_cdi",
        name="vs CDI",
        value=None,
        explanation=(
            "Excess return over CDI in basis points. Positive means "
            "the fund outperformed the CDI interbank rate"
        ),
        category="comparison",
    ),
    MetricExplanation(
        key="vs_selic",
        name="vs SELIC",
        value=None,
        explanation=(
            "Excess return over SELIC in basis points. SELIC is the "
            "Brazilian central bank base rate"
        ),
        category="comparison",
    ),
    MetricExplanation(
        key="vs_ipca",
        name="vs IPCA",
        value=None,
        explanation=(
            "Excess return over IPCA (inflation) in basis points. "
            "Positive means the fund beat inflation"
        ),
        category="comparison",
    ),
    MetricExplanation(
        key="vs_cdb",
        name="vs CDB",
        value=None,
        explanation=(
            "Excess return over estimated CDB rate. CDB is a common "
            "fixed-income investment in Brazil (typically ~95% of CDI)"
        ),
        category="comparison",
    ),
    MetricExplanation(
        key="vs_poupanca",
        name="vs Poupanca",
        value=None,
        explanation=(
            "Excess return over estimated savings account (Poupanca) "
            "rate. Poupanca yields ~70% of SELIC when SELIC > 8.5%"
        ),
        category="comparison",
    ),
]


@app.get("/api/v1/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Lightweight health check -- only verifies SQLite connectivity."""
    try:
        db_exists = _DB_PATH.exists()
        if db_exists:
            # Quick SQLite ping -- no data collection
            conn = sqlite3.connect(str(_DB_PATH), timeout=2)
            conn.execute("SELECT 1")
            conn.close()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            database_connected=db_exists,
            last_collection=None,
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            database_connected=False,
            last_collection=None,
            error=str(e),
        )


@app.get("/api/v1/funds", response_model=list[FundSummary])
async def list_funds() -> list[FundSummary]:
    """List all available funds."""
    try:
        funds_data = await get_fund_metadata()
        return [FundSummary(**fund) for fund in funds_data]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving funds: {e}"
        ) from e


@app.get(
    "/api/v1/funds/{cnpj:path}/performance",
    response_model=PerformanceResponse,
)
async def get_fund_performance(
    cnpj: str = FastAPIPath(..., description="Fund CNPJ"),
    months: int | None = Query(
        default=3, ge=1, le=60, description="Number of months for analysis"
    ),
    start_date: date | None = Query(
        default=None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: date | None = Query(
        default=None, description="End date (YYYY-MM-DD)"
    ),
) -> PerformanceResponse:
    """Get comprehensive fund performance metrics and benchmarks."""
    try:
        performance = await calculate_fund_performance(
            cnpj=cnpj,
            months=months,
            start_date=start_date,
            end_date=end_date,
        )
        return _convert_to_api_response(performance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating performance: {e}",
        ) from e


@app.get(
    "/api/v1/funds/{cnpj:path}/daily",
    response_model=list[DailyDataResponse],
)
async def get_fund_daily_data_endpoint(
    cnpj: str = FastAPIPath(..., description="Fund CNPJ"),
    from_date: date | None = Query(
        default=None, alias="from", description="Start date"
    ),
    to_date: date | None = Query(
        default=None, alias="to", description="End date"
    ),
    limit: int = Query(
        default=90, ge=1, le=365, description="Maximum number of records"
    ),
) -> list[DailyDataResponse]:
    """Get daily time series data for charts."""
    try:
        months = min(limit // 30, 12) or 3
        daily_records = await get_fund_daily_data(cnpj, months=months)

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
                net_flow=record.deposits - record.withdrawals,
            )
            for record in daily_records
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving daily data: {e}",
        ) from e


@app.get(
    "/api/v1/funds/{cnpj:path}/explanations",
    response_model=list[MetricExplanation],
)
async def get_metric_explanations(
    cnpj: str = FastAPIPath(..., description="Fund CNPJ"),
) -> list[MetricExplanation]:
    """Get explanations for all metrics (for tooltips)."""
    return METRIC_EXPLANATIONS


@app.post("/api/v1/collect", response_model=CollectionResponse)
async def trigger_data_collection() -> CollectionResponse:
    """Trigger data collection (CVM + BCB data)."""
    start_time = datetime.now()

    try:
        records = await asyncio.to_thread(
            collect_multiple_months,
            NU_RESERVA_CNPJ,
            6,
        )

        await asyncio.to_thread(
            collect_all_benchmarks_sync,
            records[0].date if records else None,
            records[-1].date if records else None,
        )

        total_items = len(records) + 3  # CVM records + 3 benchmark series
        duration = (datetime.now() - start_time).total_seconds()

        return CollectionResponse(
            status="success",
            items_collected=total_items,
            duration_secs=duration,
            timestamp=datetime.now(),
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        return CollectionResponse(
            status="error",
            items_collected=0,
            duration_secs=duration,
            timestamp=datetime.now(),
            error=str(e),
        )


def _convert_to_api_response(
    performance: FundPerformance,
) -> PerformanceResponse:
    """Convert domain FundPerformance to API response model."""
    return PerformanceResponse(
        fund=FundSummary(
            cnpj=performance.fund_cnpj,
            name=performance.fund_name,
            short_name=performance.fund_name,
            fund_type="Renda Fixa",
            manager="Nu Asset Management",
            benchmark="CDI",
            status="active",
        ),
        period=PeriodInfo(
            start=performance.period_start,
            end=performance.period_end,
            days=(performance.period_end - performance.period_start).days,
        ),
        performance=PerformanceMetrics(
            return_pct=round(performance.return_pct, 4),
            nav_start=round(performance.nav_start, 6),
            nav_end=round(performance.nav_end, 6),
        ),
        risk=RiskMetrics(
            volatility=round(performance.volatility, 4),
            sharpe_ratio=round(performance.sharpe_ratio, 4),
            max_drawdown=round(performance.max_drawdown, 4),
            var_95=round(performance.var_95, 4),
        ),
        efficiency=EfficiencyMetrics(
            alpha=round(performance.alpha, 4),
            beta=round(performance.beta, 4),
        ),
        benchmarks=BenchmarkComparison(
            cdi=BenchmarkDetail(
                accumulated=round(performance.benchmark_cdi, 4),
                vs_fund=round(performance.vs_cdi, 0),
            ),
            selic=BenchmarkDetail(
                accumulated=round(performance.benchmark_selic, 4),
                vs_fund=round(performance.vs_selic, 0),
            ),
            ipca=BenchmarkDetail(
                accumulated=round(performance.benchmark_ipca, 4),
                vs_fund=round(performance.vs_ipca, 0),
            ),
            cdb=BenchmarkEstimate(
                estimated=round(performance.benchmark_cdi * 0.95, 4),
            ),
            poupanca=BenchmarkEstimate(
                estimated=round(performance.benchmark_selic * 0.70, 4),
            ),
        ),
        market=MarketContext(
            trend_30d=performance.trend_30d,
            shareholders=performance.shareholders_current,
            equity_millions=round(performance.equity_end / 1_000_000, 2),
        ),
        updated_at=datetime.now(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "market_analysis.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
