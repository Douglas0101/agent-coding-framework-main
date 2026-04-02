# FRAMEWORK DE DEEP AGENTS ORIENTADO A SPEC DRIVEN DEVELOPMENT
## Plano de Evolução Arquitetural - v3.0

---

## 1. VISÃO ESTRATÉGICA

### 1.1 Proposta de Valor
Transformar o repositório de um **template de agent coding** em uma **plataforma de deep agent operations orientada a especificações executáveis**, onde a spec é o artefato primário e código, testes, DAGs, validações, policies e observabilidade são derivados, verificados e reconciliados continuamente.

### 1.2 Tese Arquitetural
O problema central em sistemas com agentes não é apenas coordenação; é **desalinhamento entre intenção, execução e evidência**. Em um modelo verdadeiramente spec-driven, a plataforma deve responder a cinco perguntas antes de escrever código ou disparar um agente:

1. **O que o sistema deve fazer?** → capability spec
2. **Sob quais restrições?** → policy spec, security spec, SLO spec
3. **Como o comportamento evolui no tempo?** → workflow/state spec
4. **Como validamos conformidade?** → verification spec
5. **Como detectamos drift entre spec, código e runtime?** → conformance + observability

### 1.3 Princípios Fundamentais
1. **Spec como Fonte da Verdade**: prompts, DAGs, contratos, testes e gates são derivados de specs versionadas
2. **Governança como Código**: policies executáveis, auditáveis e vinculadas à spec de domínio
3. **Contratos Tipados e Evolutivos**: handoffs entre agentes via schemas com compatibilidade semântica e regras explícitas de evolução
4. **Memória Orientada a Evidências**: aprendizado persistente só entra no sistema se puder ser rastreado a evidências verificáveis
5. **Execução Determinística sob Restrições**: DAGs com budgets, retries, invariantes e circuit breakers compilados a partir da spec
6. **Conformidade Contínua**: o sistema mede, em runtime, a distância entre comportamento observado e comportamento especificado
7. **Traceabilidade Bidirecional**: cada requisito deve apontar para código, testes, owners, decisões e sinais operacionais; cada artefato deve apontar de volta para a spec que o originou

---

## 2. O QUE MUDA COM SPEC DRIVEN DEVELOPMENT

### 2.1 De Prompt-First para Spec-First
No modelo atual, os agentes recebem instruções, executam tarefas e produzem artefatos. No modelo avançado de spec driven development, o fluxo correto é:

`intent -> canonical spec -> compiled execution plan -> generated validation artifacts -> runtime -> conformance feedback -> spec refinement`

Isso muda a função dos agentes:
- o agente deixa de “improvisar” a estrutura da solução
- a plataforma passa a **compilar** a solução a partir da spec
- decisões discricionárias do agente são reduzidas a áreas explicitamente permitidas pela spec
- o runtime deixa de confiar apenas em heurísticas e passa a exigir **proof-by-evidence**

### 2.2 A Pirâmide de Especificações
A plataforma deve tratar a spec como uma pilha de camadas complementares:

| Camada | Pergunta que responde | Exemplo de artefato |
|---|---|---|
| **Intent Spec** | Qual problema de negócio estamos resolvendo? | RFC, change request, product brief |
| **Capability Spec** | Quais capacidades o sistema precisa oferecer? | `capability.yaml` |
| **Behavior Spec** | Como o sistema se comporta em fluxos e estados? | state machine, workflow spec |
| **Contract Spec** | Quais são as interfaces e schemas válidos? | OpenAPI, JSON Schema, Protobuf |
| **Policy Spec** | Quais restrições são obrigatórias? | policy bundles, OPA/Rego, YAML |
| **SLO Spec** | Quais limites operacionais e de qualidade devem ser mantidos? | latency/error budget spec |
| **Verification Spec** | Como demonstrar que está correto? | test matrix, properties, model checks |
| **Release Spec** | Como mudar sem causar dano? | rollout spec, rollback spec |

### 2.3 Specs Executáveis
A evolução mais importante é abandonar specs apenas narrativas e adotar **specs executáveis**, contendo:
- invariantes formais
- pré-condições e pós-condições
- regras de compatibilidade
- state transitions válidas
- budgets máximos
- requisitos de evidência
- critérios de aceite verificáveis por máquina

---

## 3. ARQUITETURA DE 5 PLANOS

### 3.1 Spec Plane (Fonte da Verdade)
Responsabilidade: modelar intenção, comportamento, contratos, restrições, critérios de aceite e evolução.

**Componentes Core:**
- `spec-registry.ts`: registry central de specs e suas versões
- `spec-compiler.ts`: compila specs em DAGs, tests, gates e manifests
- `spec-diff.ts`: classifica mudanças como additive, compatible, risky ou breaking
- `spec-linker.ts`: mantém rastreabilidade entre requirement, code, test, owner e telemetry
- `conformance-engine.ts`: compara execução real contra spec vigente

**Modelo Canônico de Spec:**
```typescript
interface SystemSpec {
  spec_id: string;
  domain: string;
  version: string;
  status: 'draft' | 'proposed' | 'approved' | 'deprecated';
  intent: {
    objective: string;
    scope: string[];
    out_of_scope: string[];
    business_criticality: 'low' | 'medium' | 'high' | 'critical';
  };
  capabilities: CapabilitySpec[];
  behaviors: BehaviorSpec[];
  contracts: ContractSpec[];
  policies: PolicyRef[];
  slos: SLOSpec[];
  verification: VerificationSpec;
  release: ReleaseSpec;
  traceability: TraceLink[];
}
```

### 3.2 Control Plane (Governança & Orquestração)
Responsabilidade: compilar a execução a partir da spec, impor budgets, approvals, dependency rules e retries.

**Mudança-chave:** o DAG não é mais montado apenas pela tarefa textual; ele é **derivado do merge entre intent spec, behavior spec, policy spec e verification spec**.

**Metadados do Nó DAG Compilado:**
```typescript
interface TaskNode {
  task_id: string;
  derived_from_specs: string[];
  type: 'discovery' | 'analysis' | 'implementation' | 'validation' | 'synthesis' | 'release';
  inputs: Record<string, unknown>;
  dependencies: string[];
  write_scope: string[];
  invariants: string[];
  admissible_outputs: string[];
  retry_policy: {
    max_attempts: number;
    backoff: 'fixed' | 'exponential';
    circuit_breaker: boolean;
  };
  budget: {
    max_tokens: number;
    max_cost_usd: number;
    timeout_ms: number;
  };
  required_evidence: string[];
  required_approvals: string[];
  conformance_checks: string[];
  risk_level: 'low' | 'medium' | 'high' | 'critical';
}
```

### 3.3 Knowledge Plane (Memória & Contexto)
Responsabilidade: memória episódica, semântica, procedural e base de evidências; sempre vinculadas a specs e a resultados de conformidade.

**Regra nova:** memória persistida sem link para `spec_id`, `run_id` e `evidence_refs` não entra na base curada.

**Camadas de Memória:**

| Tipo | Função | Implementação | Critério de Persistência |
|---|---|---|---|
| **Episódica** | Histórico imutável de runs | Append-only ledger com checksum | Sempre persistida |
| **Semântica** | Fatos e padrões derivados | Vector store + knowledge graph | Só após validação |
| **Procedural** | Heurísticas e runbooks | ADRs, playbooks, templates | Curadoria obrigatória |
| **Conformance** | Drift entre spec e runtime | Conformance snapshots | Persistência obrigatória para incidentes |
| **Working** | Contexto de sessão | Sliding window/scratchpad | Descartável |

### 3.4 Execution Plane (Agentes & Ferramentas)
Responsabilidade: execução de agentes especializados, ferramentas, adapters e sandboxes, sempre sob orçamento e conformance checks.

**Agentes Especializados:**

| Agente | Responsabilidade | Gatilho de Ativação |
|---|---|---|
| **orchestrator** | Coordenação do DAG compilado | Início de toda run |
| **spec-architect** | Estruturar e normalizar specs | Início de mudanças complexas |
| **spec-compiler** | Compilar spec em DAG, testes e gates | Após aprovação da spec |
| **policy-guardian** | Avaliar conformidade com policies | Antes de cada nó crítico |
| **impact-analyst** | Medir blast radius | Mudanças em contratos e dados |
| **contract-verifier** | Validar compatibilidade de schemas | Handoffs, APIs, eventos |
| **migration-guardian** | Proteger alterações destrutivas | Mudanças em schema/modelo |
| **conformance-auditor** | Validar comportamento observado vs especificado | Pós-execução e pós-deploy |
| **drift-detector** | Detectar drift entre spec, código e runtime | Runtime contínuo |
| **release-manager** | Planejar rollout e rollback | Preparação de deploy |
| **memory-curator** | Persistir aprendizado confiável | Final de run bem-sucedida |
| **incident-simulator** | Analisar contrafactuais e falhas | Mudanças de alto risco |
| **autocoder** | Implementar código aderente à spec | Após aprovação de escopo |
| **reviewer** | Revisão técnica estruturada | Após implementação |
| **tester** | Validar conformidade multi-stack | Pre-merge e pre-release |

### 3.5 Observability Plane (Telemetria & Analytics)
Responsabilidade: telemetria operacional e telemetria de conformidade.

**Nova orientação:** observabilidade deixa de medir apenas latência e custo; passa a medir **aderência à spec**.

**Métricas Essenciais:**
```typescript
interface AgentMetrics {
  // Execução
  task_completion_rate: number;
  retry_burden: number;
  circuit_breaker_triggers: number;

  // Qualidade estrutural
  schema_validation_failures: number;
  conformance_failures: number;
  spec_drift_events: number;
  verifier_block_rate: number;

  // Custo & performance
  cost_per_successful_run: number;
  token_efficiency: number;
  latency_p95: number;

  // Governança
  approval_wait_time: number;
  policy_violations: number;
  escape_rate: number;

  // Spec-driven
  spec_coverage: number;
  traceability_completeness: number;
  runtime_to_spec_alignment: number;
  evidence_sufficiency_score: number;
}
```

---

## 4. MODELO AVANÇADO DE SPEC

### 4.1 Capability Spec
Define o que a plataforma deve ser capaz de fazer, independentemente da implementação.

```yaml
spec_id: capability.payment-authorization
version: 1.2.0
status: approved
objective: autorizar pagamentos com avaliação de risco em até 250ms
inputs:
  - payment_request
  - customer_context
outputs:
  - authorization_decision
  - audit_record
invariants:
  - toda decisão deve gerar trilha auditável
  - requisições idempotentes devem produzir o mesmo resultado lógico
non_functional:
  latency_p95_ms: 250
  availability_slo: 99.95
```

### 4.2 Behavior Spec
Especifica fluxos, estados válidos e transições permitidas. O ideal é modelar fluxos críticos como **máquinas de estado tipadas**.

```yaml
behavior_id: payment.authorization-flow
states:
  - received
  - validated
  - risk_scored
  - authorized
  - declined
  - failed
transitions:
  - from: received
    to: validated
    guard: request_schema_valid == true
  - from: validated
    to: risk_scored
    guard: customer_context_available == true
  - from: risk_scored
    to: authorized
    guard: risk_score < 0.72
  - from: risk_scored
    to: declined
    guard: risk_score >= 0.72
forbidden:
  - from: received
    to: authorized
```

### 4.3 Verification Spec
Aqui entram os conceitos mais avançados de spec-driven validation:
- **property-based testing** derivado de invariantes
- **model-based testing** derivado da máquina de estados
- **contract testing** derivado de schemas e compatibilidade
- **golden traces** para fluxos críticos
- **negative specs** para provar o que o sistema não pode fazer
- **metamorphic tests** quando não há oráculo simples

```yaml
verification:
  acceptance_criteria:
    - toda decisão deve possuir evidence_ref resolvível
    - nenhuma transição proibida pode aparecer em trace
  properties:
    - name: idempotency
      statement: mesma chave idempotente implica mesmo outcome lógico
    - name: auditability
      statement: toda autorização ou recusa gera ledger entry
  model_checks:
    - no_dead_end_before_terminal_state
    - forbidden_transitions_never_observed
  generated_tests:
    - contract_tests
    - property_tests
    - state_transition_tests
    - replay_tests
```

### 4.4 Policy Spec
Policies deixam de ser anexos operacionais e passam a integrar a spec como restrições de execução.

```yaml
policy_bundle: payments-critical
rules:
  - id: require-dual-approval
    when:
      risk_level: [high, critical]
      change_surface: [api, data, auth]
    action: require_approval
    approvers: [security-team, tech-lead]

  - id: forbid-unbounded-retries
    when:
      node_type: implementation
    action: require
    constraint:
      retry_policy.max_attempts_lte: 3

  - id: require-rollback-plan
    when:
      change_kind: destructive_migration
    action: require_evidence
    evidence_types: [rollback_plan, dry_run_result]
```

### 4.5 Release Spec
Em ambientes com agentes, release precisa ser especificado com a mesma seriedade do contrato.

```yaml
release:
  strategy: canary
  stages:
    - percentage: 1
      bake_minutes: 15
    - percentage: 10
      bake_minutes: 30
    - percentage: 50
      bake_minutes: 60
  rollback:
    trigger_conditions:
      - latency_p95_ms > 250
      - error_rate > 0.5
      - runtime_to_spec_alignment < 0.98
```

---

## 5. CONTRATOS FORMAIS ENTRE AGENTES

### 5.1 Schema Registry
Local: `.opencode/lib/artifact-schemas/`

**Schemas Versionados:**
- `review-result.schema.json`
- `test-result.schema.json`
- `evidence-report.schema.json`
- `impact-report.schema.json`
- `release-plan.schema.json`
- `synthesis-package.schema.json`
- `approval-request.schema.json`
- `run-manifest.schema.json`
- `conformance-report.schema.json`
- `spec-diff.schema.json`
- `traceability-link.schema.json`

### 5.2 Regra de Handoff
Nenhum handoff entre agentes ocorre sem:
1. validação do schema contra o registry
2. `schema_version` explícito
3. `spec_id` e `spec_version` associados
4. `producer_agent` identificado
5. `run_id` e timestamp
6. `evidence_refs` resolvíveis
7. `risk_level` classificado
8. `compatibility_assessment` quando houver evolução de contrato
9. `trace_links` para requirement, código, testes e owners

### 5.3 Compatibilidade de Contratos
Toda mudança deve ser classificada automaticamente em uma destas categorias:
- **additive-compatible**
- **behavior-compatible**
- **risky-compatible**
- **breaking**

**Regra operacional:** breaking change só pode avançar com approval explícito, plano de migração, janela de rollout e consumidores identificados.

**Exemplo de Artifact com vínculo à spec:**
```json
{
  "schema_version": "1.1.0",
  "artifact_type": "impact-report",
  "producer_agent": "impact-analyst",
  "spec_id": "capability.payment-authorization",
  "spec_version": "1.2.0",
  "run_id": "run_2026_04_02_001",
  "timestamp": "2026-04-02T14:32:00Z",
  "compatibility_assessment": "risky-compatible",
  "payload": {
    "impact_scope": {
      "services": ["payments-api", "risk-worker"],
      "contracts": ["openapi/payments.yaml"],
      "datastores": ["billing.transactions"],
      "slos": ["latency_p95", "error_rate"]
    },
    "risk_level": "high",
    "blast_radius": {
      "files": 12,
      "apis": 3,
      "consumers": 7,
      "databases": 2
    }
  },
  "trace_links": [
    "trace://requirement/RQ-102",
    "trace://code/src/payments/service.ts",
    "trace://test/tests/contracts/payments.spec.ts"
  ],
  "evidence_refs": [
    "evidence://repo/payments/service.ts#L120-L188",
    "evidence://openapi/payments.yaml#charge-create",
    "evidence://tests/contracts/payments-compatibility.json",
    "evidence://memory/episodes/run_2026_03_15_042.jsonl"
  ],
  "checksum": "sha256:abc123..."
}
```

---

## 6. TRACEABILIDADE BIDIRECIONAL

### 6.1 Matriz de Traceabilidade
Um framework maduro de spec-driven development precisa garantir a cadeia completa:

`requirement -> spec -> DAG node -> code change -> test case -> evidence -> runtime trace -> SLO impact`

### 6.2 Trace Links Obrigatórios
Cada item crítico deve possuir links mínimos:
- requirement / ticket / RFC de origem
- spec_id e versão vigente
- arquivos alterados
- testes gerados ou selecionados
- evidências produzidas
- spans/trace IDs em runtime
- owner técnico e owner de domínio

### 6.3 Benefício Operacional
Quando ocorrer incidente, a investigação deixa de começar no log; começa no **gap entre spec e observação**. Isso reduz drasticamente MTTR em ambientes complexos.

---

## 7. CONFORMANCE ENGINE E DETECÇÃO DE DRIFT

### 7.1 Tipos de Drift
A plataforma deve medir quatro drifts distintos:

| Tipo de Drift | Descrição | Exemplo |
|---|---|---|
| **Spec-to-Code** | Código não implementa o comportamento especificado | endpoint ignora regra de validação |
| **Code-to-Test** | Testes não cobrem a mudança relevante | novo branch sem caso negativo |
| **Spec-to-Runtime** | Sistema em produção viola invariantes | transição proibida observada |
| **Intent-to-Spec** | A própria spec não representa mais a necessidade de negócio | regra desatualizada após mudança regulatória |

### 7.2 Conformance Report
Após cada run e após cada release, gerar `conformance-report` com:
- spec version avaliada
- asserts aprovados e reprovados
- transições observadas vs previstas
- coverage por capability
- evidência faltante
- score de aderência por domínio

### 7.3 Golden Paths e Golden Traces
Para os fluxos mais críticos, manter:
- **golden path specs**: fluxos ideais e suportados
- **golden traces**: execuções de referência para replay e regressão

Esses artefatos são especialmente úteis para verificar regressões silenciosas de agentes e do runtime.

---

## 8. POLICY ENGINE COMO COMPILADOR DE RESTRIÇÕES

### 8.1 Policy-as-Code
Policies definidas em `.opencode/policies/` e resolvidas no momento da compilação da spec.

```yaml
version: "2.0.0"
policies:
  - name: "critical-path-protection"
    scope:
      paths: ["/auth/**", "/billing/**", "/security/**"]
      change_surface: ["api", "data", "runtime"]
    rules:
      - type: "require_approval"
        approvers: ["security-team", "tech-lead"]
        conditions:
          risk_level: ["high", "critical"]
      - type: "require_evidence"
        evidence_types: ["security_scan", "dependency_check", "rollback_plan"]
      - type: "require_conformance_floor"
        min_runtime_to_spec_alignment: 0.99
      - type: "block_direct_write"
        message: "Alterações em paths críticos exigem spec aprovada, DAG compilado e simulação"
```

### 8.2 Runtime Enforcement em 4 Camadas
O `policy-enforcer.ts` passa a operar assim:
1. **Spec-time**: valida a própria spec antes de aprová-la
2. **Pre-flight**: valida o DAG compilado antes da execução
3. **In-flight**: monitora budget, timeout, transições e restrições
4. **Post-flight**: valida outputs, evidências e conformidade

---

## 9. ROADMAP DE IMPLEMENTAÇÃO SEQUENCIAL

### FASE 1: SPEC FOUNDATION (Semanas 1-6)
**Objetivo**: tornar specs o artefato primário.

#### Sprint 1.1: Canonical Spec Model & Registry (Semanas 1-2)
**Entregáveis:**
- [ ] `spec-registry.ts` com versionamento semântico
- [ ] `capability.schema.json`, `behavior.schema.json`, `verification.schema.json`, `release.schema.json`
- [ ] Pasta `specs/` com exemplos por domínio
- [ ] Workflow de aprovação de spec

**Critérios de Aceitação:**
- mudança sem `spec_id` não inicia DAG
- spec inválida é rejeitada em <100ms
- toda spec aprovada recebe manifest de rastreabilidade

#### Sprint 1.2: Spec Compiler (Semanas 3-4)
**Entregáveis:**
- [ ] `spec-compiler.ts`
- [ ] geração automática de DAG a partir de behavior + policy + verification specs
- [ ] geração de matriz de testes e evidências requeridas
- [ ] `spec-diff.ts` com classificação additive/compatible/breaking

**Critérios de Aceitação:**
- alteração de contrato gera diff classificado automaticamente
- mudança breaking exige gate humano
- DAG compilado lista invariantes e checks por nó

#### Sprint 1.3: Traceability Backbone (Semanas 5-6)
**Entregáveis:**
- [ ] `traceability-link.schema.json`
- [ ] `spec-linker.ts`
- [ ] ligação requirement -> code -> test -> runtime trace
- [ ] score de completude de rastreabilidade por run

**Critérios de Aceitação:**
- toda mudança crítica aponta para spec e owner
- toda run gera manifest com trace links mínimos
- ausência de trace link bloqueia release crítica

### FASE 2: GOVERNED EXECUTION (Semanas 7-12)
**Objetivo**: compilar execução e governança a partir da spec.

#### Sprint 2.1: Policy Engine & Approval Gates (Semanas 7-8)
**Entregáveis:**
- [ ] `policy-enforcer.ts` com enforcement spec-time, pre-flight, in-flight e post-flight
- [ ] `approval-gate.ts`
- [ ] bundles de policy por domínio
- [ ] floors mínimos de conformance

**Critérios de Aceitação:**
- alteração em `/auth/**` sem spec aprovada é bloqueada
- run acima do budget é interrompida automaticamente
- policy violation gera trace e evidence no ledger

#### Sprint 2.2: DAG Executor Reentrante (Semanas 9-10)
**Entregáveis:**
- [ ] `build-task-graph.ts` derivado do spec compiler
- [ ] topological executor com paralelização segura
- [ ] retry policy, idempotency keys e checkpoints por nó
- [ ] resume seletivo por artifact validity

**Critérios de Aceitação:**
- DAG com 10 nós executa em ordem correta
- falha em nó dispara retry configurado
- sucesso parcial permite resume sem reexecução global

#### Sprint 2.3: Memory & Evidence Binding (Semanas 11-12)
**Entregáveis:**
- [ ] estrutura `memory/{episodes,semantic,conformance,evidence}/`
- [ ] `memory-curator.ts` com retenção por valor probatório
- [ ] evidências indexadas por `spec_id`, `run_id`, `artifact_type`
- [ ] semantic retrieval de runs similares e conformance failures históricas

**Critérios de Aceitação:**
- episode é persistido automaticamente após run
- evidência é endereçável por URI estável
- memória curada só aceita conteúdo com evidence_refs válidos

### FASE 3: ADVANCED VERIFICATION (Semanas 13-18)
**Objetivo**: provar conformidade, não apenas testar funcionalidade.

#### Sprint 3.1: Contract & Compatibility Verification (Semanas 13-14)
**Entregáveis:**
- [ ] `validate-agent-contract.ts`
- [ ] `detect-breaking-change.ts`
- [ ] checks de backward compatibility para OpenAPI, protobuf e eventos
- [ ] classificação automática de impacto para consumidores

**Critérios de Aceitação:**
- handoff sem `schema_version` é rejeitado
- breaking change exige major version e approval explícito
- consumidores afetados são listados no report de impacto

#### Sprint 3.2: Property-Based & Model-Based Testing (Semanas 15-16)
**Entregáveis:**
- [ ] geração de tests a partir de invariantes e state machines
- [ ] harness para property tests e transition tests
- [ ] golden traces para fluxos críticos
- [ ] negative spec suite

**Critérios de Aceitação:**
- transição proibida é detectada automaticamente
- invariant violation falha o pipeline
- regressão em golden trace bloqueia release

#### Sprint 3.3: Conformance Engine (Semanas 17-18)
**Entregáveis:**
- [ ] `conformance-engine.ts`
- [ ] `conformance-report.schema.json`
- [ ] score de aderência em runtime
- [ ] detecção de spec drift em produção

**Critérios de Aceitação:**
- release gera conformance report obrigatório
- drift acima do limiar abre incidente automaticamente
- runtime_to_spec_alignment é calculado por serviço e por capability

### FASE 4: OBSERVABILITY & RELEASE INTELLIGENCE (Semanas 19-24)
**Objetivo**: operar em produção com feedback contínuo sobre aderência à spec.

#### Sprint 4.1: Telemetria de Conformidade (Semanas 19-20)
**Entregáveis:**
- [ ] `trace-exporter.ts` com spans de decisão, guard e evidência
- [ ] `artifact-ledger.ts` imutável
- [ ] painéis de spec coverage, drift e evidence sufficiency
- [ ] alertas por invariant violation

#### Sprint 4.2: Release Management Spec-Driven (Semanas 21-22)
**Entregáveis:**
- [ ] `release-manager.md`
- [ ] `rollback-plan.md`
- [ ] canary validation vinculada a SLO spec e conformance floors
- [ ] integração com CI/CD para gates automáticos

#### Sprint 4.3: Production Pilot & Feedback Loop (Semanas 23-24)
**Entregáveis:**
- [ ] deploy em projeto piloto
- [ ] coleta de métricas de aderência à spec
- [ ] processo de refinement da spec pós-operação
- [ ] ajustes no compiler, policies e verification specs

---

## 10. RESPONSABILIDADES FINAIS DOS AGENTES

### 10.1 Matriz RACI

| Atividade | orchestrator | spec-architect | spec-compiler | policy-guardian | impact-analyst | contract-verifier | migration-guardian | conformance-auditor | drift-detector | release-manager | memory-curator | incident-simulator | autocoder | reviewer | tester |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Definir modelo de spec | C | R/A | C | C | I | C | I | I | I | I | I | I | I | I | I |
| Compilar DAG e gates | A | C | R | C | C | C | C | C | I | C | I | I | I | I | C |
| Validar policies | C | I | C | R/A | C | C | C | C | I | C | I | I | I | I | I |
| Analisar impacto | I | C | C | C | R/A | C | C | C | I | C | I | C | I | I | I |
| Validar contratos | I | C | C | C | C | R/A | C | C | I | C | I | I | C | C | I |
| Aprovar migrations | I | I | C | C | C | C | R/A | C | I | C | I | C | I | I | I |
| Auditar conformidade | I | I | C | C | C | C | C | R/A | C | C | I | C | I | I | C |
| Detectar drift | I | I | I | C | I | C | I | C | R/A | C | I | C | I | I | I |
| Planejar release | I | I | C | C | C | C | C | C | C | R/A | I | C | I | I | C |
| Curar memória | I | I | I | I | I | I | I | C | C | I | R/A | I | I | I | I |
| Simular incidentes | I | I | C | C | C | I | C | C | C | C | I | R/A | I | I | I |
| Implementar código | I | I | I | I | I | I | I | I | I | I | I | I | R/A | I | I |
| Revisar código | I | I | I | I | I | I | I | I | I | I | I | I | C | R/A | C |
| Validar testes | I | I | C | I | I | C | I | C | I | C | I | I | C | C | R/A |

*R = Responsible, A = Accountable, C = Consulted, I = Informed*

---

## 11. ESTRUTURA DE DIRETÓRIOS FINAL

```text
.
├── .opencode/
│   ├── agents/
│   │   ├── orchestrator.md
│   │   ├── spec-architect.md
│   │   ├── spec-compiler.md
│   │   ├── policy-guardian.md
│   │   ├── impact-analyst.md
│   │   ├── contract-verifier.md
│   │   ├── migration-guardian.md
│   │   ├── conformance-auditor.md
│   │   ├── drift-detector.md
│   │   ├── release-manager.md
│   │   ├── memory-curator.md
│   │   ├── incident-simulator.md
│   │   ├── autocoder.md
│   │   ├── reviewer.md
│   │   └── tester.md
│   ├── commands/
│   │   ├── plan-system.md
│   │   ├── compile-spec.md
│   │   ├── run-dag.md
│   │   ├── assess-impact.md
│   │   ├── verify-conformance.md
│   │   ├── validate-release.md
│   │   └── rollback-plan.md
│   ├── specs/
│   │   ├── capabilities/
│   │   ├── behaviors/
│   │   ├── contracts/
│   │   ├── policies/
│   │   ├── slos/
│   │   ├── verification/
│   │   └── release/
│   ├── tools/
│   │   ├── spec-registry.ts
│   │   ├── spec-compiler.ts
│   │   ├── spec-diff.ts
│   │   ├── spec-linker.ts
│   │   ├── analyze-system-impact.ts
│   │   ├── validate-agent-contract.ts
│   │   ├── detect-breaking-change.ts
│   │   ├── conformance-engine.ts
│   │   └── compute-blast-radius.ts
│   ├── plugins/
│   │   ├── policy-enforcer.ts
│   │   ├── trace-exporter.ts
│   │   ├── artifact-ledger.ts
│   │   └── approval-gate.ts
│   ├── lib/
│   │   ├── artifact-schemas/
│   │   ├── graph/
│   │   ├── memory/
│   │   ├── tracing/
│   │   ├── conformance/
│   │   ├── traceability/
│   │   └── adapters/
│   ├── manifests/
│   ├── ledger/
│   ├── evidence/
│   └── memory/
│       ├── episodes/
│       ├── semantic/
│       ├── conformance/
│       └── evidence/
├── docs/
│   ├── architecture/
│   ├── governance/
│   ├── operations/
│   ├── specs/
│   └── migration/
└── AGENTS.md
```

---

## 12. MÉTRICAS DE SUCESSO

### 12.1 KPIs Técnicos
| Métrica | Baseline (v2) | Target (6 meses) | Target (12 meses) |
|---|---:|---:|---:|
| Spec Coverage | 0% | 70% | 95% |
| Runtime-to-Spec Alignment | N/A | >97% | >99% |
| Traceability Completeness | <20% | >85% | >95% |
| Schema Validation Coverage | 0% | 85% | 100% |
| Breaking Changes Detectadas Pre-Merge | ? | >90% | >97% |
| Policy Enforcement Latency | N/A | <100ms | <50ms |
| Conformance Report Coverage | 0% | 80% | 100% |
| Escape Rate | ? | <5% | <2% |
| Cost per Successful Run | ? | -20% | -40% |

### 12.2 KPIs de Governança
| Métrica | Target |
|---|---:|
| % runs com evidence completa | >95% |
| % mudanças críticas com rollback plan | 100% |
| % releases com canário guiado por spec | >85% |
| Tempo médio de aprovação humana | <4h |
| % incidentes com trace completo até spec de origem | >90% |

### 12.3 KPIs de Conformidade
| Métrica | Target |
|---|---:|
| Forbidden transitions observadas em produção | 0 |
| Drift crítico aberto por mais de 24h | 0 |
| Evidence sufficiency score médio | >0.95 |
| % specs com tests gerados automaticamente | >80% |

---

## 13. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Overhead de modelagem inicial | Média | Alto | começar por domínios críticos e specs mínimas, não por cobertura total |
| Specs virarem documentação morta | Alta | Alto | tornar spec gate obrigatório de compile, test e release |
| Falso senso de segurança com schemas sem comportamento | Média | Alto | complementar contract specs com behavior specs e properties |
| Complexidade do compiler | Média | Alto | separar compiler em fases determinísticas e outputs auditáveis |
| Drift não detectado em runtime | Média | Alto | golden traces, invariant checks e conformance alerts |
| Memória acumular ruído | Média | Médio | curadoria baseada em evidência e score de confiabilidade |
| Resistência cultural à disciplina de specs | Alta | Médio | mostrar ganho em incident response, compatibilidade e velocidade segura |

---

## 14. CONCLUSÃO

Este plano evolui o framework de um modelo **runtime-governed** para um modelo **spec-governed**, no qual:

1. **Specs são o artefato primário**
2. **DAGs, testes, gates e release plans são compilados a partir da spec**
3. **Compatibilidade e conformidade são verificadas continuamente**
4. **Memória só persiste conhecimento apoiado por evidência**
5. **Observabilidade mede aderência à intenção, e não apenas telemetria operacional**

O resultado é uma plataforma de deep agents capaz de operar software complexo em larga escala com **governança executável, rastreabilidade ponta a ponta, verificação forte e detecção contínua de drift**.

---

**Documento Versionado**: v3.0  
**Data**: 2026-04-02  
**Próxima Revisão**: 2026-05-02
