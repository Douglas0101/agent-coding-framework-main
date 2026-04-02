# Agent Coding Framework

Repositorio de configuracoes de **agent coding** para sistemas de IA de alta confiabilidade.
Template reutilizavel para qualquer projeto que utilize **OpenCode**, **Codex** e **skills especializadas**.

## Visao Geral

Este repositorio contem a infraestrutura completa de agentes, ferramentas, plugins e workflows
para orquestracao de coding agents em projetos de engenharia de software e machine learning.

### Componentes

| Componente | Descricao | Arquivos |
|------------|-----------|----------|
| **OpenCode** | Agents, commands, plugins, tools, lib | `.opencode/` |
| **Codex** | Multi-agent swarm config | `.codex/` |
| **Skills** | 57 skills especializadas | `.agent/skills/` |
| **Workflows** | 11 workflows prontos | `.agent/workflows/` |
| **Swarm Rules** | Regras nativas do swarm | `AGENTS.md` |

## Estrutura

```
.
├── .opencode/
│   ├── agents/           # 11 agent definitions (orchestrator, reviewer, tester, etc.)
│   ├── commands/         # 6 commands (analyze, autocode, review, ship, etc.)
│   ├── plugins/          # output-filter.ts (redaction, suppression, manifest tracking)
│   ├── tools/            # examine-algorithm.ts (tree-sitter based analysis)
│   ├── lib/              # shared.ts, cache.ts, metrics.ts, tree-sitter-parsers.ts
│   ├── skills/           # self-bootstrap-opencode
│   ├── context/project/  # conventions.md
│   ├── tests/            # unit, integration, fuzz, performance tests
│   ├── package.json      # Bun dependencies
│   ├── tsconfig.json     # TypeScript config
│   ├── output-filter.config.json  # Filter configuration
│   └── .gitignore
├── .codex/
│   ├── config.toml       # Multi-agent configuration
│   └── agents/           # 6 agent configs (synthesizer, verifier, etc.)
├── .agent/
│   ├── skills/           # 57 specialized skills
│   └── workflows/        # 11 ready-to-use workflows
└── AGENTS.md             # Native Swarm Rules
```

## Skills Disponiveis (57)

### Engenharia de Codigo
- `code-quality`, `code-quality-pep`, `refactor-patterns`, `complexity-reduction`
- `dead-code-removal`, `type-safety`, `data-structures-rigor`
- `advanced-layered-engineering`, `layered-python-flow`

### Seguranca
- `security-audit`, `hardening`, `threat-modeling`, `compliance-checker`
- `vulnerability-scanner`, `security-resolver`, `dependency-audit`

### Performance
- `performance-profiling`, `deep-performance-tuning`, `gpu-profiler`
- `advanced-ml-optimization`

### ML/Data
- `data-augmentation`, `experiment-tracking`, `model-lineage`, `model-zoo`
- `ml-guardian`, `training-circuit-quality`, `inference-pipeline`
- `agentic-rag`, `agentic-reporting`, `specialist-ensemble`
- `specialist-group-a/b/c/d` (medical imaging specialists)

### DevOps/Observabilidade
- `ci-cd-optimization`, `devops-patterns`, `observability`
- `slo-sli-tracking`, `backend-reliability`, `dba-governance`
- `data-contracts`, `etl-ml-readiness`, `itch-pipeline`

### Arquitetura/Design
- `hexagonal-arch`, `enterprise-cv-refactoring`, `mas-orchestration`
- `documentation-as-code`, `semantic-versioning`

### Estrategia
- `vp-ai-strategy`, `ai-engineering-practices`, `ai-research-advisor`
- `scientific-logbook`, `ui-ux-engineering`

### Utilities
- `auto-fixer`, `test-coverage`, `rpa-engineer`

## Workflows Disponiveis (11)

| Workflow | Descricao |
|----------|-----------|
| `full-quality-check` | Verificacao completa de qualidade |
| `security-hardening` | Hardening de seguranca |
| `rpa-quality` | Pipeline RPA de qualidade |
| `code-quality` | Verificacao de qualidade de codigo |
| `performance-optimization` | Otimizacao de performance |
| `refactor-session` | Sessao de refatoracao |
| `etl-ml-readiness` | Readiness para ML pipeline |
| `validate-data` | Validacao de dados |
| `run-pipeline` | Execucao de pipeline |
| `run-tests` | Execucao de testes |
| `linux_remote_setup` | Setup remoto Linux |

## OpenCode Agents

### Primary Agent
- **orchestrator**: Orquestra analise, implementacao, revisao e validacao com confidence gates

### Subagents
| Agent | Funcao |
|-------|--------|
| `hypothesis` | Geracao de hipoteses testaveis |
| `evidence` | Coleta de evidencias com source grading |
| `citation` | Verificacao de credibilidade de fontes |
| `contradiction` | Deteccao e resolucao de contradicoes |
| `gap` | Identificacao de lacunas de cobertura |
| `synthesis` | Consolidacao de achados multiplos |
| `validation` | Verificacao independente |
| `reviewer` | Revisao tecnica com severity classification |
| `tester` | Execucao de harness de testes |
| `autocoder` | Coding agent com raciocinio sequencial |

## Codex Agents

| Agent | Funcao |
|-------|--------|
| `synthesizer` | Escrita final do pacote |
| `verifier` | Gatekeeper de completude |
| `docs-researcher` | Pesquisa de documentacao externa |
| `runbook-writer` | Documentacao artifact-first |
| `runtime-validator` | Validacao de baseline runtime |
| `viewer-consolidator` | Exploracao de contratos API/UI |

## Uso

### Como Template

1. Clone este repositorio no seu projeto:
   ```bash
   git clone <repo-url> /tmp/agent-framework
   cp -r /tmp/agent-framework/.opencode seu-projeto/
   cp -r /tmp/agent-framework/.codex seu-projeto/
   cp -r /tmp/agent-framework/.agent seu-projeto/
   cp /tmp/agent-framework/AGENTS.md seu-projeto/
   ```

2. Instale dependencias no `.opencode/`:
   ```bash
   cd seu-projeto/.opencode
   bun install
   ```

3. Customize `conventions.md` e `AGENTS.md` para seu projeto.

### Com OpenCode

O OpenCode detectara automaticamente os agents e commands ao iniciar no diretorio do projeto.

### Com Codex

O Codex usara `.codex/config.toml` para configurar o swarm multi-agent.

## Requisitos

- **Bun** runtime (para plugins/tools TypeScript)
- **OpenCode** CLI
- **Node.js** 20+ (para tree-sitter parsers)

## Licenca

Proprietary -- All Rights Reserved.

---

*Framework extraido do Projeto Vitruviano -- High-Assurance Medical AI Engine*
