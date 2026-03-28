#!/usr/bin/env python3
"""Demo das novas métricas implementadas.

Script de demonstração mostrando as métricas expandidas funcionando
e a estrutura preparada para integração LLM futura.
"""

from datetime import date
from src.market_analysis.domain.models.fund import FundDailyRecord
from src.market_analysis.infrastructure.benchmarks.data_models import BenchmarkData
from src.market_analysis.application.performance import compute_performance, extract_metrics_for_llm_explanation


def create_sample_data():
    """Create sample fund data for demonstration."""
    records = [
        FundDailyRecord(
            cnpj="43.121.002/0001-41",
            date=date(2024, 1, 1),
            nav=1.000000,
            equity=50_000_000.0,
            total_value=50_000_000.0,
            deposits=0.0,
            withdrawals=0.0,
            shareholders=1000,
        ),
        FundDailyRecord(
            cnpj="43.121.002/0001-41",
            date=date(2024, 1, 15),
            nav=1.015000,
            equity=50_750_000.0,
            total_value=50_750_000.0,
            deposits=0.0,
            withdrawals=0.0,
            shareholders=1000,
        ),
        FundDailyRecord(
            cnpj="43.121.002/0001-41",
            date=date(2024, 2, 1),
            nav=1.008000,
            equity=50_400_000.0,
            total_value=50_400_000.0,
            deposits=0.0,
            withdrawals=0.0,
            shareholders=1000,
        ),
        FundDailyRecord(
            cnpj="43.121.002/0001-41",
            date=date(2024, 2, 15),
            nav=1.025000,
            equity=51_250_000.0,
            total_value=51_250_000.0,
            deposits=0.0,
            withdrawals=0.0,
            shareholders=1000,
        ),
        FundDailyRecord(
            cnpj="43.121.002/0001-41",
            date=date(2024, 3, 1),
            nav=1.030000,
            equity=51_500_000.0,
            total_value=51_500_000.0,
            deposits=0.0,
            withdrawals=0.0,
            shareholders=1000,
        ),
    ]

    benchmarks = BenchmarkData(
        date_range=(date(2024, 1, 1), date(2024, 3, 1)),
        selic_accumulated=2.5,
        cdi_accumulated=2.3,
        ipca_accumulated=1.1,
    )

    return records, benchmarks


def main():
    print("🚀 Demonstração das Novas Métricas Implementadas\n")

    # Create sample data
    records, benchmarks = create_sample_data()

    # Compute full performance
    performance = compute_performance(records, benchmarks)

    print(f"📊 Análise de Performance: {performance.fund_name}")
    print(f"Período: {performance.period_start} a {performance.period_end}")
    print(f"Retorno: {performance.return_pct:.4f}%\n")

    print("📈 Métricas Básicas:")
    print(f"  • Volatilidade: {performance.volatility:.4f}%")
    print(f"  • Trend 30d: {performance.trend_30d}")

    print("\n🎯 Métricas Avançadas (NOVAS!):")
    print(f"  • Sharpe Ratio: {performance.sharpe_ratio:.4f}")
    print(f"  • Alpha: {performance.alpha:.4f}%")
    print(f"  • Beta: {performance.beta:.4f}")
    print(f"  • Max Drawdown: {performance.max_drawdown:.4f}%")
    print(f"  • VaR 95%: {performance.var_95:.4f}%")

    print("\n🏛️ Comparação vs Benchmarks:")
    print(f"  • vs CDI: {performance.vs_cdi:+.4f}%")
    print(f"  • vs SELIC: {performance.vs_selic:+.4f}%")
    print(f"  • vs IPCA: {performance.vs_ipca:+.4f}%")

    print("\n🤖 Estrutura para LLM (preparada para Elliot):")
    llm_data = extract_metrics_for_llm_explanation(performance)

    print("  📊 Performance:")
    print(f"    - Retorno: {llm_data['performance_metrics']['return_pct']:.4f}%")
    print(f"    - Período: {llm_data['performance_metrics']['period']['days']} dias")

    print("  ⚡ Risco:")
    print(f"    - Volatilidade: {llm_data['risk_metrics']['volatility']:.4f}%")
    print(f"    - Sharpe: {llm_data['risk_metrics']['sharpe_ratio']:.4f}")
    print(f"    - Max Drawdown: {llm_data['risk_metrics']['max_drawdown']:.4f}%")

    print("  🎯 Eficiência:")
    print(f"    - Alpha: {llm_data['efficiency_metrics']['alpha']:.4f}%")
    print(f"    - Beta: {llm_data['efficiency_metrics']['beta']:.4f}")

    print("\n✅ Sistema expandido e pronto para integração LLM!")
    print("📤 Dados estruturados disponíveis para Elliot implementar explicações educacionais.")


if __name__ == "__main__":
    main()