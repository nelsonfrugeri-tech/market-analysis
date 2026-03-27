#!/usr/bin/env python3
"""Teste end-to-end completo do sistema de análise de fundos.

Este script testa TODA a integração real:
- Coleta CVM (código do Tyrell)
- Coleta BCB (código do Elliot)
- Cálculo de performance
- Geração de PDF
- Envio por email

Execute: python test_end_to_end.py --email seu.email@exemplo.com
"""

import argparse
import asyncio
import logging
import smtplib
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

# Import the actual CLI module to reuse all real code
from market_analysis.cli import main as cli_main


class TestEmailSender:
    """Implementação simples de EmailSender para teste end-to-end."""

    def __init__(self, smtp_config: dict[str, str]):
        self.smtp_config = smtp_config

    def send_report(self, pdf_path: Path, recipient_email: str) -> bool:
        """Envia o relatório PDF por email."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['sender_email']
            msg['To'] = recipient_email
            msg['Subject'] = f"Relatório Nu Reserva Planejada - {datetime.now().strftime('%d/%m/%Y')}"

            # Body
            body = f"""
Relatório de análise do fundo Nu Reserva Planejada gerado automaticamente.

Sistema de Market Analysis - Teste End-to-End
Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

Este é um teste do sistema completo:
✅ Coleta CVM (dados reais do fundo)
✅ Coleta BCB (taxas de benchmark reais)
✅ Cálculo de performance
✅ Geração de PDF
✅ Envio por email

Arquivo anexo: {pdf_path.name}
            """

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Attach PDF
            with open(pdf_path, 'rb') as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                pdf_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename={pdf_path.name}'
                )
                msg.attach(pdf_attachment)

            # Send email
            with smtplib.SMTP(self.smtp_config['host'], int(self.smtp_config['port'])) as server:
                if self.smtp_config.get('use_tls', 'true').lower() == 'true':
                    server.starttls()

                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.send_message(msg)

            return True

        except Exception as e:
            logging.error(f"Erro ao enviar email: {e}")
            return False


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the test."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [TEST-E2E] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_smtp_config() -> dict[str, str]:
    """Carrega configuração SMTP do arquivo .env ou variáveis de ambiente."""
    import os

    # Try to load .env file (python-dotenv is optional)
    env_path = Path('.env')
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            print("⚠️  python-dotenv não instalado. Instale com: pip install python-dotenv")
            print("   Ou configure as variáveis MA_SMTP_* no ambiente")
            print("   Continuando sem carregar .env...")

    config = {
        'host': os.getenv('MA_SMTP_HOST', 'smtp.gmail.com'),
        'port': os.getenv('MA_SMTP_PORT', '587'),
        'username': os.getenv('MA_SMTP_USERNAME', ''),
        'password': os.getenv('MA_SMTP_PASSWORD', ''),
        'use_tls': os.getenv('MA_SMTP_USE_TLS', 'true'),
        'sender_email': os.getenv('MA_SMTP_SENDER_EMAIL', ''),
    }

    # Validate required fields
    required_fields = ['username', 'password', 'sender_email']
    missing_fields = [field for field in required_fields if not config[field]]

    if missing_fields:
        print(f"❌ Configuração SMTP incompleta. Faltam: {missing_fields}")
        print("\nConfigura as variáveis no .env:")
        print("MA_SMTP_HOST=smtp.gmail.com")
        print("MA_SMTP_PORT=587")
        print("MA_SMTP_USERNAME=seu.email@gmail.com")
        print("MA_SMTP_PASSWORD=sua_senha_de_app")
        print("MA_SMTP_SENDER_EMAIL=seu.email@gmail.com")
        print("MA_SMTP_USE_TLS=true")
        sys.exit(1)

    return config


def main() -> int:
    """Main test runner."""
    parser = argparse.ArgumentParser(
        prog="test-end-to-end",
        description="Teste completo end-to-end do sistema de análise de fundos",
    )
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Email para receber o relatório de teste",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Número de meses para analisar (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        logger.info("🚀 INICIANDO TESTE END-TO-END DO SISTEMA REAL")
        logger.info("=" * 60)

        # Step 1: Load SMTP configuration
        logger.info("📧 Carregando configuração SMTP...")
        smtp_config = load_smtp_config()
        logger.info(f"   SMTP Host: {smtp_config['host']}:{smtp_config['port']}")
        logger.info(f"   Sender: {smtp_config['sender_email']}")

        # Step 2: Generate PDF using real CLI code
        logger.info("📊 Executando CLI real para gerar relatório...")
        logger.info(f"   Target: Nu Reserva Planejada (CNPJ: 43.121.002/0001-41)")
        logger.info(f"   Período: {args.months} meses")
        logger.info(f"   Teste inclui: CVM + BCB + Performance + PDF")

        # Create reports directory
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        # Set output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = reports_dir / f"teste_e2e_{timestamp}.pdf"

        # Run the actual CLI with real data collection
        cli_args = [
            "--months", str(args.months),
            "--output", str(output_path),
            "--verbose" if args.verbose else ""
        ]
        cli_args = [arg for arg in cli_args if arg]  # Remove empty strings

        exit_code = cli_main(cli_args)

        if exit_code != 0:
            logger.error("❌ Falha na geração do relatório via CLI")
            return exit_code

        if not output_path.exists():
            logger.error(f"❌ PDF não foi gerado: {output_path}")
            return 1

        # Step 3: Send email
        logger.info("📧 Enviando relatório por email...")
        logger.info(f"   Destinatário: {args.email}")
        logger.info(f"   Arquivo: {output_path.name} ({output_path.stat().st_size} bytes)")

        email_sender = TestEmailSender(smtp_config)

        if not email_sender.send_report(output_path, args.email):
            logger.error("❌ Falha no envio do email")
            return 1

        # Success!
        logger.info("✅ TESTE END-TO-END CONCLUÍDO COM SUCESSO!")
        logger.info("=" * 60)
        logger.info(f"📁 PDF salvo em: {output_path.resolve()}")
        logger.info(f"📧 Relatório enviado para: {args.email}")
        logger.info("")
        logger.info("🎯 COMPONENTES TESTADOS:")
        logger.info("   ✅ CVM Collector (código do Tyrell)")
        logger.info("   ✅ BCB Benchmark Fetcher (código do Elliot)")
        logger.info("   ✅ Performance Calculation")
        logger.info("   ✅ News Collection")
        logger.info("   ✅ PDF Generation")
        logger.info("   ✅ Email Delivery")
        logger.info("")
        logger.info("Verifique seu email para confirmar o recebimento!")

        return 0

    except KeyboardInterrupt:
        logger.info("Teste cancelado pelo usuário")
        return 1
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())