# PRD Denso — Núcleo Híbrido 1x/2x para Agent Coding

**Documento:** Product Requirements Document (PRD)  
**Versão:** 1.0.0  
**Data:** 2026-04-04  
**Status:** Ready for implementation  
**Autor:** Douglas Souza / ChatGPT Business  
**Target Executor:** Agent Coding / Autocoder  
**Classificação:** Arquitetura Obrigatória do Framework

---

## 1. Resumo Executivo

Este PRD especifica a implementação de um **núcleo híbrido de execução** para o framework de agent coding, estruturado em dois perfis operacionais:

- **1x (default)**: aplica o **Núcleo Obrigatório Universal (NOU)** a 100% das tarefas de código.
- **2x (performance/limite)**: aplica **NOU + Núcleo Obrigatório Especializado (NOE)** quando o escopo da tarefa exigir profundidade algorítmica, garantias de complexidade, validações de performance, ou uso de estruturas/algoritmos de fronteira.

O objetivo é eliminar dois extremos indesejados:

1. **Subengenharia** em tarefas críticas, nas quais o modelo entrega soluções corretas porém insuficientes em escala, performance ou rigor.
2. **Over-engineering** em tarefas simples, nas quais o modelo injeta complexidade acidental, estruturas desnecessárias e custo cognitivo excessivo.

O sistema proposto preserva um padrão universal de excelência de engenharia e ativa, de forma condicional, um motor de performance/limite com roteamento semântico, contratos de qualidade, gates de validação e saídas auditáveis.

---

## 2. Problema

O framework atual precisa suportar duas classes distintas de trabalho sob o mesmo arcabouço:

### 2.1 Classe A — Engenharia de Software Geral
Exemplos:
- CRUD
- APIs REST/gRPC
- workers e jobs
- integrações externas
- refactors de domínio
- feature delivery convencional

Nesses casos, o mais importante é:
- tipagem explícita
- segurança
- clareza
- arquitetura coerente
- testes
- compatibilidade com padrões do repositório
- baixo custo de manutenção

### 2.2 Classe B — Problemas de Performance / Limite / Fronteira
Exemplos:
- consultas em ranges com alto throughput
- grafos dinâmicos
- árvores mutáveis
- strings avançadas
- workloads de baixa latência
- problemas com `n`, `q` ou `m` de ordem `10^5+`
- algoritmos competitivos/IOI-grade

Nesses casos, além da qualidade universal, é necessário:
- seleção algorítmica explícita
- provas ou certificados de complexidade
- análise de memória
- edge-case analysis
- stress tests
- uso de estruturas e técnicas avançadas quando o problema exigir

### 2.3 Falha Atual a Resolver
Sem um modelo híbrido formalizado, o agente tende a oscilar entre:
- respostas excessivamente simples para problemas difíceis, ou
- respostas excessivamente sofisticadas para tarefas comuns.

Este PRD formaliza uma arquitetura onde:
- a qualidade universal é **sempre obrigatória**;
- a excelência algorítmica é **obrigatória quando o escopo indicar necessidade real**.

---

## 3. Visão do Produto

### 3.1 Nome Proposto
**Hybrid Core Execution Engine**

### 3.2 Definição
Um mecanismo de execução e validação para geração de código, com:
- **perfil 1x** como baseline universal;
- **perfil 2x** como modo especializado de performance/limite;
- **detecção automática de escopo**;
- **contratos de qualidade e especialização**;
- **saídas rastreáveis e auditáveis**.

### 3.3 Princípio Central
> Todo código deve cumprir o NOU. Apenas os casos com exigência real de escala, complexidade ou fronteira sobem para o NOE.

---

## 4. Objetivos

### 4.1 Objetivos Primários
1. Padronizar a geração de código de alta qualidade em todo o framework.
2. Formalizar o perfil híbrido **1x/2x** como mecanismo oficial de execução.
3. Implementar detecção de escopo capaz de ativar automaticamente o modo 2x.
4. Integrar um catálogo de técnicas de fronteira para problemas compatíveis.
5. Tornar a saída do agente verificável por meio de certificados, notas de conformidade e gates.

### 4.2 Objetivos Secundários
1. Reduzir over-engineering em tarefas de Tier 1.
2. Reduzir under-engineering em tarefas de Tier 2 e Tier 3.
3. Melhorar previsibilidade, auditabilidade e manutenção do framework.
4. Criar base expansível para futuras especializações algorítmicas.

---

## 5. Não Objetivos

1. Não transformar toda tarefa de código em problema de competição.
2. Não obrigar frontier algorithms em tarefas CRUD, API, worker ou refactor comum.
3. Não substituir o núcleo universal por um núcleo algorítmico.
4. Não introduzir um perfil 3x nesta fase.
5. Não permitir micro-otimizações que violem legibilidade, segurança ou arquitetura.

---

## 6. Personas

### 6.1 Persona Primária
**Agent Coding / Autocoder**
- gera código
- modifica código existente
- precisa obedecer contratos do framework
- precisa adaptar profundidade ao escopo real

### 6.2 Persona Secundária
**Revisor Técnico / Arquiteto**
- valida se a saída do agente está consistente com o escopo
- precisa de artefatos auditáveis
- precisa saber por que o agente escolheu determinada abordagem

### 6.3 Persona Terciária
**Engenheiro de Aplicação**
- usa o agente para acelerar delivery
- quer qualidade consistente sem complexidade desnecessária

---

## 7. Princípios de Projeto

1. **Obrigatoriedade graduada**: qualidade universal sempre ativa; especialização condicional.
2. **Simplicidade adequada**: a solução mais simples que satisfaça o escopo deve prevalecer em 1x.
3. **Escalada por necessidade**: 2x entra apenas por sinal forte de performance/limite.
4. **Auditabilidade**: decisões do agente devem ser rastreáveis.
5. **Segurança e manutenção acima de micro-otimização**.
6. **Compatibilidade com o framework existente**: contratos YAML como fonte de verdade.

---

## 8. Escopo Funcional

### 8.1 Núcleo Obrigatório Universal (NOU)
Aplica-se a toda geração de código, sem exceção.

Deve impor:
- tipagem explícita
- null safety tratada explicitamente
- invariantes arquiteturais
- clareza e tamanho controlado de funções
- segurança de entrada/saída
- tratamento de erro consistente
- testes obrigatórios para lógica de negócio
- aderência a padrões do repositório
- justificativa de mudanças significativas

### 8.2 Núcleo Obrigatório Especializado (NOE)
Aplica-se somente em tarefas detectadas como algorítmicas, de performance, de alta escala, baixa latência, ou competitivas.

Deve impor:
- justificativa de algoritmo/estrutura
- certificado de complexidade
- prova mínima de corretude/invariantes
- edge-case analysis
- stress testing
- análise de memória/layout/cache quando aplicável
- uso de algoritmos e estruturas de fronteira quando o problema exigir

### 8.3 Motor Híbrido 1x/2x
- **1x**: ativa apenas o NOU
- **2x**: ativa NOU + NOE
- detecção automática baseada em sinais do input, contexto e constraints

### 8.4 Scope Detection Engine
Mecanismo de classificação da tarefa em:
- Tier 1: engenharia geral
- Tier 2: algorítmico/otimização
- Tier 3: competitivo/frontier

### 8.5 Pipeline de Validação
O sistema deve validar a saída conforme o perfil ativo:
- gates universais sempre obrigatórios
- gates especializados apenas quando 2x estiver ativo

---

## 9. Arquitetura Proposta

### 9.1 Camadas

#### Camada A — Execution Profiles
Define os perfis `default_1x` e `performance_2x`.

#### Camada B — Universal Quality Core
Define obrigações permanentes de engenharia.

#### Camada C — Scope Detection
Analisa a tarefa e decide se o 2x é necessário.

#### Camada D — Algorithmic Frontier Core
Fornece o conteúdo técnico avançado do modo 2x.

#### Camada E — Validation Gates
Reprova outputs que não satisfaçam o perfil ativo.

### 9.2 Precedência
Em qualquer conflito:
1. Segurança vence micro-otimização.
2. Corretude vence velocidade percebida.
3. Clareza arquitetural vence cleverness local.
4. NOU vence NOE em conflitos de diretriz.

---

## 10. Estrutura de Diretórios Requerida

```text
/.internal/
├── core/
│   ├── execution-profiles.yaml
│   ├── universal-quality-contract.yaml
│   ├── algorithmic-frontier-contract.yaml
│   └── scope-detection-engine.yaml
├── domains/
│   ├── software-engineering/
│   │   └── standards/
│   │       └── advanced-coding-quality.yaml
│   └── ioi-gold-compiler/
│       ├── contract.yaml
│       ├── frontier-algorithmic-core.yaml
│       ├── algorithm-selection-map.yaml
│       ├── frontier-validation-gates.yaml
│       └── structural-memory.yaml
└── modes/
    └── autocoder/
        ├── contract.yaml
        └── adapters/
            ├── default-1x.yaml
            ├── performance-2x-tier-2.yaml
            └── performance-2x-tier-3.yaml
```

---

## 11. Requisitos Funcionais

### FR-001 — Perfis de Execução
O sistema deve definir dois perfis operacionais canônicos:
- `default_1x`
- `performance_2x`

#### Critérios
- perfis versionados
- legíveis por modo/contrato
- sobreposição previsível
- sem ambiguidade de ativação

---

### FR-002 — Ativação do 1x por Default
Toda tarefa de geração ou modificação de código deve iniciar em `default_1x`.

#### Critérios
- 100% das tarefas entram via 1x
- nenhuma tarefa ignora o NOU
- ausência de sinal de escalada mantém 1x

---

### FR-003 — Ativação Condicional do 2x
O sistema deve subir para `performance_2x` quando identificar sinais de complexidade, performance ou limite.

#### Triggers mínimos
- `n`, `q`, `m` >= `100000`
- menção a throughput, latência, time limit, memory limit
- problemas com `graph`, `tree`, `flow`, `range query`, `substring`, `palindrome`, `dynamic connectivity`
- menção explícita a otimização, constraints pesados, competição, IOI/ICPC

#### Critérios
- ativação explicável
- ativação auditável
- possibilidade de registrar quais triggers dispararam

---

### FR-004 — Contrato Universal Obrigatório
O sistema deve aplicar o NOU a toda tarefa.

#### Conteúdos mínimos do NOU
- explicit typing
- null safety
- architecture invariants
- code clarity
- security
- error handling
- testing
- project conventions
- change justification

#### Critérios
- output com `compliance_notes`
- falha em qualquer gate crítico reprova a saída

---

### FR-005 — Contrato Especializado Condicional
Quando 2x estiver ativo, o sistema deve aplicar o NOE além do NOU.

#### Conteúdos mínimos do NOE
- algorithm selection rationale
- complexity certificate
- invariant documentation
- edge-case analysis
- stress test plan
- memory bound estimate

#### Critérios
- deve haver rastreabilidade entre problema detectado e técnica escolhida
- não pode haver solução ingênua quando constraints a inviabilizam

---

### FR-006 — Scope Detection Engine
O sistema deve classificar a tarefa em um tier operacional.

#### Tiers
- `tier_1_universal`
- `tier_2_algorithmic`
- `tier_3_competitive`

#### Critérios
- motor baseado em padrões semânticos, constraints e contexto
- deve retornar score de confiança
- deve retornar triggers disparados
- deve orientar quais contratos entram no contexto do modo

---

### FR-007 — Catálogo Algorítmico de Fronteira
O sistema deve disponibilizar um catálogo técnico para o NOE, com mapeamento problema -> abordagem.

#### Conteúdos mínimos
- Eertree
- Link-Cut Tree
- Wavelet Tree
- SOS DP
- Parallel Binary Search
- Min-Cost Max-Flow com Potenciais
- Simulated Annealing

#### Critérios
- cada técnica deve possuir:
  - aplicabilidade
  - complexidade
  - pré-condições
  - riscos/pitfalls
  - limite de uso

---

### FR-008 — Mapa de Seleção Algorítmica
O sistema deve conter um arquivo de roteamento semântico do tipo problema -> algoritmo sugerido.

#### Exemplos mínimos
- `dynamic_tree_queries -> link_cut_tree`
- `range_quantile_dynamic -> wavelet_tree`
- `distinct_palindromes_substring -> eertree`
- `offline_parallel_decisions -> parallel_binary_search`
- `min_cost_flow_negative_edges -> min_cost_max_flow_potentials`
- `subset_aggregation_masks -> sos_dp`

---

### FR-009 — Adapters por Perfil
O modo `autocoder` deve possuir adapters separados por perfil/tier.

#### Critérios
- adapter 1x para engenharia geral
- adapter 2x tier 2 para otimização avançada
- adapter 2x tier 3 para frontier/competitive
- cada adapter injeta contexto, exigências e formato de saída específicos

---

### FR-010 — Output Auditável
O output do agente deve mudar conforme o perfil ativo.

#### Em 1x, deve incluir no mínimo
- summary
- code changes
- compliance notes
- tests executed / proposed
- risks

#### Em 2x, deve incluir adicionalmente
- algorithm selection rationale
- complexity certificate
- edge-case checklist
- stress test strategy
- memory/performance notes

---

### FR-011 — Gates Universais
O sistema deve executar validações universais em todas as tarefas.

#### Gates mínimos
- linting
- type checking
- complexity guard (universal)
- security scan
- test coverage threshold
- architecture conformance

---

### FR-012 — Gates Especializados
O sistema deve executar gates adicionais quando o 2x estiver ativo.

#### Gates mínimos
- algorithmic validation
- constraint satisfaction check
- correctness invariant verification
- stress test pass/fail
- memory layout audit
- cache/throughput note quando aplicável

---

### FR-013 — Prevenção de Over-Engineering
O sistema deve rejeitar ou sinalizar uso de algoritmos/estruturas desnecessariamente complexos em escopos Tier 1.

#### Exemplos de reprovação/sinalização
- uso de LCT em domínio CRUD
- adoção de Wavelet Tree para problema de consulta simples resolvido por prefix sums
- introdução de meta-heurística sem requisito real

---

### FR-014 — Prevenção de Under-Engineering
O sistema deve rejeitar ou sinalizar soluções inadequadas para constraints declarados.

#### Exemplos de reprovação/sinalização
- loop O(n²) para `n=200000`
- busca linear por query em workload de alta taxa
- ignorar risco de overflow
- ignorar necessidade de estrutura dinâmica apropriada

---

### FR-015 — Estrutural Memory
O sistema deve manter uma memória estrutural com:
- convenções de projeto
- decisões arquiteturais persistentes
- mapa de padrões algorítmicos
- pitfall notes por técnica

---

## 12. Requisitos Não Funcionais

### NFR-001 — Determinismo Contratual
A mesma classe de input deve produzir a mesma classe de ativação, salvo overrides explícitos.

### NFR-002 — Explicabilidade
Toda ativação do 2x deve ser explicável em linguagem natural e em sinalização estruturada.

### NFR-003 — Extensibilidade
Novas técnicas, novos tiers e novos domínios devem poder ser adicionados sem quebrar o NOU.

### NFR-004 — Baixo Acoplamento
O core universal não deve depender do domínio algorítmico.

### NFR-005 — Auditabilidade
Toda execução deve permitir reconstruir:
- perfil aplicado
- triggers disparados
- gates rodados
- razões de aprovação/reprovação

### NFR-006 — Segurança
O NOE não pode flexibilizar nenhuma exigência do NOU.

### NFR-007 — Performance Operacional
O motor de detecção não pode introduzir overhead incompatível com o uso do framework.

---

## 13. Modelo de Dados / Schemas

### 13.1 execution-profiles.yaml

```yaml
version: 1.0.0
profiles:
  default_1x:
    activates:
      - universal_quality_core
    requires:
      - compliance_notes
      - tests
      - risk_assessment
    early_exit: true
    quality_threshold: 0.80

  performance_2x:
    activates:
      - universal_quality_core
      - algorithmic_frontier_core
    requires:
      - compliance_notes
      - tests
      - risk_assessment
      - algorithm_selection_rationale
      - complexity_certificate
      - edge_case_analysis
      - stress_test_plan
      - memory_bound_estimate
    early_exit: false
    quality_threshold: 0.95
    frontier_tiers:
      - tier_2
      - tier_3
```

### 13.2 scope-detection-engine.yaml

```yaml
version: 1.0.0
triggers:
  complexity_indicators:
    keywords:
      - optimize
      - performance
      - low latency
      - graph
      - tree
      - flow
      - substring
      - palindrome
      - range query
      - quantile
      - dynamic connectivity
      - competitive programming
      - ioi
      - icpc
  constraints:
    max_n_for_escalation: 100000
    max_q_for_escalation: 100000
classification:
  tier_1_universal:
    profile: default_1x
  tier_2_algorithmic:
    profile: performance_2x
  tier_3_competitive:
    profile: performance_2x
output:
  - tier
  - profile
  - confidence
  - triggers_matched
  - rationale
```

### 13.3 universal-quality-contract.yaml

```yaml
version: 1.0.0
mandatory: true
dimensions:
  - type_safety
  - architecture_invariants
  - code_clarity
  - security
  - error_handling
  - testing
  - project_conventions
  - change_justification
enforcement:
  fail_on:
    - missing_typing
    - missing_validation
    - missing_error_strategy
    - missing_tests_for_business_logic
```

### 13.4 algorithmic-frontier-contract.yaml

```yaml
version: 1.0.0
mandatory_when:
  - profile == performance_2x
requires:
  - algorithm_selection_rationale
  - complexity_certificate
  - invariant_documentation
  - edge_case_analysis
  - stress_test_plan
  - memory_bound_estimate
frontier_tiers:
  tier_2:
    focus:
      - advanced_data_structures
      - optimization_patterns
      - strong_complexity_control
  tier_3:
    focus:
      - frontier_algorithms
      - correctness_proofs
      - competitive_patterns
```

---

## 14. Lógica de Ativação

### 14.1 Regras Gerais
1. Toda tarefa entra em 1x.
2. O motor avalia semântica, constraints e forma do problema.
3. Se os sinais atingirem limiar, o sistema promove para 2x.
4. Dentro do 2x, classifica se é Tier 2 ou Tier 3.

### 14.2 Heurísticas Mínimas
Promover para 2x quando qualquer conjunto abaixo estiver presente:

#### Grupo A — Constraints
- `n >= 100000`
- `q >= 100000`
- time limit restrito
- memory limit explícito

#### Grupo B — Estrutura do Problema
- consultas em ranges com updates
- grafos com caminhos/custos/fluxos
- árvores dinâmicas
- substrings/palíndromos/sufixos
- decisão offline em massa

#### Grupo C — Linguagem do Usuário
- “otimize”
- “alta performance”
- “limite”
- “competitivo”
- “IOI-grade”
- “baixa latência”

### 14.3 Anti-Falso-Positivo
Não promover para 2x apenas por:
- uso da palavra “rápido” em contexto não técnico
- presença de listas, loops ou paginação simples
- tarefas CRUD com volume moderado sem constraints críticos

---

## 15. Catálogo Inicial de Técnicas do 2x

### 15.1 Tier 2
- Segment Tree
- Fenwick Tree
- DSU / rollback
- Sparse Table
- Dijkstra / 0-1 BFS
- SCC
- bridges/articulation
- HLD básico
- Digit DP
- SOS DP
- Binary Search on Answer
- Parallel Binary Search

### 15.2 Tier 3
- Link-Cut Tree
- Wavelet Tree
- Eertree
- Persistent data structures
- Min-Cost Max-Flow com Potenciais
- Centroid Decomposition
- Suffix Automaton
- Simulated Annealing (somente quando exato é impraticável)

### 15.3 Requisito por Técnica
Cada item do catálogo deve incluir:
- nome
- classe do problema
- complexidade
- pré-condições
- limitações
- pitfalls
- exemplo de uso
- motivos para não usar

---

## 16. Formato de Saída Esperado do Agent Coding

### 16.1 Saída Mínima em 1x
```yaml
execution_profile: default_1x
scope_classification: tier_1_universal
summary:
code_changes:
compliance_notes:
tests:
risks:
```

### 16.2 Saída Mínima em 2x
```yaml
execution_profile: performance_2x
scope_classification: tier_2_algorithmic | tier_3_competitive
summary:
problem_analysis:
algorithm_selection_rationale:
complexity_certificate:
edge_case_analysis:
stress_test_plan:
memory_bound_estimate:
code_changes:
compliance_notes:
tests:
risks:
```

---

## 17. Gates e Critérios de Aprovação

### 17.1 Gates Universais
Aprovado somente se:
- lint sem erros críticos
- type check sem falhas
- ausência de vulnerabilidade evidente
- tratamento de erro compatível
- testes mínimos definidos
- aderência estrutural ao projeto

### 17.2 Gates do 2x
Aprovado somente se, além dos universais:
- algoritmo compatível com constraints
- complexidade declarada é coerente
- edge cases foram considerados
- plano de stress test existe
- risco de overflow/memória foi tratado
- técnica frontier não foi usada sem justificativa

### 17.3 Rejeição Automática
Reprovar quando:
- perfil ativo exige artefato ausente
- solução ingênua viola constraints
- técnica de fronteira é usada sem necessidade em Tier 1
- saída viola NOU

---

## 18. Casos de Uso e Comportamento Esperado

### Caso 1 — CRUD simples
**Input:** “Criar endpoint para cadastro de usuário.”

**Resultado esperado:**
- perfil 1x
- NOU ativo
- sem catálogo frontier
- foco em validação, tipagem, testes, segurança

### Caso 2 — Query engine
**Input:** “Precisamos responder queries de menor valor em ranges com updates, n=200k.”

**Resultado esperado:**
- perfil 2x
- Tier 2
- algoritmo sugerido: segment tree / fenwick conforme operação
- complexity certificate obrigatório

### Caso 3 — Árvore dinâmica
**Input:** “Manter floresta dinâmica com link/cut e query de máximo no caminho.”

**Resultado esperado:**
- perfil 2x
- Tier 3
- LCT considerado
- invariantes e stress test obrigatórios

### Caso 4 — Subpalíndromos distintos
**Input:** “Encontrar todos os palíndromos distintos em string grande.”

**Resultado esperado:**
- perfil 2x
- Tier 3
- Eertree considerado
- prova de linearidade ou justificativa equivalente

---

## 19. Telemetria e Observabilidade

O sistema deve registrar:
- perfil aplicado
- tier classificado
- triggers disparados
- algoritmo sugerido/escolhido
- gates executados
- gates falhos
- causa de escalada para 2x
- motivo de rejeição, se houver

Esses logs devem permitir:
- auditoria posterior
- tuning de heurísticas
- análise de falsos positivos/falsos negativos da classificação

---

## 20. Plano de Implementação

### Fase 1 — Contratos Base
Entregáveis:
- `execution-profiles.yaml`
- `universal-quality-contract.yaml`
- `algorithmic-frontier-contract.yaml`
- `scope-detection-engine.yaml`

### Fase 2 — Conteúdo de Domínio
Entregáveis:
- `frontier-algorithmic-core.yaml`
- `algorithm-selection-map.yaml`
- `frontier-validation-gates.yaml`
- `structural-memory.yaml`

### Fase 3 — Integração no Autocoder
Entregáveis:
- atualização do `autocoder/contract.yaml`
- adapters 1x e 2x
- output schema expandido
- validação por perfil

### Fase 4 — Testes e Calibração
Entregáveis:
- suíte de cenários Tier 1, Tier 2 e Tier 3
- tuning de triggers
- tuning de thresholds
- casos de regressão para over/under-engineering

### Fase 5 — Rollout Controlado
Entregáveis:
- rollout por feature flag
- métricas de aceitação
- avaliação de precisão da detecção

---

## 21. Backlog Técnico Inicial

### Epic A — Core Contracts
- criar schemas base
- validar herança entre contratos
- definir precedência

### Epic B — Scope Engine
- implementar parser semântico de sinais
- criar regras de thresholds
- retornar justificativa estruturada

### Epic C — Frontier Catalog
- normalizar técnicas
- mapear problema -> algoritmo
- adicionar pitfalls e exemplos

### Epic D — Autocoder Integration
- adaptar modo para perfis
- expandir `compliance_notes`
- adicionar certificados e campos 2x

### Epic E — Validation
- gates universais
- gates especializados
- rejeição automática baseada em perfil

### Epic F — Regression Harness
- benchmark de classificação
- cenários de falso positivo/negativo
- suite de smoke tests por perfil

---

## 22. Critérios de Aceitação do Produto

O PRD será considerado implementado quando:

1. Toda tarefa de código passar por `default_1x`.
2. O sistema conseguir promover para `performance_2x` com base em triggers verificáveis.
3. O NOU estiver formalizado e acoplado ao autocoder.
4. O NOE estiver formalizado e acionável condicionalmente.
5. O catálogo frontier existir e estar ligado ao modo 2x.
6. O output do agente variar corretamente entre 1x e 2x.
7. Houver gates universais e especializados funcionando.
8. Houver cobertura mínima de cenários Tier 1, 2 e 3.
9. Casos de over-engineering e under-engineering forem detectáveis por teste.
10. A precedência NOU > NOE estiver implementada.

---

## 23. Riscos

### Risco 1 — Escalada excessiva para 2x
**Impacto:** complexidade desnecessária  
**Mitigação:** thresholds conservadores + casos de falso positivo

### Risco 2 — Não escalada em problemas críticos
**Impacto:** soluções lentas ou inviáveis  
**Mitigação:** triggers explícitos + testes de constraints

### Risco 3 — Catálogo frontier virar repositório teórico sem uso real
**Impacto:** custo de manutenção sem benefício  
**Mitigação:** exigir aplicabilidade, pitfalls e critérios de uso

### Risco 4 — NOE conflitar com clareza universal
**Impacto:** código “esperto” e frágil  
**Mitigação:** precedência formal do NOU

### Risco 5 — Saída do agente ficar excessivamente verbosa
**Impacto:** pior experiência operacional  
**Mitigação:** schemas compactos, porém obrigatórios, e adapters por perfil

---

## 24. Dependências

- contratos YAML como source of truth
- integração do modo autocoder com adapters por perfil
- mecanismo de validação/gates do framework
- memória estrutural persistente do projeto

---

## 25. Questões em Aberto

1. Quais thresholds exatos de escalada devem ser calibrados por linguagem/domínio?
2. Quais linguagens terão suporte inicial completo no 2x?
3. O scope engine será puramente heurístico ou incluirá scoring ponderado?
4. Como o framework armazenará e versionará exemplos canônicos por técnica?
5. Qual será a superfície mínima de output para não degradar usabilidade?

---

## 26. Recomendação Final para Implementação

Implementar o sistema em duas ondas:

### Onda 1
- contratos
- perfis
- scope detection
- output schema
- gates mínimos

### Onda 2
- catálogo frontier robusto
- structural memory avançada
- tier 3 completo
- tuning fino de heurísticas

A recomendação é **não adiar o 1x**, pois ele resolve a padronização universal imediatamente; e **não superdimensionar o 2x na primeira entrega**, concentrando-se inicialmente nos casos com maior ganho prático: range queries, grafos, árvores dinâmicas e strings avançadas.

---

## 27. Definition of Done

Uma implementação estará “done” quando:
- os arquivos de contrato existirem e validarem;
- o autocoder reconhecer e aplicar 1x/2x;
- o motor de escopo classificar corretamente um conjunto mínimo de cenários;
- a saída tiver campos obrigatórios por perfil;
- gates universais e especializados estiverem conectados;
- houver exemplos de referência para Tier 1, Tier 2 e Tier 3;
- o repositório possuir documentação de uso e manutenção.

---

## 28. Anexo A — Exemplo de Decision Record

```yaml
execution_decision_record:
  input_summary: "Range minimum query com updates em n=200000"
  detected_profile: performance_2x
  detected_tier: tier_2_algorithmic
  triggers_matched:
    - large_scale
    - range_query
    - frequent_updates
    - optimization_request
  selected_approach: segment_tree
  rejected_alternatives:
    - naive_scan_per_query
    - prefix_sum_not_applicable_due_to_updates
  complexity_certificate:
    build: O(n)
    update: O(log n)
    query: O(log n)
  universal_compliance:
    typing: pass
    security: pass
    tests: pass
  specialized_compliance:
    stress_test_plan: pass
    edge_case_analysis: pass
    memory_bound_estimate: pass
```

---

## 29. Anexo B — Exemplo de Policy Statement

```yaml
policy:
  all_code_must_pass_universal_quality: true
  performance_frontier_is_scope_conditional: true
  default_profile: default_1x
  escalated_profile: performance_2x
  no_opt_out_from_universal_core: true
  no_frontier_without_scope_signal: true
  universal_core_has_precedence: true
```

