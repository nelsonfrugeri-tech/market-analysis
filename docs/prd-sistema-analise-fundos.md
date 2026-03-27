# PRD: Sistema de Análise de Fundos de Investimento

## Problema

**Para quem:** Investidores que possuem múltiplos fundos de investimento (especificamente fundos Nubank) e precisam acompanhar performance de forma consistente e automatizada.

**Qual problema:** Atualmente, o acompanhamento de performance de fundos de investimento é manual, trabalhoso e inconsistente. Requer acesso a múltiplas fontes de dados (MaisRetorno, sites do BCB, notícias), cálculos manuais de benchmarks e compilação manual de informações para análise.

**Dor atual:**
- **Tempo**: 30-60 minutos diários para coletar e analisar dados manualmente
- **Inconsistência**: Análises variam em profundidade e frequência
- **Delay**: Informações críticas podem ser perdidas entre verificações manuais
- **Erro humano**: Cálculos e comparações manuais são suscetíveis a erros

## Contexto

**Por que agora:**
- Fundos Nubank em carteira requerem acompanhamento ativo
- Dados necessários estão disponíveis via APIs gratuitas (BCB, CVM, Google News)
- ROI claro: automação economiza 30h/mês de trabalho manual
- Stack técnico Python já dominiado pelo time

**Oportunidade:**
- APIs oficiais BCB/CVM garantem dados confiáveis sem custos
- Sistema local remove dependências de terceiros
- Escalabilidade: pode expandir para múltiplos investidores

## Solução Proposta

**Sistema automatizado de análise e relatórios de fundos de investimento com:**

1. **Coleta automatizada diária** de dados de:
   - Performance dos fundos (CVM)
   - Benchmarks oficiais (BCB: SELIC, CDI, IPCA)
   - Notícias relevantes (Google News RSS)

2. **Análise comparativa automática**:
   - Performance vs benchmarks (SELIC, CDI, Tesouro IPCA+)
   - Evolução histórica (últimos 30/90/365 dias)
   - Identificação de tendências e alertas

3. **Relatório executivo em PDF** entregue diariamente por email às 9h com:
   - Dashboard visual da performance
   - Comparação com benchmarks
   - Resumo de notícias relevantes
   - Recomendações de ação (se aplicável)

## User Stories

### Epic 1: Coleta de Dados Automatizada

**US-001: Coleta de dados BCB**
```
Como investidor,
Quero que o sistema colete automaticamente dados de SELIC, CDI e IPCA do BCB,
Para ter benchmarks oficiais atualizados diariamente.

Critérios de Aceite:
- [ ] Dado que é 9h de um dia útil, quando o sistema executa, então coleta dados BCB do dia anterior
- [ ] Dado que há dados históricos, quando há nova coleta, então compara com período anterior
- [ ] Dado que API BCB está indisponível, quando sistema executa, então usa dados cached e notifica erro

Notas Técnicas:
- API BCB: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados
- Séries: SELIC (432), CDI (4389), IPCA (433)
- Fallback: cache local + retry após 30min
```

**US-002: Coleta de notícias Nubank**
```
Como investidor,
Quero que o sistema colete notícias relevantes sobre Nubank automaticamente,
Para ficar informado sobre fatores que podem impactar meus investimentos.

Critérios de Aceite:
- [ ] Dado que é 9h, quando sistema executa, então coleta últimas 24h de notícias
- [ ] Dado que há notícias encontradas, quando processa, então filtra por relevância
- [ ] Dado que há notícias irrelevantes, quando filtra, então exclui spam/duplicatas

Notas Técnicas:
- Source: Google News RSS feed
- Keywords: "Nubank", "Nu Holdings", "fundos Nubank"
- Limite: 10 notícias mais relevantes por dia
```

### Epic 2: Análise e Comparação

**US-003: Cálculo de performance vs benchmarks**
```
Como investidor,
Quero ver a performance dos meus fundos comparada com SELIC, CDI e Tesouro IPCA+,
Para entender se estão performando acima ou abaixo do mercado.

Critérios de Aceite:
- [ ] Dado que há dados do fundo e benchmarks, quando calcula, então mostra % vs SELIC
- [ ] Dado que há histórico, quando calcula, então mostra tendência 30/90/365 dias
- [ ] Dado que performance está abaixo do benchmark, quando analisa, então destaca alerta

Definição de Done:
- Cálculos validados com fórmulas financeiras padrão
- Testes unitários cobrindo cenários edge
- Performance comparativa exibida com precisão de 2 casas decimais
```

### Epic 3: Geração de Relatórios

**US-004: Relatório PDF automatizado**
```
Como investidor,
Quero receber um relatório PDF diário por email às 9h,
Para ter visão consolidada sem precisar acessar multiple sistemas.

Critérios de Aceite:
- [ ] Dado que são 9h de um dia útil, quando sistema executa, então gera PDF
- [ ] Dado que PDF foi gerado, quando processo completa, então envia por email
- [ ] Dado que há erro na geração, quando falha, então notifica por email sem PDF

Notas Técnicas:
- Layout: 1-2 páginas máximo
- Seções: Performance, Benchmarks, Notícias, Alertas
- Formato: ReportLab PDF + templates HTML/CSS
- Email: SMTP local + fallback Gmail
```

### Epic 4: Infraestrutura e Monitoramento

**US-005: Scheduler e persistência**
```
Como operador do sistema,
Quero que o sistema execute automaticamente todos os dias úteis às 9h,
Para garantir relatórios consistentes sem intervenção manual.

Critérios de Aceite:
- [ ] Dado que é 9h de segunda a sexta, quando scheduler executa, então roda pipeline completo
- [ ] Dado que há dados coletados, quando processa, então salva em SQLite local
- [ ] Dado que sistema falha, quando erro ocorre, então loga erro e notifica admin

Definição de Done:
- Cron job configurado (Linux/Mac) ou Task Scheduler (Windows)
- SQLite database com schema versionado
- Logs estruturados com rotação automática
- Health check endpoint para monitoramento
```

## Métricas de Sucesso

### Eficiência Operacional
- **Tempo de análise manual**: 30-60 min/dia → 0 min/dia (automação completa)
- **Consistência de relatórios**: ad-hoc → diário, 100% uptime
- **Tempo até insights**: 24-48h → tempo real (dados do dia anterior)

### Qualidade da Informação
- **Accuracy de dados**: >99% (APIs oficiais BCB/CVM)
- **Coverage de notícias**: >90% notícias relevantes Nubank capturadas
- **Alertas acionáveis**: >80% dos alertas geram ação do usuário

### Adoção e Satisfação
- **Tempo para first value**: <24h após setup inicial
- **User satisfaction**: >4/5 (pesquisa após 30 dias)
- **Abandonment rate**: <10% após primeiro mês

## Escopo

### In Scope (MVP)
- ✅ **Coleta automatizada**: BCB (SELIC, CDI, IPCA) + Google News RSS
- ✅ **Análise básica**: Performance vs benchmarks + tendências
- ✅ **Relatório PDF**: Layout simples, enviado por email
- ✅ **Scheduler**: Execução diária automatizada
- ✅ **Persistência local**: SQLite para dados históricos

### Out of Scope (Versão 1)
- ❌ **Web dashboard**: Interface web (apenas PDF por email)
- ❌ **Multiple portfolios**: Apenas fundos Nubank inicialmente
- ❌ **Advanced analytics**: ML/AI para predições
- ❌ **Mobile app**: Acesso apenas via email
- ❌ **Multi-user**: Sistema single-user inicialmente

### Future Iterations
- 🔮 **Dashboard web** para visualização interativa
- 🔮 **API própria** para integrações externas
- 🔮 **Alertas avançados** via Slack/WhatsApp
- 🔮 **Análise de múltiplos portfolios** de usuários
- 🔮 **Machine learning** para insights preditivos

## Dependências

### Técnicas
- ✅ **APIs externas confirmadas**: BCB, CVM, Google News RSS funcionais
- ⚠️ **SMTP local**: Configuração de servidor email local required
- ⚠️ **Scheduler OS**: Cron (Linux/Mac) ou Task Scheduler (Windows)

### Dados
- ✅ **Dados históricos BCB**: Disponíveis via API sem limite
- ✅ **Dados CVM**: Portal CSV acessível
- ⚠️ **Dados fundos Nubank**: Dependente de scraping MaisRetorno (fallback)

### Negócio
- ✅ **Aprovação para uso**: APIs públicas, sem restrições comerciais
- ✅ **Infra local**: Sistema roda em máquina local, sem cloud costs

## Timeline

### Sprint 1: Foundation (Semana 1)
- **Setup**: Estrutura projeto + ambiente Python
- **APIs**: Integração BCB + testes básicos
- **Persistência**: SQLite schema + models básicos

### Sprint 2: Data Pipeline (Semana 2)
- **Coleta**: BCB + Google News automatizada
- **Processing**: Lógica de análise vs benchmarks
- **Scheduler**: Cron job configurado

### Sprint 3: Reporting (Semana 3)
- **PDF**: Geração de relatório com ReportLab
- **Email**: SMTP integration + templates
- **Testing**: E2E testing do pipeline completo

### Sprint 4: Polish & Launch (Semana 4)
- **Error handling**: Logs + exception handling robusto
- **Documentation**: README + setup instructions
- **Launch**: Deploy em produção + primeira execução

**Release target**: 4 semanas após kick-off

## Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| **API BCB instabilidade** | Média | Alto | Cache local + retry logic + alertas |
| **MaisRetorno bloqueia scraping** | Alta | Médio | Priorizar APIs oficiais CVM, accept degraded mode |
| **SMTP local complexo** | Baixa | Alto | Fallback para Gmail SMTP, documentação detalhada |
| **Scheduler falha silenciosamente** | Baixa | Alto | Health check diário + alertas |
| **PDF geração muito lenta** | Baixa | Baixo | Performance profiling + otimização templates |

---

## Aprovação e Next Steps

**Aprovação necessária de:**
- ✅ Product Lead (Nelson) - Escopo e prioridades
- ⏳ Tech Lead (Mr. Robot) - Arquitetura e feasibility
- ⏳ Dev Lead (Elliot) - Timeline e recursos

**Próximos passos:**
1. **Approval**: Review final e sign-off do PRD
2. **Issues**: Criação de GitHub Issues detalhadas por user story
3. **Sprint 1**: Kick-off técnico e setup inicial

---

*Documento criado por: Tyrell Wellick (TPM)*
*Data: 2026-03-27*
*Versão: 1.0*