# FRAMEWORK DE DEEP AGENTS ORIENTADO A SPEC DRIVEN DEVELOPMENT
## Relatório Técnico Atualizado Conforme o Estado Atual do Repositório - v4.0

---

## 1. RESUMO EXECUTIVO

O repositório evoluiu além de um plano conceitual e já materializa um **baseline funcional de execução estável orientada por specs**, com três avanços concretos:

1. **Foundation de specs implementada em código**: já existem `spec-registry.ts`, `spec-linker.ts`, `run-manifest.ts` e `spec-compiler.ts`, o que significa que a camada central de registro, aprovação, rastreabilidade e compilação deixou de ser apenas roadmap e passou a existir como artefato executável.
2. **Domínio inicial consolidado**: a capacidade que hoje organiza o repositório não é um exemplo genérico de pagamentos, mas sim a capability `stable-execution`, orientada a garantir estabilidade, roteamento correto, isolamento de escrita, handoffs válidos e prevenção de loops.
3. **Validação regressiva estruturada**: o repositório possui uma suíte explícita de testes para invariantes, roteamento, integridade de configuração, existência de specs e padrões proibidos.

Em contrapartida, o repositório ainda **não evidencia, de forma equivalente, todas as camadas do plano v3**. Há sinais fortes de implementação em Fase 1 e parte da Fase 2, mas ainda não há confirmação equivalente de maturidade para itens como `conformance-engine.ts`, `policy-enforcer.ts`, `approval-gate.ts`, `trace-exporter.ts`, `artifact-ledger.ts`, telemetria de aderência à spec ou inteligência de release em produção.

**Conclusão prática**: o repositório já deve ser descrito como um framework em transição de **prompt/runtime-governed** para **spec-governed**, mas ainda em estágio de **foundation operacional + enforcement parcial**, e não como plataforma completa de deep agent operations conforme a arquitetura-alvo integral.

---

## 2. POSICIONAMENTO ARQUITETURAL REVISADO

### 2.1 O que o repositório já é hoje

No estado atual, o repositório já pode ser caracterizado como:

> **Um framework de agent coding com foundation spec-driven implementada para execução estável, roteamento controlado, rastreabilidade mínima e validação regressiva orientada a invariantes.**

Isso é um avanço relevante em relação ao documento anterior, que descrevia quase toda a solução como alvo futuro. Hoje já existe uma espinha dorsal que inclui:

- registro e aprovação de specs
- linker de rastreabilidade bidirecional
- compilação determinística de DAG a partir de specs
- bootstrap de run manifest
- capability, behavior, policy e contract specs do domínio `stable-execution`
- testes de regressão cobrindo invariantes centrais do runtime

### 2.2 O que o repositório ainda não é

Ainda não há evidência suficiente para classificar o projeto como:

- plataforma completa de deep agent operations com observabilidade de conformidade em produção
- sistema maduro de detecção contínua de drift spec-to-runtime
- release platform spec-driven com canário, rollback, floors de conformidade e incident automation
- ecossistema completo de plugins e ferramentas listados no roadmap v3

Portanto, o posicionamento técnico correto neste momento é:

> **spec-driven foundation implemented, governed execution partially implemented, conformance/observability/release intelligence still incomplete.**

---

## 3. EVIDÊNCIAS DE PROGRESSO JÁ MATERIALIZADAS

### 3.1 Spec Plane já implementado em núcleo mínimo funcional

O plano anterior tratava `spec-registry.ts`, `spec-linker.ts` e `spec-compiler.ts` como itens de fundação. No repositório atual, esses artefatos já existem e definem o backbone do modelo.

#### 3.1.1 Registry de specs

O `spec-registry.ts` já cumpre responsabilidades reais de:

- validação estrutural por tipo de spec
- registro versionado por `spec_id` + `version`
- bloqueio de downgrade de versão
- fluxo formal de aprovação via `approveSpec()`
- gate que impede compilação sem spec aprovada

**Leitura arquitetural**: isso significa que a ideia “spec como fonte da verdade” já começou a ser internalizada no runtime de framework, deixando de ser apenas disciplina documental.

#### 3.1.2 Traceability backbone

O `spec-linker.ts` implementa a cadeia de rastreabilidade exigida no documento anterior:

`requirement -> spec -> DAG node -> code ref -> test case -> evidence -> runtime trace -> ownership`

Além disso, o linker já calcula `completeness_score`, identifica gaps, aplica severidade (`warning`, `error`, `blocking`) e expõe um gate `assertMinimumLinks()` para bloquear releases críticas com rastreabilidade insuficiente.

**Leitura arquitetural**: a rastreabilidade bidirecional deixou de ser conceito aspiracional e passou a ser mecanismo mensurável.

#### 3.1.3 Compiler determinístico com merge de behavior, policy e verification

O `spec-compiler.ts` já compila DAGs tipados a partir de specs aprovadas, herdando invariantes, orçamento, retry policy, evidências requeridas e checks de conformidade. Também aplica policy bundle, faz merge de verification e realiza ordenação topológica do grafo.

**Leitura arquitetural**: o framework já começou a trocar composição oportunista por **compilação determinística da execução**.

### 3.2 Run manifest já existe como artefato de execução

O arquivo `run-manifest.ts` evidencia que o runtime já produz uma estrutura explícita para execução, incluindo:

- `run_id`, `spec_id`, `spec_version`, `dag_id`
- referência ao traceability link
- agentes ativados
- artefatos produzidos
- orçamento
- risco agregado
- riscos remanescentes
- próximos passos

**Leitura arquitetural**: isso é importante porque move o sistema de uma execução pouco observável para uma execução com artefato administrativo estruturado.

### 3.3 O domínio real implementado é “stable execution”

O documento anterior usava exemplos genéricos e um domínio ilustrativo de pagamentos. O repositório atual já convergiu para um domínio concreto: **execução estável de agentes de coding**.

A capability `stable-execution` formaliza objetivos e invariantes como:

- proibição de loops sem budget decrescente e cutoff verificável
- proibição de síntese final sem verifier aprovado
- handoff obrigatório com schema mínimo
- reexecução apenas com checkpoint ou invalidação explícita
- exigência de idempotência lógica
- proibição de fallback silencioso no roteamento
- write scopes disjuntos entre workers paralelos
- synthesizer como único writer final permitido

**Leitura arquitetural**: isso mostra um bom padrão de adoção incremental. Em vez de tentar cobrir toda a visão v3 de uma só vez, o repositório escolheu um domínio crítico do próprio runtime e o tratou como capability formal.

### 3.4 Behavior spec já modela máquina de estados real

A behavior spec `stable-execution.behavior.yaml` já descreve uma máquina de estados operacional com estados como:

- `received`
- `spec_ready`
- `dag_compiled`
- `preflight_validated`
- `running`
- `waiting_dependency`
- `retrying`
- `checkpointed`
- `validating`
- `verified`
- `synthesized`
- `failed`
- `aborted`

Também define transições proibidas importantes, por exemplo:

- `running -> running` sem progresso mensurável
- `retrying -> retrying` em loop
- `running -> synthesized` sem validação prévia
- `failed -> running` sem invalidação explícita

**Leitura arquitetural**: isso comprova que a tese de “workflow/state spec” já foi levada a código no domínio principal atual.

### 3.5 Policy spec já formaliza restrições operacionais centrais

A policy spec `stable-execution.policy.yaml` já impõe, ao menos em nível declarativo:

- `max_attempts: 3`
- backoff exponencial
- timeout por nó
- checkpoint antes de retry
- circuit breaker por estagnação
- isolamento de `write_scope`
- binding obrigatório entre frontmatter e agente
- proibição de fallback silencioso
- verifier gate obrigatório
- checkpoint persistence e selective resume
- conformance logging obrigatório

**Leitura arquitetural**: o repositório já formalizou governança operacional como spec, mesmo que parte do enforcement ainda esteja concentrada em testes e validações estruturais, e não em plugins completos de runtime.

### 3.6 Contract spec já existe para handoffs

A contract spec `agent-handoff.contract.yaml` já define os campos mandatórios do handoff entre agentes, incluindo:

- `schema_version`
- `artifact_type`
- `producer_agent`
- `consumer_agent`
- `spec_id`
- `spec_version`
- `run_id`
- `timestamp`
- `evidence_refs`
- `risk_level`
- `compatibility_assessment`
- `trace_links`

Além disso, as regras de validação já incluem:

- `no_partial_payload`
- `no_missing_provenance`
- `evidence_refs_resolvable`
- `versioning_required`
- `write_scope_disjoint`
- `verifier_gate`

**Leitura arquitetural**: isso é um passo consistente com a visão de contratos formais entre agentes, embora ainda não haja evidência equivalente de um verificador de contrato tão completo quanto o documento v3 previa como ferramenta dedicada.

### 3.7 Testes de regressão já sustentam as invariantes do framework

A suíte `.internal/tests/test_stable_execution.py` é particularmente importante porque transforma a arquitetura em disciplina verificável. Os testes já cobrem:

- paridade entre `opencode.json` e `.opencode/opencode.json`
- roteamento de comandos para agentes corretos
- existência das specs obrigatórias
- invariantes de retry, write_scope e verifier gate
- estrutura do contrato de handoff
- consistência de `AGENTS.md`
- padrões proibidos como doom loop e fallback silencioso

Esse ponto é decisivo: o repositório já não depende apenas de intenção arquitetural; ele possui **regressão executável** sobre partes críticas do comportamento esperado.

---

## 4. REINTERPRETAÇÃO DOS 5 PLANOS ARQUITETURAIS À LUZ DO REPOSITÓRIO

### 4.1 Spec Plane — **Parcialmente implementado e funcional**

**Status atual:** forte evidência de implementação.

**Já materializado:**
- registry
- approval path
- capability/behavior/policy/contract specs
- compilação básica de DAG
- defaults de rastreabilidade derivados da spec

**Ainda pendente ou não evidenciado no mesmo nível:**
- `spec-diff.ts` com classificação robusta additive/behavior/risky/breaking
- cobertura formal equivalente para release spec e SLO spec como artefatos ativos no runtime
- schema registry amplo nos moldes do roadmap v3

**Diagnóstico:** Fase 1 está claramente avançada, mas não fechada por completo.

### 4.2 Control Plane — **Parcialmente implementado**

**Status atual:** presente no compiler e na modelagem da máquina de estados, porém ainda incompleto como runtime de governança total.

**Já materializado:**
- DAG derivada de behavior spec
- budget e retry policy por nó
- required evidence e required approvals por nó
- topological ordering
- bloqueio de compilação sem spec aprovada

**Ainda pendente ou não evidenciado:**
- executor reentrante completo com checkpoints reais por nó
- approval gate explícito como componente separado
- enforcement runtime completo das quatro camadas previstas no documento anterior

**Diagnóstico:** o control plane existe em embrião funcional, mas ainda não no nível de orquestração plena descrito no v3.

### 4.3 Knowledge Plane — **Baixa evidência de implementação operacional**

**Status atual:** conceitualmente presente, mas com pouca evidência concreta no material inspecionado.

Há referências a evidência, checkpoint, run manifest e rastreabilidade, porém não há a mesma robustez comprovada para:

- memória curada persistente por `spec_id` / `run_id`
- storage episódico/semântico/conformance implementado em toolchain clara
- retrieval histórico de runs similares

**Diagnóstico:** continua mais próximo do roadmap do que da entrega.

### 4.4 Execution Plane — **Implementado no domínio de stable execution, mas não como malha completa de agentes especializados do v3**

**Status atual:** há execução governada no sentido de regras, comandos e roteamento, mas não há evidência equivalente da malha extensa de agentes especializados que o documento anterior listava.

**Já materializado:**
- regras de swarm documentadas em `AGENTS.md`
- binding de comandos para agentes
- verifier gate como regra central
- single final writer
- write scope isolation

**Ainda pendente ou não evidenciado:**
- malha completa com `policy-guardian`, `impact-analyst`, `migration-guardian`, `conformance-auditor`, `drift-detector`, `release-manager`, `memory-curator` etc. como componentes operacionais bem delimitados

**Diagnóstico:** a execução já é mais disciplinada, mas ainda não corresponde à topologia completa de agentes do plano v3.

### 4.5 Observability Plane — **Principal lacuna estrutural atual**

**Status atual:** pouco evidenciado.

Há sinais de logging e manifestação de execução, mas não há evidência equivalente de:

- telemetria de conformidade consolidada
- métricas de runtime-to-spec alignment operacionais
- alertas por invariant violation integrados
- exporter de traces e artifact ledger imutável
- conformance reports emitidos como rotina operacional do runtime

**Diagnóstico:** este plano permanece predominantemente aspiracional.

---

## 5. REVISÃO DO ROADMAP ANTERIOR COM STATUS REALISTA

### 5.1 FASE 1 — SPEC FOUNDATION

#### Sprint 1.1: Canonical Spec Model & Registry
**Status revisado:** **majoritariamente entregue**

**Evidências presentes:**
- `spec-registry.ts`
- capability spec aprovada
- fluxo de aprovação formal
- gate de aprovação antes da compilação

**Lacunas remanescentes:**
- catálogo mais amplo de schemas e spec types em uso real
- maior evidência de persistência externa ao processo

#### Sprint 1.2: Spec Compiler
**Status revisado:** **entregue em baseline funcional**

**Evidências presentes:**
- `spec-compiler.ts`
- compilação de nodes a partir de behavior spec
- merge com policy e verification
- ordenação topológica
- bootstrap de run manifest

**Lacunas remanescentes:**
- diffs semânticos de contrato maduros
- cobertura mais ampla de release/SLO/contract compilation

#### Sprint 1.3: Traceability Backbone
**Status revisado:** **parcialmente entregue, com boa base**

**Evidências presentes:**
- `spec-linker.ts`
- scoring de completude
- gaps por severidade
- append/update de links
- gate mínimo para release crítica

**Lacunas remanescentes:**
- prova de uso fim a fim em pipelines reais
- integração mais explícita com runtime traces e observabilidade

### 5.2 FASE 2 — GOVERNED EXECUTION

#### Sprint 2.1: Policy Engine & Approval Gates
**Status revisado:** **parcial**

**Evidências presentes:**
- policy spec formal
- enforcement parcial dentro do compiler
- required approvals por nó em alguns cenários

**Lacunas remanescentes:**
- componente dedicado de policy enforcement em spec-time / pre-flight / in-flight / post-flight
- approval gate operacional como módulo próprio

#### Sprint 2.2: DAG Executor Reentrante
**Status revisado:** **incipiente / não comprovado plenamente**

**Evidências presentes:**
- DAG compilada e ordenação topológica
- conceitos de retry, checkpoint e resume estão presentes nas specs e testes

**Lacunas remanescentes:**
- executor reentrante completo
- checkpoint/resume operacional por nó com evidência clara em runtime

#### Sprint 2.3: Memory & Evidence Binding
**Status revisado:** **majoritariamente pendente**

**Evidências presentes:**
- evidence refs, trace links e run manifest

**Lacunas remanescentes:**
- memória curada estruturada
- ledger/evidence store comprovados
- retrieval semântico ou conformance history

### 5.3 FASE 3 — ADVANCED VERIFICATION

#### Sprint 3.1: Contract & Compatibility Verification
**Status revisado:** **parcial em nível de spec/teste**

**Evidências presentes:**
- contract spec de handoff
- testes cobrindo required fields e validation rules

**Lacunas remanescentes:**
- verificador dedicado executando compatibilidade em runtime/pre-merge
- classificação automática robusta de breaking changes

#### Sprint 3.2: Property-Based & Model-Based Testing
**Status revisado:** **parcial**

**Evidências presentes:**
- invariantes testadas
- behavior spec com forbidden transitions
- negative patterns em testes

**Lacunas remanescentes:**
- harness explícito de property-based testing
- golden traces e replay suite formalizados

#### Sprint 3.3: Conformance Engine
**Status revisado:** **não evidenciado como entrega plena**

**Evidências presentes:**
- conformance checks anexados aos nodes compilados
- conformance report citado como output da capability
- logging de conformidade previsto na policy spec

**Lacunas remanescentes:**
- engine dedicado de conformance em runtime
- cálculo operacional consolidado de alignment por serviço/capability

### 5.4 FASE 4 — OBSERVABILITY & RELEASE INTELLIGENCE

**Status revisado:** **majoritariamente pendente**

Não há evidência equivalente à ambição da fase em termos de exporter, ledger, painéis, alertas, canary spec-driven e feedback loop produtivo em produção.

---

## 6. REVISÃO DA ESTRUTURA DO REPOSITÓRIO

### 6.1 Estrutura-alvo do documento anterior

O documento v3 apresentava uma estrutura final ampla, cobrindo ferramentas, plugins, memória, ledger, evidência, manifests e docs por domínio.

### 6.2 Estrutura efetivamente evidenciada no estado atual

Com base no material inspecionado, a estrutura efetivamente comprovada inclui pelo menos:

- `AGENTS.md`
- `.opencode/specs/capabilities/stable-execution.capability.yaml`
- `.opencode/specs/behaviors/stable-execution.behavior.yaml`
- `.opencode/specs/policies/stable-execution.policy.yaml`
- `.opencode/specs/contracts/agent-handoff.contract.yaml`
- `.opencode/tools/spec-registry.ts`
- `.opencode/tools/spec-linker.ts`
- `.opencode/tools/spec-compiler.ts`
- `.opencode/tools/run-manifest.ts`
- `.internal/tests/test_stable_execution.py`
- `opencode.json` e `.opencode/opencode.json` (referenciados pela suíte e por AGENTS.md)

### 6.3 Implicação prática

A seção de “estrutura final” do documento anterior deve deixar de sugerir que todos os blocos já existem e passar a diferenciar:

- **estrutura já implementada**
- **estrutura parcialmente implementada ou inferida**
- **estrutura alvo ainda não evidenciada**

---

## 7. RISCOS TÉCNICOS ATUAIS DO REPOSITÓRIO

### 7.1 Risco de descompasso entre arquitetura-alvo e baseline entregue

O principal risco atual é documental: o relatório anterior sugere uma maturidade maior do que a comprovada em runtime. Isso pode gerar:

- percepção inflada de prontidão
- decisões de roadmap baseadas em capacidades ainda não entregues
- erro de governança ao tratar o sistema como se já tivesse conformance e release intelligence completos

### 7.2 Risco de enforcement fragmentado

Hoje, parte do enforcement está distribuída entre:

- specs
- testes
- compiler
- AGENTS.md

Esse arranjo é útil como fundação, mas ainda pode deixar lacunas entre:

- o que está declarado
- o que é testado
- o que é realmente imposto em runtime durante todas as execuções

### 7.3 Risco de domínio excessivamente centrado em stable execution

A escolha do domínio `stable-execution` é correta como primeira capability, mas ainda não prova que o framework já generaliza o modelo para:

- release management
- impact analysis
- migration governance
- drift detection contínua
- observabilidade de conformidade em múltiplos domínios

### 7.4 Risco de drift entre contrato sanitizado e schema real do runtime

A investigação posterior mostrou que a principal causa do desvio em `/autocode` neste snapshot não era um defeito inevitável do runtime, mas sim o uso de um schema de configuração antigo/incompatível no repositório. O risco dominante, portanto, passa a ser:

- drift entre o contrato sanitizado publicado pelo repositório
- o schema efetivamente aceito pelo OpenCode em produção

Esse achado reforça a necessidade de ancorar a narrativa operacional em validação com o runtime real (`opencode debug config` e smoke tests controlados), e não apenas em paridade textual entre arquivos ou em hipóteses históricas sobre comportamento upstream.

---

## 8. RECOMENDAÇÕES DE ATUALIZAÇÃO DO RELATÓRIO

### 8.1 Ajuste de narrativa

O documento deve migrar de:

> “plano de evolução integral ainda por executar”

para:

> “baseline spec-driven já implementado para stable execution, com expansão planejada para conformance, observability e release intelligence.”

### 8.2 Ajuste de exemplos

Substituir ou reduzir o protagonismo do exemplo `payment-authorization` como eixo do relatório, já que o repositório atual evidencia um domínio mais concreto e aderente:

- `capability.stable-execution`
- `behavior.stable-execution`
- `policy.stable-execution`
- `contract.agent-handoff`

Os exemplos de pagamento podem permanecer apenas como ilustração futura, e não como espelho do estado atual do código.

### 8.3 Ajuste do roadmap

O roadmap deve ganhar três estados explícitos:

- **implementado**
- **parcialmente implementado**
- **planejado**

Sem isso, o documento continuará misturando fundação já entregue com capacidades ainda aspiracionais.

### 8.4 Ajuste da seção de métricas

As métricas devem diferenciar:

- **métricas hoje mensuráveis**: existência de specs, cobertura de testes, invariantes verificadas, completude de traceabilidade quando link gerado
- **métricas-alvo futuras**: runtime-to-spec alignment, evidence sufficiency global, drift crítico em produção, canary governed by spec

---

## 9. VERSÃO REVISADA DO DIAGNÓSTICO DE MATURIDADE

### 9.1 Maturidade por dimensão

| Dimensão | Status atual | Leitura técnica |
|---|---|---|
| Spec Foundation | **Alta** | Registry, compiler, linker e capability real já existem |
| Contract Formalization | **Média** | Contract spec e testes existem, enforcement dedicado ainda não está plenamente comprovado |
| Governed Execution | **Média** | Regras, guards e DAG compilada existem; executor/governança full-runtime ainda é parcial |
| Verification | **Média** | Regressão e invariantes já existem; conformance engine completo ainda não |
| Knowledge / Memory | **Baixa** | Pouca evidência operacional no baseline inspecionado |
| Observability | **Baixa** | Telemetria de conformidade ainda não aparece como camada madura |
| Release Intelligence | **Baixa** | Não há evidência equivalente à ambição do plano original |

### 9.2 Classificação geral

O repositório está em um estágio que pode ser descrito como:

> **Spec-Driven Foundation / Stable Execution Baseline**

E não ainda como:

> **Full Spec-Governed Deep Agent Operations Platform**

---

## 10. CONCLUSÃO ATUALIZADA

O estado atual do repositório confirma que a iniciativa saiu da fase exclusivamente conceitual e já possui uma fundação técnica relevante. O avanço mais importante não é apenas a existência de specs, mas o fato de que o framework já conecta:

- specs aprovadas
- rastreabilidade estruturada
- compilação determinística de DAG
- policy/check semantics incorporadas aos nodes
- run manifest explícito
- testes regressivos sobre invariantes críticas

Ao mesmo tempo, o repositório ainda não comprova a totalidade da arquitetura proposta no relatório v3. A evolução correta da documentação, portanto, não é declarar vitória arquitetural completa, mas **registrar uma transição bem-sucedida para uma primeira camada spec-driven operacional**, concentrada no domínio de stable execution.

A formulação mais precisa para o momento atual é:

> **O framework já implementa o núcleo de uma abordagem spec-driven para estabilidade de execução e governança básica de agentes, mas ainda precisa expandir conformance runtime, observabilidade, memória curada e inteligência de release para atingir plenamente a visão de deep agent operations spec-governed.**

---

## 11. CHANGELOG DESTA REVISÃO

### Principais mudanças em relação ao documento anterior

- reposicionamento do texto: de roadmap integral para relatório de progresso real
- substituição do eixo ilustrativo por evidências do domínio `stable-execution`
- reclassificação do roadmap com foco em implementado/parcial/planejado
- rebaixamento explícito de claims ainda não comprovadas em conformance, observability e release intelligence
- incorporação da suíte de regressão e do problema conhecido de roteamento como parte do diagnóstico técnico

---

**Documento Versionado**: v4.0  
**Base de Revisão**: estado atual do repositório inspecionado em 2026-04-03  
**Próxima Revisão Recomendada**: após evidência concreta de conformance engine, policy enforcement runtime e release intelligence
