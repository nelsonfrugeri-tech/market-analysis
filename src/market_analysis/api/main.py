"""
FastAPI application for Market Analysis v0.2.0

Provides REST API endpoints for fund performance data, metrics, and collection.
"""

import asyncio
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    BenchmarkComparison,
    BenchmarkDetail,
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
from .service import calculate_fund_performance, get_fund_daily_data, get_fund_metadata
from ..domain.models.fund import FundPerformance
from ..infrastructure.benchmarks import collect_all_benchmarks_sync
from ..infrastructure.cvm_collector import NU_RESERVA_CNPJ, collect_multiple_months


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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Get API health status. Lightweight check — no external calls."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        database_connected=True,
        last_collection=None,
    )


@app.get("/api/v1/funds", response_model=list[FundSummary])
async def list_funds() -> list[FundSummary]:
    """List all available funds."""
    try:
        funds_data = await get_fund_metadata()
        return [FundSummary(**fund) for fund in funds_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving funds: {e}")


@app.get("/api/v1/funds/{cnpj:path}/performance", response_model=PerformanceResponse)
async def get_fund_performance(
    cnpj: str = Path(..., description="Fund CNPJ"),
    months: Optional[int] = Query(
        default=3, ge=1, le=60, description="Number of months for analysis"
    ),
    start_date: Optional[date] = Query(
        default=None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating performance: {e}"
        )


@app.get(
    "/api/v1/funds/{cnpj:path}/daily", response_model=list[DailyDataResponse]
)
async def get_fund_daily_data_endpoint(
    cnpj: str = Path(..., description="Fund CNPJ"),
    from_date: Optional[date] = Query(
        default=None, alias="from", description="Start date"
    ),
    to_date: Optional[date] = Query(
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
            status_code=500, detail=f"Error retrieving daily data: {e}"
        )


@app.get(
    "/api/v1/funds/{cnpj:path}/explanations",
    response_model=list[MetricExplanation],
)
async def get_metric_explanations(
    cnpj: str = Path(..., description="Fund CNPJ"),
) -> list[MetricExplanation]:
    """Get explanations for all metrics (for tooltips)."""
    return _build_metric_explanations()


@app.post("/api/v1/collect", response_model=CollectionResponse)
async def trigger_data_collection() -> CollectionResponse:
    """Trigger data collection (CVM + BCB data)."""
    start_time = datetime.now()

    try:
        records = await asyncio.to_thread(
            collect_multiple_months, NU_RESERVA_CNPJ, 6
        )

        benchmarks = await asyncio.to_thread(
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


def _convert_to_api_response(performance: FundPerformance) -> PerformanceResponse:
    """Convert domain FundPerformance to API response model with full type safety."""
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
            cdb=BenchmarkDetail(
                estimated=round(performance.benchmark_cdi * 0.95, 4),
            ),
            poupanca=BenchmarkDetail(
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


def _build_metric_explanations() -> list[MetricExplanation]:
    """Build comprehensive metric explanations covering all dashboard metrics."""
    return [
        # Performance metrics
        MetricExplanation(
            key="return_pct",
            name="Retorno (%)",
            value=None,
            explanation="Retorno percentual do fundo no período selecionado. Mostra quanto o investimento valorizou ou desvalorizou.",
            category="performance",
        ),
        MetricExplanation(
            key="nav_start",
            name="Cota Inicial",
            value=None,
            explanation="Valor da cota no início do período de análise.",
            category="performance",
        ),
        MetricExplanation(
            key="nav_end",
            name="Cota Final",
            value=None,
            explanation="Valor da cota no final do período de análise.",
            category="performance",
        ),
        MetricExplanation(
            key="nav_variation",
            name="Variação da Cota",
            value=None,
            explanation="Diferença entre cota final e inicial, indica valorização absoluta.",
            category="performance",
        ),
        # Risk metrics
        MetricExplanation(
            key="volatility",
            name="Volatilidade",
            value=None,
            explanation="Mede quanto os retornos do fundo variam dia a dia. Maior volatilidade significa mais risco e incerteza.",
            category="risk",
        ),
        MetricExplanation(
            key="sharpe_ratio",
            name="Índice de Sharpe",
            value=None,
            explanation="Retorno ajustado ao risco. Valores maiores indicam melhor retorno por unidade de risco. Acima de 1.0 é considerado bom.",
            category="risk",
        ),
        MetricExplanation(
            key="max_drawdown",
            name="Máximo Drawdown",
            value=None,
            explanation="Maior queda do pico ao vale durante o período. Mostra o pior cenário que o investimento enfrentou.",
            category="risk",
        ),
        MetricExplanation(
            key="var_95",
            name="VaR 95%",
            value=None,
            explanation="Value at Risk — perda potencial que não será excedida em 95% das condições normais de mercado.",
            category="risk",
        ),
        # Efficiency metrics
        MetricExplanation(
            key="alpha",
            name="Alpha",
            value=None,
            explanation="Retorno excedente acima do esperado dado o nível de risco. Alpha positivo indica que o gestor está superando o benchmark.",
            category="efficiency",
        ),
        MetricExplanation(
            key="beta",
            name="Beta",
            value=None,
            explanation="Sensibilidade aos movimentos do mercado. Beta > 1 = mais volátil que o mercado; < 1 = menos volátil.",
            category="efficiency",
        ),
        # Benchmark comparisons
        MetricExplanation(
            key="benchmark_cdi",
            name="CDI Acumulado",
            value=None,
            explanation="Certificado de Depósito Interbancário — principal benchmark para renda fixa no Brasil. Taxa básica de referência entre bancos.",
            category="benchmark",
        ),
        MetricExplanation(
            key="benchmark_selic",
            name="SELIC Acumulada",
            value=None,
            explanation="Taxa básica de juros da economia brasileira, definida pelo Banco Central a cada 45 dias.",
            category="benchmark",
        ),
        MetricExplanation(
            key="benchmark_ipca",
            name="IPCA Acumulado",
            value=None,
            explanation="Índice de Preços ao Consumidor Amplo — inflação oficial do Brasil. Comparar com IPCA mostra se o fundo preserva poder de compra.",
            category="benchmark",
        ),
        MetricExplanation(
            key="vs_cdi",
            name="vs CDI (bps)",
            value=None,
            explanation="Diferença em pontos-base entre o retorno do fundo e o CDI. Positivo = superou o CDI.",
            category="benchmark",
        ),
        MetricExplanation(
            key="vs_selic",
            name="vs SELIC (bps)",
            value=None,
            explanation="Diferença em pontos-base entre o retorno do fundo e a SELIC. Positivo = superou a SELIC.",
            category="benchmark",
        ),
        MetricExplanation(
            key="vs_ipca",
            name="vs IPCA (bps)",
            value=None,
            explanation="Diferença em pontos-base entre o retorno do fundo e o IPCA. Positivo = retorno real positivo acima da inflação.",
            category="benchmark",
        ),
        MetricExplanation(
            key="cdb_estimated",
            name="CDB Estimado",
            value=None,
            explanation="Retorno estimado de um CDB a 95% do CDI no mesmo período. Serve como referência para investimentos bancários.",
            category="benchmark",
        ),
        MetricExplanation(
            key="poupanca_estimated",
            name="Poupança Estimada",
            value=None,
            explanation="Retorno estimado da poupança (70% da SELIC quando SELIC > 8.5%). Serve como comparação com o investimento mais básico.",
            category="benchmark",
        ),
        # Market context
        MetricExplanation(
            key="trend_30d",
            name="Tendência 30 dias",
            value=None,
            explanation="Direção da tendência do fundo nos últimos 30 dias: alta, estável ou queda.",
            category="market",
        ),
        MetricExplanation(
            key="shareholders",
            name="Cotistas",
            value=None,
            explanation="Número atual de investidores no fundo. Muitos cotistas indicam confiança coletiva no produto.",
            category="market",
        ),
        MetricExplanation(
            key="equity_millions",
            name="Patrimônio (R$ MM)",
            value=None,
            explanation="Patrimônio líquido total do fundo em milhões de reais. Fundos maiores tendem a ter mais liquidez e estabilidade.",
            category="market",
        ),
        # Flow metrics
        MetricExplanation(
            key="deposits",
            name="Captação",
            value=None,
            explanation="Total de aplicações (entradas) no fundo no período. Alta captação indica interesse crescente dos investidores.",
            category="flow",
        ),
        MetricExplanation(
            key="withdrawals",
            name="Resgates",
            value=None,
            explanation="Total de resgates (saídas) do fundo no período. Resgates altos podem indicar desconfiança ou necessidade de liquidez.",
            category="flow",
        ),
        MetricExplanation(
            key="net_flow",
            name="Fluxo Líquido",
            value=None,
            explanation="Diferença entre captação e resgates. Positivo = mais dinheiro entrando; negativo = mais saindo.",
            category="flow",
        ),
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "market_analysis.api.main:app", host="0.0.0.0", port=8000, reload=True
    )
