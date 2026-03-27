# Phase 2: Implement GitHub Actions for daily automated reports

## Objetivo
Implementar execução automática do relatório diário via GitHub Actions, rodando às 9h da manhã (horário de Brasília) de segunda a sexta-feira.

## Contexto
- ✅ Sistema end-to-end homologado e testado localmente
- ✅ GitHub Actions workflow criado em `.github/workflows/daily-report.yml`
- ⏳ Atualmente executando manualmente na máquina local
- 🎯 Próxima fase: automação via GitHub

## Tasks
- [ ] Validar execução do workflow automaticamente após merge
- [ ] Configurar GitHub Secrets no repositório:
  - `MA_SMTP_USERNAME` = f18.cloud@gmail.com
  - `MA_SMTP_PASSWORD` = (App Password do Gmail)
  - `MA_SMTP_SENDER_EMAIL` = f18.cloud@gmail.com
  - `MA_RECIPIENT_EMAIL` = seu.email@gmail.com
- [ ] Monitorar logs do primeiro run automatizado
- [ ] Ajustar timezone/horário se necessário
- [ ] Configurar alertas de falha

## Workflow Configurado
```yaml
# .github/workflows/daily-report.yml
- ⏰ Horário: 09:00 (Brasília - CRON: 12 14 * * 1-5 UTC)
- 📅 Dias: Segunda a Sexta
- 🔧 Runtime: Python 3.12
- 📧 Notificação: Email automático
```

## Referência
- Documentação local: README_TEAM_HANDOFF.md
- Código dos collectors: src/collectors/
- Testes: tests/integration/test_end_to_end.py
- Workflow: .github/workflows/daily-report.yml
