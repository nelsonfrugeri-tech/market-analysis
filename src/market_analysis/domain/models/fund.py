"""Domain models for CVM fund daily data."""

from datetime import date, datetime
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FundDailyRecord:
    """A single daily record for a fund from CVM INF_DIARIO.

    Represents one row from the CVM CSV after filtering by CNPJ.
    """

    cnpj: str
    date: date
    nav: float  # VL_QUOTA (valor da cota)
    equity: float  # VL_PATRIM_LIQ (patrimonio liquido)
    total_value: float  # VL_TOTAL
    deposits: float  # CAPTC_DIA (captacao do dia)
    withdrawals: float  # RESG_DIA (resgates do dia)
    shareholders: int  # NR_COTST (numero de cotistas)

    @property
    def net_flow(self) -> float:
        """Net capital flow for the day."""
        return self.deposits - self.withdrawals


@dataclass(frozen=True, slots=True)
class FundPerformance:
    """Computed performance metrics for a fund over a period."""

    fund_cnpj: str
    fund_name: str
    period_start: date
    period_end: date
    nav_start: float
    nav_end: float
    return_pct: float  # percentage return over period
    equity_start: float
    equity_end: float
    volatility: float  # annualized std dev of daily returns
    shareholders_current: int
    benchmark_selic: float  # accumulated SELIC over same period
    benchmark_cdi: float  # accumulated CDI over same period
    benchmark_ipca: float  # accumulated IPCA over same period
    vs_selic: float  # return - selic (bps outperformance)
    vs_cdi: float
    vs_ipca: float
    trend_30d: str  # "up", "down", "flat"
    daily_records: list[FundDailyRecord] = field(default_factory=list)
