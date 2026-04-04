# Agent Orchestration Framework

**Status:** PRD Framework 2.0 — Governança Operacional por Contrato (Completo)  
**Architecture:** Core domain-agnostic + Mode Contracts + Mode Skills + Domain Packs + Runtime Governado  
**Reference:** [CONSTITUTION_emendada.md](docs/CONSTITUTION_emendada.md) | [PRD Framework 2.0](docs/PRD_Framework_2_0_Executivo.md)

---

## Visão Geral

O **Agent Orchestration Framework** é uma plataforma contratual governada, extensível e observável para orquestração multi-agente. O **Core** é domain-agnostic — não contém lógica de negócio específica de domínio vertical.

### O que é o Framework 2.0

A versão 2.0 transforma o framework de **routing + guardrails** para **contratos operacionais por modo com enforcement, budget, memória e handoff economics**. São **302 testes passando**, **10 skills governadas**, **7 módulos de runtime** e **8 KPIs rastreados**.

### Componentes Principais

| Componente | Descrição |
|---|---|
| **Core domain-agnostic** | Protocolos de orquestração, handoff, verificação e síntese — sem lógica de domínio |
| **Agent Mode Contracts** | 4 modos operacionais (explore, reviewer, orchestrator, autocoder) com budget, memória e semântica formal |
| **Mode Skills** | 10 skills governadas por contrato, budget e evidência, ativadas contextualmente por modo |
| **Domain Packs** | Extensões contratuais opcionais — software-engineering (ativo), ml-ai e medical-imaging (experimentais), ioi-gold-compiler (experimental) |
| **Runtime Governado** | 7 módulos de enforcement: contract-verifier, policy-enforcer, approval-gate, conformance-tracker, observability, replay-engine, metrics-collector |

### Propósito

1. **Execução Estável**: Verificação de conformidade, fail-fast, sem fallback silencioso
2. **Contratos Formais**: Handoff entre agentes com validação estrutural e compressão seletiva
3. **Skills Governadas**: Novas capacidades via contratos com budget, evidência e testes obrigatórios
4. **Observabilidade**: Artifact ledger, evidence store, handoff history e KPIs por modo
5. **Neutralidade**: Core independente de domínio vertical

---

## Arquitetura do Sistema

### Modelo: Core + Mode Contracts + Mode Skills + Domain Packs + Runtime

```
agent-orchestration-framework/
├── docs/                          # ÚNICA superfície pública documental
│   ├── CONSTITUTION_emendada.md
│   ├── PRD_Framework_2_0_Executivo.md
│   ├── PRD_desverticalizacao_framework.md
│   ├── PRD_Operacional_Arquitetura_Multiagente_Orientada_a_Contratos.md
│   ├── analise_sdd_token_economics.md
│   ├── ADOPTION_RUNBOOK.md
│   ├── GIT-FLOW-GUIDE.md
│   └── README.md
├── .internal/                     # TODA a estrutura operacional
│   ├── specs/core/                # Core domain-agnostic (nível 0)
│   │   ├── orchestration-contract.yaml
│   │   ├── agent-mode-contract.yaml
│   │   ├── memory-model.yaml
│   │   └── planner-subcontract.yaml
│   ├── specs/modes/               # Contratos por modo (nível 1)
│   │   ├── explore.yaml           (v1.2.0 — 4 skills)
│   │   ├── reviewer.yaml          (v1.2.0 — 5 skills)
│   │   ├── orchestrator.yaml      (v1.2.0 — 6 skills)
│   │   └── autocoder.yaml         (v1.1.0 — execution-pure)
│   ├── runtime/                   # Runtime governado (7 módulos)
│   │   ├── contract_verifier.py
│   │   ├── policy_enforcer.py
│   │   ├── approval_gate.py
│   │   ├── conformance_tracker.py
│   │   ├── observability.py
│   │   ├── replay_engine.py
│   │   ├── budget_conservation.py
│   │   ├── metrics_collector.py
│   │   └── tests/                 # 107 testes de runtime
│   ├── skills/                    # Skills v2 por modo (10 skills)
│   │   ├── repo_topology_map.py
│   │   ├── dependency_surface.py
│   │   ├── change_impact_deep.py
│   │   ├── contract_drift_audit.py
│   │   ├── policy_gate_plus.py
│   │   ├── boundary_leak_detector.py
│   │   ├── explicit_planner.py
│   │   ├── budget_allocator.py
│   │   ├── handoff_compressor.py
│   │   ├── memory_curator_v2.py
│   │   └── tests/                 # 75 testes de skills
│   ├── domains/                   # Domain Packs
│   │   ├── software-engineering/
│   │   ├── ml-ai/
│   │   └── medical-imaging/
│   ├── registry/                  # Extension Registry
│   ├── adr/                       # Decisões arquiteturais (5 ADRs)
│   ├── templates/                 # Templates para novos packs
│   ├── scripts/                   # Scripts operacionais
│   ├── tests/                     # Suite de conformidade (120 testes)
│   └── artifacts/                 # Artefatos de execução
├── .opencode/                     # Configuração OpenCode (interno)
├── README.md                      # Interface pública
├── AGENTS.md                      # Regras de swarm
└── opencode.json                  # Config pública sanitizada
```

### Camadas Arquiteturais

```
Core domain-agnostic (Nível 0)
  └── Mode Contracts (Nível 1) — explore, reviewer, orchestrator, autocoder
        └── Mode Skills (Nível 2) — 10 skills governadas por contrato
              └── Domain Packs (Nível 3) — software-engineering, ml-ai, medical-imaging
                    └── Runtime Governado ( enforcement )
                          ├── contract-verifier (12 regras CV-001 a CV-012)
                          ├── policy-enforcer (SEC, POL, OWASP)
                          ├── approval-gate (risk classification)
                          ├── conformance-tracker (trace spans)
                          ├── observability-hub (ledger + evidence + handoff)
                          ├── replay-engine (replay + classification + golden traces)
                          └── metrics-collector + kpi-tracker (8 métricas)
```

### Fluxo de Execução

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Input    │────▶│   Explorer   │────▶│   Evidence   │────▶│  Reviewer   │
│  (Command) │     │   (Explore)   │     │  (Collect)   │     │  (Analyze)  │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                          │                                         │
                    Skills:                                   Skills:
                    • repo_topology_map                       • conformance_audit
                    • dependency_surface                      • policy_gate
                    • change_impact_deep                      • policy_gate_plus
                                                              • contract_drift_audit
                                                              • boundary_leak_detector
                          │                                         │
                          ▼                                         ▼
                    ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
                    │   Planner    │────▶│   Verifier   │────▶│   Gap       │
                    │ (explicit)   │     │   (Gate)     │     │  (Identify) │
                    └──────────────┘     └──────────────┘     └─────────────┘
                          │                                         │
                    Skills:                                   Skills:
                    • budget_allocator                        • impact_analysis
                    • handoff_compressor
                    • memory_curator_v2
                    • spec_architecture
                    • spec_compilation
                          │
                          ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  Synthesizer │────▶│   Output    │
                    │   (Write)    │     │  (Artifact) │
                    └──────────────┘     └─────────────┘
```

---

## Modo Agente: Seleção via Tab

No TUI do OpenCode, a tecla **Tab** alterna ciclicamente entre os agentes configurados (`agent_cycle`). Cada agente está vinculado a um **Agent Mode Contract** que define seu comportamento operacional:

| Tecla | Ação | Efeito |
|-------|------|--------|
| `Tab` | Cycle agent (forward) | Alterna: autocoder → general → explore → reviewer → orchestrator → autocoder |
| `Shift+Tab` | Cycle agent (reverse) | Alterna na ordem inversa |

### Comportamento por Modo

| Agente | Modo Contract | Versão | Satisficing | Budget | Skills |
|--------|---------------|--------|-------------|--------|--------|
| `autocoder` | `modes/autocoder.yaml` | 1.1.0 | BALANCED | 72k tokens | 0 (execution-pure) |
| `general` | N/A (fallback) | — | BALANCED | — | — |
| `explore` | `modes/explore.yaml` | 1.2.0 | BALANCED | 36k tokens | 4 |
| `reviewer` | `modes/reviewer.yaml` | 1.2.0 | DEEP | 52k tokens | 5 |
| `orchestrator` | `modes/orchestrator.yaml` | 1.2.0 | BALANCED | 68k tokens | 6 |

### Skills por Modo (Framework 2.0)

Cada skill possui contrato formal com: modo-alvo, ativação, input/output, budget share, política de evidência, testes de regressão e justificativa de por que não pertence ao Core ou a um Domain Pack.

#### Explore (4 skills — budget total: 0.75)

| Skill | Budget | Verifier | Ativação |
|-------|--------|----------|----------|
| `impact_analysis` | 0.15 | false | Automática em mudanças de código |
| `repo_topology_map` | 0.20 | false | Exploração de codebase |
| `dependency_surface` | 0.20 | false | Análise de dependências |
| `change_impact_deep` | 0.20 | true | Condicional (após dependency_surface) |

#### Reviewer (5 skills — budget total: 0.80)

| Skill | Budget | Verifier | Ativação |
|-------|--------|----------|----------|
| `conformance_audit` | 0.15 | true | Arquivos controlados por specs |
| `policy_gate` | 0.10 | true | Obrigatória antes de handoff |
| `contract_drift_audit` | 0.20 | true | Mudanças em contratos/configs |
| `policy_gate_plus` | 0.20 | true | Condicional (após drift detection) |
| `boundary_leak_detector` | 0.15 | true | Mudanças em docs/config pública |

#### Orchestrator (6 skills — budget total: 0.70)

| Skill | Budget | Verifier | Ativação |
|-------|--------|----------|----------|
| `explicit_planner` | 0.15 | true | Workflows multi-step |
| `budget_allocator` | 0.10 | true | Após planner produz plano |
| `handoff_compressor` | 0.10 | false | Antes de cada handoff |
| `memory_curator_v2` | 0.10 | false | Contexto > 60% ou pré-handoff |
| `spec_architecture` | 0.15 | true | Novas specs necessárias |
| `spec_compilation` | 0.10 | true | Após spec_architecture |

> **Princípio:** 4 modos no Tab cycling. O `autocoder` é execution-puro — sem skills analíticas.

---

## Runtime Governado

O runtime incorpora 7 módulos operacionais que operam sobre os contratos de modo existentes:

### Contract Verifier

Valida contratos de modo contra schema e invariantes. 12 regras (CV-001 a CV-012):

| Regra | Descrição |
|-------|-----------|
| CV-001 | Seções obrigatórias presentes |
| CV-002 | Metadata completo (name, version, parent) |
| CV-003 | Budget positivo e coerente |
| CV-004 | Memory tiers válidos |
| CV-005 | Satisficing mode válido |
| CV-006 | Handoff targets existem |
| CV-007 | Error policy válido |
| CV-008 | Tools allowlist/denylist disjuntos |
| CV-009 | Retry max 0-3 |
| CV-010 | Skills válidas com budget ≤ 1.0 |
| CV-011 | Handoff budget ≤ context budget |
| CV-012 | Tools disjuntos |

### Policy Enforcer

Scanner de segurança com 3 categorias:

| Categoria | Regras | Descrição |
|---|---|---|
| **Secrets** | SEC-001 a SEC-008 | API keys, passwords, tokens, AWS keys, private keys, GitHub tokens |
| **Forbidden** | POL-001 a POL-006 | eval/exec, os.system, shell=True, dynamic import, pickle, unsafe yaml |
| **OWASP** | OWASP-001 a OWASP-004 | SQL injection, XSS, SSRF, injection patterns |

### Approval Gate

Gate de aprovação com classificação de risco por mudança:

| Fator de Risco | Nível | Aprovadores |
|---|---|---|
| Mudança em contrato core | critical | 2 |
| Mudança em API pública | high | 2 |
| Padrão de segurança detectado | critical | 2 |
| Mudança em config de routing | high | 2 |

### Conformance Tracker

Tracking de conformidade por execução com trace spans e relatório estruturado. Produz registros em `.internal/artifacts/conformance/`.

### Observability Hub

Combina 3 componentes:

| Componente | Função | Diretório |
|---|---|---|
| Artifact Ledger | Registro imutável de artefatos | `.internal/artifacts/ledger/` |
| Evidence Store | Store de evidências com integridade | `.internal/artifacts/evidence/` |
| Handoff History | Histórico de handoffs com compressão | `.internal/artifacts/handoffs/` |

### Replay Engine

| Capacidade | Descrição |
|---|---|
| Replay de runs | Re-execução de runs críticas a partir de artifacts |
| Change Classifier | Classificação de risco por tipo de mudança |
| Golden Traces | Traces de referência para regressão |

### Budget Conservation

| Capacidade | Descrição |
|---|---|
| Hierarchical enforcement | `sum(children) <= parent` com overhead de 10% |
| Selective compression | 4 modos: none, summary, summary+refs, delta |
| On-demand rehydration | Reconstrução com ref_resolver |

---

## KPIs Rastreados

O framework coleta e agrega 8 métricas principais:

| KPI | Métrica | Implementação |
|---|---|---|
| Custo | tokens médios por run | `MetricsCollector` |
| Custo | custo por modo | Agregação por mode |
| Custo | custo por handoff | Tracking de handoff_tokens |
| Confiabilidade | taxa de compressão de contexto | `avg_compression_ratio` |
| Confiabilidade | taxa de verifier_pass | `verifier_pass_rate` |
| Confiabilidade | taxa de budget_exceeded | `budget_exceeded_rate` |
| Confiabilidade | taxa de partial_success | `partial_success_rate` |
| Confiabilidade | taxa de handoff inválido | `invalid_handoff_rate` |

---

## Decisões Arquiteturais (ADRs)

| ADR | Título | Decisão |
|---|---|---|
| [ADR-001](.internal/adr/ADR-001-taxonomia.md) | Taxonomia de Componentes | Core define protocolos, Skills estendem modos, Domain Packs implementam verticalmente |
| [ADR-002](.internal/adr/ADR-002-planner.md) | Planner Explícito | Planner como subcontrato formal do orchestrator, não agente independente |
| [ADR-003](.internal/adr/ADR-003-budget.md) | Budget Multidimensional | 7 dimensões: input/output/context tokens, retrieval chunks, iterations, handoffs, timeout |
| [ADR-004](.internal/adr/ADR-004-skill-contract.md) | Skill Contract | Toda skill declara: modo-alvo, ativação, input/output, budget, evidência, testes, justificativa |
| [ADR-005](.internal/adr/ADR-005-evidence-policy.md) | Evidence Policy | Evidências imutáveis, auditáveis, com integridade criptográfica e política de retenção |

---

## Domain Packs Disponíveis

Domain Packs são extensões contratuais opcionais. O Core permanece domain-agnostic e não depende de nenhum pack.

### Software Engineering Pack (Default — Active)

| Capacidade | Descrição |
|---|---|
| Code analysis | Exploração de codebase, identificação de padrões |
| Code review | Análise de segurança e qualidade |
| Code generation | Geração e refatoração de código |

### ML/AI Pack (Experimental — Opcional)

> Ilustrativo. Não requerido para operação do Core.

| Capacidade | Descrição |
|---|---|
| ML research | Pesquisa de técnicas e papers |
| ML engineering | Desenvolvimento de modelos |
| ML optimization | Otimização de hiperparâmetros |

### Medical Imaging Pack (Experimental — Opcional)

> Ilustrativo. Não requerido para operação do Core.

| Capacidade | Descrição |
|---|---|
| Radiologist assistant | Análise de imagens médicas |
| Specialist groups | Opacidades, anomalias, lesões, interação coração-pulmão |
| Medical reporter | Geração de laudos estruturados |

### IOI Gold Compiler Pack (Experimental — Opcional)

> Ilustrativo. Algoritmos avançados e competitive programming. Não requerido para operação do Core.

| Capacidade | Descrição |
|---|---|
| Algorithm selection | Mapeamento problema → algoritmo |
| Complexity certification | Certificados de complexidade |
| Stress test generation | Planos de validação sob carga |

> **Nota**: Domain Packs são opcionais. O Core permanece domain-agnostic.

---

## Execução Estável (Stable Execution)

### Garantias Implementadas

1. **Fail-fast de Configuração**: wrapper falha imediatamente quando config diverge nos campos críticos de routing
2. **Paridade de Configuração**: `opencode.json` e `.opencode/opencode.json` equivalentes nos campos críticos
3. **Invariantes**:
   - Sem retry ilimitado (`max_attempts ≤ 3`)
   - Sem fallback silencioso de agente
   - Gate obrigatório do verifier antes do synthesizer
   - Isolamento de write_scope entre workers paralelos
   - Prevenção de doom loops (`doom_loop: deny`)
   - Idempotência garantida
4. **Máquina de Estados**: 13 estados, 20 transições válidas, 7 proibidas
5. **Contrato de Handoff**: 12 campos obrigatórios, 6 regras de validação

### Testes de Conformidade

```bash
# Todos os testes (302 testes)
python -m pytest .internal/tests/ .internal/runtime/tests/ .internal/skills/tests/ -v

# Apenas mode contracts (120 testes)
python -m pytest .internal/tests/ -v

# Apenas runtime (107 testes)
python -m pytest .internal/runtime/tests/ -v

# Apenas skills (75 testes)
python -m pytest .internal/skills/tests/ -v

# Validação de budget
python .internal/scripts/validate_mode_budgets.py --fail-on-violation
```

---

## Integração CI/CD

### Workflows

| Workflow | Descrição | Gatilho |
|----------|-----------|---------|
| `routing-regression.yml` | Regressão de routing + paridade de config | Push/PR em config/spec |
| `mode-contract-compliance.yml` | Validação de contratos, budget, handoff | Push/PR em modes/specs |
| `constitutional-compliance.yml` | Invariantes constitucionais + drift | Push/PR em core/domains |
| `public-repo-guard.yml` | Scanner de padrões sensíveis (gitleaks) | Push/PR em main/master |
| `public-boundary-check.yml` | Verificação de boundary público | Push/PR em main/master |
| `budget-governance.yml` | Validação de budget por modo | Push/PR em modes |
| `config-contract-parity.yml` | Paridade de config crítica | Push/PR em config |
| `handoff-integrity.yml` | Integridade de contrato de handoff | Push/PR em specs |

> **Merge gate obrigatório**: configure `Routing Regression (Required)` e `Mode Contract Compliance (Required)` como *required*.

### Execução Local

```bash
# Testes completos (302 testes)
python -m pytest .internal/tests/ .internal/runtime/tests/ .internal/skills/tests/ -v

# Validação de budget
python .internal/scripts/validate_mode_budgets.py --fail-on-violation

# Verificação de boundary
.internal/scripts/check-public-boundary.sh

# Scanner de padrões sensíveis
python .internal/scripts/scan_sensitive_patterns.py

# Pre-commit hooks
pre-commit run --all-files
```

---

## Segurança e Compliance

### Política de Configuração Sanitizada

| Categoria | Permitido (público) | Proibido (público) |
|---|---|---|
| API keys | Placeholders (`${API_KEY}`) | Tokens reais |
| Endpoints | URLs públicas | Hosts internos/IPs RFC1918 |
| Chaves criptográficas | Placeholders | Blocos PEM privados |
| Config runtime | Interface e exemplos mínimos | IDs internos/estados de sessão |

### Pre-commit hooks

```bash
python -m pip install pre-commit detect-secrets
pre-commit install
pre-commit run --all-files
```

---

## Root Cause Corrigida: Routing do `/autocode`

O problema vinha de configs com schema inválido para o OpenCode v1.3.13. A solução usa schema suportado com top-level `agent` e `command`:

```bash
# Via wrapper (recomendado)
.internal/scripts/run-autocode.sh "sua tarefa aqui"

# Comando nativo
opencode run --command autocode "sua tarefa aqui"
```

---

## Requisitos do Sistema

- **CLI**: OpenCode
- **Python**: 3.10+ (para testes e scripts)
- **Ferramentas**: Git, pre-commit

---

## Configuração de IDE

### JetBrains (IntelliJ/PyCharm)

1. Importe o projeto normalmente
2. **Não** adicione arquivos de `.idea/` ao commit
3. Valide com `git status --short` antes de abrir PR

### VS Code / Neovim

O projeto inclui `.editorconfig` aplicado automaticamente.

---

## Public vs Internal Artifacts

Only `docs/` is the public documentary surface. All operational code, contracts, and runtime state live in `.internal/`. This repository is intended for **private repository only** use — do not expose `.internal/` contents publicly.

| Surface | Allowed | Prohibited |
|---|---|---|
| `docs/` | Sanitized PRDs, constitutions, runbooks | Internal specs, contracts, evidence |
| `README.md` | Architecture overview, setup guide | Routing details, internal endpoints |
| `.internal/` | Full operational structure | Must never be published |

---

## Contribuindo

### Fluxo de Trabalho

1. **Fork** o repositório
2. **Crie** uma branch (`feature/nova-feature`)
3. **Execute** testes: `python -m pytest .internal/tests/ .internal/runtime/tests/ .internal/skills/tests/ -v`
4. **Abra** um PR com descrição detalhada

### Convenções de Commit

```
<tipo>(<escopo>): <descrição>
```

Exemplos:
- `feat(explore): adicionar skill dependency_surface`
- `fix(runtime): corrigir budget conservation overflow`
- `docs(readme): atualizar seção de skills`

---

## Licença

**Proprietary — All Rights Reserved**

---

## Referências

- [OpenCode Documentation](https://opencode.ai/docs)
- [AGENTS.md](./AGENTS.md) — Regras nativas do swarm
- [.internal/MANIFEST.md](./.internal/MANIFEST.md) — Manifesto de interconectividade
- [docs/README.md](./docs/README.md) — Documentação adicional
- [docs/PRD_Framework_2_0_Executivo.md](./docs/PRD_Framework_2_0_Executivo.md) — PRD Framework 2.0
- [docs/CONSTITUTION_emendada.md](./docs/CONSTITUTION_emendada.md) — Constituição emendada
- [docs/analise_sdd_token_economics.md](./docs/analise_sdd_token_economics.md) — Análise de token economics
