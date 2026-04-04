# Agent Orchestration Framework

**Status:** Agent Mode Contracts — Governança Operacional por Contrato  
**Architecture:** Spec-Driven Architecture (SDA) + Agent Mode Contracts  
**Reference:** [CONSTITUTION_emendada.md](docs/CONSTITUTION_emendada.md)

---

## Visão Geral

O **Agent Orchestration Framework** é uma infraestrutura de orquestração multi-agente de propósito geral. O **Core** é domain-agnostic — não contém lógica de negócio específica de ML, Medical, Finance ou outros domínios verticais.

O framework combina:
- **Core de Orquestração**: Gramática de execução, verificação, síntese e handoff
- **Agent Mode Contracts**: Governança contratual por modo operacional com budget, memória e semântica formal
- **Domain Packs**: Extensões contratuais que fornecem capacidades específicas de domínio
- **Extension Registry**: Catálogo de packs disponíveis para ativação

### Propósito

Este framework foi projetado para automatizar orquestração de agentes em qualquer domínio computacional:

1. **Execução Estável**: Verificação de conformidade, fail-fast de configuração
2. **Contratos Formais**: Handoff entre agentes com validação estrutural
3. **Extensibilidade**: Novas capacidades via Domain Packs registrados
4. **Neutralidade**: Core independente de domínio vertical

---

## Arquitetura do Sistema

### Modelo: Core Domain-Agnostic + Domain Packs

```
agent-orchestration-framework/
├── docs/                  # ÚNICA superfície pública documental
│   ├── CONSTITUTION_emendada.md
│   ├── PRD_desverticalizacao_framework.md
│   ├── ADOPTION_RUNBOOK.md
│   └── README.md
├── .internal/             # TODA a estrutura operacional
│   ├── specs/core/           # Core domain-agnostic (nível 0)
│   ├── domains/              # Domain Packs (extensões contratuais)
│   ├── registry/             # Extension Registry
│   ├── templates/            # Templates para novos packs
│   ├── scripts/              # Scripts operacionais
│   ├── tests/                # Suite de testes
│   └── artifacts/            # Artefatos de execução
├── .opencode/              # Configuração OpenCode (interno)
├── .codex/                 # Orquestração multi-agente (interno)
├── .agent/                 # Skills operacionais (interno)
├── README.md               # Interface pública
├── AGENTS.md               # Regras de swarm
└── opencode.json           # Config pública sanitizada
```

### Camadas Arquiteturais

1. **Core (Nível 0)**: Gramática de orquestração — interfaces, protocolos, invariantes
2. **Agent Mode Contracts (Nível 1)**: Governança operacional por modo — missão, budget, memória, handoff
3. **Domain Packs**: Semântica de domínio implementada como extensões contratuais
4. **Runtime**: Execução concreta via OpenCode/Codex

### Fluxo de Execução

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Input    │────▶│   Explorer   │────▶│   Evidence   │────▶│  Reviewer   │
│  (Command) │     │   (Explore)   │     │  (Collect)   │     │  (Analyze)  │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
                                                                          │
                         ┌──────────────────────────────────────────────┘
                         ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│   Output    │◀────│  Synthesizer │◀────│   Verifier   │◀────│   Gap       │
│  (Artifact)│     │   (Write)    │     │   (Gate)     │     │  (Identify) │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
```

---

## Modo Agente: Seleção via Tab

No TUI do OpenCode, a tecla **Tab** alterna ciclicamente entre os agentes configurados (`agent_cycle`). Cada agente está vinculado a um **Agent Mode Contract** que define seu comportamento operacional:

| Tecla | Ação | Efeito |
|-------|------|--------|
| `Tab` | Cycle agent (forward) | Alterna: autocoder → general → explore → reviewer → orchestrator → autocoder |
| `Shift+Tab` | Cycle agent (reverse) | Alterna na ordem inversa |
| `<leader>+a` | Agent list | Exibe lista completa de agentes disponíveis |
| `Ctrl+P` | Command list | Exibe comandos disponíveis (autocode, analyze, review, ship) |

### Comportamento por Modo

| Agente | Modo Contract | Satisficing | Budget | Uso Típico |
|--------|---------------|-------------|--------|------------|
| `autocoder` | `modes/autocoder.yaml` | BALANCED | 72k tokens | Geração e modificação de código |
| `general` | N/A (fallback) | BALANCED | — | Tarefas gerais sem contrato específico |
| `explore` | `modes/explore.yaml` | BALANCED | 36k tokens | Explorar codebase, identificar padrões |
| `reviewer` | `modes/reviewer.yaml` | DEEP | 52k tokens | Revisão técnica, segurança, qualidade |
| `orchestrator` | `modes/orchestrator.yaml` | BALANCED | 68k tokens | Orquestrar workflows multi-agente |

### Skills Incrementais por Modo

Cada modo absorve capacidades built-in do OpenCode como **skills incrementais** — ativadas contextualmente, sem criar confusão mental de escolha entre agentes separados:

| Modo | Skill | Origem | Ativação |
|------|-------|--------|----------|
| `explore` | `impact_analysis` | impact-analyst | Automática em tarefas com mudanças de código |
| `reviewer` | `conformance_audit` | conformance-auditor | Automática em arquivos controlados por specs |
| `reviewer` | `policy_gate` | policy-guardian | Obrigatória antes de handoff |
| `orchestrator` | `memory_curation` | memory-curator | Automática quando contexto > 60% |
| `orchestrator` | `spec_architecture` | spec-architect | Automática quando novas specs são necessárias |
| `orchestrator` | `spec_compilation` | spec-compiler | Após spec_architecture, antes de delegar |

> **Princípio:** 4 modos no Tab cycling, cada um com skills internas ativadas contextualmente. O `autocoder` é execution-puro — sem skills analíticas, focado em implementar.

### Como Funciona na Prática

1. Abra o terminal no diretório do projeto e execute `opencode`
2. Digite sua tarefa no prompt de input
3. Pressione **Tab** para alternar entre agentes até selecionar o modo desejado
4. Pressione **Enter** para submeter a tarefa ao agente selecionado
5. O agente executa dentro dos limites do seu Mode Contract (budget, ferramentas, memória)

### Comandos vs. Agentes

Os comandos mapeiam diretamente para agentes, mas você pode usar qualquer agente via Tab:

| Comando | Agente Padrão | Uso |
|---------|---------------|-----|
| `/autocode <tarefa>` | `autocoder` | Gerar/modificar código |
| `/analyze <alvo>` | `explore` | Explorar codebase |
| `/review <arquivo>` | `reviewer` | Revisar código |
| `/ship <tarefa>` | `orchestrator` | Orquestrar workflow completo |

---

## Estrutura de Diretórios

> **Regra**: apenas `docs/` é superfície pública. Toda estrutura operacional (`specs/`, `domains/`, `registry/`, `templates/`, scripts, testes) reside em `.internal/`.

### `.internal/` — Núcleo Operacional

Todo aprimoramento do framework acontece aqui:

| Subdiretório | Conteúdo |
|--------------|----------|
| `.internal/specs/core/` | Contratos de orquestração domain-agnostic + Agent Mode Contracts |
| `.internal/specs/modes/` | Contratos operacionais por modo (explore, reviewer, orchestrator, autocoder) |
| `.internal/domains/` | Domain Packs (software-engineering, ml-ai, medical-imaging) |
| `.internal/registry/` | Extension Registry (catálogo de packs) |
| `.internal/templates/` | Templates para criação de novos packs |
| `.internal/scripts/` | Scripts operacionais e wrappers |
| `.internal/tests/` | Suite de testes de regressão (stable execution + mode contracts) |
| `.internal/artifacts/` | Artefatos de execução e evidências |

### `docs/` — Superfície Pública Documental

Único diretório exposto publicamente:

| Arquivo | Conteúdo |
|---------|----------|
| `CONSTITUTION_emendada.md` | Fonte da verdade arquitetural |
| `PRD_desverticalizacao_framework.md` | Plano de desverticalização |
| `ADOPTION_RUNBOOK.md` | Guia de adoção para mantenedores |
| `README.md` | Índice de documentação |

---

## Public vs Internal Artifacts

**Regra fundamental**: apenas `docs/` é superfície pública. Todo aprimoramento, spec, contract, registry, template, script e teste reside em `.internal/`.

| Camada | Localização | Acesso |
|--------|-------------|--------|
| Documentação pública | `docs/` | Público |
| Especificações do Core | `.internal/specs/` | Interno |
| Domain Packs | `.internal/domains/` | Interno |
| Extension Registry | `.internal/registry/` | Interno |
| Templates | `.internal/templates/` | Interno |
| Scripts e testes | `.internal/scripts/`, `.internal/tests/` | Interno |
| Config OpenCode pública | `opencode.json` (raiz) | Público (sanitizado) |
| Config OpenCode operacional | `.opencode/` | Interno |
| Runtime e skills | `.agent/`, `.codex/` | Interno |

---

## Domain Packs Disponíveis

### Software Engineering Pack (Default)

O pack funcional padrão fornece capacidades de desenvolvimento:

| Agente | Descrição |
|--------|-----------|
| `analyze` | Exploração de codebase, identificação de padrões |
| `reviewer` | Análise de código, segurança e qualidade |
| `autocoder` | Geração e refatoração de código |

### ML/AI Pack (Experimental, Opcional)

Disponível em `.internal/domains/ml-ai/`. Fornece:

| Agente | Descrição |
|--------|-----------|
| `ml-researcher` | Pesquisa de técnicas e papers |
| `ml-engineer` | Desenvolvimento de modelos |
| `ml-optimizer` | Otimização de hiperparâmetros |

### Medical Imaging Pack (Experimental, Opcional)

Disponível em `.internal/domains/medical-imaging/`. Requer ML/AI Pack. Fornece:

| Agente | Descrição |
|--------|-----------|
| `radiologist-assistant` | Análise de imagens médicas |
| `specialist-group-a` | Opacidades pulmonares difusas |
| `specialist-group-b` | Anomalias estruturais grosseiras |
| `specialist-group-c` | Lesões focais e fibrose |
| `specialist-group-d` | Interação coração-pulmão |
| `medical-reporter` | Geração de laudos estruturados |

> **Nota**: ML/AI e Medical Imaging são Domain Packs opcionais, não parte do Core. O Core permanece domain-agnostic.

---

## Execução Estável (Stable Execution)

O framework implementa um sistema robusto de garantias de execução:

### Garantias Implementadas

1. **Fail-fast de Configuração**: o wrapper `.internal/scripts/run-autocode.sh` falha imediatamente quando `.opencode/opencode.json` está ausente ou diverge nos campos críticos de routing

2. **Paridade de Configuração**: `opencode.json` (raiz) e `.opencode/opencode.json` devem ser equivalentes
   - Campos críticos de routing (obrigatoriamente idênticos): `default_agent`, `command.autocode.agent`, `agent.autocoder.maxSteps`, `agent.general.maxSteps`
   - Campos permitidos a divergir: campos suportados não críticos de runtime ou templates sanitizados (ex.: `providers`, `instructions`). Divergências nesses campos não podem alterar roteamento ou limites de steps.
3. **Invariantes de Execução**:
   - Sem retry ilimitado (`max_attempts ≤ 3`)
   - Sem fallback silencioso de agente
   - Gate obrigatório do verifier antes do synthesizer
   - Isolamento de write_scope entre workers paralelos
   - Prevenção de doom loops
   - Idempotência garantida

4. **Máquina de Estados**: 13 estados, 20 transições válidas, 7 proibidas
5. **Contrato de Handoff**: 12 campos obrigatórios, 6 regras de validação

### Agent Mode Contracts

Cada agente opera sob um contrato formal que define missão, escopo, budget, memória e política de erro:

| Contrato | Caminho |
|----------|---------|
| Schema | `.internal/specs/core/agent-mode-contract.yaml` |
| explore | `.internal/specs/modes/explore.yaml` |
| reviewer | `.internal/specs/modes/reviewer.yaml` |
| orchestrator | `.internal/specs/modes/orchestrator.yaml` |
| autocoder | `.internal/specs/modes/autocoder.yaml` |

### Testes de Conformidade

Execute a suite completa:

```bash
# Todos os testes (stable execution + mode contracts)
python -m pytest .internal/tests/ -v

# Apenas mode contracts
python -m pytest .internal/tests/test_mode_contracts.py -v

# Apenas stable execution
python -m pytest .internal/tests/test_stable_execution.py -v

# Validação de budget
python .internal/scripts/validate_mode_budgets.py --fail-on-violation
```

---

## Public vs Internal Artifacts

Este repositório público publica apenas interfaces e templates sanitizados.
Toda configuração/runtime operacional real permanece em **private repository only**.

- Superfície pública: `opencode.json`, `.opencode/opencode.json`, `.opencode/specs/README.md`, `.opencode/specs/*.sanitized.json`, `.opencode/manifests/README.md`, `.opencode/manifests/sanitized/*.json`, `.opencode.example/`, `.codex.example/`, `.agent.example/`.
- Superfície interna: `.opencode/` operacional (commands/plugins/runtime state), `.codex/`, `.agent/` e qualquer artefato com estado de sessão ou segredo (não versionados neste repositório público).

---

## Integração CI/CD

### Workflows Disponíveis

| Workflow | Descrição | Gatilho |
|----------|-----------|---------|
| `routing-regression.yml` | Regressão de routing + paridade de config + evidências auditáveis | Push/PR em config/spec |
| `mode-contract-compliance.yml` | Validação de contratos de modo, budget, handoff e compliance | Push/PR em modes/specs |
| `constitutional-compliance.yml` | Invariantes constitucionais + drift de contratos | Push/PR em core/domains |
| `public-artifacts-guard.yml` | Verificação de boundary público | Push/PR em main/master |
| `public-repo-guard.yml` | Scanner de padrões sensíveis | Push/PR em main/master |

> **Merge gate obrigatório**: configure os status checks `Routing Regression (Required)` e `Mode Contract Compliance (Required)` como *required* na proteção de branch.

### Execução Local

Para validar antes de push:

```bash
# Testes completos (stable execution + mode contracts)
python -m pytest .internal/tests/ -v

# Validação de budget por modo
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

Este repositório segue uma política rigorosa de configuração sanitizada:

| Categoria | Permitido (público) | Proibido (público) |
|-----------|---------------------|--------------------|
| API keys | Placeholders (`${API_KEY}`) | Tokens reais |
| Endpoints | URLs públicas | Hosts internos/IPs RFC1918 |
| Chaves criptográficas | Texto explicativo/placeholders | Blocos PEM privados |
| Config runtime | Interface e exemplos mínimos | IDs internos/estados de sessão |

### Pre-commit hooks

Configure hooks locais para validação:

```bash
# Instale dependências
python -m pip install pre-commit detect-secrets

# Configure hooks
pre-commit install

# Execute validação
pre-commit run --all-files
```

---

## Root Cause Corrigida: Routing do `/autocode`

### Descrição

O problema observado neste repositório vinha de configs com schema inválido ou obsoleto para o OpenCode v1.3.13. As chaves top-level antigas como `maxSteps` e `routing` não eram suportadas no formato usado aqui, o que invalidava a configuração efetiva.

### Solução

Use o schema suportado com top-level `agent` e `command`. Com isso, o runtime resolve `/autocode` nativamente para `autocoder` sem `--agent`:

```bash
# Execute via wrapper (recomendado)
.internal/scripts/run-autocode.sh "sua tarefa aqui"

# Ou use o comando nativo diretamente
opencode run --command autocode "sua tarefa aqui"
```

### Tracking

A investigação histórica está registrada em `.internal/artifacts/codex-swarm/run-stable-execution/debug_autocode.log`, mas a interpretação atual correta para este snapshot e este repositório é: schema inválido/stale no repositório, não bug upstream como hipótese principal.

---

## Requisitos do Sistema

- **Runtime**: Bun (para plugins/tools TypeScript)
- **CLI**: OpenCode
- **Node.js**: 20+ (para tree-sitter parsers)
- **Python**: 3.10+ (para testes)
- **Ferramentas**: Git, pre-commit

---

## Configuração de IDE

O projeto segue o padrão `.editorconfig` para consistência entre editores:

### JetBrains (IntelliJ/PyCharm)

1. Importe o projeto normalmente
2. Aplique preferências locais (tema, plugins, layout)
3. **Não** adicione arquivos de `.idea/` ao commit
4. Valide com `git status --short` antes de abrir PR

### VS Code / Neovim

O projeto inclui configuração `.editorconfig` que será aplicada automaticamente.

---

## Contribuindo

### Fluxo de Trabalho

1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`feature/nova-feature`)
3. **Faça** suas alterações seguindo as convenções
4. **Execute** testes localmente
5. **Abra** um PR com descrição detalhada

### Convenções de Commit

Siga o padrão Conventional Commits:

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[footer opcional]
```

Exemplos:
- `feat(autocoder): adicionar suporte a novo padrão de código`
- `fix(routing): corrigir fallback silencioso do /autocode`
- `docs(readme): atualizar seção de configuração`

---

## Licença

**Proprietary — All Rights Reserved**

Este projeto contém configurações operacionais sensíveis. Para uso em produção, entre em contato com a organização.

---

## Referências

- [OpenCode Documentation](https://opencode.ai/docs)
- [Codex Documentation](https://codex.io)
- [AGENTS.md](./AGENTS.md) — Regras nativas do swarm + Agent Mode Contracts
- [.internal/MANIFEST.md](./.internal/MANIFEST.md) — Manifesto de interconectividade
- [docs/README.md](./docs/README.md) — Documentação adicional
- [docs/PRD_Operacional_Arquitetura_Multiagente_Orientada_a_Contratos.md](./docs/PRD_Operacional_Arquitetura_Multiagente_Orientada_a_Contratos.md) — PRD aprovado para Agent Mode Contracts

# Agent Coding Framework (Public Template)

Repositorio publico com artefatos sanitizados para bootstrap de ambientes de agent coding.

## Public vs Internal Artifacts

### Publico por padrao (este repositorio)
- `README.md`, `AGENTS.md` e documentacao de alto nivel.
- `.internal/scripts/` e `.internal/tests/` com validacoes voltadas ao boundary publico.
- Templates sanitizados em `.agent.example/`, `.codex.example/` e `.opencode.example/`.
- `opencode.json` com placeholders e notas de uso publico.

### Interno (repositório privado)
- `.agent/`, `.codex/` e `.opencode/` com runtime operacional completo.
- Segredos, chaves privadas, tokens e qualquer artefato sensivel.

Para detalhes expandidos, consulte `docs/README.md`.
