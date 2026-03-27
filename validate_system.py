#!/usr/bin/env python3
"""Script de validação rápida dos componentes individuais.

Execute antes do teste end-to-end para identificar problemas mais facilmente.
"""

import asyncio
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VALIDATE] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def test_imports():
    """Testa se todas as importações funcionam."""
    logger.info("🔍 Testando importações...")

    try:
        from market_analysis.infrastructure.cvm_collector import collect_multiple_months, NU_RESERVA_CNPJ
        from market_analysis.infrastructure.benchmark_fetcher import collect_benchmarks
        from market_analysis.infrastructure.news_fetcher import collect_news
        from market_analysis.infrastructure.pdf_generator import generate_pdf
        from market_analysis.application.performance import compute_performance
        logger.info("   ✅ Todas as importações OK")
        return True
    except ImportError as e:
        logger.error(f"   ❌ Erro de importação: {e}")
        return False


def test_cvm_connection():
    """Testa conexão com API CVM."""
    logger.info("📈 Testando conexão CVM...")

    try:
        from market_analysis.infrastructure.cvm_collector import collect_multiple_months, NU_RESERVA_CNPJ

        # Test with just 1 week of data to be quick
        records = collect_multiple_months(cnpj=NU_RESERVA_CNPJ, num_months=1)

        if records:
            logger.info(f"   ✅ CVM OK - coletados {len(records)} registros")
            logger.info(f"   📊 Período: {records[0].date} até {records[-1].date}")
            return True
        else:
            logger.warning("   ⚠️  CVM retornou dados vazios")
            return False

    except Exception as e:
        logger.error(f"   ❌ Erro CVM: {e}")
        return False


def test_bcb_connection():
    """Testa conexão com API BCB."""
    logger.info("🏛️ Testando conexão BCB...")

    try:
        from market_analysis.infrastructure.benchmark_fetcher import collect_benchmarks

        # Test with recent dates
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        benchmarks = collect_benchmarks(start_date, end_date)

        if benchmarks and (benchmarks.get('selic_rate') or benchmarks.get('cdi_rate')):
            logger.info("   ✅ BCB OK - benchmarks coletados")
            if 'selic_rate' in benchmarks:
                logger.info(f"   📊 SELIC: {benchmarks['selic_rate']}")
            if 'cdi_rate' in benchmarks:
                logger.info(f"   📊 CDI: {benchmarks['cdi_rate']}")
            return True
        else:
            logger.warning("   ⚠️  BCB retornou dados vazios")
            return False

    except Exception as e:
        logger.error(f"   ❌ Erro BCB: {e}")
        return False


def test_news_connection():
    """Testa coleta de notícias."""
    logger.info("📰 Testando coleta de notícias...")

    try:
        from market_analysis.infrastructure.news_fetcher import collect_news

        news = collect_news()

        if news:
            logger.info(f"   ✅ News OK - coletadas {len(news)} notícias")
            return True
        else:
            logger.warning("   ⚠️  Nenhuma notícia coletada")
            return False

    except Exception as e:
        logger.error(f"   ❌ Erro News: {e}")
        return False


def test_pdf_generation():
    """Testa geração de PDF com dados mock."""
    logger.info("📄 Testando geração de PDF...")

    try:
        from market_analysis.infrastructure.pdf_generator import generate_pdf
        from market_analysis.domain.models.fund import FundPerformance, FundDailyRecord
        from market_analysis.infrastructure.news_fetcher import NewsItem
        from decimal import Decimal

        # Create mock performance data (FundPerformance structure)
        mock_performance = FundPerformance(
            fund_cnpj="43.121.002/0001-41",
            fund_name="Nu Reserva Planejada (TESTE)",
            period_start=date.today() - timedelta(days=90),
            period_end=date.today(),
            nav_start=1.000000,
            nav_end=1.052500,
            return_pct=5.25,
            equity_start=100000.0,
            equity_end=105250.0,
            volatility=0.15,
            shareholders_current=1000,
            benchmark_selic=4.00,
            benchmark_cdi=4.10,
            benchmark_ipca=3.50,
            vs_selic=1.25,
            vs_cdi=1.15,
            vs_ipca=1.75,
            trend_30d="up",
            daily_records=[]
        )

        # Create mock news
        mock_news = [
            NewsItem(
                title="Teste de Notícia",
                link="https://exemplo.com",
                pub_date=datetime.now(),
                source="Fonte Teste"
            )
        ]

        # Try to generate PDF
        test_output = Path("reports") / "test_validation.pdf"
        test_output.parent.mkdir(exist_ok=True)

        pdf_path = generate_pdf(
            performance=mock_performance,
            news=None,
            output_path=str(test_output)
        )

        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            logger.info(f"   ✅ PDF OK - gerado {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
            # Clean up test file
            pdf_path.unlink()
            return True
        else:
            logger.error("   ❌ PDF gerado está vazio ou inválido")
            return False

    except Exception as e:
        logger.error(f"   ❌ Erro PDF: {e}")
        return False


def test_smtp_config():
    """Testa configuração SMTP."""
    logger.info("📧 Testando configuração SMTP...")

    try:
        import os
        from pathlib import Path

        # Try to load .env
        env_path = Path('.env')
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_path)
            except ImportError:
                logger.info("   ℹ️  python-dotenv não disponível, usando env vars diretas")

        smtp_vars = {
            'MA_SMTP_HOST': os.getenv('MA_SMTP_HOST'),
            'MA_SMTP_USERNAME': os.getenv('MA_SMTP_USERNAME'),
            'MA_SMTP_PASSWORD': os.getenv('MA_SMTP_PASSWORD'),
            'MA_SMTP_SENDER_EMAIL': os.getenv('MA_SMTP_SENDER_EMAIL'),
        }

        missing = [key for key, value in smtp_vars.items() if not value]

        if missing:
            logger.warning(f"   ⚠️  Variáveis SMTP faltando: {missing}")
            logger.info("   💡 Configure no .env ou variáveis de ambiente")
            return False
        else:
            logger.info("   ✅ Configuração SMTP OK")
            logger.info(f"   📧 Host: {smtp_vars['MA_SMTP_HOST']}")
            logger.info(f"   📧 Sender: {smtp_vars['MA_SMTP_SENDER_EMAIL']}")
            return True

    except Exception as e:
        logger.error(f"   ❌ Erro SMTP config: {e}")
        return False


def main():
    """Run all validation tests."""
    logger.info("🔍 VALIDAÇÃO RÁPIDA DO SISTEMA")
    logger.info("=" * 50)

    tests = [
        ("Importações", test_imports),
        ("Conexão CVM", test_cvm_connection),
        ("Conexão BCB", test_bcb_connection),
        ("Coleta News", test_news_connection),
        ("Geração PDF", test_pdf_generation),
        ("Config SMTP", test_smtp_config),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Erro inesperado em {test_name}: {e}")
            results.append((test_name, False))

        logger.info("")  # Blank line between tests

    # Summary
    logger.info("📋 RESUMO DA VALIDAÇÃO")
    logger.info("-" * 30)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1

    logger.info("")
    logger.info(f"📊 Resultado: {passed}/{len(tests)} testes passaram")

    if passed == len(tests):
        logger.info("🎉 Sistema pronto para teste end-to-end!")
        logger.info("Execute: python test_end_to_end.py --email seu@email.com")
        return 0
    else:
        logger.warning("⚠️  Corrija os problemas antes do teste end-to-end")
        return 1


if __name__ == "__main__":
    sys.exit(main())