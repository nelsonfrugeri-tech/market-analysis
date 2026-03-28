"""Build template context from metric values and benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class MetricContext:
    """All variables needed to fill a PromptTemplate.user_template."""

    value: float
    fund_name: str
    period: str
    benchmark: str  # e.g. "CDI"
    bench_value: float
    investment: str  # e.g. "10.000"
    result: str  # e.g. "10.345"


def build_context(
    metric_name: str,
    value: float,
    *,
    fund_name: str = "Nu Reserva Planejada",
    period: str = "",
    benchmark_name: str = "CDI",
    benchmark_value: float = 0.0,
    investment_amount: float = 10_000.0,
) -> MetricContext:
    """Create a MetricContext for a given metric.

    Automatically computes the R$ result for investment examples.
    """
    # Compute result based on metric type
    if _is_return_metric(metric_name):
        result_value = investment_amount * (1 + value / 100)
    elif metric_name == "max_drawdown":
        result_value = investment_amount * (1 + value / 100)
    elif metric_name == "var_95":
        result_value = investment_amount * abs(value) / 100
    elif metric_name in ("best_month", "worst_month"):
        result_value = investment_amount * (value / 100)
    else:
        result_value = 0.0

    return MetricContext(
        value=value,
        fund_name=fund_name,
        period=period,
        benchmark=benchmark_name,
        bench_value=benchmark_value,
        investment=_fmt_brl(investment_amount),
        result=_fmt_brl(result_value),
    )


def fill_template(template_str: str, ctx: MetricContext) -> str:
    """Substitute placeholders in a user_template string."""
    return template_str.format(
        value=_fmt_num(ctx.value),
        fund_name=ctx.fund_name,
        period=ctx.period,
        benchmark=ctx.benchmark,
        bench_value=_fmt_num(ctx.bench_value),
        investment=ctx.investment,
        result=ctx.result,
    )


def _is_return_metric(name: str) -> bool:
    return name in {
        "cumulative_return",
        "ytd_return",
        "twelve_month_return",
        "six_month_return",
        "three_month_return",
        "monthly_avg_return",
    }


def _fmt_brl(v: float) -> str:
    """Format as Brazilian currency string without R$ prefix."""
    if abs(v) < 0.005:
        return "0,00"
    integer = int(v)
    decimal = int(round(abs(v - integer) * 100))
    int_str = f"{integer:,}".replace(",", ".")
    return f"{int_str},{decimal:02d}"


def _fmt_num(v: float) -> str:
    """Format a number for display (Brazilian decimal comma)."""
    return f"{v:.2f}".replace(".", ",")
