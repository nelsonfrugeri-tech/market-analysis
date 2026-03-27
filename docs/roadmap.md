# Roadmap - Sistema de Análise de Fundos Nubank

**Data:** 27/03/2026
**Versão:** 1.0

---

## 🎯 Visão Estratégica

**Objetivo:** Criar sistema automatizado de análise diária de fundos Nubank com relatórios por email, evoluindo de MVP básico para plataforma completa de monitoramento de investimentos.

---

## 📅 Now (Sprint Atual - Semana 27/03 a 03/04)

| Item | Status | Owner | ETA |
|------|--------|-------|-----|
| ✅ Investigação APIs | Completo | Mr. Robot | 27/03 |
| 🔄 Documentação de negócio | Em andamento | Tyrell Wellick | 27/03 |
| ⏳ Criação de GitHub Issues | Aguardando | TBD | 28/03 |
| ⏳ Setup repositório | Aguardando | TBD | 28/03 |

**Objetivo da Sprint:** Completar discovery e preparar para desenvolvimento

---

## 📋 Next (Próximo Ciclo - Semana 04/04 a 10/04)

### MVP - Versão 1.0

| Item | Prioridade | Estimativa | Descrição |
|------|-----------|------------|-----------|
| Coleta dados BCB | P0 | 2 dias | SELIC, CDI, IPCA via API oficial |
| Coleta notícias Google News | P0 | 1 dia | RSS feed Nubank |
| Base SQLite | P0 | 1 dia | Persistência local |
| Geração PDF básica | P0 | 2 dias | ReportLab com dados essenciais |
| Email automático | P0 | 1 dia | SMTP + scheduler |
| Testes e validação | P0 | 1 dia | QA completo |

**Entrega:** Sistema funcional executando localmente às 9h diárias

---

## 🚀 Later (Backlog Priorizado)

### V1.1 - Dados de Fundos (Semana 11/04 a 17/04)

| Item | Prioridade | Estimativa | Notas |
|------|-----------|------------|-------|
| Integração CVM | P1 | 2 dias | Parse CSV + filtro Nubank |
| Análise comparativa | P1 | 2 dias | Performance vs benchmarks |
| PDF melhorado | P1 | 1 dia | Gráficos + layout profissional |
| Sistema de retry | P1 | 1 dia | Error handling robusto |

**Entrega:** Análises comparativas reais de fundos

### V1.2 - Melhorias UX (Semana 18/04 a 24/04)

| Item | Prioridade | Estimativa | Notas |
|------|-----------|------------|-------|
| Interface web configuração | P2 | 3 dias | Flask app para settings |
| Múltiplos destinatários | P2 | 1 dia | Lista de emails |
| Métricas de sistema | P2 | 1 dia | Dashboards internos |

**Entrega:** Sistema configurável via web

### V2.0 - Plataforma (Futuro - TBD)

| Item | Prioridade | Estimativa | Notas |
|------|-----------|------------|-------|
| Deploy na nuvem | P2 | 2 semanas | AWS/GCP hosting |
| API pública | P2 | 1 semana | REST API para dados |
| Múltiplos bancos | P3 | 3 semanas | Inter, BTG, XP |
| Mobile app | P3 | 6 semanas | React Native |

---

## 🚫 Won't Have (Decisões Explícitas)

| Item | Razão |
|------|-------|
| Recomendações de IA | Fora do escopo de análise, foco em dados |
| Trading automatizado | Regulamentação complexa + riscos |
| Análise preditiva | MVP foca em dados históricos |
| Integração corretoras | APIs privadas + complexidade |
| Alertas tempo real | Relatório diário suficiente para MVP |

---

## 📊 Métricas de Roadmap

### Indicadores de Progresso

| Métrica | Q1 2026 | Q2 2026 | Q3 2026 |
|---------|---------|---------|---------|
| **Funcionalidades entregues** | 5 core | 8 total | 12 total |
| **Uptime do sistema** | 95% | 99% | 99.5% |
| **Tempo médio execução** | <5min | <3min | <2min |
| **Dados coletados/dia** | 4 fontes | 6 fontes | 8+ fontes |

### Success Criteria por Versão

**V1.0 (MVP):**
- ✅ Sistema executa diariamente sem intervenção
- ✅ PDF gerado e enviado automaticamente
- ✅ Dados BCB coletados com 100% precisão

**V1.1 (Dados Fundos):**
- 🎯 Performance fundos Nubank vs benchmarks
- 🎯 Análises comparativas nos relatórios
- 🎯 <1% erro nos cálculos financeiros

**V1.2 (UX):**
- 🎯 Configuração via interface web
- 🎯 Múltiplos usuários suportados
- 🎯 Métricas de uso disponíveis

---

## ⚠️ Dependências Críticas

### Externas
- **API BCB estável** - essencial para MVP
- **Google News acessível** - fallback: NewsAPI
- **CVM CSV formato consistente** - monitoramento necessário

### Internas
- **Aprovação do project lead** - cada fase
- **Tempo de desenvolvimento** - 40-60h estimadas
- **Ambiente de teste** - setup local completo

### Riscos ao Roadmap

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| APIs indisponíveis | Alto | Fallbacks + cache |
| Mudança prioridades | Médio | Roadmap flexível |
| Overengineering | Médio | MVP-first approach |
| Scope creep | Alto | Decisões explícitas |

---

## 🔄 Processo de Atualização

- **Weekly reviews:** Toda segunda-feira
- **Sprint retrospectives:** Final de cada ciclo
- **Stakeholder alignment:** Monthly
- **Roadmap adjustments:** Conforme necessário

**Próxima revisão:** 03/04/2026

---

## 🎯 Definition of Ready para Roadmap Items

Antes de mover item de "Later" para "Next":
- [ ] User stories escritas com critérios de aceite
- [ ] Dependências técnicas mapeadas
- [ ] Estimativa refinada com time
- [ ] Aprovação do product owner
- [ ] Capacity do time confirmada

---

*Última atualização: 27/03/2026*
*Próxima revisão: 03/04/2026*
