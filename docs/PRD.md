# PRD: Sistema de Análise de Fundos de Investimento

## 🎯 Problema

### Situação Atual
Investidores que desejam acompanhar a performance de fundos de investimento (especificamente Nubank) enfrentam:
- **Análise manual demorada**: Buscar dados em múltiplas fontes (MaisRetorno, BCB, CVM)
- **Dados dispersos**: Informações espalhadas em diferentes plataformas
- **Falta de comparação sistemática**: Dificuldade para comparar com benchmarks (SELIC, CDI, IPCA)
- **Ausência de histórico**: Sem base consolidada para análises temporais
- **Inconsistência**: Análises irregulares ou superficiais

### Impacto
- Decisões de investimento baseadas em informações incompletas
- Tempo perdido em coleta manual de dados
- Oportunidades perdidas por falta de monitoramento regular

## 💡 Solução Proposta

### Visão
Sistema automatizado que coleta, processa e analisa dados de fundos de investimento diariamente, fornecendo relatórios comparativos via email.

### Funcionalidades Principais
1. **Coleta automatizada de dados**
   - APIs oficiais: BCB (SELIC, CDI, IPCA), CVM (fundos)
   - Notícias: Google News RSS (Nubank)
   - Fallback: Web scraping MaisRetorno

2. **Processamento e análise**
   - Comparação com benchmarks de mercado
   - Análise de tendências e performance
   - Consolidação de notícias relevantes

3. **Geração de relatórios**
   - PDF formatado e legível
   - Gráficos comparativos
   - Resumo executivo

4. **Entrega automatizada**
   - Email diário às 9h
   - Histórico em base local

## 👥 User Stories

### Epic 1: Coleta de Dados
**Como** investidor interessado em fundos Nubank,
**Quero** que o sistema colete automaticamente dados de performance,
**Para** não precisar buscar informações manualmente.

### Epic 2: Análise Comparativa
**Como** tomador de decisões de investimento,
**Quero** comparações automáticas com benchmarks de mercado,
**Para** avaliar se meus investimentos estão performando bem.

### Epic 3: Relatórios Automatizados
**Como** usuário do sistema,
**Quero** receber relatórios diários por email,
**Para** manter-me informado sem esforço manual.

## 🎯 Métricas de Sucesso

| Métrica | Baseline | Target | Como Medir |
|---------|----------|--------|------------|
| Disponibilidade do sistema | - | 99% | Logs de execução diária |
| Tempo de geração de relatório | - | < 5 min | Timestamp início/fim |
| Precisão dos dados | - | 99% | Validação vs fonte oficial |
| Entregas de email | - | 100% | Confirmação SMTP |

## 📋 Escopo

### In Scope (MVP)
- ✅ Coleta de dados BCB (SELIC, CDI)
- ✅ Coleta de notícias Nubank (Google News RSS)
- ✅ Base de dados SQLite local
- ✅ Geração de PDF básico
- ✅ Envio por email
- ✅ Scheduler diário (9h)

### In Scope (V2)
- Dados CVM de fundos específicos
- Gráficos avançados no PDF
- Interface web para configurações
- Múltiplos fundos de interesse
- API própria para consultas

### Out of Scope
- ❌ Recomendações de investimento
- ❌ Integração com corretoras
- ❌ Trading automatizado
- ❌ Análises preditivas/IA
- ❌ Mobile app

## 🔗 Dependências

### Técnicas
- APIs BCB (gratuitas e estáveis)
- Google News RSS (gratuito)
- SMTP server para email
- Ambiente Python local

### Riscos
| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| API BCB indisponível | Baixa | Alto | Cache local + fallback |
| Google News muda formato | Média | Médio | Parser flexível + NewsAPI backup |
| MaisRetorno bloqueia scraping | Alta | Baixo | Priorizar APIs oficiais |

## 📅 Timeline

### Fase 1: MVP (Semana 1-2)
- **Desenvolvimento**: Python + SQLite + PDF + Email
- **Testes**: Validação dados BCB + Google News
- **Deploy**: Ambiente local

### Fase 2: Melhorias (Semana 3)
- **Dados CVM**: Integração fundos específicos
- **UX**: PDF melhorado com gráficos
- **Confiabilidade**: Error handling + logs

### Fase 3: Otimização (Semana 4)
- **Performance**: Otimização queries
- **Monitoramento**: Alertas de falha
- **Documentação**: Manual do usuário

## 🏗️ Arquitetura de Alto Nível

```
[Scheduler] → [Data Collector] → [Analyzer] → [PDF Generator] → [Email Sender]
                     ↓
              [SQLite Database]
```

### Componentes
- **Scheduler**: Cron/Task Scheduler para execução diária
- **Data Collector**: Módulo de coleta (APIs + RSS)
- **Analyzer**: Processamento e comparações
- **PDF Generator**: ReportLab para relatórios
- **Email Sender**: SMTP para entrega
- **Database**: SQLite para histórico

## ✅ Critérios de Aceite

### Funcional
- [ ] Sistema executa automaticamente às 9h
- [ ] Coleta dados BCB e Google News
- [ ] Gera PDF com análise comparativa
- [ ] Envia email com sucesso
- [ ] Armazena histórico em SQLite

### Não-Funcional
- [ ] Execução completa em < 5 minutos
- [ ] PDF legível e bem formatado
- [ ] Log de execução para troubleshooting
- [ ] Error handling para falhas de API

---

**Aprovação**: Project Lead
**Data**: 27/03/2026
**Versão**: 1.0