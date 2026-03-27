# User Stories - Sistema de Análise de Fundos Nubank

**Data:** 27/03/2026
**Versão:** 1.0

---

## 📋 Épicos e User Stories

### Epic 1: Coleta Automatizada de Dados

#### US001 - Coletar dados BCB diários
**Como** investidor interessado em benchmarks de mercado,
**Quero** que o sistema colete automaticamente dados de SELIC, CDI e IPCA do BCB,
**Para** ter informações atualizadas e confiáveis sobre indicadores econômicos.

##### Critérios de Aceite
- [ ] Dado que são 9h da manhã em um dia útil, quando o sistema executar, então deve coletar dados da API BCB (séries 432, 4389, 433)
- [ ] Dado que a API BCB retorna dados, quando os dados são recebidos, então devem ser validados (formato de data, valor numérico)
- [ ] Dado que os dados são válidos, quando armazenados, então devem ser persistidos no SQLite com timestamp da coleta
- [ ] Dado que a API BCB está indisponível, quando houver erro de conexão, então deve usar dados do último dia útil disponível

##### Definição de Done
- [ ] Código implementado e testado
- [ ] Testes unitários para casos de sucesso e erro
- [ ] Log estruturado de execução
- [ ] Documentação de API e parâmetros

---

#### US002 - Coletar dados CVM de fundos Nubank
**Como** investidor em fundos Nubank,
**Quero** que o sistema colete automaticamente dados de performance dos fundos,
**Para** acompanhar meu portfólio sem esforço manual.

##### Critérios de Aceite
- [ ] Dado que são 9h da manhã, quando o sistema executar, então deve baixar dados CVM mais recentes
- [ ] Dado que os dados CVM são baixados, quando processados, então deve filtrar apenas fundos do Nubank
- [ ] Dado que fundos Nubank são identificados, quando analisados, então deve extrair código, nome, e última cota
- [ ] Dado que dados são coletados, quando processados, então devem ser armazenados com data de referência

##### Definição de Done
- [ ] Download e parse de CSV CVM funcional
- [ ] Filtro de fundos Nubank implementado
- [ ] Dados persistidos com referência temporal
- [ ] Error handling para formato CVM inválido

---

### Epic 2: Análise e Processamento

#### US003 - Calcular performance dos fundos vs benchmarks
**Como** investidor analítico,
**Quero** que o sistema compare automaticamente performance dos fundos Nubank com benchmarks,
**Para** avaliar se estou tomando boas decisões de investimento.

##### Critérios de Aceite
- [ ] Dado que dados de fundos e benchmarks estão disponíveis, quando analisados, então deve calcular rentabilidade nos últimos 30 dias
- [ ] Dado que performance é calculada, quando comparada, então deve mostrar diferença vs SELIC, CDI, IPCA
- [ ] Dado que há histórico, quando processado, então deve calcular volatilidade e sharpe ratio
- [ ] Dado que análise está completa, quando finalizada, então deve ranquear fundos por performance

##### Definição de Done
- [ ] Algoritmos de cálculo implementados
- [ ] Testes unitários para cálculos financeiros
- [ ] Validação com dados históricos conhecidos
- [ ] Performance otimizada para datasets grandes

---

### Epic 3: Geração de Relatório

#### US004 - Gerar PDF com dados atuais
**Como** usuário final,
**Quero** receber um relatório PDF bem formatado,
**Para** consumir informações de forma clara e profissional.

##### Critérios de Aceite
- [ ] Dado que análise está completa, quando PDF é gerado, então deve incluir cabeçalho com data e hora
- [ ] Dado que dados estão processados, quando PDF é criado, então deve mostrar tabela de fundos com performance
- [ ] Dado que há benchmarks, quando incluídos no PDF, então deve exibir gráfico comparativo
- [ ] Dado que há notícias, quando adicionadas, então deve mostrar seção com resumo das principais

##### Definição de Done
- [ ] PDF gerado com layout consistente
- [ ] Tabelas e gráficos legíveis
- [ ] Seção de notícias formatada
- [ ] Arquivo salvo localmente antes do envio

---

## 🎯 Priorização (MoSCoW)

### Must Have (P0) - MVP
- [x] US001: Coletar dados BCB diários
- [ ] US002: Coletar dados CVM de fundos Nubank
- [ ] US003: Análise comparativa com benchmarks
- [ ] US004: Gerar PDF básico

### Should Have (P1) - V1.1
- [ ] Melhorias no formato do PDF
- [ ] Sistema de retry robusto
- [ ] Coleta de notícias relevantes
- [ ] Envio automatizado por email

### Could Have (P2) - V1.2
- [ ] Interface web para configurações
- [ ] Múltiplos destinatários
- [ ] Notificações alternativas (Slack/WhatsApp)
- [ ] Métricas de sistema
