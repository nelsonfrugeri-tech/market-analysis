#!/usr/bin/env python3
"""MVP Demo: Advanced Metrics + LLM Explanations."""

import os
from datetime import date, timedelta
from src.market_analysis.domain.models.fund import FundDailyRecord
from src.market_analysis.application.performance import compute_performance
from src.market_analysis.infrastructure.benchmarks import BenchmarkData
from src.market_analysis.ai.explainer import MetricsExplainer, ExplanationResult


def create_nu_reserva_sample():
    """Simulate Nu Reserva Planejada data."""
    records = []
    base_date = date(2024, 1, 1)
    base_nav = 1053.42  # Typical Nu Reserva NAV

    # Simulate 120 days (4 months) of realistic fund data
    for i in range(120):
        # CDI-like behavior with small variations
        daily_change = 0.0003 + (i % 5 - 2) * 0.0001  # ~0.02-0.04% daily
        base_nav *= (1 + daily_change)

        record = FundDailyRecord(
            cnpj="43.121.002/0001-41",
            date=base_date + timedelta(days=i),
            nav=round(base_nav, 4),
            equity=base_nav * 50000000,  # ~50M in equity
            total_value=base_nav * 50000000,
            deposits=5000 + (i % 10) * 1000,  # Variable daily deposits
            withdrawals=2000 + (i % 7) * 500,
            shareholders=15000 + i * 10  # Growing shareholder base
        )
        records.append(record)

    return records


def create_realistic_benchmarks():
    """Create realistic benchmark data for the period."""
    return BenchmarkData(
        date_range=(date(2024, 1, 1), date(2024, 4, 30)),
        selic_accumulated=4.2,   # ~4.2% over 4 months
        cdi_accumulated=4.3,     # Slightly above SELIC
        ipca_accumulated=1.8,    # Lower inflation
        selic_annual_rate=12.25,
        cdi_annual_rate=12.85,
        cdb_estimated=4.1,       # CDI minus spread
        poupanca_estimated=3.1   # Lower return
    )


def format_metrics_report(performance, results: list[ExplanationResult]):
    """Format a nice report showing metrics and explanations."""

    report = f"""
RELATORIO DE METRICAS - {performance.fund_name}
{'=' * 55}

PERFORMANCE BASICA
{'-' * 24}
* Periodo: {performance.period_start} a {performance.period_end}
* Retorno: {performance.return_pct:.2f}% (vs CDI: {performance.vs_cdi:+.2f}%)
* Volatilidade: {performance.volatility:.2f}%
* Tendencia 30d: {performance.trend_30d}

METRICAS AVANCADAS
{'-' * 24}
* Sharpe Ratio: {performance.sharpe_ratio:.3f}
* Alpha: {performance.alpha:.2f}%
* Beta: {performance.beta:.3f}
* VaR 95%: {performance.var_95:.2f}%

EXPLICACOES EDUCACIONAIS
{'-' * 28}
"""

    for r in results:
        report += f"\n[{r.category.upper()}] {r.display_name} (via {r.provider})\n"
        report += f"{r.text}\n"
        report += "-" * 60 + "\n"

    return report


def main():
    """Run the complete MVP demo."""
    print("🚀 MVP DEMO: Nu Reserva Planejada - Métricas Educacionais")
    print("=" * 60)

    # 1. Create sample data
    print("📊 Gerando dados de exemplo...")
    records = create_nu_reserva_sample()
    benchmarks = create_realistic_benchmarks()

    # 2. Calculate performance with new metrics
    print("🔢 Calculando métricas avançadas...")
    performance = compute_performance(records, benchmarks)

    # 3. Generate explanations (fallback chain: Claude -> Ollama -> static)
    print("Gerando explicacoes educacionais...")
    explainer = MetricsExplainer()
    metrics = {
        "sharpe_ratio": performance.sharpe_ratio,
        "alpha": performance.alpha,
        "beta": performance.beta,
        "var_95": performance.var_95,
    }
    results, stats = explainer.explain_all_sync(metrics, period="4 meses")
    print(f"  -> {stats.total} metricas: {stats.from_llm} LLM, {stats.from_static} static, {stats.from_cache} cache")

    # 4. Create formatted report
    report = format_metrics_report(performance, results)

    # 5. Display results
    print("\n" + "="*80)
    print(report)
    print("="*80)

    # 6. Save to file for integration demo
    output_file = "nu_reserva_metrics_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n💾 Relatório salvo em: {output_file}")
    print("\n✅ MVP COMPLETO! Pronto para integração no PDF generator.")

    # Show integration hints
    print("\n🔧 PRÓXIMOS PASSOS PARA INTEGRAÇÃO:")
    print("1. ✅ Métricas calculadas: Sharpe, Alpha, Beta, VaR")
    print("2. ✅ Explicações LLM: Claude API + fallback")
    print("3. 📄 Adicionar ao PDF: nova seção 'Métricas Explicadas'")
    print("4. 🎨 UX: boxes coloridos por categoria")
    print("5. 🧪 Testes: validação com dados reais")


if __name__ == "__main__":
    main()